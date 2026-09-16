#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q35 · 候选③: 87 件「不可入库裁定」的 license 逐件复核。

Q34 的裁定表把外部件许可记为 `unasserted`(未主张) —— 这是**结构占位**, 不是复核结论。
本器具把 `license` 从人读占位升级为**逐件可机检**读数:

  许可证据来源 (按优先级, 全部要求盘上真实文本):
    E1 `.deps.json` / `.nuspec` / `.nupkg` 在同目录内 ⇒ 直接解析其包清单与许可表达式;
    E2 首方构建产物 (发布目录含本仓程序集名/pdb) ⇒ 第三方闭包取**该工程** `obj/project.assets.json`
       的包清单 (Name/Version), 逐包在 NuGet 缓存解析 `<license type="expression">` 或 `<licenseUrl>`;
    E3 目录内含第三方许可文本 (LICENSE/COPYING/NOTICE) ⇒ 逐文件判型 (MIT/Apache-2.0/...);
    E4 以上皆无 ⇒ 首方探针产物 (本仓轮次脚本/证据) ⇒ 许可 = 本仓 LICENSE (MIT), 证据 = LICENSE 字节 sha。

  三态判决 (ticket: 缺证据 = 弃权单列, 不判红也不冒充 resolved):
    resolved     : 无 unresolved 且有 >=1 许可标识
    partial      : 有 unresolved (逐条列出)
    no_evidence  : 无任何可用证据面 (件已消失 / 全不可解析)

  判据 (预注册 D3/D3n):
    · 件数守恒: n_resolved + n_partial + n_no_evidence == 裁定表件数;
    · 非恒 no_evidence: resolved+partial > 0;
    · 双控: 正控 (含 nuspec + LICENSE 文本的目录) 必须解出 >=1 许可标识;
            负控 (清空目录) 必须落 no_evidence 且 license_ids 为空 (禁编造);
            第三控 (引用不存在包) 必须落 partial 且 unresolved 点名该包。
    · 字节漂移: 逐件复测 bytes 与 Q34 记录比对 (不同记 bytes_drift, 属对象变化不是许可问题)。

