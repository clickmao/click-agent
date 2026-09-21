#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R623 登记行追加件（幂等 + 序列化逐字节复现断言 + 写后读回）。

纪律（承「登记表程序化改写」铁律 R409）：
  ① 改写前断言 `json.dumps(doc, indent=1, ensure_ascii=False)+tail == 原文件字节`，不符即拒写；
  ② 只追加一行到 rows 末尾，不重排、不动既有行；
  ③ 幂等（重跑不重复插入）；
  ④ 写后读回复核（含新增行 id 与 pin 字段）。
用法: python3 eval/rover/r623/registry_append_r623.py [--apply]
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
REG = ROOT / 'docs/verification-registry.json'
REPORT = 'eval/rover/r623/report-r623.md'
INSTR = 'eval/rover/r623/closeout_r623.py'
ROW_ID = 'r623.rerank-four-metrics'


def sha12(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:12]


CAPABILITY = (
    "RF0005 §0 DoD **面 4 · 上下文精排**：把四项指标（NDCG@k / MRR / Precision@k / Recall@N）从「未测」推进为「有读数」，并在**产品真身**"
    "召回路径（`RAGRecall.RecallAsync` → `ApplyRerank`）上取数。口径：唯一单变量轴 = `RAGConfig.RerankEnabled`（T=精排开 / C=轴关=旧行为）；"
    "形态 = 生产 DI（`Fusion{Enabled=true,K0=10,DenseWeight=1.0,LexicalWeight=1.0}`，`ServiceCollectionExtensions.cs:240`）；"
    "测量池 K=50（代码事实：精排在 `Take(TopK)` **之后**执行 ⇒ 池尺寸 = 精排可重排空间）；冻结件 = `eval/bge/fixtures`（语料 1299 篇 sha12 fa7c448c505d / "
    "查询 120 条 sha12 b37fbe564e23，单 gold 分级，**零新增夹具**）。**读数**（聚合域 = Recall@N==1 的 90/120 查询）："
    "C 与 T 的 NDCG@10 中位同为 0.5000（63/90 并列 ⇒ 中位被钳制）；MRR 均值 C 0.4772 → T **0.4929**；**逐查询配对 27 升 / 0 降 / 63 平（零回归）**；"
    "Recall@N = **0.75**（前置天花板：精排只重排不补召回）；生效遥测 T `RerankApplied` **120/120**、C 恒 0、错位查询 120/120 ⇒ **非孤岛**；池集合逐条相同 120/120。"
    "**DoD 阈值对照（不下调）**：NDCG@k ≥0.8 ✗ · MRR ≥0.6 ✗ · P@k ≥0.8 ✗（单 gold ⇒ 上界 = 1/k，k≥2 **结构性不可达**）· R@N =1.0 ✗。"
    "**两侧控制**：NEG 退化打分器中位 NDCG@10 = 0.0000 ≤ C+0.02（有牙）· POS oracle 置顶 = 1.0000（度量敏感）。"
    "**未测**：tokens（调用数 / 新算 prompt / completion）与缓存命中率（本面零远端 / 零 LLM）。"
)


def build_row():
    return {
        'id': ROW_ID,
        'round': 'R623',
        'owner_round': 'R623',
        'level': 'L2',
        'evidence_generated_with': {
            'evidence_kind': 'artifact',
            'pin_status': 'frozen',
            'pin_reason': 'archived-per-round',
            'artifact_sha12': sha12(REPORT),
            'instrument': INSTR,
            'instrument_sha12': sha12(INSTR),
            'binding': 'audit-pin',
            'audited_by_round': 'R623',
        },
        'capability': CAPABILITY,
        'evidence_path': REPORT,
        'evidence_cmd': (
            'bash eval/rover/r623/repro-r623.sh && '
            'python3 eval/rover/r623/closeout_r623.py && '
            'python3 eval/capability/status_gen.py --check'
        ),
        'negative_control': (
            '① **轴关臂 = 旧行为**：C 臂 `RerankApplied` 必须恒 0（实测 0/120），且 T/C 共用同一召回池（池集合逐条相同 120/120）⇒ 差异只可能来自精排段；'
            '② **退化打分器 NEG**（`-coarseScore`，stage 层同池重排）必须不优于 C（实测中位 NDCG@10 0.0000 ≤ 0.5+0.02；MRR 均值 0.0278）⇒ 判据对「坏精排」有牙；'
            '③ **oracle 置顶打分器 POS** 必须近满分（实测中位 NDCG@1/@5/@10 = 1.0）⇒ 度量对「把 gold 置顶」敏感，非恒真门；'
            '④ **确定性 ∧ 非平凡成对**：同二进制 `--no-build` 复跑 n=3，payload（去 `ts`）逐字节同一（sha12 9272c0b6da2d）∧ 跨臂读数互异；'
            '⑤ **两处器具缺陷原样入档不翻案**：v1（legacy 形态 × 池 10 ⇒ R@N==1 仅 22/120 ⇒ 触发预注册证伪条目② rc=3 不可判）与 '
            'v2a（池同一性判据写成「id 序列逐位相同」⇒ 与「精排就是重排序」的轴语义自相矛盾，0/120 恒红）⇒ 修正形态（集合相同）单列 checks_posthoc；'
            '证据 `eval/rover/r623/out-v1-legacy-k10/run-v1-console.txt` / `rerank-face-readings-v2a-poolseqbug.json`。'
        ),
        'covers': [
            'rerank-four',
            'src/agent.tests/RerankFaceTests.cs',
            'eval/rover/r623/report-r623.md',
            'eval/capability/baselines.json',
        ],
        'runs': 3,
        'verdict': ('面 4 = **有读数（未达标）** · 精排段接线通且真机生效 · 相对轴关臂零回归（27↑/0↓/63=）· MRR 均值 +0.0157（+3.3% rel）· '
                    'rc=0（仅表本轮判据全绿）· 零产品源码改动 ⇒ 无降幅可宣称 · 禁下调阈值 / 禁改 K 凑数'),
        'aot': ('未跑。本面为**组件级 JIT 测试路径**读数（xUnit 驱动产品真身召回路径 + 冻结语料）⇒ 证据阶梯按实定级 **L2**，不升级；'
                'AOT/CLI E2E 未行使（该组件未接 CLI 直通路径）⇒ 不得据此宣称「发布形态已验收」。'),
    }


