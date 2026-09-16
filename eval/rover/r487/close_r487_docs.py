#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R487 文档收口: 主计划轮次索引增量(**机取自 registry, 禁手改**) + improvements.md 本轮条目。
幂等: 目标文件已含 'R487' 段则跳过; 保形: 追加而非重写, 结尾换行齐备。
"""
import os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
MP = os.path.join(ROOT, "docs/reports/iteration-master-plan.md")
IMP = os.path.join(ROOT, "docs/improvements.md")

MP_SEC = """## R487（2026-09-16）真机三臂隔离微闸 — **主 KPI 判负**，闸效应首次真机读数 −20.6%

- 靶点：R413 验收②③（用户一轮任务总 token 降 ≥30% / r1 对管道有可测增益）；R485 只交付器具未跑真机臂。
- 设计（为什么是三臂）：微闸接线在 `src/agent/IndustrialAgentV2.cs` **两臂均无条件** ⇒ 闸开/闸关两臂**结构上无法隔离**该闸；
  改用 **同臂参只换二进制**的差分：`A0`(r479v2 `6a9b7aed22a22f48…`) vs `Arole485`(r485 `03c77d56e8c485af…`) = 微闸单独效应；
  `R485` = 新二进制 + `turn_gate=on` + `repeat_skip=on`（生产 R 形态）。
- 真跑：`bash eval/rover/r487/run_both_r487.sh` ⇒ **rc=0 / ALLDONE 11:29:51**，三臂各 12 轮（本地中继 → 真供应商）。
- 读数（供应商 usage 真值列）：A0 **22 调用 / 80,302 tok**；Arole485 **15 / 63,825**；R485 **14 / 81,770**。
- **主 KPI：FAIL**（A0→R485 = **+1.83%**，不降反升）；H3 配对方向 FAIL（Arole485→R485 **+28.1%**）；H4 质量 FAIL（R485 实质轮 6/12）。
- **post-hoc 正读数（预注册未点名，单列）**：A0→Arole485 = 调用 **−31.8%** / token **−20.6%** / 质量 12/12 未降
  ⇒ **微闸确有可测增益，但 < 30%**；`micro_step_skipped`：A0 **0** / Arole485 **4** / R485 **2** ⇒ H1 PASS（闸在管道内活着）。
- 归因（算术可验）：R485 每次调用 prompt **5,540** vs Arole485 **4,071**（+36%），调用数只少 1 ⇒ 总 token 上升；
  与 skip 类答复 6/12（模板 4 + 复述回放 2，t9「从头说」逐字等于 t8）同时出现。**未做因果分离实验**（两开关同时改动）⇒ 只报相关。
- H0 锚 **FAIL**（A0=22 调用 vs R482 锚 21 / 72,634 tok）⇒ 上游在飞漂移，本轮**不与 R482 相减**，只用同刻差分。
- 器具收口：④ `blocker_cause` **多因并列** + 三态差分负控（C1 rc=0 / C2 [内存不足] / C3 [内存不足, build-server 残留]）；
  ⑦ `run_arm/run_both` **机派生** 28 条替换逐条计数断言 + 起手闸**单一源**（`grep -c 2650` = 0）⇒ H6/H7 PASS。
- ⑥ R481-G 遗留：`eval/recall/r487/band_probe_r487.py` ⇒ markdown **0.8125**（阈值 0.90，与已注册 R481-B 器具**同值**）/
  explicit_rel **0.0913**（0.85）/ root_rel **1.0**（PASS）/ slash_token 58,155；守恒式 True；负控 `--nc-blind` 1.0→0.0；
  语料清单导出（6882 文件 / `files_sha16=3da4c878e2b160bb`，与 R481-B 6658 文件**不可比**）。
- 诚实边界：单夹具单次（n=12，无置信区间）；`turn_gate` 与 `repeat_skip` 混淆未分离；③（对侧 R486 承接）/⑤（会换被测二进制）未做；
  自检出器具缺陷：relay/prov 命名未并入 TAG（本轮三臂 ARM token 互不相同 ⇒ 无覆盖，列为遗留）；未 push；未跑全量回归。
- registry：本轮 +3 行（`updated_round=R487`）。

"""

IMP_SEC = """## R487（2026-09-16）真机三臂隔离微闸 — 主 KPI 判负；闸效应首次真机读数 −20.6%

