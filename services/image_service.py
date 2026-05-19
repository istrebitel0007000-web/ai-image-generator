import io
import urllib.request
import urllib.parse

from PIL import Image, ImageDraw, ImageFont, ImageEnhance


def build_image_url(prompt, w, h, seed):
    encoded = urllib.parse.quote(prompt)
    return (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={w}&height={h}&seed={seed}&nologo=true&enhance=true"
    )


def fetch_image_bytes(image_url):
    req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def upscale_image(image_data, scale=2):
    img   = Image.open(io.BytesIO(image_data))
    new_w = img.width * scale
    new_h = img.height * scale
    up    = img.resize((new_w, new_h), Image.LANCZOS)
    up    = ImageEnhance.Sharpness(up).enhance(1.5)
    up    = ImageEnhance.Contrast(up).enhance(1.1)
    out   = io.BytesIO()
    up.save(out, format="PNG", optimize=True)
    return out.getvalue(), new_w, new_h


def add_watermark(image_data, text="AI Generated", position="bottom-right",
                  opacity=0.6, size="medium"):
    img      = Image.open(io.BytesIO(image_data)).convert("RGBA")
    size_map = {"small": 0.03, "medium": 0.045, "large": 0.06}
    fs       = max(20, int(min(img.width, img.height) * size_map.get(size, 0.045)))
    font     = None
    for fp in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]:
        try:
            font = ImageFont.truetype(fp, fs)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw  = ImageDraw.Draw(layer)
    bbox  = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad   = int(fs * 0.5)
    W, H  = img.size
    pos_map = {
        "bottom-right": (W - tw - pad, H - th - pad),
        "bottom-left":  (pad, H - th - pad),
        "top-right":    (W - tw - pad, pad),
        "top-left":     (pad, pad),
        "center":       ((W - tw) // 2, (H - th) // 2),
    }
    x, y = pos_map.get(position, pos_map["bottom-right"])
    draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, int(180 * opacity)))
    draw.text((x, y),         text, font=font, fill=(255, 255, 255, int(255 * opacity)))
    result = Image.alpha_composite(img, layer).convert("RGB")
    out    = io.BytesIO()
    result.save(out, format="PNG")
    return out.getvalue()
