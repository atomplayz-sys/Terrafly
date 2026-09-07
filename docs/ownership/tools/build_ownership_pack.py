from __future__ import annotations

import base64
import html
import io
import re
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image as RLImage,
    KeepTogether,
    LongTable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parents[3]
OWNERSHIP = ROOT / "docs" / "ownership"
DIAGRAM_DIR = OWNERSHIP / "diagrams"
SCREENSHOT_DIR = OWNERSHIP / "screenshots"
RENDER_DIR = OWNERSHIP / "rendered-pages"

GREEN = "#0D6B5B"
DARK = "#12302B"
INK = "#1B2926"
MUTED = "#55706A"
PALE = "#E9F4F1"
AMBER = "#B36A16"
RED = "#A33A35"
WHITE = "#FFFFFF"
GRID = "#C5D5D1"


def safe_ascii(value: str) -> str:
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00d7": "x",
        "\u2192": "->",
        "\u2265": ">=",
        "\u2264": "<=",
        "\u00b0": " degrees",
        "\u00b7": " / ",
        "\u00a0": " ",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    return value.encode("ascii", "replace").decode("ascii")


def find_font(bold: bool = False, mono: bool = False) -> str:
    candidates = []
    if mono:
        candidates = [
            Path("C:/Windows/Fonts/consola.ttf"),
            Path("C:/Windows/Fonts/lucon.ttf"),
        ]
    elif bold:
        candidates = [
            Path("C:/Windows/Fonts/arialbd.ttf"),
            Path("C:/Windows/Fonts/calibrib.ttf"),
        ]
    else:
        candidates = [
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/calibri.ttf"),
        ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return ""


BODY_TTF = find_font()
BOLD_TTF = find_font(bold=True)
MONO_TTF = find_font(mono=True)
if BODY_TTF:
    pdfmetrics.registerFont(TTFont("TerraBody", BODY_TTF))
if BOLD_TTF:
    pdfmetrics.registerFont(TTFont("TerraBold", BOLD_TTF))
if MONO_TTF:
    pdfmetrics.registerFont(TTFont("TerraMono", MONO_TTF))

FONT_BODY = "TerraBody" if BODY_TTF else "Helvetica"
FONT_BOLD = "TerraBold" if BOLD_TTF else "Helvetica-Bold"
FONT_MONO = "TerraMono" if MONO_TTF else "Courier"


def pil_font(size: int, bold: bool = False):
    path = BOLD_TTF if bold else BODY_TTF
    return ImageFont.truetype(path, size) if path else ImageFont.load_default()


DIAGRAMS = {
    "01_runtime_architecture": {
        "title": "TerraFly runtime architecture",
        "columns": [
            [("Operator", "Browser actions"), ("React UI", "App + Viewer")],
            [("HTTP contract", "api.ts"), ("FastAPI", "routes + static UI"), ("Job store", "atomic job state")],
            [("Photo AI", "pipeline + DAV2"), ("DEM Terrain", "validation + alignment"), ("Calibration", "fit + gates")],
            [("Artifacts", "arrays, reports, GLB"), ("Evidence", "manifest + SHA-256")],
        ],
        "note": "Poll status -> show only artifacts that actually exist",
    },
    "02_scientific_states": {
        "title": "Scientific states require new evidence",
        "columns": [
            [("PNG / JPG", "visual input"), ("Optical GeoTIFF", "horizontal georeference")],
            [("Relative", "0..1, no metres"), ("Georeferenced Relative", "0..1 + CRS/transform")],
            [("Independent gate", "reference DSM or GCP"), ("Named source DEM", "metre evidence + datum")],
            [("Metric Calibrated", "AI-derived metres"), ("Metric Source DEM", "source-derived metres")],
        ],
        "note": "A visual switch cannot create scale, offset or datum",
    },
    "03_dem_terrain_flow": {
        "title": "DEM Terrain workflow",
        "columns": [
            [("Optical GeoTIFF", "bands, CRS, transform"), ("Source DEM", "units, CRS, NoData")],
            [("Overlap gate", "same place?"), ("Alignment", "reproject + bilinear")],
            [("Metric arrays", "preserve metres + mask"), ("Display grid", "normalized copy")],
            [("Outputs", "GeoTIFF, GLB, report"), ("Viewer", "texture + A/B metres")],
        ],
        "note": "Resampling aligns the grid; it never upgrades native DEM information",
    },
    "04_photo_ai_flow": {
        "title": "Photo AI workflow",
        "columns": [
            [("Image validation", "PNG/JPG/GeoTIFF -> RGB"), ("DAV2 Large", "exact revision + device")],
            [("Raw prediction", "direct or bounded tiles"), ("Tile alignment", "positive affine + feather")],
            [("Direction contract", "inverse-depth/proximity"), ("Canonical surface", "one global 0..1 normalization")],
            [("Display copy", "cleanup + GLB"), ("Evidence", "raw, relative, diagnostics")],
        ],
        "note": "The first output remains relative even when it looks three-dimensional",
    },
    "05_calibration_gate": {
        "title": "Metric calibration gate",
        "columns": [
            [("Relative + georef", "canonical array"), ("Reference / GCP", "independent evidence")],
            [("Fit", "elevation = scale x relative + offset"), ("Holdout", "never fits scale/offset")],
            [("Six checks", "scale, span, inliers, coverage, RMSE, R2")],
            [("PASS", "write metric files"), ("REJECT", "report only; files locked")],
        ],
        "note": "Rejection is a correct scientific result, not a software failure",
    },
    "06_pixels_to_mesh": {
        "title": "Height pixels to textured mesh and measurement",
        "columns": [
            [("Height grid", "one value per row/column"), ("Optical RGB", "source texture")],
            [("Geometry", "vertices + triangle indices"), ("Attributes", "normals + UV")],
            [("PBR mesh", "GLB / Three.js"), ("Camera", "orbit or free flight")],
            [("Raycast", "UV -> pixel"), ("A/B result", "value, delta, distance, slope")],
        ],
        "note": "Display exaggeration changes vertices, never stored measurements",
    },
    "07_request_flows": {
        "title": "Five auditable request flows",
        "columns": [
            [("A Photo", "App -> API -> pipeline"), ("B DEM", "App -> terrain worker")],
            [("C Calibrate", "request -> gates"), ("D Download", "link -> safe route")],
            [("E Click", "raycast -> grid sample")],
            [("Common proof", "job update + poll + test + artifact")],
        ],
        "note": "Every visible result has a route, worker, stored evidence and supporting test",
    },
}


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]):
    draw.line([start, end], fill=GREEN, width=4)
    ex, ey = end
    sx, sy = start
    if abs(ex - sx) >= abs(ey - sy):
        sign = 1 if ex > sx else -1
        points = [(ex, ey), (ex - 14 * sign, ey - 8), (ex - 14 * sign, ey + 8)]
    else:
        sign = 1 if ey > sy else -1
        points = [(ex, ey), (ex - 8, ey - 14 * sign), (ex + 8, ey - 14 * sign)]
    draw.polygon(points, fill=GREEN)


