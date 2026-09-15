#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R475 台账收口: registry +3 行 / taskplan +1 节点 / kpi.jsonl +1 行 / improvements 段 / 轮次索引扩到 R475。

保形铁律: registry 保持 indent=1; kpi.jsonl 逐行追加 (utf-8 无 BOM, 与 HEAD 字节一致);
轮次索引只追加行 + 改 2 处 (覆盖自检行 / 标题), 其余逐字节保留。
"""
import collections
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
R = os.path.join(ROOT, "docs/verification-registry.json")
T = os.path.join(ROOT, "docs/plans/v715_dev_plan.taskplan.json")
I = os.path.join(ROOT, "docs/improvements.md")
K = os.path.join(ROOT, "eval/capability/kpi.jsonl")
MP = os.path.join(ROOT, "docs/reports/iteration-master-plan.md")

NEW_ROWS = [
    {
        "id": "r475.repeat-replay-substantive-guard",
        "level": "L2",
        "capability": "纯复述轮的回放守卫: 只有存在**可回放的实质答复**才允许本地消化; 上一条为空/模板/空正文徽标 ⇒ 撤销 Skip 降级远端(禁以模板冒充答复)。"
                      "判据单源: 用户轮 IsPureRepeat + Assistant 侧 ModelQueueRouter.IsReplayableReply(基于产品自身徽标常量, 非新增关键词表)",
        "evidence_cmd": "dotnet test src/agent.tests/agentframework.tests.csproj --filter R475AccountingTests",
        "evidence_path": "src/agent.tests/R475AccountingTests.cs",
        "negative_control": "A1 反向样例(空/空白/模板/徽标 ⇒ false) ∧ A3 结构门(判定必须是 Pass, 出现 Skip 即判红) ⇒ 判据非恒真",
        "covers": [
            "src/agent/IndustrialAgentV2.cs",
            "src/agent.modelqueue/ModelQueueRouter.cs",
            "src/agent.tests/R475AccountingTests.cs",
            "docs/reports/r475-replay-and-cache-accounting.md",
        ],
        "owner_round": "R475",
    },
    {
        "id": "r475.recover-channel-accounting-fields",
        "level": "L2",
        "capability": "llm_call_recover 行补齐 prompt_tokens/cache_hit_tokens/cache_miss_tokens/cache_hit_rate(与 llm_call 同源, 未上报 -1) "
                      "⇒ 产品自记账不再漏账(R474 实测漏 15,458 prompt tokens = Arole 的 21.8%)",
        "evidence_cmd": "dotnet test src/agent.tests/agentframework.tests.csproj --filter R475AccountingTests",
        "evidence_path": "src/agent.tests/R475AccountingTests.cs",
        "negative_control": "A5/A6 反向断言: 任一 emit 出现 old form(无 prompt_tokens 或无 cache_hit_tokens) ⇒ 判红; 且字段缺失时取值为 -1(不冒充 0)",
        "covers": [
            "src/agent.modelqueue/ModelQueueRouter.cs",
            "eval/rover/r475/usage-truth.json",
        ],
        "owner_round": "R475",
    },
    {
        "id": "r475.usage-truth-twin-column",
        "level": "L2",
        "capability": "双列并账(供应商 usage 真值列 vs 产品自记列): 硬分离禁混算; recover 缺字段 ⇒ unreconciled(禁按 0); 唯一跨列运算 gap.* 显式列名; "
                      "并账闭合判据 truth.prompt == product.prompt_call + product.prompt_recover",
        "evidence_cmd": "python3 eval/rover/r475/join_usage_truth.py",
        "evidence_path": "eval/rover/r475/usage-truth.json",
        "negative_control": "join_usage_truth.py --selftest: NC1 缺字段 ⇒ prompt_delta=null(不冒充 0) ∧ NC2 恒等式破坏 ⇒ J1 红 ∧ NC3 混算可辨 ∧ NC4 真数据必有红(判别力非恒绿)",
        "covers": [
            "eval/rover/r475/join_usage_truth.py",
            "eval/rover/r475/usage-truth.json",
            "eval/rover/r475/relay_real_r475.py",
            "eval/rover/r475/selftest_relay_r475.py",
        ],
        "owner_round": "R475",
    },
]

NODE = {
    "Id": "dev-r475-replay-guard-and-accounting",
    "Title": "R475 复述回放取实质答复 + 命中率口径禁>1 + 记账/证据面补齐",
    "State": "done",
    "Round": "R475",
    "DocRef": "docs/plans/v0.91.0-r475-replay-and-cache-accounting.md",
    "Evidence": "eval/rover/r475/verdict-r475.json",
    "Summary": "R474 真端点暴露: R 臂 3/12 用户可见空正文徽标 + 6/12 模板应答 ⇒ 回放守卫(无实质答复则降级远端); "
               "命中率 >1 三例 ⇒ channel 归 shared_prefix + effective=-1; recover 补 prompt/缓存字段(漏账 21.8%); 中继 v2 补 finish_reason/采样面",
}

KPI_ROW = {
    "round": "R475",
    "ts": "2026-09-16T05:05+0800",
    "kind": "质量修复+记账口径+器具硬化 (产品改链 ⇒ AOT 重发布; 本轮零真实调用, 无 llama-server)",
    "artifact": "eval/rover/r475/{relay_real_r475.py,selftest_relay_r475.py,join_usage_truth.py,usage-truth.json,prereg_r475.json,verdict-r475.json,run_tests_x3.sh}; "
                "src/agent.tests/R475AccountingTests.cs; docs/plans/v0.91.0-r475-replay-and-cache-accounting.md; docs/reports/r475-replay-and-cache-accounting.md",
    "change": "① 纯复述轮回放守卫(IsReplayableReply + repeat_degrade_remote, 无实质答复则撤销 Skip) ② llm_call_recover 补 prompt/缓存字段 "
              "③ effective_hit_rate 禁 >1(hit>cacheable ⇒ -1; 该轮 channel 归 shared_prefix) ④ 徽标单源常量 ⑤ 中继 v2(采样面+空正文定因面+逐调用恒等式) ⑥ 双列并账器具",
    "readings": {
        "quality_defect_closed": {
            "r474_R_arm": "实质答复 3/12, 模板 6/12, 用户可见空正文徽标 3/12",
            "r475_fix": "纯复述轮无实质答复 ⇒ 不再以模板冒充, 撤销 Skip 降级远端 (结构门 A3/A4 + 守卫单测 A1/A2)",
            "e2e_rerun": "未做 (MemAvailable 1984MB < 2650MB 起手闸; 见诚实边界)"
        },
        "hit_rate_ceiling_fix": {
            "r474_gt_1_instances": 3,
            "r474_gt_1_values": [1.0589, 1.0066, 1.0822],
            "r475_rule": "hit > min(prompt,last) ⇒ channel=shared_prefix ∧ effective_hit_rate=-1",
            "redline_unchanged": "REDLINE=0.97 一字未动 (仅口径不再产出 >1)"
        },
        "accounting_gap": {
            "truth_vs_product_Arole": {"truth_calls": 20, "truth_prompt": 70890, "product_calls": 16, "product_calls_recover": 4, "product_prompt_call": 55432},
            "truth_vs_product_R": {"truth_calls": 9, "truth_prompt": 29477, "product_calls": 6, "product_calls_recover": 3, "product_prompt_call": 20306},
            "unreconciled_upper": {"Arole_tok": 15458, "Arole_share": 0.2181, "R_tok": 9171, "R_share": 0.3111},
            "allowed_use": "accounting_gap_evidence_only_forbidden_as_kpi_denominator",
            "closure": "deferred (需新一轮真实调用; 本轮以结构门 + 单元测试背书)"
        },
        "instrument_selftests": {"relay_v2": "S1-S7 7/7 (零真实调用, 本地假上游)", "join_usage_truth": "PC+NC1-4 5/5"},
        "form_gate": {"aot_sha256_16": "63dbe9f5f20e19f1", "aot_bytes": 15343232, "il_warnings": 0, "v0_rc": 0, "ldd": "libc/libm only"},
        "tests": {"targeted": "R475AccountingTests 8/8", "full_x3": "eval/rover/r475/run_tests_x3.sh (结果见 tests_x3_r475.log)"}
    },
    "honest_boundaries": [
        "本轮零真实供应商调用 ∧ 无 llama-server ⇒ 质量修复只经结构门 + 单元测试, **未做真机 E2E 复演** (内存闸 1984MB < 2650MB)",
        "recover 字段闭合(R475 fix B)在真实流量上的效果**未验**: 真数据(R474 产物)J2/J3 仍红 = 修复前产物, 属预期",
        "命中率口径 >1 的修复只改「归因/上报」, 供应商实际计价仍未知 (命中是否折价未取到)",
        "中继 v2 的 finish_reason/采样面只经本地假上游自检, 未在真端点取到样本 (R474 空正文根因仍未定)",
        "97% 红线真机可达性仍只有 R469 离线界 (同会话第 2 轮真实样本 = 0)"
    ],
    "next": [
        "内存闸开闸后跑 R 臂真机 E2E: 用中继 v2 让上游返回空正文 ⇒ 验「徽标轮 + 复述轮」不再冒充答复 (fix A 的行为证据)",
        "补真机样本验 recover 字段闭合 + 双列并账 J3 转绿",
        "命中率分档红线迁移(分档上限 + 达成轮占比 + 分通道)",
        "真实供应商计价面(命中折价)取证"
    ],
    "owner_round": "R475",
}

IMPROVE = """
## R475（2026-09-16）复述回放取实质答复 + 命中率口径禁 >1 + 记账面补齐

