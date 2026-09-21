#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R625 收口 · 文档面追加（§7 轮块 + improvements 条目）——只追加，不重排、不补写历史轮。
用法: python3 eval/rover/r625/closeout_docs_r625.py [--apply]"""
import io
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
PLAN = ROOT / 'docs/reports/iteration-master-plan.md'
IMP = ROOT / 'docs/improvements.md'
MARK = '- **R625（RF0005 §0 DoD 面 4'

BLOCK = MARK + '「上下文精排」的**口径收口轮**（生产池宽 K=10）+ 精排段**成本列首测**；**零产品源码改动 / 零远端调用 / 零 LLM / 零新增夹具语义**）**: 换杆依据 = 前提机检 F1/F2（内嵌于判据器 P0；**代码事实** = 生产 RAG 召回 `TopK = 10` —— `src/agent/contextassembler/ContextAssembler.Recall.cs:216` ∧ `src/agent.rag/RAGConfig.cs:15 MaxRecallResults = 10` ∧ `src/agent.rag/RAGRecall.cs:448` Take(`TopK>0?TopK:MaxRecallResults`)；精排在 `:498` 执行 ⇒ **池尺寸 = 精排可重排空间**）⇒ R623/R624 的读数取自**测量池 K=50**（产品不使用的档）⇒ 本轮把口径对齐生产档。**唯一单变量轴 = 召回池宽 K**（口径轴，非产品开关；K=10 = 生产口径 / K=50 = R623–R624 测量口径）；形态 = fusion ∧ `embed=vec`（生产 DI，承 R624）；冻结件 = `eval/bge/fixtures`（语料 1299 sha12 `fa7c448c505d` / 查询 120 sha12 `b37fbe564e23`，单 gold）；臂 = `{hash,vec}×{10,50}` + `zero×10`（负控），`--no-build` 同二进制串行。**读数**：`R@N` 生产档 **B10 0.7333（gated 88/120）** vs 旧测量档 **B50 0.8083（gated 97）** · 兜底形态 A10 0.6333（76）/ A50 0.7500（90）· 零向量负控 Z10 0.5417；`pool_len_median` K=10 **10** vs K=50 **48**（口径生效）。**DoD 四值（生产口径，阈值零下调）**：NDCG@10 中位 **1.0000** ✓ / MRR 中位 **1.0000** ✓ / P@10 中位 **0.1000** ✗ / `R@N` **0.7333** ✗ ⇒ 名义 **2/4**；**饱和声明（禁读作能力达标）** = K=10 时**池宽恰等于 k** ⇒ 单 gold 下 NDCG@10 与 MRR **分辨率失效**（任一「gold 置顶」排序即 1.0；K=50 时池 49 ≫ k=10 故中位被 63/90 并列钳制在 0.5），真正有分辨率的两项 —— P@10（上界 = 1/k = 0.1 ⇒ ≥0.8 **算术不可达**）与 `R@N`（0.7333 < 1.0）—— **双双未达**。**成本列首测（信息项，R410 不入红绿）**：精排段配对耗时中位 **K=10 69.0 µs vs K=50 1,942.7 µs（≈28×）**（p90 1,484.7 / 4,904.7；同进程 `Stopwatch`，单位入字段名）+ 装配面候选集合字符和 **498,318 vs 2,420,739（≈4.9×）**（声明估算器 `chars/3` ⇒ ≈166k / 807k tok，**非真 token**：本面零远端）；**`candidates_scored`（粗排面计数）跨池宽恒等 233,040 ⇒ 显式判为「非精排成本代理」**（防按字段名读成本的空心结论）。**零回归（决定性）**：A50/B50 对 R624 件 `A1`/`B1` 的 `per_query` membership 集 **逐位差异 0** ∧ gated 90/97 同值 ∧ `pool_len_median` 48/49 同值 ⇒ 本轮器具改动（**只加成本列信息字段**）未动判据路径 ⇒ R623/R624 既有 pin **不失效、无需重钉**。**两侧控制（判别力自证）**：NEG 零向量臂 R@N 0.5417 ≤ 兜底 0.6333 ∧ membership 差 **13** 条（有牙）；**守恒**：A10 未召回 44 条五桶合计 **44**（仅池宽 4 · 仅形态 3 · 任一路线 10 · 两者皆需 5 · **结构性不可召回 22**）。**预注册证伪条目**：`R@N(K=10) ≥ R@N(K=50)` ⇒ **未命中**（0.7333 < 0.8083）⇒ 「池宽是召回面可回收来源」假设**未被证伪**（与 R623 K=50→200 +5.83 pt 同向）。**文献小步**：3 检索式（arXiv）+ 1 摘要取件；**采信 1 条** = arXiv **2505.14432v1**（cs.IR/cs.CL，comment「15 pages, 4 figures」、**无 journal-ref ⇒ 纯预印本，权威代理最低档**；逐字引文「retrieve-and-rerank … by reducing the number of comparisons」）⇒ 机制假设「首级检索池**宽度**是慢而准重排器在查询时的**成本/效果旋钮**」**与本仓代码事实同向**且由本轮读数支承（池宽 +40 ⇒ 质量 +7.5 pt ∧ 精排段耗时 ×28）；2 式 0 结果 ⇒ 记「未取到原文、不采信」；`cited_by_count` 无 key ⇒ **不可用，不编造**；连续 0 采信计数**归零** ⇒ 检索不降频。台账 = `docs/research/lit-review-ledger.md` §22。**门禁**：`roundcheck preflight --round R625 --min-avail-mb 2769` **rc=0**（起手清 VBCSCompiler/MSBuild/pyright）· 形式门禁 **14/14** · `status_gen.py --check` **PASS（违规 0 / 基准漂移 0 / 缺源 0）** · 判据器 `defects=[]`（rc=1 = 器具可用但**主判据未达标**）· 新增基准 `rerank-production-caliber` + registry 行 `r625.rerank-production-caliber`（L2）+ kpi 行（带 `baselines` 3 条）。**自捕 1 件（流程）**：写 `src/agent.tests/RerankFaceTests.cs` 时工具报「被兄弟 subagent 修改」⇒ 机检 `pgrep`（无在飞执行体）+ `git diff --stat`（19 行全属本轮）⇒ 判**陈旧追踪告警**，非真并发写者。**诚实边界**：① 本面**零远端** ⇒ tokens（调用/新算/completion）与缓存命中率**未测**、不得补记；**codex 外部真值臂本轮未跑**（本地检索面无远端题面）；② `rc=1` ⇒ **面 4 仍未达标**，禁把「名义 2/4」或「K=50 的 0.8083」读作达标；③ 成本列只作信息项（同机墙钟、未做复跑摆动分离）⇒ **不得**宣称收益或损失；④ 单 gold ⇒ `P@k` 上界 = 1/k，分级加厚 = 新增夹具 ⇒ **须用户放行**；⑤ 与 R585–R624 **禁相减、只并列**（K=10 与 K=50 亦只并列）；⑥ 三档终局目标读数（32 ms / 快 50× / −95% / −85~91%）本轮**不动不宣称**。**artifacts**：`src/agent.tests/RerankFaceTests.cs` · `eval/rover/r625/{dag-r625.md,prereg-r625.json,run_r625.sh,judge_r625.py,closeout_r625.py,closeout_docs_r625.py,report-r625.md,verdict-r625.json,out/}` · 台账 `eval/capability/kpi.jsonl`（R625）· registry 行 `r625.rerank-production-caliber` · 基准 `eval/capability/baselines.json#rerank-production-caliber` · 文献 §22。**证据文档形态说明**：与 R614–R623 同处置 —— R 轮次证据面 = 轮报告 `report-r625.md`（registry 行 `artifact_sha12` 钉住，sha12 `5827a587f6da`）+ 本 §7 块 + registry 行 + kpi 行，**不新建 `docs/evidence/R625/`**。\n' + \
    '- **下轮候选 (R626)**: ① **面 4 达标路径（召回面为主）**（`R@N` 生产档 **0.7333** → 目标 ≥0.9）：须**先只读定位 88/120 之外的 32 例**（K=10 池内无 gold ⇒ 精排无权越池）—— 分层 = 粗排融合位 vs 召回族本身；**可用的零产品改动臂** = 池宽档（K=10/50/200 三档已各有读数）⇒ 判据 = 逐例四分 + 独立 oracle + 「结构性不可召回 22 例」单列（禁混入可回收缺额）② **分级加厚**（单 gold ⇒ `P@10` 结构性不可达；新增夹具分级 ⇒ **须用户放行**）③ **精排器升级位**（`IRerankScorer` 换交叉编码器 / 本地结构化打分；`src/` 改动 ⇒ **未放行不动**，动前须先写「改哪一格读数」= 本面 NDCG@k / MRR + 成本列）④ **成本列的摆动分离**（本轮只作信息项 ⇒ 若要把「池宽成本」升级为判据，须预注册 reps≥3 + 逐窗中位/极差）⑤ **口径面回填**：R624 轮块 §7 未同步（与 R619/R620/R622 同处置，本文件只增量追加、**不补写历史轮**）⇒ **不单独开轮**；⑥ wythoff 族质量缺口（RF0005 §4 并行面）+ 「信息类工具回执 / 序依赖面」（R619 候选，未闭合，随主线推进）。\n'

IMP_ENTRY = '\n'.join([
    '## R625 (2026-09-22) — 面 4「上下文精排」**口径收口轮**（生产池宽 K=10）+ 精排段**成本列首测** · 单变量轴 = 召回池宽 K（K=10 = 生产口径 / K=50 = R623–R624 测量口径；零产品源码改动 / 零远端）',
    ' — 结果: **口径收口完成 · 面 4 仍未达标**（`R@N` 生产档 **0.7333**（gated 88）vs 旧测量档 0.8083（gated 97）⇒ 前两轮读数取自产品不使用的池宽，只作并列对照）',
    ' · **DoD 四值（阈值零下调）名义 2/4**：NDCG@10 / MRR 中位 1.0000 ✓✓（**饱和**：K=10 时池宽 == k ⇒ 单 gold 下分辨率失效，禁读作能力达标）· `P@10` 0.1000 ✗（= 1/k **算术不可达** 0.8）· `R@N` 0.7333 ✗',
    ' · **成本列（信息项）**：精排段配对耗时中位 **69.0 µs（K=10）vs 1,942.7 µs（K=50）≈28×**、装配面字符和 498,318 vs 2,420,739 ≈4.9×、`candidates_scored` 跨池宽恒等 233,040（**显式排除**作精排成本代理）',
    ' · **零回归**：A50/B50 对 R624 `A1`/`B1` per_query membership 差 **0** ⇒ 器具只加信息字段、既有 pin 不失效',
    ' · **判别力**：零向量负控 0.5417 ≤ 兜底 0.6333（差 13 条）· 守恒 44 = 4+3+10+5+22 · 预注册证伪条目**未命中**（R@N K=10 < K=50 ⇒ 池宽假设未被证伪）· rc=1（`defects=[]`）',
    '（轮志: `eval/rover/r625/report-r625.md` · 器具 `eval/rover/r625/` · 基准 `rerank-production-caliber` · 文献 §22）',
    '',
])


def main():
    apply = '--apply' in sys.argv
    if MARK in PLAN.read_text(encoding='utf-8', errors='replace'):
        print('SKIP: §7 R625 块已存在（幂等）')
        return 0
    if apply:
        with io.open(PLAN, 'a', encoding='utf-8') as f:
            f.write(BLOCK)
        with io.open(IMP, 'a', encoding='utf-8') as f:
            f.write(IMP_ENTRY)
    plan2 = PLAN.read_text(encoding='utf-8', errors='replace')
    imp2 = IMP.read_text(encoding='utf-8', errors='replace')
    ok_p = MARK in plan2
    ok_i = '## R625 (2026-09-22)' in imp2
    print('%s plan_block=%s imp_entry=%s plan_lines=%d' % ('APPLY' if apply else 'DRY', ok_p, ok_i,
                                                          len(plan2.splitlines())))
    return 0 if (not apply or (ok_p and ok_i)) else 3


if __name__ == '__main__':
    sys.exit(main())
