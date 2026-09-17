#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R523 登记行 (克隆上一行键形状 ⇒ 只改 id/level/capability/covers/evidence_*/negative_control/owner_round)。
追加 2 行 + 形式门禁 (R2e/R2f 字段形状: covers 纯路径须存在 · evidence_path 须存在 · owner_round 合法段 ·
evidence_generated_with 为对象且 pin_status=frozen 行才可带 artifact_sha12 · sha12 取现盘字节)。
"""
import hashlib, json, os, re, sys

REPO = "/home/agentuser/AgentFramework"
P = os.path.join(REPO, "docs/verification-registry.json")


def sha12(rel):
    p = os.path.join(REPO, rel)
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12] if os.path.isfile(p) else None


NEW = [
    {
        "id": "internal.n3-same-window-contrast-r523",
        "level": "L2",
        "capability": (
            "**n=3 同窗对照 (reps>=3): 纪律臂无增益, 本侧不优于外部真值 (如实收窄)** —— 三窗 (w1/w2/w3), 每窗独立 "
            "adapter 端口 (48700/48701/48702) + 独立 run 目录 + 每跑次独立 session; 每窗三臂 A0-off (=R521 旧行为, 消融控制) / "
            "A1-on (交付面) / C-codex (外部真值, 经同一计量 adapter 同模型); 单变量 = env AGENTFRAMEWORK_ACTION_DISCIPLINE; "
            "三臂同一 AOT 二进制 sha256 cc611646… (本轮零产品源码改动, 只改 eval/ 器具); 题面 sha256 516f3208… 起手硬门 + "
            "起手闸 2xPASS + 挂载机检 MOUNT_OK=True (纪律真进实发 prompt)。机检读数 (调用数 / 新算 prompt / completion / 用例): "
            "A1-on 17/20004/9440/58 · 4/10068/4217/58 · 12/13548/10712/58; A0-off 4/6655/6641/58 · 8/11069/6572/58 · "
            "12/14054/6302/58; codex 7/3824/4125/58 · 9/6133/5067/**46** · 5/3506/2370/58。中位比值 A1/codex = 调用 1.71 · "
            "新算 3.54 · completion 2.29 · 有效 token 3.05 · 名义 2.29 ⇒ 预注册 C3/C4/C5 (各降 >=30%) **三条全否, 不宣称任何降幅**; "
            "A1/A0 调用中位比 1.5 (逐窗 4.25 / 0.5 / 1.0) ⇒ 纪律**无增益**: R522 的「两臂同步 19→4 调用」判定为**窗口方差** "
            "(同一 A1 臂在三同输入窗间摆动 4.25 倍), 非纪律作用。质量面 A1 三窗 58/58 >= A0 58/58 ⇒ 质量未降。"
            "诚实边界: 铁律 11 前置器 rc=1 (w2/codex 46/58, 12 例 wythoff 隐藏用例错) ⇒ 全部读数标『参考(未可验收)』; "
            "外部真值自身跨窗不稳定 (58/46/58) 是本系列单窗结论不可用的直接证据。"
        ),
        "covers": [
            "docs/reports/r523-n3-same-window-contrast.md",
            "eval/rover/r523/prereg-r523.json",
            "eval/rover/r523/run_r523.sh",
            "eval/rover/r523/kpi_r523.py",
            "eval/rover/r523/freeze_r523.py",
            "eval/rover/r523/taskset-r523.json",
            "eval/rover/r523/evidence/kpi-r523.json",
            "eval/rover/r523/evidence/kpi-r523.txt",
            "eval/rover/r523/evidence/precond-r523.txt",
            "eval/rover/r523/evidence/windows/w1/report.json",
            "eval/rover/r523/evidence/windows/w2/report.json",
            "eval/rover/r523/evidence/windows/w3/report.json",
        ],
        "evidence_cmd": "bash eval/rover/r523/run_r523.sh (三窗 x 三臂; 同输入硬门 + 起手闸 + 挂载机检 + 冻结判分 + KPI + 前置器)",
        "evidence_path": "eval/rover/r523/evidence/kpi-r523.json",
        "evidence_generated_with": {
            "evidence_kind": "artifact",
            "pin_status": "frozen",
            "pin_reason": "archived-per-round",
            "artifact_sha12": sha12("eval/rover/r523/evidence/kpi-r523.json"),
            "instrument": "eval/rover/r523/kpi_r523.py",
            "instrument_sha12": sha12("eval/rover/r523/kpi_r523.py"),
            "binding": "audit-pin",
            "audited_by_round": "R523",
        },
        "negative_control": (
            "控制臂即负控: A0-off (纪律关) 与 codex (外部真值) 同窗同题同二进制; 若判据器/计量泄漏, 两臂读数会同向漂移 —— "
            "实测三臂独立摆动 (调用 4/8/12 vs 17/4/12 vs 7/9/5), 未出现同向。质检门: 起手闸 2xPASS 先于起臂; 产物树非空断言; "
            "挂载机检证明纪律确进实发 prompt (否则处理臂名不副实)。"
        ),
        "owner_round": "R523",
    },
    {
        "id": "eval.precondition-scoped-acceptance-face-r523",
        "level": "L2",
        "capability": (
            "**前置器 rc 改由「验收面」(require ∪ 未声明) 判定, 早退分支同规则 (R522 补丁修过头后收窄)** —— R522 把 rc 前置为 "
            "全局 `blocked` 非空 ⇒ 已声明**非验收面**的臂失败 (含缺判据件) 也把 rc 顶成 1, 使控制臂噪声污染整轮验收。修: "
            "① 早退分支 `task_not_in_taskset` / `missing_case_script` 经新增 `_early_scope()` 归入同一套归属规则 (require/undeclared ⇒ "
            "进 `blocked_scoped`; nonrequired ⇒ 只进全局 `blocked` 并单列 `NONREQUIRED`); ② rc 判据改读 `blocked_scoped`; ③ 全局 "
            "`blocked` 始终非空记账并打印差额, 不放水。7 项正/负控 A/B (同沙盒对 HEAD 前版): 仅 NC2 (非验收面臂失败) 与 NC6 "
            "(非验收面臂缺判据件) 由 rc 1→0, 其余 NC1/NC3/NC4/NC5/NC7 (全对/验收面失败/未声明臂/验收面缺脚本/无预注册) rc 恒 1 ⇒ "
            "未放水; 旧轮判决不变 (r521 rc=1 · r522 rc=1 重跑各一次)。R523 本体 rc 仍 1 (w2/codex 属验收面且失败) ⇒ 修复非为本轮开绿灯。"
        ),
        "covers": [
            "eval/rover/r507pre/exec_precondition.py",
            "eval/rover/r523/nc_semantics_r523.py",
            "eval/rover/r523/evidence/nc-panel-r523.json",
            "eval/rover/r523/evidence/precond-r523.txt",
        ],
        "evidence_cmd": "python3 eval/rover/r523/nc_semantics_r523.py (7 控 A/B; 期望 NC_PANEL_PASS)",
        "evidence_path": "eval/rover/r523/evidence/nc-panel-r523.json",
        "evidence_generated_with": {
            "evidence_kind": "artifact",
            "pin_status": "frozen",
            "pin_reason": "archived-per-round",
            "artifact_sha12": sha12("eval/rover/r523/evidence/nc-panel-r523.json"),
            "instrument": "eval/rover/r507pre/exec_precondition.py",
            "instrument_sha12": sha12("eval/rover/r507pre/exec_precondition.py"),
            "binding": "audit-pin",
            "audited_by_round": "R523",
        },
        "negative_control": (
            "过宽负控 (防放水): NC3 require 臂失败 ⇒ rc=1 且 BLOCKED 点名; NC4 未声明臂存在 ⇒ rc=1 UNDECLARED; NC5 验收面臂缺判据件 ⇒ "
            "rc=1; NC7 无预注册 ⇒ 全臂皆验收面 ⇒ rc=1。过窄负控 (防误伤): NC1 全对 ⇒ rc=0; NC2/NC6 非验收面失败 ⇒ rc=0 但读数列打印。"
            "同器重跑旧轮 (r521/r522) 判决不变, 证明只影响被声明为非验收面的臂。"
        ),
        "owner_round": "R523",
    },
]


def main():
    reg = json.load(open(P, encoding="utf-8"))
    rows = reg["rows"] if isinstance(reg, dict) and "rows" in reg else reg
    last = rows[-1]
    added = []
    for spec in NEW:
        if any(r.get("id") == spec["id"] for r in rows):
            print("已存在, 跳过:", spec["id"])
            continue
        row = dict(last)
        row.update(spec)
        rows.append(row)
        added.append(spec["id"])
    if isinstance(reg, dict) and "updated_round" in reg:
        reg["updated_round"] = "R523"

    # --- 形式门禁 (只查本轮新增行, 不替历史行背书) -------------------------
    errs = []
    for r in [x for x in rows if x.get("owner_round") == "R523"]:
        for k in ("id", "level", "capability", "covers", "evidence_cmd", "evidence_path",
                  "evidence_generated_with", "owner_round"):
            if not r.get(k):
                errs.append("%s 缺字段 %s" % (r.get("id"), k))
        if not re.match(r"^(R\d+|EXP1-Q\d+)$", str(r.get("owner_round"))):
            errs.append("%s owner_round 非法段 %s" % (r.get("id"), r.get("owner_round")))
        for c in r.get("covers") or []:
            if any(ch in c for ch in "*?[]") or not os.path.exists(os.path.join(REPO, c)):
                errs.append("%s covers 非法/缺失: %s" % (r.get("id"), c))
        if not os.path.exists(os.path.join(REPO, r.get("evidence_path") or "")):
            errs.append("%s evidence_path 缺失: %s" % (r.get("id"), r.get("evidence_path")))
        eg = r.get("evidence_generated_with")
        if not isinstance(eg, dict):
            errs.append("%s evidence_generated_with 非对象 (R2f)" % r.get("id"))
        else:
            if eg.get("pin_status") == "live" and eg.get("artifact_sha12"):
                errs.append("%s pin_status=live 禁带 artifact_sha12 (R2e)" % r.get("id"))
            if not re.match(r"^(R\d+|EXP1-Q\d+)$", str(eg.get("audited_by_round"))):
                errs.append("%s audited_by_round 非法段 %s" % (r.get("id"), eg.get("audited_by_round")))
            for k in ("artifact_sha12", "instrument_sha12"):
                if eg.get(k) and not re.match(r"^[0-9a-f]{12}$", eg[k]):
                    errs.append("%s %s 非 12 位 hex" % (r.get("id"), k))
    json.dump(reg, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("WROTE 行数", len(rows), "新增", added)
    print("FORM_GATE=%s" % ("PASS" if not errs else "FAIL"))
    for e in errs:
        print("  !", e)
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
