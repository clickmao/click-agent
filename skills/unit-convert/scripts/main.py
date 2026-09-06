#!/usr/bin/env python3
"""单位换算 (执行型技能): 摄氏↔华氏 双向。v0.11.0 R16: 触发动词扩展 (转换成/转成/换成/换算成/转/to)。"""
import json
import re
import sys

text = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()

C2F = r"(-?[0-9.]+)\s*(?:摄氏度|°C|℃)\s*(?:转换成|换算成|转成|换成|转|to)\s*(?:华氏度|华氏|°F|℉)"
F2C = r"(-?[0-9.]+)\s*(?:华氏度|华氏|°F|℉)\s*(?:转换成|换算成|转成|换成|转|to)\s*(?:摄氏度|摄氏|°C|℃)"

m = re.search(C2F, text)
if m:
    c = float(m.group(1))
    print(json.dumps({"skill": "unit-convert", "celsius": c,
                      "fahrenheit": round(c * 9 / 5 + 32, 2)}, ensure_ascii=False))
else:
    m = re.search(F2C, text)
    if m:
        f = float(m.group(1))
        print(json.dumps({"skill": "unit-convert", "fahrenheit": f,
                          "celsius": round((f - 32) * 5 / 9, 2)}, ensure_ascii=False))
    else:
        print(json.dumps({"skill": "unit-convert", "error": "no_pattern_match"},
                         ensure_ascii=False))
