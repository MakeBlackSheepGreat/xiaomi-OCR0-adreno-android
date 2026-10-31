#!/bin/bash
exec > /root/mesa-build/build-kgsl.log 2>&1
cd /root/mesa-build/mesa-26.2.4
echo "START $(date)"
ninja -C build-kgsl -j 4 || { echo BUILD_FAIL; exit 1; }
echo "BUILD_OK $(date)"
ls -l build-kgsl/src/freedreno/vulkan/*.so build-kgsl/src/freedreno/vulkan/*.json 2>/dev/null
