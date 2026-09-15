#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R478 台账机派生刷新（承 R472/R474/R475 先例，幂等）。

面: ① registry 3 行 id 幂等注册(已由 bind_evidence --apply --round R478 派生子字段, 本脚本不重复派生)
    ② taskplan 节点 dev-r478 (幂等)
    ③ kpi.jsonl 逐行追加(round 已存在则跳过, utf-8 无 BOM)
    ④ improvements.md R478 块(幂等, 只在缺失时追加)
    ⑤ iteration-master-plan.md 轮次索引 R476–R478 行 + 覆盖自检行机派生刷新(只追加行 + 改 1 行)
保形铁律: registry / taskplan 沿用既有 indent; 索引面只动「插入行 + 覆盖自检行」两处。
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

ROUND, FROM, TO = "R478", 476, 478

NEW_IDS = [
    "r478.empty-body-cause-protocol-only",
    "r478.request-turn-causal-binding",
    "r478.hit-rate-cold-steady-split",
]

NODE = {
    "Id": "dev-r478-empty-body-cause-and-request-binding",
    "Title": "R478 空正文定因机制化(finish_reason 判据) + 请求-轮次因果绑定 + 命中率冷/稳态分列",
    "State": "done",
    "Round": "R478",
    "DocRef": "docs/plans/v0.94.0-r478-empty-body-cause-and-request-binding.md",
    "Evidence": "eval/rover/r478/verdict-r478.json",
    "Summary": "R477 真机: 20/20 空正文调用上游 finish_reason==tool_calls 而产品误诊为「推理吃满预算」且白跑 32k 重试 "
               "⇒ 定因只取协议字段 + ToolCall 因不重试 + 文案单源(产品面 3 调用点) + 动作环出口禁静默空回复; "
               "另 request_id 贯穿 llm_call/loop_turn ⇒ 轮次归属按 id join; R477 命中率聚合差 −6.70pp 中 −6.29pp 系冷启动占比伪影(稳态差 −0.41pp)",
}

IMPROVE = """
## R478（2026-09-16）空正文定因机制化（finish_reason 判据）+ 请求-轮次因果绑定 + 命中率冷/稳态分列

**因果链**：R477 真机复演抓到两处同源缺陷。① **误诊**：20/20 条「用户可见空正文」调用的上游 `finish_reason == tool_calls`（`max_tokens == None`、`reasoning_tokens` 395/122 ≪ 预算）⇒ 不是预算被推理吃满，而是上游在请求执行工具动作；产品徽标却写「推理过程占满了输出预算」，并据此**白跑一次 32k 预算的重试**（调用数与 token 双浪费）。② **归属漂移**：5 条 `llm_call` 落在所记轮次窗口之外 ⇒ 轮次归属只能靠时间窗猜。③ **读数伪影**：R 臂命中率 0.791 < Arole 0.858 看似机制退化，按 R456b 分列后 **稳态两臂近等（0.9149 vs 0.9190，−0.41pp）**，聚合差 −6.70pp 中 −6.29pp 系**冷启动窗口占比差**（9.5% vs 20.0%）。

**改动（单源 + 可机检）**
1. **定因机制** `src/agent.modelqueue/EmptyBodyDiagnosis.cs`：`EmptyBodyCause{ToolCall,LengthExhausted,UpstreamStop,Unknown}`；判据**只取上游协议字段**（`finish_reason` / `tool_calls` / reasoning 长度），**零用户文本关键词**；文案单源 `Banner(cause, finishReason)`（**产品面仅 3 个调用点**：`ActionLoop.cs:243`、`ModelQueueRouter.cs:736`（空正文）、`:1217`（恢复通告））。
2. **不浪费重试**：`ToolCall` 因 `Retryable=false` ⇒ 空正文分支 `retry_skipped=true`（×2 emit 路径），恢复路径被 `LengthExhausted ∨ reasoning 非空` 守卫。
3. **因果绑定**：`QueueResponse.RequestId`（单调签发）→ `llm_call` 遥测带 `request_id`/`finish_reason`/`tool_calls_n`/`empty_cause` → 透传 `llmResponse.ResponseId` → 链侧 `_replyRequestId` 捕获并逐轮清零、`loop_turn` 打点带 `request_id` ⇒ 轮次归属可按 id **严格 join**。
4. **动作环出口可见**：出口空正文 ⇒ 单源文案 + `ContentIsUserFacing = true`，**禁静默空回复**。
5. **器具**：`eval/rover/r478/check_r478.py`（C1–C7 + 负控 NC1–NC3，fail-closed：取不到源码常量即抛 MISS）、`band_reestimate_r477.py`（R456b 冷/稳态分列）。
6. **台账机派生刷新**：`bind_evidence.py --apply --round R478`（附带抓到本方 3 行缺 `owner_round` ⇒ 形式门禁判红 ⇒ 已补）。

**读数**
| 项 | 值 |
|---|---|
| 定因面机检 | `verdict=PASS 7/7` + 负控 `NC 3/3`（NC1 旧文案⇒C2 红 / NC2 关键词分类器⇒C1 红 / NC3 未透传⇒C4 红） |
| 全量单测 | **1469/1469 ×3**（R476 时 1451 ⇒ 净增 18；Failed 0） |
| 焦点单测 | 30/30 → 43/43 |
| AOT | 15,363,712 B · sha16 `499a7552897992f1` · IL 0 · `env -i --version` rc=0 |
| 命中率（供应商真值） | 稳态 Arole `0.919019`(19 调用) vs R `0.914939`(8 调用) = **−0.41pp**；聚合 `0.857967` vs `0.791011` = −6.70pp（−6.29pp 系冷启动占比伪影） |
| 恒等式 | `hit + miss == prompt` 逐行成立 21/21 + 10/10 |

**诚实边界**：起手闸 `MemAvailable 2293 MB < 2650 MB` ⇒ **本轮无真机 E2E**；`request_id` 因果绑定只证机制存在（真机 join 未验）；分档轴 `prompt_tokens` 代理全落 `201+` 档 ⇒ `band_degenerate=true`，**不冒充分档结论**；预注册晚于焦点单测首跑 ⇒ 描述性数字入 `checks_posthoc`（承 R453）。
"""


