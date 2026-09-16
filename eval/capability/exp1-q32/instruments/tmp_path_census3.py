#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q32 · C1 census v3 (终口径): /tmp 逐行核查, 依赖面只取**可执行段**。

三代口径一律留在档 (v1 红 11 / v2 红 1 / v3):
  · v1 (`tmp_path_census.py`): 词面判据过宽 —— `negative_control` 里的目录字面量也判红 (同 AF.1 kernel32 缺陷族)。
  · v2 (`tmp_path_census2.py`): 分类学修正 (外部资产/写输出/文本引用分列), 但两处仪器缺陷:
      ① `/tmp` 正则在**路径内部**也命中 (`.../instruments/tmp_archive_restore.py` ⇒ 假阳);
      ② 未区分**注释段** ⇒ 本侧写进 cmd 的历史说明(`# 原声明 bash /tmp/…`)被当成活依赖 (自指实例)。
  · v3 (本文件): ① 路径边界断言 `(?<![\\w./\\-])/tmp`; ② evidence_cmd **剥注释**后再抽取依赖;
      ③ materialize 感知 (命令含归档还原步且该路径被 manifest 覆盖 ⇒ 判自足, 不判红)。
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
OUT = 'eval/capability/exp1-q32/tmp_path_census3_q32.json'
MANIFEST = 'eval/capability/exp1-q32/archived_tmp/manifest.json'
TMP_RE = re.compile(r'(?<![\w./\-])/tmp[A-Za-z0-9._/\-]*')
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


def strip_comments(cmd):
    """剥 shell 注释: ' #…' 起到行尾 (命令里 # 只作注释用; 保守: 仅剥前面有空白的 '#')。"""
    return '\n'.join(re.sub(r'\s+#.*$', '', ln) for ln in cmd.split('\n'))


def form_of(cmd, m):
    seg = cmd[:m.start()].rstrip().rstrip('"\'( ')
    prev = seg.split()[-1] if seg.split() else ''
    if prev in WRITE_FLAGS or prev.endswith('>'):
        return 'write_out', prev
    if RUNNERS.match(prev) or prev.startswith('-'):
        return 'read_dep', prev
    if '=' in prev and not prev.startswith('-'):
        var = prev.split('=')[0]
        return ('write_out' if any(h in var.upper() for h in ('OUT', 'JSON', 'REPORT', 'DIR'))
                else 'read_dep'), prev
    return 'unclassified', prev


def main():
    try:
        reg = json.load(open(os.path.join(ROOT, REG), encoding='utf-8-sig'))
    except Exception as e:
        print('ENV_FAIL: %r' % (e,))
        return 3
    man = json.load(open(os.path.join(ROOT, MANIFEST), encoding='utf-8')) if os.path.isfile(
        os.path.join(ROOT, MANIFEST)) else {'entries': []}
    mat_targets = {e['origin'] for e in man['entries']}
    rows, idx = reg['rows'], repo_index()
    pos = {'rows': len(rows),
           'evidence_cmd_nonempty': sum(1 for r in rows if r.get('evidence_cmd')),
           'evidence_cmd_has_eval': sum(1 for r in rows if 'eval/' in (r.get('evidence_cmd') or ''))}
    print('POSITIVE_CONTROL %s' % json.dumps(pos))
    if pos['evidence_cmd_has_eval'] == 0:
        print('CENSUS=VOID (正控失败 ⇒ 读数作废)')
        return 2

    findings, reds, classes = [], [], {}
    for r in rows:
        for field in ('evidence_cmd', 'evidence_path', 'negative_control', 'covers'):
            val = r.get(field)
            if not val or '/tmp' not in json.dumps(val, ensure_ascii=False):
                continue
            searchable = strip_comments(val) if field == 'evidence_cmd' else json.dumps(val, ensure_ascii=False)
            for m in TMP_RE.finditer(searchable):
                tok = m.group(0).rstrip('.,;)\\')
                form, prev = form_of(searchable, m) if field == 'evidence_cmd' else ('ref_text', '')
                exists = os.path.exists(tok)
                if form == 'write_out':
                    v = 'ACCEPT_write_out_intermediate'
                elif tok.rstrip('/') in ('/tmp', '/tmp/models') or tok.startswith(EXTERNAL_DIRS) \
                        or tok.endswith(EXTERNAL_SUFFIX):
                    v = 'ACCEPT_external_asset_or_build_output'
                elif form == 'unclassified':
                    v = 'ABSTAIN_unclassified_form'
                elif field == 'evidence_cmd' and 'tmp_archive_restore.py' in searchable and any(
                        tg == tok.rstrip('/') or tg.startswith(tok.rstrip('/') + '/')
                        or tok.rstrip('/') == os.path.dirname(tg) for tg in mat_targets):
                    v = 'OK_materialized_from_archive'
                else:
                    bn = os.path.basename(tok.rstrip('/'))
                    strong = [c for c in idx.get(bn, [])
                              if sha256(tok) and sha256(os.path.join(ROOT, c)) == sha256(tok)]
                    if strong:
                        v = 'OK_repo_identical:%s' % strong[0]
                    elif field != 'evidence_cmd':
                        v = 'NOTE_text_ref_procedure'
                    elif not exists:
                        v = 'RED_single_copy_absent_now'
                    else:
                        v = 'RED_single_copy_volatile'
                classes[v.split(':')[0]] = classes.get(v.split(':')[0], 0) + 1
                findings.append({'id': r['id'], 'field': field, 'token': tok, 'form': form,
                                 'exists_today': exists, 'verdict': v})
                if v.startswith('RED_'):
                    reds.append('%s:%s:%s' % (r['id'], field, tok))

    repo_missing, repo_total = [], 0
    for r in rows:
        for m in REPO_RE.finditer(r.get('evidence_cmd') or ''):
            t = m.group(0).rstrip('.,;)\\')
            if os.path.exists(os.path.join(ROOT, t)):
                repo_total += 1
            elif os.path.splitext(t)[1] in ('.py', '.sh'):
                repo_missing.append('%s:%s' % (r['id'], t))

    payload = {'round': 'EXP1-Q32', 'schema': 'tmp-path-census/3', 'positive_control': pos,
               'classes': classes, 'n_findings': len(findings), 'reds': reds,
               'repo_path_refs_existing': repo_total, 'repo_path_refs_missing': repo_missing,
               'caliber_note': 'v3 = 路径边界 + 剥注释 + materialize 感知; v1 红 11 / v2 红 1 / v3 见 reds',
               'findings': findings}
    with open(os.path.join(ROOT, OUT), 'w', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False, indent=1) + '\n')
    print('CLASSES %s' % json.dumps(classes, ensure_ascii=False))
    for x in reds:
        print('  RED %s' % x)
    print('REPO_PATH_REFS existing=%d missing=%d %s' % (repo_total, len(repo_missing), repo_missing[:8]))
    print('落盘 %s' % OUT)
    print('TMP_CENSUS=%s (v1 红 11 → v2 红 %d → v3 红 %d)'
          % ('FAIL' if reds else 'OK', 1, len(reds)))
    return 2 if reds else 0


if __name__ == '__main__':
    sys.exit(main())
