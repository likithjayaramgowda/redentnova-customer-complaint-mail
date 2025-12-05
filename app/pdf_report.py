from __future__ import annotations
from io import BytesIO
from typing import Any, Dict, List, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth


# IMPORTANT:
# These strings must match your Google Sheet header names exactly.
FIELD_SECTIONS: List[Tuple[str, List[str]]] = [
    (
        "Customer Information",
        [
            "First Name",
            "Last Name",
            "Phone Number",
            "Email Address",
            "Address",
        ],
    ),
    (
        "Product Information",
        [
            "Product Name",
            "Product Size",
            "LOT / Serial Number",
            "Quantity",
            "Purchased From (Distributor)",
            "Country",
        ],
    ),
    (
        "Complaint Details",
        [
            "Complaint Type",
            "Complaint Description",
            "Additional Information",
            "Primary Solution (If Provided)",
            "Comments (If Applicable)",
        ],
    ),
    (
        "Regulatory Information",
        [
            "Should this complaint be reported to authorities?",
            "Was the device used on a patient?",
            "Was the device cleaned before returning?",
            "What kind of system is this?",
        ],
    ),
]


def _wrap_text(text: str, max_width: float, font_name: str, font_size: int) -> List[str]:
    """Wrap text into multiple lines that fit inside max_width."""
    text = "" if text is None else str(text)
    if not text:
        return [""]

    words = text.split()
    lines: List[str] = []
    current = ""

    for w in words:
        trial = (current + " " + w).strip()
        if stringWidth(trial, font_name, font_size) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = w

    if current:
        lines.append(current)
    return lines or [""]


def build_pdf_bytes(title: str, fields: Dict[str, Any]) -> bytes:
    """
    Build a complaint PDF that looks like a structured form:
    - Title + Submission ID + Timestamp at top
    - Sections with labels and boxes
    - Box height auto-adjusts to content length
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_width, page_height = A4

    # Layout constants
    margin_x = 25 * mm
    top_y = page_height - 25 * mm
    bottom_margin = 20 * mm

    line_height = 6 * mm
    min_box_height = 7 * mm
    long_min_box_height = 20 * mm

    label_col_width = 55 * mm
    value_col_width = page_width - 2 * margin_x - label_col_width - 5 * mm

    font_label = "Helvetica-Bold"
    font_value = "Helvetica"
    size_title = 16
    size_section = 12
    size_label = 9
    size_value = 9

    # Helper: new page with title
    def start_page():
        nonlocal y
        c.setFont("Helvetica-Bold", size_title)
        c.drawCentredString(page_width / 2.0, top_y, title)
        y = top_y - 2 * line_height

    # Helper: ensure there is enough vertical space, otherwise new page
    def ensure_space(h: float):
        nonlocal y
        if y - h < bottom_margin:
            c.showPage()
            start_page()

    # Start first page
    y = 0
    start_page()

    # Submission metadata (we expect caller to add these into fields)
    submission_id = fields.get("submission_id", "")
    timestamp = fields.get("timestamp", "")

    c.setFont(font_value, 10)
    if submission_id:
        c.drawString(margin_x, y, f"Submission ID: {submission_id}")
        y -= line_height
    if timestamp:
        c.drawString(margin_x, y, f"Timestamp: {timestamp}")
        y -= line_height * 1.5

    # Don't show these again in the body
    body_fields = {k: v for k, v in fields.items() if k not in {"submission_id", "timestamp"}}

    # Which fields are considered "long text"
    long_text_fields = {
        "Address",
        "Complaint Description",
        "Additional Information",
        "Comments (If Applicable)",
    }

    # Draw sections
    for section_title, section_fields in FIELD_SECTIONS:
        # Skip the section if absolutely none of the fields exist
        if not any(name in body_fields for name in section_fields):
            continue

        # Section heading
        ensure_space(3 * line_height)
        c.setFont("Helvetica-Bold", size_section)
        c.drawString(margin_x, y, section_title)
        y -= line_height * 1.3

        for field_name in section_fields:
            raw_value = body_fields.get(field_name, "")
            value = "" if raw_value is None else str(raw_value)

            # Wrap text first, so we know how tall the box must be
            c.setFont(font_value, size_value)
            wrapped = _wrap_text(value, value_col_width - 4, font_value, size_value)
            num_lines = max(1, len(wrapped))

            # Choose min box height based on type
            base_min = long_min_box_height if field_name in long_text_fields else min_box_height
            box_height = max(base_min, line_height * (num_lines + 0.5))

            ensure_space(box_height + line_height * 1.2)

            # Draw label
            c.setFont(font_label, size_label)
            c.drawString(margin_x, y, field_name + " :")

            # Draw box
            box_x = margin_x + label_col_width
            box_y = y - box_height + 2
            c.setStrokeColor(colors.black)
            c.rect(box_x, box_y, value_col_width, box_height, stroke=1, fill=0)

            # Draw value lines inside box
            c.setFont(font_value, size_value)
            text_y = box_y + box_height - line_height
            for line in wrapped:
                if text_y < box_y + 2:
                    break
                c.drawString(box_x + 2, text_y, line)
                text_y -= line_height

            # Move below this row
            y = box_y - line_height * 0.3

        # Extra gap after each section
        y -= line_height * 0.6

    c.showPage()
    c.save()
    return buf.getvalue()
