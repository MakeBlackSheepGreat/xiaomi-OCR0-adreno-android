#!/bin/bash
# 编 llama-quantize（本机把 BF16 GGUF 量化成 Q4_K_M 用，量化本身 17 秒）
# 用法: bash build-quantize.sh [llama.cpp-dir]
set -e
export PATH=/opt/python/bin:$PATH
export CC=/usr/bin/gcc CXX=/usr/bin/g++
cd "${1:-/root/xiaomi-ocr/llama.cpp}"
cmake -B build -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF -DGGML_NATIVE=ON
cmake --build build --target llama-quantize -j 4
ls -l build/bin/llama-quantize
# 量化: build/bin/llama-quantize <bf16.gguf> out-q4km.gguf Q4_K_M
