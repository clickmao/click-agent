#!/usr/bin/env python3
"""R521 登记表追加 (程序化改写纪律: 先证序列化器逐字节复现原文件, 再改写; 幂等; 改写后读回校验)。"""
import json
import sys

PATH = "docs/verification-registry.json"

NEW_ROWS = [
    {
        "id": "external.contrast-games-longtask-r521",
        "level": "L3",
        "capability": (
            "主线对照**三臂同窗**读数 (R521, games-longtask-v1 · 58 用例 · 同 adapter 窗口 w2 · "
            "双侧同模型 deepseek-chat · 二进制 /tmp/pub_r520/agenthost sha256 a0ac9695…): "
            "臂 A 本侧单轮 (--max-steps 32) **58/58** 用例级全对 (19 上游调用 / 302,809 tok / 66.1 s / 17 工具步); "
            "臂 C 外部真值 codex-cli **58/58** (5 调用 / 46,372 tok / 25.1 s); 臂 O 本侧编排器 5 节点×8 步 **31/58** "
            "(30 调用 / 429,908 tok / 117.8 s)。⇒ 质量面 A=C 打平 (回复质量不降); 效率面本侧 A = codex 的 6.53× tok "
            "⇒ **不比外部真值省** (跨实现方向读数)。R413 的 token ↓≥30% 判据本轮**无同窗关闸消融臂 ⇒ 未测, 不宣称降幅**。"
            "按铁律 11 的前置器 `exec_precondition.py --round r521` ⇒ **rc=1** (预注册 evidence_scope 用 w1/* 窗口名, "
            "该窗因器具缺陷作废 ⇒ w2/agentO 未声明 ⇒ fail-closed) ⇒ 上述读数一律标**「参考 (未可验收)」**。"
        ),
        "covers": [
            "eval/rover/r521/run_r521.sh",
            "eval/rover/r521/prereg-r521.json",
            "eval/rover/r521/REPORT-r521.md",
            "eval/rover/r521/evidence/windows/w2/report.json",
            "eval/rover/r521/diag-orch-r521.md",
        ],
        "evidence_cmd": (
            "R521_WINDOW=w2 bash eval/rover/r521/run_r521.sh && "
            "python3 eval/rover/r507pre/exec_precondition.py --round r521"
        ),
        "evidence_path": "eval/rover/r521/REPORT-r521.md",
        "evidence_generated_with": (
            "AOT /tmp/pub_r520/agenthost 真机三臂同窗 (run-0917-154115); 判分权威 = 仓内不可变快照 "
            "eval/rover/r521/snapshots/w2/*; 断言 `_claimed_rows` 自报 vs 实测一致 (SELF_REPORT_AGREES=True)"
        ),
        "negative_control": (
            "① 编排臂单次读数不可用: 同器具同题面 O 在 w1=9/58、w2=31/58 ⇒ 摆动 22 用例; "
            "② w1 作废窗读数保留于 eval/rover/r521/nc/w1-armA-no-steps/ (C 58/58 · O 9/58); "
            "③ 逐用例定因见 diag-orch-r521.md (life 输出字母表错 0/14 · sub 首行未跳过崩溃 0/14 · nim 非规范最小解 5/15 · wythoff WIN 后丢两整数 4/15)"
        ),
        "owner_round": "R521",
    },
    {
        "id": "eval.freeze-empty-arm-failclosed-r521",
        "level": "L2",
        "capability": (
            "**缺臂/空产物 fail-closed** (R521 真机自抓器具缺陷修复): 冻结器 `freeze_r521.py` 原实现对产物为空的臂 "
            "**静默跳过** (os.walk 零迭代 ⇒ 目标目录不落盘), 而前置器 `exec_precondition.py` 只遍历已存在的快照目录 "
            "⇒ 零产物臂既不判分也不阻断 ⇒ **rc=0 假绿** (R521 w1 实测: 臂 A 0 字节, 前置器仍报可验收)。"
            "判据: `emit()` 必先 `makedirs(dst)` 再拷树 ⇒ 空臂也落盘, 行内记 `snapshot_empty: true`; "
            "配套 `run_r521.sh` 起臂后**产物非空断言** (空则打印 PRODUCT_EMPTY 且不得静默)。"
        ),
        "covers": [
            "eval/rover/r521/freeze_r521.py",
            "eval/rover/r521/run_r521.sh",
            "eval/rover/r507pre/exec_precondition.py",
            "eval/rover/r521nc/prereg-r521nc.json",
        ],
        "evidence_cmd": (
            "python3 eval/rover/r507pre/exec_precondition.py --round r521nc "
            "(负控面板: snapshots/w1/agentA 为**空树** + 自报 all_pass=true ⇒ 期望 rc=1)"
        ),
        "evidence_path": "eval/rover/r521/nc/w1-armA-no-steps/README.md",
        "evidence_generated_with": (
            "负控机检: BLOCKED w1/agentA/g1 0/58 · SELF_REPORT_AGREES=False · rc=1 (空树不再假绿); "
            "修复前后对比 = w1 前置器 rc=0 (假绿) vs 负控 r521nc rc=1"
        ),
        "negative_control": (
            "过宽负控: 真产物树不受影响 —— w2 的 agentA/agentO/codex 三快照照常判分 (58/58 · 31/58 · 58/58), "
            "即修复只把「空」判成不可验收, 不改变已有产物的判分结果"
        ),
        "owner_round": "R521",
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
    doc["updated_round"] = "R521"
    out = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    open(PATH, "w", encoding="utf-8").write(out)
    print("ADDED=%d ROWS_TOTAL=%d" % (added, len(doc["rows"])))
    back = json.loads(open(PATH, encoding="utf-8").read())
    assert back["updated_round"] == "R521"
    ids = [r["id"] for r in back["rows"]]
    assert len(ids) == len(set(ids)), "重复 id"
    print("READBACK_OK rows=%d updated_round=%s" % (len(back["rows"]), back["updated_round"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