def render_diagram(key: str, spec: dict):
    width, height = 1800, 980
    image = Image.new("RGB", (width, height), "#F7FAF9")
    draw = ImageDraw.Draw(image)
    title_font = pil_font(48, bold=True)
    heading_font = pil_font(29, bold=True)
    body_font = pil_font(23)
    note_font = pil_font(25, bold=True)
    draw.rectangle((0, 0, width, 105), fill=DARK)
    draw.text((70, 27), spec["title"], font=title_font, fill=WHITE)
    columns = spec["columns"]
    margin_x, gap = 70, 48
    col_w = int((width - 2 * margin_x - gap * (len(columns) - 1)) / len(columns))
    top, bottom = 170, 760
    centers = []
    for col_idx, nodes in enumerate(columns):
        x0 = margin_x + col_idx * (col_w + gap)
        col_centers = []
        count = len(nodes)
        node_gap = 28
        node_h = min(215, int((bottom - top - node_gap * (count - 1)) / count))
        total_h = count * node_h + (count - 1) * node_gap
        y = top + (bottom - top - total_h) // 2
        for title, subtitle in nodes:
            x1, y1 = x0, y
            x2, y2 = x0 + col_w, y + node_h
            draw.rounded_rectangle((x1, y1, x2, y2), radius=22, fill=WHITE, outline=GREEN, width=4)
            wrapped_title = textwrap.wrap(title, width=max(12, int(col_w / 24)))
            wrapped_sub = textwrap.wrap(subtitle, width=max(14, int(col_w / 18)))
            ty = y1 + 28
            for line in wrapped_title:
                box = draw.textbbox((0, 0), line, font=heading_font)
                draw.text((x1 + (col_w - (box[2] - box[0])) / 2, ty), line, font=heading_font, fill=DARK)
                ty += 37
            ty += 8
            for line in wrapped_sub:
                box = draw.textbbox((0, 0), line, font=body_font)
                draw.text((x1 + (col_w - (box[2] - box[0])) / 2, ty), line, font=body_font, fill=MUTED)
                ty += 31
            col_centers.append((int((x1 + x2) / 2), int((y1 + y2) / 2)))
            y += node_h + node_gap
        centers.append(col_centers)
    for idx in range(len(centers) - 1):
        left = centers[idx]
        right = centers[idx + 1]
        for j, p1 in enumerate(left):
            p2 = right[min(j, len(right) - 1)]
            draw_arrow(draw, (p1[0] + col_w // 2, p1[1]), (p2[0] - col_w // 2, p2[1]))
    draw.rounded_rectangle((70, 835, width - 70, 925), radius=18, fill="#FFF4E7", outline=AMBER, width=3)
    note = safe_ascii(spec["note"])
    bbox = draw.textbbox((0, 0), note, font=note_font)
    draw.text(((width - (bbox[2] - bbox[0])) / 2, 864), note, font=note_font, fill="#7B4712")
    png_path = DIAGRAM_DIR / f"{key}.png"
    image.save(png_path, quality=95)


def annotations_for(name: str):
    mapping = {
        "01-live-start-screen": [
            (0.20, 0.22, "Recommended DEM workflow"),
            (0.50, 0.22, "Experimental Photo AI boundary"),
            (0.23, 0.64, "Source and datum provenance"),
        ],
        "02-live-dem-terrain-result": [
            (0.16, 0.12, "Metric Source DEM state"),
            (0.50, 0.44, "Textured height mesh"),
            (0.49, 0.12, "Inspection controls"),
            (0.88, 0.58, "Numeric metre legend"),
        ],
        "03-live-photo-ai-calibrated": [
            (0.16, 0.12, "Metric Calibrated state"),
            (0.50, 0.44, "Inspection mesh"),
            (0.20, 0.77, "Model and provenance evidence"),
            (0.49, 0.12, "Photo/height modes"),
        ],
        "04-live-calibration-passed": [
            (0.76, 0.66, "Gate status: Passed"),
            (0.76, 0.79, "Report and metric artifacts"),
            (0.25, 0.90, "Synthetic oracle - not accuracy"),
        ],
    }
    return mapping[name]


def annotate_screenshot(source: Path):
    original = Image.open(source).convert("RGB")
    w, h = original.size
    panel_w = max(360, int(w * 0.33))
    canvas = Image.new("RGB", (w + panel_w, h), "#F7FAF9")
    canvas.paste(original, (0, 0))
    draw = ImageDraw.Draw(canvas)
    heading = pil_font(max(24, int(h / 28)), bold=True)
    body = pil_font(max(19, int(h / 38)))
    number_font = pil_font(max(20, int(h / 34)), bold=True)
    draw.rectangle((w, 0, w + panel_w, h), fill=DARK)
    draw.text((w + 30, 28), "LIVE EVIDENCE", font=heading, fill=WHITE)
    annotations = annotations_for(source.stem)
    y = 105
    svg_shapes = []
    for index, (xp, yp, label) in enumerate(annotations, start=1):
        px, py = int(w * xp), int(h * yp)
        radius = max(18, int(h / 38))
        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=GREEN, outline=WHITE, width=3)
        number = str(index)
        bb = draw.textbbox((0, 0), number, font=number_font)
        draw.text((px - (bb[2] - bb[0]) / 2, py - (bb[3] - bb[1]) / 2 - 2), number, font=number_font, fill=WHITE)
        draw.line((px + radius, py, w + 12, y + 18), fill=GREEN, width=3)
        draw.ellipse((w + 25, y, w + 63, y + 38), fill=GREEN)
        draw.text((w + 37, y + 4), number, font=number_font, fill=WHITE)
        lines = textwrap.wrap(label, width=max(22, int(panel_w / 14)))
        ty = y
        for line in lines:
            draw.text((w + 78, ty), line, font=body, fill=WHITE)
            ty += int(h / 30)
        y = ty + 35
        svg_shapes.append((index, px, py, label, y))
    out_png = SCREENSHOT_DIR / f"{source.stem}-annotated.png"
    canvas.save(out_png, quality=95)

    encoded = base64.b64encode(source.read_bytes()).decode("ascii")
    mime = "image/png"
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w + panel_w}" height="{h}" viewBox="0 0 {w + panel_w} {h}">',
        f'<image href="data:{mime};base64,{encoded}" x="0" y="0" width="{w}" height="{h}"/>',
        f'<rect x="{w}" y="0" width="{panel_w}" height="{h}" fill="{DARK}"/>',
        f'<text x="{w + 30}" y="60" font-family="Arial" font-size="34" font-weight="bold" fill="white">LIVE EVIDENCE</text>',
    ]
    sy = 125
    for index, (xp, yp, label) in enumerate(annotations, start=1):
        px, py = int(w * xp), int(h * yp)
        svg.extend([
            f'<line x1="{px + 24}" y1="{py}" x2="{w + 16}" y2="{sy}" stroke="{GREEN}" stroke-width="4"/>',
            f'<circle cx="{px}" cy="{py}" r="24" fill="{GREEN}" stroke="white" stroke-width="3"/>',
            f'<text x="{px}" y="{py + 9}" text-anchor="middle" font-family="Arial" font-size="25" font-weight="bold" fill="white">{index}</text>',
            f'<circle cx="{w + 44}" cy="{sy}" r="20" fill="{GREEN}"/>',
            f'<text x="{w + 44}" y="{sy + 8}" text-anchor="middle" font-family="Arial" font-size="22" font-weight="bold" fill="white">{index}</text>',
        ])
        wrapped = textwrap.wrap(label, width=28)
        svg.append(f'<text x="{w + 78}" y="{sy + 7}" font-family="Arial" font-size="23" fill="white">')
        for line_idx, line in enumerate(wrapped):
            dy = 0 if line_idx == 0 else 29
            svg.append(f'<tspan x="{w + 78}" dy="{dy}">{xml_escape(line)}</tspan>')
        svg.append('</text>')
        sy += 65 + 29 * max(0, len(wrapped) - 1)
    svg.append('</svg>')
    (SCREENSHOT_DIR / f"{source.stem}-annotated.svg").write_text("\n".join(svg), encoding="utf-8")


