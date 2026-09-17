#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R544 登记行写入 eval/capability/kpi.jsonl（RF0001 §6 规则③：KPI 行只写该台账）。

纪律：
  · **键集必须与既有同族行逐字相同**（round/ts/kind/artifact/change/readings/honest_boundaries/next/owner_round）；
  · 幂等（同 round 已存在 ⇒ 跳过，不重复追加）；
  · 写后全文件逐行 json.loads 回读（解析失败即报错）。
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
    "round": "R544",
    "ts": datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
    "kind": "主线轮(分支A · RF0001.2 开口): 产物侧**公开用例独立回放**落地(默认关) + 同窗单变量对照(AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK off/on × 3 rep + 旧路径基线 A1on) + AOT 重发布",
    "artifact": ("src/agent/r1/PublicExample{,Set,Extractor,ProbeResult,Probe}.cs + src/agent/contract/StructuredPrompt.cs(PublicProbeRepairMessage)"
                 " + src/agent/r1/{R1Options.cs,R1RunResult.cs,R1Pipeline.cs,R1Transcript.cs} + src/agent.tests/R1PublicProbeTests.cs"
                 " + docs/api-surface.baseline.txt(重生) + eval/rover/r544/** (setup/prereg/taskset/pins/run/analyze/probe_smoke/readings-w1/smoke-probe/run-w1/snapshots/evidence)"
                 " + docs/reports/r544-public-example-probe.md + docs/evidence/RF0001/{EVIDENCE.md,KPI.md} + docs/plans/RF0001-fable-aligned-development-plan.md"),
    "change": ("① 产品: R1Pipeline 在 PlanExecutor 返回 rc=0(自称完成)后调用 PublicExampleProbe —— 题面**公开用例**机械抽取(输入/期望取自题面, 禁模型自撰/禁模型裁判)"
               " + 判分器同语义回放(rc==0 ∧ stdout 尾换行归一逐字节等) + 失败则用**管道自产证据**回灌执行回灌预算(PublicProbeRepairMessage); 预算耗尽 ⇒ rc=8 public_probe_unmet(成对报, correctness_asserted=0);"
               " 台账新增 public_probe_ran/total/failed(关闭态不出字段 ⇒ 与旧台账逐字节同); 环境轴 AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK 默认关。"
               "② 器具: eval/rover/r544 7 臂同窗单变量(off/on × a,b,c 交错 + A1on), 同输入硬门逐项机检 == R542, 预注册范围闸 rc=0, 起手闸 2/2 PASS; AOT /tmp/pub_r544/agenthost sha256 f516234a…(15,812,000 B, IL 0)。"
               "③ 文档: 轮志 + E16 + KPI 行 + 计划 §2/§3/§7。"),
    "readings": ("P0a(off) rc=5 expect_stdout_exhausted 58/58 · 2 调用/16,476/4,049/20,525; P0b(off) rc=4 contract 0/58(空树) · 2/16,240/3,999/20,239; "
                 "P0c(off) rc=8 self_test_unmet 55/58 · 4/32,787/7,646/40,433; P1a(on) rc=5 58/58 · 2/16,473/3,966/20,439; "
                 "P1b(on) rc=0 done 58/58 · **1**/8,083/2,322/10,405 且 public_probe_ran=1/total=8/failed=0(8 条公开用例全过); P1c(on) rc=5 43/58 · 4/32,736/7,990/40,726; "
                 "A1on rc=- 46/58 · 34/702,146/12,141/714,287。列汇总: off 全绿 1/3, on 全绿 2/3; 两列假成功臂(rc=0 ∧ 非全对)=0; "
                 "on/off 中位倍率: 调用 1.0× / 新算 prompt 1.0× / completion 0.98× / 总 0.996×。"
                 "自洽: prefix_identical=True · role_mounted_all=True(326 字符) · cases_total_58_all=True · off 臂 public_probe 字段缺席(机制真缺席)。"
                 "**预注册 J1(on 臂须 ran=1) 判 FAIL**(mechanism_on_arms_ran=False: 探针只在 exec.Rc==0 触发 ⇒ P1a/P1c 在计划执行阶段即 rc=5 ⇒ 结构性不可达)。"
                 "L2: R1PublicProbeTests 9/9(含冻结 g1 题面抽出 8 条逐条==题面字面) · 真机接线冒烟 PROBE_SMOKE_RC=0(on ran=1 / off 缺席) · 形式门禁 14/14 · 全量 1867/1867(Release)。"
                 "铁律 11: exec_precondition --round r544 **rc=1**(验收面 blocked_scoped=1 = w1/agentP1c-g1 43/58) ⇒ 本轮一切成本/质量推断标「参考(未可验收)」, 不宣称任何降幅/增益。"),
    "honest_boundaries": ("① 预注册 J1 FAIL 照原样保留不翻案(触发面只到 exec.Rc==0; 修法=R545 把回放挂到产物已在盘的全部出口); "
                          "② n=3/单窗, rc ∈ {5,4,8}/{5,0,5} 用例 0–58 ⇒ 离散方差主导; R542 的「rc=0 ∧ 43–55/58」假成功现象本窗**未复现**(两列 0 臂) ⇒ 属窗内采样; "
                          "③ 旧路径对照列本窗自身崩(A1on 34 调用/714,287 tok/46/58 vs R542 4/38,990/58/58; 调用 8.5×/token 18.3×) ⇒ 跨窗禁相减, g1 族「r1 更省且质量不降」未成立/未可判; "
                          "④ 外部真值(codex-cli)本轮不出场(g1 形态 32 步上限已判不可用) ⇒ 主线四硬条件外侧缺失; "
                          "⑤ 公开用例仅 8 条(4 族×2) ⇒ 回放是**必要非充分**自检, 禁把「公开全过」当整题正确; "
                          "⑥ 自捕器具缺陷 1 条(已修): 产物同秒同长度改写 ⇒ pyc mtime+size 校验失效 ⇒ 旧字节码复用 ⇒ 回放假红; 修法=独立空 PYTHONPYCACHEPREFIX + PYTHONDONTWRITEBYTECODE=1; "
                          "⑦ 全量首跑 1 例假红(FrontendHandshakeTests socket 用例) 隔离复跑 4/4 绿 ⇒ 判同机争用, 非本轮回归; "
                          "⑧ 本轮改了产品源码 ⇒ AOT 必重发布(已做, 不带 -p:PublishAot); 新增公共成员 ⇒ API 基线显式重生(diff 仅本轮 22 行)。"),
    "next": ("① 探针触发面扩到全部「产物已在盘」的出口(rc=5/8), 以题面公开用例证据优先回灌; 预注册 J1 阈值不变(3/3), 披露 v1 run/二进制 sha 后重跑; "
             "② 采样方差定量(单剂量 reps≥5 或固定 seed/温度)后再判轴; "
             "③ 旧路径对照列可用性定因(该列自身跨窗崩) ⇒ 不可用则须换外部真值或缩题面规模; "
             "④ codex 外部列在 g1 形态的可用性(32 步上限)或用同族小题面重挂外侧; "
             "⑤ RF0001.3 completion 压缩(reasoning 吃满上限)。"),
    "owner_round": "R544",
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
    if len(back) != len(rows) + 1 or back[-1]["round"] != "R544":
        print("回读失败: 行数 %d ⇒ %d" % (len(rows), len(back)))
        return 2
    print("登记行已写入并回读通过: 行数 %d ⇒ %d, 末行 round=%s" % (len(rows), len(back), back[-1]["round"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
