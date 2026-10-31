# Xiaomi-OCR-0 推理后端可行性调研（Android / proot / ARM64 / 无 GPU）

对象：https://github.com/SeerRay-Lab/Xiaomi-OCR-0 的 Skill 安装（backbone 推理 + 可选 region 布局）。
本机实测：aarch64、8 核、总内存 15109 MB、MemAvailable 3.0–3.8 GB（swap 已用 8.7 GB）、Ubuntu 24.04.5、
glibc 2.39、Python 3.12.15、无 systemctl / 无 /run/systemd、无 /dev/dri（不可读）、无 /dev/nvidia*、无 /dev/kvm、
ollama 未安装；CPU flags 含 asimd bf16 i8mm sve sve2。

## 结论速览

| 后端 | 判定 | 一句话依据 |
|---|---|---|
| SGLang | **infeasible** | 官方只支持 NVIDIA GPU；CPU 后端限 Intel Xeon AMX |
| vLLM | **uncertain（值得实测）** | ARM64 CPU 有官方 wheel 与代码路径，但 Qwen3.5 未进 CPU 校验清单 |
| Ollama（CPU/ARM64） | **feasible（内存压线）** | 官方有 linux-arm64 包；proot 无 systemd 需手动 serve；社区已有 Android+proot 成功案例 |
| PaddlePaddle CPU（region 用） | **feasible** | 官方 CPU 索引有 linux_aarch64 cp312 wheel；PyPI 缺 3.3+ 的 aarch64 |

## 1. 模型规模与架构（已核实）

- HF 规范 id 现为 `xiaomi-research/Xiaomi-OCR-0`（旧 id `SeerRay-Lab/Xiaomi-OCR-0` 仍可用），sha `bbd8cf8d21f256b3644b44cb860f3a7cecb93c30`。
  https://huggingface.co/api/models/SeerRay-Lab/Xiaomi-OCR-0
- 参数量 **873,438,784**，全部 BF16（API `?expand[]=safetensors` → `{"parameters":{"BF16":873438784},"total":873438784}`）。
- `model.safetensors` = **1,746,937,856 B = 1.747 GB（1.627 GiB）**；`tokenizer.json` 19.99 MB；模型本体约 **1.77 GB**。
  https://huggingface.co/api/models/SeerRay-Lab/Xiaomi-OCR-0/tree/main?recursive=true
- 架构 `Qwen3_5ForConditionalGeneration`（model_type `qwen3_5`），base model **Qwen/Qwen3.5-0.8B-Base**。
  https://huggingface.co/SeerRay-Lab/Xiaomi-OCR-0/raw/main/config.json
- config 关键值：24 层 / hidden 1024 / 8 attn heads / 2 KV heads / head_dim 256 / vocab 248320（tie embeddings）；
  每 4 层一个 full_attention（共 6 层，其余为 linear_attention=GDN）/ max_position_embeddings 262144；
  vision：depth 12 / hidden 768 / patch 16 / merge 2。
- 仓库口径一致：README “0.8B”“from Qwen3.5-0.8B”；`OLLAMA.md` 记社区 GGUF 约 1.8 GB（1.6 GiB）含 vision projector。
  本地：/sdcard/projects/xiaomi-ocr/repo/README.md、/sdcard/projects/xiaomi-ocr/repo/OLLAMA.md

## 2. SGLang / vLLM 在 CPU-only ARM64 上

### SGLang：infeasible
- 安装文档："These instructions target Linux with NVIDIA GPUs"，Docker 需 CUDA 13 驱动。
  https://docs.sglang.ai/get_started/install.html
- 唯一 CPU 文档 “CPU Servers” 写死 Intel AMX：“enabled and optimized on the CPUs equipped with Intel® AMX® Instructions,
  which are 4th generation or newer Intel® Xeon®”，示例用 `LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu`、`--tp` 按 Xeon SNC 切。
  https://docs.sglang.io/docs/hardware-platforms/cpu_server.md
