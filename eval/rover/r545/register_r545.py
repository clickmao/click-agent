#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R545 登记行写入 eval/capability/kpi.jsonl（RF0001 §6 规则③：KPI 行只写该台账）。

纪律（与 register_r544.py 同）：
  · 键集必须与既有同族行逐字相同；
  · 幂等（同 round 已存在 ⇒ 跳过，不重复追加）；
  · 写后全文件逐行 json.loads 回读。
"""
from __future__ import annotations
import datetime
import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
LEDGER = os.path.join(REPO, "eval/capability/kpi.jsonl")

ROW = {
    "round": "R545",
    "ts": datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
    "kind": ("主线轮(R544 预注册 J1 被同窗证伪 ⇒ 触发面修订轮 r2): 公开用例回放的触发面由 `exec.Rc==0` 扩到"
             "**全部「产物在盘」出口** + 同窗单变量对照(AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK off/on × 5 rep) + 旧路径 A1on × 3 样本 + AOT 重发布"),
    "artifact": ("src/agent/r1/{PublicProbeResult.cs(TriggerRc),PublicExampleProbe.cs(RunAsync triggerRc),R1Pipeline.cs(RunAsync 实参),R1Transcript.cs(public_probe_reason/trigger_rc)}"
                 " + src/agent.tests/R1PublicProbeTests.cs(14/14) + tools/r1gen/gen_csharp.py(PublicProbePassedNote) + src/agent/contract/StructuredPrompt.cs(生成物重生)"
                 " + docs/api-surface.baseline.txt(重生, 差异仅本轮) + eval/rover/r545/** (setup/prereg/analyze/run/taskset/pins/readings-w1/run-w1/logs/evidence)"
                 " + docs/reports/r545-public-probe-trigger-face-v2.md + docs/evidence/RF0001/{EVIDENCE.md,KPI.md}"),
    "change": ("① 产品: 探针触发面 v2 —— 只要**执行器出口已把产物写到盘**(work 文件数>0)就回放题面公开用例, 不再要求 `exec.Rc==0`;"
               "台账新增 `trigger_rc`(触发那一刻的执行器出口 rc, -1=未触发)与 `public_probe_reason`(如 no_artifacts_on_disk);"
               "rc=5/8 等出口的失败证据同样用管道自产证据回灌; 关闭态不出字段(与旧台账逐字节同)。"
               "② 证据优先回灌: 生成器 `PublicProbePassedNote` 把「公开面通过」写进 prompt 措辞(明示**必要非充分**, 禁据公开面收尾)。"
               "③ 器具: eval/rover/r545 13 臂同窗单变量(off/on × a..e 交错 10 臂 + 旧路径 A1on/A1onb/A1onc), 同输入硬门逐项机检 == R544(4 项 md5 逐字节同),"
               "预注册范围闸 rc=0, 起手闸 2/2 PASS; AOT /tmp/pub_r545/agenthost sha256 aecdc80de82699c1c34d8a3a46b415c1f93facabef54557a65e190ae9a450563(15,812,016 B, IL 警告 0)。"),
    "readings": ("off(5): 56/58@2c/20,220 · 0/58@1c/8,298(non_exec) · 58/58@2c/20,828 · 52/58@2c/19,984 · 53/58@2c/20,791 ⇒ 全绿 1/5 · 用例中位 53 · 假成功(rc=0∧非全对)1;"
                 " on(5): 47/58@2c(pfail2,trig5) · 58/58@2c(pfail0) · 33/58@2c(pfail4) · 43/58@2c(pfail2,rc8) · 58/58@**1c**/10,140(pfail0,trig0,rc0) ⇒ 全绿 2/5 · 用例中位 47 · 假成功 0;"
                 " legacy(3): 58/58@4c/35,761 · 58/58@4c/34,657 · 56/58@5c/53,685 ⇒ 全绿 2/3。"
                 "**J1v2(v2 触发面) PASS**: 5/5 on 臂产物在盘(6–8 文件)且 public_probe_ran=1, off 5/5 字段缺席; **J8 出口覆盖 PASS**: trigger_rc 集 = [0,5] ⇒ **4/5 on 臂在 rc=5 触发**(v1 面只会覆盖 1/5)。"
                 "J2 支持(假成功 1→0); **J3 收窄(如实)**: 全绿臂 2 vs 1(≥) 而用例中位 **47 vs 53(<)**;"
                 " **J4 代价(on/off 中位倍率)**: calls 1.0 / prompt 0.994 / completion 1.009 / total 1.005 ⇒ 回放**零远端调用增量**;"
                 " J5 旧路径列: 质量前提 **不成立**(legacy 2/3 满绿) ⇒ calls 0.5× / token 0.568× **只作参考**;"
                 " 事后单列(非预注册): 公开面失败数 0/2/4 ⇒ 隐藏分均值 **58.0/45.0/33.0**(单调降, monotone=True)。"
                 "自洽: prefix_identical=True · role_mounted_all=True(326 字符) · cases_total_58_all=True。"
                 "L2: R1PublicProbeTests **14/14**(含新增触发面/判别力/零回归用例) · 全量测试见 honest_boundaries⑥ · 形式门禁/范围闸 rc=0。"
                 "铁律 11: `exec_precondition --round r545` **rc=1**(BLOCKED: 8/13 臂 <58/58, 逐条点名) ⇒ 本轮一切成本/质量读数标「参考(未可验收)」。"),
    "honest_boundaries": ("① 判据器实现修正(同窗同产物重算, 不动读数): 预注册 J3 是两维非劣(全绿臂数 ∧ 用例中位), 初版实现只算前者 ⇒ 补齐后判「收窄」(全绿 2≥1 成立, 用例中位 47<53 不成立);"
                          " ② 质量轴**无增益证据**(on 中位 47 < off 53)且 n=5 单窗, 离散结局(rc∈{0,5,8}, 用例 0–58)主导方差 ⇒ 只报「触发面真生效」+「回放零代价」, 不宣称质量提升;"
                          " ③ 旧路径列本窗 3 样本(4/4/5 调用, 34,657–53,685 tok, 极差 1.55×)与 R544 单样本(34 调用/714,287 tok/46/58)**跨窗崩 8.5×/18.3×** ⇒ 跨窗禁相减, 本窗该列质量前提亦不成立 ⇒ 无「更省且质量不降」可宣称;"
                          " ④ 外部真值(codex-cli)本轮仍缺席(g1 形态 32 步上限已判不可用) ⇒ 主线四硬条件缺外侧;"
                          " ⑤ 公开用例仅 8 条(4 族×2) ⇒ 回放是**必要非充分**自检, 「公开全过」≠整题正确(反例: P1b/P1e 公开 8/8 过且隐藏 58/58 = 正例, 但 P1a pfail2 → 47/58 说明公开面漏检 45 条隐藏);"
                          " ⑥ 全量测试: 首跑 1 红 = PublicApiSurfaceTests(本轮新增公共成员 `TriggerRc` ⇒ 未重钉 API 基线), 显式 `AGENTFRAMEWORK_API_BASELINE_WRITE=1` 重生(差异**仅本轮** 4 加 2 删)后复跑;"
                          " ⑦ 未测: 探针预测力跨轮/跨族稳定性(单窗 5 点)、role 轴对质量的影响(R542 起未分辨)、codex 外侧列、探针回灌预算与质量的关系。"),
    "next": ("① 用「公开面失败数」作**早停信号**(pfail≥2 ⇒ 提前停远端重试/降配)并以预注册成对判据 + 对照臂验证是否真省调用(本窗 pfail 0/2/4 ⇒ 隐藏分 58.0/45.0/33.0 单调, 是本轮唯一有预测力的杠杆);"
             " ② on 中位 47 < off 53 的定因: 单剂量 reps≥5 或固定 temperature/seed, 判定「探针回灌挤占修复预算」vs 采样方差;"
             " ③ 旧路径列可用性: A1on 扩到 ≥5 样本并定因(R544 34 调用离群 vs R545 4–5 调用紧致);"
             " ④ 前置器口径: 「任一臂-题不许错」使 rc=0 在随机模型下近乎不可达 ⇒ 需先写后跑地决定是否引入臂级阈值(禁事后放宽);"
             " ⑤ RF0001.3 completion 压缩(reasoning 吃满上限)。"),
    "owner_round": "R545",
}

KEYS = ["round", "ts", "kind", "artifact", "change", "readings", "honest_boundaries", "next", "owner_round"]


def main() -> int:
    rows = [json.loads(l) for l in io.open(LEDGER, encoding="utf-8") if l.strip()]
    same = [r for r in rows if r.get("round") == ROW["round"]]
    if same:
        print("幂等跳过: 已存在 round=%s 的登记行" % ROW["round"])
        return 0
    if sorted(rows[-1].keys()) != sorted(KEYS):
        print("键集不一致: 末行 %s != 本轮 %s ⇒ fail-closed" % (sorted(rows[-1].keys()), sorted(KEYS)))
        return 3
    with io.open(LEDGER, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(ROW, ensure_ascii=False) + "\n")
    back = [json.loads(l) for l in io.open(LEDGER, encoding="utf-8") if l.strip()]
    if len(back) != len(rows) + 1 or back[-1]["round"] != "R545":
        print("回读失败: 行数 %d ⇒ %d" % (len(rows), len(back)))
        return 2
    print("登记行已写入并回读通过: 行数 %d ⇒ %d, 末行 round=%s" % (len(rows), len(back), back[-1]["round"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
