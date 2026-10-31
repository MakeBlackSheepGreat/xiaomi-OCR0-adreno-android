#!/bin/bash
# 启动本地推理服务：Q4_K_M 模型 + 开源 Turnip(kgsl) 走 Adreno 840 GPU
# 需要 <repo>/scripts/turnip-kgsl.json（自建 Mesa 26.2.4 freedreno/msm→kgsl）
D=/root/xiaomi-ocr
MODEL=$D/xiaomi-ocr-q4km.gguf
PROJ=$D/ollama/models/blobs/sha256-aa8b9bed474e2f5c34356c15e25c35a82f0da55ba6e76d36f710d6acdb82e2a8
LOG=$D/logs/llama-server.log
GPU=1
[ "$1" = "--cpu" ] && GPU=0

for p in $(pgrep -f "llama-server"); do kill $p 2>/dev/null; done
sleep 2

if [ "$GPU" = "1" ] && [ -f <repo>/scripts/turnip-kgsl.json ]; then
  export VK_ICD_FILENAMES=<repo>/scripts/turnip-kgsl.json
  BIN=$D/llama.cpp/build-vk/bin/llama-server
  EXTRA="-ngl 99 --device Vulkan0"
  echo "using Vulkan (Adreno) backend"
else
  BIN=$D/ollama/dist/lib/ollama/llama-server
  EXTRA=""
  echo "using CPU backend"
fi

setsid nohup $BIN -m $MODEL --mmproj $PROJ $EXTRA \
  --host 127.0.0.1 --port 8000 -c 4096 --no-warmup \
  > $LOG 2>&1 < /dev/null &
for i in $(seq 1 90); do
  sleep 2
  if python3 -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2)" 2>/dev/null; then
    echo "llama-server ready on :8000"; exit 0
  fi
done
echo "startup timeout"; tail -10 $LOG