退出码: 0 全过 / 2 判据红 / 3 弃权 (语料不可读)。
"""
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(HERE) != 'exp1-q35':      # 允许在 /tmp 开发期运行
    HERE = os.path.dirname(HERE)
ROOT = None
for cand in (os.path.dirname(os.path.dirname(HERE)),):
    if os.path.isdir(os.path.join(cand, 'src')) and os.path.isdir(os.path.join(cand, 'eval')):
        ROOT = cand
if ROOT is None:
    ROOT = os.getcwd()
SRC = os.path.join(ROOT, 'eval/capability/exp1-q34/deps_depth2_q34.json')
OUT = os.path.join(ROOT, 'eval/capability/exp1-q35/license_audit_q35.json')
NUGET = os.path.expanduser('~/.nuget/packages')
MAX_SCAN_FILES = 5000

LICENSE_IDS = ('mit', 'apache-2.0', 'bsd-2-clause', 'bsd-3-clause', 'mpl-2.0', 'ms-pl',
               'gpl-2.0', 'gpl-3.0', 'lgpl-2.1', 'lgpl-3.0', 'isc', 'unlicense', 'other')
TEXT_MARKERS = ('LICENSE', 'COPYING', 'NOTICE', 'THIRD-PARTY', 'THIRDPARTY')
PKG_MARKERS = ('.nuspec', '.nupkg', '.deps.json', '.gguf', '.whl', 'package.json')
# 首方产物文件类型 (本仓轮次产出: 代码/证据/文档/配置/调试符号) —— 仅用于「无第三方包标记」时的首方归属
PROVENANCE_MARKERS = ('.py', '.md', '.stdout', '.json', '.txt', '.sh', '.pdb', '.yaml', '.yml',
                      '.toml', '.csv', '.log', '.db', '.err', '.inprogress')

_URL_MAP = {
    'licenses.nuget.org/mit': 'mit', 'opensource.org/licenses/mit': 'mit',
    'apache.org/licenses/license-2.0': 'apache-2.0',
    'opensource.org/licenses/apache-2.0': 'apache-2.0',
    'opensource.org/licenses/bsd-3-clause': 'bsd-3-clause',
    'opensource.org/licenses/bsd-2-clause': 'bsd-2-clause',
    'mozilla.org/mpl/2.0': 'mpl-2.0', 'opensource.org/licenses/mpl-2.0': 'mpl-2.0',
    'opensource.org/licenses/ms-pl': 'ms-pl',
    'gnu.org/licenses/old-licenses/gpl-2.0': 'gpl-2.0', 'gnu.org/licenses/gpl-3.0': 'gpl-3.0',
    'gnu.org/licenses/old-licenses/lgpl-2.1': 'lgpl-2.1', 'gnu.org/licenses/lgpl-3.0': 'lgpl-3.0',
    'opensource.org/licenses/isc': 'isc', 'unlicense.org': 'unlicense',
}


def sha256_file(p, limit=8 * 1024 * 1024):
    h = hashlib.sha256()
    n = 0
    with open(p, 'rb') as fh:
        while True:
            b = fh.read(1 << 16)
            if not b:
                break
            h.update(b)
            n += len(b)
            if n >= limit:
                break
    return h.hexdigest()


def norm_license_token(tok):
    """把许可表达式/URL/文本首行 归一化到闭集; 无法归一 ⇒ 'other:<原文前 24>'. """
    t = (tok or '').strip().strip('"').strip()
    if not t:
        return None
    low = t.lower()
    if low in LICENSE_IDS:
        return low
    for key, val in _URL_MAP.items():
        if key in low:
            return val
    for cid in LICENSE_IDS:
        if low.startswith(cid) or low == cid:
            return cid
    if 'mit' in low and 'license' in low:
        return 'mit'
    if 'apache' in low:
        return 'apache-2.0'
    if 'bsd' in low and '3' in low:
        return 'bsd-3-clause'
    if 'bsd' in low and '2' in low:
        return 'bsd-2-clause'
    if 'mozilla public' in low or low == 'mpl-2.0':
        return 'mpl-2.0'
    if 'microsoft public license' in low:
        return 'ms-pl'
    return 'other:' + t[:24]


def classify_license_text(first_kb):
    """许可**文本**判型 (只在文件名像许可时调用)。"""
    head = first_kb[:1200].lower()
    if 'mit license' in head or 'permission is hereby granted, free of charge' in head:
        return 'mit'
    if 'apache license' in head and '2.0' in head:
        return 'apache-2.0'
    if 'mozilla public license' in head:
        return 'mpl-2.0'
    if 'gnu general public license' in head:
        if 'version 3' in head:
            return 'gpl-3.0'
        if 'version 2' in head:
            return 'gpl-2.0'
        return 'other:gpl-unknown-version'
    if 'redistribution and use in source and binary forms' in head:
        return 'bsd-3-clause' if 'neither the name' in head else 'bsd-2-clause'
    if 'microsoft public license' in head:
        return 'ms-pl'
    if 'isc license' in head:
        return 'isc'
    if 'this is free and unencumbered software released into the public domain' in head:
        return 'unlicense'
    return 'other:text-unrecognized'


def nuspec_license(path):
    """从 nuspec 取许可: 优先 <license type="expression">, 退回 <licenseUrl>。"""
    try:
        raw = open(path, encoding='utf-8', errors='replace').read()
    except OSError:
        return None, None
    m = re.search(r'<license[^>]*type="expression"[^>]*>\s*([^<]+?)\s*</license>', raw, re.I)
    if m:
        return norm_license_token(m.group(1)), ('nuspec-expression', path)
    m = re.search(r'<licenseUrl>\s*([^<]+?)\s*</licenseUrl>', raw, re.I)
    if m:
        return norm_license_token(m.group(1)), ('nuspec-url', path)
    m = re.search(r'<license[^>]*>\s*([^<]+?)\s*</license>', raw, re.I)
    if m:
        return norm_license_token(m.group(1)), ('nuspec-generic', path)
    return None, None


def package_closure_for(project_dir):
    """读工程 obj/project.assets.json 的包清单 (Name/Version)。"""
    ap = os.path.join(project_dir, 'obj/project.assets.json')
    if not os.path.exists(ap):
        return None
    try:
        d = json.load(open(ap, encoding='utf-8'))
    except ValueError:
        return None
    out = []
    for k, v in (d.get('libraries') or {}).items():
        if isinstance(v, dict) and v.get('type') == 'package':
            if '/' in k:
                nm, ver = k.rsplit('/', 1)
                out.append((nm, ver))
    return sorted(out)


def repo_projects():
    """src/* 下含 obj/project.assets.json 的工程 (名 → 目录)。"""
    out = {}
    srcroot = os.path.join(ROOT, 'src')
    if not os.path.isdir(srcroot):
        return out
    for nm in sorted(os.listdir(srcroot)):
        p = os.path.join(srcroot, nm)
        if os.path.isdir(os.path.join(p, 'obj')):
            out[nm.lower()] = p
    return out


def walk_files(path, limit=MAX_SCAN_FILES):
    """对有界文件集做扫描; 返回 (文件列表, 是否截断)。目录不存在返回 None。"""
    if not os.path.exists(path):
        return None, False
    if os.path.isfile(path):
        return [path], False
    fs, truncated = [], False
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules')]
        for f in files:
            fs.append(os.path.join(root, f))
            if len(fs) >= limit:
                truncated = True
                return fs, truncated
    return fs, truncated


def repo_file_index(subdirs=('config',), limit_bytes=1 << 20):
    """仓内小文件 (名, 字节) → (相对路径, sha256) 索引 —— 用于「逐字节副本」式的首方归属。"""
    idx = {}
    for sub in subdirs:
        base = os.path.join(ROOT, sub)
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in ('.git', 'obj', 'bin', 'node_modules')]
            for f in files:
                p = os.path.join(root, f)
                try:
                    sz = os.path.getsize(p)
                except OSError:
                    continue
                if sz > limit_bytes:
                    continue
                idx[(f, sz)] = (os.path.relpath(p, ROOT), sha256_file(p, limit_bytes))
    return idx


def audit_item(dep, payload, projects, repo_cfg=None, nuget=NUGET):
    rec = {'dep': dep, 'kind': payload.get('kind'), 'bytes_recorded': payload.get('bytes'),
           'bytes_measured': None, 'bytes_drift': None, 'license_ids': [], 'unresolved': [],
           'evidence': [], 'state': None, 'why': None, 'provenance': []}
    fs, truncated = walk_files(dep)
    if fs is None:
        rec.update(state='no_evidence', why='gone_at_audit_time')
        return rec
    rec['n_files_scanned'] = len(fs)
    rec['scan_truncated'] = truncated
    total = 0
    text_hits, pkg_hits, prov_hits = [], [], []
    for f in fs:
        try:
            total += os.path.getsize(f)
        except OSError:
            continue
        base = os.path.basename(f).upper()
        if any(m in base for m in TEXT_MARKERS):
            text_hits.append(f)
        if any(f.lower().endswith(m) or m in os.path.basename(f).lower() for m in PKG_MARKERS):
            pkg_hits.append(f)
        if any(f.lower().endswith(m) for m in PROVENANCE_MARKERS):
            prov_hits.append(f)
    rec['bytes_measured'] = total
    if payload.get('bytes') is not None and total != payload.get('bytes'):
        rec['bytes_drift'] = {'recorded': payload.get('bytes'), 'measured': total}

    ids, unresolved = set(), []
    # E1: 同目录的 nuspec / deps.json
    for f in pkg_hits:
        if f.lower().endswith('.nuspec'):
            lid, ev = nuspec_license(f)
            if lid:
                ids.add(lid)
                rec['evidence'].append({'kind': 'in-dir-nuspec', 'path': f, 'license': lid})
        if f.lower().endswith('.deps.json'):
            try:
                dd = json.load(open(f, encoding='utf-8'))
            except ValueError:
                continue
            libs = [k for k in (dd.get('libraries') or {}) if '/' in k]
            for k in libs:
                nm, ver = k.rsplit('/', 1)
                spec = os.path.join(nuget, nm.lower(), ver, nm.lower() + '.nuspec')
                lid, ev = nuspec_license(spec)
                if lid:
                    ids.add(lid)
                    rec['evidence'].append({'kind': 'deps.json->nuget-nuspec', 'path': spec, 'pkg': k,
                                            'license': lid})
                elif ver.lower() != 'project':
                    unresolved.append(k)
    # E2: 首方构建产物 ⇒ 工程包闭包 (**并集**, 不取首个: 发布目录含主件与全部被引程序集/pdb)
    matched = {}
    for f in fs:
        nm = os.path.basename(f).lower()
        cand = None
        if nm.startswith('agenthost'):
            cand = projects.get('agent.host')
        elif nm.startswith('agent.') and nm.count('.') >= 2:
            cand = projects.get('agent.' + nm.split('.')[1])
        if cand:
            matched[os.path.relpath(cand, ROOT)] = cand
    closure_all = {}
    for key, cand in sorted(matched.items()):
        cl = package_closure_for(cand)
        if not cl:
            continue
        rec['provenance'].append({'evidence_kind': 'first-party-build-of', 'project': key,
                                  'n_packages': len(cl)})
        for nm2, ver in cl:
            closure_all[(nm2, ver)] = True
    for (nm2, ver) in sorted(closure_all):
        spec = os.path.join(nuget, nm2.lower(), ver, nm2.lower() + '.nuspec')
        lid, ev = nuspec_license(spec)
        if lid:
            ids.add(lid)
            rec['evidence'].append({'kind': 'project-closure->nuget-nuspec', 'path': spec,
                                    'pkg': nm2 + '/' + ver, 'license': lid})
        else:
            unresolved.append(nm2 + '/' + ver)
    # E3: 目录内第三方许可文本
    for f in text_hits:
        try:
            first = open(f, 'rb').read(2048).decode('utf-8', 'replace')
        except OSError:
            continue
        lid = classify_license_text(first)
        ids.add(lid)
        rec['evidence'].append({'kind': 'in-dir-license-text', 'path': f, 'license': lid,
                                'sha256': sha256_file(f, 1 << 20)})
    # E4: 首方产物 ⇒ 本仓 LICENSE。先试「逐字节副本」归属 (最强), 再退回文件类型归属。
    if repo_cfg:
        for f in fs:
            try:
                sz = os.path.getsize(f)
            except OSError:
                continue
            hit = repo_cfg.get((os.path.basename(f), sz))
            if not hit:
                continue
            if sha256_file(f, 1 << 20) == hit[1]:
                rec['provenance'].append({'evidence_kind': 'repo-identical-file', 'file': f,
                                          'repo_path': hit[0], 'sha256': hit[1]})
    if prov_hits and not pkg_hits:
        lic = os.path.join(ROOT, 'LICENSE')
        if os.path.exists(lic):
            ids.add('mit')
            rec['evidence'].append({'kind': 'repo-license(first-party-output)',
                                    'path': 'LICENSE', 'license': 'mit',
                                    'sha256': sha256_file(lic, 1 << 20)})
        rec['provenance'].append({'evidence_kind': 'first-party-probe-output', 'n_files': len(prov_hits)})

    rec['license_ids'] = sorted(ids)
    rec['unresolved'] = sorted(set(unresolved))
    # 证据档位**分开报** (字段存在性 ≠ 非空): strong-text = 盘上许可文本/nuspec 表达式;
    #   rule-based = 仅靠「首方产物 + 本仓 LICENSE」规则归属 (无第三方许可文本在场)。
    strong = [e for e in rec['evidence'] if e['kind'] != 'repo-license(first-party-output)']
    rec['evidence_grade'] = 'strong-text' if strong else ('rule-based-first-party' if ids else None)
    if not ids and unresolved:
        rec.update(state='partial', why='packages_unresolved_no_text_evidence')
    elif not ids:
        rec.update(state='no_evidence', why='no_license_evidence_in_tree')
    elif unresolved:
        rec.update(state='partial', why='some_packages_unresolved')
    else:
        rec.update(state='resolved', why=None)
    return rec


def controlled_controls(tmp=nuspec_license):
    """D3n 双控: 正控 (nuspec+LICENSE 文本) / 负控 (空目录) / 第三控 (缺失包)。"""
    base = tempfile.mkdtemp(prefix='q35_lic_ctl_')
    pos = os.path.join(base, 'pos')
    empty = os.path.join(base, 'empty')
    misspkg = os.path.join(base, 'missing')
    os.makedirs(pos)
    os.makedirs(empty)
    os.makedirs(misspkg)
    real = os.path.join(NUGET, 'anglesharp/1.4.0/anglesharp.nuspec')
    if os.path.exists(real):
        shutil.copy(real, os.path.join(pos, 'vendor.nuspec'))
    with open(os.path.join(pos, 'LICENSE'), 'w', encoding='utf-8') as fh:
        fh.write('MIT License\n\nPermission is hereby granted, free of charge, to any person.\n')
    with open(os.path.join(pos, 'probe.py'), 'w', encoding='utf-8') as fh:
        fh.write('print(1)\n')
    with open(os.path.join(misspkg, 'app.deps.json'), 'w', encoding='utf-8') as fh:
        json.dump({'libraries': {'totally.absent.package/9.9.9': {'type': 'package'}}}, fh)
    projects = repo_projects()
    r_pos = audit_item(pos, {'kind': 'directory', 'bytes': None}, projects)
    r_empty = audit_item(empty, {'kind': 'directory', 'bytes': 0}, projects)
    r_miss = audit_item(misspkg, {'kind': 'directory', 'bytes': None}, projects)
    checks = {
        'positive_resolved': (r_pos['state'] == 'resolved' and len(r_pos['license_ids']) >= 1),
        'negative_no_evidence': (r_empty['state'] == 'no_evidence' and not r_empty['license_ids']),
        'missing_pkg_partial_named': (r_miss['state'] == 'partial'
                                      and any('totally.absent.package' in u for u in r_miss['unresolved'])),
        'nontrivial_distinct': len({tuple(r_pos['license_ids']), tuple(r_empty['license_ids']),
                                    tuple(r_miss['license_ids'])}) >= 2,
    }
    shutil.rmtree(base, ignore_errors=True)
    return {'positive': r_pos, 'negative_empty': r_empty, 'negative_missing_pkg': r_miss, 'checks': checks}


def run(out_path=OUT):
    doc_src = json.load(open(SRC, encoding='utf-8'))
    ext = doc_src['external_dispositions']
    projects = repo_projects()
    repo_cfg = repo_file_index()
    rows = []
    for e in ext:
        rows.append(audit_item(e['dep'], e['disposition'], projects, repo_cfg))
    states = {'resolved': 0, 'partial': 0, 'no_evidence': 0}
    for r in rows:
        states[r['state']] += 1
    ids_all = {}
    for r in rows:
        for lid in r['license_ids']:
            ids_all[lid] = ids_all.get(lid, 0) + 1
    deps = [r['dep'] for r in rows]
    dupes = sorted({d for d in deps if deps.count(d) > 1})
    nested = sorted({(a, b) for a in set(deps) for b in set(deps)
                     if a != b and b.rstrip('/').startswith(a.rstrip('/') + '/')})
    conservation = {
        'n_items': len(rows),
        'sum_states_eq_n': sum(states.values()) == len(rows),
        'states': states,
        'n_non_no_evidence': states['resolved'] + states['partial'],
        'n_distinct_dep': len(set(deps)),
        'duplicate_rows': {d: deps.count(d) for d in dupes},
        'nested_pairs': len(nested),
        'nested_sample': [list(x) for x in nested[:6]],
        'bytes_drift_rows': sum(1 for r in rows if r['bytes_drift']),
        'n_unresolved_pkg_mentions': sum(len(r['unresolved']) for r in rows),
    }
    ctl = controlled_controls()
    ctl_ok = all(ctl['checks'].values())
    grades = {}
    for r in rows:
        g = r.get('evidence_grade') or 'none'
        grades[g] = grades.get(g, 0) + 1
    verdict = 'PASS' if (conservation['sum_states_eq_n'] and conservation['n_non_no_evidence'] > 0
                         and ctl_ok) else 'FAIL'
    doc = {'schema': 'license-audit/1', 'round': 'EXP1-Q35', 'source': os.path.relpath(SRC, ROOT),
           'nuget_cache': NUGET, 'nugget_cache_present': os.path.isdir(NUGET),
           'license_closed_set': list(LICENSE_IDS) + ['mit(first-party repo LICENSE)'],
           'conservation': conservation, 'license_id_histogram': ids_all,
           'evidence_grade_histogram': grades,
           'distinct_packages_resolved': len({e['pkg'] for r in rows for e in r['evidence']
                                              if 'pkg' in e}),
           'controls': {'checks': ctl['checks'],
                        'positive': {k: ctl['positive'][k] for k in ('state', 'license_ids', 'evidence')},
                        'negative_empty': {k: ctl['negative_empty'][k] for k in ('state', 'license_ids')},
                        'negative_missing_pkg': {k: ctl['negative_missing_pkg'][k] for k in
                                                 ('state', 'license_ids', 'unresolved')}},
           'verdict': verdict, 'rows': rows,
           'rule': ('许可标识只能来自盘上真实文本 (nuspec 表达式 / 许可正文 / 本仓 LICENSE); '
                    '缺证据 ⇒ no_evidence 弃权单列; unresolved 点名到包级; '
                    'bytes 逐件复测与 Q34 记录比对 (漂移单列)。')}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    print('LICENSE_AUDIT n=%d states=%s histogram=%s' % (len(rows), states, ids_all))
    print('CONTROLS %s' % ctl['checks'])
    print('CONSERVATION sum_states_eq_n=%s non_no_evidence=%d'
          % (conservation['sum_states_eq_n'], conservation['n_non_no_evidence']))
    print('VERDICT=%s out=%s' % (verdict, out_path))
    return 0 if verdict == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(run(sys.argv[1] if len(sys.argv) > 1 else OUT))
