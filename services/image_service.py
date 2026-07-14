import io
import os
import time
import base64
import json
import urllib.request
import urllib.parse
import urllib.error
from dotenv import load_dotenv
load_dotenv()
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

# ── xAI / Grok config ────────────────────────────────────────────────
# NOTE: "aurora" is the name of xAI's underlying image-model architecture,
# not something you pass as "model" in the API. The real, current,
# callable model (verified against xAI's live docs) is:
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')  # kept only so any other
                                                    # file that still imports
                                                    # this name doesn't crash
XAI_API_KEY      = os.getenv('XAI_API_KEY', '')
GROK_IMAGE_MODEL = os.getenv('GROK_IMAGE_MODEL', 'grok-imagine-image-quality')
XAI_IMAGES_URL   = 'https://api.x.ai/v1/images/generations'

MAX_RETRIES   = 3
RETRY_DELAY   = 5
FETCH_TIMEOUT = 120

# xAI's image API takes aspect_ratio + resolution, NOT width/height.
SIZE_ASPECT_RATIOS = {
    "square":    "1:1",
    "portrait":  "3:4",
    "landscape": "16:9",
    "wide":      "2:1",
}


def build_image_url(prompt, w, h, seed):
    # Legacy/unused helper, kept only so nothing that still imports it breaks.
    encoded = urllib.parse.quote(prompt[:100])
    return f'https://api.x.ai/placeholder/{encoded}'


def fetch_image_bytes(prompt_text, size_key="square"):
    """
    Generate an image via xAI's Grok image model
    (grok-imagine-image-quality, built on xAI's "Aurora" architecture).
    Returns raw PNG bytes.

    Raises ValueError for API-level failures (bad key, bad model, bad
    request, empty/malformed response) so the REAL reason reaches the
    user instead of a misleading "service unavailable, try again" message.
    Only raises OSError / urllib.error.URLError for genuine network-level
    failures — matching what generate_service.py's except blocks expect.
    """
    if not XAI_API_KEY:
        raise ValueError('XAI_API_KEY not set')

    aspect_ratio = SIZE_ASPECT_RATIOS.get(size_key, "1:1")
    payload = json.dumps({
        'model':           GROK_IMAGE_MODEL,
        'prompt':          prompt_text,
        'n':               1,
        'response_format': 'b64_json',
        'aspect_ratio':    aspect_ratio,
        'resolution':      '1k',
    }).encode('utf-8')

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(
                XAI_IMAGES_URL, data=payload,
                headers={
                    'Content-Type':  'application/json',
                    'Authorization': f'Bearer {XAI_API_KEY}',
                },
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            b64_data = data['data'][0]['b64_json']
            return base64.b64decode(b64_data)

        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode('utf-8')
            except Exception:
                body = ''
            api_error = ValueError(f'xAI API error {e.code}: {body[:200] or e.reason}')
            if e.code == 429 or e.code >= 500:
                # Rate-limited or server-side issue — worth a retry.
                last_error = api_error
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
            # Bad key / bad model / bad request — will fail identically
            # every time, so surface it immediately instead of retrying.
            raise api_error

        except (urllib.error.URLError, OSError, KeyError, IndexError, json.JSONDecodeError) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    raise last_error


def upscale_image(image_data, scale=2):
    img = Image.open(io.BytesIO(image_data))
    new_w, new_h = img.width * scale, img.height * scale
    up = img.resize((new_w, new_h), Image.LANCZOS)
    up = ImageEnhance.Sharpness(up).enhance(1.5)
    up = ImageEnhance.Contrast(up).enhance(1.1)
    out = io.BytesIO()
    up.save(out, format='PNG', optimize=True)
    return out.getvalue(), new_w, new_h


def add_watermark(image_data, text='AI Generated', position='bottom-right', opacity=0.6, size='medium'):
    img = Image.open(io.BytesIO(image_data)).convert('RGBA')
    size_map = {'small': 0.03, 'medium': 0.045, 'large': 0.06}
    fs = max(20, int(min(img.width, img.height) * size_map.get(size, 0.045)))
    font = None
    for fp in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 'C:/Windows/Fonts/arialbd.ttf']:
        try:
            font = ImageFont.truetype(fp, fs); break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    pad = int(fs*0.5)
    W, H = img.size
    pos_map = {'bottom-right': (W-tw-pad, H-th-pad), 'bottom-left': (pad, H-th-pad), 'top-right': (W-tw-pad, pad), 'top-left': (pad, pad), 'center': ((W-tw)//2, (H-th)//2)}
    x, y = pos_map.get(position, pos_map['bottom-right'])
    draw.text((x+2, y+2), text, font=font, fill=(0, 0, 0, int(180*opacity)))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, int(255*opacity)))
    result = Image.alpha_composite(img, layer).convert('RGB')
    out = io.BytesIO()
    result.save(out, format='PNG')
    return out.getvalue()
