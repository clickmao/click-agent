#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q32 · C1: /tmp 路径逐行核查 (承 AF.4/AF.6.4: 9 行 evidence_cmd 仍含 /tmp)。

判据 (预注册 eval/capability/exp1-q32/prereg_q32.json §criteria.C1):
  · 抽取器**正控**: evidence_cmd 含 'eval/' 的行数必须 > 0, 否则读数作废 (防空表假绿)。
  · 分类 = 字段(evidence_cmd / evidence_path / negative_control / covers) × 形态(read_dep / write_out / unclassified)。
  · r1: read_dep 且**无仓库内等价物** ⇒ 判红 (单副本易失依赖)。
  · r2: write_out (中间产物可重建) ⇒ 接受为永久口径, reason=intermediate-regenerable。
  · r3 (D-ARCH): 历史证据归档件**禁止改字节**; 自足化只在入口层做逐位还原 + 冲突 fail-closed。
  · r4: 新增归档文件必须与 /tmp 原件逐字节相同 (sha256 相等)。

等价物判定 (两级, 无证据即弃权):
  · 强: 仓库内存在 basename 相同且 sha256 与 /tmp 原件相等的文件;
  · 弱: 仓库内存在 basename 相同的文件 (记 candidate, 不据此判绿)。
退出码: 0 无红 / 2 有红 / 3 环境失败 (登记表不可解析)。
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
OUT = 'eval/capability/exp1-q32/tmp_path_census_q32.json'
TMP_RE = re.compile(r'/tmp[A-Za-z0-9._/\-]*')
WRITE_FLAGS = {'--out', '-o', '--json', '--report', '--out-json', 'tee'}
WRITE_VAR_HINTS = ('OUT', 'JSON', 'REPORT', 'LOG', 'DUMP')


def sha256(p):
    h = hashlib.sha256()
    try:
        with open(p, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def repo_index():
    """basename → [路径] 全树索引 (跳过 .git)。"""
    idx = {}
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ('.git', 'bin', 'obj', 'node_modules')]
        for fn in files:
            idx.setdefault(fn, []).append(os.path.relpath(os.path.join(base, fn), ROOT))
    return idx


def classify_cmd(cmd):
    """把命令行里的 /tmp 出现分成 read_dep / write_out / unclassified (附原文上下文)。"""
    out = []
    for m in TMP_RE.finditer(cmd):
        tok = m.group(0).rstrip('.,;)\\')
        seg = cmd[:m.start()].rstrip()
        prev = seg.split()[-1] if seg.split() else ''
        # 形态判定: 写标志 / 变量名含输出义 / 重定向
        if prev in WRITE_FLAGS or prev.endswith('>'):
            kind = 'write_out'
        elif '=' in prev and not prev.startswith('-') and any(h in prev.split('=')[0].upper() for h in WRITE_VAR_HINTS):
            kind = 'write_out'
        elif re.search(r'(bash|sh|python3?|source|\.)\s+$', seg) or prev.startswith('-'):
            kind = 'read_dep'
        else:
            kind = 'unclassified'
        out.append({'token': tok, 'form': kind, 'prev_token': prev,
                    'context': cmd[max(0, m.start() - 40):m.end() + 40]})
    return out


def equivalent(tok, idx):
    """按 basename 找仓库内候选; 强判据 = sha256 相等 (原件存在时)。"""
    bn = os.path.basename(tok)
    cands = idx.get(bn, [])
    if not cands:
        # 目录形态 (归档目录) ⇒ 按前缀匹配
        cands = [p for k, v in idx.items() for p in v if tok.rstrip('/') in p]
    if not cands:
        return {'verdict': 'no_repo_candidate', 'candidates': []}
    origin_sha = sha256(tok)
    strong = []
    for c in cands:
        csha = sha256(os.path.join(ROOT, c))
        if origin_sha and csha and csha == origin_sha:
            strong.append({'path': c, 'sha256': csha})
    if strong:
        return {'verdict': 'repo_identical', 'candidates': [c['path'] for c in strong],
                'origin_sha256': origin_sha}
    return {'verdict': 'repo_same_name_only' if origin_sha else 'origin_absent',
            'candidates': cands[:5], 'origin_sha256': origin_sha}


FIELD_GET = {
    'evidence_cmd': lambda r: r.get('evidence_cmd'),
    'evidence_path': lambda r: r.get('evidence_path'),
    'negative_control': lambda r: r.get('negative_control'),
    'covers': lambda r: r.get('covers'),
}


