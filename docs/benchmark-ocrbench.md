# OCRBench 实测说明（仅供参考）

> **结论先行**：本机（Q4_K_M + Adreno GPU + llama.cpp）OCRBench **78.30%**，官方公布 **84.6**，差 **−6.3**。
> 这个差值**不是**纯量化损失，它混合了量化、推理后端、图像分辨率、提示词、计分口径五项因素。
> 单次运行，未做重复实验；数字仅供工程参考，不能作为对官方分数的正式复现或质疑。

## 1. 我们到底测了什么

| 项 | 设置 |
|---|---|
| 数据 | OCRBench 全量 1000 题（`echo840/OCRBench`，67.6 MB parquet，图片内嵌） |
| 模型 | Xiaomi-OCR-0 **Q4_K_M**（518 MB，本机用 llama-quantize 自行量化） |
| 运行时 | llama.cpp Vulkan 后端，`-ngl 99 --device Vulkan0`，Adreno 840 / Turnip(kgsl) |
| 视觉 | mmproj F16（未量化），图像长边**压到 1024px**（控 GPU 内存） |
| 提示词 | `题目 + " Answer with only the answer text, no explanation."` |
| 解码 | temperature 0，`chat_template_kwargs.enable_thinking=false`，max_tokens 64（公式 192/512） |
| 计分 | 归一化后完全匹配（小写、去标点/冠词/空白）；公式额外做 LaTeX 宽松匹配 |

## 2. 结果

| 计分口径 | 本机 | 官方 | 差 |
|---|---|---|---|
| 数学感知归一化（宽松） | **78.30%** | 84.6 | **−6.3** |
| 严格逐字符归一化 | 75.90% | — | −8.7 |

| 类别 | 本机 | 题数 |
|---|---|---|
| Non-Semantic Text Recognition | 98.0% | 50 |
| Regular Text Recognition | 96.0% | 50 |
| Irregular Text Recognition | 96.0% | 50 |
| Artistic Text Recognition | 94.0% | 50 |
| Handwriting Recognition | 82.0% | 50 |
| Digit String Recognition | 80.0% | 50 |
| Key Information Extraction | 78.0% | 200 |
| Scene Text-centric VQA | 75.5% | 200 |
| Doc-oriented VQA | 70.0% | 200 |
| Handwritten Math (HME) | 63.0% | 100 |

印刷体识别几乎无损（94–98%），损失集中在文档理解与手写公式。

## 3. 局限性（重要）

1. **无 BF16 对照**：按需求没有跑官方模型，所以 6.3 分是“量化 + 后端 + 分辨率 + 提示词 + 计分”的**合计差**，无法拆分出“量化本身掉了多少”。要拆分需要 BF16 GGUF（+1.52 GB）跑同一批题。
2. **分辨率被压**：17%（173/1000）的题图超过 1024px，本机为控显存压到 1024；官方无此限制。Doc VQA / KIE 的掉分主要来自这里，与量化无关。
3. **提示词不对齐**：官方未公开 OCRBench 提示词与解码参数。实测同一批 VQA 题，不加“只输出答案”约束时 41%，加了之后 90% —— 提示词的影响力大于量化误差。
4. **计分非官方**：OCRBench 官方评分脚本未完全公开，本仓库用的是自写归一化匹配；公式题额外做了宽松匹配（否则 38% 会被误判为 63%）。不同计分实现之间可能有数个点差异。
5. **单次运行**：1000 题只跑了一轮，无重复、无置信区间；单题噪声约 ±1.5 个百分点（按 1000 题二项分布估算）。
6. **量化版本**：Q4_K_M 是本机自行量化，社区另有 `prithivMLmods` 的 Q4_K_M（529 MB），两者不保证逐位一致。
7. **运行时差异**：官方为 BF16 + vLLM（GPU 服务器），本机为 Q4 + llama.cpp + 手机 GPU；后端实现、batch、KV 策略均不同。
8. **GPU 边界**：尝试 2048px + 8192 上下文复跑大图时 Turnip 报 `device lost`，说明这条路线的显存上限较低，也是掉分来源之一。

因此：**78.30 只能说明“这套手机端方案大约落在官方 84.6 的 6 分以内”，不能据此断言模型官方分数有水分，也不能断言量化损失就是 6.3 分。**

## 4. 复现

```bash
# 1. 数据（67.6 MB）
hf download echo840/OCRBench --repo-type dataset --local-dir ./ocrbench

# 2. 起服务（GPU）
bash scripts/start-llama-server.sh

# 3. 评测
python3 scripts/ocrbench_eval.py      # 逐题推理，写 ckpt_concise.json
python3 scripts/ocrbench_scorer.py    # 计分，输出总分与分项
```

逐题原始结果：`verification/ocrbench/results_concise.json`（1000 条，含预测、标准答案、判分）。