- Skill 引的 Qwen3.5 cookbook 只有 GPU 配方（H100/H200/B200/B300/MI300X；397B BF16 约 800 GB 显存）。
  https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.5.md
  注：Skill 里的 `docs_new/cookbook/.../Qwen3.5.mdx` 已 404。

### vLLM：uncertain
- 官方支持 ARM CPU：“basic model inferencing and serving on Arm CPU platform, with support for NEON, data types FP32, FP16 and BF16”，要求 Linux + NEON。
  https://docs.vllm.ai/en/latest/getting_started/installation/cpu/
- 预编译 aarch64 CPU wheel：`vllm-0.32.0+cpu-cp38-abi3-manylinux_2_39_aarch64.whl`（71 MB）；每夜构建索引 https://wheels.vllm.ai/nightly/cpu。
  https://api.github.com/repos/vllm-project/vllm/releases/latest → 本机 glibc 2.39 正好满足 manylinux_2_39。
- ARM BF16 需 ARMv8.6-A / FEAT_BF16（同页）；本机 /proc/cpuinfo 有 `bf16` flag，满足。
- 架构已实现：`Qwen3_5ForConditionalGeneration` 注册 MULTIMODAL_REGISTRY。
  https://docs.vllm.ai/en/latest/api/vllm/model_executor/models/qwen3_5/
- 但 CPU “已校验模型” 清单只有 Xeon 6/5 + AMD Zen，多模态只到 Qwen2.5-VL-7B、Qwen3-VL-30B-A3B，**无 Qwen3.5**。
  https://docs.vllm.ai/en/latest/models/hardware_supported_models/cpu/
  （通用 supported_models 表的两个 ✅ 是 LoRA 与 PP，不代表 CPU 支持。）
- 有利推断证据：源码存在 GDN 的 CPU 实现 `vllm/model_executor/layers/mamba/ops/cpu/gdn_attention.py`，
  用 `is_arm_bf16()` 选 NEON/BF16 路径，说明为 ARM CPU 留了通路；但“代码存在”≠“跑通”。
- 判定 uncertain：0.8B/1.75 GB 体量小、概率不低，必须实测 `vllm serve ... --max-model-len 16384 --dtype bfloat16` + 真实图片请求后才可宣称可用。

## 3. Ollama（CPU / ARM64 / Android proot / 免 root）

- Tag（文档事实）：`longwayxu/xiaomi-ocr-0:bf16`，digest `e66e0eaee51a`，**1.8 GB**、**256K context window**、输入 Text+Image。
  https://ollama.com/longwayxu/xiaomi-ocr-0/tags
- 官方 ARM64 包：`ollama-linux-arm64.tar.zst`（1,582 MB），安装为 `curl -fsSL https://ollama.com/download/ollama-linux-arm64.tar.zst | sudo tar x -C /usr` + 手动 `ollama serve`。
  https://docs.ollama.com/linux ；体积见 https://api.github.com/repos/ollama/ollama/releases/latest（v0.40.13）
- 无官方 Android 构建：下载页只有 macOS/Linux/Windows（https://ollama.com/download）；maintainer 在
  https://github.com/ollama/ollama/issues/721 说没有官方 Android 发布计划（2023，已 closed）。
- proot 限制（实测+文档）：无 systemd（`systemctl`、`/run/systemd` 都不存在）→ 只能用文档的 Manual install + `ollama serve`；
  不需要 /dev/kvm（本机也没有，KVM 只关虚拟机，Ollama 文档未要求）；无 GPU 用 `CUDA_VISIBLE_DEVICES=-1` 强制 CPU；
  /dev 与 /proc 在 proot 被裁剪（本机 `ls /dev` 直接 Permission denied）；模型默认落 `~/.ollama`（rootfs），别放大文件到 /sdcard 的 FUSE 上。
- 第三方成功案例：https://github.com/kpmagno/openclaw-ollama-android （Termux + proot-distro Ubuntu 跑 Ollama 的 playbook）、
  https://github.com/MohammadArsalanShakil/Running-Ollama-StableLM-1.6B-on-Android （用 proot-distro 提供 glibc 层）。
  issue #721 里有人报告 proot 下需 patchelf 改 interpreter，那是手工拼 fs 的场景；proot-distro 的 Ubuntu 自带 `ld-linux-aarch64.so.1`。
