# 实际环境

所有数据来自本机实测（`uname` / `/proc` / `/sys` / `vulkaninfo`），不是推测。

## 1. 设备与系统

| 项 | 实测值 |
|---|---|
| SoC | Snapdragon SM8850（骁龙 8 Elite Gen 5，`ro.soc.model=SM8850`，`soc_id=660`） |
| CPU | 8 核，`CPU implementer=0x51`（高通），含 SVE2 / SME / i8mm / bf16 |
| 内存 | 总 14.8 GB，空载可用 6–7 GB，swap 16 GB |
| 系统 | Ubuntu 24.04.5 LTS（proot），glibc 2.39 |
| 内核 | 6.12.69-android16（Android 16 宿主） |
| 存储 | /dev/block/dm-88，969 GB，已用 702 GB |
| 工作区 | /sdcard（模拟存储，**不支持符号链接**）；重度依赖放 /root（ext4） |

## 2. GPU

| 项 | 实测值 |
|---|---|
| GPU | Adreno 840（`/sys/class/kgsl/kgsl-3d0/gpu_model` = `Adreno840v2`） |
| 驱动接口 | `/dev/kgsl-3d0`（`crw-rw-rw-`，可 open）；`/dev/dri/*` 与 `/dev/fastrpc-cdsp` 均 EACCES |
| 系统 Mesa | 25.2.8 —— Turnip 只编了 MSM/DRM 后端，找不到 `/dev/dri` 即失败 |
| 自建 Mesa | **26.2.4**，`-Dvulkan-drivers=freedreno -Dfreedreno-kmds=kgsl`，7 分钟编完 |
| Vulkan 识别 | `deviceName = Adreno (TM) 840`，`driverName = turnip Mesa driver`，API 1.4.354 |
| llama.cpp 视角 | `Vulkan0: Adreno (TM) 840 (11332 MiB, 3911 MiB free)` |

## 3. NPU

Hexagon 存在，但**在 proot 内不可用**：

- `/dev/fastrpc-cdsp` → EACCES
- `libQnnHtp.so` / `libcdsprpc.so` 位于 `/vendor/lib64`，该目录未挂载
- 结论：QNN 只能跑在 Android 应用进程里；本仓库不含 NPU 方案

## 4. 软件栈版本

| 组件 | 版本/来源 |
|---|---|
| llama.cpp | git `0ec4027`（2026-10-30），本机编译 `-DGGML_VULKAN=ON` |
| Mesa (Turnip) | 26.2.4，源码来自清华 TUNA 镜像 |
| Ollama | 0.40.13（只用它 dist 里的 CPU `llama-server` 与投影器 blob） |
| llama-quantize | 由 llama.cpp 源码本机编译，`-j4` |
| Python | 3.12.15；MCP venv 约 428 MB（Pillow / numpy / pypdfium2 / wordfreq） |
| DSH | 0.2.1-rc.4（Web GUI 127.0.0.1:3080） |
| PyArrow | 用于读 OCRBench parquet |

## 5. 磁盘占用（实测）

| 路径 | 大小 |
|---|---|
| /root/xiaomi-ocr | 1.9 GB（仓库 445M + llama.cpp 626M + ollama dist 259M + 模型 517M + venv 428M） |
| /root/mesa-build | 712 MB（源码 + 构建产物 + Turnip .so） |
| /sdcard/projects/xiaomi-ocr | 1.4 GB（含 LFS 里的 716 MB 模型 + 文档） |

## 6. 网络与镜像（这台机器上的有效做法）

| 用途 | 可用方式 | 备注 |
|---|---|---|
| Mesa 源码 | `mirrors.tuna.tsinghua.edu.cn` / `mirrors.ustc.edu.cn` | 66 MB / 2 秒 |
| HF 权重与数据集 | `hf-mirror.com` | 直连 huggingface.co 不稳 |
| GitHub Release | `gh-proxy.com` | 直连常被限速 |
| Ollama registry | 分块 Range 请求 + 校验 sha256 | 原生 `ollama pull` 因 fake-IP DNS 判定“非公网地址”失败 |

## 7. 已知环境限制

1. `/sdcard` 不支持符号链接，`python -m venv` 会报 `Permission denied: 'lib' -> 'lib64'`。
2. proot 内没有 Docker、没有 TeX Live，官方 OmniDocBench 指标（公式 CDM）跑不了。
3. GPU 显存由系统统一管理：上下文 8192 + 2048px 图像会让 Turnip 报 `device lost`。
4. Android 会回收后台内存；常驻 2 GB 以上的进程可能连带把 DSH 主进程拖死（实测发生过两次）。
