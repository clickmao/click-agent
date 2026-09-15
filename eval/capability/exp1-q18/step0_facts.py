#!/usr/bin/env python3
"""第 0 步·主线提醒取证 (有界输出): 最新计划文档 / 改进日志最新条目 / 主线 §7。"""
import pathlib
import re
import subprocess

ROOT = pathlib.Path("/home/agentuser/AgentFramework")

print("### 最新计划文档 (按 mtime)")
plans = sorted((ROOT / "docs/plans").glob("v0.*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
for p in plans:
    head = p.read_text(encoding="utf-8", errors="replace").splitlines()[:2]
    print(f"  {p.name}  mtime={p.stat().st_mtime:.0f}  | {head[0][:90] if head else ''}")

print("\n### improvements.md 最新条目 (文件头 18 行)")
imp = (ROOT / "docs/improvements.md").read_text(encoding="utf-8", errors="replace").splitlines()[:18]
for ln in imp:
    if ln.strip():
        print("  " + ln[:150])

print("\n### master plan 段落索引 (末尾 6 段)")
mp = (ROOT / "docs/reports/iteration-master-plan.md").read_text(encoding="utf-8", errors="replace")
secs = [(m.start(), m.group(0)) for m in re.finditer(r"^## .*$", mp, re.M)]
print(f"  total_lines={mp.count(chr(10))+1} sections={len(secs)}")
for off, name in secs[-6:]:
    print("   ", name[:110])

print("\n### 对侧执行体状态 (并发判定)")
for pat in ("dotnet (test|publish|build)", "agenthost", "vstest|testhost", "MSBuild|VBCSCompiler"):
    r = subprocess.run(["bash", "-c", f"pgrep -f '{pat}' | wc -l"], capture_output=True, text=True)
    print(f"  {pat:32s} -> {r.stdout.strip()}")
mem = [l for l in pathlib.Path("/proc/meminfo").read_text().splitlines() if "MemAvailable" in l]
print("  " + (mem[0] if mem else "MemAvailable n/a"))
print("\n### 本次提交是否波及对侧文件")
r = subprocess.run(["bash", "-c", "git show --stat --name-only HEAD | grep -cE 'r462|eval/rover' || true"],
                   capture_output=True, text=True, cwd=str(ROOT))
print("  peer_files_in_commit:", r.stdout.strip())
r = subprocess.run(["bash", "-c", "git log --oneline -3"], capture_output=True, text=True, cwd=str(ROOT))
print("  recent commits:\n" + "\n".join("   " + x for x in r.stdout.strip().splitlines()))
r = subprocess.run(["bash", "-c", "ls -la ~/.hermes/skills/*/kpi-eval-harness-design/references/frozen-corpus-and-arm-hygiene.md 2>/dev/null || find ~/.hermes/skills -name 'frozen-corpus-and-arm-hygiene.md'"],
                   capture_output=True, text=True, cwd=str(ROOT))
print("  skill_ref:", r.stdout.strip() or r.stderr.strip()[:120])
