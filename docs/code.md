# 代码说明

## 1. 整体数据流

```text
图片/PDF
  │  150 dpi 渲染 / 缩放（fit_image，长边 ≤ 2048，默认 1600）
  ▼
ocr.py / ocr_page.py                      ← 本仓库脚本
  │  POST /v1/chat/completions (OpenAI 兼容，base64 PNG)
  ▼
llama-server (build-vk, Vulkan)  ──Vulkan──▶  Adreno 840（自建 Turnip/kgsl）
  │  text GGUF (Q4_K_M) + mmproj (F16)
  ▼
Markdown 文本
```

另一条等价路径是 MCP：DSH 通过 `dsh-mcp-client` 启动 `mcp_ocr_server.py`，它做同样的图像预处理与调用，
并把结果包装成 `ocr_image / ocr_pdf / kie_image / vqa_image` 四个工具。两条路径共用同一个 `llama-server`。

## 2. 脚本清单

| 文件 | 行数 | 作用 | 关键参数 |
|---|---|---|---|
| `scripts/ocr.py` | 38 | 单图 OCR，直接打 llama-server | `XIAOMI_OCR_LOCAL_URL`（默认 127.0.0.1:8000/v1）、max_tokens |
| `scripts/ocr_page.py` | 60 | 大图分块 OCR（横向条带 + 重叠），逐块识别后拼接 | `--bands`（默认 3）、`--overlap`（默认 60）、`--max-edge` |
| `scripts/start-llama-server.sh` | 34 | 启动推理服务；GPU 优先，`--cpu` 回退 | `VK_ICD_FILENAMES`、`-ngl 99 --device Vulkan0`、`-c 4096` |
| `scripts/build-turnip-kgsl.sh` | 7 | 编 Mesa/Turnip（kgsl 后端） | `-Dvulkan-drivers=freedreno -Dfreedreno-kmds=kgsl` |
| `scripts/build-vulkan.sh` | 13 | 编 llama.cpp Vulkan 后端 | `-DGGML_VULKAN=ON`，target `llama-server` |
| `scripts/build-quantize.sh` | 9 | 编 `llama-quantize` | `-j4` 控内存 |
| `scripts/turnip-kgsl.json` | 7 | Vulkan ICD，指向自建 `libvulkan_freedreno.so` | 必须绝对路径 |
| `scripts/ocrbench_eval.py` | 81 | OCRBench 逐题推理（含断点续跑） | `ckpt_concise.json`、并发 2、`enable_thinking=false` |
| `scripts/ocrbench_scorer.py` | 12 | 计分归一化（含 LaTeX 宽松匹配） | `tight()` / `word()` |

## 3. 未入库的运行件（体积大，按需生成）

| 件 | 位置 | 体积 | 生成方式 |
|---|---|---|---|
| 模型 Q4_K_M | `models/xiaomi-ocr0-q4_k_m.gguf` | 518 MB | LFS 已入库；或 `llama-quantize` 自产 |
| 视觉投影器 | `models/xiaomi-ocr0-mmproj-f16.gguf` | 197 MB | 同上（不可量化） |
| Turnip .so | `/root/mesa-build/.../libvulkan_freedreno.so` | 16 MB | `scripts/build-turnip-kgsl.sh` |
| llama-server(Vulkan) | `/root/xiaomi-ocr/llama.cpp/build-vk/bin/` | ~70 MB | `scripts/build-vulkan.sh` |
| MCP venv | `/root/xiaomi-ocr/repo/skills/xiaomi-ocr/.venv` | 428 MB | 官方 `install.sh` |

## 4. MCP 接入（DSH）

配置文件：`/root/.dsh/profiles/web/cordis.patch.yml`（追加一条 entry，不改其它条目）

```yaml
- id: mcp-xiaomi-ocr
  name: "@deepseek-ai/dsh-mcp-client"
  config:
    serverName: xiaomi-ocr
    transport: stdio
    command: /root/xiaomi-ocr/repo/skills/xiaomi-ocr/.venv/bin/python
    args: [/root/xiaomi-ocr/repo/skills/xiaomi-ocr/mcp_ocr_server.py]
    env:
      XIAOMI_OCR_LOCAL_URL: http://127.0.0.1:8000/v1
      XIAOMI_OCR_MODEL: local
      XIAOMI_OCR_REPO: /root/xiaomi-ocr/repo
    toolCallTimeoutMs: 900000
```

对外工具名：`mcp__xiaomi-ocr__ocr_image / ocr_pdf / kie_image / vqa_image`。推理服务需另外启动（见 start 脚本）。

## 5. 已知问题

1. `find_slot: non-consecutive token position` 警告在视觉请求里反复出现，实测不影响输出，来源是 mtmd 的 slot 位置计算。
2. 单进程内连续请求会累积显存/内存（约 40–75 MB/请求），批量评测需要每 25 题重启一次服务。
3. `-c 8192` 搭配 2048px 图像会触发 `ggml_vulkan: device lost`，建议上下文 ≤ 4096、图像长边 ≤ 1600。
4. region 模式（PP-DocLayoutV3）在本机 PaddlePaddle 3.2.2 下 `predict` 段错误，不可用；相应依赖已移除。
