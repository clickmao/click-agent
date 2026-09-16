#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R492 台账行生成器: 从落盘证据机算 sha12, 生成 rows_r492.json (禁手抄)。"""
import collections, hashlib, io, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))


def sha12(rel):
    p = os.path.join(ROOT, rel)
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()[:12]


def gen(rel):
    return {"evidence_kind": "artifact", "pin_status": "frozen", "pin_reason": "archived-per-round",
            "artifact_sha12": sha12(rel), "instrument": None, "instrument_sha12": None,
            "binding": "audit-pin", "audited_by_round": "R492"}


rows = []

g = gen("eval/rover/r492/host_log_audit.json")
g["instrument"] = "eval/rover/r492/host_log_audit.py"
g["instrument_sha12"] = sha12("eval/rover/r492/host_log_audit.py")
rows.append(collections.OrderedDict([
    ("id", "r492.paid-token-caliber-relay-vs-host"),
    ("level", "L2"),
    ("capability", "**付费量口径双列 (中继 usage 真值 vs 宿主打点) — 发现宿主遥测缺一次截断续调用的 prompt 量**。"
     "机检口径: 调用数按 `request_id` 去重 + 截断续调用点(`llm_call_continue`)计入后, **r482 起五轮臂 100% 对齐**"
     "(r491/TP1 等); 但 `llm_call_continue` 行**不带 token 字段** ⇒ 若按宿主行汇总 token 会少算 r491/Aroleb 的 **5,215 tok (6.37%)**, "
     "使降幅读数从真值 **−72.42%** 变 **−70.54%**(保守方向)。**旧遥测格式 r474/r477 有真调用缺口**(宿主行数 < 中继付费调用数), r482 起格式对齐。"),
    ("evidence_cmd", "python3 eval/rover/r492/host_log_audit.py"),
    ("evidence_path", "eval/rover/r492/host_log_audit.json"),
    ("evidence_generated_with", g),
    ("negative_control", "三态自检: `--no-dedupe`(不去重空正文诊断行) / `--ignore-continue`(漏计续调用点) / `--drop-host-row`(人为删一行) "
     "⇒ 三者必被检出 (detected=True, rc=0); 正常路径 rc=0 且 gap=0。禁把「宿主口径汇总」当分母真值。"),
    ("covers", ["eval/rover/r492/host_log_audit.py", "eval/rover/r492/host_log_audit.json",
                "docs/reports/r492-paid-token-caliber-audit.md"]),
    ("owner_round", "R492"),
]))

g = gen("eval/rover/r492/verdict-r492.json")
g["instrument"] = "eval/rover/r492/analyze_r492.py"
g["instrument_sha12"] = sha12("eval/rover/r492/analyze_r492.py")
rows.append(collections.OrderedDict([
    ("id", "r492.replay-pair-trim-gate-open"),
    ("level", "L2"),
    ("capability", "**回放配对剪裁 (ReplayPairTrim) 门开 T×3 同窗单变量验收**。同一 AOT 产物 / 同一 12 轮夹具 / 同窗(16:42:49–17:13:52): "
     "TC(闸关, 对照) **6 调用/25,916 tok**; TP1 **23,455 (−9.50%)**, TP2 **22,383 (−13.63%)**, TP3 **23,212 (−10.43%)**; "
     "三跑最差 **−9.50%**, 付费调用数 6↔6 不变。结构面 3/3 生效: 配对闸遥测 `0→1`(人面 on 必须显式映射成 1, 直传 \"on\" 会被产品当关)、"
     "`replay_user_trimmed 0→20`、**user→user 相邻对 20→0**、空正文 0、teardown 四臂全 clean。"
     "**判据证伪 (如实记)**: 预注册 I7「处理臂无 user 侧泄漏」`skip_user_leak==0` **3/3 红** —— 该计数是子串代理: "
     "每请求最后一个 user(活轮)必然内嵌上轮模板, 结构性不可达 0 (post-hoc 拆分: 陈轮 15→10, 活轮 5 恒在)。"
     "质量面: 粗判在 TP1 turn12 给**假阴性**(用「不准/否」而非关键词表内的词), 逐字人读与对照语义等价(均承认字面错误、均坚持 3+5=8、均区分提及与断言) ⇒ **不宣称质量退化**, 但按纪律记 FAIL。"),
    ("evidence_cmd", "python3 eval/rover/r492/analyze_r492.py"),
    ("evidence_path", "eval/rover/r492/verdict-r492.json"),
    ("evidence_generated_with", g),
    ("negative_control", "对照臂 TC(闸关)同窗同二进制 ⇒ 差值只归因开关; I6 为**门态正控**(遥测必与臂参一致, 假阴性会被抓); "
     "I7 判据被证伪后**不修判据凑绿**(FAIL 原样保留, 机制解释单列 `checks_posthoc`); 跨轮禁相减(不设 R491 分母); "
     "首跑因 aux 缺失判废并整目录移入 invalid-run1 (relay usage 为 append 模式, 不清理会静默混算)。"),
    ("covers", ["eval/rover/r492/analyze_r492.py", "eval/rover/r492/prereg_r492_arms.json",
                "eval/rover/r492/run_arm_real_r492.sh", "eval/rover/r492/verdict-r492.json",
                "docs/reports/r492-replay-pair-trim-gate-open.md"]),
    ("owner_round", "R492"),
]))