- 靶点：R413 验收②③；R485 只交付器具未跑真机臂，R486 巡检发现微闸**两臂均无条件** ⇒ 两臂设计无法隔离。
- 设计：**同臂参只换二进制** = 微闸单独效应（`A0` r479v2 vs `Arole485` r485），另加 `R485`（新二进制 + `turn_gate` + `repeat_skip`）做生产形态对照。
- 真跑（rc=0 / ALLDONE 11:29:51，三臂各 12 轮，本地中继 → 真供应商）：A0 **22 调用 / 80,302 tok**；Arole485 **15 / 63,825**；R485 **14 / 81,770**。
- 判据：**H2 主 KPI FAIL**（A0→R485 **+1.83%**）· H3 FAIL（Arole485→R485 **+28.1%**）· H4 FAIL（R485 实质轮 6/12；模板 4 + 复述回放 2）· H0 锚 FAIL（22 vs 21）· H1 **PASS**（`micro_step_skipped` 0/4/2）· H5/H6/H7 **PASS**。
- **正读数（post-hoc 单列）**：A0→Arole485（臂参逐字同、只换二进制）= 调用 **−31.8%** / token **−20.6%** / 质量 12/12 未降 ⇒ 闸确有增益但**未达 30%**。
- 归因：R485 每调用 prompt 5,540 vs Arole485 4,071（+36%）而调用只少 1 ⇒ 剩余调用上下文变长；与 6/12 skip 类答复同时出现。**两开关同时改动 ⇒ 未做因果分离**。
- 器具：④ `blocker_cause` 多因并列 + 差分负控三态；⑦ 臂执行器**机派生**（28 条替换逐条计数）+ 起手闸单一源（手抄常数 0）；⑥ 分档器具 + 语料清单（markdown 0.8125 与注册器具同值；守恒式可机检；负控翻面）。
- 器具缺陷（自检，不掩盖）：臂调 relay/prov 未传 TAG ⇒ 真值列落 `usage-<ARM>.jsonl`、臂自身 `$USAGE` 恒 0 字节；本轮三臂 token 互异 ⇒ 无污染，遗留下一轮修。
- 诚实边界：单夹具 n=12 无置信区间；H0 锚未复现（不与 R482 相减）；③（对侧承接）/⑤（会换被测二进制）未做；未 push；未跑全量回归。
- 下轮候选：① **消融 `repeat_skip` / `turn_gate`**（分离「吃掉收益」的开关）② **上下文剪裁 / 前缀复用**（把 −20.6% 推向 ≥30%）③ skip 类答复不得冒充实质答（复用须显式声明）④ relay/prov 命名并入 TAG ⑤ R479 遗留（路由器接线 / prompt 正文槽位化；须在不跑真机臂窗口做 + AOT 重发布）⑥ ③空正文基数与对侧 R486 读数合并 ⑦ H0 锚漂移纪律（锚不达线 ⇒ 只做同刻差分并标注不可比）

"""

idx = subprocess.run([sys.executable, os.path.join(ROOT, "eval/tools/master_plan_round_index.py"), "R487"],
                     capture_output=True, text=True, cwd=ROOT)
if idx.returncode != 0:
    print("MISS(index-tool) rc=%s %s" % (idx.returncode, idx.stderr[:200])); sys.exit(3)
lines = [l for l in idx.stdout.strip().split("\n") if l.strip()]
rows = [l for l in lines if l.startswith("| R487 ")]
cov = [l for l in lines if l.startswith("覆盖自检") or l.startswith("**缺登记行轮号")]
if len(rows) != 3 or not cov:
    print("MISS(index-shape) rows=%d cov=%d" % (len(rows), len(cov))); sys.exit(3)

mp_add = MP_SEC + "### R487 · 轮次索引增量（机取自 `docs/verification-registry.json`，禁手改）\n\n" + \
         "\n".join(rows) + "\n\n" + "\n".join(cov) + "\n\n"

done = []
for path, sec, tag in ((MP, mp_add, "master-plan"), (IMP, IMP_SEC, "improvements")):
    txt = open(path, encoding="utf-8").read()
    if "R487" in txt:
        print("skip(%s): 已含 R487" % tag); continue
    if not txt.endswith("\n"):
        txt += "\n"
    txt += "\n" + sec
    open(path, "w", encoding="utf-8").write(txt)
    done.append(tag)

print("WROTE:", done, "| index rows:", len(rows))
print("|".join(cov))
