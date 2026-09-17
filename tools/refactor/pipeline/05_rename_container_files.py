#!/usr/bin/env python3
"""R526 收口2: 把「文件名≠类型名」的容器文件重命名为 <类型名>.cs (纯改名, 零代码改动)。"""
import io, os, re, shutil

ROOT = "/home/agentuser/AgentFramework"
os.chdir(ROOT)
RX = re.compile(r"^(?:(?:public|internal|private|protected|static|sealed|abstract|partial|readonly|ref|unsafe|file)\s+)*"
                r"(?:record\s+struct|record\s+class|class|record|struct|interface|enum)\s+(?P<n>\w+)", re.M)

renamed, skipped = [], []
for dp, dn, fn in os.walk("src"):
    dn[:] = [d for d in dn if d not in ("obj", "bin")]
    for f in sorted(fn):
        if not f.endswith(".cs"):
            continue
        p = os.path.join(dp, f)
        stem = f[:-3]
        t = io.open(p, encoding="utf-8", errors="replace").read()
        ts = [m.group("n") for m in RX.finditer(t) if m.start() == 0 or t[m.start() - 1] == "\n"]
        if len(ts) != 1:
            continue
        n = ts[0]
        if stem == n or stem.startswith(n + ".") or stem == "Program":
            continue
        dst = os.path.join(dp, n + ".cs")
        if os.path.exists(dst):
            skipped.append((p, dst))
            continue
        shutil.move(p, dst)
        renamed.append((p, dst))

print(f"重命名 {len(renamed)} 个文件")
for a, b in renamed:
    print("   ", os.path.relpath(a, ROOT), "→", os.path.basename(b))
if skipped:
    print(f"跳过 {len(skipped)} (目标已存在):")
    for a, b in skipped[:10]:
        print("   ", os.path.relpath(a, ROOT), "→", os.path.relpath(b, ROOT))
