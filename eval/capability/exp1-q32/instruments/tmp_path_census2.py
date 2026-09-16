#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q32 · C1 census v2 (修正口径): /tmp 逐行 + 仓库内引用存在性, 逐类裁定。

v1 (`instruments/tmp_path_census.py`, 口径 1) 的首跑把 `negative_control` 文本里的 /tmp
**目录字面量** (如 「发布到 /tmp/d2-cwd」) 判红 —— 与 AF.1 的 kernel32 同族缺陷: **词面出现 ≠ 依赖**。
v2 修正 (记 v1/v2 两栏读数, 不翻 v1):
  · 判红只对**证据命令的读依赖**中「**可入库而未入库的唯一副本**」(脚本/编排器/数据/项目源码);
  · 外部资产 (模型权重 / 外部 venv / 发布物二进制 / 测试 scratch 目录) ⇒ ACCEPT_* 类 + 记 reason;
  · 文本引用 ⇒ NOTE_* 类 (不判红);
  · 新增正面检查: 证据命令里的**仓库内路径**引用必须存在 (缺失记 NOTE_ 并列出, 用于验证本轮改指生效)。
退出码: 0 无红 / 2 有红 / 3 环境失败。
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
OUT = 'eval/capability/exp1-q32/tmp_path_census2_q32.json'
TMP_RE = re.compile(r'/tmp[A-Za-z0-9._/\-]*')
REPO_RE = re.compile(r'(?:eval|scripts|src|tools|docs|config)/[A-Za-z0-9._/\-]+')
WRITE_FLAGS = {'--out', '-o', '--json', '--report', '--out-json', 'tee'}
RUNNERS = re.compile(r'^(bash|sh|python3?|source|\.)$')
EXTERNAL_SUFFIX = ('.gguf', '.bin', '.so', '.dll')
EXTERNAL_DIRS = ('/tmp/models', '/tmp/z3env', '/tmp/pub_', '/tmp/aot', '/tmp/proxies')


def sha256(p):
    try:
        h = hashlib.sha256()
        with open(p, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def repo_index():
    idx = {}
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ('.git', 'bin', 'obj', 'node_modules', '__pycache__')]
        for fn in files:
            idx.setdefault(fn, []).append(os.path.relpath(os.path.join(base, fn), ROOT))
    return idx


def form_of(cmd, m):
    seg = cmd[:m.start()].rstrip().rstrip('"\'( ')
    prev = seg.split()[-1] if seg.split() else ''
    if prev in WRITE_FLAGS or prev.endswith('>'):
        return 'write_out', prev
    if RUNNERS.match(prev):
        return 'read_dep', prev
    if prev.startswith('-'):
        return 'read_dep', prev
    if '=' in prev and not prev.startswith('-'):
        var = prev.split('=')[0]
        if any(h in var.upper() for h in ('OUT', 'JSON', 'REPORT', 'DIR')):
            return 'write_out', prev
        return 'read_dep', prev
    return 'unclassified', prev


def verdict_of(tok, form, field, idx, exists_today):
    """逐类裁定 (v2 口径)。"""
    if form == 'write_out':
        return 'ACCEPT_write_out_intermediate'
    if tok.rstrip('/') in ('/tmp', '/tmp/models') or any(tok.startswith(d) for d in EXTERNAL_DIRS) \
            or tok.endswith(EXTERNAL_SUFFIX):
        return 'ACCEPT_external_asset_or_build_output'
    if form == 'unclassified':
        return 'ABSTAIN_unclassified_form'
    bn = os.path.basename(tok.rstrip('/'))
    cands = idx.get(bn, [])
    strong = [c for c in cands if sha256(tok) and sha256(os.path.join(ROOT, c)) == sha256(tok)]
    if strong:
        return 'FIX_repo_identical_exists:%s' % strong[0]
    if field != 'evidence_cmd':
        return 'NOTE_text_ref_procedure'
    if not exists_today:
        return 'RED_single_copy_absent_now'
    return 'RED_single_copy_volatile'


def main():
    try:
        reg = json.load(open(os.path.join(ROOT, REG), encoding='utf-8-sig'))
    except Exception as e:
        print('ENV_FAIL: %r' % (e,))
        return 3
    rows, idx = reg['rows'], repo_index()
    pos = {'rows': len(rows),
           'evidence_cmd_nonempty': sum(1 for r in rows if r.get('evidence_cmd')),
           'evidence_cmd_has_eval': sum(1 for r in rows if 'eval/' in (r.get('evidence_cmd') or ''))}
    print('POSITIVE_CONTROL %s' % json.dumps(pos))
    if pos['evidence_cmd_has_eval'] == 0:
        print('CENSUS=VOID (正控失败)')
        return 2

    findings, reds, classes = [], [], {}
    for r in rows:
        for field in ('evidence_cmd', 'evidence_path', 'negative_control', 'covers'):
            val = r.get(field)
            if not val:
                continue
            blob = json.dumps(val, ensure_ascii=False)
            if '/tmp' not in blob:
                continue
            if field == 'evidence_cmd':
                occ = [(m.group(0).rstrip('.,;)\\'),) + form_of(val, m) for m in TMP_RE.finditer(val)]
            else:
                occ = []
                for m in TMP_RE.finditer(blob):
                    occ.append((m.group(0).rstrip('.,;)\\'), 'ref_text', ''))
            for tok, form, prev in occ:
                exists = os.path.exists(tok)
                v = verdict_of(tok, form, field, idx, exists)
                classes[v.split(':')[0]] = classes.get(v.split(':')[0], 0) + 1
                rec = {'id': r['id'], 'field': field, 'token': tok, 'form': form, 'exists_today': exists,
                       'verdict': v}
                findings.append(rec)
                if v.startswith('RED_'):
                    reds.append('%s:%s:%s' % (r['id'], field, tok))

    # 正面检查: evidence_cmd 里仓库内路径必须存在 (验证改指生效)
    repo_missing, repo_total = [], 0
    for r in rows:
        cmd = r.get('evidence_cmd') or ''
        for m in REPO_RE.finditer(cmd):
            t = m.group(0).rstrip('.,;)\\')
            p = os.path.join(ROOT, t)
            if os.path.exists(p):
                repo_total += 1
            elif os.path.splitext(t)[1] in ('.py', '.sh', '.tar', '.gz'):
                repo_missing.append('%s:%s' % (r['id'], t))

    payload = {'round': 'EXP1-Q32', 'schema': 'tmp-path-census/2', 'positive_control': pos,
               'classes': classes, 'n_findings': len(findings),
               'rows_with_tmp_evidence_cmd': sorted({f['id'] for f in findings if f['field'] == 'evidence_cmd'}),
               'reds': reds,
               'repo_path_refs_existing': repo_total, 'repo_path_refs_missing': repo_missing,
               'findings': findings}
    with open(os.path.join(ROOT, OUT), 'w', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False, indent=1) + '\n')
    print('CLASSES %s' % json.dumps(classes, ensure_ascii=False))
    print('ROWS_WITH_TMP_ANY %d  FINDINGS %d  REDS %d' % (len(payload['rows_with_tmp_evidence_cmd']),
                                                          len(findings), len(reds)))
    for x in reds:
        print('  RED %s' % x)
    print('REPO_PATH_REFS existing=%d missing=%d %s' % (repo_total, len(repo_missing), repo_missing[:8]))
    print('落盘 %s' % OUT)
    print('TMP_CENSUS=%s (v1 口径首跑红 11 → v2 口径红 %d)' % ('FAIL' if reds else 'OK', len(reds)))
    return 2 if reds else 0


if __name__ == '__main__':
    sys.exit(main())
