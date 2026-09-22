#!/usr/bin/env python3
"""R635 · verification-registry 追加一行（L3 真机运行）。派生自 r631/r633/r634 同族件（纪律逐字沿袭）:
① 改前断言序列化器逐字节复现原文件; ② 只追加一行, 不动既有行; ③ 幂等; ④ 写后读回 + numstat。
用法: python3 eval/rover/r635/add_registry_row_r635.py [--apply]
"""
import hashlib
import io
import json
import os
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
REG = os.path.join(REPO, "docs/verification-registry.json")
INSTR = os.path.join(REPO, "eval/rover/r635/judge_r635.py")
EVID = "docs/evidence/RF0001/R635-mainline-new-windows.md"
EVID_ABS = os.path.join(REPO, EVID)


def sha12(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:12]


NEW = {
    "id": "r635.mainline-new-window-set",
    "level": "L3",
    "owner_round": "R635",
    "capability": (
        "主线对照轮（**新窗集 w231/w232/w233**，与历史 w184..w230 不相交；产品默认档 ×3/窗 + codex 外部真值 ×1/窗；"
        "同一枚 AOT 件 cefd045e8d1d，零产品源码改动 / 零新增夹具 / 零新增开关）：**主判据 Q1 PASS** —— "
        "逐窗配对差 **D = [0, 0, 2]**（中位 **0** ≥ 阈值 −2；逐窗均 ≥ −15），有效窗 **3**（承 R634 的窗有效性修正）。"
        "次级 Q2 **非回归**：整题全对 P **8/9 = 0.8889** vs codex 真值 **2/3 = 0.6667**。"
        "**但铁律 11 可执行前置器 rc=1**（`ACCEPTABLE_SCOPED=False`；`SCOPE_SOURCE=eval/rover/r635/prereg-r635.json` ∧ "
        "`PREREG=True` ∧ `POLICY_ACTIVE=True`）⇒ 验收面存在未通过项 **`w232/agentP-r2` rc=1 · 43/58 · "
        "failed = wythoff#43-public,#44-public,#45..#57-hidden（15 例 = 整族）** ⇒ **质量/成本一律「参考（未可验收）」**。"
        "**中位口径看不见族级失败**（该跑次被中位 58 掩盖）⇒ 中位判据必须与逐臂-题可执行面成对读（本轮的核心方法学产出）。"
        "成本三列（中继 dump 时间轴）：P n=9 `18 调用 / 16,639 新算 / 44,653 completion`（v_all 中位 0.9039 / v_incr 0.8407）"
        "vs 真值 n=3 `36 / 22,806 / 14,944`（0.9201 / 0.9306）——**跑次数不等（9 vs 3）⇒ 总和列是异分母口径**，"
        "归一列（本轮新登记）另报：每跑次调用 **2.00 vs 12.00（−83.3%）** · 每跑次新算 **1,849 vs 7,602（−75.7%）** · "
        "每跑次 completion **4,961 vs 4,981（−0.4%）** ⇒ 「completion +199%」是分母产物，**不得单读总和列**。"
        "**诚实边界：无单变量轴（测量轮，禁跨轮相减）· n 欠功率 · 真值成本摆幅（25→36 调用，+44%）大于任何臂间差 ⇒ 成本面不作结论 · "
        "wythoff 族只复现未归因（承 R621/R622 定因）· 三档终局目标读数不动不宣称。**"
    ),
    "evidence_cmd": (
        "bash eval/rover/r635/run_r635.sh && "
        "python3 eval/rover/r635/judge_r635.py --D $HOME/.agentframework/harness/runs/r635 --pd eval/rover/r635 && "
        "python3 eval/rover/r635/judge_r635.py --D /tmp/none --pd eval/rover/r635 --selftest && "
        "python3 eval/rover/r507pre/exec_precondition.py --round r635 && "
        "python3 eval/capability/decl_sweep.py --check && "
        "python3 eval/capability/status_gen.py --check"
    ),
    "evidence_path": EVID,
    "evidence_generated_with": {
        "evidence_kind": "artifact",
        "pin_status": "live",
        "pin_reason": "worktree-only",
        "artifact_sha12": sha12(EVID_ABS),
        "instrument": "eval/rover/r635/judge_r635.py",
        "instrument_sha12": sha12(INSTR),
        "binding": "audit-pin",
        "audited_by_round": "R635",
    },
    "covers": [
        "eval/rover/r635/judge_r635.py",
        "eval/rover/r635/run_r635.sh",
        "eval/rover/r635/prereg-r635.json",
        "eval/rover/r635/selftest-r635.json",
        "eval/rover/r635/verdict-r635.json",
        "eval/rover/r635/kpi-table-r635.json",
        "eval/rover/r635/cases/run_cases_r521.py",
        "eval/rover/r507pre/exec_precondition.py",
        "docs/evidence/RF0001/R635-mainline-new-windows.md",
        "冻结题集双钉（文件 sha e0c667c2… + payload sha e7ddce02…；aux 同批携带 sha d9aecf4d…）与新窗集不相交（w231..w233）",
        "逐窗配对 D 报告面（P 中位 − 真值中位）与有效窗口径（真值跑通 ∧ 非自败例 ≥1）",
        "成本三列的「总和 / 每跑次归一」双列口径（异分母 9 vs 3 的诚实读法）",
    ],
    "negative_control": (
        "成对/负向控制（现场执行，读数入 selftest-r635.json / verdict-r635.json / precond-r635.json）："
        "① **判据修正的两侧成对（最承重、承 R634）**——`TRUTH_SELF_FAIL_NOW_VALID`（真值自败但跑通）**正控** = 有效窗 3；"
        "`TRUTH_VOID`（真值挂死）**负控** = 有效窗 2 ∧ `unreliable=[w232]` ⇒ 修正**不放宽**另一侧（只证一侧 = 放宽）。"
        "② **锚面两侧样例**——有提示面跑次 **9/9 == 锚**（正控）；`waiver.missing_runs=[]` 且缺席下限与覆盖列齐备 ⇒ "
        "缺项**出声弃权**、不读成漂移、不抬 rc=2。"
        "③ **真值自败单列 vs 窗剔除的分离**——w233 真值自败 2 例**逐条单列**（`truth_self_failed_cases`）而窗仍有效；"
        "`policy_demoted=[w233/codex]`（`unreliable_excluded`）与 `blocked_scoped` 名单**互不重叠** ⇒ 策略未把本侧失败一并吞掉。"
        "④ **验收面 fail-closed**——`blocked_scoped` 非空 ⇒ rc=1（不判绿）；`SCOPE_SOURCE` 非空 ∧ `PREREG=True` ⇒ "
        "验收面**不退化**为全局口径（承 R634 E2 的复现与修正）。"
        "⑤ **零器具改版**——`decl_sweep --check` = `checked=30 drifted=0`（本轮零放宽、零声明漂移）。"
    ),
    "note": (
        "轮次工件: eval/rover/r635/{prereg,judge,run,report,kpi-table,verdict,selftest,bins,gate-margin,"
        "premise}-r635.* + dag-r635.md + evidence/** + snapshots/** + run-stdout.log。"
        "自捕 0 条（零器具改版轮）；跳步「构建/AOT」（零 `src/` 改动 ⇒ 无新二进制可构建）。"
        "跨轮禁相减（RF0005 §6 红线 4）：R633（rc=3）/ R634（rc=1，D 中位 −3）/ 本轮（rc=1，D 中位 0）**只并列**。"
        "基线引用: eval/capability/kpi.jsonl 行 O635 带 `baselines` 10 id（RF0004 §4.1 引用义务）。"
        "推送暂停令在效：只本地 commit，无 push / 无镜像 / 无 gh api 写。"
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