- 判定 feasible，但两点必须说清：`OLLAMA.md` 记录 BF16 GGUF 在 Apple Silicon 上 5/7 回答与 HF 一致、2 个公式有差异 → 不等价；
  1.8 GB 权重 + 运行时 + KV 对本机 3.0–3.8 GB 可用内存是压线。

## 4. PaddlePaddle CPU wheel（aarch64 Linux / Python 3.12）

- PyPI `paddlepaddle` 3.3.1 只有 `manylinux1_x86_64` / `macosx_11_0_arm64` / `win_amd64`，**没有 linux aarch64**；
  全量 276 个文件中 linux aarch64 只到 **3.2.1 / 3.2.2**（`paddlepaddle-3.2.2-cp312-cp312-manylinux2014_aarch64.whl`，88.1 MB）。
  https://pypi.org/pypi/paddlepaddle/json
- 官方 CPU 索引有 aarch64：linux_aarch64 覆盖 3.2.0 / 3.2.1 / 3.2.2 / 3.3.0 / 3.3.1 / 3.4.0，cp39–cp313（含 cp312）。
  https://www.paddlepaddle.org.cn/packages/stable/cpu/paddlepaddle/
- PaddleX 页的 pip 命令正是 `pip install paddlepaddle==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/`。
  https://paddlepaddle.github.io/PaddleX/latest/en/installation/paddlepaddle_install.html
- 判定 feasible：走官方索引并 pin 版本（PyPI 取不到 3.3+ aarch64），再按
  https://github.com/SeerRay-Lab/Xiaomi-OCR-0/blob/main/requirements-paddlex.txt 装 `paddlex[cv]` + `shapely`，设 `XIAOMI_OCR_LAYOUT_DEVICE=cpu`。

## 5. 资源账

| 项 | 数值 | 性质 |
|---|---|---|
| HF 权重 | 1.747 GB | 实测文件大小 |
| HF 权重+tokenizer | ≈1.77 GB | 实测 |
| Ollama 包下载 | 1.582 GB | release asset |
| Ollama 解压 + 模型 | ≈2 + 1.8 = 3.8 GB | 解压为估算 |
| vLLM 栈（torch aarch64 484 MB + vllm 71 MB + 依赖） | ≈2–3 GB | 估算 |
| Paddle wheel + paddlex[cv] | ≈0.8–1.5 GB | wheel 88 MB 实测，余为估算 |
| KV cache（6 层 full attn，2 heads×256×2 B×2） | ≈12.6 KB/token → 4K≈52 MB、16K≈210 MB | 由 config 推算 |
| 推理常驻内存 | 2.5–3.5 GB | 推断；本机可用 3.0–3.8 GB |

## 6. 建议路线

1. 先实测 **vLLM CPU**（aarch64 wheel + glibc 2.39 匹配，精度等同 HF）；跑通即最优，跑不通就记录报错别硬推。
2. 保底 **Ollama**：`ollama pull longwayxu/xiaomi-ocr-0:bf16` + `ollama serve`（不用 systemd），上下文压到 4K–8K；明确告知精度不等价。
3. **SGLang 排除**（无 ARM64 CPU 支持）。
4. **region 模式单算**：Paddle 走官方 CPU 索引 pin 3.3.x，与 backbone 后端互不替代。
5. 监听只留 loopback（`127.0.0.1:11434/v1` 或 `:8000/v1`）。

## 7. 事实 / 推断分界

- 事实：参数量与字节数、config 结构、Ollama tag 大小与上下文、vLLM ARM CPU 支持与 wheel 名、SGLang CPU 限 Xeon AMX、
  Paddle 平台矩阵、本机 glibc/CPU flag/内存/systemd/设备节点现状。
- 推断（未实跑）：vLLM CPU 能否加载 Qwen3.5 的 GDN + 视觉塔；Ollama 在 3 GB 可用内存下的吞吐与是否 OOM；vLLM/Paddle 安装后真实占用。
