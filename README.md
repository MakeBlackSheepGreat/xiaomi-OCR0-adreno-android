# Xiaomi-OCR-0 本地安装（这台手机）

按 https://raw.githubusercontent.com/xiaomi-research/Xiaomi-OCR-0/main/SKILL.md 执行的安装结果。
结论先行：**技能已装好，page 模式的 OCR/KIE/VQA 已用真实图片跑通；region（版面切分）模式在这台机器上不可用。**

## 一、装了什么

| 组件 | 状态 | 位置 |
| --- | --- | --- |
| xiaomi-ocr 技能（DSH 全局） | ✅ | `/root/.dsh/skills/xiaomi-ocr` → 软链到仓库 |
| 仓库 checkout | ✅ | `/root/xiaomi-ocr/repo` |
| MCP Python 环境 | ✅ | `repo/skills/xiaomi-ocr/.venv`（428 MB） |
| 模型 | ✅ **Q4_K_M，518 MB** | `/root/xiaomi-ocr/xiaomi-ocr-q4km.gguf` |
| 推理运行时 | ✅ llama.cpp（Vulkan 版）+ CPU 回退 | `llama.cpp/build-vk/bin/llama-server` |
| **GPU 加速** | ✅ 自建 Turnip(kgsl) → Adreno 840 | `/root/mesa-build/turnip-kgsl.json` |
| DSH MCP 条目 | ✅ 已配 127.0.0.1:8000 | `profiles/web/cordis.patch.yml` |
| region（版面切分） | ❌ Paddle 在 proot 里 SIGSEGV | 已删相关依赖 |

## 二、实测（Q4_K_M）

| 任务 | CPU | GPU(Vulkan/Adreno 840) |
|---|---|---|
| 千字文页 510×979 | 101 s | **5 s** |
| 扫描目录页 707×1000 | 143 s | **18 s（29.6 tok/s）** |
| MCP 端到端（千字文） | 105 s | **2.0 s** |
| 小票字段抽取（KIE） | 92.8 s | 未单测，预计 <10 s |

识别内容与仓库标准答案一致（千字文逐字对；目录页章节页码对）。

## 三、怎么用

```bash
bash /root/xiaomi-ocr/start-llama-server.sh        # GPU（Turnip）
bash /root/xiaomi-ocr/start-llama-server.sh --cpu  # 纯 CPU 回退
```

DSH 重启后 `mcp__xiaomi-ocr__*` 四个工具即可用；也可以直接调：

```bash
python3 /root/xiaomi-ocr/ocr.py <图片> [max_tokens]
python3 /root/xiaomi-ocr/ocr_page.py <图片> --bands 3   # 大图分块
```

## 四、限制

1. GPU 依赖自建 Mesa：启动前必须 `export VK_ICD_FILENAMES=/root/mesa-build/turnip-kgsl.json`（脚本已内置）。
2. 模型走 GPU 时占共享内存，可用内存从 4.3 GB 降到 3.4 GB。
3. NPU 在 proot 里仍不可用：`/dev/fastrpc-cdsp` 是 EACCES、`/vendor` 未挂载；要用 NPU 得做 Android 端程序。
4. region 模式因 Paddle 段错误不可用，只用 `mode="page"`。
5. Ollama BF16 与 HF 数值不等价（仓库 OLLAMA.md 自述）；现在用 llama.cpp 直接跑 GGUF。

## 五、目录

```
/sdcard/projects/xiaomi-ocr/
├── README.md
├── SKILL.md
├── start-ollama.sh（旧，已不用）
├── notes/
│   ├── backend-research.md      # 后端选型调研
│   └── gpu-turnip-kgsl.md       # GPU 加速完整复现步骤
└── verification/
    ├── page-ocr.md / kie.json / vqa.json
    └── region-mode-failure.txt
```

## 六、模型下载（Release 附件）

本仓库的 Release 里直接提供可用权重（无需自己量化）：https://github.com/MakeBlackSheepGreat/xiaomi-OCR0-adreno-android/releases/tag/v1.0.0

| 文件 | 大小 | 说明 |
| --- | --- | --- |
| `xiaomi-ocr0-q4_k_m.gguf` | 518 MB | Q4_K_M 量化后的文本模型 |
| `xiaomi-ocr0-mmproj-f16.gguf` | 198 MB | 视觉投影器（F16，不要量化） |

```bash
# 下载（约 716 MB）
gh release download v1.0.0 -R MakeBlackSheepGreat/xiaomi-OCR0-adreno-android -D models
```

下载放在同一目录后直接启动：

```bash
bash scripts/start-llama-server.sh
```

## 六之二、模型从哪来（自行生成）

仓库里不含模型权重（Q4_K_M 约 518 MB）。两种方式：

```bash
# 方式 A：直接拉社区 GGUF（ollama 格式）
ollama pull longwayxu/xiaomi-ocr-0:bf16

# 方式 B：自己量化（本机做法）
# 从 ollama blobs 里取出 BF16 文本 GGUF 与 projector，然后：
llama-quantize <bf16-text.gguf> xiaomi-ocr-q4km.gguf Q4_K_M
```

本项目用方式 B：BF16 1.56 GB → Q4_K_M 518 MB，量化耗时 17 秒，识别质量基本无损。

## 七、一句话总结

在这台骁龙 8 Elite Gen 5 手机上：Q4 + 自建 Turnip(kgsl) GPU 加速后，一页扫描件 OCR 约 18 秒，千字文页约 5 秒；纯 CPU 分别是 143 秒和 101 秒。NPU 仍受限于 Android 权限模型，需要在 Android 端另做程序。

## 八、仓库命名

仓库名 `xiaomi-OCR0-adreno-android`：Xiaomi-OCR-0 + Adreno GPU（自建 Turnip/kgsl）+ Android 宿主环境。

## 九、真实材料验证

《人工智能导论》扫描件三页（150 dpi）：识别 35–40 秒/页，与人工转录相似度 91.6% / 98.7%，
脚注与引用角标都能识别。详见 `verification/real-pages/REPORT.md`。

## 十、OCRBench 实测（本机设置 vs 官方）

本机 Q4_K_M + Adreno GPU + llama.cpp：**78.30%**（数学感知计分）/ 75.90%（严格计分），官方 BF16+vLLM：**84.6**，差 **−6.3**。
印刷体类 94–98% 基本无损；损失在 Doc VQA（70%）、KIE（78%）、手写公式（63%），主要来自 1024px 降采样与 GPU 显存限制。
详见 `verification/ocrbench/report.md`。
