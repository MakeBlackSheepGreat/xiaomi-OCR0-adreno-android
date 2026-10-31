#!/bin/bash
# 编 Mesa/Turnip（kgsl 后端）—— Android 上 Adreno 唯一可用的开源 Vulkan 驱动
# 用法: bash build-turnip-kgsl.sh [mesa-src-dir]
# 源码: https://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/pool/main/m/mesa/mesa_26.2.4.orig.tar.xz
# 依赖: meson>=1.4 (pip) ninja bison flex python3-mako
set -e
cd "${1:-/root/mesa-build/mesa-26.2.4}"
/opt/python/bin/meson setup build-kgsl . -Dbuildtype=release \
  -Dvulkan-drivers=freedreno -Dgallium-drivers= -Dfreedreno-kmds=kgsl \
  -Dglx=disabled -Degl=disabled -Dgbm=disabled -Dllvm=disabled \
  -Dplatforms= -Dopengl=false -Dgles1=disabled -Dgles2=disabled
ninja -C build-kgsl -j 4
ls -l build-kgsl/src/freedreno/vulkan/libvulkan_freedreno.so
