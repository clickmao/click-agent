#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R552 收口: 往共享台账 `docs/reports/round-collision-log.jsonl` 追加本会话归属行。

纪律(承 skill unattended-job-reliability §11 / shared-artifact-integrity):
  · 键集必须与该族**既有行**逐一相同(先从末条同族行 dump 键);
  · 写后**全文件逐行 json.loads** 校验;
  · 单行探针读数**不写** KPI sink(kpi.jsonl)。
"""
import io
import json
import os

REPO = "/home/agentuser/AgentFramework"
LOG = os.path.join(REPO, "docs/reports/round-collision-log.jsonl")
rows = [json.loads(l) for l in io.open(LOG, encoding="utf-8") if l.strip()]
# 同族 = event=round-close / round-claim-start; 取最近的同族行键集
fam_close = [r for r in rows if r.get("event") == "round-close"]
fam_start = [r for r in rows if r.get("event") == "round-claim-start-and-source-takeover"]
kc = sorted(fam_close[-1].keys())
ks = sorted(fam_start[-1].keys())
print("既有 round-close 键集:", kc)
print("既有 round-claim-start 键集:", ks)

new_start = {"ts": "2026-09-18T12:35+08:00", "event": "round-claim-start", "round": "R552",
             "detected_by": "本 tick 起手: .git/ROUND_CLAIM 缺席 · ps 无 run_r*/agenthost/dotnet 活动执行体 · 工作树仅余前轮已提交态(无 M 源码件) · 端口 49041/49051/49061 空闲 ⇒ 无兄弟作业在跑",
             "owner": "cron 本会话(R552): 主线轴 = 探针修复预算剂量面 {0,1,2}(既有开关, 同一二进制 e2fdab87…, 零产品改动/零重发布)",
             "evidence": "eval/rover/r552/prereg-r552.json(先写后跑, 起臂前机检) · runner 第 0 步 print '[先写后跑闸] prereg ok' · /tmp/r552v2_b{0,1,2}/logs/run.txt",
             "action": "3 臂 × 最多 9 窗(含两次书面增补 sup1/sup2, 均为填满声明 n 而非挑选窗); 未 push(PUSH_PAUSED 在位)"}

new_close = {"ts": "2026-09-18T13:10+08:00", "event": "round-close", "round": "R552",
             "detected_by": "24 窗齐 + 入仓 + 铁律 11 前置器机检完成",
             "result": "b0(轴0) 6 窗全无有效读数(5 窗 rc=4) · b1(轴1) 9 窗: 预注册有效 2(w35 47/58, w45 58/58) · b2(轴2) 9 窗: 预注册有效 2(w37 58/58, w56 54/58) ⇒ 三臂均 <3 ⇒ J2 不可判; 调用Σ 13/27/23 · 新算 promptΣ 59,705/153,355/119,885 · completionΣ 29,993/62,855/51,412; exec_precondition --round r552 ⇒ rc=1",
             "root_cause": "元凶 = 上游契约面退化: 24 窗中 15 窗(62%) rc=4 stage=contract, 逐窗上游闸(dump mtime 时间片可解析率 >0.25)同样触发 15 窗; 文本级形态 = 模型多输出一个 JSON 对象 / 复读指令(finish_reason=stop, 非截断) ⇒ 与 R551 w8/w9 同源且更重。剂量未被行使: b2 的 5 个探针窗零失败(probe_failed=0/8), 全窗 probe_repairs 从未到 2 ⇒ 「1 vs 2」无机会产生差别。判据过宽(实测 rc=4 窗仍产出 45–58/58 可判分产物)⇒ 修正只作 checks_posthoc, 留 R553 预注册。",
             "evidence": "eval/rover/r552/{prereg-r552.json, prereg-r552-v2.json, prereg-r552-sup1.json, prereg-r552-sup2.json, readings-r552.json, kpi-table-r552.json, void_gate_selfcheck.json(has_teeth=True), gate-switch-inventory.txt, snapshots/, evidence/windows/} · eval/rover/r507pre/precondition-r552.json(rc=1) · docs/reports/r552-dose-surface.md",
             "action": "本轮自捕三处器具缺陷并修复(漏复制 cases-r521.json / 裁决件名覆盖 / 空窗目录致前置器假红); 被中止的 v1 运行树改名保留(/tmp/r552_b0-v1nocases, 不删); 候选①经机检判定『只翻既有开关』不可满足(87 开关中交付语义命中 0)⇒ 留 R553; 全量测试与 AOT 未跑(零源码改动 ⇒ 无重发布需求); commit 仅本地"}

assert sorted(new_start.keys()) == ks, (sorted(new_start.keys()), ks)
assert sorted(new_close.keys()) == kc, (sorted(new_close.keys()), kc)
rows.append(new_start)
rows.append(new_close)
with io.open(LOG, "w", encoding="utf-8") as fh:
    for r in rows:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
# 写后全文件逐行校验
n = 0
for i, l in enumerate(io.open(LOG, encoding="utf-8"), 1):
    if l.strip():
        json.loads(l)
        n += 1
print("追加 2 行(键集对齐: start=%d close=%d), 全文件逐行可解析行数=%d" % (len(ks), len(kc), n))
