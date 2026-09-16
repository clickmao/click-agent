#!/usr/bin/env python3
"""R484 收口: 把 post-hoc 判据修正 + 判定 写回探针读数, 并追加 docs 两处。

原则: 预注册读数**不覆盖**; 修正单列 `checks_posthoc`; 未入 registry / 未刷轮次索引表 (如实记)。
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
P = ROOT / "eval/rover/r484/micro_local_probe.json"
d = json.loads(P.read_text())

d["checks_posthoc"] = {
    "note": "预注册判据有两条过宽/过严, 预注册读数保留不动, 修正单列于此 (判据纪律: 被证伪⇒宣称收窄+post-hoc单列)",
    "not_echo_too_weak": {
        "evidence": "seq20 本地答案 == 问题首行逐字复读 '[微步骤隔离问询] 不对，你上一条不准确，请重新确认'",
        "why_passed": "预注册用整条 qn (含 '…(只回答本微问题, 不引申)' 尾) 做子串判定 ⇒ 复读首行不触发",
        "strict_rule": "答案 ⊂ 问题正文 (去空白后) ⇒ 判 echo",
        "H2_corrected": "4/5"
    },
    "H4_negation_too_strict": {
        "evidence": "本地 '3 加 5 等于 8。' 只给正确和值, 未加否定词",
        "why_failed": "预注册要求 (含 8 ∧ 含否定词), 否定词非表达『纠错』的必要条件",
        "H4_corrected": {"local": "1/1", "remote": "1/1", "n": 1, "weak": "n=1 ⇒ 证据薄弱"}
    }
}
d["semantic_observations"] = [
    {"seq": 12, "q": "从头再说", "local": "好的，让我们从头开始。", "remote": "我这里没有可重复的前文——本问询是隔离执行的…请把需要『从头再说』的具体内容发给我…",
     "read": "隔离语境下正确行为=指出缺失指代; 本地答成空洞承诺(声称开始却无内容)"},
    {"seq": 20, "q": "不对，你上一条不准确，请重新确认", "local": "(复读首行)", "remote": "本微步骤未提供『上一条』的具体内容…无法重新确认",
     "read": "同型: 本地逐字复读 ⇒ 零信息"}
]
d["fresh_empty_body_repro"] = {
    "seq": 18, "arm": "remote", "finish_reason": "length", "reasoning_tokens": 512, "content_len": 0,
    "note": "本条远端调用**未经 relay** 直连真供应商 ⇒ 独立复现『推理预算吃满 ⇒ 空正文』成因, 排除 relay 侧伪影; 与 R477/R478 诊断 (EmptyBodyCause.LengthExhausted) 一致"
}
d["verdict"] = {
    "micro_all_local_substitution": "NO",
    "basis": "预注册 fail_action: H2<4/5 或 local 算术 0/x 而 remote ≥1/x ⇒ 不实施; 修正后 H2=4/5(勉强过) 但语义面 2/5 空洞 ⇒ 按语义面结案=否",
    "kpi_ceiling_hit": False,
    "kpi_ceiling_note": "本探针只测可行性, 未改变任何 KPI 读数 (R482 分母/分子不动)",
    "residual_candidate": "微问询形态分流: 含指代词(上一条/从头/刚才)者隔离无效 ⇒ 可**直接不发**该微问询(省 1 次远端调用/条, 零信息损失——远端 2 条只花了 132+289 completion 说『没有前文』); 无指代的轻问询才谈本地化"
}
P.write_text(json.dumps(d, ensure_ascii=False, indent=1))
print("[json] patched", P, "len", len(P.read_text()))

IMP = ROOT / "docs/improvements.md"
PLAN = ROOT / "docs/reports/iteration-master-plan.md"

imp_block = """
## R484 · 【探索】微步骤隔离问询 → 本地 r1：可行性探针**判否**（附起手闸假阳性修复）
- 靶点来源（R482 真机读数）：Arole 21 次远端调用中 **7 次(33.3%)** 带 `[微步骤隔离问询]` 前缀（5 次单发 `n_messages==2` + 2 次自身走工具轮），占 token **8.3%** ⇒ 「远端调用数」最大未开发面。
- 器具 `eval/rover/r484/micro_local_probe.py`（预注册 `prereg_r484.json` 先落盘）：5 条真实单发微问询，两臂同题同判据 —— local = 产品同参 llama-server（`-c 4608 -np 1 --cache-type-k/v f32 --flash-attn off --jinja`，模型 sha `626b4a66…`）vs remote = 真供应商（`calls-Arole.jsonl` sha `89f53b56…` 钉住）。
- 预注册读数：H1 非空 **5/5** · H2 机械判据 **5/5** · H3 长度带 **3/4** · H4 算术纠错 local **0/1** vs remote **1/1** · H5 本地延迟 max **4.09s**（n=5）。llama-server 已回收（`alive_after=0`）。
- **判据缺陷两条（post-hoc 单列，不覆盖预注册）**：① `not_echo` 拿整条 qn 比对 ⇒ seq20 本地**逐字复读问题首行**仍判过（严格规则下 H2=4/5）；② H4 要求「含 8 ∧ 含否定词」过严 ⇒ 本地 `3 加 5 等于 8。`（H4 local=1/1，n=1 证据薄弱）。
- 语义面（人读）：**2/5 本地答案实质空洞**（seq12「从头再说」⇒ `好的，让我们从头开始。`；seq20 ⇒ 复读首行），而远端**正确指出「隔离执行未携带前文」** ⇒ 失败模式 = 隔离语境下 r1 不复现「指出缺失指代」，与 R475 反证（r1 生成确认语退化）同族。
- 附带外部真值：远端**自身 1 次空正文**（seq18 `finish_reason=length` / 512 reasoning / content 0，**直连未经 relay**）⇒ 独立复现「推理预算吃满 ⇒ 空正文」，排除 relay 伪影。
- 判定：**微问询整体替换本地 = 否**；残留候选 = **微问询形态分流**（含指代词者隔离无效 ⇒ 直接不发该微问询，省调用且零信息损失）。
- 诚实边界：n=5（H4 n=1）；未测回注主 prompt 后端到端质量；未测工具轮微问询；未入 registry；未刷轮次索引表；未 push。

