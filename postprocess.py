from __future__ import annotations

from pathlib import Path
from typing import List

import pypdfium2 as pdfium
from PIL import Image


def _remove_watermark(img: Image.Image) -> Image.Image:
    """Lighten near-white areas to reduce watermarks."""
    gray = img.convert('L')
    cleaned = gray.point(lambda x: 255 if x > 200 else x)
    return cleaned.convert('RGB')


def postprocess_storybooks(pdf_paths: List[Path], output_path: Path, logo_path: Path) -> Path:
    """Merge PDFs, desaturate interior pages, remove watermarks and add logo."""
    images: List[Image.Image] = []
    first_page = True
    for path in pdf_paths:
        pdf = pdfium.PdfDocument(str(path))
        for page_index, page in enumerate(pdf):
            pil = page.render(scale=1).to_pil()
            if first_page and page_index == 0:
                # cover: keep colors and add logo
                if logo_path and logo_path.exists():
                    logo = Image.open(logo_path).convert('RGBA')
                    lw, lh = logo.size
                    pw, ph = pil.size
                    factor = min(pw * 0.3 / lw, ph * 0.3 / lh)
                    logo = logo.resize((int(lw * factor), int(lh * factor)))
                    pil.paste(logo, (10, 10), logo)
            else:
                pil = _remove_watermark(pil)
            images.append(pil.convert('RGB'))
            first_page = False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if images:
        images[0].save(output_path, save_all=True, append_images=images[1:], format='PDF')
    return output_path
