from __future__ import annotations
import os
from io import BytesIO
from typing import Any, Dict, List, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth

# Path to logo file (relative to repo root)
LOGO_PATH = os.environ.get("PDF_LOGO_PATH", "logo.png")

# Footer text (document version / ID)
DOC_VERSION = os.environ.get("PDF_DOC_VERSION", "QAF-12-01 (rev 04)")

# Sections and logical field order
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
            "Product Size  ",
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


def _normalize_key(key: str) -> str:
    return (
        key.lower()
        .replace(":", "")
        .replace("?", "")
        .replace("/", " ")
        .replace("_", " ")
        .strip()
    )


def _lookup_field_value(all_fields: Dict[str, Any], logical_name: str) -> Any:
    if logical_name in all_fields:
        return all_fields[logical_name]
    target = _normalize_key(logical_name)
    for real_key, value in all_fields.items():
        if _normalize_key(str(real_key)) == target:
            return value
    return ""


def build_pdf_bytes(title: str, fields: Dict[str, Any]) -> bytes:
    """
    Build the complaint PDF with:
      - Logo centered at top
      - Title
      - Date + Complaint ID
      - Sections with aligned labels + auto-sized boxes
      - Footer with document version + page number
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    page_width, page_height = A4

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

    complaint_id = str(fields.get("submission_id") or fields.get("Complaint ID") or "")
    timestamp = str(fields.get("timestamp") or fields.get("Date") or "")

    page_num = 1
    y = 0  # updated by draw_header

    def draw_header():
        nonlocal y
        # Large centered logo
        if LOGO_PATH and os.path.exists(LOGO_PATH):
            logo_width = 80 * mm
            logo_height = 25 * mm
            logo_x = (page_width - logo_width) / 2
            logo_y = top_y - logo_height

            c.drawImage(
                LOGO_PATH,
                logo_x,
                logo_y,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask="auto",
            )

            y = logo_y - 8 * mm
        else:
            y = top_y

        # Title
        c.setFont("Helvetica-Bold", size_title)
        c.drawCentredString(page_width / 2.0, y, title)
        y -= 2 * line_height

        # Date + Complaint ID
        c.setFont(font_value, 10)
        if timestamp:
            c.drawString(margin_x, y, f"Date: {timestamp}")
            y -= line_height
        if complaint_id:
            c.drawString(margin_x, y, f"Complaint ID: {complaint_id}")
            y -= line_height * 1.5

    def draw_footer():
        c.setFont("Helvetica", 8)
        footer_y = 12 * mm
        c.drawString(margin_x, footer_y, DOC_VERSION)
        c.drawRightString(page_width - margin_x, footer_y, f"Page {page_num}")

    def finish_page(start_new: bool):
        nonlocal page_num
        draw_footer()
        c.showPage()
        page_num += 1
        if start_new:
            draw_header()

    def ensure_space(h: float):
        nonlocal y
        if y - h < bottom_margin:
            finish_page(start_new=True)

    # Start first page
    draw_header()

    body_fields = dict(fields)
    long_text_fields = {
        "Address",
        "Complaint Description",
        "Additional Information",
        "Comments (If Applicable)",
    }

    for section_title, section_fields in FIELD_SECTIONS:
        # Skip empty sections
        if not any(_lookup_field_value(body_fields, name) not in ("", None, "") for name in section_fields):
            continue

        ensure_space(3 * line_height)
        c.setFont("Helvetica-Bold", size_section)
        c.drawString(margin_x, y, section_title)
        y -= line_height * 1.3

        for logical_name in section_fields:
            raw_value = _lookup_field_value(body_fields, logical_name)
            value = "" if raw_value is None else str(raw_value)

            label_text = logical_name

            # Wrap label + value
            c.setFont(font_label, size_label)
            label_lines = _wrap_text(label_text, label_col_width - 2, font_label, size_label)
            label_block_height = max(line_height * len(label_lines), line_height)

            c.setFont(font_value, size_value)
            value_lines = _wrap_text(value, value_col_width - 4, font_value, size_value)
            num_value_lines = max(1, len(value_lines))

            base_min = long_min_box_height if logical_name in long_text_fields else min_box_height
            box_height = max(base_min, line_height * (num_value_lines + 0.5))

            row_height = max(label_block_height, box_height)
            ensure_space(row_height + line_height * 0.4)

            row_top = y
            row_bottom = y - row_height

            # Label
            c.setFont(font_label, size_label)
            label_start_y = row_top - (row_height - label_block_height) / 2
            current_y = label_start_y
            for line in label_lines:
                c.drawString(margin_x, current_y, line)
                current_y -= line_height

            # Box
            box_x = margin_x + label_col_width
            box_y = row_top - (row_height + box_height) / 2 + 2
            c.setStrokeColor(colors.black)
            c.rect(box_x, box_y, value_col_width, box_height, stroke=1, fill=0)

            # Value
            c.setFont(font_value, size_value)
            text_y = box_y + box_height - line_height
            for line in value_lines:
                if text_y < box_y + 2:
                    break
                c.drawString(box_x + 2, text_y, line)
                text_y -= line_height

            y = row_bottom - line_height * 0.2

        y -= line_height * 0.5

    finish_page(start_new=False)
    c.save()
    return buf.getvalue()
