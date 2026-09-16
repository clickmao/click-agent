#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q32 · C3: 「器具改了而登记表未重审」的**提交前机检** (r483b 类漏检前移)。

背景 (AF.6.1): R487 提交时 `r483b.preflight-gate-instrument` 的器具 pin 停在旧值, 直到下一轮
跑**全量面**才发现 ⇒ 发现太晚。本守卫把该检查搬到提交面:

  · 每行 `evidence_generated_with.instrument` 的 `instrument_sha12` 必须 == 现盘文件 sha256 前 12 位;
  · `artifact_sha12` 非空时, 必须 == `evidence_path` 现盘 sha256 前 12 位 (记录被重写 ⇒ 需重审);
  · `pin_status == live` / `artifact_sha12 == null` ⇒ 该项**弃权** (自派生证据无冻结件);
  · 无 `evidence_generated_with` 的行 ⇒ 弃权单列 (unpinned), **不判红**。

判据 (预注册 eval/capability/exp1-q32/prereg_q32.json §criteria.C3):
  · 影子自检三态先跑: clean 夹具 rc=0 / 注入 stale_pin rc=2 / 注入 instrument_missing rc=2 / 仅 unpinned rc=0;
  · 真机读数如实报 (违例行逐条列出), 由本轮全量面刷新引起的 artifact 漂移 ⇒ 交定向重审收口。
退出码: 0 无违例 / 2 有违例 (断言失败) / 3 环境失败 (登记表不可解析 / 文件不可读)。
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
REG = 'docs/verification-registry.json'
BIND = None  # 产品侧器具模块 (bind_evidence.py), 由 main() 惰性加载


