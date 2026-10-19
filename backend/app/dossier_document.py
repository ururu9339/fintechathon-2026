import json
from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .core.llm import get_openai_client

PROMPT_VERSION = "credit-passport-v1"


def generate_narrative(snapshot: dict) -> tuple[str, str, str]:
    client = get_openai_client()
    if client is None:
        return (
            "Narrative generation is pending because the language-model service is not configured. "
            "Review the calculated metrics, data gaps, and limitations before using this draft.",
            "needs_review",
            "unconfigured",
        )
    safe_snapshot = dict(snapshot)
    safe_snapshot["applicant"] = {
        key: value
        for key, value in snapshot["applicant"].items()
        if key not in {"ownership"}
    }
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.1,
        messages=[
            {
                "role": "system",
                "content": (
                    "Write a neutral professional credit dossier narrative from the supplied JSON. "
                    "Use only facts and numbers present in the JSON. Do not claim audit, approval, "
                    "certification, eligibility, guarantee, or lender outcome. Mention limitations and gaps."
                ),
            },
            {"role": "user", "content": json.dumps(safe_snapshot, sort_keys=True)},
        ],
    )
    text = response.choices[0].message.content
    if not text:
        return "Narrative generation returned no content.", "needs_review", "gpt-4o-mini"
    return text.strip(), "ok", "gpt-4o-mini"


def render_dossier_pdf(dossier) -> bytes:
    narrative, narrative_status, model = generate_narrative(dossier.snapshot)
    dossier.narrative_text = narrative
    dossier.narrative_status = narrative_status
    dossier.narrative_model = model
    dossier.narrative_prompt_version = PROMPT_VERSION
    dossier.pdf_generated_at = datetime.now(timezone.utc)

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Credit Passport",
        author="Qyze Ai",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleCenter", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#17324D")))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10, textColor=colors.HexColor("#555555")))
    story = [
        Paragraph("Credit Passport", styles["TitleCenter"]),
        Paragraph("Draft financial analysis generated from recorded business data", styles["Small"]),
        Spacer(1, 8 * mm),
    ]
    applicant = dossier.snapshot["applicant"]
    story.append(Paragraph(applicant["legal_name"], styles["Heading2"]))
    story.append(Paragraph(
        f"Registration: {applicant['registration_type']} | {applicant['registration_number']} | "
        f"Status: {applicant['registration_status']} | MSIC: {applicant['msic_code']}",
        styles["BodyText"],
    ))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Executive narrative", styles["Heading2"]))
    for paragraph in narrative.split("\n"):
        if paragraph.strip():
            story.append(Paragraph(paragraph, styles["BodyText"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Calculated metrics", styles["Heading2"]))
    metrics = dossier.snapshot["metrics"]
    table_data = [["Metric", "Value"]] + [[key.replace("_", " ").title(), str(value)] for key, value in metrics.items()]
    table = Table(table_data, colWidths=[105 * mm, 55 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C4CE")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F6F8")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.extend([table, Spacer(1, 5 * mm)])
    story.append(Paragraph("Ownership", styles["Heading2"]))
    ownership = applicant.get("ownership", [])
    ownership_data = [["Owner reference", "Share", "Malaysian citizen"]]
    ownership_data.extend([
        [item["owner_reference"], item["share_percentage"], str(item["is_malaysian_citizen"])]
        for item in ownership
    ] or [["None recorded", "-", "-"]])
    ownership_table = Table(ownership_data, colWidths=[80 * mm, 35 * mm, 45 * mm], repeatRows=1)
    ownership_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C4CE")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.extend([ownership_table, Spacer(1, 5 * mm)])
    story.append(Paragraph("Statutory remittances", styles["Heading2"]))
    statutory = dossier.snapshot.get("statutory_remittances", {})
    statutory_data = [["Type", "On time", "Late", "Missing"]]
    statutory_data.extend([
        [key, str(value["on_time"]), str(value["late"]), str(value["missing"])]
        for key, value in sorted(statutory.items())
    ] or [["No records", "-", "-", "-"]])
    statutory_table = Table(statutory_data, colWidths=[80 * mm, 27 * mm, 27 * mm, 27 * mm], repeatRows=1)
    statutory_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C4CE")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.extend([statutory_table, Spacer(1, 5 * mm)])
    story.append(Paragraph("Data gaps and limitations", styles["Heading2"]))
    for item in dossier.snapshot["data_gaps"] + dossier.snapshot["limitations"]:
        story.append(Paragraph(f"• {item}", styles["BodyText"]))
    story.append(PageBreak())
    story.append(Paragraph("Traceability appendix", styles["Heading2"]))
    trace = dossier.snapshot["traceability"]
    trace_data = [["Source", "Record IDs"]] + [[key.replace("_", " ").title(), ", ".join(value) if isinstance(value, list) else str(value or "None")] for key, value in trace.items()]
    trace_table = Table(trace_data, colWidths=[60 * mm, 100 * mm], repeatRows=1)
    trace_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C4CE")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.extend([trace_table, Spacer(1, 5 * mm), Paragraph(f"Input snapshot SHA-256: {dossier.input_hash}", styles["Small"])])
    story.extend([
        Spacer(1, 8 * mm),
        Paragraph("Owner review and declaration", styles["Heading2"]),
        Paragraph(
            "Owner review: ____________________    Date: ____________________<br/>"
            "This document is a draft analysis of recorded data. It is not an audit, certification, "
            "approval, guarantee, or lender decision.",
            styles["BodyText"],
        ),
    ])
    document.build(story)
    return buffer.getvalue()