def build_visual_assets():
    DIAGRAM_DIR.mkdir(parents=True, exist_ok=True)
    for key, spec in DIAGRAMS.items():
        render_diagram(key, spec)
    for source in sorted(SCREENSHOT_DIR.glob("0[1-4]-live-*.png")):
        if "-annotated" not in source.stem:
            annotate_screenshot(source)


def inline_markup(text: str) -> str:
    text = safe_ascii(text.strip())
    tokens: list[str] = []

    def store(value: str) -> str:
        tokens.append(value)
        return f"@@TOKEN{len(tokens)-1}@@"

    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", lambda m: store(f'<link href="{html.escape(m.group(2), quote=True)}" color="{GREEN}"><u>{html.escape(m.group(1))}</u></link>'), text)
    text = re.sub(r"`([^`]+)`", lambda m: store(f'<font name="{FONT_MONO}" color="#204B43">{html.escape(m.group(1))}</font>'), text)
    text = re.sub(r"\*\*([^*]+)\*\*", lambda m: store(f'<b>{html.escape(m.group(1))}</b>'), text)
    text = html.escape(text)
    for idx in reversed(range(len(tokens))):
        token = tokens[idx]
        text = text.replace(f"@@TOKEN{idx}@@", token)
    return text


class SectionMarker(Flowable):
    def __init__(self, key: str):
        super().__init__()
        self.key = key
        self.width = self.height = 0

    def draw(self):
        pass