### R484 附 · 起手闸自匹配假阳性修复（R483b 器具被实跑触发）
- 现象：R484 首跑 `preflight_gate.py` 报 **GATE_BLOCKED**，blocker = `rss=3MB` 的 **bash wrapper**（其 cmd 内含 `llama-server` 字面量，实为**调用方自己的命令行**）⇒ 假阳性（修前只排除自身 pid）。
- 修复：`scan_procs` 改为**排除自身 + 全祖先链**（`/proc/<pid>/stat` PPid 上溯）并**跳过 shell argv0**（监视对象 llama-server/VBCSCompiler/MSBuild/dotnet 均为可执行本体，shell 只会「提到」它们）；新增审计字段 `self_ancestors` / `shells_skipped_n` / `legacy_self_only`。
- **差分负控**（同环境只翻开关）：`--nc-selfmatch`（只排除自身）⇒ **GATE_BLOCKED rc=2**，blocker 指纹与 R483 一致（bash wrapper / rss 3MB）；开关打开 ⇒ **PASS rc=0**（`shells_skipped_n=1`）。器具 sha 修前 `193cc18b…` → 修后 `1a64ceb6…`。
- 附：该负控记录里 `blocker_cause` 标为「内存不足」（mem 2609<2650 同时成立）⇒ **标签不精确**（明细仍在 `blockers`），留作器具候选。
- 复原：本首跑曾覆写 `eval/rover/r483/preflight.json` ⇒ 已 `git checkout` 复原为提交态；其他未提交改动未动。
"""

plan_block = """
### R484 · 【探索】微步骤隔离问询 → 本地 r1：探针判否 + 起手闸假阳性修复
- 器具：`eval/rover/r484/prereg_r484.json`（先落盘）+ `micro_local_probe.py`；读数 `eval/rover/r484/micro_local_probe.json`（`checks_posthoc` / `verdict` 字段）。
- 读数：H1 5/5 · H2 5/5→**post-hoc 4/5** · H3 3/4 · H4 local 0/1 vs remote 1/1→**post-hoc 1/1** · H5 max 4.09s。语义面 **2/5 空洞**（远端反而正确指出「隔离无前文」）。
- 判定：**微问询整体替换本地 = 否**（R475 反证同族）；残留 = **微问询形态分流**。
- 起手闸：`preflight_gate.py` 自匹配假阳性修复（排除自身+祖先+shell argv0）；差分负控 `--nc-selfmatch` rc=2 / 修后 rc=0；sha `1a64ceb6…`。**真机测量起手前必跑**。
- 注：本段为手写追加；**轮次索引表未刷新**（待 R484 入 registry 后由 `eval/tools/master_plan_round_index.py` 生成，禁手改该表）。
- 下轮候选（本段产出）：① **微问询形态分流**（含 `上一条/从头/刚才` 等指代词的隔离微问询 ⇒ 直接不发，省 1 次远端调用/条，零信息损失；无指代轻问询才谈本地化）；② 空正文基数可测化（确定性 stub 造 `finish_reason=tool_calls`+0 tool_calls，对 修前 `/tmp/pub_r476/agenthost` vs 修后 `/tmp/pub_r479v2/agenthost` 做调用数差分）；③ `blocker_cause` 标签精确化；④ R479 遗留（路由器接线 / 入链 prompt 正文槽位化）；⑤ R481-G 遗留（by_subband 分档 / 语料钉四元组）。
"""

IMP.write_text(IMP.read_text() + imp_block)
PLAN.write_text(PLAN.read_text() + plan_block)
print("[docs] appended improvements(%d) plan(%d)" % (len(IMP.read_text()), len(PLAN.read_text())))
