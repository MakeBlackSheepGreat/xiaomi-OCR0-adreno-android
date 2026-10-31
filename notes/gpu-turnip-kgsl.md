# GPU 加速：自建 Turnip(kgsl) 在本机跑通

结论：**Adreno 840 可以在 proot 里被 llama.cpp 使用**，不需要 vendor 驱动。

## 为什么系统自带的 Vulkan 不行

- 系统 Mesa 25.2.8 的 Turnip 只编了 MSM/DRM 后端，走 `/dev/dri/renderD128`；本机该节点是 EACCES。
- 本机 Adreno 的可用节点是 `/dev/kgsl-3d0`（crw-rw-rw-，实测 open 成功）。
- 上游 Mesa 有 `tu_knl_kgsl.cc`，可编出 kgsl 后端；Adreno Gen 8 支持在 Mesa 26.x。

## 复现步骤（已执行）

```bash
# 1. 源码（TUNA 镜像很快）
cd /root/mesa-build
wget https://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports/pool/main/m/mesa/mesa_26.2.4.orig.tar.xz
tar xf mesa_26.2.4.orig.tar.xz

# 2. 依赖
apt-get install -y meson ninja-build bison flex python3-mako spirv-headers
pip install "meson>=1.4"        # 系统 meson 1.3.2 太旧

# 3. 只编 turnip + kgsl
cd mesa-26.2.4
/opt/python/bin/meson setup build-kgsl . -Dbuildtype=release \
  -Dvulkan-drivers=freedreno -Dgallium-drivers= -Dfreedreno-kmds=kgsl \
  -Dglx=disabled -Degl=disabled -Dgbm=disabled -Dllvm=disabled \
  -Dplatforms= -Dopengl=false -Dgles1=disabled -Dgles2=disabled
ninja -C build-kgsl -j 4          # 约 7 分钟

# 4. ICD
cat > /root/mesa-build/turnip-kgsl.json <<EOF
{"file_format_version":"1.0.1","ICD":{"api_version":"1.4.354",
 "library_path":"/root/mesa-build/mesa-26.2.4/build-kgsl/src/freedreno/vulkan/libvulkan_freedreno.so"}}
EOF
VK_ICD_FILENAMES=/root/mesa-build/turnip-kgsl.json vulkaninfo --summary
# → deviceName = Adreno (TM) 840, driverName = turnip Mesa driver, Mesa 26.2.4

# 5. llama.cpp Vulkan 后端
cmake -B build-vk -DGGML_VULKAN=ON -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build build-vk --target llama-server -j 4
build-vk/bin/llama-server --list-devices
# → Vulkan0: Adreno (TM) 840 (11332 MiB, 3911 MiB free)

# 6. 起服务
VK_ICD_FILENAMES=/root/mesa-build/turnip-kgsl.json \
  build-vk/bin/llama-server -m /root/xiaomi-ocr/xiaomi-ocr-q4km.gguf \
  --mmproj <projector.gguf> -ngl 99 --device Vulkan0 -c 4096 \
  --host 127.0.0.1 --port 8000
```

## 实测（Q4_K_M，Adreno 840 vs CPU）

| 任务 | CPU | GPU(Vulkan) | 加速 |
|---|---|---|---|
| 纯文本短句 27 tokens | ~8 tok/s | **34.5 tok/s** | ~4x |
| 千字文页 510×979 | 101 s | **5 s** | ~20x |
| 扫描目录页 707×1000（525 tokens） | 143 s | **18 s（29.6 tok/s）** | ~8x |
| MCP 端到端（千字文，含进程启动） | 105 s | **2.0 s** | ~50x |

识别内容一致（千字文逐字正确；目录页章节页码正确）。

## 注意

- 必须设置 `VK_ICD_FILENAMES`，否则 llama.cpp 找不到 Adreno。
- 视觉部分也会走 GPU（mtmd），这是提速的主要来源之一。
- 模型走 GPU 时占用共享内存，实测可用内存从 4.3 GB 降到 3.4 GB。
- 回退纯 CPU：`start-llama-server.sh --cpu`。
