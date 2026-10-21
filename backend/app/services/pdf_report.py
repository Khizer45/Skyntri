from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import settings
from app.db.models import ProgressCheck, SkinAnalysis, User
from app.services.skin_analysis import build_recommendations


BRAND_TEAL = colors.HexColor("#0f7c74")
LIGHT_TEAL = colors.HexColor("#effcfa")
MUTED = colors.HexColor("#6b7280")
DARK = colors.HexColor("#111827")
BORDER = colors.HexColor("#e5e7eb")


# ============================================================
# Helpers
# ============================================================

def _safe_text(value: object) -> str:
    """
    Escape text before putting it into a ReportLab Paragraph.
    """

    if value is None:
        return ""

    return escape(
        str(value)
    )


def _condition_list(
    predicted_condition: str,
) -> list[str]:
    """
    Convert the database comma-separated condition string
    into individual conditions.

    Example:
        "Pigmentation, Acne, Visible Pores"

    becomes:
        ["Pigmentation", "Acne", "Visible Pores"]
    """

    if not predicted_condition:
        return []

    return [
        condition.strip()
        for condition in predicted_condition.split(",")
        if condition.strip()
    ]


def _load_observations(
    observations_json: str | None,
) -> list[str]:
    """
    Safely decode progress observations stored as JSON.
    """

    if not observations_json:
        return []

    try:
        data = json.loads(
            observations_json
        )
    except (
        json.JSONDecodeError,
        TypeError,
    ):
        return []

    # Current progress service stores a list of strings.
    if isinstance(data, list):
        return [
            str(item)
            for item in data
            if str(item).strip()
        ]

    # Backward compatibility if an older version stored
    # a dictionary.
    if isinstance(data, dict):
        observations: list[str] = []

        for key, value in data.items():
            if value is None:
                continue

            observations.append(
                f"{key}: {value}"
            )

        return observations

    return []


def _add_bullet_section(
    story: list,
    heading: str,
    items: list[str],
    heading_style: ParagraphStyle,
    body_style: ParagraphStyle,
) -> None:
    """
    Add a heading and bullet list to the PDF.
    """

    if not items:
        return

    story.append(
        Paragraph(
            _safe_text(heading),
            heading_style,
        )
    )

    for item in items:
        story.append(
            Paragraph(
                f"• {_safe_text(item)}",
                body_style,
            )
        )

        story.append(
            Spacer(
                1,
                3,
            )
        )


def _make_table(
    rows: list[list[str]],
    col_widths: list[float],
) -> Table:
    """
    Create a consistent Skyntri information table.
    """

    table = Table(
        rows,
        colWidths=col_widths,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    LIGHT_TEAL,
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (0, -1),
                    BRAND_TEAL,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (0, -1),
                    "Helvetica-Bold",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    BORDER,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
            ]
        )
    )

    return table


# ============================================================
# PDF generation
# ============================================================

