#!/bin/bash
set -e
export PATH=/opt/python/bin:$PATH
export CC=/usr/bin/gcc CXX=/usr/bin/g++
cd /root/xiaomi-ocr/llama.cpp
rm -rf build
cmake -B build -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF -DGGML_NATIVE=ON -DCMAKE_MAKE_PROGRAM=/usr/bin/make 2>&1 | tail -5
cmake --build build --target llama-quantize -j 8 2>&1 | tail -6
ls -l build/bin/llama-quantize
