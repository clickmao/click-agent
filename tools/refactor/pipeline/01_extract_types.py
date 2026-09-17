#!/usr/bin/env python3
"""R526 流水线阶段 A: 回滚 src 到 HEAD + 重跑「类型单一化」。"""
import subprocess, sys, os

ROOT = "/home/agentuser/AgentFramework"
os.chdir(ROOT)

print("=== A1 回滚 src 到 HEAD ===")
print(subprocess.run(["git", "checkout", "--", "src"], capture_output=True, text=True).stderr.strip())
print(subprocess.run(["git", "clean", "-fd", "src"], capture_output=True, text=True).stdout.strip()[-400:])
st = subprocess.run(["git", "status", "--porcelain", "src"], capture_output=True, text=True).stdout.strip()
print("src 变更行数:", len(st.split("\n")) if st else 0)

print("=== A2 类型单一化 (Roslyn) ===")
p = subprocess.run([os.path.join(ROOT, "tools/refactor/reftool/bin/Debug/net10.0/reftool"), "extract", "--apply",
                    "--manifest", "/tmp/r526-manifest2.json"], cwd=ROOT, capture_output=True, text=True)
print(p.stdout.strip().split("\n")[-1])
print(p.stderr.strip()[:300])
sys.exit(p.returncode)
