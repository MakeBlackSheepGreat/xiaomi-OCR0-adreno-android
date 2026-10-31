#!/bin/bash
export PATH=/opt/python/bin:$PATH
export CC=/usr/bin/gcc CXX=/usr/bin/g++
D=/root/xiaomi-ocr
exec > $D/logs/build-vulkan.log 2>&1
echo "START $(date)"
cd $D/llama.cpp
if [ ! -f build-vk/CMakeCache.txt ]; then
  cmake -B build-vk -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF -DGGML_NATIVE=ON -DGGML_VULKAN=ON -DCMAKE_MAKE_PROGRAM=/usr/bin/make || { echo CMAKE_FAIL; exit 10; }
fi
cmake --build build-vk --target llama-server -j 4 || { echo BUILD_FAIL; exit 11; }
ls -l build-vk/bin/llama-server
echo "DONE $(date)"