class TerraDoc(BaseDocTemplate):
    def __init__(self, filename: str, short_title: str, **kwargs):
        super().__init__(filename, **kwargs)
        self.short_title = short_title
        self._outline_started = False
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="main")
        self.addPageTemplates(PageTemplate(id="pages", frames=[frame], onPage=self._decorate))

    def _decorate(self, canvas, doc):
        page = canvas.getPageNumber()
        if page == 1:
            return
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor(GRID))
        canvas.line(self.leftMargin, A4[1] - 16 * mm, A4[0] - self.rightMargin, A4[1] - 16 * mm)
        canvas.setFont(FONT_BODY, 8)
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawString(self.leftMargin, A4[1] - 13 * mm, self.short_title)
        canvas.drawRightString(A4[0] - self.rightMargin, 11 * mm, f"TerraFly ownership pack | Page {page}")
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style_name = flowable.style.name
            if style_name in ("H1", "H2"):
                if self.page == 1:
                    return
                level = 0 if style_name == "H1" else 1
                if level == 1 and not self._outline_started:
                    return
                if level == 0:
                    self._outline_started = True
                text_value = safe_ascii(flowable.getPlainText())
                key = f"h-{self.page}-{abs(hash(text_value))}"
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text_value, key, level=level, closed=False)
                self.notify("TOCEntry", (level, text_value, self.page, key))


