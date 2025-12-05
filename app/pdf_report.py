from __future__ import annotations
from io import BytesIO
from typing import Any, Dict, List, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth


# Logical sections of the complaint form and the order of fields in each section.
# IMPORTANT: These field names must match your Google Sheet / payload labels exactly.
FIELD_SECTIONS: List[Tuple[str, List[str]]] = [
    (
        "Customer Information",
        [
            "First Name  ",
            "Last Name  ",
            "Phone Number  ",
            "Email Address  ",
            "Address  ",
        ],
    ),
    (
        "Product Information",
        [
            "Product Name  ",
            " Product Size  ",
            "LOT / Serial Number  ",
            "Quantity  ",
            "Purchased From (Distributor)  ",
            "Country  ",
        ],
    ),
    (
        "Complaint Details",
        [
            "Complaint Type  ",
            "Complaint Description  ",
            "Additional Information  ",
            "Primary Solution (If Provided)  ",
            "Comments (If Applicable)  ",
        ],
    ),
    (
        "Regulatory Information",
        [
            "Should this complaint be reported to authorities?  ",
            "Was the device used on a patient?  ",
            "Was the device cleaned before returning?  ",
            "What kind of system is this?  ",
        ],
    ),
]


def _wrap_text(text: str, max_width: float, font_name: str, font_size: int) -> List[str]:
    """Wrap text so it fits into max_width."""
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
    """Generate a complaint PDF with a simple form-style layout."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    margin_x = 25 * mm
    margin_top = height - 25 * mm
    line_height = 6 * mm
    box_height_small = 8 * mm
    box_height_large = 20 * mm
    label_col_width = 60 * mm
    value_col_width = width - 2 * margin_x - label_col_width - 5 * mm

    # ----- Title -----
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2.0, margin_top, title)
    y = margin_top - 2 * line_height

    # Submission metadata (if present)
    submission_id = str(fields.get("submission_id", ""))
    timestamp = str(fields.get("timestamp", ""))

    c.setFont("Helvetica", 10)
    if submission_id:
        c.drawString(margin_x, y, f"Submission ID: {submission_id}")
        y -= line_height
    if timestamp:
        c.drawString(margin_x, y, f"Timestamp: {timestamp}")
        y -= line_height * 1.5

    # We don't want submission_id/timestamp to appear again in the form body
    body_fields = {k: v for k, v in fields.items() if k not in {"submission_id", "timestamp"}}

    font_label = "Helvetica-Bold"
    font_value = "Helvetica"
    size_label = 10
    size_value = 10

    def ensure_space(required_height: float) -> float:
        nonlocal y
        # Start a new page if we are running out of space
        if y - required_height < 20 * mm:
            c.showPage()
            # re-draw title on new page
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(width / 2.0, height - 25 * mm, title)
            y = height - 25 * mm - 3 * line_height
            c.setFont(font_label, size_label)
        return y

    # Draw all sections in order
    for section_title, section_fields in FIELD_SECTIONS:
        # Only render section if at least one of its fields exists
        if not any(name in body_fields for name in section_fields):
            continue

        ensure_space(3 * line_height)
        # Section heading
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin_x, y, section_title)
        y -= line_height * 1.3

        c.setFont(font_label, size_label)

        for field_name in section_fields:
            if field_name not in body_fields:
                value = ""
            else:
                raw = body_fields[field_name]
                value = "" if raw is None else str(raw)

            # Long text fields get bigger boxes
            is_long = field_name in {
                "Address",
                "Complaint Description",
                "Additional Information",
                "Comments (If Applicable)",
            }
            box_h = box_height_large if is_long else box_height_small

            ensure_space(box_h + line_height * 1.5)

            # Label
            c.setFont(font_label, size_label)
            c.drawString(margin_x, y, field_name + " :")

            # Box
            box_y = y - box_h + 2
            box_x = margin_x + label_col_width
            c.setStrokeColor(colors.black)
            c.rect(box_x, box_y, value_col_width, box_h, stroke=1, fill=0)

            # Value text inside box
            c.setFont(font_value, size_value)
            wrapped = _wrap_text(
                value,
                max_width=value_col_width - 4,
                font_name=font_value,
                font_size=size_value,
            )
            text_y = box_y + box_h - line_height + 1
            for line in wrapped:
                if text_y < box_y + 2:
                    break
                c.drawString(box_x + 2, text_y, line)
                text_y -= line_height

            # Move cursor below the box
            y = box_y - line_height * 0.3

        # Extra space after each section
        y -= line_height * 0.7

    c.showPage()
    c.save()
    return buf.getvalue()
