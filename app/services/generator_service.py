"""GeneratorService — full pipeline orchestration.

extract → detect work type → validate → build docx → save to tracker.
Runs on a worker thread; reports progress via callback.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.builders.cost_table_extractor import extract_cost_table_image
from app.builders.docx_builder import DocxBuilder
from app.builders.work_type_detector import detect_work_type
from app.data.case_repository import CaseRepository
from app.data.database import Database
from app.domain.enums import CaseStatus, FileType, WorkType
from app.domain.exceptions import ExtractionError, ValidationError
from app.domain.models import Case, ExtractionResult, Material
from app.extractors.extractor_factory import ExtractorFactory
from app.infrastructure.audit_logger import AuditLogger
from app.infrastructure.config_manager import ConfigManager
from app.infrastructure.recovery_manager import RecoveryManager
from app.services.validator_service import ValidatorService

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, str], None]  # (percent, message)


class GeneratorService:
    """Orchestrates the executive-summary generation pipeline."""

    def __init__(
        self,
        db: Database | None = None,
        config: ConfigManager | None = None,
    ) -> None:
        self._config = config or ConfigManager()
        self._db = db or Database(self._config.db_path)
        self._repo = CaseRepository(self._db)
        self._validator = ValidatorService()
        self._docx_builder = DocxBuilder()
        self._audit = AuditLogger(self._db)
        self._recovery = RecoveryManager(self._config.recovery_dir)

    # ── public entry point ──────────────────────────────────────

    def generate(
        self,
        scheme_pdf_path: str | Path | None = None,
        site_visit_pdf_path: str | Path | None = None,
        pm06_excel_path: str | Path | None = None,
        progress_cb: ProgressCallback | None = None,
    ) -> Case:
        """Run the full pipeline synchronously. Returns the saved Case.

        Call from a worker thread to keep the UI responsive.
        """
        cb = progress_cb or (lambda p, m: None)

        try:
            # 1 ── Extract ───────────────────────────────────────
            cb(5, "Extracting scheme PDF…")
            scheme_data = self._extract_file(scheme_pdf_path, FileType.SCHEME_PDF)

            cb(20, "Extracting site-visit form…")
            sv_data = self._extract_file(site_visit_pdf_path, FileType.SITE_VISIT_PDF)

            cb(35, "Extracting PM06 Excel…")
            pm06_data = self._extract_file(pm06_excel_path, FileType.PM06_EXCEL)

            # 2 ── Merge into Case ───────────────────────────────
            cb(50, "Merging extracted data…")
            case = self._merge_into_case(scheme_data, sv_data, pm06_data)

            # Collect extraction-level warnings for the Review Tab
            extraction_warnings: list[str] = []
            for label, data in [
                ("Scheme PDF", scheme_data),
                ("Site Visit PDF", sv_data),
                ("PM06 Excel", pm06_data),
            ]:
                if "_error" in data:
                    extraction_warnings.append(
                        f"{label}: {data['_error'].message}"
                    )
            case.extraction_warnings = extraction_warnings

            # Store source file paths on the case for reference
            case.scheme_pdf_path = str(scheme_pdf_path) if scheme_pdf_path else None
            case.site_visit_pdf_path = str(site_visit_pdf_path) if site_visit_pdf_path else None
            case.pm06_excel_path = str(pm06_excel_path) if pm06_excel_path else None

            # 3 ── Detect work type ──────────────────────────────
            cb(55, "Detecting work type…")
            case.work_type = detect_work_type(
                materials=case.materials or [],
                nature_text=case.nature_of_scheme or "",
            )

            # 3b ── Derive DT-specific fields from materials ─────
            self._derive_dt_fields(case)

            # 4 ── Zone / District / WBS lookup ──────────────────
            self._resolve_zone_wbs(case)

            # 4b ── Derive CAPEX year from file path date ────────
            self._derive_capex_year(case)

            # 5 ── Validate ──────────────────────────────────────
            cb(60, "Validating…")
            validation = self._validator.validate(case)
            case.validation_result = validation

            # 6 ── Cost table image ──────────────────────────────
            cb(70, "Extracting cost table image…")
            cost_image: bytes | None = None
            if scheme_pdf_path and Path(scheme_pdf_path).exists():
                cost_img_path = Path(self._config.output_dir) / "cost_table_temp.png"
                if extract_cost_table_image(Path(scheme_pdf_path), cost_img_path):
                    cost_image = cost_img_path.read_bytes()
                    cost_img_path.unlink(missing_ok=True)

            # 7 ── Build DOCX ────────────────────────────────────
            cb(80, "Building Executive Summary…")
            output_dir = Path(self._config.output_dir)
            safe_order = (case.order_no or "UNKNOWN").replace("/", "_").replace("\\", "_")
            output_name = f"Executive_Summary_{safe_order}.docx"

            # Determine source folder: save alongside input files
            source_dir = self._find_source_dir(scheme_pdf_path, pm06_excel_path, site_visit_pdf_path)
            # Primary save location: source folder (if available), else output/
            primary_dir = source_dir if source_dir else output_dir
            primary_dir.mkdir(parents=True, exist_ok=True)
            output_path = primary_dir / output_name

            # If file is locked (open in Word), use an incremented name
            if output_path.exists():
                try:
                    with open(output_path, "a"):
                        pass
                except PermissionError:
                    for counter in range(1, 100):
                        alt = primary_dir / f"Executive_Summary_{safe_order}_{counter}.docx"
                        if not alt.exists():
                            output_path = alt
                            break
                        try:
                            with open(alt, "a"):
                                pass
                            output_path = alt
                            break
                        except PermissionError:
                            continue
            self._docx_builder.build_summary(
                case=case, output_path=output_path, cost_table_image=cost_image
            )
            case.output_docx_path = str(output_path)

            # Also copy to output/ directory for centralized access
            if source_dir and source_dir != output_dir:
                import shutil
                output_dir.mkdir(parents=True, exist_ok=True)
                copy_dest = output_dir / output_path.name
                try:
                    shutil.copy2(str(output_path), str(copy_dest))
                except Exception as copy_err:
                    logger.warning("Could not copy to output/: %s", copy_err)

            # 8 ── Persist to DB ─────────────────────────────────
            cb(90, "Saving to database…")
            case.status = CaseStatus.PENDING
            self._repo.create_case(case)

            if scheme_pdf_path:
                from app.infrastructure.file_utils import compute_file_hash
                self._repo.add_source_file(
                    case.id, "SCHEME_PDF", str(scheme_pdf_path),
                    compute_file_hash(str(scheme_pdf_path))
                )
            if site_visit_pdf_path:
                self._repo.add_source_file(
                    case.id, "SITE_VISIT_PDF", str(site_visit_pdf_path),
                    compute_file_hash(str(site_visit_pdf_path))
                )
            if pm06_excel_path:
                self._repo.add_source_file(
                    case.id, "PM06_EXCEL", str(pm06_excel_path),
                    compute_file_hash(str(pm06_excel_path))
                )
            if case.output_docx_path:
                self._repo.add_generated_doc(
                    case.id, case.output_docx_path,
                    self._config.engineer_name or "Unknown"
                )

            self._audit.log(action="GENERATED", case_id=case.id, details=f"Summary generated → {output_name}")
            self._recovery.clear_state()

            cb(100, "Done ✓")
            logger.info("Pipeline complete for Order %s → %s", case.order_no, output_path)
            return case

        except Exception:
            # Save recovery state so work isn't lost on crash
            self._recovery.update_state("last_error", "pipeline_failure")
            raise

    # ── worker thread helper ────────────────────────────────────

    @staticmethod
    def _find_source_dir(
        scheme_pdf: str | Path | None,
        pm06_excel: str | Path | None,
        site_visit: str | Path | None,
    ) -> Path | None:
        """Determine the common source folder of the input files.

        Returns the parent directory that contains at least one source file,
        or None if no valid source path is available.
        """
        for p in (scheme_pdf, pm06_excel, site_visit):
            if p and Path(p).exists():
                return Path(p).parent
        return None

    def generate_async(
        self,
        scheme_pdf_path: str | Path | None = None,
        site_visit_pdf_path: str | Path | None = None,
        pm06_excel_path: str | Path | None = None,
        progress_cb: ProgressCallback | None = None,
        done_cb: Callable[[Case | None, Exception | None], None] | None = None,
    ) -> threading.Thread:
        """Start generation on a daemon thread. Returns the Thread object."""

        def _worker() -> None:
            try:
                case = self.generate(
                    scheme_pdf_path, site_visit_pdf_path, pm06_excel_path, progress_cb
                )
                if done_cb:
                    done_cb(case, None)
            except Exception as exc:
                logger.exception("Pipeline failed")
                if done_cb:
                    done_cb(None, exc)

        t = threading.Thread(target=_worker, daemon=True, name="GeneratorWorker")
        t.start()
        return t

    # ── private helpers ─────────────────────────────────────────

    def _extract_file(
        self, path: str | Path | None, file_type: FileType
    ) -> Dict[str, ExtractionResult]:
        """Extract data from a single file. Returns empty dict if path is None.

        Logs warnings for extraction errors and propagates them as
        LOW-confidence ``_error`` / ``_warning`` results so the
        validator and review tab can surface them to the user.
        """
        if path is None or not Path(path).exists():
            return {}
        extractor = ExtractorFactory.get_extractor(file_type)
        results = extractor.extract(str(path))

        # Surface extraction-level errors so they aren't silently lost
        if "_error" in results:
            err = results["_error"]
            logger.warning(
                "Extraction warning for %s (%s): %s",
                path, file_type.value, err.message,
            )
        return results

    def _merge_into_case(
        self,
        scheme: Dict[str, ExtractionResult],
        sv: Dict[str, ExtractionResult],
        pm06: Dict[str, ExtractionResult],
    ) -> Case:
        """Merge extraction results into a single Case.

        Priority: scheme > pm06 > site_visit (for overlapping fields).
        """
        case = Case()
        # Combine all dicts — higher-priority sources only overwrite
        # if they have a non-None value (avoid losing good data).
        combined: Dict[str, ExtractionResult] = {}
        # Fields where longer values are preferred (address/name text blocks)
        _PREFER_LONGER = {"address", "applicant_name"}
        for source in (sv, pm06, scheme):  # last wins → scheme has top priority
            for k, v in source.items():
                if v.value is not None or k not in combined:
                    if k in _PREFER_LONGER and k in combined and combined[k].value is not None:
                        # Keep the longer string for address/name fields
                        existing = str(combined[k].value)
                        candidate = str(v.value) if v.value is not None else ""
                        if len(candidate) > len(existing):
                            combined[k] = v
                    else:
                        combined[k] = v

        field_names = {f.name for f in dc_fields(Case)}

        # Aliases: extraction key → Case field name
        _ALIASES: Dict[str, str] = {
            "dt_capacity_existing": "existing_dt_capacity",
            "sanctioned_load": "load_applied",
        }
        # Keys to skip entirely (list values that don't map to scalar fields)
        _SKIP_KEYS = {"notification_nos", "feeders", "lt_extension_materials"}

        for key, result in combined.items():
            if result.value is None:
                continue
            # Map extraction keys to Case fields
            attr = key.lower().replace(" ", "_").replace("-", "_")
            if attr in _SKIP_KEYS:
                continue
            attr = _ALIASES.get(attr, attr)  # check alias table
            if attr in field_names:
                val = result.value
                # Coerce lists to first element for scalar fields
                if isinstance(val, list):
                    val = val[0] if val else None
                if val is not None:
                    setattr(case, attr, val)

        # Special handling for materials list
        if "materials" in combined and combined["materials"].value:
            raw = combined["materials"].value
            if isinstance(raw, list):
                mats: List[Material] = []
                for item in raw:
                    if isinstance(item, Material):
                        mats.append(item)
                    elif isinstance(item, dict):
                        mats.append(Material(**item))
                # Clean up newlines in material descriptions from PDF extraction
                for m in mats:
                    if m.description and "\n" in m.description:
                        m.description = m.description.replace("\n", " ").strip()
                case.materials = mats

        # Supplement with LT extension materials from PM06 Excel when BOM is empty
        if not case.materials and "lt_extension_materials" in combined:
            lt_ext = combined["lt_extension_materials"].value
            if lt_ext and isinstance(lt_ext, list):
                for item in lt_ext:
                    if isinstance(item, dict) and item.get("description"):
                        case.materials.append(Material(
                            description=item["description"],
                            quantity=item.get("quantity"),
                        ))

        return case

    def _resolve_zone_wbs(self, case: Case) -> None:
        """Look up zone/district/WBS from config maps."""
        # Derive zone from tapping pole, substation_name, or scope_of_work
        # Patterns: HT572-63/21A → 572, UHT 572-27 → 572, 511-65/5 → 511, U511-49 → 511
        if not case.zone:
            import re
            for field in (case.tapping_pole, case.substation_name, case.scope_of_work):
                if field:
                    # Try HT-prefix (with optional space): HT572, HT 572, UHT572, UHT 572
                    m = re.search(r"U?HT\s*(\d{3,4})", field, re.IGNORECASE)
                    if m:
                        case.zone = m.group(1)
                        break
                    # Try U-prefix numeric (with optional space): U511, U 532
                    m = re.search(r"U\s*(\d{3,4})", field, re.IGNORECASE)
                    if m:
                        case.zone = m.group(1)
                        break
                    # Try bare numeric pole: 511-65/5, 523-53/1/1
                    m = re.search(r"^(\d{3,4})[-/]", field)
                    if m:
                        case.zone = m.group(1)
                        break

        # Validate extracted zone against known districts
        if case.zone:
            zone_str = case.zone.strip()
            found = False
            for _code, districts in self._config.zone_district_map.items():
                if int(zone_str) in districts if zone_str.isdigit() else False:
                    found = True
                    break
            if not found and zone_str.isdigit():
                logger.warning("Zone '%s' not found in any district mapping", zone_str)

        if case.zone and not case.district:
            district = self._config.get_district_for_zone(case.zone)
            if district:
                case.district = district
        if case.district and not case.wbs_no:
            wbs = self._config.get_wbs_for_district(case.district)
            if wbs:
                case.wbs_no = wbs

    @staticmethod
    def _derive_capex_year(case: Case) -> None:
        """Derive CAPEX financial year from file path date folder (dd-mm-yyyy)."""
        if case.capex_year:
            return
        import re
        from datetime import date as dt_date
        for path_str in (case.scheme_pdf_path, case.pm06_excel_path):
            if not path_str:
                continue
            m = re.search(r"(\d{2})-(\d{2})-(\d{4})", path_str)
            if m:
                try:
                    d = dt_date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                    from app.infrastructure.formatting import get_capex_year
                    case.capex_year = get_capex_year(d)
                    return
                except (ValueError, TypeError):
                    continue

    @staticmethod
    def _derive_dt_fields(case: Case) -> None:
        """Derive DT-specific fields from materials and scope when missing."""
        import re

        mats = case.materials or []

        # ── new_transformer_rating from materials ───────────────
        if not case.new_transformer_rating:
            for m in mats:
                desc = (m.description or "").upper()
                # Look for new (larger) transformer: TRANSFORMER250KVA, TRANSFORMER 500KVA, etc.
                match = re.search(r"TRANSFORMER\s*(\d+)\s*KVA", desc)
                if match:
                    kva = int(match.group(1))
                    # Skip the old/existing transformer (smaller one)
                    existing_kva = 0
                    if case.existing_dt_capacity:
                        em = re.search(r"(\d+)\s*[kK][vV][aA]", case.existing_dt_capacity)
                        if em:
                            existing_kva = int(em.group(1))
                    if kva > existing_kva:
                        case.new_transformer_rating = f"{kva} KVA"
                        break

        # ── acb_description from materials ──────────────────────
        if not case.acb_description:
            for m in mats:
                desc = (m.description or "").upper()
                if "ACB" in desc or "LT ACB" in desc:
                    # e.g. "LTACB 400A WITHFDR" → "one additional LT ACB"
                    acb_match = re.search(r"ACB\s*(\d+)\s*A", desc)
                    if acb_match:
                        case.acb_description = f"one additional LT ACB"
                    else:
                        case.acb_description = "one additional LT ACB"
                    break

        # ── existing_dt_capacity clean-up ───────────────────────
        if case.existing_dt_capacity:
            cap = case.existing_dt_capacity.strip()
            # Normalize: "63 kVA DT" → "63 kVA DT" (keep DT suffix)
            m = re.search(r"(\d+)\s*[kK][vV][aA]", cap)
            if m:
                kva = m.group(1)
                has_dt = "DT" in cap.upper()
                case.existing_dt_capacity = f"{kva}kVA DT" if has_dt else f"{kva} KVA"