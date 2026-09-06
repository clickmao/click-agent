---
name: wordcount
description: 字数统计 — 统计输入文本的字符数与词数 (执行型脚本技能, 确定性输出)
version: 1.0.0
license: MIT
type: executive
keywords:
  - 字数统计
  - 统计字数
  - 字数
  - 数一下
  - word count
regex_patterns:
  - "统计.{0,6}(字数|字符)"
domain_words:
  - 统计
  - 字数
---
# 口径
统计用户输入文本的字符数 (不含空白) 与词数, 输出一行 JSON。
