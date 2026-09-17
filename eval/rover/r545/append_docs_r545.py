#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R545 文档回填（幂等追加）：docs/improvements.md 轮节 + docs/evidence/RF0001/EVIDENCE.md(E17) + KPI.md 追加段。

纪律：只**追加**，不改既有行；幂等（尾部已含本轮标记即跳过）；写后回读校验尾部标记。
"""
from __future__ import annotations
import io
import os
import sys

REPO = "/home/agentuser/AgentFramework"
IMP = os.path.join(REPO, "docs/improvements.md")
EV = os.path.join(REPO, "docs/evidence/RF0001/EVIDENCE.md")
KPI = os.path.join(REPO, "docs/evidence/RF0001/KPI.md")
MARK = "## R545 (2026-09-18)"

IMP_BLOCK = """
## R545 (2026-09-18) — 公开用例回放的**触发面修订轮 v2**(全部「产物在盘」出口) + 同窗 13 臂单变量对照 — 结果: **J1v2 PASS(可达 1/5→5/5 · 4/5 臂在 rc=5 触发) · 回放零远端代价(倍率 1.0) · 但 J3 收窄(用例中位 47 vs 53) ⇒ 质量无增益证据 · 前置器 rc=1 ⇒ 参考(未可验收)** (轮志: `docs/reports/r545-public-probe-trigger-face-v2.md` · prereg/证据 `eval/rover/r545/`)

