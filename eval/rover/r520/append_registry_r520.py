#!/usr/bin/env python3
"""R520 登记表追加 (程序化改写纪律: 先证序列化器逐字节复现原文件, 再改写; 幂等; 改写后读回校验)。"""
import json
import sys

PATH = "docs/verification-registry.json"

NEW_ROWS = [
    {
        "id": "agent.shadow-path-gate",
        "level": "L3",
        "capability": (
            "工作区**影子路径闸** (R520, 真机自抓缺陷修复): 相对路径重复工作区自身位置时 "
            "(实证请求 `eval/rover/r519/run-0917-144416/orch/ws/games/life.py`) 会在工作区内重建影子副本, "
            "而写入仍回 ok + 回显请求串 ⇒ 节点读到另一份文件并自述「环境预置的另一版实现」, 随后被范围闸判 "
            "out_of_scope ⇒ 整条编排 fail-closed (R519 编排臂 0/58 的唯一读数)。判据: (a) 相对路径以根完整路径 "
            "(去前导分隔符) 开头, 或 (b) 前 k 段 (k>=2) == 根路径后 k 段 ⇒ 拒绝并给出落点与建议改写; "
            "单段同名目录不判 (防过宽); 与 P1 边界同闸常量 (AGENTFRAMEWORK_ACTION_BOUNDARY=0 ⇒ 同关)。"
        ),
        "covers": [
            "src/agent/action/WorkspaceActionPort.cs",
            "src/agent.host/OrchestrateCommand.cs",
            "src/agent.tests/R520ShadowPathTests.cs",
        ],
        "evidence_cmd": (
            "dotnet test src/agent.tests/agentframework.tests.csproj --filter "
            "\"FullyQualifiedName~R520ShadowPath|FullyQualifiedName~R498Boundary|FullyQualifiedName~R511Delete|"
            "FullyQualifiedName~ActionLoop\" --nologo -v q"
        ),
        "evidence_path": "eval/rover/r520/REPORT-r520.md",
        "evidence_generated_with": (
            "AOT /tmp/pub_r520/agenthost (15,609,168 B) 真机复跑: 5/5 节点 Completed, 范围违规 0, "
            "影子文件 0 (磁盘级独立机检 eval/rover/r520/shadow_check_r520.py GREEN); 单测 40/40"
        ),
        "negative_control": (
            "① 消融臂: AGENTFRAMEWORK_ACTION_BOUNDARY=0 ⇒ 同一影子写**成功**且影子文件确实出现 "
            "(证明拒绝非恒真, R520ShadowPathTests); ② 前态真机症状: R519 真机 ws 上独立机检 RED 1 条 "
            "(form-b 前 6 段重复根尾) + 该轮 n1 Failed/n2-n5 未执行; ③ 过宽负控: 区内正常/深层嵌套/"
            "单段同名目录/越界语义不变 4 条均照常通过"
        ),
        "owner_round": "R520",
    },
    {
        "id": "external.contrast-orch-arm-r520",
        "level": "L3",
        "capability": (
            "主线对照**编排臂**读数 (R520, 修复后首次可测): 同题面 (plan/scope 与 R519 md5 同源 "
            "1c84c4be… / dc9793be…) 5 节点 × 8 步 + --scope, AOT 真机 ⇒ 完成 **5/5** · 范围违规 **0** · "
            "预算上界 40 步 · 升预算重试 0 次; 落盘 games/{__init__,life,sub,nim,wythoff,__main__}.py; "
            "58 用例**用例级 9/58** (整题全对率 0) ⇒ 产物可执行但未正确, 按铁律 11 属未过可验收前置。"
        ),
        "covers": [
            "eval/rover/r520/run_r520.sh",
            "eval/rover/r520/prereg-r520.json",
            "eval/rover/r520/run-0917-145837/orch/report.json",
        ],
        "evidence_cmd": (
            "bash eval/rover/r520/run_r520.sh && python3 eval/rover/r520/grade_r520.py "
            "--dir <run>/orch/ws --out <run>/grade-orch.json"
        ),
        "evidence_path": "eval/rover/r520/run-0917-145837/",
        "evidence_generated_with": (
            "AOT /tmp/pub_r520/agenthost; 判据器 grade_r520.py 与 grade_r519.py md5 相同 "
            "(9c8a00043ef2b235e4929a024ea16dea), 对 R519 同一 ws 复跑得 rc=1/total=58/passed=0 逐位相同"
        ),
        "negative_control": (
            "前态 (R519 同题面同判据器): 1/5 节点完成 · 范围违规 1 · 影子文件 1 · 0/58 —— 与修复后逐项对照"
        ),
        "owner_round": "R520",
    },
]


def main():
    original = open(PATH, encoding="utf-8").read()
    doc = json.loads(original)
    if json.dumps(doc, ensure_ascii=False, indent=2) + "\n" != original:
        print("FAIL: 序列化器不能逐字节复现原文件 ⇒ 拒绝程序化改写 (改用文本插入)")
        return 2
    have = {r.get("id") for r in doc["rows"]}
    added = 0
    for row in NEW_ROWS:
        if row["id"] in have:
            print("SKIP (幂等):", row["id"])
            continue
        doc["rows"].append(row)
        added += 1
    doc["updated_round"] = "R520"
    out = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    open(PATH, "w", encoding="utf-8").write(out)
    print("ADDED=%d ROWS_TOTAL=%d" % (added, len(doc["rows"])))
    back = json.loads(open(PATH, encoding="utf-8").read())
    assert back["updated_round"] == "R520"
    ids = [r["id"] for r in back["rows"]]
    assert len(ids) == len(set(ids)), "重复 id"
    print("READBACK_OK rows=%d updated_round=%s" % (len(back["rows"]), back["updated_round"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
