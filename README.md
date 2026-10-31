# xiaomi-OCR0-adreno-android

Xiaomi-OCR-0（0.8B OCR 专用 VLM）在**骁龙 8 Elite Gen 5 手机**上的本地部署：Q4 量化 + 自建 **Turnip(kgsl)** 走 Adreno GPU + llama.cpp + DSH MCP 集成。

## 亮点（全部本机实测）

| 项 | 结果 |
|---|---|
| 扫描件整页 OCR（707×1000） | **18 s**（CPU 143 s） |
| 千字文页（510×979） | **5 s**（CPU 101 s） |
| MCP 端到端单次调用 | **2.0 s**（CPU 105 s） |
| GPU 推理速度 | 29.6 tok/s（纯文本 34.5 tok/s） |
| 模型体积 | BF16 1.56 GB → **Q4_K_M 518 MB**（量化 17 秒） |
| OCRBench（1000 题） | **78.30%**，官方 84.6，差 −6.3（含后端/分辨率/提示词差异，见下） |

关键发现：系统自带 Mesa 25.2 的 Turnip 只有 MSM 后端，用不了 Android 的 `/dev/kgsl-3d0`；
用 Mesa **26.2.4** 以 `-Dfreedreno-kmds=kgsl` 自编后，`vulkaninfo` 直接识别出 `Adreno (TM) 840`。

## 快速开始

```bash
# 1. 起服务（GPU；没有 Turnip 时用 --cpu）
bash scripts/start-llama-server.sh

# 2. 单图 OCR
python3 scripts/ocr.py page.png

# 3. 大图分块
python3 scripts/ocr_page.py big_page.png --bands 3 --out out.md
```

模型获取：`gh release download v1.0.0 -R MakeBlackSheepGreat/xiaomi-OCR0-adreno-android -D models`，
或直接用仓库 `models/` 下的 LFS 文件。

## 文档

| 文档 | 内容 |
|---|---|
| [docs/environment.md](docs/environment.md) | 实际环境：SoC/GPU/NPU、内核、版本、磁盘、镜像源、限制 |
| [docs/code.md](docs/code.md) | 数据流、脚本逐个说明、MCP 配置、已知问题 |
| [docs/benchmark-ocrbench.md](docs/benchmark-ocrbench.md) | OCRBench 测法、结果、**8 条局限性** |
| [notes/gpu-turnip-kgsl.md](notes/gpu-turnip-kgsl.md) | GPU 加速完整复现步骤 |
| [notes/backend-research.md](notes/backend-research.md) | 后端选型调研（SGLang/vLLM/Ollama/Paddle） |
| [verification/real-pages/REPORT.md](verification/real-pages/REPORT.md) | 真实扫描书页验证（91.6% / 98.7%） |

## 仓库结构

```text
├── docs/                 环境、代码、评测文档
├── models/               LFS：Q4_K_M 518 MB + mmproj 197 MB
├── notes/                后端调研与 GPU 复现
├── scripts/              启动、OCR、构建、评测脚本
├── verification/         实测输出与标准答案对照
│   └── ocrbench/         1000 题逐题结果
└── SKILL.md              官方安装说明（存档）
```

## 局限（先看这段）

- **NPU 用不了**：`/dev/fastrpc-cdsp` EACCES、`/vendor` 未挂载，QNN 只能在 Android 应用进程里跑。
- **region 模式不可用**：PaddlePaddle 3.2.2 在本机 ARM64 proot 下 `predict` 段错误。
- **GPU 显存有限**：8192 上下文 + 2048px 图像会 `device lost`；建议 ≤4096 上下文、≤1600px。
- **78.30% 不是纯量化损失**：没跑 BF16 对照，差值混合了后端、分辨率、提示词、计分口径。**仅供参考。**

## 致谢与许可

- 模型：[SeerRay-Lab/Xiaomi-OCR-0](https://huggingface.co/SeerRay-Lab/Xiaomi-OCR-0)（权重许可见其仓库）
- 运行时：[ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)（MIT）
- GPU 驱动：[Mesa3D](https://gitlab.freedesktop.org/mesa/mesa)（MIT）
- 数据集：[echo840/OCRBench](https://huggingface.co/datasets/echo840/OCRBench)
- 本仓库脚本：MIT（见 [LICENSE](LICENSE)）
