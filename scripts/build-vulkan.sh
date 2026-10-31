#!/bin/bash
# 编 llama.cpp 的 Vulkan 后端（llama-server）
# 用法: bash build-vulkan.sh [llama.cpp-dir]
# 依赖: cmake, g++, libvulkan-dev, glslang-tools, spirv-headers
set -e
export PATH=/opt/python/bin:$PATH
export CC=/usr/bin/gcc CXX=/usr/bin/g++
cd "${1:-/root/xiaomi-ocr/llama.cpp}"
cmake -B build-vk -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF -DGGML_NATIVE=ON -DGGML_VULKAN=ON
cmake --build build-vk --target llama-server -j 4
ls -l build-vk/bin/llama-server
