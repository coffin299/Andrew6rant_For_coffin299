"""Face-crop coffin299.png and embed ultra HQ colored ASCII into SVG banners."""
from __future__ import annotations

import base64
import io
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
IMG = ROOT / "coffin299.png"
BANNER = ROOT / "coffin299_banner.png"
FACE = ROOT / "coffin299_face.png"
AA_PNG = ROOT / "coffin299_aa.png"
AA_HQ = ROOT / "coffin299_aa_hq.png"

# Left panel size — stays left of the text column at x=390
WIDTH, HEIGHT = 340, 470
X, Y = 20, 30

# Face crop on 1920x1080 source (ears high + peace sleeve in frame)
FACE_BOX = (0.26, 0.0, 0.64, 0.95)
FACE_CENTER = (0.42, 0.22)

# Dense → sparse: on dark bg, denser glyph = brighter pixel
CHARS = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
FONT_PATH = Path(r"C:\Windows\Fonts\consola.ttf")


def crop_face(src: Image.Image) -> Image.Image:
    w, h = src.size
    l, t, r, b = FACE_BOX
    return src.crop((int(w * l), int(h * t), int(w * r), int(h * b)))


def fitted_face(size: tuple[int, int] = (WIDTH, HEIGHT)) -> Image.Image:
    src = Image.open(IMG).convert("RGBA")
    face = crop_face(src)
    face.save(FACE, "PNG", optimize=True)
    fitted = ImageOps.fit(
        face, size, method=Image.Resampling.LANCZOS, centering=FACE_CENTER
    )
    if size == (WIDTH, HEIGHT):
        fitted.save(BANNER, "PNG", optimize=True)
    return fitted.convert("RGB")


def _cell_size(font: ImageFont.FreeTypeFont, line_pad: int) -> tuple[int, int]:
    probe = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(probe)
    bbox = draw.textbbox((0, 0), "M", font=font)
    return max(1, bbox[2] - bbox[0]), max(1, bbox[3] - bbox[1] + line_pad)


def render_colored_aa(
    src: Image.Image,
    *,
    font_size: int = 6,
    scale: int = 2,
    bg: tuple[int, int, int] = (22, 27, 34),
    contrast: float = 1.35,
    color: float = 1.25,
    out_size: tuple[int, int] | None = None,
) -> Image.Image:
    """Ultra-dense colored ASCII on a dark background."""
    font = ImageFont.truetype(str(FONT_PATH), font_size * scale)
    cell_w, cell_h = _cell_size(font, line_pad=scale)

    target_w = (out_size or (WIDTH, HEIGHT))[0] * scale
    target_h = (out_size or (WIDTH, HEIGHT))[1] * scale
    cols = max(40, target_w // cell_w)
    rows = max(40, target_h // cell_h)

    sample = src.resize((cols, rows), Image.Resampling.LANCZOS)
    sample = ImageEnhance.Contrast(sample).enhance(contrast)
    sample = ImageEnhance.Color(sample).enhance(color)
    gray = ImageOps.autocontrast(sample.convert("L"), cutoff=1)

    canvas = Image.new("RGB", (cols * cell_w, rows * cell_h), bg)
    draw = ImageDraw.Draw(canvas)
    n = len(CHARS) - 1
    px = sample.load()
    gx = gray.load()

    for y in range(rows):
        for x in range(cols):
            r, g, b = px[x, y]
            ch = CHARS[int(gx[x, y] / 255 * n)]
            if ch == " ":
                continue
            draw.text((x * cell_w, y * cell_h), ch, font=font, fill=(r, g, b))

    final = out_size or (WIDTH, HEIGHT)
    return canvas.resize(final, Image.Resampling.LANCZOS)


def to_jpeg_bytes(img: Image.Image, quality: int = 93) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def portrait_block(jpeg_bytes: bytes) -> str:
    b64 = base64.b64encode(jpeg_bytes).decode("ascii")
    return f"""<defs>
<clipPath id="portraitClip">
<rect x="{X}" y="{Y}" width="{WIDTH}" height="{HEIGHT}" rx="12"/>
</clipPath>
</defs>
<image href="data:image/jpeg;base64,{b64}" x="{X}" y="{Y}" width="{WIDTH}" height="{HEIGHT}" clip-path="url(#portraitClip)" preserveAspectRatio="xMidYMid slice"/>"""


def replace_portrait(svg_path: Path, block: str) -> None:
    text = svg_path.read_text(encoding="utf-8")
    profile = text.find('<text x="390"')
    if profile < 0:
        raise SystemExit(f"profile panel not found in {svg_path.name}")
    rect_end = text.find("/>", text.find("</style>")) + 2
    new = text[:rect_end] + "\n" + block + "\n" + text[profile:]
    new = re.sub(
        r'<text x="15" y="30"[^>]*>.*?</text>\n?',
        "",
        new,
        count=1,
        flags=re.DOTALL,
    )
    svg_path.write_text(new, encoding="utf-8")


def main() -> None:
    face = fitted_face()

    # Panel AA → SVG embed
    aa = render_colored_aa(face, font_size=6, scale=3, contrast=1.4, color=1.3)
    aa.save(AA_PNG, "PNG", optimize=True)

    # Standalone ultra HQ (2x panel)
    face_hq = fitted_face((WIDTH * 2, HEIGHT * 2))
    aa_hq = render_colored_aa(
        face_hq,
        font_size=5,
        scale=3,
        contrast=1.4,
        color=1.35,
        out_size=(WIDTH * 2, HEIGHT * 2),
    )
    aa_hq.save(AA_HQ, "PNG", optimize=True)

    block = portrait_block(to_jpeg_bytes(aa))
    for name in ("light_mode.svg", "dark_mode.svg"):
        replace_portrait(ROOT / name, block)
        print(f"Updated {name}")

    print(f"AA:    {AA_PNG.name}  {aa.size}  {AA_PNG.stat().st_size:,} bytes")
    print(f"AA HQ: {AA_HQ.name}  {aa_hq.size}  {AA_HQ.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
