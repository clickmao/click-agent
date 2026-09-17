#!/usr/bin/env python3
"""R526 命名空间归一: ① agent.Recall* → 小写 ② 测试项目命名空间统一为 agent.tests
   ③ 无命名空间测试文件补 namespace agent.tests; (目录↔命名空间一致不变式)"""
import io, os, re, sys

ROOT = "/home/agentuser/AgentFramework"
os.chdir(ROOT)


def files_under(top):
    out = []
    for dp, dn, fn in os.walk(top):
        dn[:] = [d for d in dn if d not in ("obj", "bin")]
        for f in fn:
            if f.endswith(".cs"):
                out.append(os.path.join(dp, f))
    return sorted(out)


def rewrite(path, subs):
    t = io.open(path, encoding="utf-8").read()
    n = t
    for a, b in subs:
        n = re.sub(a, b, n, flags=re.M)
    if n != t:
        io.open(path, "w", encoding="utf-8", newline="").write(n)
        return True
    return False


# ① Recall 命名空间小写化
pairs = [(r"\bagent\.Recall\.Bench\b", "agent.recall.bench"),
         (r"\bagent\.Recall\.Tests\b", "agent.recall.tests"),
         (r"\bagent\.Recall\b", "agent.recall")]
n1 = 0
for f in files_under("src"):
    if rewrite(f, pairs):
        n1 += 1

# ② 测试项目命名空间统一
n2 = 0
for f in files_under("src/agent.tests"):
    if rewrite(f, [(r"^\s*namespace\s+agentframework\.tests\b", "namespace agent.tests"),
                   (r"^\s*using\s+agentframework\.tests\s*;", "using agent.tests;")]):
        n2 += 1

# ③ 无命名空间测试文件补命名空间
n3 = 0
for f in files_under("src/agent.tests"):
    t = io.open(f, encoding="utf-8").read()
    if re.search(r"^\s*namespace\s+", t, re.M):
        continue
    lines = t.split("\n")
    i = 0
    while i < len(lines) and (lines[i].strip() == "" or lines[i].lstrip().startswith("using ")
                              or lines[i].lstrip().startswith("//")):
        i += 1
    lines.insert(i, "namespace agent.tests;")
    lines.insert(i + 1, "")
    io.open(f, "w", encoding="utf-8", newline="").write("\n".join(lines))
    n3 += 1

print(f"rewritten: recall={n1} tests_ns={n2} add_ns={n3}")

# ④ 头部区 using 去重 (仅 namespace 之前 — 方法内 local using 不得触碰)
n4 = 0
for f in files_under("src"):
    lines = io.open(f, encoding="utf-8").read().split("\n")
    cut = len(lines)
    for i, l in enumerate(lines):
        if re.match(r"^\s*namespace\b", l):
            cut = i
            break
    seen, dup = set(), 0
    out = []
    for i, l in enumerate(lines):
        s = l.strip()
        if i < cut and re.match(r"^using\s+[\w.]+\s*;$", s):
            if s in seen:
                dup += 1
                continue
            seen.add(s)
        out.append(l)
    if dup:
        io.open(f, "w", encoding="utf-8", newline="").write("\n".join(out))
        n4 += 1
print(f"头部 using 去重文件数={n4}")
# 残留检查
bad = []
for f in files_under("src"):
    t = io.open(f, encoding="utf-8").read()
    for m in re.finditer(r"^\s*namespace\s+([\w.]+)", t, re.M):
        ns = m.group(1)
        if ns != ns.lower():
            bad.append((f, ns))
print("非全小写命名空间残留:", len(bad))
for f, ns in bad[:10]:
    print("  ", f, ns)
