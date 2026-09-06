#!/usr/bin/env python3
import json, re, sys
text = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
m = re.search(r"(-?[0-9.]+)\s*(?:摄氏度|°C|℃)\s*(?:转|to|换算成)\s*(?:华氏|°F|℉)", text)
if not m:
    print(json.dumps({"skill": "unit-convert", "error": "no_pattern_match"}, ensure_ascii=False))
else:
    c = float(m.group(1))
    f = c * 9 / 5 + 32
    print(json.dumps({"skill": "unit-convert", "celsius": c, "fahrenheit": round(f, 2)}, ensure_ascii=False))
