#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R481-D9 台账机派生刷新 (承 R472/R474/R475/R478 先例, 幂等)。

面: ① registry 追加 1 行 `r481.recall-d9-alternating-verify` (证据绑定字段由 bind_evidence --apply --round R481 派生)
    ② docs/improvements.md 的 R481 段: 状态行 + 新增 R481-D 条 + 基线条 + 下轮候选 (定点替换, 锚缺失即 MISS 退出)
    ③ docs/reports/iteration-master-plan.md: R481 基线段正文刷新 + 追加「R481 轮次索引增量」段 (机取自 registry)
不写 kpi.jsonl (单轮探针, 非 KPI 轮)。
保形铁律: registry 沿用 indent=1 / ensure_ascii=False / 尾换行, 写前断言序列化器逐字节复现原文件, 写后读回。
"""
import collections
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
R = os.path.join(ROOT, "docs/verification-registry.json")
I = os.path.join(ROOT, "docs/improvements.md")
MP = os.path.join(ROOT, "docs/reports/iteration-master-plan.md")
IDX = os.path.join(ROOT, "eval/tools/master_plan_round_index.py")
ROUND = "R481"

ROW = collections.OrderedDict([
    ("id", "r481.recall-d9-alternating-verify"),
    ("level", "L2"),
    ("capability",
     "**目录 mtime 剪枝盲区**修复 = 交替核验: 指纹头 stamp 改 `(stampTicks << 1) | 上轮是否剪枝`(低位), 读侧 `(ticks >> 1)` + "
     "`(ticks & 1UL) != 0UL`; 剪枝开关 = `options.PruneUnchangedDirs && store is not null && !prevScanPruned` ⇒ 上轮剪过的目录本轮"
     "**强制 readdir+stat 全量核验**(不读内容), idle 轮仍剪枝(保 `DirsPruned >= 1`); 语义变化 = 核验轮 `DirsPruned == 0` 且 "
     "`VerifiedAllDirs == true` **单列**(不冒充「无变化」)。真读数: `agent.recall.tests` **12/13 → 14/14**(新增「等字节长度改写」回归用例, "
     "size 不变只有文件 mtime 变), 0 failed / 0 skipped; 修前 1 红(改写态 `Modified==0`)。"
     ),
    ("evidence_cmd", "python3 eval/recall/r481/check_r481d9.py"),
    ("evidence_path", "eval/recall/r481/verdict-r481d9.json"),
    ("negative_control",
     "变异测试(判据必须对注入缺陷翻红, 否则判据恒绿): **NC1** 剪枝门 `!prevScanPruned` 反转 ⇒ C1 红; **NC2** 删 stamp 左移编码 ⇒ C1 红; "
     "**NC3** 删读侧标志位解码 ⇒ C1 红(3/3 实测全部翻红); 正向面 C1 源码派生(读/写两侧成对, 缺一即红) + C2 真跑读数(trx 结果行数 > 0, "
     "0 行 ⇒ 假绿判红) + C3 核验轮语义锁存(`Assert.Equal(0, DirsPruned)` / `VerifiedAllDirs`) —— **不含**: 旧格式 store 的实读行为"
     "(仅推理: ticks 量级 LEB128 恒 9 B ⇒ 左移前后字节数不变 ⇒ 旧值被读成更早 stamp ⇒ 只多核验不误剪; 未实测), 亦不含内容级哈希兜底 "
     "(`VerifyMode.Hash` / 周期全量核验, 当前未实现)。"),
    ("covers", [
        "src/agent.recall/RecallFingerprint.cs",
        "src/agent.recall/RecallUpdater.cs",
        "src/agent.recall.tests/RecallModuleTests.cs",
        "eval/recall/r481/check_r481d9.py",
    ]),
    ("owner_round", ROUND),
])

BULLET_D = (
    "- **R481-D（本轮，D9 收口）**：`agent.recall.tests` **12/13 → 14/14**（Failed 0 / Skipped 0 / trx 结果行 14）。"
    "根因(承 R481-C 定位)：目录剪枝条件 `dir.mtime <= 上次 stamp` 对**纯内容改写**不可见(改写文件不改父目录 mtime) ⇒ 整目录被剪 ⇒ "
    "文件级 `(size, mtime)` 比对根本没发生。修法 = **交替核验**：指纹头 stamp 低位记「上轮是否剪枝」，上轮剪过的目录本轮**强制核验**"
    "(readdir + stat，不读内容)，idle 轮仍剪枝；纯内容改写最多滞后 1 轮被捕获。语义变化单列：核验轮 `DirsPruned == 0` ∧ "
    "`VerifiedAllDirs == true`(不冒充「无变化」)。新增回归用例刻意用**等字节长度**改写(size 不变) ⇒ 逼出「文件级比对必须真的发生」，"
    "并锁「核验轮 DirsPruned 恒 0」「下一轮恢复剪枝」两条。器具 `eval/recall/r481/check_r481d9.py` 判 `verdict=PASS`："
    "C1 源码派生(读写契约成对) + C2 真跑读数(trx 14 行) + C3 语义锁存 + 变异负控 **3/3**(NC1 反转剪枝门 / NC2 删 stamp 左移 / "
    "NC3 删标志位解码 ⇒ 全部翻红)。\n"
)

BASE_LINE_OLD_START = "- **基线**：`agent.recall.tests` **Failed 1 / Passed 12 / Total 13**"
BASE_LINE_NEW = (
    "- **基线(修后)**：`agent.recall.tests` **Failed 0 / Passed 14 / Total 14**（rc=0，`Duration 949 ms`，`Skipped 0`；R481-C 前为 "
    "**Failed 1 / Passed 12 / Total 13**）；库 `dotnet build src/agent.recall -c Release` = `0 warning / 0 error`。\n"
)

NEXT_OLD_START = "- **下轮候选**：① 实施 D9 交替核验 ⇒ **13/13**（默认先做）"
NEXT_NEW = (
    "- **下轮候选**：① 内容级哈希兜底（`VerifyMode.Hash` 或周期全量核验：D9 只保证「最多滞后 1 轮」，**不保证**任意改写当轮可见）"
    "② 相对地址按引用方目录解析 ⇒ G3 0.2718↑、G1 ≥0.90 ③ 判据锁进 `prereg_r481a.json` ④ 1e5 规模臂 ⑤ R479 遗留"
    "（路由器接线 / 入链 prompt 正文槽位化）—— 注意：recall 模块**尚未入链**，R413 主线「用户一轮 tasks tokens −30%」"
    "在本面无贡献（本面只做模块正确性收口，不冒充主线 KPI）。\n"
)

MP_SECTION_NEW_BODY = [
    "- 状态: **D9 面已验收**（`agent.recall.tests` **14/14**，rc=0，trx 结果行 14，Failed 0 / Skipped 0）",
    "- 权威计划: `docs/plans/v0.97.0-r481-consolidation.md`；缺陷与证据台账: `docs/reports/r480-recall-test-ledger.md`",
    "- 本机实跑读数（2026-09-16）: 测试 **2/13 → 12/13 → 14/14**；`OutOfMemoryException` **16 → 0**；用例耗时 **2m12s → 391 ms → 949 ms**（多 1 用例）；`agent.recall` 库 **rc=0 / 0 warning / 0 error**",
    "- 已修 7 处真根因（F1–F7）+ 本轮 **D9**（交替核验：stamp 低位记「上轮剪枝」⇒ 核验轮强制 readdir+stat；核验轮 `DirsPruned == 0` 单列 `VerifiedAllDirs`），**全为读写契约/缓存可见性错误，无一处改断言凑绿**",
    "- 证据器具: `python3 eval/recall/r481/check_r481d9.py` ⇒ `verdict=PASS`（C1 源码派生 / C2 真跑 trx 14 行 / C3 语义锁存 / 变异负控 3/3 翻红）；`eval/recall/r481/verdict-r481d9.json`",
    "- 【探索】判据基线（R481-A，Python 代理面）: 解析率 **0.8508**（目标 ≥0.90 ❌）/ 悬空 **0.1492**（✅ ≤0.35）/ 相对引用落地 **0.2718 = 309 条**（❌）/ 地址覆盖 **p50=0、76.11% 零地址**（❌）/ 跨 URL **2,720 = unreported**",
    "- 诚实边界: `agent.recall` 尚未并入 `agent.host`（本面无 AOT 重发布验证）；recall **未入链** ⇒ 对 R413 主线「tokens −30%」**本轮无贡献**（不冒充）；旧格式 store 兼容**只推理未实测**；内容级哈希兜底**未实现**（D9 只保证最多滞后 1 轮）；全程未 push（`PUSH_PAUSED`）",
    "- 下轮候选: ① `VerifyMode.Hash` / 周期全量核验兜底 ② 相对地址按引用方目录解析 ⇒ G3↑ ③ G2 四条判据锁进 `prereg_r481a.json` ④ 1e5 规模臂 ⑤ R479 遗留（路由器接线 / 入链 prompt 正文槽位化）",
]


def main():
    reg_raw = io.open(R, encoding="utf-8", newline="").read()
    doc = json.loads(reg_raw, object_pairs_hook=collections.OrderedDict)
    ser = json.dumps(doc, indent=1, ensure_ascii=False)
    repair = 0
    if ser + "\n" == reg_raw:
        print("SER_ASSERT=OK (indent=1, ensure_ascii=False, 尾换行)")
    elif ser == reg_raw:
        # 现场漂移: 现盘文件缺尾换行 ⇒ bind_evidence.py --apply 的同一断言会 FAIL(器具有主地拒绝写)。
        # 以其自身序列化器契约为准补 1 B (只补尾换行, 不动任何 JSON 内容), 使两个写者口径一致。
        repair = 1
        print("SER_ASSERT=REPAIR_TRAILING_NEWLINE (现盘缺尾换行; 非 JSON 内容差异, 只补 1 B)")
    else:
        print("SER_ASSERT=FAIL 序列化器未能逐字节复现原文件 (禁改写)")
        return 3
    rows = doc["rows"]
    row_added = 0
    if all(r.get("id") != ROW["id"] for r in rows):
        rows.append(ROW)
        row_added = 1
    doc["updated_round"] = ROUND

    # ---- improvements.md 定点替换 (锚缺失即 MISS 退出, 不做部分写入) ----
    imp = io.open(I, encoding="utf-8").read()
    anchors = {
        "status": "## v0.97.0 · R481 · 2026-09-16 · 状态: 进行中（测试面 12/13，不认通过）",
        "base": BASE_LINE_OLD_START,
        "next": NEXT_OLD_START,
        "c": "- **R481-C（本轮，测试面收口）**",
    }
    miss = [k for k, v in anchors.items() if v not in imp]
    if miss:
        print("MISS anchors in improvements.md: %s" % miss)
        return 2
    new_imp = imp
    if "R481-D" not in imp:
        # ① 状态行
        new_imp = new_imp.replace(anchors["status"],
                                  "## v0.97.0 · R481 · 2026-09-16 · 状态: 进行中（D9 已验收：测试面 14/14；【探索】G1/G3/G4 未达）", 1)
        # ② R481-C 条之后插 R481-D
        i = new_imp.index(anchors["c"])
        j = new_imp.index("\n", i) + 1
        new_imp = new_imp[:j] + BULLET_D + new_imp[j:]
        # ③ 基线条
        i = new_imp.index(BASE_LINE_OLD_START)
        j = new_imp.index("\n", i) + 1
        new_imp = new_imp[:i] + BASE_LINE_NEW + new_imp[j:]
        # ④ 下轮候选条
        i = new_imp.index(NEXT_OLD_START)
        j = new_imp.index("\n", i) + 1
        new_imp = new_imp[:i] + NEXT_NEW + new_imp[j:]

    # ---- master plan: R481 基线段正文刷新 + 索引增量段 ----
    mp = io.open(MP, encoding="utf-8").read()
    hdr = "## R481（2026-09-16）recall 模块收口 — 当前基线（承焦点令 A/B/C）"
    if hdr not in mp:
        print("MISS master-plan R481 section")
        return 2
    lines = mp.splitlines(keepends=True)
    i_hdr = next(i for i, l in enumerate(lines) if l.startswith(hdr))
    # 旧正文 = 标题之后直到下一个 "## " 段头 (或 EOF) —— 必须**替换**而非插入, 否则旧基线整段残留 (本轮实测踩过)
    i_end = i_hdr + 1
    while i_end < len(lines) and not lines[i_end].startswith("## "):
        i_end += 1
    body_new = "\n" + "\n".join(MP_SECTION_NEW_BODY) + "\n"
    out = lines[:i_hdr + 1] + [body_new] + lines[i_end:]

    idx_txt = subprocess.run(["python3", IDX, ROUND], cwd=ROOT, capture_output=True, text=True)
    if idx_txt.returncode != 0 or not idx_txt.stdout.strip():
        print("MISS index tool output (rc=%d) —— 不猜, 判红" % idx_txt.returncode)
        return 2
    mp2 = "".join(out)
    sec = ("\n## R481 轮次索引增量（2026-09-16 机取自 `docs/verification-registry.json`，勿手改）\n\n"
           "器具: `python3 eval/tools/master_plan_round_index.py R481`（只读 JSON，输出可直接粘的 Markdown 行）。\n\n"
           "| 轮号 | id | level | 能力摘要 |\n|---|---|---|---|\n" + idx_txt.stdout.rstrip("\n") + "\n\n"
           "> 取代关系: 本增量取代上方各段「轮次索引」的 row 数口径（149 → %d，最新轮号 R479 → R481）。旧段正文保留为历史读数。\n" % len(rows))
    if "## R481 轮次索引增量" not in mp2:
        mp2 = mp2.rstrip("\n") + "\n" + sec

    reg_out = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    if reg_out != reg_raw:
        io.open(R, "w", encoding="utf-8", newline="\n").write(reg_out)
        back = io.open(R, encoding="utf-8", newline="").read()
        print("REG_WRITE_READBACK=%s" % ("OK" if back == reg_out else "MISMATCH"))
    else:
        print("REG_IDEMPOTENT=OK")
    if new_imp != imp:
        io.open(I, "w", encoding="utf-8", newline="\n").write(new_imp)
        print("IMP_READBACK=%s" % ("OK" if io.open(I, encoding="utf-8").read() == new_imp else "MISMATCH"))
    else:
        print("IMP_IDEMPOTENT=OK")
    if mp2 != mp:
        io.open(MP, "w", encoding="utf-8", newline="\n").write(mp2)
        print("MP_READBACK=%s" % ("OK" if io.open(MP, encoding="utf-8").read() == mp2 else "MISMATCH"))
    else:
        print("MP_IDEMPOTENT=OK")

    print(json.dumps({"registry_rows": len(rows), "row_added": row_added,
                      "trailing_newline_repaired": repair,
                      "updated_round": doc["updated_round"]}, ensure_ascii=False))
    print(subprocess.run(["git", "diff", "--numstat", "docs/verification-registry.json",
                          "docs/improvements.md", "docs/reports/iteration-master-plan.md"],
                         cwd=ROOT, capture_output=True, text=True).stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
