# OCRBench 实测：Q4_K_M + Adreno GPU（本机设置）vs 官方 84.6

日期：2026-11-01　设备：骁龙 8 Elite Gen 5（SM8850，Adreno 840）　模型：Xiaomi-OCR-0 Q4_K_M（517 MB）

## 结果

| 指标 | 本机 | 官方（BF16 + vLLM） | 差值 |
|---|---|---|---|
| OCRBench 总分 | **78.30%** | **84.6** | **−6.3** |
| 严格逐字符口径 | 75.90% | — | −8.7 |

78.30 用数学感知归一化（去 LaTeX 命令名、空格、括号后比较），主要修正手写公式题；75.90 是严格归一化。官方计分口径未完全公开，两个都列。

## 分项

| 类别 | 本机 | 题数 |
|---|---|---|
| Regular Text Recognition | 96.0% | 50 |
| Irregular Text Recognition | 96.0% | 50 |
| Non-Semantic Text Recognition | 98.0% | 50 |
| Artistic Text Recognition | 94.0% | 50 |
| Handwriting Recognition | 82.0% | 50 |
| Digit String Recognition | 80.0% | 50 |
| Key Information Extraction | 78.0% | 200 |
| Scene Text-centric VQA | 75.5% | 200 |
| Doc-oriented VQA | 70.0% | 200 |
| Handwritten Math (HME) | 63.0% | 100 |

印刷体识别基本无损（94–98%）；损失集中在文档理解类（Doc VQA 70%、KIE 78%）和手写公式（63%）。

## 6.3 分的来源（可定位部分）

1. 分辨率被压到 1024px：OCRBench 有 17%（173/1000）的图超过 1024px。为控 GPU 内存，批量评测把长边压到 1024；官方没有这个限制。Doc VQA 掉分主要来自这里。
2. GPU 硬限制：尝试用 2048px + 8192 上下文复跑大图时，Turnip/Vulkan 直接 device lost（kgsl 显存耗尽）。这既是掉分原因，也是必须记录的工程限制。
3. 提示词与解码：官方未公开 OCRBench 提示词。本机用「只输出答案、不要解释」+ max_tokens 64/192。同一批 VQA 题实测：不加强约束时 41%，加约束后 90%——提示词影响极大，这部分与量化无关。
4. Q4 量化本身：无法单独隔离。要分离它必须再跑一遍 BF16 同题对照（+1.5 GB 下载）。

## 复现

    数据 67.6 MB：hf download echo840/OCRBench --repo-type dataset --local-dir ./ocrbench
    脚本：scripts/ocrbench_eval.py（推理）、scripts/ocrbench_scorer.py（计分）
    逐题结果：verification/ocrbench/results_concise.json（1000 题，含预测与标准答案）
