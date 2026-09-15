#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q19 · L2 器具登记写入器。

工作流 (先读数后登记):
  1. 读 eval/capability/exp1-q19/l2_probe.json (双证读数) —— 只有 verified_pair=true 的候选才写入;
  2. 给 **所有** 行补契约 L2 机械化字段: version / version_source / instrument_sha12 / input_fingerprint;
  3. 追加新行 (从读数派生, 一切哈希由文件字节重算, 不手打);
  4. 改写前断言「序列化器逐字节复现原文件」—— 不成立即中止 (改用文本插入), 绝不静默重排;
  5. 幂等: 已存在的 id 只更新字段, 不重复插入; 写后读回校验。

用法:
  python3 eval/capability/exp1-q19/register_l2.py --check-roundtrip   # 只做改写前置断言
  python3 eval/capability/exp1-q19/register_l2.py --apply             # 写入 + 读回校验
"""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
MAN = ROOT / 'eval/capability/instruments.json'
PROBE = ROOT / 'eval/capability/exp1-q19/l2_probe.json'
BACKUP = ROOT / 'eval/capability/exp1-q19/instruments.json.bak'

KPI_QUAD = {
    'exp1q11.other-bucket-decompose': {'单位': '边', '分母': 'v2.6.0 边级 kind 轴 other 桶',
                                       '真值源': '归档 citations.jsonl (exp1-q10)', '口径档': '边级/单标签'},
    'exp1q15.unit-axis-guard': {'单位': '轴(单位×分母)', '分母': '登记面 cited_edges 总数',
                                '真值源': '归档 citations.jsonl + 器具源码 AST', '口径档': '10 fixture'},
    'exp1q15.unit-axis-guard-q16': {'单位': '轴(单位×分母)', '分母': '登记面 cited_edges 总数',
                                    '真值源': '归档 citations.jsonl + 器具源码 AST', '口径档': '14 fixture'},
    'exp1q17.archive-field-provenance': {'单位': '字段(生产者/落盘/归档)', '分母': 'Σ=35 (P∪D∪A)',
                                         '真值源': 'probe_v260.py 写点 ∪ citations.jsonl ∪ attribution_q10.json',
                                         '口径档': '五类归因桶'},
    'exp1q18.rebuild-constructor': {'单位': '行(变更行)', '分母': '源文件总行数',
                                    '真值源': 'probe_v260.py 字节 sha256', '口径档': '单变量: 2 行'},
    'l2.instruments-check': {'单位': '器具行', '分母': 'instruments.json 行数',
                             '真值源': '磁盘文件重算 sha256', '口径档': 'L2 全字段 + 正/负控'},
}

NEW_ROW_META = {   # 读数派生之外的人工语义字段 (允许人工: id/kind/owner/说明)
    'exp1q11.other-bucket-decompose': 'analyzer',
    'exp1q15.unit-axis-guard': 'guard',
    'exp1q15.unit-axis-guard-q16': 'guard',
    'exp1q17.archive-field-provenance': 'analyzer',
    'exp1q18.rebuild-constructor': 'builder',
}
NC_META = {
    'exp1q11.other-bucket-decompose': {'nc_expect': 'nonzero'},
    'exp1q18.rebuild-constructor': {'nc_expect': 'detect:NC_OK'},
}
# 既有行的命令面覆盖: 器具把结果写回**轮次证据路径** (无 --out 参数或默认指向证据文件) 时,
# 全量面复跑会把它改写 → 证据降级 (实测 q17 / q1)。覆盖 = 显式把输出指向 scratch 目录。
CMD_OVERRIDE = {
    'exp1q1.scope-selftest': {
        'cmd': ('python3 eval/capability/exp1-q1/selftest_scope.py '
                '--out eval/capability/exp1-q19/l2runs/selftest_q1.json'),
        'nc_cmd': ('python3 eval/capability/exp1-q1/selftest_scope.py '
                   '--out eval/capability/exp1-q19/l2runs/selftest_q1_nc.json --bogus'),
        'nc_expect': 'nonzero',
        'why': '原 cmd 的 selftest 把 selftest.json 写回轮次产物路径 (硬编码) ⇒ 复跑即改写入口证据',
    },
}
DECL_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*VERSION[A-Za-z0-9_]*)\s*=\s*"([^"]+)"', re.M)
TOK = re.compile(r'[A-Za-z0-9_./\-]+\.[A-Za-z0-9]{1,6}')
OUT_FLAGS = ('--out', '--json', '--emit', '--fixtures-out', '--archive-out')


def sha12(p):
    try:
        return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:12]
    except Exception:
        return None


def declared_version(path):
    """只认**器具自身**的版本常量 (排除 prereg_* 等非器具版本)。"""
    try:
        txt = (ROOT / path).read_text(encoding='utf-8', errors='replace')
    except Exception:
        return None
    for m in DECL_RE.finditer(txt):
        name = m.group(1).lower()
        if name.endswith('_version') and 'prereg' not in name and name != 'version':
            return m.group(2)
    return None


def derive_version(path, sha):
    v = declared_version(path)
    if v and 'sha' not in v.lower():
        return v, 'declared'
    return f'content-sha12:{sha}', 'content-sha12'


def cmd_input_paths(cmd, evidence_path):
    """从 cmd 字面量机械抽取**输入**文件路径 (排除器具自身与输出参数后的路径)。"""
    out = []
    for m in TOK.finditer(cmd):
        tok = m.group(0)
        if tok == evidence_path:
            continue
        pre = cmd[max(0, m.start() - 16):m.start()]
        if any(f in pre for f in OUT_FLAGS):
            continue
        if (ROOT / tok).is_file():
            out.append(tok)
    return sorted(set(out))


def build_fingerprint(paths):
    return [{'path': p, 'sha12': sha12(p)} for p in paths]


def main():
    apply_ = '--apply' in sys.argv
    raw = MAN.read_text(encoding='utf-8')
    man = json.loads(raw)
    roundtrip = json.dumps(man, ensure_ascii=False, indent=1) + '\n'
    same = (roundtrip == raw)
    print(f'roundtrip_byte_identical={same}  bytes={len(raw)}')
    if '--check-roundtrip' in sys.argv:
        return 0 if same else 1
    if not same:
        print('ABORT: 序列化器不能逐字节复现原文件 ⇒ 改用文本插入 (本轮中止, 不静默重排)')
        return 2

    probe = json.loads(PROBE.read_text(encoding='utf-8'))
    added, updated, refreshed = [], [], []
    for e in man['instruments']:
        ov = CMD_OVERRIDE.get(e['id'])
        if ov:
            e['cmd'] = ov['cmd']
            if 'nc_cmd' in ov:
                e['nc_cmd'] = ov['nc_cmd']
            if 'nc_expect' in ov:
                e['nc_expect'] = ov['nc_expect']
            e['cmd_override_reason'] = ov['why']
        ep = e['evidence_path']
        sha = sha12(ep)
        ver, vsrc = derive_version(ep, sha)
        e['version'] = ver
        e['version_source'] = vsrc
        e['instrument_sha12'] = sha
        paths = cmd_input_paths(e['cmd'], ep)
        e['input_fingerprint'] = build_fingerprint(paths)
        paths2 = [p['path'] for p in (probe_inputs(probe, e['id']) or [])]
        for p in paths2:
            if p not in paths:
                e['input_fingerprint'].append({'path': p, 'sha12': sha12(p)})
        updated.append(e['id'])

    by_id = {e['id']: e for e in man['instruments']}
    for c in probe['candidates']:
        if not c.get('verified_pair'):
            continue
        if c['id'] in by_id:
            # 已存在的行: 命令面以**读数**为单源刷新 (否则器具默认 --out 会覆盖轮次证据)
            e = by_id[c['id']]
            e['cmd'] = c['pos_cmd']
            e['expect_rc'] = 0
            e['expect_substr'] = c['pos_substr']
            for k in ('nc_cmd', 'nc_expect', 'nc_cmd2', 'nc_expect2'):
                e.pop(k, None)
            if c['negs']:
                e['nc_cmd'] = c['negs'][0]['cmd']
                e['nc_expect'] = NC_META.get(c['id'], {}).get('nc_expect', 'nonzero')
            if len(c['negs']) > 1:
                e['nc_cmd2'] = c['negs'][1]['cmd']
                e['nc_expect2'] = 'nonzero'
            refreshed.append(c['id'])
            continue
        ep = c['file']
        sha = sha12(ep)
        ver, vsrc = derive_version(ep, sha)
        inputs = [i['path'] for i in c['inputs']] + cmd_input_paths(c['pos_cmd'], ep)
        row = {
            'id': c['id'], 'kind': NEW_ROW_META.get(c['id'], 'analyzer'),
            'cmd': c['pos_cmd'], 'expect_rc': 0, 'expect_substr': c['pos_substr'],
            'version': ver, 'version_source': vsrc, 'instrument_sha12': sha,
            'input_fingerprint': build_fingerprint(sorted(set(inputs))),
            'kpi_quad': KPI_QUAD.get(c['id'], {}),
            'owner_round': 'EXP1-Q19', 'evidence_path': ep,
        }
        if c['negs']:
            row['nc_cmd'] = c['negs'][0]['cmd']
            row['nc_expect'] = NC_META.get(c['id'], {}).get('nc_expect', 'nonzero')
        if len(c['negs']) > 1:
            row['nc_cmd2'] = c['negs'][1]['cmd']
            row['nc_expect2'] = 'nonzero'
        man['instruments'].append(row)
        by_id[row['id']] = row
        added.append(row['id'])

    # 机检自身作为一行 (其负控 = 注入指纹漂移必须判红)
    if 'l2.instruments-check' not in by_id:
        ep = 'eval/capability/instruments_check.py'
        sha = sha12(ep)
        man['instruments'].append({
            'id': 'l2.instruments-check', 'kind': 'checker',
            'cmd': 'python3 eval/capability/instruments_check.py --only exp1q17.archive-field-provenance',
            'expect_rc': 0, 'expect_substr': 'L2 器具验收面',
            'nc_cmd': ('python3 eval/capability/instruments_check.py '
                       '--only exp1q17.archive-field-provenance --fingerprint-drift-inject'),
            'nc_expect': 'nonzero',
            'version': f'content-sha12:{sha}', 'version_source': 'content-sha12',
            'instrument_sha12': sha, 'input_fingerprint': [],
            'kpi_quad': KPI_QUAD['l2.instruments-check'],
            'owner_round': 'EXP1-Q19', 'evidence_path': ep,
        })
        added.append('l2.instruments-check')

    if not apply_:
        print(f'DRY-RUN: 将更新 {len(updated)} 行, 追加 {len(added)} 行 {added}')
        return 0

    BACKUP.write_text(raw, encoding='utf-8')
    MAN.write_text(json.dumps(man, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    back = json.loads(MAN.read_text(encoding='utf-8'))
    print(f'WROTE rows={len(back["instruments"])} (updated={len(updated)} refreshed={len(refreshed)} {refreshed} added={len(added)} {added})')
    miss = []
    for e in back['instruments']:
        for k in ('version', 'version_source', 'instrument_sha12', 'input_fingerprint', 'kpi_quad'):
            if k not in e:
                miss.append((e['id'], k))
    print(f'READBACK missing_fields={miss}')
    print('ids:', [e['id'] for e in back['instruments']])
    return 0 if not miss else 1


def probe_inputs(probe, rid):
    for c in probe['candidates']:
        if c['id'] == rid:
            return c['inputs']
    return None


if __name__ == '__main__':
    sys.exit(main())
