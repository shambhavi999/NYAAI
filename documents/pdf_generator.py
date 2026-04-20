from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, Frame, PageTemplate
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import date
import os

# ── Colour Palette (Law Firm) ─────────────────────────────────────────────────
NAVY      = colors.HexColor('#0a1628')   # deep navy — headings, borders
STEEL     = colors.HexColor('#1e3a5f')   # steel blue — section bars
GOLD      = colors.HexColor('#b8960c')   # gold accent — rule lines
MID_GREY  = colors.HexColor('#4a5568')   # body text support
LIGHT_BG  = colors.HexColor('#f7f8fc')   # section background tint
RED_WARN  = colors.HexColor('#7b1c1c')   # warning text
RED_BG    = colors.HexColor('#fff5f5')   # warning box background
WHITE     = colors.white
BLACK     = colors.black


# ── Page border drawn on every page ──────────────────────────────────────────
def draw_page_border(canvas_obj, doc):
    canvas_obj.saveState()
    w, h = A4

    # Outer navy border
    canvas_obj.setStrokeColor(NAVY)
    canvas_obj.setLineWidth(2)
    canvas_obj.rect(1.2*cm, 1.2*cm, w - 2.4*cm, h - 2.4*cm)

    # Inner gold hairline
    canvas_obj.setStrokeColor(GOLD)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.rect(1.5*cm, 1.5*cm, w - 3.0*cm, h - 3.0*cm)

    # Page number at bottom centre
    canvas_obj.setFont('Helvetica', 7)
    canvas_obj.setFillColor(MID_GREY)
    canvas_obj.drawCentredString(w / 2, 1.0*cm, f"Page {doc.page}")

    canvas_obj.restoreState()


