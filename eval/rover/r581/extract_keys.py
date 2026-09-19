#!/usr/bin/env python3
"""R581 起手: 从既有 shell 快照中提取 AGENTFRAMEWORK_KEYS_* 到本机 600 模式 env 文件。
纪律: 值不打印、不落仓(路径在 $HOME 下, 非仓库内); 只报 变量名 + 长度。
"""
import glob
import os
import re
import stat

SRC = glob.glob("/home/agentuser/.codex/shell_snapshots/*.sh") + \
      glob.glob("/home/agentuser/.hermes/cache/terminal*/**/*.sh", recursive=True)
OUT = "/home/agentuser/.agentframework/keys.env"
pat = re.compile(r"^(?:export\s+)?(AGENTFRAMEWORK_[A-Z0-9_]+)=(.+)$")
found = {}
for p in SRC:
    try:
        for line in open(p, "r", encoding="utf-8", errors="replace"):
            m = pat.match(line.strip())
            if m:
                name, val = m.group(1), m.group(2).strip().strip('"').strip("'")
                if val and name not in found:
                    found[name] = val
    except Exception:
        continue

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    for k, v in sorted(found.items()):
        f.write(f'export {k}="{v}"\n')
os.chmod(OUT, stat.S_IRUSR | stat.S_IWUSR)
print("names:", {k: len(v) for k, v in sorted(found.items())})
print("out:", OUT, "mode:", oct(stat.S_IMODE(os.stat(OUT).st_mode)))
