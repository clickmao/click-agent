#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q33 · C5: 复现前提的外部资产 → registry **显式字段**。

现状 (Q32 §AG.6.5): `*.gguf` / 发布物 (`/tmp/pub_*`) / 外部 venv (`/tmp/z3env`) 只散落在 registry 行的
`evidence_cmd` 文本里 ⇒ 机检答不出「这条能力的复现前提现在还在不在场」。

本器具 (结构化派生 + 在场实测):
  1. 抽取: 从 registry 行的证据字段文本里抽路径样 token (声明式规则 + **去散文污染**);
  2. 判定: kind ∈ {dir,file,missing} + present 实测 + 在场时 bytes/sha12; 与散文无关的片段记 not_an_asset;
  3. 产出: 每行 `external_assets[]` (path/kind/present/sha12/bytes/source_field);
  4. `--apply`: 把该字段写回 `docs/verification-registry.json` (幂等 + 逐字节复现断言 + 读回校验);
     写回后**必须**跑形式门禁 (VerificationForm)。
负控: 夹具里删掉一个在场资产 ⇒ present 必翻 false; 注入一行含外部路径但无字段 ⇒ 覆盖闸必报缺口。
退出码: 0 达标 / 2 越线 / 3 环境失败。
"""
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
REG = 'docs/verification-registry.json'
OUT = 'eval/capability/exp1-q33/external_assets_q33.json'
FIELDS = ('evidence_cmd', 'evidence_path', 'negative_control')
# 声明式规则: 绝对值路径 token (.gguf 也单列), 去掉散文尾随符 (CJK 标点/全角括号/引号/逗号)
ASSET_RE = re.compile(r'(/tmp/[A-Za-z0-9_./+-]*|/home/[A-Za-z0-9_./+-]*|[\w.-]+\.gguf)')
TRIM_RE = re.compile(r'[，。、；：（）【】「」《》\s"\'`,;)）】]+$')
PROSE_TOKENS = {'/tmp', '/home', '/', '/tmp/aot', '/tmp/models'}


def sha12(p):
    try:
        return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]
    except OSError:
        return None


def classify_asset(path, root=None):
    root = root or ROOT
    full = path if os.path.isabs(path) else os.path.join(root, path)
    if os.path.isdir(full):
        n, nb = 0, 0
        for dp, _dn, fn in os.walk(full):
            for f in fn:
                n += 1
                try:
                    nb += os.path.getsize(os.path.join(dp, f))
                except OSError:
                    pass
        return {'path': path, 'kind': 'dir', 'present': True, 'n_files': n, 'bytes': nb}
    if os.path.isfile(full):
        return {'path': path, 'kind': 'file', 'present': True,
                'bytes': os.path.getsize(full), 'sha12': sha12(full)}
    return {'path': path, 'kind': 'missing', 'present': False,
            'note': '复现前提不在场 ⇒ 该行 capability 复现需先重建此资产'}


def extract(row):
    """返回 (assets, not_an_asset)。source_field 记录来自哪个字段 —— 归属可见。"""
    found, prose = {}, {}
    for f in FIELDS:
        txt = row.get(f)
        if not isinstance(txt, str):
            continue
        for m in ASSET_RE.finditer(txt):
            raw = m.group(0)
            clean = TRIM_RE.sub('', raw)
            if clean in PROSE_TOKENS or len(clean) < 6:
                prose[raw] = f
                continue
            found.setdefault(clean, f)
    return found, prose


def build(root=None, rows_path=None):
    root = root or ROOT
    doc = json.load(open(rows_path or os.path.join(root, REG), encoding='utf-8'))
    rows = doc['rows']
    result = []
    for r in rows:
        found, prose = extract(r)
        if not found:
            continue
        assets = [classify_asset(p, root=root) for p in sorted(found)]
        for a in assets:
            a['source_field'] = found[a['path']]
        result.append({'id': r['id'], 'level': r.get('level'), 'owner_round': r.get('owner_round'),
                       'external_assets': assets,
                       'prose_fragments_ignored': sorted(prose)})
    n_assets = sum(len(x['external_assets']) for x in result)
    present = sum(1 for x in result for a in x['external_assets'] if a['present'])
    payload = {'round': 'EXP1-Q33', 'schema': 'external-assets/1', 'registry': rows_path or REG,
               'n_rows_total': len(rows), 'n_rows_with_assets': len(result), 'n_assets': n_assets,
               'n_present': present, 'n_missing': n_assets - present,
               'rows': result,
               'rule': ('外部资产按**字段**登记 (path/kind/present/sha12/bytes/source_field); present 为'
                        '现盘实测; 散文碎片 (如 "/tmp、") 记 not_an_asset 不冒充资产'),
               'coverage': {'rows_without_field_but_with_asset_text': 0}}
    return payload


def selftest():
    """负控: ①在场资产被删 ⇒ present 翻 false; ②注入行含外部路径但无字段 ⇒ 覆盖闸报缺口。"""
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix='q33-extassets-')
    bad = 0
    cases = {}
    try:
        os.makedirs(os.path.join(tmp, 'eval/capability'), exist_ok=True)
        os.makedirs(os.path.join(tmp, 'assets'), exist_ok=True)
        asset = os.path.join(tmp, 'assets', 'model.gguf')
        open(asset, 'wb').write(b'GGUF' + b'\x00' * 32)
        rows = {'rows': [
            {'id': 'a.ok', 'level': 'L3', 'owner_round': 'R1', 'evidence_cmd': 'run %s' % asset,
             'evidence_path': 'x', 'negative_control': 'n'},
            {'id': 'b.prose', 'level': 'L3', 'owner_round': 'R1', 'evidence_cmd': 'cwd=/tmp/aot、/tmp、/ 混排',
             'evidence_path': 'x', 'negative_control': 'n'},
        ]}
        p = os.path.join(tmp, 'reg.json')
        json.dump(rows, open(p, 'w', encoding='utf-8'))
        pay = build(root=tmp, rows_path=p)
        cases['asset_present_detected'] = (pay['n_assets'] == 1 and pay['n_present'] == 1
                                           and pay['rows'][0]['external_assets'][0]['kind'] == 'file')
        cases['prose_fragment_not_asset'] = (pay['n_rows_with_assets'] == 1)
        os.remove(asset)
        pay2 = build(root=tmp, rows_path=p)
        cases['missing_asset_flips_present_false'] = (pay2['n_present'] == 0 and pay2['n_missing'] == 1
                                                      and pay2['rows'][0]['external_assets'][0]['kind'] == 'missing')
        # 覆盖闸: 行内文本含资产路径, 但结构化字段缺失 (--check-coverage 语义)
        rows['rows'][0].pop('external_assets', None)
        cov = coverage(rows['rows'], pay2)
        cases['coverage_flags_missing_field'] = (cov['n_missing_field'] == 1)
        # EXP1-Q34: 判据必须读**写回后**的盘面 —— 首版读 apply 前快照 ⇒ 首次运行恒报 GAP=20 (空心红)。
        reg2 = os.path.join(tmp, 'reg2.json')
        rows2 = {'rows': [dict(r) for r in rows['rows']]}
        open(reg2, 'w', encoding='utf-8').write(json.dumps(rows2, ensure_ascii=False, indent=1) + '\n')
        pay3 = build(root=tmp, rows_path=reg2)
        rc3, _ = apply_to_registry(pay3, rows_path=reg2)
        now = json.load(open(reg2, encoding='utf-8'))['rows']
        cases['coverage_zero_after_apply'] = (rc3 == 0 and coverage(now, pay3)['n_missing_field'] == 0)
        rc4, _ = apply_to_registry(pay3, rows_path=reg2)
        cases['apply_is_idempotent'] = (rc4 == 0 and json.load(open(reg2, encoding='utf-8'))['rows'] == now)
        for k, v in cases.items():
            print('  %-38s %s' % (k, 'OK' if v else 'FAIL'))
            bad += 0 if v else 1
        n = len(cases)
        print('SELFTEST %s (%d/%d)' % ('PASS' if bad == 0 else 'FAIL', n - bad, n))
        return 0 if bad == 0 else 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def coverage(rows, payload):
    """覆盖闸: 文本里有资产路径的行必须已登记 `external_assets` 字段。"""
    by_id = {x['id']: x for x in payload['rows']}
    missing = []
    for r in rows:
        found, _ = extract(r)
        if found and 'external_assets' not in r:
            missing.append(r['id'])
        elif found and r['id'] in by_id and not by_id[r['id']]['external_assets']:
            missing.append(r['id'])
    return {'n_rows_with_asset_text': len([r for r in rows if extract(r)[0]]),
            'n_missing_field': len(missing), 'missing': missing}


def apply_to_registry(payload, rows_path=None):
    """把 external_assets 写回 registry (幂等 + 序列化器逐字节复现断言 + 读回校验)。"""
    path = rows_path or os.path.join(ROOT, REG)
    raw = open(path, encoding='utf-8').read()
    doc = json.loads(raw)
    rebuilt = json.dumps(doc, ensure_ascii=False, indent=1) + '\n'
    if rebuilt != raw:
        return 3, {'error': 'SERIALIZER_NOT_BYTE_REPRODUCIBLE',
                   'note': '改写前必须能逐字节复现原文件, 否则改用文本插入 (禁止静默重排)'}
    by_id = {x['id']: x for x in payload['rows']}
    touched = 0
    for r in doc['rows']:
        x = by_id.get(r['id'])
        if not x:
            continue
        if r.get('external_assets') == x['external_assets']:
            continue
        r['external_assets'] = x['external_assets']
        touched += 1
    if not touched:
        return 0, {'touched': 0, 'note': 'IDEMPOTENT_NO_CHANGE'}
    new = json.dumps(doc, ensure_ascii=False, indent=1) + '\n'
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(new)
    back = json.loads(open(path, encoding='utf-8').read())
    n_back = sum(1 for r in back['rows'] if r.get('external_assets') == by_id.get(r['id'], {}).get('external_assets'))
    return 0, {'touched': touched, 'readback_rows_matching': n_back}


def main():
    if '--selftest' in sys.argv:
        return selftest()
    payload = build()
    cov_pre = coverage(json.load(open(os.path.join(ROOT, REG), encoding='utf-8'))['rows'], payload)
    payload['coverage_pre_apply'] = cov_pre
    if '--apply' in sys.argv:
        rc, rep = apply_to_registry(payload)
        payload['apply'] = rep
        if rc:
            print('APPLY_ABORT: %s' % json.dumps(rep, ensure_ascii=False))
            return rc
    # EXP1-Q34 判据修正 (自我否证): 覆盖闸必须在**写回之后**的盘面上复算。首版用 apply 前的内存快照判定
    #   ⇒ 首次运行**恒**报 GAP=20, 且列出的正是本次要补的那 20 行 —— 判据与动作互相矛盾 (空心红:
    #   读数与器具行为相反, 谁也修不绿)。修正后: pre_apply 覆盖保留作「本次补了哪些行」的信息项,
    #   判决只读 post-apply。禁止为了让脚本变绿而放宽阈值 —— 这里改的是**读哪一面**, 不是阈值。
    rows_now = json.load(open(os.path.join(ROOT, REG), encoding='utf-8'))['rows']
    cov = coverage(rows_now, payload)
    payload['coverage'] = cov
    payload['staged_application'] = {'field': 'external_assets',
                                     'target': REG,
                                     'gate': 'VerificationForm (写回后必须同轮跑形式门禁)'}
    if '--apply' in sys.argv:
        rc, rep = apply_to_registry(payload)
        payload['apply'] = rep
        if rc:
            print('APPLY_ABORT: %s' % json.dumps(rep, ensure_ascii=False))
            return rc
    with open(os.path.join(ROOT, OUT), 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, indent=1) + '\n')
    print('ROWS_TOTAL=%d ROWS_WITH_ASSETS=%d ASSETS=%d PRESENT=%d MISSING=%d'
          % (payload['n_rows_total'], payload['n_rows_with_assets'], payload['n_assets'],
             payload['n_present'], payload['n_missing']))
    print('COVERAGE=%s' % json.dumps(cov, ensure_ascii=False)[:200])
    print('落盘 %s' % OUT)
    print('EXTERNAL_ASSETS=%s' % ('OK' if not cov['n_missing_field'] else 'GAP %s' % cov['missing']))
    return 0 if not cov['n_missing_field'] else 2


if __name__ == '__main__':
    sys.exit(main())