def main():
    try:
        reg = json.load(open(os.path.join(ROOT, REG), encoding='utf-8-sig'))
    except Exception as e:  # 环境失败 ≠ 断言失败
        print('ENV_FAIL: 登记表不可解析: %r' % (e,))
        return 3
    rows = reg['rows']
    idx = repo_index()

    # ---- 正控: 抽取器必须看得见非空字段 ----
    pos_cmd = sum(1 for r in rows if r.get('evidence_cmd'))
    pos_eval = sum(1 for r in rows if 'eval/' in (r.get('evidence_cmd') or ''))
    print('POSITIVE_CONTROL rows=%d evidence_cmd_nonempty=%d evidence_cmd_has_eval=%d'
          % (len(rows), pos_cmd, pos_eval))
    if pos_eval == 0:
        print('CENSUS=VOID (正控失败: 抽取器看不见 evidence_cmd ⇒ 读数作废)')
        return 2

    findings, by_form, reds = [], {'read_dep': 0, 'write_out': 0, 'unclassified': 0}, []
    for r in rows:
        for field, getter in FIELD_GET.items():
            val = getter(r)
            if not val:
                continue
            blob = json.dumps(val, ensure_ascii=False)
            if '/tmp' not in blob:
                continue
            if field == 'evidence_cmd':
                occ = classify_cmd(val)
            else:
                occ = [{'token': t.rstrip('.,;)\\'), 'form': 'ref_text',
                        'prev_token': '', 'context': blob[max(0, blob.find(t) - 40):blob.find(t) + len(t) + 40]}
                       for t in sorted(set(TMP_RE.findall(blob)))]
            for o in occ:
                by_form[o['form']] = by_form.get(o['form'], 0) + 1
                eq = equivalent(o['token'], idx) if os.path.isabs(o['token']) else {'verdict': 'n/a'}
                exists = os.path.exists(o['token']) if os.path.isabs(o['token']) else False
                row = {'id': r['id'], 'field': field, 'token': o['token'], 'form': o['form'],
                       'exists_today': exists, 'equivalent': eq, 'context': o['context']}
                if field == 'evidence_cmd' and o['form'] == 'read_dep' and eq['verdict'] != 'repo_identical':
                    row['verdict'] = 'RED_volatile_single_copy'
                    reds.append(row['id'] + ':' + o['token'])
                elif field == 'evidence_cmd' and o['form'] == 'write_out':
                    row['verdict'] = 'ACCEPT_intermediate_regenerable'
                elif field == 'evidence_cmd' and o['form'] == 'read_dep':
                    row['verdict'] = 'FIX_rewrite_to_repo'
                    reds.append(row['id'] + ':' + o['token'])
                elif field == 'evidence_cmd':
                    row['verdict'] = 'ABSTAIN_unclassified_form'
                else:
                    row['verdict'] = ('RED_text_ref_volatile' if (field == 'negative_control' and exists and eq['verdict'] != 'repo_identical')
                                      else 'NOTE_text_ref')
                    if row['verdict'] == 'RED_text_ref_volatile':
                        reds.append(row['id'] + ':' + o['token'])
                findings.append(row)

    payload = {'round': 'EXP1-Q32', 'schema': 'tmp-path-census/1',
               'positive_control': {'rows': len(rows), 'evidence_cmd_nonempty': pos_cmd,
                                    'evidence_cmd_has_eval': pos_eval},
               'by_form': by_form, 'n_findings': len(findings),
               'rows_with_tmp_evidence_cmd': sorted({f['id'] for f in findings if f['field'] == 'evidence_cmd'}),
               'rows_with_tmp_any': sorted({f['id'] for f in findings}),
               'reds': reds, 'findings': findings}
    with open(os.path.join(ROOT, OUT), 'w', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False, indent=1) + '\n')

    print('BY_FORM %s' % json.dumps(by_form, ensure_ascii=False))
    print('ROWS_WITH_TMP_EVIDENCE_CMD %d' % len(payload['rows_with_tmp_evidence_cmd']))
    for rr in payload['rows_with_tmp_evidence_cmd']:
        print('  cmd_row %s' % rr)
    print('ROWS_WITH_TMP_ANY %d  FINDINGS %d' % (len(payload['rows_with_tmp_any']), len(findings)))
    for f_ in findings:
        print('  %-46s %-16s %-16s %-28s exists=%s %s'
              % (f_['id'], f_['field'], f_['form'], f_['verdict'], f_['exists_today'],
                 os.path.basename(f_['token'])))
    print('落盘 %s' % OUT)
    print('TMP_CENSUS=%s (REDS=%d)' % ('FAIL' if reds else 'OK', len(reds)))
    return 2 if reds else 0


if __name__ == '__main__':
    sys.exit(main())