- **靶点来源**: R544 预注册 J1 被同窗实测**证伪**(探针只在 `exec.Rc==0` 触发 ⇒ 3 个 on 臂里 2 个在计划执行阶段即 `rc=5` ⇒ 结构性不可达) ⇒ 本轮为修订轮 r2。**单变量** = `AGENTFRAMEWORK_R1_PUBLIC_SELFCHECK ∈ {unset,1}` × 5 rep + 旧路径 `A1on/A1onb/A1onc`(3 样本), 单窗 13 臂。
- **产品改动(触发面 v2)**: 只要**执行器已把产物写到盘**(work 文件数>0)就回放题面公开用例; 台账新增 `trigger_rc`(触发那一刻的出口 rc, -1=未触发)与 `public_probe_reason`(如 `no_artifacts_on_disk`) ⇒ 「真未触发」与「无产物可测」可机检区分; 关闭态不出字段(与旧台账逐字节同)。
- **证据优先回灌**: 生成器 `PublicProbePassedNote` 把「公开面通过」写进 prompt 措辞, 并明示**必要非充分**(禁据公开面收尾)。
- **读数 (同题 sha `516f3208…` 与 R544 逐字节同, 起手闸 2/2 PASS, AOT `aecdc80de82699c1c34d8a3a46b415c1f93facabef54557a65e190ae9a450563` 15,812,016 B IL 警告 0)**: `off`(5) 56/58·**0/58**·**58/58**·52/58·53/58 ⇒ 全绿 1/5 · 用例中位 53 · 假成功 1; `on`(5) 47/58·**58/58**·33/58·43/58·**58/58** ⇒ 全绿 2/5 · 用例中位 47 · 假成功 0; 旧路径 58/58·58/58·56/58(4/4/5 调用)。
- **判据**: **J1v2 PASS**(5/5 on 臂产物在盘且 `public_probe_ran=1`; off 5/5 字段缺席) · **J8 出口覆盖 PASS**(`trigger_rc` 集 `[0,5]` ⇒ **4/5 臂在 v1 面外的 rc=5 出口触发**) · J2 支持(假成功 1→0) · **J3 收窄(如实)**: 全绿臂 2 vs 1 成立 / **用例中位 47 vs 53 不成立** · **J4 代价倍率 calls 1.0 / prompt 0.994 / completion 1.009 / total 1.005**(回放零远端调用) · J5 旧路径质量前提**不成立**(2/3 满绿) ⇒ 0.5×/0.568× **只作参考**。
- **事后单列(非预注册)**: 公开面失败数 **0/2/4** ⇒ 隐藏用例均值 **58.0/45.0/33.0**(单调降) ⇒ 公开面回放**零远端调用**却有预测力 ⇒ 下轮候选①的杠杆。
- **测试基线**: `R1PublicProbeTests` **14/14**; 全量 `agentframework.tests` **1872/1872**(0 failed, 38 s, Release); 新增公共成员 ⇒ API 基线显式重生(**差异仅本轮** 4 加 2 删)。
- **诚实边界**: ① 判据器实现修正(预注册 J3 两维, 初版只算一维) ⇒ 同窗同产物重算并分列, 不动读数 ② 质量**无增益证据**且 n=5 单窗、离散结局主导方差 ⇒ 不宣称质量提升 ③ 旧路径列跨窗崩(R544 34 调用/714,287 tok vs 本轮 4–5 调用/34,657–53,685 tok) ⇒ 跨窗禁相减, 本窗亦无「更省且质量不降」 ④ 外部真值(codex)仍缺席(`g1` 32 步上限) ⇒ 主线四硬条件缺外侧 ⑤ 公开面 8 条必要非充分(P1a 公开失败 2 而隐藏 47/58) ⑥ 前置器 `--round r545` **rc=1**(BLOCKED: 8/13 臂 <58/58) ⇒ 全部读数标「参考(未可验收)」 ⑦ 未测: 预测力跨轮稳定性、role 轴质量效应、探针回灌预算与质量关系。
- **下轮候选 (R546)**: ① 用「公开面失败数」作**早停信号**(pfail≥2 ⇒ 提前停远端重试/降配), 预注册成对判据 + 对照臂验证是否真省调用 ② `on` 中位 47 < `off` 53 定因(单剂量 reps≥5 / 固定 seed) ③ 旧路径列扩到 ≥5 样本并定因 ④ 前置器臂级阈值是否引入(**先写后跑**, 禁事后放宽) ⑤ RF0001.3 completion 压缩。
"""

EV_ROW = """
| RF0001-E17 | **公开用例回放触发面修订(v2) 并真机验证**: 触发面由 `exec.Rc==0` 扩到**全部「产物在盘」出口**; 台账新增 `trigger_rc`(触发时刻出口 rc)/`public_probe_reason` ⇒ 「真未触发」vs「无产物可测」可机检区分。同窗 13 臂单变量: `on`(5) 47/58·58/58·33/58·43/58·58/58 · `off`(5) 56/58·**0/58**·58/58·52/58·53/58 · 旧路径(3) 58/58·58/58·56/58。**J1v2 PASS**: 5/5 on 臂产物在盘(6–8 文件, 机检非自报)且 `public_probe_ran=1`, off 5/5 字段缺席; **J8 PASS**: `trigger_rc` 集 `[0,5]` ⇒ **4/5 臂在 v1 面外(rc=5)触发**(v1 只会覆盖 1/5=P1e) ⇒ 结构性不可达**已消除**。**J4 代价倍率 calls 1.0/prompt 0.994/completion 1.009/total 1.005** ⇒ 回放零远端调用增量。**J2 支持**(假成功 1→0)。**J3 收窄(如实)**: 全绿臂 2 vs 1 成立 / **用例中位 47 vs 53 不成立** ⇒ 质量**无增益证据**。事后单列: 公开面失败数 0/2/4 ⇒ 隐藏均值 58.0/45.0/33.0(单调)。`exec_precondition --round r545` **rc=1**(BLOCKED: 8/13 臂 <58/58)。 | L2+L3 | `dotnet test src/agent.tests/agentframework.tests.csproj --filter FullyQualifiedName~R1PublicProbeTests`(**14/14**) ∧ 全量 **1872/1872**(38 s, Release) ∧ `bash eval/rover/r545/run_r545.sh`(起手闸 2/2 PASS) | `src/agent/r1/{PublicProbeResult.cs,PublicExampleProbe.cs,R1Pipeline.cs,R1Transcript.cs}` + `tools/r1gen/gen_csharp.py` + `src/agent/contract/StructuredPrompt.cs` + `eval/rover/r545/{readings-w1.json,prereg-r545.json,analyze-w1.txt}`; 前置器 `eval/rover/r507pre/precondition-r545.json`(**rc=1**) | R545 |
"""

EV_ANNEX = """> R545 追加：`exec_precondition --round r545` **rc=1**（验收面 8/13 臂 <58/58，逐条点名）⇒ 该轮读数一律「参考（未可验收）」。触发面修订**已收口**（v1 面下可达臂 1/5 → v2 面 5/5；4/5 在 `rc=5` 出口触发），但 `on` 列质量**中位低于** `off`（47 vs 53）⇒ 「回放带来质量增益」**未成立**；旧路径列本窗紧致（4–5 调用）与 R544 离群（34 调用/714,287 tok）**跨窗崩** ⇒ 该列仍不可作单窗对照。
"""

KPI_BLOCK = """
### R545（2026-09-18）触发面修订轮 v2 · 同窗 13 臂

