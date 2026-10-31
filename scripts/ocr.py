#!/usr/bin/env python3
"""直接用本机 Ollama 调 Xiaomi-OCR-0 做 OCR（绕开 MCP 的 300s 超时）。
用法: ocr.py <图片路径> [max_tokens]  输出 markdown 到 stdout，耗时和用量打到 stderr。
"""
import base64, io, json, os, sys, time, urllib.request
from PIL import Image

def png_bytes(path, max_edge=1600):
    im = Image.open(path).convert("RGB")
    if max(im.size) > max_edge:
        im.thumbnail((max_edge, max_edge), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue(), im.size

PROMPT = ("Extract all information from the main body of the document image and represent it "
          "in markdown format, ignoring headers and footers. Tables should be expressed in OTSL "
          "format, formulas in the document should be represented using LATEX format, and the "
          "parsing should be organized according to the reading order.")

def ocr(path, max_tokens=1200):
    raw, size = png_bytes(path)
    payload = {"model": "longwayxu/xiaomi-ocr-0:bf16",
               "messages": [{"role": "user", "content": [
                   {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(raw).decode()}},
                   {"type": "text", "text": PROMPT}]}],
               "max_tokens": max_tokens, "temperature": 0, "top_p": 0.8}
    base = os.environ.get("XIAOMI_OCR_LOCAL_URL", "http://127.0.0.1:8000/v1").rstrip("/")
    req = urllib.request.Request(base + "/chat/completions",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.time()
    r = json.load(urllib.request.urlopen(req, timeout=3600))
    dt = time.time() - t
    u = r.get("usage") or {}
    print(f"[ocr] {path} {size} -> {dt:.0f}s, completion_tokens={u.get('completion_tokens')}, "
          f"tok/s={round((u.get('completion_tokens') or 0)/max(dt,1),2)}", file=sys.stderr)
    return r["choices"][0]["message"]["content"]

if __name__ == "__main__":
    print(ocr(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1200))