#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R448 登记：verification-registry + improvements + master plan（纯落盘，可重跑幂等）。"""
import json
import pathlib

ROOT = pathlib.Path("/home/agentuser/AgentFramework")

ROW = {
    "id": "r448.judge-think-length-cap",
    "capability": "判官 prompt 侧「限长思考」（保留思考、只压缩长度）真机消融 —— 负结论: 生成仅降 33.0%"
                  "（178.6→119.7）且预算 128 下 61.1% 思考被截断、与产品基线判决一致率 0.1667 ⇒ 不得启用",
    "level": "L3",
    "owner_round": "R448",
    "evidence_cmd": "python3 eval/rover/r448/r448_corpus.py; python3 eval/rover/r448/r448_probe.py; "
                    "python3 eval/rover/r448/r448_analyze.py",
    "evidence_path": "eval/rover/r448/verdict-r448.json",
    "negative_control": "C6 真错配 prev 8/8（语料构建器机检 G3）且 agree(NC1t,T1)=0.0<=0.85 ⇒ 器具非空心; "
                        "CH2 归档第三通道 J0 12/12 逐条复现产品字母; CH7 同 prompt 同解码档跨轮 gen 和逐位相同"
                        "（3215/3215, R447 存档）⇒ 器具可复现; C7 恒等式 tokens_evaluated==timings.prompt_n+cache_n "
                        "62/62 ⇒ 闭合 R447 C5 未测债; C7 红为判定项设计缺陷（T 臂 prompt 长 28 字符 ⇒ 跨臂 prompt_n "
                        "按定义不等）其语义由 CH6 修正口径承接（T2 vs T1 18/18）",
    "covers": ["eval/rover/r448/r448_corpus.py", "eval/rover/r448/r448_probe.py",
               "eval/rover/r448/r448_analyze.py", "src/agent.roles/CorrectionDetector.cs",
               "src/agent.modelqueue/LocalGenerationPort.cs"],
}

reg_path = ROOT / "docs/verification-registry.json"
reg = json.loads(reg_path.read_text(encoding="utf-8"))
reg["rows"] = [r for r in reg["rows"] if r.get("id") != ROW["id"]] + [ROW]
reg["updated_round"] = "R448"
reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("registry rows:", len(reg["rows"]), "updated_round:", reg["updated_round"])

R448_DOC = """
## R448 — 判官 prompt 侧「限长思考」消融：**负结论**（真机探针，零产品代码改动）

- 靶（承 R446 机制 + R447 负结论）: 本地判官成本 = 预填充 2764 + **生成 1974**（M20 全本地真值 7841）；R447 已判死「解码侧强制单字母」（取消思考 ⇒ 恒 A、不等价）。本轮独剩的形态 = **保留思考、只限其长度**（prompt 插入「思考最多 2 句 (不超过 40 字), 不要展开推理。」，`n_predict` 128）。
- 臂（同语料 18 对，解码档钉死 temp 0）：`J0` 产品 prompt/512（本轮重跑基线）｜`T2` 限长 prompt/**512**（隔离 prompt 单独效应）｜`T1` 限长 prompt/**128**｜`NC1t` T1 配置 + **真错配 prev**（8 对）。
- 读数（`verdict-r448.json`）: J0 gen 均值 **178.6**（median 169，max 512，Σ3215）；**T2 138.5**（median 138.5，max 211，0/18 截断）；**T1 119.7**（median 128 = 触顶，**截断 11/18 = 61.1%**，另有 1 条空结论 ⇒ 可解析率 **0.3333**）。
- 判据 6 红: **C1 非空心 FAIL**（T1 可解析 0.3333）｜**C2 生成降幅 FAIL**（比值 0.6702 > 0.36）｜**C3 prompt 单独效应 FAIL**（T2 比值 0.7755 > 0.75 **且** agree(T2,J0)=0.4444）｜**C4 等价 FAIL**（agree(T1,J0)=0.1667、agree(T1,归档)=0.1667）｜**C5 截断闭合 FAIL**（T1 11 条 vs 目标 0）｜**C7 记账 FAIL**（判定项设计缺陷，见下）。**C6 负控 PASS**。
- 机制结论: **该 1.5b 蒸馏模型的思考长度不受 prompt 指令控制**（限长子句下真实长度仍 median 138.5 / max 211），而在判官通道里**思考是判决的承重结构**（改一字即刻改判决：T2 与 J0 判决一致率仅 0.4444）⇒ 压思考=改判决=不等价；只压预算=截断=产品必然 fallback 远端=**更贵**。**本地生成侧无可用的压缩通道**（R447 解码约束 + R448 prompt 限长，两条均因不等价关闭）。
- 收益上限（反事实，不计入 KPI）: 即便强行启用，判官生成按 0.67 折算 ⇒ M20「含本地真值」口径仅 33.32% → **34.38%**（+1.06 pt）⇒ 收益与风险不成比例。
- 器具机械闸（承 R447 候选 4，新建立即生效）: G1 独立重建 18/18 与快照逐字节相同｜G1b 忠实性 9/9 产品实发原文｜G2 prev 面多样性下界（distinct=3、>25 字符 1 条——**只钉下界不宣称强**）｜**G3 负控真错配 8/8**（直接封死 R447 C4a 那类「判定项设计缺陷」）。
- 自纠（必须披露）: ① 分析器 C6 判据写成 `(ag_NC or 1) <= 0.85`，`agree=0.0` 被 `or` 吞掉成 1.0 ⇒ 首版误判 FAIL；已修并重跑（C6 转 PASS）。② C7 预注册含「逐样本 prompt_n 跨臂相等」——但 T 臂 prompt 比 J0 长 28 字符（正是被消融的自变量）⇒ 该断言按定义不可能成立（0/18），属**判定项设计缺陷**；已按判据纪律**保留 C7 红、单列** CH6 修正口径（T2 vs T1 **18/18** 相等 + cache/恒等式/argv 全绿）。
- 诚实边界: ① 单模型档（`r1-distill-1.5b-q4km`）+ 单容器（`-c 4608`）；② 语料 msg 全 ≤18 字符、prev 真值仅 3 种（**prev 面弱**，G2 只钉下界）；③ 口径 = 本地 llama-server 真值 token，**未转成**用户可见的远端 API 计费；④ 未做远端 A/B（等价已红 ⇒ 无必要）；⑤ 门通道（`local_turn_gate` ~130 tok/调用 ×7）**本轮未测**；⑥ 无链跑 ⇒ **不写 `eval/capability/kpi.jsonl`**；零产品代码改动 ⇒ 无 AOT/测试对象。
- 登记: `docs/verification-registry.json` → `r448.judge-think-length-cap`；证据 `eval/rover/r448/README-evidence.md`；计划 `docs/plans/v0.68.0-r448-judge-think-length-cap.md`。

### 下轮候选（R449，按优先级）
1. **预填充侧压缩**（2764 tok/10 调用 = M20 判官成本的 58%）：判官 prompt head 含 3 条例式示例 → 逐条删减/改述的**等价性**真机消融（同臂 J0 对照 + 归档第三通道 + G3 真错配负控）。← 首选（本地降本仅剩的两条通道之一，且与生成侧无关）
2. **判官 + 门合并为单次本地调用**（R435/R438 遗留候选）：省一次冷启动与一次预填充；先只读复现两通道 prompt 形状与调用次数（判官 10 / 门 7，M20）。
3. **门通道同构消融**（`local_turn_gate` 生成 ~130 tok ×7）：先只读机制复现，再与判官同臂。
4. **把「判定项设计缺陷」前置成器具闸**：预注册里凡出现「跨臂相等」类断言，构建器须先机检该断言在**臂定义层面**可满足（本轮 C7 / R447 C4a 同类错误两次复发 ⇒ 升为通用闸）。
"""

