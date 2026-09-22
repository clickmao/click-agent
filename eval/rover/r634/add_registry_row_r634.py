#!/usr/bin/env python3
"""R634 · verification-registry 追加一行（L3 真机运行）。派生自 r631/r633 同族件（纪律逐字沿袭）:
① 改前断言序列化器逐字节复现原文件; ② 只追加一行, 不动既有行; ③ 幂等; ④ 写后读回 + numstat。
用法: python3 eval/rover/r634/add_registry_row_r634.py [--apply]
"""
import hashlib
import io
import json
import os
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
REG = os.path.join(REPO, "docs/verification-registry.json")
INSTR = os.path.join(REPO, "eval/rover/r634/judge_r634.py")

NEW = {
    "id": "r634.mainline-criterion-fix",
    "level": "L3",
    "owner_round": "R634",
    "capability": (
        "主线对照轮（**新窗集 w228/w229/w230**，与历史 w184..w227 不相交；产品默认档 ×3/窗 + codex 外部真值 ×1/窗；"
        "同一枚 AOT 件 cefd045e8d1d，零产品源码改动 / 零新增夹具 / 零新增开关）：**R633 登记的判据构造缺陷"
        "（窗有效性绑真值整题全对 ⇒ 有效窗恒 0 ⇒ 主判据原理不可判）已按新预注册修正并落地** ⇒ 有效窗 **0 → 3**"
        "（`W_floor` 由 `NO_RESOLUTION` 变为可判；真值自败例单列于 `truth_self_failed_cases`）。"
        "修正后主判据读数 = **不达**：逐窗配对差 D = **0 / −3 / −5**（中位 **−3**，阈值中位 ≥ −2 ∧ 逐窗 ≥ −15）；"
        "次级 Q2 整题全对率**劣化**（P 3/9 = 0.3333 vs 真值 2/3 = 0.6667）⇒ rc=1。"
        "成本三列（中继 dump 时间轴）P 18 调用 / 15,480 新算 / 42,987 completion（命中 v_all 中位 0.9083 / v_incr 0.8483）"
        "vs 真值 25 / 13,755 / 12,283（0.9336 / 0.9675）⇒ **调用 −28% 但新算 prompt +12.5%、completion 3.5×**。"
        "事后复算（零重测，冻结快照 12 棵树独立重放）：`rc≠0 ∧ stdout 正确` = **0/12** ⇒「冻结判分器退出码优先造成"
        "真值低估」**证伪**（假阴性负控 = 0），且复算数与冻结判分器**逐条同数** ⇒ 判分器可复现。"
        "**诚实边界：铁律 11 前置器 rc=1（自捕 E2：预注册缺 `evidence_scope` ⇒ 验收面退化为全局口径，含真值自败窗 "
        "w229 56/58 ⇒ 恒不可满足；本轮按原文照判、**不事后激活**）⇒ 质量/成本标「参考（未可验收）」；"
        "无单变量轴 ⇒ 不计为单变量轮、禁跨轮相减；n=9/3 欠功率；摆动面（R571 登记同臂跨窗极差 14–15 例）> 本轮效应。**"
    ),
    "evidence_cmd": (
        "bash eval/rover/r634/run_r634.sh && python3 eval/rover/r634/judge_r634.py "
        "--D $HOME/.agentframework/harness/runs/r634 --pd eval/rover/r634 && "
        "python3 eval/rover/r634/judge_r634.py --D /tmp/none --pd eval/rover/r634 --selftest && "
        "python3 eval/rover/r507pre/exec_precondition.py --round r634 && "
        "python3 eval/rover/r634/codex_stdout_first_r634.py"
    ),
    "evidence_path": "docs/evidence/RF0001/R634-mainline-new-windows.md",
    "evidence_generated_with": {
        "evidence_kind": "artifact",
        "pin_status": "live",
        "pin_reason": "worktree-only",
        "artifact_sha12": None,
        "instrument": "eval/rover/r634/judge_r634.py",
        "instrument_sha12": hashlib.sha256(io.open(INSTR, "rb").read()).hexdigest()[:12],
        "binding": "audit-pin",
        "audited_by_round": "R634",
    },
    "covers": [
        "eval/rover/r634/judge_r634.py",
        "eval/rover/r634/run_r634.sh",
        "eval/rover/r634/prereg-r634.json",
        "eval/rover/r634/codex_stdout_first_r634.py",
        "eval/rover/r634/cases/run_cases_r521.py",
        "eval/rover/r507pre/exec_precondition.py",
        "docs/evidence/RF0001/R634-mainline-new-windows.md",
        "冻结题集双钉（文件 sha e0c667c2… + payload sha e7ddce02…；aux 同批携带 sha d9aecf4d…）与新窗集不相交（w228..w230）",
        "逐窗配对 D 报告面（P 中位 − 真值中位）与有效窗口径（真值跑通 ∧ 非自败例 ≥1）",
    ],
    "negative_control": (
        "五组成对/负向控制（现场执行，读数入 verdict-r634.json / selftest-r634.json）："
        "① **判据修正的两侧成对（最承重）**——六态影子自检中 `TRUTH_SELF_FAIL_NOW_VALID`（真值自败但跑通）"
        "**正控** = 有效窗 3（修正确实解除不可判）；`TRUTH_VOID`（真值挂死）**负控** = w229 仍判 `unreliable` 剔除"
        "（修正**不放宽**另一侧）；另 `MISSING_TRUTH` ⇒ `NO_RESOLUTION`、`EQUAL`/`WORSE_BY_3` 两侧样例齐备。"
        "② **假阴性负控**——冻结判分器为退出码优先（`ok = (rc==0) ∧ (stdout==expected)`），"
        "`rc≠0 ∧ stdout 正确` = **0/12 棵树**（含全部 4 臂）⇒「真值/产品被低估」假设证伪；"
        "同件复算读数与冻结判分器**逐条同数**（w228 58/58/58/49 · w229 56/53/58/50 · w230 58/55/53/44）⇒ 判分器可复现。"
        "③ **锚面口径两侧样例**——有提示面跑次 **9/9 == legacy 锚**（正控）；waiver 要求"
        "`all_missing_are_void_or_timeout=True` 才给适用面 PASS（本轮 `missing_runs=[]`）⇒ 缺项不得读成漂移、不抬 rc=2。"
        "④ **声明漂移自捕（E1）**——沿袭串（R633 的「13/14/15 条 rc=1」）在 R634 判据器里失真 ⇒ 改为"
        "**由复算件逐行派生**（`codex_rc_ne_stdout_ok` / `all_arms_rc_ne_stdout_ok`）；器具改后 `decl_sweep --check`"
        "= `checked=30 drifted=0`（登记面零漂移）。"
        "⑤ **验收面不可满足的复现（E2）**——`SCOPE_SOURCE=None ∧ POLICY_ACTIVE=False reason=no_policy_key` 下，"
        "前置器 blocked 列表**含真值臂自身**（w229/codex 56/58）⇒ 全局口径恒不可满足；该复现即 R635 修正形态的判据依据"
        "（机检点 = `SCOPE_SOURCE != None ∧ POLICY_ACTIVE=True`）。"
    ),
    "note": (
        "轮次工件: eval/rover/r634/{prereg,judge,run,codex_stdout_first,kpi-table,verdict,selftest,bins,gate-margin,"
        "premise,report}-r634.* + dag-r634.md + evidence/** + snapshots/**。自捕 3 条（E1 声明滞后 / E2 预注册缺 "
        "`evidence_scope` / E3 跳步「roundcheck preflight 工具口径」，起手闸由 run 脚本自带 gate-margin A1/A2/B 承担）"
        "全部入档轮志与 verdict；E2 修正形态下沉 R635 预注册（声明先于跑，禁事后 `--scope` 补声明 = 翻案）。"
        "跨轮禁相减（RF0005 §6 红线 4）；R633 rc=3 与本轮 rc=1 只并列。"
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
