# Xiaomi-OCR-0 on Adreno GPU (Android)

在 Android 手机上用**开源驱动**把 Xiaomi-OCR-0（0.8B OCR 专用 VLM）完整跑起来：Q4_K_M 量化 + Mesa Turnip（kgsl 后端）走 Adreno GPU + llama.cpp，并接入 DSH 的 MCP。

无需 root、无需厂商 SDK、无需 NPU。纯 proot 环境内实测可用。

---

## 目录

- [核心结果](#核心结果)
- [工作原理](#工作原理)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [模型](#模型)
- [从源码构建](#从源码构建)
- [使用](#使用)
- [基准测试](#基准测试)
- [性能特征](#性能特征)
- [已知限制](#已知限制)
- [仓库结构](#仓库结构)
- [复现评测](#复现评测)
- [排错](#排错)
- [文档索引](#文档索引)
- [许可与致谢](#许可与致谢)

## 核心结果

| 场景 | CPU | GPU（Adreno 840） | 加速 |
|---|---|---|---|
| 扫描件整页 OCR（707×1000） | 143 s | **18 s**（29.6 tok/s） | 8× |
| 书法页（510×979） | 101 s | **5 s** | 20× |
| MCP 端到端单次调用 | 105 s | **2.0 s** | 50× |
| 纯文本生成 | ~8 tok/s | **34.5 tok/s** | 4× |

| 指标 | 值 |
|---|---|
| 模型体积 | BF16 1.56 GB → Q4_K_M **518 MB**（量化耗时 17 s） |
| OCRBench（1000 题） | **78.30%**（官方 BF16+vLLM 84.6，差 −6.3） |
| 扫描书页 vs 人工转录 | 91.6% / 98.7% 字符相似度 |

> OCRBench 的 6.3 分差距混合了量化、后端、图像分辨率、提示词与计分口径，**不能**视为纯量化损失，详见 [docs/benchmark-ocrbench.md](docs/benchmark-ocrbench.md)。

## 工作原理

```text
图片 / PDF ──渲染/缩放──▶ ocr.py / MCP server
                              │  OpenAI 兼容请求（base64 PNG）
                              ▼
                    llama-server (Vulkan 后端)
                              │  Vulkan 1.4
                              ▼
          Mesa Turnip (freedreno + kgsl)  ──▶  /dev/kgsl-3d0  ──▶  Adreno GPU
```

**关键点**：Android 的 Adreno 不用 `/dev/dri`，而是 `/dev/kgsl-3d0`。发行版自带的 Mesa 只编译了 MSM/DRM 后端，因此必定失败。
用 Mesa ≥ 26 以 `-Dfreedreno-kmds=kgsl` 自编 Turnip 后，`vulkaninfo` 即可枚举出 `Adreno (TM) 840`。

## 环境要求

| 项 | 实测环境 |
|---|---|
| SoC | Snapdragon 8 Elite Gen 5（SM8850），8 核，含 SVE2 / SME / i8mm |
| 内存 | 14.8 GB（proot 内可用 4–7 GB） |
| 系统 | Ubuntu 24.04（proot），glibc 2.39，Android 16 宿主内核 6.12 |
| GPU 节点 | `/dev/kgsl-3d0` 可读写；`/dev/dri`、`/dev/fastrpc-*` 通常不可访问 |
| 软件 | Mesa 26.2.4（自编）、llama.cpp（本机编译）、Python 3.10+ |

其他 Adreno 机型理论上同理，但需要对应 Mesa 版本支持该 GPU（Adreno Gen 8 需 Mesa 26+）。

## 快速开始

```bash
# 1) 取模型（约 716 MB）
gh release download v1.0.0 -R <owner>/<repo> -D models
#    或直接用仓库 models/ 下的 LFS 文件

# 2) 起推理服务（GPU；无 Turnip 时加 --cpu）
bash scripts/start-llama-server.sh

# 3) 识别一张图
python3 scripts/ocr.py page.png

# 4) 大图分块（推荐用于整页文档）
python3 scripts/ocr_page.py big_page.png --bands 3 --out out.md
```

## 模型

| 文件 | 大小 | 说明 |
|---|---|---|
| `xiaomi-ocr0-q4_k_m.gguf` | 518 MB | 文本模型，Q4_K_M |
| `xiaomi-ocr0-mmproj-f16.gguf` | 197 MB | 视觉投影器，**保持 F16** |

获取方式（任选）：

1. 仓库 `models/`（Git LFS，716 MB；注意 GitHub 免费 LFS 配额为 1 GB 存储 / 1 GB 月流量）；
2. Release 附件 `v1.0.0`；
3. 自行生成：`llama-quantize <bf16-text.gguf> out.gguf Q4_K_M`，投影器不要量化。

## 从源码构建

```bash
# Mesa / Turnip（kgsl 后端），约 7 分钟
bash scripts/build-turnip-kgsl.sh /path/to/mesa-26.2.4

# llama.cpp Vulkan 后端，约 6 分钟
bash scripts/build-vulkan.sh /path/to/llama.cpp

# llama-quantize（可选，用于自行量化）
bash scripts/build-quantize.sh /path/to/llama.cpp
```

Mesa 源码建议用镜像（TUNA/USTC 约 30 MB/s）。依赖：`meson>=1.4`、`ninja`、`bison`、`flex`、`python3-mako`、`libvulkan-dev`、`glslang-tools`、`spirv-headers`。

## 使用

**命令行**

| 命令 | 作用 |
|---|---|
| `scripts/start-llama-server.sh` | 启动服务（GPU） |
| `scripts/start-llama-server.sh --cpu` | 纯 CPU 回退 |
| `scripts/ocr.py <img> [max_tokens]` | 整图 Markdown |
| `scripts/ocr_page.py <img> --bands N` | 横向分块，适合长文档 |

**MCP（DSH）**

推理服务启动后，通过 `dsh-mcp-client` 暴露四个工具：

| 工具 | 用途 |
|---|---|
| `mcp__xiaomi-ocr__ocr_image` | 单图 → Markdown（`mode="page"`） |
| `mcp__xiaomi-ocr__ocr_pdf` | PDF 逐页 |
| `mcp__xiaomi-ocr__kie_image` | 关键字段抽取（JSON） |
| `mcp__xiaomi-ocr__vqa_image` | 针对文档图提问 |

配置片段见 [docs/code.md](docs/code.md#4-mcp-接入dsh)。

## 基准测试

**OCRBench 全量 1000 题**（Q4_K_M + Adreno GPU + 简洁作答提示）：

| 计分口径 | 本机 | 官方 | 差 |
|---|---|---|---|
| 数学感知归一化 | **78.30%** | 84.6 | −6.3 |
| 严格逐字符 | 75.90% | — | −8.7 |

| 类别 | 本机 | 题数 |
|---|---|---|
| 非语义 / 常规 / 非常规 / 艺术字 | 98 / 96 / 96 / 94% | 各 50 |
| 手写文本 | 82% | 50 |
| 数字串 | 80% | 50 |
| 关键信息抽取 | 78% | 200 |
| 场景文本 VQA | 75.5% | 200 |
| 文档 VQA | 70% | 200 |
| 手写公式 | 63% | 100 |

结论：印刷体识别基本无损（94–98%），损失集中在文档理解与公式，主要来自 **1024px 降采样** 与 GPU 显存上限，而非量化本身（未做 BF16 对照，无法拆分）。**数字仅供参考。**

**真实扫描书页**：150 dpi 整页约 35–40 s，与人工转录字符相似度 91.6% / 98.7%，脚注与引用角标均可识别。

## 性能特征

| 项 | 数值 |
|---|---|
| 生成速度（GPU，Q4） | 29–34 tok/s |
| 生成速度（CPU，Q4） | 3.7–6.5 tok/s |
| 视觉编码 | 约 5–20 s/图（随分辨率线性增长） |
| 常驻内存 | 服务约 0.6 GB；连续请求会累积（约 40–75 MB/次） |
| GPU 显存 | 报告 11.3 GB 可用，实际安全线约 1–2 GB |

## 已知限制

1. **NPU 不可用**：`/dev/fastrpc-cdsp` 无权限、`/vendor` 未挂载，QNN 只能在 Android 应用进程内运行；本项目不涉及。
2. **region（版面切分）不可用**：PaddlePaddle 在本机 ARM64 proot 下推理段错误，相关依赖已移除。
3. **GPU 显存有限**：`-c 8192` + 2048px 图像会 `device lost`；建议上下文 ≤4096、图像长边 ≤1600。
4. **性能随内存压力剧烈变化**：被系统换页时生成速度可从 30 tok/s 掉到 1 tok/s 以下。
5. **不是官方复现**：官方为 BF16 + vLLM；本项目的分数与速度来自不同栈。

## 仓库结构

```text
├── docs/                 环境、代码、评测三份文档
├── models/               LFS：Q4_K_M + mmproj
├── notes/                后端选型调研、GPU 复现步骤
├── scripts/              启动 / OCR / 分块 / 构建 / 评测
├── verification/         实测输出与标准答案对照
│   └── ocrbench/         1000 题逐题结果
└── SKILL.md              上游安装说明（存档）
```

## 复现评测

```bash
hf download echo840/OCRBench --repo-type dataset --local-dir ./ocrbench
bash scripts/start-llama-server.sh
python3 scripts/ocrbench_eval.py      # 推理，断点续跑
python3 scripts/ocrbench_scorer.py    # 计分
```

## 排错

| 现象 | 原因 | 处理 |
|---|---|---|
| `vk::DeviceLostError` | 上下文/图像过大 | 降 `-c`、降分辨率、重启服务 |
| `vulkaninfo` 找不到 GPU | 用了发行版 Turnip（MSM） | 按上文自编 kgsl 版并设 `VK_ICD_FILENAMES` |
| `python -m venv` 报 Permission denied | 目录在 `/sdcard`（不支持软链） | 换到 `/root` |
| `ollama pull` 报非公网地址 | fake-IP DNS 被安全校验拦截 | 用分块 HTTP 拉 blob |
| MCP 工具不出现 | 配置后未重启 DSH | 重启宿主进程 |

## 文档索引

| 文档 | 内容 |
|---|---|
| [docs/environment.md](docs/environment.md) | 实际环境全量数据与限制 |
| [docs/code.md](docs/code.md) | 数据流、脚本说明、MCP 配置、已知问题 |
| [docs/benchmark-ocrbench.md](docs/benchmark-ocrbench.md) | 评测方法、结果、8 条局限性 |
| [notes/gpu-turnip-kgsl.md](notes/gpu-turnip-kgsl.md) | GPU 加速逐步复现 |
| [notes/backend-research.md](notes/backend-research.md) | SGLang / vLLM / Ollama / Paddle 选型对比 |

## 许可与致谢

- 模型：[SeerRay-Lab/Xiaomi-OCR-0](https://huggingface.co/SeerRay-Lab/Xiaomi-OCR-0)（权重许可见上游）
- 运行时：[ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)（MIT）
- GPU 驱动：[Mesa3D](https://gitlab.freedesktop.org/mesa/mesa)（MIT）
- 数据集：[echo840/OCRBench](https://huggingface.co/datasets/echo840/OCRBench)
- 本仓库脚本：[MIT](LICENSE)
