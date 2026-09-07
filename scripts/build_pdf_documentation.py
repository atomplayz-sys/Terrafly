"""
Builds a high-quality, professional PDF document from TerraFly_Complete_Explanation.md
using ReportLab Platypus with seamless pagination for long code blocks and diagrams.
"""

from __future__ import annotations

import html
import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Preformatted,
    HRFlowable,
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#4a5568"))

        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(
                42,
                756,
                "TerraFly: Complete Technical & Educational Guide (SIH PS 26175)",
            )
            self.setStrokeColor(colors.HexColor("#cbd5e0"))
            self.setLineWidth(0.5)
            self.line(42, 750, 570, 750)

        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#cbd5e0"))
        self.setLineWidth(0.5)
        self.line(42, 45, 570, 45)

        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(570, 32, page_str)
        self.drawString(42, 32, "CONFIDENTIAL & PROPRIETARY — TERRAFLY ENGINEERING")
        self.restoreState()


def format_inline_markdown(text: str) -> str:
    """Escape XML special chars and convert Markdown bold/italics/code to ReportLab tags."""
    # Convert code spans first using a placeholder
    codes = []

    def save_code(match):
        idx = len(codes)
        codes.append(match.group(1))
        return f"__CODE_SPAN_{idx}__"

    text = re.sub(r"`([^`]+)`", save_code, text)

    # Escape HTML/XML entities
    text = html.escape(text)

    # Bold + Italic
    text = re.sub(r"\*\*\*([^*]+)\*\*\*", r"<b><i>\1</i></b>", text)
    # Bold
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    # Italic
    text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)

    # Restore code spans with styling
    for idx, code_content in enumerate(codes):
        escaped_code = html.escape(code_content)
        code_tag = f'<font name="Courier" color="#b83280"><b>{escaped_code}</b></font>'
        text = text.replace(f"__CODE_SPAN_{idx}__", code_tag)

    return text


