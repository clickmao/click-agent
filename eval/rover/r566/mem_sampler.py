#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""运行窗口内的内存采样器 (后台; 由 runner 起、收尾按 pid 杀)。

写 JSONL: {ts, elapsed_s, mem_available_mb}。被 SIGTERM 时也已落盘 (逐行 flush),
不依赖退出时写盘 (R412 纪律: 被杀也不能丢证据)。
"""
import io
import json
import sys
import time

out = sys.argv[1]
period = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
t0 = time.time()
fh = io.open(out, "a", encoding="utf-8")
while True:
    m = None
    for ln in io.open("/proc/meminfo", encoding="utf-8", errors="replace"):
        if ln.startswith("MemAvailable:"):
            m = int(ln.split()[1]) // 1024
            break
    fh.write(json.dumps({"ts": round(time.time(), 1), "elapsed_s": round(time.time() - t0, 1),
                         "mem_available_mb": m}) + "\n")
    fh.flush()
    time.sleep(period)
