#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R624 登记行追加件（幂等 + 序列化逐字节复现断言 + 写后读回）。

纪律（承 R409 / R623）：① 写前断言序列化器逐字节复现原文件，不符拒写；② 只追加一行；③ 幂等；④ 写后读回。
用法: python3 eval/rover/r624/registry_append_r624.py [--apply|--repin]
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
REG = ROOT / 'docs/verification-registry.json'
REPORT = 'eval/rover/r624/report-r624.md'
INSTR = 'eval/rover/r624/closeout_r624.py'
ROW_ID = 'r624.rerank-recall-shape'


def sha12(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:12]


CAPABILITY = (
    "RF0005 §0 DoD **面 4 · 上下文精排 —— 召回面（R@N 前置天花板）** 的**形态对齐**读数：把 R623 的召回面读数从"
    "**兜底形态**（R623 器具未设 `RAGConfig.EmbeddingFunction` ⇒ dense 路走词袋哈希兜底，申报「生产 DI」不成立）"
    "修正为**生产形态**（链上真身 bge-q8.gguf 语义向量 ∧ 按**实现单位 UTF-16 code unit** 切块，"
    "`src/agent.rag/RAGRecall.cs:203-228`），并在同一产品真身召回路径（`RAGRecall.RecallAsync` + fused 粗排）上取数。"
    "口径：唯一单变量轴 = 召回 dense 路的**向量源**（hash 兜底 = R623 现档 / vec 生产 / zero 常量零向量负控）；"
    "池 K 为并列读数轴（50 / 200 / 1299=全语料）；冻结件 = `eval/bge/fixtures`（语料 1299 / 查询 120，单 gold）。"
    "**读数**（R@N = gold 落在被消费召回池内的查询占比）：兜底 K=50 **0.7500**（= R623 件，per_query membership 逐位相同 ⇒ 零回归）· "
    "兜底 K=200 0.8083 · 兜底全池 **0.8833**（14 条结构性缺口）；**生产 K=50 0.8083（+5.83 pt / +7 条 ≥ Δ_min 6）** · "
    "生产 K=200 0.9000 · **生产全池 1.0000（结构性不可召回 0）**；零向量负控 K=50 **0.7417 < 0.7500** 且 membership 有异（有牙）。"
    "**DoD 阈值对照（不下调）**：R@N = 1.0 在**生产形态全池**达成 ✓；预注册主判据（生产形态**同池宽** K=50 ≥ 0.90）**未达标（0.8083）**。"
    "**逐例五分（30 条未召回，守恒）**：仅池宽即可 8 · 任一路线即可 8 · **两者皆需 14** · 仅形态即可 0 · 结构性不可召回 0。"
    "**未测**：tokens（调用数 / 新算 prompt / completion）与缓存命中率（本面零远端 / 零 LLM）；池宽轴**成本未测**（禁当免费收益）。"
)