imp = ROOT / "docs/improvements.md"
txt = imp.read_text(encoding="utf-8")
if "## R448 — 判官 prompt 侧" not in txt:
    if not txt.endswith("\n"):
        txt += "\n"
    txt += R448_DOC
    imp.write_text(txt, encoding="utf-8")
    print("improvements.md: appended R448")
else:
    print("improvements.md: already has R448")

MP = """
## R448（2026-09-15）判官 prompt 侧「限长思考」消融 → **负结论**（本地生成侧压缩通道全部关闭）
- 臂: J0(产品/512) / T2(限长 prompt/512) / T1(限长 prompt/128) / NC1t(T1+真错配 prev)，18 对忠实语料。
- 读数: gen 178.6 → T2 **138.5**（0 截断）→ T1 **119.7**；T1 截断 **11/18**、可解析 0.3333；agree(T1,J0)=**0.1667**、agree(T1,归档)=**0.1667**。
- 判据: C6 PASS，C1/C2/C3/C4/C5 功能性红 + C7 判定项缺陷（CH6 修正口径 18/18 PASS）。
- 机制: 思考长度不受 prompt 指令控制（T2 median 138.5）且思考承重（改 prompt ⇒ 判决漂移 0.4444）⇒ 压思考=改判决；压预算=截断=fallback 远端=更贵。
- 反事实上限: 含本地真值口径 33.32% → 34.38%（+1.06 pt），收益/风险不成比例。
- 器械: G1 重建 18/18｜G1b 忠实性 9/9｜G2 prev 多样性下界（3 / 长 1）｜**G3 真错配 8/8**；C7 恒等式 62/62 闭合 R447 C5 债；跨轮确定性 Σgen 3215/3215 相同。
- 证据: `eval/rover/r448/README-evidence.md`｜计划: `docs/plans/v0.68.0-r448-judge-think-length-cap.md`｜登记: registry `r448.judge-think-length-cap`。
- 下轮候选: ①判官**预填充**侧压缩（2764 tok/10 调用）等价性消融 ②判官+门合并单次本地调用 ③门通道同构消融 ④把「跨臂相等类断言须先机检臂定义可满足」升为器具通用闸。
"""
mp = ROOT / "docs/reports/iteration-master-plan.md"
t2 = mp.read_text(encoding="utf-8")
if "## R448（2026-09-15）" not in t2:
    if not t2.endswith("\n"):
        t2 += "\n"
    t2 += MP
    mp.write_text(t2, encoding="utf-8")
    print("master-plan: appended R448")
else:
    print("master-plan: already has R448")