g = gen("eval/recall/prereg_r492_g2_supersede.json")
g["instrument"] = "eval/recall/prereg_r481a.json"
g["instrument_sha12"] = sha12("eval/recall/prereg_r481a.json")
rows.append(collections.OrderedDict([
    ("id", "r492.recall-g2-caliber-supersede"),
    ("level", "L1"),
    ("capability", "**召回 G2 判据口径 supersede**: 以新预注册 (悬空 ≤0.10 ∧ 解析率 ≥0.90 ∧ 覆盖度单列 ∧ 词面倒排兜底永久保留 ∧ 跨 URL 一律 unreported) "
     "覆盖 `prereg_r481a.json` 内 ≤0.35 的旧悬空线; **旧文件一字未改**(sha256 记于新文件) ⇒ 不用事后改预注册的方式消解冲突。"),
    ("evidence_cmd", "python3 -c \"import json,io;print(json.load(io.open('eval/recall/prereg_r492_g2_supersede.json',encoding='utf-8'))['supersedes']['sha256'])\""),
    ("evidence_path", "eval/recall/prereg_r492_g2_supersede.json"),
    ("evidence_generated_with", g),
    ("negative_control", "旧预注册 sha256 在写新文件前后机检一致 ⇒ 「不改旧文件」可验证; 新口径只收严不放宽 (0.35→0.10)。"),
    ("covers", ["eval/recall/prereg_r492_g2_supersede.json", "eval/recall/prereg_r481a.json"]),
    ("owner_round", "R492"),
]))

g = gen("eval/rover/r492/derive_runner_r492.py")
g["instrument"] = "eval/rover/r491/run_arm_real_r491.sh"
g["instrument_sha12"] = sha12("eval/rover/r491/run_arm_real_r491.sh")
rows.append(collections.OrderedDict([
    ("id", "r492.arm-runner-derive-aux-carry"),
    ("level", "L2"),
    ("capability", "**臂执行器机派生: 必同批携带 aux + 起手 fail-closed**(本轮自伤修正)。派生器只改正文不复制 `teardown_assert.py` ⇒ "
     "首跑 teardown 空跑、本地模型进程泄漏、矩阵带残留续跑。修法三重: ① 派生器同批复制 aux 并**逐字节一致性断言**; "
     "② runner 起手 aux 预检缺失即 `exit 12`; ③ 矩阵遇错即止(不再带残留跑下一臂)。派生差异机检: 名称/端口/入参/回显/映射/aux 六组断言。"),
    ("evidence_cmd", "python3 eval/rover/r492/derive_runner_r492.py"),
    ("evidence_path", "eval/rover/r492/derive_runner_r492.py"),
    ("evidence_generated_with", g),
    ("negative_control", "断言 fail-closed: 锚点缺失 / 人面 on 未映射成产品 1 / aux 复制不一致 ⇒ 派生即 rc≠0 且**不写盘**; "
     "首跑受污染产物归档于 `eval/rover/r492/invalid-run1/` 以备审计。"),
    ("covers", ["eval/rover/r492/derive_runner_r492.py", "eval/rover/r492/run_arm_real_r492.sh",
                "eval/rover/r492/run_arm_real_r492.diff", "eval/rover/r492/teardown_assert.py"]),
    ("owner_round", "R492"),
]))

dst = os.path.join(HERE, "rows_r492.json")
io.open(dst, "w", encoding="utf-8").write(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
print(json.dumps({"written": dst, "rows": len(rows),
                  "ids": [r["id"] for r in rows],
                  "sha12": {r["id"]: r["evidence_generated_with"]["artifact_sha12"] for r in rows}},
                 ensure_ascii=False, indent=1))
