#!/usr/bin/env bash
# R494 形式门禁 (承 R493 gates_r493.sh 结构):
#   [0] 轮内产物在场 (prereg/flags/usage/calls/assert-face/audit)
#   [1] 收口断言 (逐臂 assert_face_r494.py, fail-closed)
#   [2] 读数器 (analyze_r494.py) + 判据门 (阶梯与验收口径读数必须存在)
#   [3] 落档形式检查 (报告/主计划/改进/登记行)
#   [4] 构建 + 形式门禁三真名 + 全量单测
# 口径: 任一步非 0 ⇒ 非 0 退出; 不打印任何凭据。
set -uo pipefail
export DOTNET_ROOT="$HOME/.dotnet"
DOTNET="$HOME/.dotnet/dotnet"
cd /home/agentuser/AgentFramework || exit 1

echo "=== [0] 轮内产物在场 ==="
for f in prereg_r494.json grid/task-p12-adv.json flags-B.json flags-T0.json flags-T1.json \
         calls-B.jsonl calls-T0.jsonl calls-T1.jsonl usage-B.jsonl usage-T0.jsonl usage-T1.jsonl; do
  [ -s "eval/rover/r494/$f" ] || { echo "[RED] 缺产物 eval/rover/r494/$f"; exit 2; }
done
echo "  [OK] 产物齐"

echo "=== [1] 收口断言 (逐臂) ==="
for a in B T0 T1; do
  ch=off; [ "$a" = "T1" ] && ch=on
  python3 eval/rover/r494/assert_face_r494.py --arm "$a" --dir eval/rover/r494 --channel "$ch" \
    || { echo "[RED] $a 收口断言红"; exit 3; }
done

echo "=== [2] 读数器 + 判据门 ==="
python3 eval/rover/r494/analyze_r494.py || { echo "[RED] 读数器失败"; exit 4; }
python3 - <<'PY' || exit 5
import json
d = json.load(open("eval/rover/r494/kpi-r494.json", encoding="utf-8"))
arm = d["arms"]
assert {"B", "T0", "T1"} <= set(arm), "三臂不全"
assert arm["T1"]["iso_calls_with_tools"] == 0, "T1 隔离通道仍带工具 (实发面红)"
assert d["acceptance"], "验收口径读数缺失"
print("  [OK] 阶梯 %s" % [l["pair"] for l in d["ladder"]])
print("  同窗 B→T1 tokens %.2f%% (目标 -30%%)" % (-float(d["acceptance"]["tokens_drop_pct"])))
PY

echo "=== [3] 落档形式检查 ==="
python3 - <<'PY' || exit 6
import json, os
R = "/home/agentuser/AgentFramework"
rep = os.path.join(R, "docs/reports/r494-isolated-channel-tool-decl.md")
txt = open(rep, encoding="utf-8").read()
assert "R494" in txt, "报告缺轮号"
for kw in ("通道轴", "同窗", "诚实边界"):
    assert kw in txt, "报告缺要素 %s" % kw
reg = json.load(open(os.path.join(R, "docs/verification-registry.json"), encoding="utf-8"))
assert reg["updated_round"] == "R494", "registry updated_round 未推进"
ids = [r["id"] for r in reg["rows"]]
for want in ("r494.isolated-channel-tool-decl", "r494.isolated-channel-realmachine-ladder", "r494.capability-face-readonly-audit"):
    assert want in ids, "缺登记行 %s" % want
for r in reg["rows"]:
    if r["id"].startswith("r494."):
        for f in ("id", "level", "capability", "evidence_cmd", "evidence_path", "owner_round"):
            assert r.get(f), "%s 缺字段 %s" % (r["id"], f)
        assert r["level"] in ("L1", "L2") and r["owner_round"] == "R494"
        for c in r["covers"]:
            assert os.path.exists(os.path.join(R, c)), "covers 路径不存在: %s" % c
mp = open(os.path.join(R, "docs/reports/iteration-master-plan.md"), encoding="utf-8").read()
assert "## R494" in mp, "主计划未追加 R494 段"
imp = open(os.path.join(R, "docs/improvements.md"), encoding="utf-8").read()
assert "下轮候选 (R495" in imp, "improvements 未追加 R495 候选"
print("  [OK] 报告/主计划/候选/登记行 形式检查通过; rows=%d" % len(reg["rows"]))
PY

echo "=== [4] 构建 + 形式门禁三真名 ==="
"$DOTNET" build src/agent.tests/agentframework.tests.csproj -c Release 2>&1 | tail -3
res=$(env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR "$DOTNET" test src/agent.tests/agentframework.tests.csproj -c Release --no-build \
  --filter "FullyQualifiedName~VerificationFormTests|FullyQualifiedName~DevPlanDocRefTests|FullyQualifiedName~SkillGeneralizationTests" 2>&1)
echo "$res" | tail -3
echo "$res" | grep -qE "Passed!" || { echo "[RED] 形式门禁三真名未全过"; exit 7; }

echo "=== [5] 全量单测 ==="
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR "$DOTNET" test src/agent.tests/agentframework.tests.csproj -c Release --no-build 2>&1 | tail -4
echo "[R494 门禁] 通过"