**因果链**：R474 首次让真端点回话，暴露两件事：① **质量缺陷** —— R 臂 12 轮里 6 轮模板应答、3 轮用户可见「模型未产出正文…」徽标，实质回答仅 3/12（同轮 Arole 12/12 实质）；② **记账缺口** —— 产品 `llm_call` 自报 16 调用 / 55,432 prompt tokens，而供应商 usage 是 20 调用 / 70,890 tokens，差的 15,458（21.8%）全在 `llm_call_recover` 行（不带 prompt/缓存字段）。同时 R474 报告里 `effective_hit_rate` 出现 **3 例 >1**（1.0589 / 1.0066 / 1.0822），因为「同会话可缓存上界 = min(prompt, 上一条 prompt)」小于真实命中量（命中来自更长的共享前缀）。

**改动（单源 + 可机检）**
1. **回放守卫** `ModelQueueRouter.IsReplayableReply`：空/空白/`LocalSkipFallback` 模板/空正文徽标前缀 ⇒ 不可回放；纯复述轮取不到可回放答复 ⇒ **撤销 Skip 降级远端**（`gate:repeat_no_replayable_prev`），遥测 `repeat_degrade_remote` + `prefilter_repeat_degrade`。徽标文本改由 `EmptyBodyBannerPrefix` 单源常量拼出（判据作用于 Assistant 侧历史文本，非新增用户轮关键词表）。
2. **记账补齐**：`llm_call_recover` 两条 emit（成功/异常路径）补 `prompt_tokens` + `cache_hit_tokens/cache_miss_tokens/cache_hit_rate`（同源 `first`，未上报 -1）。
3. **口径禁 >1**：`EffectiveHitRate` 加 `hit > cacheable ⇒ -1` 钳制；`Channel/SharedPrefix*` 增加 `ExceedsSameSession` 判据（命中量超过同会话上界 ⇒ 归 `shared_prefix`）。
4. **器具**：中继 v2（`relay_real_r475.py`，另存不改 R474 器具 = 证据↔器具绑定）补采样面 + `finish_reason/content_len/reasoning_len/reasoning_tokens/empty_body` + **逐调用**恒等式；`join_usage_truth.py` 双列并账（真值列/自记列硬分离，唯一跨列运算 gap.*，缺字段 ⇒ unreconciled 禁按 0）。