def sha12(p):
    try:
        h = hashlib.sha256()
        with open(p, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
        return h.hexdigest()[:12]
    except OSError:
        return None


def sha12_bytes(b):
    return hashlib.sha256(b).hexdigest()[:12]


def load_bind():
    """按路径加载产品侧器具 bind_evidence.py (单一真理源; 目录摘要在那里定义)。"""
    import importlib.util
    p = os.path.join(ROOT, 'eval/capability/bind_evidence.py')
    if not os.path.isfile(p):
        return None
    spec = importlib.util.spec_from_file_location('bind_evidence_q32', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def my_dir_digest(root, rel):
    """**独立第二实现** (与产品侧 dir_manifest 同规格): 目录清单摘要。

    规格 (EXP1-Q27/AF): 文件集取 `git ls-files <rel>` (索引; 未跟踪/忽略件不入闸);
    digest = sha256[:12] of 按 relpath 排序的 "<relpath>:<size>:<sha12>\\n" 串联。
    """
    out = subprocess.run(['git', 'ls-files', '--', rel], cwd=root, capture_output=True, text=True,
                         check=False).stdout.split('\n')
    rows = []
    for p in sorted(x for x in out if x.strip()):
        try:
            b = open(os.path.join(root, p), 'rb').read()
        except OSError:
            continue
        rows.append('%s:%d:%s\n' % (p, len(b), sha12_bytes(b)))
    return sha12_bytes(''.join(rows).encode()), len(rows)


def evidence_digest(root, row, kind, bind):
    """按 evidence_kind 取现盘摘要: file ⇒ sha12; directory ⇒ 目录清单摘要 (第二实现 + 与产品侧差分)。"""
    ep = row.get('evidence_path')
    if not ep:
        return None, 'no_evidence_path'
    full = os.path.join(root, ep)
    if kind == 'directory' or os.path.isdir(full):
        mine, n = my_dir_digest(root, ep)
        if bind is not None:
            try:
                theirs = bind.dir_manifest(root, ep)
            except Exception:
                theirs = None
            if theirs is not None and theirs[0] != mine:
                return mine, 'PORT_DIVERGENCE:mine=%s:bind=%s' % (mine, theirs[0])
        return mine, 'directory_manifest(n=%d)' % n
    return sha12(full), 'file'


def audit(doc, base):
    """返回 (rows, violations, abstain)。base = 仓库根 (夹具可指向临时根)。"""
    rows, viol, abstain = [], [], []
    for r in doc.get('rows', []):
        rid = r.get('id')
        gen = r.get('evidence_generated_with')
        if not gen:
            abstain.append({'id': rid, 'why': 'unpinned_no_evidence_generated_with'})
            continue
        rec = {'id': rid, 'instrument': gen.get('instrument'), 'instrument_sha12': gen.get('instrument_sha12'),
               'artifact_sha12': gen.get('artifact_sha12'), 'pin_status': gen.get('pin_status'),
               'evidence_path': r.get('evidence_path'), 'audited_by_round': gen.get('audited_by_round')}
        inst = gen.get('instrument')
        if inst:
            p = os.path.join(base, inst)
            cur = sha12(p)
            rec['instrument_now'] = cur
            if cur is None:
                rec['verdict'] = 'instrument_missing'
                viol.append(rec)
            elif gen.get('instrument_sha12') and cur != gen['instrument_sha12']:
                rec['verdict'] = 'stale_pin'
                viol.append(rec)
            else:
                rec['verdict'] = 'instrument_ok'
        want_a = gen.get('artifact_sha12')
        ep = r.get('evidence_path')
        if want_a and ep:
            kind = gen.get('evidence_kind')
            cur, how = evidence_digest(base, r, kind, BIND)
            rec['artifact_now'] = cur
            rec['artifact_digest'] = how
            if cur is None:
                rec['artifact_verdict'] = 'artifact_missing'
                viol.append(rec)
            elif str(how).startswith('PORT_DIVERGENCE'):
                rec['artifact_verdict'] = 'port_divergence'
                viol.append(rec)
            elif cur != want_a:
                rec['artifact_verdict'] = 'artifact_drift'
                viol.append(rec)
            else:
                rec['artifact_verdict'] = 'artifact_ok'
        elif not want_a:
            rec['artifact_verdict'] = 'abstain_live_or_null'
        rec.setdefault('verdict', 'checked')
        rows.append(rec)
    # 去重 (同一行可能同时命中器具与记录两类违例 ⇒ 只记一次)
    seen, uniq = set(), []
    for v in viol:
        if v['id'] in seen:
            continue
        seen.add(v['id'])
        uniq.append(v)
    return rows, uniq, abstain


def audit_face(man, base, viol):
    """L2 器具面 (instruments.json) 的 pin 复核: 每条 `instrument_sha12` vs 现盘文件 sha12。

    与 registry 行同一族缺陷 (「器具改了而面清单未重审」) —— Q32 实测该面把这条抓在**跑完整个
    全量面之后**, 本守卫把它前移到提交面。
    """
    stale, ok, missing = [], 0, []
    for e in man.get('instruments', []):
        ep, want = e.get('evidence_path'), e.get('instrument_sha12')
        if not ep or not want:
            continue
        cur = sha12(os.path.join(base, ep))
        if cur is None:
            missing.append(e.get('id'))
            viol.append({'id': 'face:' + str(e.get('id')), 'kind': 'face_instrument_missing',
                         'instrument': ep, 'instrument_sha12': want, 'instrument_now': None})
        elif cur != want:
            stale.append({'id': e.get('id'), 'path': ep, 'want': want, 'now': cur})
            viol.append({'id': 'face:' + str(e.get('id')), 'kind': 'face_stale_pin',
                         'instrument': ep, 'instrument_sha12': want, 'instrument_now': cur})
        else:
            ok += 1
    return {'n_entries': len(man.get('instruments', [])), 'n_ok': ok, 'stale': stale, 'missing': missing}


def selftest():
    bad = 0
    tmp = tempfile.mkdtemp(prefix='q32-guard-')
    try:
        inst = os.path.join(tmp, 'inst.py')
        open(inst, 'w').write('print(1)\n')
        art = os.path.join(tmp, 'art.json')
        open(art, 'w').write('{"a":1}\n')
        good = sha12(inst)
        fixtures = [
            ('clean', [{'id': 'x.ok', 'evidence_path': 'art.json',
                        'evidence_generated_with': {'instrument': 'inst.py', 'instrument_sha12': good,
                                                    'artifact_sha12': sha12(art)}}], 0),
            ('stale_pin', [{'id': 'x.stale', 'evidence_path': 'art.json',
                            'evidence_generated_with': {'instrument': 'inst.py',
                                                        'instrument_sha12': 'deadbeef0000',
                                                        'artifact_sha12': sha12(art)}}], 2),
            ('instrument_missing', [{'id': 'x.miss', 'evidence_path': 'art.json',
                                     'evidence_generated_with': {'instrument': 'nope.py',
                                                                 'instrument_sha12': good,
                                                                 'artifact_sha12': sha12(art)}}], 2),
            ('artifact_drift', [{'id': 'x.drift', 'evidence_path': 'art.json',
                                 'evidence_generated_with': {'instrument': 'inst.py', 'instrument_sha12': good,
                                                             'artifact_sha12': 'deadbeef0000'}}], 2),
            ('unpinned_only', [{'id': 'x.raw', 'evidence_path': 'art.json'}], 0),
        ]
        for name, rows, want in fixtures:
            _, v, a = audit({'rows': rows}, tmp)
            rc = 2 if v else 0
            ok = rc == want
            bad += 0 if ok else 1
            print('  %-20s expect_rc=%d got=%d viol=%d abstain=%d %s'
                  % (name, want, rc, len(v), len(a), 'OK' if ok else 'FAIL'))
        # 器具面 pin 夹具 (face_stale_pin / face_clean)
        face_fix = [
            ('face_clean', [{'id': 'f.ok', 'evidence_path': 'inst.py', 'instrument_sha12': good}], 0),
            ('face_stale_pin', [{'id': 'f.stale', 'evidence_path': 'inst.py',
                                 'instrument_sha12': 'deadbeef0000'}], 2),
            ('face_instrument_missing', [{'id': 'f.miss', 'evidence_path': 'gone.py',
                                          'instrument_sha12': good}], 2),
        ]
        for name, entries, want in face_fix:
            viol = []
            audit_face({'instruments': entries}, tmp, viol)
            rc = 2 if viol else 0
            ok = rc == want
            bad += 0 if ok else 1
            print('  %-20s expect_rc=%d got=%d viol=%d %s' % (name, want, rc, len(viol), 'OK' if ok else 'FAIL'))
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    print('SELFTEST %s (%d/%d)' % ('PASS' if bad == 0 else 'FAIL', 8 - bad, 8))
    return 0 if bad == 0 else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--json', default='eval/capability/exp1-q32/reaudit_guard_q32.json')
    ap.add_argument('--registry', default=REG, help='登记表路径 (默认 %s; 供负控夹具注入)' % REG)
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    global BIND
    BIND = load_bind()
    if BIND is None:
        print('WARN: 未找到 eval/capability/bind_evidence.py ⇒ 目录摘要只走第二实现 (无差分绑定)')
    try:
        doc = json.load(open(os.path.join(ROOT, a.registry), encoding='utf-8-sig'))
    except Exception as e:
        print('ENV_FAIL: 登记表不可解析: %r' % (e,))
        return 3
    rows, viol, abstain = audit(doc, ROOT)
    face_viol = []
    face = {'n_entries': 0, 'n_ok': 0, 'stale': [], 'missing': []}
    fmp = os.path.join(ROOT, 'eval/capability/instruments.json')
    if os.path.isfile(fmp):
        face = audit_face(json.load(open(fmp, encoding='utf-8')), ROOT, face_viol)
    checked = sum(1 for r in rows if r.get('instrument_now') or r.get('artifact_now'))
    out = {'round': 'EXP1-Q32', 'schema': 'reaudit-guard/1', 'registry': REG,
           'rows_total': len(doc.get('rows', [])), 'rows_checked': checked,
           'violations': viol, 'n_violations': len(viol), 'abstain_unpinned': abstain,
           'n_abstain': len(abstain), 'face_pins': face, 'face_violations': face_viol,
           'rule': 'instrument_sha12 == 现盘 sha12 ∧ artifact_sha12 == 现盘 sha12 (registry) ∧ '
                   'instruments.json 每条 pin == 现盘 sha12; live/null ⇒ 弃权'}
    p = os.path.join(ROOT, a.json)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    if not a.quiet:
        for v in viol + face_viol:
            print('  VIOLATION %-42s %-22s inst=%s→%s art=%s→%s'
                  % (v['id'], v.get('kind') or v.get('verdict'), v.get('instrument_sha12'),
                     v.get('instrument_now'), v.get('artifact_sha12'), v.get('artifact_now')))
        print('REAUDIT_GUARD rows=%d checked=%d abstain=%d violations=%d | face %d/%d ok 违例=%d | 落盘 %s'
              % (out['rows_total'], checked, len(abstain), len(viol), face['n_ok'], face['n_entries'],
                 len(face_viol), a.json))
        print('REAUDIT=%s (0=无违例, 2=需重审)' % ('OK' if not (viol or face_viol) else 'FAIL'))
    return 2 if (viol or face_viol) else 0


if __name__ == '__main__':
    sys.exit(main())
