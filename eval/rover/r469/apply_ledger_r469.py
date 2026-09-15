#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R469 台账收口: registry +2 行 / taskplan 节点 / improvements 段。"""
import io, json

R = "docs/verification-registry.json"
T = "docs/plans/v715_dev_plan.taskplan.json"
I = "docs/improvements.md"

NEW_ROWS = [
    {
        "id": "r469.hit-ceiling-bands",
        "level": "L2",
        "capability": "命中率理论上限分档: 把用户轮长度从命中率分母剥离, 机检真实轮(400)在四档下的命中上限与达97%所需前缀; 显式声明长档(>93 tok)结构性不可达(86.8~96.2%), 97%单值红线不得对长中档报出",
        "evidence_cmd": "python3 eval/rover/r469/hit_ceiling_bands.py",
        "evidence_path": "eval/rover/r469/hit-ceiling.json",
        "negative_control": "prefix_stability.py --neg-control: 正控(纯尾部追加) share=1.0 ∧ 负控(system 首段注入动态字段) share=0.7918 分歧前移 ⇒ 前缀占比指标非恒真",
        "covers": [
            "eval/rover/r469/hit_ceiling_bands.py",
            "eval/rover/r469/hit-ceiling.json",
            "docs/reports/r469-hit-ceiling-bands.md",
        ],
        "owner_round": "R469",
    },
    {
        "id": "r469.main-call-prefix-stability",
        "level": "L2",
        "capability": "主调用 prompt 前缀逐字节稳定性(离线, 无 llama-server): 从桩侧落盘全量 messages 复算逐对公共前缀/新增字符数; 门控臂 R 主调用 5/5 对 tail_only ∧ share=1.0, 新增由用户轮主导(206~367 字符) ⇒ 注入侧无压缩空间",
        "evidence_cmd": "python3 eval/rover/r469/prefix_stability.py",
        "evidence_path": "eval/rover/r469/prefix_stability_r467.json",
        "negative_control": "同 --neg-control 正/负控对(见 r469.hit-ceiling-bands); 且真实低值对(share 0.0010~0.0013)来自跨类调用交错, 证明指标对非 tail-only 输入不恒真",
        "covers": [
            "eval/rover/r469/prefix_stability.py",
            "eval/rover/r469/prefix_stability_r467.json",
            "eval/rover/r469/prefix_stability_negctl.json",
        ],
        "owner_round": "R469",
    },
]

NODE = {
    "Id": "dev-r469-hit-ceiling-bands",
    "Title": "R469 命中率理论上限分档(用户轮不可压 ⇒ 97% 对长档不可用)",
    "State": "done",
    "Round": "R469",
    "DocRef": "docs/plans/v0.86.0-r469-hit-ceiling-bands.md",
    "Evidence": "eval/rover/r469/hit-ceiling.json",
    "Summary": "主调用 5/5 对 tail-only(share=1.0); 短档 49.5% 可达 97%, 长档上限 86.8~96.2% 结构性不可达; 负控 share 1.0→0.7918",
}

IMPROVE = """
## R469（2026-09-16）命中率理论上限分档：用户轮长度不可压

**因果链**：R461 起 97% 命中率以单值红线报出（前缀 3.1k ⇒ 新增 ≤93.5 tok），从未检验「新增里的用户轮能否被注入策略压到 93.5 tok 以下」→ 用桩侧落盘的全量 `messages[]`（外部真值）离线复算逐对公共前缀 + 按用户轮长度分档 → 新增部分 = 上一轮承接（15/21 字符）+ **本轮用户轮（206–367 字符）**，由用户轮主导，注入侧无可压空间。

**读数**

| 档（字符） | 轮数 | 占比 | 中位用户 tok | 前缀 2.1k | 前缀 3k | 前缀 4k | 97% 可达 |
|---|---|---|---|---|---|---|---|
| 0–30 | 130 | 32.5% | 11 | 98.51% | 98.94% | 99.21% | ✔ |
| 31–93 | 68 | 17.0% | 51 | 96.70% | 97.66% | 98.23% | ✔ |
| 94–200 | 64 | 16.0% | 138 | 92.99% | 94.97% | 96.18% | ✘ |
| 201+ | 138 | 34.5% | 300 | 86.80% | 90.33% | 92.57% | ✘ |

门控臂 R 主调用 **5/5 对逐字节 tail-only**（`prefix_share`=1.0）⇒ 可缓存性经实测，非假设；负控（system 首段动态字段）`share` 1.0 → 0.7918 ⇒ 指标非恒真。

**结论**：命中率须**分档报**（上限 + 达成轮占比）：短档 49.5% 现况即 ≥96.7%；长档上限 ≤96.2%，97% 结构性不可达。提升路径由「压新增」改为「升前缀」（稳定内容前置、缓存摊薄），与 R461 按需注入方向相反 ⇒ 列 R470。
"""


def main():
    reg = json.load(io.open(R, encoding="utf-8"))
    rows = reg["rows"] if isinstance(reg, dict) and "rows" in reg else reg
    have = {r["id"] for r in rows}
    added = 0
    for r in NEW_ROWS:
        if r["id"] not in have:
            rows.append(r)
            added += 1
    if isinstance(reg, dict):
        reg["updated_round"] = "R469"
        reg["rows"] = rows
    io.open(R, "w", encoding="utf-8").write(json.dumps(reg, ensure_ascii=False, indent=1) + "\n")

    tp = json.load(io.open(T, encoding="utf-8"))
    if all(n.get("Id") != NODE["Id"] for n in tp["Nodes"]):
        tp["Nodes"].append(NODE)
    io.open(T, "w", encoding="utf-8").write(json.dumps(tp, ensure_ascii=False, indent=2) + "\n")

    s = io.open(I, encoding="utf-8").read()
    if "命中率理论上限分档" not in s:
        io.open(I, "a", encoding="utf-8").write(IMPROVE)

    print("registry_rows", len(rows), "added", added, "| taskplan_nodes", len(tp["Nodes"]),
          "| improvements_bytes", len(io.open(I, encoding="utf-8").read().encode("utf-8")))


if __name__ == "__main__":
    main()