def generate_report_pdf(
    user: User,
    report_id: str,
    title: str,
    analysis: SkinAnalysis | None,
    progress: ProgressCheck | None,
) -> str:
    """
    Generate a professionally formatted Skyntri PDF report.

    Includes:

    - User information
    - Skin analysis
    - Detected conditions
    - AI confidence
    - Estimated severity
    - Explanation
    - Skincare recommendations
    - Ingredient recommendations
    - Sun protection
    - Lifestyle recommendations
    - Things to avoid
    - Progress status
    - Progress score
    - Progress observations
    - Medical disclaimer
    """

    # ---------------------------------------------------------
    # Report directory
    # ---------------------------------------------------------

    reports_dir: Path = (
        settings.upload_path / "reports"
    )

    reports_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path = (
        reports_dir / f"{report_id}.pdf"
    )

    # ---------------------------------------------------------
    # Styles
    # ---------------------------------------------------------

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "SkyntriTitle",
        parent=styles["Heading1"],
        textColor=BRAND_TEAL,
        fontSize=20,
        leading=24,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "SkyntriSubtitle",
        parent=styles["Normal"],
        textColor=MUTED,
        fontSize=10,
        leading=14,
        spaceAfter=12,
    )

    heading_style = ParagraphStyle(
        "SkyntriHeading",
        parent=styles["Heading2"],
        textColor=DARK,
        fontSize=13,
        leading=17,
        spaceBefore=14,
        spaceAfter=7,
    )

    body_style = ParagraphStyle(
        "SkyntriBody",
        parent=styles["Normal"],
        textColor=DARK,
        fontSize=9.5,
        leading=14,
        spaceAfter=4,
    )

    small_style = ParagraphStyle(
        "SkyntriSmall",
        parent=styles["Normal"],
        textColor=MUTED,
        fontSize=8.5,
        leading=12,
    )

    disclaimer_style = ParagraphStyle(
        "SkyntriDisclaimer",
        parent=styles["Normal"],
        textColor=MUTED,
        fontSize=8.5,
        leading=12,
    )

    # ---------------------------------------------------------
    # PDF document
    # ---------------------------------------------------------

    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=A4,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title=title,
        author="Skyntri",
    )

    story: list = []

    # ---------------------------------------------------------
    # Header
    # ---------------------------------------------------------

    story.append(
        Paragraph(
            "Skyntri",
            title_style,
        )
    )

    story.append(
        Paragraph(
            "AI-Based Skin Health Assistant — Health Report",
            subtitle_style,
        )
    )

    story.append(
        Paragraph(
            _safe_text(title),
            heading_style,
        )
    )

    # ---------------------------------------------------------
    # User information
    # ---------------------------------------------------------

    story.append(
        Paragraph(
            "User Information",
            heading_style,
        )
    )

    generated_at = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    meta_table = _make_table(
        [
            [
                "Name",
                _safe_text(user.full_name),
            ],
            [
                "Email",
                _safe_text(user.email),
            ],
            [
                "Skin type",
                _safe_text(user.skin_type),
            ],
            [
                "Report generated",
                generated_at,
            ],
        ],
        [
            4 * cm,
            11 * cm,
        ],
    )

    story.append(
        meta_table
    )

    # ---------------------------------------------------------
    # Skin analysis
    # ---------------------------------------------------------

    if analysis:
        story.append(
            Paragraph(
                "Skin Analysis",
                heading_style,
            )
        )

        conditions = _condition_list(
            analysis.predicted_condition
        )

        condition_text = (
            ", ".join(conditions)
            if conditions
            else "No specific visible condition detected"
        )

        severity = (
            analysis.severity_level
            or "Low"
        )

        analysis_table = _make_table(
            [
                [
                    "Detected conditions",
                    _safe_text(condition_text),
                ],
                [
                    "Confidence",
                    f"{float(analysis.confidence_score):.1f}%",
                ],
                [
                    "Estimated severity",
                    _safe_text(severity),
                ],
                [
                    "Analysis date",
                    analysis.created_at.strftime(
                        "%Y-%m-%d"
                    ),
                ],
            ],
            [
                4 * cm,
                11 * cm,
            ],
        )

        story.append(
            analysis_table
        )

        # -----------------------------------------------------
        # Explanation
        # -----------------------------------------------------

        if analysis.explanation:
            story.append(
                Spacer(
                    1,
                    7,
                )
            )

            story.append(
                Paragraph(
                    _safe_text(
                        analysis.explanation
                    ),
                    body_style,
                )
            )

        # -----------------------------------------------------
        # Recommendations
        # -----------------------------------------------------

        recommendations = build_recommendations(
            conditions
        )

        _add_bullet_section(
            story,
            "Recommended Skincare",
            recommendations["skincare"],
            heading_style,
            body_style,
        )

        _add_bullet_section(
            story,
            "Recommended Ingredients",
            recommendations["ingredients"],
            heading_style,
            body_style,
        )

        _add_bullet_section(
            story,
            "Sun Protection",
            recommendations["sun_protection"],
            heading_style,
            body_style,
        )

        _add_bullet_section(
            story,
            "Lifestyle",
            recommendations["lifestyle"],
            heading_style,
            body_style,
        )

        _add_bullet_section(
            story,
            "Things to Avoid",
            recommendations["avoid"],
            heading_style,
            body_style,
        )

    # ---------------------------------------------------------
    # Progress tracking
    # ---------------------------------------------------------

    if progress:
        story.append(
            Paragraph(
                "Progress Tracking",
                heading_style,
            )
        )

        progress_table = _make_table(
            [
                [
                    "Status",
                    _safe_text(progress.status),
                ],
                [
                    "Progress score",
                    f"{float(progress.score):.1f}%",
                ],
                [
                    "Comparison date",
                    progress.created_at.strftime(
                        "%Y-%m-%d"
                    ),
                ],
            ],
            [
                4 * cm,
                11 * cm,
            ],
        )

        story.append(
            progress_table
        )

        # -----------------------------------------------------
        # Progress observations
        # -----------------------------------------------------

        observations = _load_observations(
            progress.observations_json
        )

        _add_bullet_section(
            story,
            "Progress Observations",
            observations,
            heading_style,
            body_style,
        )

    # ---------------------------------------------------------
    # Disclaimer
    # ---------------------------------------------------------

    story.append(
        Spacer(
            1,
            18,
        )
    )

    story.append(
        Paragraph(
            "Important Disclaimer",
            heading_style,
        )
    )

    story.append(
        Paragraph(
            (
                "This report is generated by Skyntri, an AI-based "
                "skin health assistant, for informational purposes "
                "only. AI analysis identifies visible skin patterns "
                "and provides an estimated severity level; it is not "
                "a certified medical diagnosis. Results may be "
                "affected by image quality, lighting, camera angle, "
                "and other factors. Progress scores are visual "
                "comparison estimates and should not be interpreted "
                "as a clinical measurement. This report does not "
                "replace professional medical advice. Please consult "
                "a qualified dermatologist or healthcare provider "
                "for persistent, severe, painful, rapidly worsening, "
                "or concerning skin problems."
            ),
            disclaimer_style,
        )
    )

    story.append(
        Spacer(
            1,
            8,
        )
    )

    story.append(
        Paragraph(
            (
                "Skyntri — Final Year Project, Department of "
                "Software Engineering, MUST."
            ),
            small_style,
        )
    )

    # ---------------------------------------------------------
    # Build PDF
    # ---------------------------------------------------------

    doc.build(
        story
    )

    return str(file_path)