1. **触发面 v2 可达性已收口**：`on` 臂 5/5 触发（v1 面下只有 rc=0 的 1/5），`trigger_rc` 集 `[0,5]` ⇒ 旧面外的 `rc=5` 出口真被覆盖；off 5/5 字段缺席（机制真缺席）。
2. **回放零远端代价**：on/off 中位倍率 calls 1.0 / prompt 0.994 / completion 1.009 / total 1.005 ⇒ 公开面回放（8 条，本地进程内）不增加远端请求。
3. **质量无增益证据**：全绿臂 2/5 vs 1/5，但**用例中位 47 vs 53**（<）⇒ J3 判「收窄」；n=5 单窗、离散结局主导 ⇒ 禁称质量提升。
4. **旧路径列跨窗崩**：R544 34 调用/714,287 tok/46-58% vs R545 4–5 调用/34,657–53,685 tok/56–58 ⇒ 跨窗禁相减；本窗该列质量前提不成立（2/3 满绿）⇒ 无「更省且质量不降」可宣称。
5. **事后单列（非预注册）**：公开面失败数 0/2/4 ⇒ 隐藏均值 58.0/45.0/33.0（单调）⇒ 公开面回放是**零远端调用**的预测信号，R546 候选①的抓手。
6. **未测**：预测力跨轮/跨族稳定性（单窗 5 点）、role 轴质量效应、codex 外侧列（`g1` 32 步上限已判不可用）、探针回灌预算与质量的关系。
7. **前置器 `--round r545` rc=1**（BLOCKED: 8/13 臂 <58/58）⇒ 本轮一切降幅/质量读数标「参考（未可验收）」。
"""


def append_idempotent(path: str, block: str, mark: str) -> str:
    cur = io.open(path, encoding="utf-8").read()
    if mark in cur:
        return "skip(已存在)"
    io.open(path, "a", encoding="utf-8").write(block)
    back = io.open(path, encoding="utf-8").read()
    return "ok" if mark in back else "FAILED"


def main() -> int:
    r1 = append_idempotent(IMP, IMP_BLOCK, MARK)
    r2 = append_idempotent(EV, EV_ROW, "RF0001-E17")
    r3 = append_idempotent(EV, EV_ANNEX, "> R545 追加")
    r4 = append_idempotent(KPI, KPI_BLOCK, "### R545（2026-09-18）")
    print("improvements.md=%s · EVIDENCE.md(E17)=%s · EVIDENCE.md(annex)=%s · KPI.md=%s" % (r1, r2, r3, r4))
    return 0 if all(x in ("ok", "skip(已存在)") for x in (r1, r2, r3, r4)) else 1


if __name__ == "__main__":
    sys.exit(main())
