import io
import os
import time
import base64
import json
import urllib.request
import urllib.parse
import urllib.error
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = 'gemini-2.5-flash-image'
MAX_RETRIES = 3
RETRY_DELAY = 5
FETCH_TIMEOUT = 120

def build_image_url(prompt, w, h, seed):
    encoded = urllib.parse.quote(prompt[:100])
    return f'https://generativelanguage.googleapis.com/placeholder/{encoded}'

def fetch_image_bytes(prompt_text):
    if not GEMINI_API_KEY:
        raise ValueError('GEMINI_API_KEY not set')
    api_url = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}'
    payload = json.dumps({'contents': [{'parts': [{'text': prompt_text}]}], 'generationConfig': {'responseModalities': ['TEXT', 'IMAGE']}}).encode('utf-8')
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(api_url, data=payload, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}, method='POST')
            with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            for part in data['candidates'][0]['content']['parts']:
                if 'inlineData' in part:
                    return base64.b64decode(part['inlineData']['data'])
            raise ValueError('No image in response')
        except (urllib.error.URLError, OSError, KeyError, IndexError, json.JSONDecodeError, ValueError) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    raise ValueError(f'Gemini error: {last_error}')

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
    layer = Image.new('RGBA', img.size, (0,0,0,0))
    draw = ImageDraw.Draw(layer)
    bbox = draw.textbbox((0,0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    pad = int(fs*0.5)
    W, H = img.size
    pos_map = {'bottom-right': (W-tw-pad, H-th-pad), 'bottom-left': (pad, H-th-pad), 'top-right': (W-tw-pad, pad), 'top-left': (pad, pad), 'center': ((W-tw)//2, (H-th)//2)}
    x, y = pos_map.get(position, pos_map['bottom-right'])
    draw.text((x+2,y+2), text, font=font, fill=(0,0,0,int(180*opacity)))
    draw.text((x,y), text, font=font, fill=(255,255,255,int(255*opacity)))
    result = Image.alpha_composite(img, layer).convert('RGB')
    out = io.BytesIO()
    result.save(out, format='PNG')
    return out.getvalue()
