#!/usr/bin/env python3
"""R526-2: 巨类拆分 (IndustrialAgentV2 3,208 行 → 主文件 + 3 partial)。
   先摘除跨文件失效的 #region/#endregion, 再按成员边界切分。"""
import io, re, subprocess, sys

ROOT = "/home/agentuser/AgentFramework"
F = ROOT + "/src/agent/IndustrialAgentV2.cs"
t = io.open(F, encoding="utf-8").read()
before = len([l for l in t.split("\n") if l.strip().startswith("#region") or l.strip().startswith("#endregion")])
t2 = "\n".join(l for l in t.split("\n") if not (l.strip().startswith("#region") or l.strip().startswith("#endregion")))
t2 = re.sub(r"\n{3,}", "\n\n", t2)
io.open(F, "w", encoding="utf-8", newline="").write(t2)
print(f"摘除 region 指令 {before} 行; 行数 {len(t.splitlines())} → {len(t2.splitlines())}")

T = os.path.join(ROOT, "tools/refactor/reftool/bin/Debug/net10.0/reftool")
args = [T, "split", "src/agent/IndustrialAgentV2.cs", "IndustrialAgentV2",
        "Commands=HandleModelCommand", "Plan=PlanResumeFallthrough", "Context=AssembleContextAsync"]
if "--apply" in sys.argv:
    args.append("--apply")
    args += ["--manifest", "/tmp/r526-split-manifest.txt"]
p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
print(p.stdout.strip())
print(p.stderr.strip()[:400])
sys.exit(p.returncode)
