"""
PDF Generation Service using ReportLab.
Produces a comprehensive, beautifully styled Gift Decision Report based on actual session data.
"""

import io
from typing import Dict, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether
)


def generate_gift_decision_pdf(session_data: Dict[str, Any]) -> io.BytesIO:
    """
    Generates a PDF decision report from session state and returns a BytesIO stream.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#4A148C")      # Deep Violet
    secondary_color = colors.HexColor("#7C4DFF")    # Lavender Accent
    accent_bg = colors.HexColor("#F3E5F5")          # Soft Lavender Tint
    text_dark = colors.HexColor("#212121")          # Charcoal
    gray_subtext = colors.HexColor("#555555")

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=primary_color,
        alignment=0,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=gray_subtext,
        spaceAfter=12
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=text_dark
    )

    bold_label = ParagraphStyle(
        "BoldLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13.5,
        textColor=text_dark
    )

    badge_style = ParagraphStyle(
        "BadgeText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.whitesmoke,
        alignment=1
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("Gift Decision Agent — Recommendation Report", title_style))
    session_id = session_data.get("session_id", "N/A")
    mode_text = "Gemini 2.5 Flash Enhanced" if session_data.get("mode") == "gemini" else "Deterministic Fallback Engine"
    story.append(Paragraph(f"Session ID: <b>{session_id}</b> &bull; Reasoning Mode: <b>{mode_text}</b> &bull; Curated for INR Market", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=secondary_color, spaceAfter=14))

    # 2. Discovery Parameters Table
    story.append(Paragraph("1. Discovery Profile & Constraints", section_heading))
    
    budget_range = f"₹{int(session_data.get('budget_min', 0)):,} – ₹{int(session_data.get('budget_max', 0)):,}"
    interests = ", ".join(session_data.get("interests", [])) or "None specified"
    preferences = ", ".join(session_data.get("preferences", [])) or "Standard"
    disliked = ", ".join(session_data.get("disliked_items", [])) or "None"
    owned = ", ".join(session_data.get("already_owned", [])) or "None"

    param_data = [
        [
            Paragraph("<b>Occasion:</b>", bold_label),
            Paragraph(str(session_data.get("occasion", "N/A")), body_style),
            Paragraph("<b>Target Budget:</b>", bold_label),
            Paragraph(budget_range, body_style)
        ],
        [
            Paragraph("<b>Recipient:</b>", bold_label),
            Paragraph(f"{session_data.get('recipient', 'N/A')} ({session_data.get('relationship', 'Close')})", body_style),
            Paragraph("<b>Gift Type:</b>", bold_label),
            Paragraph(str(session_data.get("gift_type", "No preference")), body_style)
        ],
        [
            Paragraph("<b>Interests:</b>", bold_label),
            Paragraph(interests, body_style),
            Paragraph("<b>Stated Purposes:</b>", bold_label),
            Paragraph(preferences, body_style)
        ],
        [
            Paragraph("<b>Exclusions:</b>", bold_label),
            Paragraph(disliked, body_style),
            Paragraph("<b>Already Owned:</b>", bold_label),
            Paragraph(owned, body_style)
        ]
    ]

    param_table = Table(param_data, colWidths=[90, 175, 90, 175])
    param_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9F9FB")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#EAEAEA")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(param_table)
    story.append(Spacer(1, 12))

    # 3. Top Recommendation Showcase
    selected = session_data.get("selected_gift")
    story.append(Paragraph("2. Top Recommendation Decision", section_heading))

    if selected:
        cost_min = int(selected.get("estimated_cost_min", 0))
        cost_max = int(selected.get("estimated_cost_max", cost_min))
        cost_display = f"₹{cost_min:,}" if cost_min == cost_max else f"₹{cost_min:,} – ₹{cost_max:,}"
        score = selected.get("total_score", 0.0)

        showcase_data = [
            [
                Paragraph(f"<b>Best Match:</b> {selected.get('gift_name')}", ParagraphStyle("TopName", parent=bold_label, fontSize=11, textColor=primary_color)),
                Paragraph(f"<b>Match Score:</b> {score} / 100", ParagraphStyle("TopScore", parent=bold_label, fontSize=11, textColor=secondary_color, alignment=2))
            ],
            [
                Paragraph(f"<b>Category:</b> {selected.get('gift_category')}", body_style),
                Paragraph(f"<b>Estimated Price:</b> {cost_display} ({selected.get('budget_fit_status', 'Within budget')})", body_style)
            ],
            [
                Paragraph(f"<b>Description:</b> {selected.get('description')}", body_style),
                Paragraph(f"<b>Confidence:</b> {selected.get('price_confidence_indicator', 'Standard estimate')}", body_style)
            ],
            [
                Paragraph(f"<b>Why It Matches:</b> {selected.get('why_it_matches')}", body_style),
                Paragraph(f"<b>Personalization:</b> {selected.get('personalization_possibilities', 'None noted')}", body_style)
            ]
        ]
        showcase_table = Table(showcase_data, colWidths=[265, 265])
        showcase_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), accent_bg),
            ("BOX", (0, 0), (-1, -1), 1, secondary_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1C4E9")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("SPAN", (0, 2), (1, 2)),
            ("SPAN", (0, 3), (1, 3)),
        ]))
        story.append(showcase_table)
    else:
        story.append(Paragraph("<i>No candidate survived filtering. Check constraints.</i>", body_style))

    story.append(Spacer(1, 10))

    # 4. Transparent Scoring Breakdown Table
    story.append(Paragraph("3. Deterministic Scoring Breakdown", section_heading))
    if selected and selected.get("score_breakdown"):
        sb = selected.get("score_breakdown", {})
        score_rows = [
            [
                Paragraph("<b>Scoring Dimension</b>", bold_label),
                Paragraph("<b>Weight</b>", bold_label),
                Paragraph("<b>Awarded Score</b>", bold_label),
                Paragraph("<b>Evaluation Rationale</b>", bold_label)
            ],
            [
                Paragraph("Interest Alignment", body_style),
                Paragraph("30%", body_style),
                Paragraph(f"{sb.get('interest_match_score', 0)} / 30", body_style),
                Paragraph("Overlap with recipient's stated hobbies and topics", body_style)
            ],
            [
                Paragraph("Budget Fitting", body_style),
                Paragraph("25%", body_style),
                Paragraph(f"{sb.get('budget_fit_score', 0)} / 25", body_style),
                Paragraph("Cost range positioned comfortably against budget target", body_style)
            ],
            [
                Paragraph("Occasion & Relationship Relevance", body_style),
                Paragraph("20%", body_style),
                Paragraph(f"{sb.get('relevance_score', 0)} / 20", body_style),
                Paragraph("Appropriateness for the celebration and intimacy level", body_style)
            ],
            [
                Paragraph("Stated Gift Purpose Match", body_style),
                Paragraph("15%", body_style),
                Paragraph(f"{sb.get('purpose_match_score', 0)} / 15", body_style),
                Paragraph("Balance of utility, sentimental resonance, and flair", body_style)
            ],
            [
                Paragraph("Personalization Potential", body_style),
                Paragraph("10%", body_style),
                Paragraph(f"{sb.get('personalization_score', 0)} / 10", body_style),
                Paragraph("Custom engraving, monogramming, or artisan dedication options", body_style)
            ],
            [
                Paragraph("<b>Normalized Total Score</b>", bold_label),
                Paragraph("<b>100%</b>", bold_label),
                Paragraph(f"<b>{selected.get('total_score', 0)} / 100</b>", bold_label),
                Paragraph("<b>Selected as Top Recommendation</b>", bold_label)
            ]
        ]
        score_table = Table(score_rows, colWidths=[150, 55, 95, 230])
        score_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDE7F6")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E1BEE7")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B388FF")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(score_table)

    story.append(Spacer(1, 12))

    # 5. Viable Alternatives Comparison Table
    alternatives = session_data.get("alternatives", [])
    if alternatives:
        story.append(Paragraph("4. Viable Alternatives Comparison", section_heading))
        alt_rows = [
            [
                Paragraph("<b>Alternative Gift</b>", bold_label),
                Paragraph("<b>Category</b>", bold_label),
                Paragraph("<b>Est. Cost (INR)</b>", bold_label),
                Paragraph("<b>Score</b>", bold_label),
                Paragraph("<b>Trade-off Comparison</b>", bold_label)
            ]
        ]
        for alt in alternatives[:3]:
            a_min = int(alt.get("estimated_cost_min", 0))
            a_max = int(alt.get("estimated_cost_max", a_min))
            a_display = f"₹{a_min:,}" if a_min == a_max else f"₹{a_min:,}–₹{a_max:,}"
            trade_text = alt.get("trade_offs", ["Alternative option"])[0] if alt.get("trade_offs") else "Alternative balance"

            alt_rows.append([
                Paragraph(alt.get("gift_name", "N/A"), body_style),
                Paragraph(alt.get("gift_category", "N/A"), body_style),
                Paragraph(a_display, body_style),
                Paragraph(f"{alt.get('total_score', 0)}", body_style),
                Paragraph(trade_text, body_style)
            ])

        alt_table = Table(alt_rows, colWidths=[140, 95, 95, 45, 155])
        alt_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDE7F6")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B388FF")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ]))
        story.append(alt_table)
        story.append(Spacer(1, 12))

    # 6. Feedback & Adaptation History (if any)
    feedback_hist = session_data.get("feedback_history", [])
    if feedback_hist:
        story.append(Paragraph("5. User Feedback & Adaptive Refinement History", section_heading))
        for idx, item in enumerate(feedback_hist, 1):
            f_reason = item.get("reason", "User Feedback")
            f_note = item.get("custom_feedback", "")
            f_text = f"<b>Iteration {idx}:</b> User indicated: <i>'{f_reason}'</i>. {f'Note: {f_note}' if f_note else ''}"
            story.append(Paragraph(f_text, body_style))
            story.append(Spacer(1, 3))
        story.append(Spacer(1, 8))

    # 7. Verification Disclaimer & Purchase Next Steps
    story.append(Paragraph("6. Retail Verification Notice & Next Steps", section_heading))
    disclaimer_text = (
        "<b>Important Retail Disclaimer:</b> All budget figures and availability indicators are market estimates "
        "derived from standard Indian e-commerce and artisan marketplace trends. Prices may fluctuate depending "
        "on retailer, seller discounts, and customization options. Always verify live pricing, return policies, and shipping "
        "delivery timelines prior to finalizing your purchase."
    )
    story.append(Paragraph(disclaimer_text, ParagraphStyle("Disc", parent=body_style, fontSize=8.5, leading=12, textColor=gray_subtext)))

    doc.build(story)
    buffer.seek(0)
    return buffer