def make_styles():
    base = getSampleStyleSheet()
    styles = {
        "Body": ParagraphStyle("Body", parent=base["BodyText"], fontName=FONT_BODY, fontSize=9.3, leading=13.2, textColor=colors.HexColor(INK), spaceAfter=5),
        "H1": ParagraphStyle("H1", parent=base["Heading1"], fontName=FONT_BOLD, fontSize=18, leading=22, textColor=colors.HexColor(DARK), spaceBefore=12, spaceAfter=7, keepWithNext=True),
        "H2": ParagraphStyle("H2", parent=base["Heading2"], fontName=FONT_BOLD, fontSize=13.5, leading=17, textColor=colors.HexColor(GREEN), spaceBefore=9, spaceAfter=5, keepWithNext=True),
        "H3": ParagraphStyle("H3", parent=base["Heading3"], fontName=FONT_BOLD, fontSize=11, leading=14, textColor=colors.HexColor(DARK), spaceBefore=7, spaceAfter=4, keepWithNext=True),
        "Quote": ParagraphStyle("Quote", parent=base["BodyText"], fontName=FONT_BODY, fontSize=9.2, leading=13, textColor=colors.HexColor(DARK), backColor=colors.HexColor(PALE), borderColor=colors.HexColor(GREEN), borderWidth=0.7, borderPadding=7, leftIndent=6, rightIndent=6, spaceBefore=5, spaceAfter=7),
        "Bullet": ParagraphStyle("Bullet", parent=base["BodyText"], fontName=FONT_BODY, fontSize=9.1, leading=12.8, leftIndent=14, firstLineIndent=-8, bulletIndent=4, textColor=colors.HexColor(INK), spaceAfter=2),
        "Code": ParagraphStyle("Code", parent=base["Code"], fontName=FONT_MONO, fontSize=7.8, leading=10.2, textColor=colors.HexColor(DARK), backColor=colors.HexColor("#F0F4F3"), borderPadding=6, spaceBefore=4, spaceAfter=7),
        "Caption": ParagraphStyle("Caption", parent=base["BodyText"], fontName=FONT_BODY, fontSize=8.3, leading=11, textColor=colors.HexColor(MUTED), alignment=TA_CENTER, spaceAfter=8),
        "CoverTitle": ParagraphStyle("CoverTitle", parent=base["Title"], fontName=FONT_BOLD, fontSize=30, leading=35, textColor=colors.HexColor(DARK), alignment=TA_LEFT, spaceAfter=12),
        "CoverSub": ParagraphStyle("CoverSub", parent=base["BodyText"], fontName=FONT_BODY, fontSize=13, leading=18, textColor=colors.HexColor(MUTED), spaceAfter=10),
    }
    return styles


def table_from_rows(rows: list[list[str]], available_width: float, styles):
    col_count = max(len(row) for row in rows)
    normalized = [row + [""] * (col_count - len(row)) for row in rows]
    lengths = []
    for col in range(col_count):
        longest = max(len(re.sub(r"[`*]", "", row[col])) for row in normalized)
        lengths.append(max(8, min(42, longest)))
    total = sum(lengths)
    col_widths = [available_width * item / total for item in lengths]
    data = []
    for row_index, row in enumerate(normalized):
        style = ParagraphStyle(
            f"Table{row_index}",
            parent=styles["Body"],
            fontName=FONT_BOLD if row_index == 0 else FONT_BODY,
            fontSize=7.5 if col_count >= 5 else 8.0,
            leading=9.6 if col_count >= 5 else 10.4,
            textColor=colors.white if row_index == 0 else colors.HexColor(INK),
            spaceAfter=0,
        )
        data.append([Paragraph(inline_markup(cell), style) for cell in row])
    table = LongTable(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor(GRID)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8F7")]),
    ]))
    return table


def parse_markdown(path: Path, styles, available_width: float):
    text = safe_ascii(path.read_text(encoding="utf-8"))
    lines = text.splitlines()
    story = []
    i = 0
    in_code = False
    code_lines: list[str] = []
    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith("```"):
            if in_code:
                story.append(Preformatted("\n".join(code_lines), styles["Code"])); code_lines = []; in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-+", lines[i + 1]):
            table_lines = [line]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].rstrip())
                i += 1
            rows = []
            for raw in table_lines:
                rows.append([cell.strip() for cell in raw.strip().strip("|").split("|")])
            story.append(table_from_rows(rows, available_width, styles))
            story.append(Spacer(1, 6))
            continue
        if line.startswith("### "):
            story.append(Paragraph(inline_markup(line[4:]), styles["H3"]))
        elif line.startswith("## "):
            story.append(Paragraph(inline_markup(line[3:]), styles["H2"]))
        elif line.startswith("# "):
            story.append(Paragraph(inline_markup(line[2:]), styles["H1"]))
        elif line.startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].startswith(">"):
                quote_lines.append(lines[i].lstrip("> "))
                i += 1
            story.append(Paragraph(inline_markup(" ".join(quote_lines)), styles["Quote"]))
            continue
        elif re.match(r"^\s*[-*] ", line):
            content = re.sub(r"^\s*[-*] ", "", line)
            story.append(Paragraph(inline_markup(content), styles["Bullet"], bulletText="-"))
        elif re.match(r"^\s*\d+\. ", line):
            match = re.match(r"^\s*(\d+)\. (.*)$", line)
            story.append(Paragraph(inline_markup(match.group(2)), styles["Bullet"], bulletText=match.group(1) + "."))
        elif line.strip():
            para_lines = [line]
            while i + 1 < len(lines):
                nxt = lines[i + 1].rstrip()
                if not nxt.strip() or nxt.startswith(("#", ">", "```", "|")) or re.match(r"^\s*[-*] ", nxt) or re.match(r"^\s*\d+\. ", nxt):
                    break
                para_lines.append(nxt)
                i += 1
            story.append(Paragraph(inline_markup(" ".join(para_lines)), styles["Body"]))
        else:
            story.append(Spacer(1, 3))
        i += 1
    return story


def scaled_image(path: Path, max_width: float, max_height: float):
    with Image.open(path) as image:
        width, height = image.size
    scale = min(max_width / width, max_height / height)
    return RLImage(str(path), width=width * scale, height=height * scale)


def cover_story(title: str, subtitle: str, styles):
    elements = [Spacer(1, 30 * mm)]
    elements.append(Table([["TF", "TERRAFLY"]], colWidths=[25 * mm, 125 * mm], rowHeights=[25 * mm], style=TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(GREEN)),
        ("TEXTCOLOR", (0, 0), (0, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), FONT_BOLD),
        ("FONTSIZE", (0, 0), (0, 0), 19),
        ("FONTSIZE", (1, 0), (1, 0), 16),
        ("TEXTCOLOR", (1, 0), (1, 0), colors.HexColor(DARK)),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (1, 0), (1, 0), 2, colors.HexColor(GREEN)),
    ])))
    elements += [Spacer(1, 28 * mm), Paragraph(title, styles["CoverTitle"]), Paragraph(subtitle, styles["CoverSub"])]
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph("Verified against the packaged TerraFly project and live application on 2026-08-28.", styles["Quote"]))
    elements.append(Spacer(1, 42 * mm))
    elements.append(Paragraph("Scientific position", styles["H2"]))
    elements.append(Paragraph("Measured mountains come from a named DEM. Photo AI begins as relative shape. AI-derived metric files exist only after independent validation passes. Good-looking 3D is never substituted for evidence.", styles["Body"]))
    elements.append(PageBreak())
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOC1", fontName=FONT_BOLD, fontSize=10.5, leading=14, leftIndent=0, textColor=colors.HexColor(DARK), spaceBefore=4),
        ParagraphStyle("TOC2", fontName=FONT_BODY, fontSize=9, leading=12, leftIndent=14, textColor=colors.HexColor(MUTED)),
    ]
    elements.append(Paragraph("Contents", styles["H1"]))
    elements.append(toc)
    elements.append(PageBreak())
    return elements