**读数**
| 项 | 值 |
|---|---|
| R474 质量缺陷（R 臂） | 实质 3/12 · 模板 6/12 · 可见徽标 3/12 |
| R474 漏账（Arole / R） | 15,458 tok (21.8%) / 9,171 tok (31.1%) |
| `effective_hit_rate` >1 | 3 例 ⇒ 本轮口径后不再可能（-1 + 归 shared_prefix） |
| 中继 v2 自检 | S1–S7 **7/7**（零真实调用） |
| 并账自检 | PC + NC1–NC4 **5/5**（真数据必有红 ⇒ 判据非恒绿） |
| AOT | 15,343,232 B · sha16 `63dbe9f5f20e19f1` · IL 警告 0 · V0 rc=0 |
| 定向单测 | R475AccountingTests **8/8** |

**诚实边界**：零真实调用 ∧ 无 llama-server（MemAvailable 1984MB < 2650MB 闸）⇒ 质量修复**未做真机 E2E**；recover 字段闭合在真实流量上未验；命中折价未取到；R474 空正文根因仍未定（本轮只把定因所需证据面补上）。
"""


def rnum(r):
    try:
        return int(str(r.get("owner_round", "")).lstrip("Rr"))
    except Exception:
        return None


def main():
    reg = json.load(io.open(R, encoding="utf-8"), object_pairs_hook=collections.OrderedDict)
    rows = reg["rows"]
    have = {r["id"] for r in rows}
    added = 0
    for r in NEW_ROWS:
        if r["id"] not in have:
            rows.append(r)
            added += 1
    reg["updated_round"] = "R475"
    io.open(R, "w", encoding="utf-8").write(json.dumps(reg, ensure_ascii=False, indent=1) + "\n")

    tp = json.load(io.open(T, encoding="utf-8"), object_pairs_hook=collections.OrderedDict)
    if all(n.get("Id") != NODE["Id"] for n in tp["Nodes"]):
        tp["Nodes"].append(NODE)
    io.open(T, "w", encoding="utf-8").write(json.dumps(tp, ensure_ascii=False, indent=2) + "\n")

    # kpi.jsonl: 逐行追加, 幂等 (round 已存在则跳过); utf-8 无 BOM
    existing = io.open(K, encoding="utf-8-sig").read() if os.path.exists(K) else ""
    if '\"round\": \"R475\"' not in existing:
        with io.open(K, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(KPI_ROW, ensure_ascii=False) + "\n")

    s = io.open(I, encoding="utf-8").read()
    if "复述回放取实质答复" not in s:
        io.open(I, "a", encoding="utf-8", newline="\n").write(IMPROVE)

    # 轮次索引: 只追 R475 行 + 改 2 处
    FROM, TO = 475, 475
    sel = [r for r in rows if rnum(r) is not None and FROM <= rnum(r) <= TO]
    new_lines = []
    for r in sel:
        cap = str(r.get("capability", "")).replace("\n", " ").replace("|", "/")
        if len(cap) > 88:
            cap = cap[:88] + "…"
        new_lines.append("| R%d | `%s` | %s | %s |\n" % (rnum(r), r["id"], r.get("level", "?"), cap))
    lines = io.open(MP, encoding="utf-8").read().splitlines(keepends=True)
    i_cov = next(i for i, l in enumerate(lines) if l.startswith("覆盖自检:"))
    i_hdr = next(i for i, l in enumerate(lines)
                 if re.match(r"^## R441–R4\d\d 轮次索引", l))
    present = set(re.findall(r"\|\s*R\d+\s*\|\s*`([^`]+)`\s*\|", "".join(lines[i_hdr:i_cov])))
    ins = [l for l in new_lines if re.findall(r"`([^`]+)`", l)[0] not in present]
    covered = sorted({rnum(r) for r in rows if rnum(r) is not None and 441 <= rnum(r) <= 475})
    missing = [n for n in range(441, 476) if n not in covered]
    imp = io.open(I, encoding="utf-8").read()
    missing_txt = ""
    if missing:
        with_block = [n for n in missing if ("\n## R%d（" % n) in imp]
        unused = [n for n in missing if n not in with_block]
        parts = []
        if with_block:
            parts.append("有块但无登记行: %s" % ", ".join(str(n) for n in with_block))
        if unused:
            parts.append("**该号未被使用(improvements.md 亦无块): %s**" % ", ".join(str(n) for n in unused))
        missing_txt = "**缺登记行轮号: %s**（%s）。" % (", ".join(str(n) for n in missing), "；".join(parts))
    new_cov = ("覆盖自检: 轮号 [%s]；registry rows=%d，updated_round=%s。%s\n"
               % (", ".join(str(n) for n in covered), len(rows), reg.get("updated_round", "?"), missing_txt))
    new_hdr = re.sub(r"^## R441–R4\d\d 轮次索引（[^；]*；",
                     "## R441–R475 轮次索引（2026-09-15 首次回填，R475 扩展到 R475；", lines[i_hdr])
    if new_cov != lines[i_cov] or ins or new_hdr != lines[i_hdr]:
        out = lines[:i_cov] + ins + [new_cov] + lines[i_cov + 1:]
        out[i_hdr] = new_hdr
        io.open(MP, "w", encoding="utf-8", newline="\n").write("".join(out))

    print(json.dumps({
        "registry_rows": len(rows), "added": added, "updated_round": reg["updated_round"],
        "taskplan_nodes": len(tp["Nodes"]),
        "kpi_rows": len([l for l in io.open(K, encoding="utf-8-sig") if l.strip()]),
        "index_rows_added": len(ins), "index_rounds": [rnum(r) for r in sel],
        "improvements_bytes": len(io.open(I, encoding="utf-8").read().encode("utf-8")),
    }, ensure_ascii=False))
    print(new_cov.strip())


if __name__ == "__main__":
    main()
