import os

from app.payload import load_event, parse_submission
from app.pdf_report import build_pdf_bytes, build_pdf_bytes_dynamic
from app.mailer import send_mail


def main():
    # Load GitHub repository_dispatch event
    event = load_event()
    submission = parse_submission(event)

    # Mail content
    subject = os.environ.get(
        "MAIL_SUBJECT",
        f"{submission.form_title} – Complaint {submission.complaint_id}",
    )
    body = os.environ.get(
        "MAIL_BODY",
        "Please find attached the generated complaint PDF.",
    )

    filename = os.environ.get("PDF_FILENAME", "complaint.pdf")

    title = f"{submission.form_title} – Complaint Report"

    # ---- PDF generation ----
    if submission.sections:
        # Fully dynamic, form-driven PDF
        pdf_bytes = build_pdf_bytes_dynamic(
            title=title,
            complaint_id=submission.complaint_id,
            timestamp=submission.timestamp,
            status=submission.status,
            contact_consent=submission.contact_consent,
            sections=submission.sections,
        )
    else:
        # Fallback legacy mode (should rarely happen)
        pdf_bytes = build_pdf_bytes(
            title=title,
            fields={
                "complaint_id": submission.complaint_id,
                "timestamp": submission.timestamp,
                **submission.fields,
            },
        )

    # ---- Send email ----
    send_mail(
        to=submission.email_to,
        subject=subject,
        body=body,
        attachment_bytes=pdf_bytes,
        attachment_name=filename,
    )


if __name__ == "__main__":
    main()