def repin(apply):
    """重钉：把该行的 artifact_sha12 / instrument_sha12 重取为现盘值（写前仍断言序列化逐字节复现）。

    用途 = 证据文档在本轮内**再次**修订（如补 §2.1 探针 / §5 门禁读数）后，pin 必须跟到新字节。
    纪律：重钉只在**同一轮内**、且报告只做**增量**（旧读数不撤）时允许；跨轮改动证据必须另立轮号。
    """
    raw = REG.read_text(encoding='utf-8')
    doc = json.loads(raw)
    ser = json.dumps(doc, indent=1, ensure_ascii=False)
    tail = '\n' if raw.endswith('\n') else ''
    if ser + tail != raw:
        print('SER_ASSERT=FAIL registry 序列化器未逐字节复现 ⇒ 拒写 (fail-closed)')
        return 3
    row = next((r for r in doc['rows'] if r.get('id') == ROW_ID), None)
    if row is None:
        print('REPIN=FAIL 无 %s 行' % ROW_ID)
        return 2
    g = row['evidence_generated_with']
    new = {'artifact_sha12': sha12(REPORT), 'instrument_sha12': sha12(INSTR)}
    old = {k: g.get(k) for k in new}
    if old == new:
        print('REPIN=noop old=%s' % json.dumps(old, ensure_ascii=False))
        return 0
    print('REPIN old=%s new=%s' % (json.dumps(old, ensure_ascii=False), json.dumps(new, ensure_ascii=False)))
    if not apply:
        print('REPIN=dry-run')
        return 0
    g.update(new)
    REG.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    back = json.loads(REG.read_text(encoding='utf-8'))
    r2 = next(r for r in back['rows'] if r.get('id') == ROW_ID)['evidence_generated_with']
    print('REPIN=ok readback artifact_sha12=%s(instrument %s)' % (r2['artifact_sha12'], r2['instrument_sha12']))
    return 0


def main():
    apply = '--apply' in sys.argv
    if '--repin' in sys.argv:
        return repin(apply)
    raw = REG.read_text(encoding='utf-8')
    doc = json.loads(raw)
    ser = json.dumps(doc, indent=1, ensure_ascii=False)
    tail = '\n' if raw.endswith('\n') else ''
    if ser + tail != raw:
        print('SER_ASSERT=FAIL registry 序列化器未逐字节复现 ⇒ 拒写 (fail-closed)')
        return 3
    ids = [r.get('id') for r in doc['rows']]
    if ROW_ID in ids:
        cur = doc['rows'][ids.index(ROW_ID)]
        print('REGISTRY_EXISTS=1 id=%s' % ROW_ID)
        print('  artifact_sha12=%s(disk %s) instrument_sha12=%s(disk %s)'
              % (cur['evidence_generated_with']['artifact_sha12'], sha12(REPORT),
                 cur['evidence_generated_with']['instrument_sha12'], sha12(INSTR)))
        return 0
    row = build_row()
    if not apply:
        print('REGISTRY_APPEND=dry-run id=%s level=%s artifact_sha12=%s instrument_sha12=%s'
              % (ROW_ID, row['level'], row['evidence_generated_with']['artifact_sha12'],
                 row['evidence_generated_with']['instrument_sha12']))
        return 0
    doc['rows'].append(row)
    doc['updated_round'] = 'R623'
    REG.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    back = json.loads(REG.read_text(encoding='utf-8'))
    got = [r for r in back['rows'] if r.get('id') == ROW_ID]
    print('REGISTRY_APPEND=ok rows=%d readback=%d updated_round=%s'
          % (len(back['rows']), len(got), back.get('updated_round')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