def build_row():
    return {
        'id': ROW_ID,
        'round': 'R624',
        'owner_round': 'R624',
        'level': 'L2',
        'evidence_generated_with': {
            'evidence_kind': 'artifact',
            'pin_status': 'frozen',
            'pin_reason': 'archived-per-round',
            'artifact_sha12': sha12(REPORT),
            'instrument': INSTR,
            'instrument_sha12': sha12(INSTR),
            'binding': 'audit-pin',
            'audited_by_round': 'R624',
        },
        'capability': CAPABILITY,
        'evidence_path': REPORT,
        'evidence_cmd': (
            'python3 eval/rover/r624/gen_vectors_r624.py && '
            'python3 eval/rover/r624/gen_chunks_r624.py && '
            'python3 eval/rover/r624/g0_v3_gate_r624.py && '
            'bash eval/rover/r624/run_r624.sh && '
            'python3 eval/rover/r624/judge_r624.py && '
            'python3 eval/rover/r624/closeout_r624.py && '
            'python3 eval/capability/status_gen.py --check'
        ),
        'negative_control': (
            '① **负控臂（有牙）**：常量零向量臂 Z1 必须严格更差（实测 R@N 0.7417 < 兜底 0.7500，且 per_query membership 与兜底臂有异）⇒ 判据对向量源敏感；'
            '② **G0 闸自证有牙**：把台账登记的权重 sha 篡改一位 ⇒ C0 同源判据必报 False（`judge_selfcheck.G0_has_teeth = true`）；'
            '③ **P1 自证有牙**：用生产臂 membership 冒充兜底臂 ⇒ 零回归判据必报 False；'
            '④ **形态生效以 miss == 0 表达**（命中 4118 =（1299 文档 + 641 补块）× 2 索引实例；`dim_mismatch_skipped = 0`）⇒ 无静默兜底；'
            '⑤ **键集完整性由「实发文本落盘差分」断言**（默认关的 missdump 闸，实测 `miss_dump_n == 0`）⇒ 源码重建的键集与产品实收输入一致；'
            '⑥ **两处判据缺陷原样入档不翻案**：G0 v1「逐位相等」被机检证明对任何实现都结构性不可满足（同服务自复跑 max|Δ|=1.66e-3）、'
            'G0 v2「min 余弦 ≥ 0.9999」差 1.4e-6 判 FAIL（阈值不下调，降为 checks_posthoc）；P5 v1 四桶字面定义在实测 S⊆P 下构造上不守恒 ⇒ 改五桶（守恒严格）。'
        ),
        'covers': [
            'rerank-recall-shape',
            'rerank-four',
            'src/agent.tests/RerankFaceTests.cs',
            'eval/rover/r624/report-r624.md',
            'eval/capability/baselines.json',
        ],
        'runs': 1,
        'verdict': (
            '面 4 召回面 = **形态对齐完成 · 主判据未达标**（预注册 P3 0.8083 < 0.90，阈值不下调；rc=1）。'
            '形态轴单变量 +5.83 pt（+7 条 ≥ Δ_min 6）∧ 兜底档零回归（membership 逐位相同）⇒ 修正形态本身有可判增益；'
            '**生产形态全池天花板 = 1.0000（结构性不可召回 0）**，兜底形态 0.8833（14 条结构性缺口）'
            '⇒ R623「R@N 结构上不可达 1.0」**只对兜底形态成立**。零产品源码改动 ⇒ 无降幅可宣称；池宽轴成本未测。'
        ),
        'aot': ('未跑。本面为**组件级 JIT 测试路径**读数（xUnit 驱动产品真身召回路径 + 冻结语料）⇒ 证据阶梯按实定级 **L2**，不升级；'
                'AOT/CLI E2E 未行使（该组件未接 CLI 直通路径）⇒ 不得据此宣称「发布形态已验收」。'),
    }


def repin(apply):
    raw = REG.read_text(encoding='utf-8')
    doc = json.loads(raw)
    if json.dumps(doc, indent=1, ensure_ascii=False) + ('\n' if raw.endswith('\n') else '') != raw:
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
        print('REPIN=noop %s' % json.dumps(old, ensure_ascii=False))
        return 0
    print('REPIN old=%s new=%s' % (json.dumps(old, ensure_ascii=False), json.dumps(new, ensure_ascii=False)))
    if not apply:
        print('REPIN=dry-run')
        return 0
    g.update(new)
    REG.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    back = json.loads(REG.read_text(encoding='utf-8'))
    r2 = next(r for r in back['rows'] if r.get('id') == ROW_ID)['evidence_generated_with']
    print('REPIN=ok readback artifact_sha12=%s instrument_sha12=%s' % (r2['artifact_sha12'], r2['instrument_sha12']))
    return 0


def main():
    apply = '--apply' in sys.argv
    if '--repin' in sys.argv:
        return repin(apply)
    raw = REG.read_text(encoding='utf-8')
    doc = json.loads(raw)
    if json.dumps(doc, indent=1, ensure_ascii=False) + ('\n' if raw.endswith('\n') else '') != raw:
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
    doc['updated_round'] = 'R624'
    REG.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    back = json.loads(REG.read_text(encoding='utf-8'))
    got = [r for r in back['rows'] if r.get('id') == ROW_ID]
    print('REGISTRY_APPEND=ok rows=%d readback=%d updated_round=%s'
          % (len(back['rows']), len(got), back.get('updated_round')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
