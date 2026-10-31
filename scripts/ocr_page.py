#!/usr/bin/env python3
"""分块 OCR：把大图切成若干横向条带，逐块识别后拼接。
大图整页送模型时视觉塔太慢（748 tokens ≈ 4min），切块能显著缩短单次耗时并避免超时。
用法: ocr_page.py <图片> [--bands 3] [--overlap 60] [--out out.md]
"""
import argparse, base64, io, json, os, sys, time, urllib.request
from PIL import Image

BASE = os.environ.get("XIAOMI_OCR_LOCAL_URL", "http://127.0.0.1:8000/v1").rstrip("/")
PROMPT = ("Extract all information from the main body of the document image and represent it "
          "in markdown format, ignoring headers and footers. Tables should be expressed in OTSL "
          "format, formulas in the document should be represented using LATEX format, and the "
          "parsing should be organized according to the reading order.")

def call(png_bytes, max_tokens=900):
    payload = {"model": os.environ.get("XIAOMI_OCR_MODEL", "local"),
               "messages": [{"role": "user", "content": [
                   {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png_bytes).decode()}},
                   {"type": "text", "text": PROMPT}]}],
               "max_tokens": max_tokens, "temperature": 0, "top_p": 0.8}
    req = urllib.request.Request(BASE + "/chat/completions", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.time()
    r = json.load(urllib.request.urlopen(req, timeout=3600))
    return r["choices"][0]["message"]["content"].strip(), time.time() - t, (r.get("usage") or {})

def png(im):
    b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image"); ap.add_argument("--bands", type=int, default=3)
    ap.add_argument("--overlap", type=int, default=60)
    ap.add_argument("--max-edge", type=int, default=1400)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    im = Image.open(a.image).convert("RGB")
    if max(im.size) > a.max_edge:
        im.thumbnail((a.max_edge, a.max_edge), Image.LANCZOS)
    W, H = im.size
    step = max(1, H // a.bands)
    parts, t_all = [], 0.0
    for i in range(a.bands):
        top = max(0, i * step - (a.overlap if i else 0))
        bot = min(H, (i + 1) * step + (a.overlap if i < a.bands - 1 else 0))
        crop = im.crop((0, top, W, bot))
        txt, dt, usage = call(png(crop))
        t_all += dt
        print(f"[band {i+1}/{a.bands}] y={top}-{bot} {dt:.0f}s in={usage.get('prompt_tokens')} out={usage.get('completion_tokens')}", file=sys.stderr)
        parts.append(txt)
    out = "\n\n".join(parts)
    if a.out:
        open(a.out, "w").write(out)
        print(f"total {t_all:.0f}s -> {a.out}", file=sys.stderr)
    else:
        print(out)

if __name__ == "__main__":
    main()