def rnum(r):
    try:
        return int(str(r.get("owner_round", "")).lstrip("Rr"))
    except Exception:
        return None


def main():
    reg = json.load(io.open(R, encoding="utf-8-sig"), object_pairs_hook=collections.OrderedDict)
    rows = reg["rows"]
    have = {r["id"] for r in rows}
    added = [i for i in NEW_IDS if i not in have]
    reg["updated_round"] = ROUND
    io.open(R, "w", encoding="utf-8", newline="\n").write(json.dumps(reg, ensure_ascii=False, indent=1) + "\n")

    tp = json.load(io.open(T, encoding="utf-8"), object_pairs_hook=collections.OrderedDict)
    node_added = 0
    if all(n.get("Id") != NODE["Id"] for n in tp["Nodes"]):
        tp["Nodes"].append(NODE)
        node_added = 1
        io.open(T, "w", encoding="utf-8", newline="\n").write(json.dumps(tp, ensure_ascii=False, indent=1) + "\n")

    kpi_text = io.open(K, encoding="utf-8-sig").read()
    kpi_added = 0
    if '"round": "R478"' not in kpi_text:
        kpi_added = 1

    s = io.open(I, encoding="utf-8").read()
    imp_added = 0
    if "R478（2026-09-16）空正文定因机制化" not in s:
        io.open(I, "a", encoding="utf-8", newline="\n").write(IMPROVE)
        imp_added = 1

    # ---- 轮次索引: 追加 R476–R478 行 + 覆盖自检行机派生 ----
    sel = [r for r in rows if rnum(r) is not None and FROM <= rnum(r) <= TO]
    new_lines = []
    for r in sel:
        cap = str(r.get("capability", "")).replace("\n", " ").replace("|", "/")
        if len(cap) > 88:
            cap = cap[:88] + "…"
        new_lines.append("| R%d | `%s` | %s | %s |\n" % (rnum(r), r["id"], r.get("level", "?"), cap))
    lines = io.open(MP, encoding="utf-8").read().splitlines(keepends=True)
    i_cov = next(i for i, l in enumerate(lines) if l.startswith("覆盖自检:"))
    i_hdr = next(i for i, l in enumerate(lines) if re.match(r"^## R441–R4\d\d 轮次索引", l))
    present = set(re.findall(r"\|\s*R\d+\s*\|\s*`([^`]+)`\s*\|", "".join(lines[i_hdr:i_cov])))
    ins = [l for l in new_lines if re.findall(r"`([^`]+)`", l)[0] not in present]
    covered = sorted({rnum(r) for r in rows if rnum(r) is not None and 441 <= rnum(r) <= TO})
    missing = [n for n in range(441, TO + 1) if n not in covered]
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
                     "## R441–R478 轮次索引（2026-09-15 首次回填，R478 扩展到 R478；", lines[i_hdr])
    wrote_mp = 0
    if new_cov != lines[i_cov] or ins or new_hdr != lines[i_hdr]:
        out = lines[:i_cov] + ins + [new_cov] + lines[i_cov + 1:]
        out[i_hdr] = new_hdr
        io.open(MP, "w", encoding="utf-8", newline="\n").write("".join(out))
        wrote_mp = 1

    print(json.dumps({
        "registry_rows": len(rows), "new_ids_missing": added, "updated_round": reg["updated_round"],
        "taskplan_nodes": len(tp["Nodes"]), "node_added": node_added, "kpi_added": kpi_added,
        "improve_added": imp_added, "index_rows_added": len(ins),
        "index_rounds": sorted({rnum(r) for r in sel}), "mp_written": wrote_mp,
    }, ensure_ascii=False))
    print(new_cov.strip())


if __name__ == "__main__":
    main()
