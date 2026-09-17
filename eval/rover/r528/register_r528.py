#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R528 登记表追加 (文本插入, 禁静默重排整份 JSON)。

纪律 (R409 教训): ① 改写前先断言「序列化器逐字节复现原文件」; ② 只补**前一行**的逗号, 末行之后不加;
③ 幂等; ④ 改写后读回校验 + json.loads 全文件。
"""
import io
import json
import os
import sys

REPO = "/home/agentuser/AgentFramework"
P = os.path.join(REPO, "docs/verification-registry.json")

ROWS = [
    {
        "id": "internal.artifact-placement-selfverification-r528",
        "level": "L4",
        "capability": "**产物落位与自验纪律 (R528)**: 动作环纪律第 6 条 —— 产出物必须落在**工作根**并按题面给定**相对路径**命名; 收尾前必须在工作根按题面验收形态自验, rc≠0 不得收尾。依据 = R525 w3 定因: 同臂 8 调用/3 步把 `games/` 包写到 `<工作根>/sols/games_pkg/games/`, 并在该子目录 `python3 -m games life` 自验通过 (rc=0) 即自认完成; 而验收形态是**工作根**下 `python3 -m games <id>` ⇒ 前置器 0/58 (同一棵树以漂移目录为 cwd 实跑 58/58 ⇒ 代码本身正确)。R528 五窗同窗对照 (同一 AOT 二进制 `8f801491…`, 同一题面 sha `516f3208…`, 同一判据器): A1-on **5/5 窗整题全对 58/58**; 布局漂移 0/5; 挂载 5/5 (纪律块 sha `16efa2f0` 跨窗恒定); 铁律 11 前置器 rc=1 —— **失败在外部真值臂** (w2 codex 52/58), 非本侧。",
        "covers": ["eval/rover/r528/mount_check_r528.py", "eval/rover/r528/layout_census.py",
                   "eval/rover/r528/prereg-r528.json", "eval/rover/r528/run_r528.sh",
                   "src/agent.modelqueue/ActionLoopDiscipline.cs"],
        "evidence_cmd": "python3 eval/rover/r528/mount_check_r528.py --dir w1=eval/rover/r528/run-0917-r528-w1/adapter --range 'A0-off=1,2' --range 'A1-on=3,8' --out eval/rover/r528/evidence/mount-w1.json",
        "evidence_path": "eval/rover/r528/evidence/mount-w1.json; eval/rover/r528/layout-census-r528.json; eval/rover/r507pre/precondition-r528.json",
        "evidence_generated_with": "R528 · /tmp/pub_r528/agenthost sha256 8f801491ef27ed2c89515d6b6e331e8a41392f0a22cdf0ed48b57e70c6d24095",
        "negative_control": "① 同一器具对 **R525 修前 dumps** 跑 ⇒ `MOUNT_VERDICT FAIL` (C1 锚缺失 / C4 仅 5 条), 反解纪律块 sha `cbc691bb` ≠ `16efa2f0` (器具有牙, 非恒真门); ② 对 R525 w3 agentA1 归档树跑普查 ⇒ 分类 `layout_drift_code_ok`, 以漂移目录为 cwd 实跑 58/58 (证伪『0/58 ⇒ 代码缺陷』归因)。",
        "owner_round": "R528",
    },
    {
        "id": "internal.artifact-layout-census-r528",
        "level": "L3",
        "capability": "**归档产物树布局漂移普查 (R528)**: 对 30 棵归档被判树(只读)四分类 —— `layout_ok` / `layout_drift_code_ok` / `layout_drift_code_bad` / `missing_artifacts`, 并对漂移树以反解出的可运行目录为 cwd 实跑同一隐藏用例脚本。读数: layout_ok 26 (其中 22 全对, 4 部分错 31/46/51/46) · layout_drift_code_ok 1 (R525 w3 agentA1) · layout_drift_code_bad 0 · missing_artifacts 3 (全为 A0-off 控制臂空产出) ⇒ 失败面按**成因**分列, 不再把布局漂移读成能力缺陷。",
        "covers": ["eval/rover/r528/layout_census.py", "eval/rover/r528/layout-census.json"],
        "evidence_cmd": "python3 eval/rover/r528/layout_census.py --out eval/rover/r528/layout-census.json",
        "evidence_path": "eval/rover/r528/layout-census.json",
        "evidence_generated_with": "R528 · 归档 r519/r521/r523/r524/r525 snapshots (只读) + /tmp 副本实跑",
        "negative_control": "① 正控: `layout_ok` 树在**树根**实跑必须 58/58 (防扫法恒假; 实测 22/26 全对, 4 棵真部分错 ⇒ 扫法可分辨); ② 同一棵树两种跑法读数不同 (R525 w3 agentA1: 树根 0/58 vs 漂移目录 58/58) ⇒ 分类不是恒值。",
        "owner_round": "R528",
    },
]


def main():
    raw = io.open(P, encoding="utf-8").read()
    doc = json.loads(raw)
    have = {r["id"] for r in doc["rows"]}
    todo = [r for r in ROWS if r["id"] not in have]
    if not todo:
        print("幂等: 全部 id 已在册 (%d 行), 无操作" % len(doc["rows"]))
        return 0

    # ① 序列化器逐字节复现断言 —— 失败则只用文本插入 (本脚本本就只做文本插入, 断言用于定策)
    canon = json.dumps(doc, ensure_ascii=False, indent=1)
    serializer_roundtrip = (canon.rstrip("\n") == raw.rstrip("\n"))
    print("序列化器逐字节复现原文件 =", serializer_roundtrip, "(不成立 ⇒ 禁整份重写, 仅文本插入)")

    anchor = '  }\n ],\n'
    if raw.count(anchor) != 1:
        print("[致命] 插入锚点不唯一 (count=%d) ⇒ 停手" % raw.count(anchor))
        return 3
    lines = []
    for idx, r in enumerate(todo):
        for ln in json.dumps(r, ensure_ascii=False, indent=1).split("\n"):
            lines.append("  " + ln)
        if idx != len(todo) - 1:
            lines[-1] += ","          # 同批多行之间补逗号 (末行不加)
    block = "\n".join(lines) + "\n"
    new = raw.replace(anchor, "  },\n" + block + " ],\n")
    new = new.replace('"updated_round": "R527"', '"updated_round": "R528"')

    io.open(P, "w", encoding="utf-8", newline="\n").write(new)

    back = json.loads(io.open(P, encoding="utf-8").read())
    print("读回校验: rows %d → %d, updated_round=%s" % (len(doc["rows"]), len(back["rows"]), back["updated_round"]))
    ids = [r["id"] for r in back["rows"]]
    ok = all(r["id"] in ids for r in todo) and len(ids) == len(set(ids))
    print("新增 id 在册 =", ok, "| 无重复 id =", len(ids) == len(set(ids)))
    for r in todo:
        row = [x for x in back["rows"] if x["id"] == r["id"]][0]
        print("  +", row["id"], row["level"], "covers=%d" % len(row["covers"]),
              "negctl=%s" % ("有" if row.get("negative_control") else "无"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
