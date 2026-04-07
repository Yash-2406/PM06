"""Help Tab — user guide, FAQ, step-by-step instructions."""

from __future__ import annotations

import tkinter as tk

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

HELP_TEXT = """\
╔══════════════════════════════════════════════════════════════╗
║            TPDDL PM06 Executive Summary Generator           ║
╚══════════════════════════════════════════════════════════════╝

STEP-BY-STEP GUIDE
═══════════════════

1. Go to the "Generate" tab
2. Upload your source documents:
   • Scheme Copy PDF — the SAP-generated scheme document
   • Site Visit Form PDF — the scanned site-visit form (optional)
   • PM06 Format Excel — the PM06 format workbook
3. Click "Generate Executive Summary"
4. Review the extracted data on the "Review" tab
5. Edit any fields that need correction
6. Click "Approve & Save" or "Reject"

SUPPORTED FILE TYPES
════════════════════
• PDF files (.pdf) — for Scheme Copy and Site Visit Form
• Excel files (.xlsx) — for PM06 Format

WORK TYPES
══════════
The tool auto-detects the work type from materials:
• LT Standard — LT line extension up to 5 poles
• LT with HT/PSCC Pole — LT extension with HT infrastructure
• DT Augmentation — transformer capacity upgrade
• ABC Wiring — Aerial Bunched Cable installation

TRACKER
═══════
• All generated cases appear in the Tracker tab
• Filter by district, zone, or status
• Double-click a row to view/edit details
• Export to Excel for reporting

MIS REPORTS
═══════════
• View summary counts by district and status
• Track total project amounts

TIPS
════
• Drag and drop files directly onto the drop zones
• The tool saves your work automatically
• If the application crashes, it will offer to recover on restart
• Check the Settings tab to customize output folder and mappings

FAQ
═══
Q: Why can't I save to the tracker Excel?
A: Close the Excel file if it's open in another program, then click Sync.

Q: The OCR results look wrong — what can I do?
A: Ensure Tesseract OCR is installed and the scan quality is good.
   You can manually edit extracted fields on the Review tab.

Q: How do I change the zone-district mapping?
A: Go to Settings → Zone-District Mapping and edit the JSON table.

Q: Where are the generated documents saved?
A: By default, in the 'output' folder. Change this in Settings.
"""


class HelpTab(ttk.Frame):
    """Tab with user guide and FAQ."""

    def __init__(self, master: tk.Widget, **kwargs):
        super().__init__(master, **kwargs)
        self._build_ui()

    def _build_ui(self) -> None:
        text = tk.Text(
            self,
            wrap=tk.WORD,
            font=("Consolas", 10),
            padx=15,
            pady=15,
            state=tk.NORMAL,
        )
        text.insert("1.0", HELP_TEXT)
        text.configure(state=tk.DISABLED)

        scrollbar = ttk.Scrollbar(self, orient=VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)

        text.pack(side=LEFT, fill=BOTH, expand=YES)
        scrollbar.pack(side=RIGHT, fill=Y)
