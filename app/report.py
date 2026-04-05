import io
from datetime import datetime

from flask import Blueprint, abort, send_file
from flask_login import current_user, login_required
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .db import get_db
from .top_performer_table import fetch_top_performers

bp = Blueprint("report", __name__, url_prefix="/report")

# ── Colour palette (matches the portal's navy/blue theme) ──────────────────
NAVY = colors.HexColor("#1a1a2e")
BLUE = colors.HexColor("#2563eb")
LGREY = colors.HexColor("#f1f5f9")
MGREY = colors.HexColor("#e2e8f0")
DGREY = colors.HexColor("#475569")
GREEN = colors.HexColor("#16a34a")
RED = colors.HexColor("#dc2626")
WHITE = colors.white
BLACK = colors.black


def _build_styles():
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "ReportTitle",
            fontSize=22,
            fontName="Helvetica-Bold",
            textColor=WHITE,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            fontSize=10,
            fontName="Helvetica",
            textColor=colors.HexColor("#c7d2fe"),
            alignment=TA_CENTER,
        ),
        "section": ParagraphStyle(
            "SectionHeading",
            fontSize=13,
            fontName="Helvetica-Bold",
            textColor=NAVY,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            fontSize=9,
            fontName="Helvetica",
            textColor=BLACK,
            spaceAfter=4,
            leading=13,
        ),
        "label": ParagraphStyle(
            "Label",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=DGREY,
        ),
        "value": ParagraphStyle(
            "Value",
            fontSize=9,
            fontName="Helvetica",
            textColor=BLACK,
        ),
        "footer": ParagraphStyle(
            "Footer",
            fontSize=7,
            fontName="Helvetica",
            textColor=DGREY,
            alignment=TA_CENTER,
        ),
        "th": ParagraphStyle(
            "TableHeader",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=WHITE,
            alignment=TA_CENTER,
        ),
        "td": ParagraphStyle(
            "TableCell",
            fontSize=8,
            fontName="Helvetica",
            textColor=BLACK,
            alignment=TA_CENTER,
        ),
        "td_left": ParagraphStyle(
            "TableCellLeft",
            fontSize=8,
            fontName="Helvetica",
            textColor=BLACK,
            alignment=TA_LEFT,
        ),
    }
    return styles


def _fmt(value, decimals=3):
    if value is None:
        return "—"
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return str(value)


def _dash(value):
    return "—" if value is None else str(value)


# ── Main PDF builder ────────────────────────────────────────────────────────


