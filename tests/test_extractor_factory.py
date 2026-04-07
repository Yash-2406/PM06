"""Tests for app.extractors.extractor_factory."""

from app.domain.enums import FileType
from app.extractors.extractor_factory import ExtractorFactory
from app.extractors.pm06_excel_extractor import PM06ExcelExtractor
from app.extractors.scheme_pdf_extractor import SchemePDFExtractor
from app.extractors.site_visit_extractor import SiteVisitExtractor


class TestExtractorFactory:
    def test_scheme_pdf(self):
        e = ExtractorFactory.get_extractor(FileType.SCHEME_PDF)
        assert isinstance(e, SchemePDFExtractor)

    def test_site_visit(self):
        e = ExtractorFactory.get_extractor(FileType.SITE_VISIT_PDF)
        assert isinstance(e, SiteVisitExtractor)

    def test_pm06_excel(self):
        e = ExtractorFactory.get_extractor(FileType.PM06_EXCEL)
        assert isinstance(e, PM06ExcelExtractor)
