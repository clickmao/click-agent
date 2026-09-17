#!/usr/bin/env python3
"""R526 结构不变式机检 (权威终版; 与待落地的 xUnit 判据同算法)。
  I1 单类型单文件; I2 文件名=类型名; I3 每文件必含命名空间 (文件级或块式) 且同目录命名空间唯一。
  豁免: Program.cs (顶层语句) / 已登记遗产命名空间 (agent.core 两个子目录)。"""
import io, os, re, collections

ROOT = "/home/agentuser/AgentFramework"
os.chdir(ROOT)
RX_TYPE = re.compile(r"^(?:(?:public|internal|private|protected|static|sealed|abstract|partial|readonly|ref|unsafe|file)\s+)*"
                     r"(?:record\s+struct|record\s+class|class|record|struct|interface|enum)\s+(?P<n>\w+)")
RX_NS_FILE = re.compile(r"^[ \t]*namespace\s+([\w.]+)\s*;", re.M)
RX_NS_BLOCK = re.compile(r"^[ \t]*namespace\s+([\w.]+)\s*$", re.M)

EXEMPT = set()   # R527 候选①: agent.core/{userinteraction,subagent} 已收敛为 agent.core ⇒ 豁免清单清空

viol = collections.defaultdict(list)
files = 0
for dp, dn, fn in os.walk("src"):
    dn[:] = [d for d in dn if d not in ("obj", "bin")]
    ns_in_dir = collections.defaultdict(list)
    for f in fn:
        if not f.endswith(".cs"):
            continue
        files += 1
        p = os.path.join(dp, f)
        rel = os.path.relpath(p, "src").replace(os.sep, "/")
        t = io.open(p, encoding="utf-8", errors="replace").read()
        stem = f[:-3]
        ts = [m.group("n") for m in RX_TYPE.finditer(t) if m.start() == 0 or t[m.start() - 1] == "\n"]
        if len(ts) > 1:
            viol["I1"].append(f"{rel}: {ts}")
        elif len(ts) == 1 and not (stem == ts[0] or stem.startswith(ts[0] + ".")) and stem != "Program":
            viol["I2"].append(f"{rel}: 类型 {ts[0]}")
        m = RX_NS_FILE.search(t) or RX_NS_BLOCK.search(t)
        ns = m.group(1) if m else "<无>"
        if ns == "<无>":
            if stem != "Program":
                viol["I3a"].append(f"{rel}: 无命名空间")
        else:
            ns_in_dir[ns].append(rel)
        o = sum(1 for l in t.split("\n") if l.strip().startswith("#region"))
        c = sum(1 for l in t.split("\n") if l.strip().startswith("#endregion"))
        if o != c:
            viol["I4"].append(f"{rel}: region 不配对 {o}/{c}")
    for ns, fs in ns_in_dir.items():
        rel_dir = os.path.relpath(dp, "src").replace(os.sep, "/")
        if len(ns_in_dir) > 1 and (rel_dir, ns) not in EXEMPT:
            viol["I3b"].append(f"{rel_dir}: 混用命名空间 {list(ns_in_dir)} x{len(fs)}")

print(f"扫描 {files} 个 .cs")
for k in ("I1", "I2", "I3a", "I3b", "I4"):
    print(f"{k}: {len(viol[k])}")
    for v in viol[k][:10]:
        print("   ", v)
print("EXIT", 1 if any(viol.values()) else 0)