# ── Main generator ────────────────────────────────────────────────────────────
def generate_legal_notice(case, user_profile):
    """
    Generate a professional law-firm style legal notice PDF.
    Returns a BytesIO buffer.

    Correctly reads from Case model fields:
        case.laws_violated      → list of dicts  {act, section, description}
        case.ai_summary         → string
        case.forum_type         → string
        case.documents_needed   → list of strings
        case.description        → string
        case.title              → string
        case.category           → string
        case.status             → string
    """
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2.8*cm,
        leftMargin=2.8*cm,
        topMargin=3.2*cm,
        bottomMargin=2.8*cm,
    )

    # ── Styles ────────────────────────────────────────────────────────────────
    S = getSampleStyleSheet()

    def style(name, parent='Normal', **kw):
        return ParagraphStyle(name, parent=S[parent], **kw)

    firm_name_style = ParagraphStyle(
    'FirmName',
    parent=S['Normal'],
    fontSize=20, fontName='Helvetica-Bold',
    alignment=TA_CENTER, textColor=NAVY,
    spaceAfter=8, spaceBefore=0)

    firm_tag_style = ParagraphStyle(
    'FirmTag',
    parent=S['Normal'],
    fontSize=8, fontName='Helvetica',
    alignment=TA_CENTER, textColor=GOLD,
    spaceAfter=10, letterSpacing=1.5)

    notice_title_style = style('NoticeTitle',
        fontSize=13, fontName='Helvetica-Bold',
        alignment=TA_CENTER, textColor=WHITE,
        spaceAfter=0, spaceBefore=0)

    ref_style = style('Ref',
        fontSize=9, fontName='Helvetica',
        alignment=TA_LEFT, textColor=MID_GREY, spaceAfter=2)

    ref_right_style = style('RefR',
        fontSize=9, fontName='Helvetica',
        alignment=TA_RIGHT, textColor=MID_GREY, spaceAfter=2)

    section_label_style = style('SectionLabel',
        fontSize=8, fontName='Helvetica-Bold',
        alignment=TA_LEFT, textColor=WHITE,
        spaceAfter=0, spaceBefore=0)

    body_style = style('Body',
        fontSize=10, fontName='Helvetica',
        leading=17, alignment=TA_JUSTIFY,
        textColor=BLACK, spaceAfter=8)

    body_bold_style = style('BodyBold',
        fontSize=10, fontName='Helvetica-Bold',
        leading=17, alignment=TA_JUSTIFY,
        textColor=NAVY, spaceAfter=6)

    bullet_style = style('Bullet',
        fontSize=10, fontName='Helvetica',
        leading=16, alignment=TA_LEFT,
        textColor=BLACK, spaceAfter=5,
        leftIndent=14)

    law_title_style = style('LawTitle',
        fontSize=10, fontName='Helvetica-Bold',
        leading=14, textColor=NAVY, spaceAfter=2)

    law_desc_style = style('LawDesc',
        fontSize=9.5, fontName='Helvetica',
        leading=15, textColor=MID_GREY, spaceAfter=8,
        leftIndent=12)

    footer_style = style('Footer',
        fontSize=7.5, fontName='Helvetica',
        alignment=TA_CENTER, textColor=MID_GREY, spaceAfter=3)

    warning_style = style('Warning',
        fontSize=9.5, fontName='Helvetica-Bold',
        leading=15, textColor=RED_WARN,
        alignment=TA_JUSTIFY)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def gold_rule():
        return HRFlowable(width='100%', thickness=1,
                          color=GOLD, spaceAfter=10, spaceBefore=4)

    def thin_rule():
        return HRFlowable(width='100%', thickness=0.4,
                          color=colors.HexColor('#d0d7e3'),
                          spaceAfter=8, spaceBefore=4)

    def section_bar(title):
        """Navy bar with white text — used for every major section heading."""
        data = [[Paragraph(title, section_label_style)]]
        t = Table(data, colWidths=[doc.width])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), STEEL),
            ('TOPPADDING',    (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING',   (0,0), (-1,-1), 8),
            ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ]))
        return t

    def info_table(rows):
        """Two-column key-value table for party details."""
        t = Table(rows, colWidths=[3.5*cm, doc.width - 3.5*cm])
        t.setStyle(TableStyle([
            ('FONTNAME',      (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME',      (1,0), (1,-1), 'Helvetica'),
            ('FONTSIZE',      (0,0), (-1,-1), 9.5),
            ('TEXTCOLOR',     (0,0), (0,-1), NAVY),
            ('TEXTCOLOR',     (1,0), (1,-1), BLACK),
            ('TOPPADDING',    (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING',   (0,0), (-1,-1), 0),
            ('RIGHTPADDING',  (0,0), (-1,-1), 0),
            ('VALIGN',        (0,0), (-1,-1), 'TOP'),
            ('LINEBELOW',     (0,-1), (-1,-1), 0.3,
             colors.HexColor('#d0d7e3')),
        ]))
        return t

    # ── Data from model ───────────────────────────────────────────────────────
    today        = date.today().strftime("%d %B %Y")
    case_no      = f"NYAAI/{case.id:05d}/{date.today().year}"

    sender_name  = (
        f"{user_profile.user.first_name} {user_profile.user.last_name}".strip()
        or user_profile.user.username
    )
    sender_email  = user_profile.user.email or "Not provided"
    sender_phone  = str(getattr(user_profile, 'phone', '') or 'Not provided')
    sender_state  = str(getattr(user_profile, 'state', '')         or 'India')

    case_title    = case.title
    case_desc     = case.description
    case_category = case.get_category_display() if hasattr(case, 'get_category_display') else str(getattr(case, 'category', 'General'))

    # ── CORRECT field names matching cases/views.py ───────────────────────────
    laws_violated     = getattr(case, 'laws_violated', [])     or []
    ai_summary        = getattr(case, 'ai_summary', '')        or ''
    forum_type        = getattr(case, 'forum_type', '')        or 'Appropriate civil court'
    documents_needed  = getattr(case, 'documents_needed', [])  or []

    respondent_name   = getattr(case, 'respondent_name', '')   or 'The Concerned Party / Opposite Party'
    respondent_addr   = getattr(case, 'respondent_address', '') or 'Address as per official records'

    # ── Build Story ───────────────────────────────────────────────────────────
    story = []

    # ═══════════════════════════════════════════════════════
    # HEADER — Firm name + gold rules
    # ═══════════════════════════════════════════════════════
    story.append(Spacer(1, 6))
    story.append(Paragraph("NYAAI LEGAL SERVICES", firm_name_style))
    story.append(Paragraph("AI-POWERED LEGAL NOTICE PLATFORM  ·  INDIA", firm_tag_style))
    story.append(Spacer(1, 6))
    story.append(gold_rule())

    # Title bar
    title_data = [[Paragraph("LEGAL NOTICE", notice_title_style)]]
    title_table = Table(title_data, colWidths=[doc.width])
    title_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), NAVY),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING',   (0,0), (-1,-1), 0),
        ('RIGHTPADDING',  (0,0), (-1,-1), 0),
    ]))
    story.append(title_table)
    story.append(gold_rule())

    # Ref + Date row
    ref_row = [[
        Paragraph(f"<b>Ref:</b> {case_no}", ref_style),
        Paragraph(f"<b>Date:</b> {today}", ref_right_style),
    ]]
    ref_table = Table(ref_row, colWidths=['55%', '45%'])
    ref_table.setStyle(TableStyle([
        ('LEFTPADDING',  (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING',   (0,0), (-1,-1), 0),
        ('BOTTOMPADDING',(0,0), (-1,-1), 0),
        ('VALIGN',       (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(ref_table)
    story.append(Spacer(1, 10))

    # ═══════════════════════════════════════════════════════
    # PARTIES
    # ═══════════════════════════════════════════════════════
    story.append(section_bar("FROM  (COMPLAINANT / NOTICEE)"))
    story.append(Spacer(1, 6))
    story.append(info_table([
        ["Name:",     sender_name],
        ["Email:",    sender_email],
        ["Phone:",    sender_phone],
        ["State:",    sender_state],
        ["Platform:", "NYAAI — AI Legal Justice Platform, India"],
    ]))
    story.append(Spacer(1, 10))

    story.append(section_bar("TO  (RESPONDENT / OPPOSITE PARTY)"))
    story.append(Spacer(1, 6))
    story.append(info_table([
        ["Name:",    respondent_name],
        ["Address:", respondent_addr],
    ]))
    story.append(Spacer(1, 10))

    # ═══════════════════════════════════════════════════════
    # SUBJECT
    # ═══════════════════════════════════════════════════════
    story.append(section_bar("SUBJECT"))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Legal Notice in the matter of: <b>{case_title}</b>",
        body_bold_style
    ))
    story.append(Paragraph(
        f"Category of Grievance: {case_category}  |  "
        f"Forum: {forum_type}",
        ref_style
    ))
    story.append(Spacer(1, 10))

    # ═══════════════════════════════════════════════════════
    # BODY OF NOTICE
    # ═══════════════════════════════════════════════════════
    story.append(section_bar("NOTICE"))
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        f"I, <b>{sender_name}</b>, am addressing this legal notice to you in "
        f"connection with the grievance described herein. This notice is issued "
        f"under the applicable statutes of India and seeks immediate redressal.",
        body_style
    ))

    story.append(Paragraph("Statement of Facts:", body_bold_style))
    story.append(Paragraph(case_desc, body_style))
    story.append(Spacer(1, 6))

    # ═══════════════════════════════════════════════════════
    # AI SUMMARY (if available)
    # ═══════════════════════════════════════════════════════
    if ai_summary:
        story.append(section_bar("LEGAL ANALYSIS  (AI-ASSISTED)"))
        story.append(Spacer(1, 6))

        # Tinted background box for AI summary
        summary_data = [[Paragraph(ai_summary, body_style)]]
        summary_table = Table(summary_data, colWidths=[doc.width])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), LIGHT_BG),
            ('TOPPADDING',    (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING',   (0,0), (-1,-1), 12),
            ('RIGHTPADDING',  (0,0), (-1,-1), 12),
            ('BOX',           (0,0), (-1,-1), 0.5,
             colors.HexColor('#c8d3e8')),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 10))

    # ═══════════════════════════════════════════════════════
    # APPLICABLE LAWS — uses case.laws_violated (list of dicts)
    # ═══════════════════════════════════════════════════════
    story.append(section_bar("APPLICABLE LAWS & PROVISIONS"))
    story.append(Spacer(1, 6))

    if laws_violated:
        for i, law in enumerate(laws_violated, 1):
            act     = law.get('act', 'Unknown Act')
            section = law.get('section', '')
            desc    = law.get('description', '')

            section_text = f" — Section {section}" if section else ""
            story.append(KeepTogether([
                Paragraph(
                    f"{i}.  {act}{section_text}",
                    law_title_style
                ),
                Paragraph(desc, law_desc_style) if desc else Spacer(1, 4),
            ]))
    else:
        story.append(Paragraph(
            "Applicable laws will be determined upon full legal review. "
            "Please ensure the case has been analysed by the AI engine first.",
            body_style
        ))

    story.append(Spacer(1, 6))

    # ═══════════════════════════════════════════════════════
    # DOCUMENTS NEEDED
    # ═══════════════════════════════════════════════════════
    if documents_needed:
        story.append(section_bar("DOCUMENTS TO BE SUBMITTED"))
        story.append(Spacer(1, 6))
        for doc_item in documents_needed:
            story.append(Paragraph(f"▸  {doc_item}", bullet_style))
        story.append(Spacer(1, 8))

    # ═══════════════════════════════════════════════════════
    # RELIEF SOUGHT
    # ═══════════════════════════════════════════════════════
    story.append(section_bar("RELIEF SOUGHT"))
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "In light of the facts stated above and the applicable provisions of law, "
        "I hereby call upon you to:",
        body_style
    ))

    reliefs = [
        "Immediately cease and desist from the wrongful act(s) described in this notice;",
        "Remedy the situation and provide appropriate compensation within "
        "<b>15 (fifteen) days</b> of receipt of this notice;",
        "Acknowledge receipt of this notice in writing within the said period.",
    ]
    for idx, r in enumerate(reliefs, 1):
        story.append(Paragraph(f"{idx}.  {r}", bullet_style))

    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Failure to comply shall compel me to initiate appropriate legal proceedings "
        f"before the <b>{forum_type}</b> or such other competent authority, "
        "entirely at your risk, cost and consequences.",
        body_style
    ))
    story.append(Spacer(1, 10))

    # ═══════════════════════════════════════════════════════
    # WARNING BOX
    # ═══════════════════════════════════════════════════════
    warning_data = [[
        Paragraph(
            "⚠  PLEASE TAKE NOTICE: If no satisfactory response or remedy is received "
            "within 15 (fifteen) days from the date of this notice, appropriate legal "
            "proceedings shall be initiated before the competent forum without any "
            "further notice, at your risk and expense.",
            warning_style
        )
    ]]
    warning_table = Table(warning_data, colWidths=[doc.width])
    warning_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), RED_BG),
        ('BOX',           (0,0), (-1,-1), 1, RED_WARN),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING',   (0,0), (-1,-1), 12),
        ('RIGHTPADDING',  (0,0), (-1,-1), 12),
    ]))
    story.append(warning_table)
    story.append(Spacer(1, 18))

    # ═══════════════════════════════════════════════════════
    # SIGNATURE BLOCK
    # ═══════════════════════════════════════════════════════
    story.append(gold_rule())

    sig_data = [
        [
            Paragraph("Yours faithfully,", body_style),
            Paragraph("Issued via NYAAI Platform", ref_right_style),
        ],
        [
            Paragraph(f"<b>{sender_name}</b>", body_bold_style),
            Paragraph(f"Date: {today}", ref_right_style),
        ],
        [
            Paragraph(sender_email, ref_style),
            Paragraph("www.nyaai.in", ref_right_style),
        ],
    ]
    sig_table = Table(sig_data, colWidths=['58%', '42%'])
    sig_table.setStyle(TableStyle([
        ('LEFTPADDING',  (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING',   (0,0), (-1,-1), 3),
        ('BOTTOMPADDING',(0,0), (-1,-1), 3),
        ('VALIGN',       (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(sig_table)

    # ═══════════════════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════════════════
    story.append(Spacer(1, 16))
    story.append(thin_rule())
    story.append(Paragraph(
        "This notice has been generated by NYAAI — AI Legal Justice Platform. "
        "It is intended as a formal legal notice and not as legal advice. "
        "For complex litigation, consultation with a licensed advocate is recommended.",
        footer_style
    ))
    story.append(Paragraph(
        f"Case Ref: {case_no}  |  Generated: {today}  |  NYAAI, India",
        footer_style
    ))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(
        story,
        onFirstPage=draw_page_border,
        onLaterPages=draw_page_border,
    )
    buffer.seek(0)
    return buffer