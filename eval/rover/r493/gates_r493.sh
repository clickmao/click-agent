#!/usr/bin/env bash
# R493 形式门禁: (1) 判据器自检 (正控=真机实发答复, 负控=合成族) (2) 三臂判据 (3) 构建 + 形式门禁三真名 + 执行数>0 断言 (4) 全量单测
# 口径: 任一步非 0 ⇒ 非 0 退出 (fail-closed); 不打印任何凭据。
set -uo pipefail
export DOTNET_ROOT="$HOME/.dotnet"
DOTNET="$HOME/.dotnet/dotnet"
cd /home/agentuser/AgentFramework || exit 1
echo "=== [1] 判据器自检 (R493 judge_adv_r493 --selftest) ==="
python3 eval/rover/r493/judge_adv_r493.py --selftest || { echo "[RED] 判据器自检失败"; exit 3; }
echo "=== [2] 三臂判据 (analyze_r493) ==="
python3 eval/rover/r493/analyze_r493.py || { echo "[RED] 判据器执行失败"; exit 4; }
python3 - <<'PY' || exit 5
import json
d = json.load(open("eval/rover/r493/verdict-r493.json", encoding="utf-8"))
print("  gate.pass =", d["gate"]["pass"], "| 阻断失败 =", d["gate"]["blocking_fail"] or "无")
if not d["gate"]["pass"]:
    raise SystemExit("[RED] 判据门未过 (阻断不变量失败或假设为 False)")
PY
echo "=== [2b] 落档形式门禁 (report/master-plan/improvements/registry) ==="
python3 - <<'PY' || exit 6
import json, os, re
R = "/home/agentuser/AgentFramework"
rep = os.path.join(R, "docs/reports/r493-adv-family-hardening-judge-supersede.md")
txt = open(rep, encoding="utf-8").read()
assert "R493" in txt and "-73.36" in txt, "报告缺 R493 主读数"
reg = json.load(open(os.path.join(R, "docs/verification-registry.json"), encoding="utf-8"))
assert reg["updated_round"] == "R493", "registry updated_round 未推进"
ids = [r["id"] for r in reg["rows"]]
for want in ("r493.adv-family-hardening", "r493.judge-structural-supersede"):
    assert want in ids, "缺登记行 %s" % want
for r in reg["rows"]:
    if r["id"].startswith("r493."):
        for f in ("id", "level", "capability", "evidence_cmd", "evidence_path", "owner_round"):
            assert r.get(f), "%s 缺字段 %s" % (r["id"], f)
        assert r["level"] == "L2" and r["owner_round"] == "R493"
        for c in r["covers"]:
            assert os.path.exists(os.path.join(R, c)), "covers 路径不存在: %s" % c
mp = open(os.path.join(R, "docs/reports/iteration-master-plan.md"), encoding="utf-8").read()
assert "## R493" in mp, "主计划未追加 R493 段"
imp = open(os.path.join(R, "docs/improvements.md"), encoding="utf-8").read()
assert "下轮候选 (R494" in imp, "improvements 未追加 R494 候选"
print("  [OK] 报告/主计划/候选/登记行 形式检查通过; rows=%d" % len(reg["rows"]))
PY
echo "=== [3] 构建 (Release) ==="
"$DOTNET" build src/agent.tests/agentframework.tests.csproj -c Release 2>&1 | tail -3
echo "=== [3b] 形式门禁 (真名: VerificationFormTests|DevPlanDocRefTests|SkillGeneralizationTests) ==="
res=$(env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR "$DOTNET" test src/agent.tests/agentframework.tests.csproj -c Release --no-build \
  --filter "FullyQualifiedName~VerificationFormTests|FullyQualifiedName~DevPlanDocRefTests|FullyQualifiedName~SkillGeneralizationTests" 2>&1)
echo "$res" | tail -4
n=$(echo "$res" | grep -oE "Passed:[ ]+[0-9]+" | grep -oE "[0-9]+" | head -1)
f=$(echo "$res" | grep -oE "Failed:[ ]+[0-9]+" | grep -oE "[0-9]+" | head -1)
if [ -n "${n:-}" ] && [ "$n" -gt 0 ]; then echo "  [OK] 执行数=$n failed=${f:-0}"; else echo "  [VOID] 执行数=0 ⇒ 假绿"; exit 1; fi
[ "${f:-0}" = "0" ] || { echo "  [RED] 形式门禁有失败用例"; exit 2; }
echo "=== [4] 全量单测 ==="
res2=$(env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR "$DOTNET" test src/agent.tests/agentframework.tests.csproj -c Release --no-build 2>&1)
echo "$res2" | tail -4
n2=$(echo "$res2" | grep -oE "Passed:[ ]+[0-9]+" | grep -oE "[0-9]+" | head -1)
f2=$(echo "$res2" | grep -oE "Failed:[ ]+[0-9]+" | grep -oE "[0-9]+" | head -1)
if [ -n "${n2:-}" ] && [ "$n2" -gt 0 ]; then echo "  [OK] 全量执行数=$n2 failed=${f2:-0}"; else echo "  [VOID] 全量执行数=0 ⇒ 假绿"; exit 1; fi
[ "${f2:-0}" = "0" ] || { echo "  [RED] 全量单测有失败用例"; exit 2; }
echo "R493_GATE_DONE"
