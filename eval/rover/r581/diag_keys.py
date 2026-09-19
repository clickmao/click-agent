#!/usr/bin/env python3
"""诊断: 列出含 AGENTFRAMEWORK 的行 (仅 文件/行号/键名/值长), 不打印值。"""
import glob
import re

SRC = sorted(glob.glob("/home/agentuser/.codex/shell_snapshots/*.sh"))
print("files:", len(SRC))
for p in SRC[:3]:
    print("---", p)
    for i, line in enumerate(open(p, "r", encoding="utf-8", errors="replace"), 1):
        if "AGENTFRAMEWORK" in line:
            key = line.split("=", 1)[0][:60]
            ln = len(line.split("=", 1)[1]) if "=" in line else -1
            print(f"  L{i} key={key!r} valuelen={ln}")

# 也扫 hermes cache/terminal-output 里出现名字的文件
import subprocess
out = subprocess.run(["grep", "-rl", "AGENTFRAMEWORK_KEYS_DEEPSEEK", "/home/agentuser/.hermes/"],
                     capture_output=True, text=True).stdout.split()
print("hermes files with name:", out[:5])
for p in out[:2]:
    try:
        txt = open(p, "r", encoding="utf-8", errors="replace").read()
    except Exception as e:
        print("  read fail", e)
        continue
    for m in re.finditer(r"AGENTFRAMEWORK_[A-Z0-9_]+", txt):
        print("  ", p, m.group(0), "count", txt.count(m.group(0)))
        break
