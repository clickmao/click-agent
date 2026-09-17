#!/usr/bin/env python3
"""R526: 单类型单文件 + 容器文件改名后, 同步修正 ① 登记表 covers 路径 ② 四处源码路径钉死的测试。"""
import io, json, os, re

ROOT = "/home/agentuser/AgentFramework"
os.chdir(ROOT)

COVERS_MAP = {
    "src/agent.frontendapi/FrontendTaskEvents.cs": "src/agent.frontendapi/FrontendTaskRegistry.cs",
    "src/agent.llamacpp/LlamaCppJson.cs": "src/agent.llamacpp/CompletionRequest.cs",
    "src/agent.llamacpp/LocalPrompt.cs": "src/agent.llamacpp/LocalPromptGate.cs",
    "src/agent.modelqueue/ActionLoop.cs": "src/agent.modelqueue/ActionLoopRunner.cs",
    "src/agent.modelqueue/LocalGenerationPort.cs": "src/agent.modelqueue/TurnGateJudge.cs",
    "src/agent.modelqueue/OpenAIChatResponseDtos.cs": "src/agent.modelqueue/OpenAIChatUsage.cs",
    "src/agent.recall.tests/RecallModuleTests.cs": "src/agent.recall.tests/RecallIncrementalTests.cs",
    "src/agent.recall/RecallFingerprint.cs": "src/agent.recall/RecallDirtyScan.cs",
    "src/agent.recall/RecallLinks.cs": "src/agent.recall/RecallLinksFile.cs",
    "src/agent.recall/RecallUpdater.cs": "src/agent.recall/RecallIndexUpdater.cs",
    "src/agent/execution/FileLocking.cs": "src/agent/execution/OccupantDetector.cs",
    "src/agent/registry/ArtifactRepair.cs": "src/agent/registry/ArtifactRepairLoop.cs",
}
for old, new in COVERS_MAP.items():
    assert os.path.exists(new), new

reg = "docs/verification-registry.json"
d = json.load(io.open(reg, encoding="utf-8"))
rows = d["rows"] if isinstance(d, dict) else d
n = 0
for r in rows:
    c = r.get("covers") or []
    out, hit = [], False
    for x in c:
        if x in COVERS_MAP:
            hit = True
            if COVERS_MAP[x] not in out:
                out.append(COVERS_MAP[x])
        else:
            out.append(x)
    if hit:
        r["covers"] = out
        n += 1
io.open(reg, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print(f"登记表 covers 修正 {n} 行")

TEST_MAP = [
    ("src/agent.tests/ExecutorHardeningTests.cs",
     '"src", "agent", "execution", "FileLocking.cs"',
     '"src", "agent", "execution", "OccupantDetector.cs"'),
    ("src/agent.tests/R524PrefixStabilityTests.cs",
     'Path.Combine("src", "agent.modelqueue", "ActionLoop.cs")',
     'Path.Combine("src", "agent.modelqueue", "ActionLoopRunner.cs")'),
    ("src/agent.tests/R497FingerprintAndSynonymTests.cs",
     '"src", "agent.modelqueue", "LocalGenerationPort.cs"',
     '"src", "agent.modelqueue", "TurnGateJudge.cs"'),
]
for p, old, new in TEST_MAP:
    t = io.open(p, encoding="utf-8").read()
    if old not in t:
        print(f"  !! 未匹配 {p}: {old}")
        continue
    t = t.replace(old, new)
    io.open(p, "w", encoding="utf-8", newline="").write(t)
    print(f"  ✓ {p}")