def generate_experiment_pdf(experiment_id: int, user_id: int) -> io.BytesIO:
    db = get_db()

    # ── Fetch experiment ────────────────────────────────────────────────────
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT experiment_id, experiment_name, uniprot_id,
                   wt_protein_sequence, created_at, saved_at, user_id
            FROM experiments
            WHERE experiment_id = %s
            """,
            (experiment_id,),
        )
        exp = cur.fetchone()

    if exp is None or exp["user_id"] != user_id:
        abort(403)

    # ── Fetch variant summary ───────────────────────────────────────────────
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*)                                            AS total,
                COUNT(*) FILTER (WHERE step1_status = 'ok')        AS ok_count,
                COUNT(*) FILTER (WHERE step1_status = 'error')     AS err_count,
                COUNT(*) FILTER (WHERE activity_score IS NOT NULL) AS scored,
                MAX(generation)                                     AS max_gen,
                AVG(activity_score)                                 AS avg_score,
                MAX(activity_score)                                 AS max_score,
                MIN(activity_score)
                    FILTER (WHERE activity_score IS NOT NULL)       AS min_score
            FROM variants
            WHERE experiment_id = %s
            """,
            (experiment_id,),
        )
        stats = cur.fetchone()

    # ── Fetch top performers ────────────────────────────────────────────────
    top_rows = fetch_top_performers(db, experiment_id, limit=10)

    # ── Fetch per-generation summary ────────────────────────────────────────
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                generation,
                COUNT(*)                                        AS variants,
                AVG(activity_score)                             AS avg_score,
                MAX(activity_score)                             AS max_score,
                COUNT(*) FILTER (WHERE activity_score IS NOT NULL) AS scored
            FROM variants
            WHERE experiment_id = %s
            GROUP BY generation
            ORDER BY generation
            """,
            (experiment_id,),
        )
        gen_rows = cur.fetchall()

    # ── Build PDF in memory ─────────────────────────────────────────────────
    buf = io.BytesIO()
    PAGE_W, PAGE_H = A4
    MARGIN = 18 * mm

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=f"Experiment Report – {exp['experiment_name']}",
        author="Directed Evolution Portal",
    )

    S = _build_styles()
    story = []

    # ── Header banner ───────────────────────────────────────────────────────
    header_data = [
        [
            Paragraph("🧬  Directed Evolution Portal", S["title"]),
        ]
    ]
    sub_data = [
        [
            Paragraph("Experiment Report", S["subtitle"]),
        ]
    ]

    header_table = Table(header_data, colWidths=[PAGE_W - 2 * MARGIN])
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("ROUNDEDCORNERS", [6]),
            ]
        )
    )
    story.append(header_table)

    sub_table = Table(sub_data, colWidths=[PAGE_W - 2 * MARGIN])
    sub_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    story.append(sub_table)
    story.append(Spacer(1, 10))

    # ── Experiment metadata grid ────────────────────────────────────────────
    story.append(Paragraph("Experiment Overview", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=MGREY, spaceAfter=8))

    saved_str = (
        exp["saved_at"].strftime("%d %b %Y, %H:%M") if exp["saved_at"] else "Not saved"
    )
    created_str = (
        exp["created_at"].strftime("%d %b %Y, %H:%M") if exp["created_at"] else "—"
    )
    wt_seq = exp["wt_protein_sequence"] or ""
    wt_display = (wt_seq[:80] + "…") if len(wt_seq) > 80 else wt_seq

    meta_data = [
        [
            Paragraph("Experiment Name", S["label"]),
            Paragraph(exp["experiment_name"], S["value"]),
            Paragraph("Experiment ID", S["label"]),
            Paragraph(str(exp["experiment_id"]), S["value"]),
        ],
        [
            Paragraph("UniProt ID", S["label"]),
            Paragraph(exp["uniprot_id"], S["value"]),
            Paragraph("Created", S["label"]),
            Paragraph(created_str, S["value"]),
        ],
        [
            Paragraph("Saved", S["label"]),
            Paragraph(saved_str, S["value"]),
            Paragraph("Report Date", S["label"]),
            Paragraph(datetime.now().strftime("%d %b %Y, %H:%M"), S["value"]),
        ],
        [
            Paragraph("WT Protein (preview)", S["label"]),
            Paragraph(f'<font name="Courier" size="7">{wt_display}</font>', S["value"]),
            Paragraph("", S["label"]),
            Paragraph("", S["value"]),
        ],
    ]

    col_w = (PAGE_W - 2 * MARGIN) / 4
    meta_table = Table(
        meta_data, colWidths=[col_w * 0.85, col_w * 1.15, col_w * 0.85, col_w * 1.15]
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LGREY),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LGREY]),
                ("GRID", (0, 0), (-1, -1), 0.5, MGREY),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                # Wide cell for WT sequence spans cols 1-3
                ("SPAN", (1, 3), (3, 3)),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # ── Summary statistics ──────────────────────────────────────────────────
    story.append(Paragraph("Analysis Summary", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=MGREY, spaceAfter=8))

    stat_items = [
        ("Total Variants", _dash(stats["total"])),
        ("ORF OK", _dash(stats["ok_count"])),
        ("ORF Errors", _dash(stats["err_count"])),
        ("Activity Scored", _dash(stats["scored"])),
        ("Generations", _dash(stats["max_gen"])),
        ("Avg Activity Score", _fmt(stats["avg_score"], 4)),
        ("Max Activity Score", _fmt(stats["max_score"], 4)),
        ("Min Activity Score", _fmt(stats["min_score"], 4)),
    ]

    # 4-column stat boxes
    box_w = (PAGE_W - 2 * MARGIN) / 4
    stat_rows = [stat_items[i : i + 4] for i in range(0, len(stat_items), 4)]
    for row in stat_rows:
        row_data = [
            [
                [
                    Paragraph(label, S["label"]),
                    Paragraph(
                        value,
                        ParagraphStyle(
                            "StatVal",
                            fontSize=14,
                            fontName="Helvetica-Bold",
                            textColor=BLUE,
                            alignment=TA_CENTER,
                        ),
                    ),
                ]
                for label, value in row
            ]
        ]
        stat_table = Table(row_data, colWidths=[box_w] * 4)
        stat_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), LGREY),
                    ("BOX", (0, 0), (-1, -1), 0.5, MGREY),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, MGREY),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(stat_table)
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 8))

    # ── Per-generation table ────────────────────────────────────────────────
    if gen_rows:
        story.append(Paragraph("Results by Generation", S["section"]))
        story.append(HRFlowable(width="100%", thickness=1, color=MGREY, spaceAfter=8))

        gen_header = [
            Paragraph("Generation", S["th"]),
            Paragraph("Variants", S["th"]),
            Paragraph("Scored", S["th"]),
            Paragraph("Avg Activity", S["th"]),
            Paragraph("Max Activity", S["th"]),
        ]
        gen_table_data = [gen_header]
        for i, g in enumerate(gen_rows):
            bg = LGREY if i % 2 == 0 else WHITE
            gen_table_data.append(
                [
                    Paragraph(_dash(g["generation"]), S["td"]),
                    Paragraph(_dash(g["variants"]), S["td"]),
                    Paragraph(_dash(g["scored"]), S["td"]),
                    Paragraph(_fmt(g["avg_score"], 4), S["td"]),
                    Paragraph(_fmt(g["max_score"], 4), S["td"]),
                ]
            )

        col_w_gen = (PAGE_W - 2 * MARGIN) / 5
        gen_table = Table(gen_table_data, colWidths=[col_w_gen] * 5, repeatRows=1)
        gen_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LGREY, WHITE]),
                    ("GRID", (0, 0), (-1, -1), 0.5, MGREY),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(gen_table)
        story.append(Spacer(1, 12))

    # ── Top performers table ────────────────────────────────────────────────
    story.append(Paragraph("Top 10 Performing Variants", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=MGREY, spaceAfter=8))

    if top_rows:
        tp_header = [
            Paragraph("Rank", S["th"]),
            Paragraph("Variant ID", S["th"]),
            Paragraph("Generation", S["th"]),
            Paragraph("Index", S["th"]),
            Paragraph("DNA Yield", S["th"]),
            Paragraph("Protein Yield", S["th"]),
            Paragraph("Activity Score", S["th"]),
            Paragraph("Mutations", S["th"]),
        ]
        tp_data = [tp_header]
        for rank, row in enumerate(top_rows, 1):
            score = row.get("activity_score")
            score_str = _fmt(score, 4)
            tp_data.append(
                [
                    Paragraph(str(rank), S["td"]),
                    Paragraph(_dash(row["variant_id"]), S["td"]),
                    Paragraph(_dash(row["generation"]), S["td"]),
                    Paragraph(_dash(row["plasmid_variant_index"]), S["td"]),
                    Paragraph(_fmt(row.get("dna_yield")), S["td"]),
                    Paragraph(_fmt(row.get("protein_yield")), S["td"]),
                    Paragraph(score_str, S["td"]),
                    Paragraph(_dash(row.get("mutation_total")), S["td"]),
                ]
            )

        avail_w = PAGE_W - 2 * MARGIN
        tp_col_widths = [
            avail_w * 0.07,  # rank
            avail_w * 0.12,  # variant id
            avail_w * 0.11,  # generation
            avail_w * 0.09,  # index
            avail_w * 0.13,  # dna yield
            avail_w * 0.14,  # protein yield
            avail_w * 0.17,  # activity score
            avail_w * 0.17,  # mutations
        ]

        tp_table = Table(tp_data, colWidths=tp_col_widths, repeatRows=1)
        tp_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LGREY, WHITE]),
                    # Highlight rank 1
                    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#dcfce7")),
                    ("TEXTCOLOR", (6, 1), (6, 1), GREEN),
                    ("FONTNAME", (6, 1), (6, 1), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, MGREY),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(tp_table)
    else:
        story.append(
            Paragraph(
                "No scored variants found for this experiment. Run the analysis pipeline first.",
                S["body"],
            )
        )

    story.append(Spacer(1, 20))

    # ── Footer ──────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=MGREY, spaceAfter=6))
    story.append(
        Paragraph(
            f"Generated by the Directed Evolution Portal  ·  {datetime.now().strftime('%d %b %Y, %H:%M')}  ·  Experiment ID {experiment_id}",
            S["footer"],
        )
    )

    doc.build(story)
    buf.seek(0)
    return buf


# ── Flask route ─────────────────────────────────────────────────────────────


@bp.route("/experiment/<int:experiment_id>")
@login_required
def download_report(experiment_id: int):
    buf = generate_experiment_pdf(experiment_id, current_user.id)
    filename = f"experiment_{experiment_id}_report.pdf"
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )
