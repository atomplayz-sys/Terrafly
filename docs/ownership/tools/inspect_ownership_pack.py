from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
OWNERSHIP = ROOT / "docs" / "ownership"


def font(size: int, bold: bool = False):
    candidates = [Path("C:/Windows/Fonts/arialbd.ttf") if bold else Path("C:/Windows/Fonts/arial.ttf")]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def contact_sheets(folder: Path, prefix: str):
    pages = sorted(folder.glob("page-*.png"))
    thumb_w, thumb_h = 420, 594
    cols, rows = 3, 3
    margin, label_h = 24, 42
    out = []
    for group_index in range(0, len(pages), cols * rows):
        group = pages[group_index : group_index + cols * rows]
        canvas = Image.new("RGB", (cols * thumb_w + (cols + 1) * margin, rows * (thumb_h + label_h) + (rows + 1) * margin), "#DDE7E4")
        draw = ImageDraw.Draw(canvas)
        for idx, page in enumerate(group):
            row, col = divmod(idx, cols)
            x = margin + col * (thumb_w + margin)
            y = margin + row * (thumb_h + label_h + margin)
            image = Image.open(page).convert("RGB")
            image.thumbnail((thumb_w, thumb_h))
            px = x + (thumb_w - image.width) // 2
            py = y + (thumb_h - image.height) // 2
            draw.rectangle((x - 2, y - 2, x + thumb_w + 2, y + thumb_h + 2), fill="white", outline="#6A817B", width=2)
            canvas.paste(image, (px, py))
            page_number = int(re.search(r"(\d+)$", page.stem).group(1))
            draw.text((x, y + thumb_h + 7), f"Page {page_number}", font=font(24, bold=True), fill="#12302B")
        sheet = OWNERSHIP / "rendered-pages" / f"{prefix}-contact-{group_index // 9 + 1:02d}.png"
        canvas.save(sheet)
        out.append(str(sheet))
    return out


def inspect_pdf(pdf_path: Path):
    reader = PdfReader(str(pdf_path))
    result = {"file": pdf_path.name, "pages": len(reader.pages), "pages_detail": [], "links": []}
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        annotations = page.get("/Annots", [])
        links = 0
        for annotation_ref in annotations:
            annotation = annotation_ref.get_object()
            action = annotation.get("/A")
            if action and action.get("/URI"):
                result["links"].append(str(action.get("/URI")))
                links += 1
        result["pages_detail"].append({
            "page": index,
            "text_chars": len(text.strip()),
            "links": links,
            "replacement_marks": text.count("?"),
        })
    result["blank_pages"] = [p["page"] for p in result["pages_detail"] if p["text_chars"] < 25]
    result["unique_external_links"] = len(set(result["links"]))
    return result


def main():
    atlas_sheets = contact_sheets(OWNERSHIP / "rendered-pages" / "atlas-v2", "atlas-v2")
    bootcamp_sheets = contact_sheets(OWNERSHIP / "rendered-pages" / "bootcamp-v2", "bootcamp-v2")
    report = {
        "atlas": inspect_pdf(OWNERSHIP / "TerraFly_Source_to_System_Atlas.pdf"),
        "bootcamp": inspect_pdf(OWNERSHIP / "TerraFly_Zero_to_Ownership_Bootcamp.pdf"),
        "contact_sheets": atlas_sheets + bootcamp_sheets,
    }
    (OWNERSHIP / "rendered-pages" / "inspection-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "atlas_pages": report["atlas"]["pages"],
        "atlas_blank": report["atlas"]["blank_pages"],
        "atlas_links": report["atlas"]["unique_external_links"],
        "bootcamp_pages": report["bootcamp"]["pages"],
        "bootcamp_blank": report["bootcamp"]["blank_pages"],
        "bootcamp_links": report["bootcamp"]["unique_external_links"],
        "sheets": len(report["contact_sheets"]),
    }, indent=2))


if __name__ == "__main__":
    main()
