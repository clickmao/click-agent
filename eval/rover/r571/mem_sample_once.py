#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单次内存采样 (起手闸条款用): 读 /proc/meminfo 的 MemAvailable 追加一行 JSON。"""
import io
import json
import sys
import time

out = sys.argv[1]
m = None
for ln in io.open("/proc/meminfo", encoding="utf-8", errors="replace"):
    if ln.startswith("MemAvailable:"):
        m = int(ln.split()[1]) // 1024
        break
io.open(out, "a", encoding="utf-8").write(
    json.dumps({"ts": round(time.time(), 1), "mem_available_mb": m}) + "\n")
print("mem_available_mb=%s" % m)
