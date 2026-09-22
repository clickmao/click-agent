#!/usr/bin/env python3
"""R631 · verification-registry 追加一行（L3 真机运行）。派生自 r630 同名件（纪律逐字沿袭）:
① 改前断言序列化器逐字节复现原文件; ② 只追加一行, 不动既有行; ③ 幂等; ④ 写后读回。
用法: python3 eval/rover/r631/add_registry_row_r631.py [--apply]
"""
import hashlib
import io
import json
import os
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
REG = os.path.join(REPO, "docs/verification-registry.json")
NEW = {
    "id": "r631.exec-axis-replication",
    "level": "L3",
    "owner_round": "R631",
    "capability": (
        "执行面轴 `AGENTFRAMEWORK_R1_ACTION_EXEC`（T=1 执行面读采纳候选映射 vs C=产品缺省）在**与历史不相交**的新窗集 "
        "w223/w224（reps=3/窗 + codex 外部真值 ×1/窗，同一枚 AOT 件 cefd045e8d1d，零产品源码改动）上**跨窗复现**："
        "J4a 复现判据**不通过** ⇒ 逐窗配对 Δ(T−C) 全对率 {w223 −0.3333, w224 +0.3333}、中位 **0**（R621 +33pt 未复现）"
        "⇒ 该轴判**非承重变量、定案关闭**（禁再为同一缺口加轮）；J4b 对外部真值在**唯一可靠窗** w223 上 D=0 持平"
        "（w224 真值自败 56/58 ⇒ 按 R4 标 unreliable 不并入）。成本三列（中继 dump 时间轴）两产品臂**相等**"
        "（T 1.83/1555/4491 vs C 1.83/1513/4434；codex 5.5/4195/3872）⇒ 该轴既非质量亦非成本杠杆。"
        "**诚实边界: 铁律 11 前置器 rc=1（验收面 w223/agentT-r1 54/58 · w224/agentT-r1 51/58 · w224/agentT-r3 46/58）"
        "⇒ 全部读数标「参考（未可验收）」；裁判件 `judge_r631.py` 判据族与预注册不同源（旧草稿残留）⇒ 其判决不予采用，"
        "本轮判决取自冻产后处理复算；n=2 窗欠功率只作趋势。**"
    ),
    "evidence_cmd": (
        "bash eval/rover/r631/run_r631.sh && python3 eval/rover/r631/recompute_j4ab_r631.py && "
        "python3 eval/rover/r507pre/exec_precondition.py --round r631"
    ),
    "evidence_path": "docs/evidence/RF0001/R631-exec-axis-replication.md",
    "evidence_generated_with": {
        "evidence_kind": "artifact",
        "pin_status": "live",
        "pin_reason": "worktree-only",
        "artifact_sha12": None,
        "instrument": "eval/rover/r631/recompute_j4ab_r631.py",
        "instrument_sha12": hashlib.sha256(
            io.open(os.path.join(REPO, "eval/rover/r631/recompute_j4ab_r631.py"), "rb").read()).hexdigest()[:12],
        "binding": "audit-pin",
        "audited_by_round": "R631",
    },
    "negative_control": (
        "① 前置器通配声明修复的**两侧样例**（R631 自捕器件缺陷 D1）: 正控 = 修后 `--round r631` 输出 `DECLARED_ABSENT=-` "
        "（修前 2 条假红 `w223/agentT-r*`/`w224/agentT-r*`，而 `snapshots/w223/{agentT-r1,r2,r3}` 在盘）且 rc 不变=1；"
        "负控 = 注入字面缺席名 `w223/agentT-r9` ⇒ 仍报 `DECLARED_ARM_ABSENT w223/agentT-r9`（牙在）并附判 `VERDICT_POSTHOC_ONLY`；"
        "② **历史判决审计**（判决中性证明）: r550 修后重放 `declared_absent` 3→3、rc 1→1 不变（该轮 3 条为字面名 `agentR550on2-g1`，与本修无关）"
        "⇒ 本修只消除通配声明的假红，不改写任何既有判决；③ 判决面**不采信裁判件自报**: `judge_r631.py` 判据族与预注册不同源，"
        "改用冻产后处理复算（幂等、零重测）并披露；④ `decl_sweep --apply` ⇒ `checked=30 drifted=0`（登记面零漂移）。"
    ),
    "note": (
        "轮次工件: eval/rover/r631/{prereg,judge,kpi-table,verdict,verdict-j4ab,bins,gate-margin,premise}-r631.* + "
        "dag-r631.md + evidence/windows/** + snapshots/**。未行使 R529 J4(b) `unreliable_policy`（`POLICY_ACTIVE=False "
        "reason=no_policy_key`）⇒ w224 真值自败窗未被机检降级，列入 R632 起手清单。跨轮禁相减（RF0005 §6 红线 4）。"
    ),
}


def main():
    apply = "--apply" in sys.argv
    raw = io.open(REG, encoding="utf-8").read()
    d = json.loads(raw)
    ok = None
    for indent in (1, 2, None):
        for ea in (False, True):
            for tail in ("\n", ""):
                if json.dumps(d, ensure_ascii=ea, indent=indent) + tail == raw:
                    ok = (indent, ea, tail)
    if ok is None:
        print("SER_ASSERT=FAIL ⇒ 拒改")
        return 3
    print("SER_ASSERT=OK %s" % (ok,))

    rows = []

    def walk(o):
        if isinstance(o, list):
            for x in o:
                walk(x)
        elif isinstance(o, dict):
            if o.get("id") == NEW["id"]:
                rows.append(o)
            for v in o.values():
                walk(v)

    walk(d)
    if rows:
        print("IDEMPOTENT (行已存在)")
        return 0
    target = None
    for k, v in d.items():
        if isinstance(v, list) and any(isinstance(x, dict) and "id" in x for x in v):
            target = v
            print("APPEND_TARGET list key=%s (n=%d)" % (k, len(v)))
    if target is None:
        print("DEFECT: 找不到登记行容器")
        return 2
    target.append(NEW)
    if not apply:
        print("DRY_RUN")
        return 0
    indent, ea, tail = ok
    io.open(REG, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=ea, indent=indent) + tail)
    back = json.load(io.open(REG, encoding="utf-8"))
    hit = [x for x in back.get("rows", []) if isinstance(x, dict) and x.get("id") == NEW["id"]]
    print("READBACK_ROWS=%d" % len(hit))
    print("NUMSTAT:", subprocess.run(["git", "diff", "--numstat", "docs/verification-registry.json"],
                                     cwd=REPO, capture_output=True, text=True).stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
