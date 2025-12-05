from __future__ import annotations
from io import BytesIO
from typing import Any, Dict

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def build_pdf_bytes(title: str, fields: Dict[str, Any]) -> bytes:
    """Generate a simple (dummy) PDF report.

    This is intentionally minimal: title + key/value fields in a list.
    Designed for low-volume automation (a few emails/day).
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    y = height - 60
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, title)
    y -= 24

    c.setFont("Helvetica", 11)
    for k, v in fields.items():
        line = f"{k}: {v}"
        # lightweight wrap
        while len(line) > 95:
            c.drawString(50, y, line[:95])
            line = line[95:]
            y -= 14
            if y < 60:
                c.showPage()
                y = height - 60
                c.setFont("Helvetica", 11)

        c.drawString(50, y, line)
        y -= 14
        if y < 60:
            c.showPage()
            y = height - 60
            c.setFont("Helvetica", 11)

    c.showPage()
    c.save()
    return buf.getvalue()
