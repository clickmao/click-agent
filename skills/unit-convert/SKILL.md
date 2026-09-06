---
name: unit-convert
description: 单位换算 — 温度/长度常用单位换算 (执行型脚本技能, 确定性输出)
version: 1.0.0
license: MIT
type: executive
keywords:
  - 单位换算
  - 换算
regex_patterns:
  - "(-?[0-9.]+)\\s*(摄氏度|°C|℃)\\s*(转|to|换算成)\\s*(华氏|°F|℉)"
domain_words:
  - 换算
  - 华氏
---
# 口径
摄氏→华氏: F = C × 9/5 + 32。输出一行 JSON。
