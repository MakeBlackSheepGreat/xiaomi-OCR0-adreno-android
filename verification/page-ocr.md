# page 模式实测（ocr_image, mode="page"）

- 图片：`example_pics/qianziwen.jpeg`（510×979，行书千文）
- 耗时：84.7 s（CPU / Ollama）
- 返回：`isError: None`

## 模型输出

```markdown
行书千文

梁员外散骑侍郎周兴嗣次韵

天地玄黄宇宙洪荒日月
```

## 仓库标准答案（example_pics/qianziwen.md）

```markdown
行书千文

梁貟外散騎侍郎周興嗣次韻

天地玄黄宇宙洪荒日月
```

差异只在三个字：员/貟、骑/騎、兴/興、嗣/嗣（繁体与简体写法），识别内容与行序一致。