def build_pdf(md_path: str, pdf_path: str) -> None:
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=42,
        rightMargin=42,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1a365d"),
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2b6cb0"),
        spaceAfter=12,
    )

    h1_style = ParagraphStyle(
        "CustomH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#1a365d"),
        spaceBefore=12,
        spaceAfter=5,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "CustomH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13.5,
        textColor=colors.HexColor("#2c5282"),
        spaceBefore=9,
        spaceAfter=4,
        keepWithNext=True,
    )

    h3_style = ParagraphStyle(
        "CustomH3",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12.5,
        textColor=colors.HexColor("#2d3748"),
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#1a202c"),
        spaceAfter=4.5,
    )

    bullet_style = ParagraphStyle(
        "CustomBullet",
        parent=body_style,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3,
    )

    code_block_style = ParagraphStyle(
        "CustomCode",
        fontName="Courier",
        fontSize=6.5,
        leading=8.5,
        textColor=colors.HexColor("#2d3748"),
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#1a202c"),
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    lines = md_text.splitlines()
    story = []

    i = 0
    in_code_block = False
    code_lines = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Handle Code / ASCII Blocks
        if stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lines = []
            else:
                in_code_block = False
                # Split large code blocks into chunks of at most 32 lines to paginate smoothly
                chunk_size = 32
                for chunk_idx in range(0, max(1, len(code_lines)), chunk_size):
                    chunk = code_lines[chunk_idx : chunk_idx + chunk_size]
                    if not chunk:
                        continue
                    block_content = "\n".join(chunk)
                    escaped_block = html.escape(block_content)

                    pre = Preformatted(escaped_block, code_block_style)
                    code_table = Table([[pre]], colWidths=[528])
                    code_table.setStyle(
                        TableStyle(
                            [
                                (
                                    "BACKGROUND",
                                    (0, 0),
                                    (-1, -1),
                                    colors.HexColor("#f7fafc"),
                                ),
                                (
                                    "BOX",
                                    (0, 0),
                                    (-1, -1),
                                    0.5,
                                    colors.HexColor("#e2e8f0"),
                                ),
                                ("PADDING", (0, 0), (-1, -1), 5),
                                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ]
                        )
                    )
                    story.append(code_table)
                    if chunk_idx + chunk_size < len(code_lines):
                        story.append(Spacer(1, 2))
                    else:
                        story.append(Spacer(1, 5))
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Blank line
        if not stripped:
            i += 1
            continue

        # Horizontal Rule
        if stripped in ["---", "===", "***"]:
            story.append(Spacer(1, 3))
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=colors.HexColor("#cbd5e0"),
                    spaceBefore=3,
                    spaceAfter=6,
                )
            )
            i += 1
            continue

        # Markdown Table Detection
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines = []
            while (
                i < len(lines)
                and lines[i].strip().startswith("|")
                and lines[i].strip().endswith("|")
            ):
                table_lines.append(lines[i].strip())
                i += 1

            if len(table_lines) >= 2:
                parsed_rows = []
                for row_idx, t_line in enumerate(table_lines):
                    if re.match(r"^\|[\s\-:|]+\|$", t_line):
                        continue
                    cols = [c.strip() for c in t_line.strip("|").split("|")]
                    parsed_rows.append((row_idx == 0, cols))

                if parsed_rows:
                    num_cols = len(parsed_rows[0][1])
                    total_width = 528
                    if num_cols == 6:
                        col_widths = [70, 70, 105, 95, 94, 94]
                    elif num_cols == 4:
                        col_widths = [105, 95, 200, 128]
                    else:
                        col_widths = [total_width / num_cols] * num_cols

                    table_data = []
                    for is_header, cols in parsed_rows:
                        row_cells = []
                        for col_idx, col in enumerate(cols):
                            formatted_text = format_inline_markdown(col)
                            if is_header:
                                row_cells.append(
                                    Paragraph(
                                        formatted_text, table_header_style
                                    )
                                )
                            else:
                                row_cells.append(
                                    Paragraph(formatted_text, table_cell_style)
                                )
                        while len(row_cells) < num_cols:
                            row_cells.append(Paragraph("", table_cell_style))
                        table_data.append(row_cells[:num_cols])

                    report_table = Table(
                        table_data, colWidths=col_widths, repeatRows=1
                    )
                    report_table.setStyle(
                        TableStyle(
                            [
                                (
                                    "BACKGROUND",
                                    (0, 0),
                                    (-1, 0),
                                    colors.HexColor("#2b6cb0"),
                                ),
                                (
                                    "TEXTCOLOR",
                                    (0, 0),
                                    (-1, 0),
                                    colors.whitesmoke,
                                ),
                                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                (
                                    "BOTTOMPADDING",
                                    (0, 0),
                                    (-1, 0),
                                    4,
                                ),
                                ("TOPPADDING", (0, 0), (-1, 0), 4),
                                ("PADDING", (0, 1), (-1, -1), 3),
                                (
                                    "GRID",
                                    (0, 0),
                                    (-1, -1),
                                    0.5,
                                    colors.HexColor("#cbd5e0"),
                                ),
                                (
                                    "ROWBACKGROUNDS",
                                    (0, 1),
                                    (-1, -1),
                                    [
                                        colors.white,
                                        colors.HexColor("#f7fafc"),
                                    ],
                                ),
                            ]
                        )
                    )
                    story.append(Spacer(1, 3))
                    story.append(report_table)
                    story.append(Spacer(1, 5))
            continue

        # Headings
        if stripped.startswith("# "):
            title_text = stripped[2:].strip()
            story.append(
                Paragraph(format_inline_markdown(title_text), title_style)
            )
            i += 1
            continue

        if stripped.startswith("## "):
            h1_text = stripped[3:].strip()
            story.append(
                Paragraph(format_inline_markdown(h1_text), subtitle_style)
            )
            i += 1
            continue

        if stripped.startswith("### "):
            h2_text = stripped[4:].strip()
            story.append(Paragraph(format_inline_markdown(h2_text), h1_style))
            i += 1
            continue

        if stripped.startswith("#### "):
            h3_text = stripped[5:].strip()
            story.append(Paragraph(format_inline_markdown(h3_text), h2_style))
            i += 1
            continue

        # Bullet List Items
        if stripped.startswith(("- ", "* ", "+ ")) or re.match(
            r"^\d+\.\s", stripped
        ):
            match = re.match(r"^(\d+\.|\-|\*|\+)\s+(.*)$", stripped)
            if match:
                marker, content = match.groups()
                formatted_item = f"<b>{html.escape(marker)}</b> {format_inline_markdown(content)}"
                story.append(Paragraph(formatted_item, bullet_style))
            else:
                story.append(
                    Paragraph(format_inline_markdown(stripped), bullet_style)
                )
            i += 1
            continue

        # Standard Paragraph
        story.append(Paragraph(format_inline_markdown(stripped), body_style))
        i += 1

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully built at: {pdf_path}")


if __name__ == "__main__":
    base_dir = os.path.abspath("G:/TerraFly_FINAL_WINDOWS")
    md_file = os.path.join(base_dir, "docs", "TerraFly_Complete_Explanation.md")
    pdf_file = os.path.join(
        base_dir, "docs", "TerraFly_Complete_Explanation.pdf"
    )

    print(f"Building PDF from {md_file} ...")
    build_pdf(md_file, pdf_file)