def add_visual_appendix(story, styles, include_screenshots: bool):
    story.append(PageBreak())
    story.append(Paragraph("Visual evidence and editable diagrams", styles["H1"]))
    story.append(Paragraph("The diagram sources are editable Mermaid files in docs/ownership/diagrams. Screenshot SVG overlays remain editable; annotated PNGs are flattened copies for portable viewing. Original captures are preserved.", styles["Body"]))
    for key, spec in DIAGRAMS.items():
        story.append(Paragraph(spec["title"], styles["H2"]))
        story.append(scaled_image(DIAGRAM_DIR / f"{key}.png", 170 * mm, 94 * mm))
        story.append(Paragraph(spec["note"], styles["Caption"]))
    if include_screenshots:
        for source in sorted(SCREENSHOT_DIR.glob("0[1-4]-live-*-annotated.png")):
            story.append(PageBreak())
            title = source.stem.replace("-annotated", "").replace("-", " ").title()
            story.append(Paragraph(title, styles["H2"]))
            story.append(scaled_image(source, 170 * mm, 205 * mm))
            story.append(Paragraph("Actual live application capture with editable SVG callouts stored beside this image.", styles["Caption"]))


def build_pdf(output: Path, title: str, subtitle: str, markdown_files: list[Path], include_screenshots: bool):
    styles = make_styles()
    doc = TerraDoc(
        str(output),
        short_title=title,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=21 * mm,
        bottomMargin=18 * mm,
        title=title,
        author="TerraFly project team",
        subject=subtitle,
    )
    story = cover_story(title, subtitle, styles)
    for idx, markdown in enumerate(markdown_files):
        if idx:
            story.append(PageBreak())
        story.extend(parse_markdown(markdown, styles, doc.width))
    add_visual_appendix(story, styles, include_screenshots=include_screenshots)
    doc.multiBuild(story)


def main():
    build_visual_assets()
    build_pdf(
        OWNERSHIP / "TerraFly_Source_to_System_Atlas.pdf",
        "TerraFly Source-to-System Atlas",
        "Problem, evidence states, complete request traces, source atlas, artifacts, claims and live proof",
        [
            OWNERSHIP / "TerraFly_Source_to_System_Atlas.md",
            OWNERSHIP / "CLAIMS_LEDGER.md",
            OWNERSHIP / "INCONSISTENCIES_AND_LIMITATIONS.md",
            OWNERSHIP / "SOURCE_LINE_INDEX.md",
        ],
        include_screenshots=True,
    )
    build_pdf(
        OWNERSHIP / "TerraFly_Zero_to_Ownership_Bootcamp.pdf",
        "TerraFly Zero-to-Ownership Bootcamp",
        "A minimal verified learning path, six role tracks, data/training plan, oral exam and judge-readiness gate",
        [
            OWNERSHIP / "TerraFly_Zero_to_Ownership_Bootcamp.md",
            OWNERSHIP / "RESOURCE_VERIFICATION_TABLE.md",
            OWNERSHIP / "CLAIMS_LEDGER.md",
        ],
        include_screenshots=False,
    )
    print(str(OWNERSHIP / "TerraFly_Source_to_System_Atlas.pdf"))
    print(str(OWNERSHIP / "TerraFly_Zero_to_Ownership_Bootcamp.pdf"))


if __name__ == "__main__":
    main()
