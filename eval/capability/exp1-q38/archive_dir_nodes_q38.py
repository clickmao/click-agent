#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q38 · 候选②: **目录结点**的归档形态 (自足性) —— Q37 遗留的 29 个 `directory_node` 裁定收口。

背景 (Q37 读数): depth-3 归档自足面把 155 个被扫结点裁成 archive 126 / live 29 / gone 0 ⇒「自足率」
0.8129, 而 29 件全部以 `not_archivable(reason=directory_node)` 结案 —— 即**目录结点从未被问过**
「它有没有可自足的归档形态」。本件即该问句的**独立预注册轮次** (Q37 的 disposition 一字不改; 本面单列)。

预注册 (写于取证前, 本文件即判据载体):
  P1 分母 = Q37 `disposition` 里 reason == 'directory_node' 的结点, 机检计数 (期望 29)。分母不符 ⇒ rc=3 弃权。
  P2 归档形态两态并列 (不是二选一):
     F-list : 只落**清单** (相对路径 / 字节数 / 文本性 / sha256) —— 不含内容;
     F-copy : **受限内容副本** —— 逐文件 ≤ CAP(262144 B)、逐结点预算 ≤ NODE_BUDGET(1 MiB)、
              走与 Q37 抽取器**同一遍历序** (os.walk 顶向下 + 逐目录文件名排序)。
  P3 判据 (成对; 缺一不可):
     c1 覆盖守恒: Σ(copy 完整 + copy 截断 + gone + unreadable) == 29 ∧ 每结点恰一个处置;
     c2 **可复算**: 对 F-copy 完整结点, 从其归档副本重跑抽取 ⇒ n_refs 与 Q37 现场读数**逐结点相等**;
     c3 **非平凡**: c2 比较面里 Σ n_refs > 0 (全零相等是空转, 不算证据);
     c4 **F-list 不足 (负控)**: 只按清单重建布局 (空文件、无内容) ⇒ n_refs 必须**小于**现场读数;
        对 Q37 n_refs > 0 的每个结点都必须严格小于 (若某结点相等 ⇒ 该处「清单够用」, 如实计数并单列);
     c5 **截断安全**: 被跳过的文件中「文本性 (抽取器口径内)」者的引用贡献必须为 0; 否则该结点移出 c2
        比较面并单列为 `truncated_risk` (不静默计入相等).
  P4 三态判决: 0 全绿 / 2 判据红 / 3 弃权 (分母不符 / 预算越界 / 源不可读)。
  P5 归档保真: 每个复制文件 sha256 读回 == 源 (逐件断言; 不符即判红)。
  P6 判据不放宽: c2 不等数 > 0 ⇒ 判红; 不把「归档不忠」降级成 warning。
  P7 判别力自证 (c2 不是空转判据): 取一个有引用的完整结点, 从副本里**摘掉一个带引用的文件** ⇒
     重跑 n_refs 必须**下降** (布尔读数 `c2_detects_removed_file`)。

口径同源: 抽取器 = Q37 模块的 `scan_refs` + Q34 模块的 `refs_in` (同一份代码, 不另写一份 ⇒ 无口径漂移)。
"""
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CAP_BYTES = 262144            # 逐文件上限
NODE_BUDGET = 1048576         # 逐结点上限
BUDGET_TOTAL = 32 * 1048576   # 全仓落盘守卫 (超 ⇒ 弃权, 不落盘)
Q37_REC = ROOT / 'eval/capability/exp1-q37/archive_selfsufficiency_q37.json'
ARCH = HERE / 'archived_deps_depth3_dirs'
OUT = HERE / 'archive_dir_nodes_q38.json'
LISTONLY = pathlib.Path('/tmp/q38_listonly')
REASONS = ('copy_complete', 'copy_truncated', 'gone', 'unreadable')
# 修订 (Q38 第二次运行, 由**凭据卫生**驱动, 不是为凑绿): 首跑把 5 个 `/tmp` 夹具密钥 (`data/master.key`,
#   32 B 随机字节) 逐字节复制进仓 ⇒ 与「凭据不入仓」纪律冲突。修订 = 名字命中即跳 (**不复制**),
#   跳过的件按「必须贡献 0 引用」计入 c5; 代价 = 该结点从「完整」变「截断」, 故等价面定义同步改为
#   「跳过的文本性/密钥件引用贡献 == 0 的结点」 (否则截断结点会被无条件逐出, 而它们的抽取结果其实未变)。
#   首跑读数原样保留在附录 AM (29/29 copy_complete) —— 两次读数并列, 不互相取代。
SECRET_RE = re.compile(r'(^|/)(id_[^/]*|[^/]*\.(pem|key|pfx|p12|jks|keystore|env|kdbx)|master\.key)$'
                       r'|token|secret|credential|password', re.I)


def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def slug(node, i):
    """确定性 + 无碰撞 (Q37 的 slug 对 '/tmp/x' 与 '/tmp/x/' 会撞名 ⇒ 追加短哈希)。"""
    base = node.strip('/').replace('/', '__') or 'root'
    return '%s__%s' % (base, hashlib.sha1(node.encode()).hexdigest()[:6])


def sha256(p):
    with open(p, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def walk_plan(node, q34):
    """与 Q37 抽取器同序的遍历计划 (顶向下 + 逐目录文件名排序 + 全局 MAX_SCAN_FILES 上限)。"""
    files, n = [], 0
    for dirpath, _dn, fns in os.walk(node):
        stop = False
        for fn in sorted(fns):
            if n >= q34.MAX_SCAN_FILES:
                stop = True
                break
            n += 1
            files.append(os.path.join(dirpath, fn))
        if stop:
            break
    return files


def build(node, q34, i):
    """落 F-copy + F-list, 返回 (row, node 内 skips 明细)。"""
    slugd = ARCH / slug(node, i)
    if slugd.exists():
        shutil.rmtree(slugd)
    listing, copied = [], 0
    if not os.path.isdir(node):
        return {'node': node, 'disposition': 'gone' if not os.path.exists(node) else 'unreadable',
                'slug': None, 'listing': [], 'copied_bytes': 0, 'skipped': []}, []
    skips = []
    budget = NODE_BUDGET
    for fp in walk_plan(node, q34):
        rel = os.path.relpath(fp, node)
        try:
            size = os.path.getsize(fp)
        except OSError:
            skips.append({'rel': rel, 'reason': 'unreadable'})
            continue
        ent = {'rel': rel, 'bytes': size}
        if SECRET_RE.search(rel):
            # 凭据卫生: 名字命中 ⇒ 不复制 (仍进清单, 便于读者知道「这里少了一件, 为什么少」)
            ent.update(textish=None, disposition='skipped_secret_like')
            listing.append(ent)
            skips.append({'rel': rel, 'reason': 'secret_like', 'bytes': size, 'textish': True})
            continue
        textish = bool(q34.is_textish(fp))
        ent['textish'] = textish
        if not textish:
            ent['disposition'] = 'skipped_nontext'      # 抽取器口径外 ⇒ 对 n_refs 贡献恒为 0
            listing.append(ent)
            continue
        if size > CAP_BYTES:
            ent['disposition'] = 'skipped_over_cap'
            skips.append({'rel': rel, 'reason': 'over_cap', 'bytes': size, 'textish': True})
            listing.append(ent)
            continue
        if size > budget:
            ent['disposition'] = 'skipped_budget'
            skips.append({'rel': rel, 'reason': 'node_budget', 'bytes': size, 'textish': True})
            listing.append(ent)
            continue
        dst = slugd / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fp, dst)
        back = sha256(dst)
        assert back == sha256(fp) and os.path.getsize(dst) == size, '归档保真失败: %s' % fp
        ent.update(disposition='copied', sha256=back)
        listing.append(ent)
        budget -= size
        copied += size
    row = {'node': node, 'slug': slug(node, i), 'listing': listing, 'copied_bytes': copied,
           'skipped': skips,
           'disposition': ('copy_truncated' if any(s.get('textish') for s in skips) else 'copy_complete')}
    return row, skips


def listonly_replay(node, row, q34):
    """F-list 负控: 按清单重建**布局**(空文件, 无内容) ⇒ 抽取结果必不完整。"""
    d = LISTONLY / row['slug']
    if d.exists():
        shutil.rmtree(d)
    for ent in row['listing']:
        dst = d / ent['rel']
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b'')
    got = []
    for dirpath, _dn, fns in os.walk(d):
        for fn in sorted(fns):
            r = q34.refs_in(os.path.join(dirpath, fn))
            if r:
                got.extend(r)
    return len(set(got))


def main():
    q37 = load_mod('q37_arch', ROOT / 'eval/capability/exp1-q37/archive_selfsufficiency_q37.py')
    q34 = q37.q34mod()
    rec = json.load(open(Q37_REC, encoding='utf-8'))
    nodes = [r['node'] for r in rec['disposition'] if r.get('reason') == 'directory_node']
    if len(nodes) != 29:
        print('DENOMINATOR_MISMATCH=%d (期望 29) ⇒ rc=3 弃权' % len(nodes))
        return 3

    # 预算守卫: 先算计划总量, 越界则一个字节都不落盘
    plan_bytes = 0
    for i, node in enumerate(sorted(nodes)):
        budget = NODE_BUDGET
        for fp in walk_plan(node, q34):
            try:
                size = os.path.getsize(fp)
            except OSError:
                continue
            if SECRET_RE.search(os.path.relpath(fp, node)):
                continue
            if q34.is_textish(fp) and size <= CAP_BYTES and size <= budget:
                plan_bytes += size
                budget -= size
    if plan_bytes > BUDGET_TOTAL:
        print('BUDGET_GUARD: 计划落盘 %d B > 上限 %d B ⇒ rc=3 弃权 (不落盘)' % (plan_bytes, BUDGET_TOTAL))
        return 3
    ARCH.mkdir(parents=True, exist_ok=True)
    print('PLAN_ARCHIVE_BYTES=%d (%.2f MiB, 上限 %d MiB)' % (plan_bytes, plan_bytes / 1048576,
                                                             BUDGET_TOTAL // 1048576))

    rows, per = [], {}
    for i, node in enumerate(sorted(nodes)):
        row, _skips = build(node, q34, i)
        rows.append(row)
        if row['disposition'] in ('gone', 'unreadable'):
            per[node] = {'n_refs': None, 'n_refs_listonly': None, 'q37_n_refs': rec['per_node'][node]['n_refs'],
                         'disposition': row['disposition']}
            continue
        arch = ARCH / row['slug']
        refs = set()
        for dirpath, _dn, fns in os.walk(str(arch)):
            for fn in sorted(fns):
                got = q34.refs_in(os.path.join(dirpath, fn))
                if got:
                    refs.update(got)
        per[node] = {'n_refs': len(refs), 'q37_n_refs': rec['per_node'][node]['n_refs'],
                     'n_refs_listonly': listonly_replay(node, row, q34),
                     'disposition': row['disposition'],
                     'skipped_textish': sum(1 for s in row['skipped'] if s.get('textish')),
                     'copied_bytes': row['copied_bytes']}
    if LISTONLY.exists():
        shutil.rmtree(LISTONLY)

    # c5: 被跳过的**文本性**文件在 live 侧的引用贡献 (必须为 0 才允许截断结点进 c2 面)
    skipped_contrib = {}
    for row in rows:
        tot, det = 0, []
        for s in row['skipped']:
            if not s.get('textish'):
                continue
            got = q34.refs_in(os.path.join(row['node'], s['rel']))
            n = 0 if not got else len(set(got))
            tot += n
            if n:
                det.append({'rel': s['rel'], 'refs': n})
        skipped_contrib[row['node']] = {'refs': tot, 'detail': det}

    # 修订后等价面 (第二次运行): 抽取结果可得 ∧ 该结点**所有**被跳过的文本性/密钥件引用贡献为 0。
    #   首跑的面定义是「disposition == copy_complete」; 修订是因为密钥件被显式跳过 (凭据卫生) ⇒
    #   5 个结点从「完整」变「截断」, 但它们的抽取结果并未改变 (贡献 0 已实测)。
    face = [n for n in sorted(nodes) if per[n].get('n_refs') is not None
            and skipped_contrib[n]['refs'] == 0]
    diffs = [{'node': n, 'q37_n_refs': per[n]['q37_n_refs'], 'rerun_n_refs': per[n]['n_refs']}
             for n in face if per[n]['n_refs'] != per[n]['q37_n_refs']]
    nonzero_face = [n for n in face if (per[n]['q37_n_refs'] or 0) > 0]
    list_violations = [n for n in nonzero_face if not (per[n]['n_refs_listonly'] < per[n]['q37_n_refs'])]
    trunc_risk = [n for n in sorted(nodes) if per[n]['disposition'] == 'copy_truncated'
                  and skipped_contrib[n]['refs'] > 0]

    # P7 判别力自证: 摘掉一个有引用的文件 ⇒ n_refs 必须下降
    c2_detect = None
    probe = next((n for n in nonzero_face), None)
    if probe:
        row = next(r for r in rows if r['node'] == probe)
        refs_by_file = [(e['rel'], len(set(q34.refs_in(str(ARCH / row['slug'] / e['rel'])) or [])))
                        for e in row['listing'] if e.get('disposition') == 'copied']
        victim = next((rel for rel, k in refs_by_file if k > 0), None)
        if victim:
            tmp = pathlib.Path('/tmp/q38_replay_minus_one')
            if tmp.exists():
                shutil.rmtree(tmp)
            shutil.copytree(str(ARCH / row['slug']), str(tmp))
            os.remove(str(tmp / victim))
            got = set()
            for dirpath, _dn, fns in os.walk(str(tmp)):
                for fn in sorted(fns):
                    r = q34.refs_in(os.path.join(dirpath, fn))
                    if r:
                        got.update(r)
            c2_detect = {'node': probe, 'removed': victim, 'n_refs': len(got),
                         'baseline': per[probe]['n_refs'], 'detects': len(got) < per[probe]['n_refs']}
            shutil.rmtree(tmp)

    by_disp = {}
    for row in rows:
        by_disp[row['disposition']] = by_disp.get(row['disposition'], 0) + 1
    conservation = {
        'c0_rows_eq_denominator': len(rows) == 29,
        'c1_dispositions_sum': sum(by_disp.values()) == 29,
        'c1b_dispositions_in_closed_set': all(k in REASONS for k in by_disp),
        'c2_rerun_equivalent_on_complete': not diffs,
        'c3_nontrivial_face': sum((per[n]['q37_n_refs'] or 0) for n in face) > 0,
        'c4_listonly_insufficient': not list_violations,
        'c5_truncation_safe': not trunc_risk,
        'p7_negative_control': bool(c2_detect and c2_detect['detects']),
    }
    ok = all(conservation.values())
    payload = {
        'round': 'EXP1-Q38', 'schema': 'archive-dir-nodes/1',
        'source': os.path.relpath(Q37_REC, ROOT), 'archive_root': os.path.relpath(ARCH, ROOT),
        'prereg': {'P1': '分母 = Q37 directory_node 结点 (29)', 'P2': 'F-list / F-copy 两态',
                   'P3': ['c1 守恒 29', 'c2 完整结点重跑逐结点等价', 'c3 非平凡 Σn_refs>0',
                          'c4 清单不足(负控)', 'c5 截断安全(文本贡献=0)'],
                   'P4': '0 全绿 / 2 判据红 / 3 弃权', 'P7': '摘文件 ⇒ n_refs 必降'},
        'denominator': len(nodes), 'by_disposition': by_disp,
        'face_definition': ('抽取可得 ∧ 被跳过件(含密钥件)引用贡献 == 0 (修订版; 首跑面定义 = copy_complete)'),
        'secret_like_skipped': sum(1 for r in rows for s in r['skipped'] if s.get('reason') == 'secret_like'),
        'archive_bytes_total': sum(r['copied_bytes'] for r in rows),
        'plan_bytes': plan_bytes,
        'equivalence_face_n': len(face), 'equivalence_face_nonzero_n': len(nonzero_face),
        'rerun_equivalence_diff': diffs, 'listonly_violations': list_violations,
        'truncated_risk': trunc_risk, 'skipped_ref_contribution': skipped_contrib,
        'negative_control_remove_file': c2_detect,
        'per_node': per, 'disposition': [{k: v for k, v in r.items() if k != 'listing'} for r in rows],
        'conservation': conservation,
        'note': ('目录结点此前只以「不可归档」结案; 本面证明**受限内容副本**可复算 (逐结点等价), '
                 '而**只落清单**在原理上不够 (c4)。被跳过的非文本文件在抽取器口径外 (贡献恒 0), '
                 '文本性跳过件必须贡献为 0 才允许该结点留在等价面 (c5)。'),
    }
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    print('DIR-NODES denom=%d by_disp=%s archive_bytes=%d' % (len(nodes), by_disp, payload['archive_bytes_total']))
    print('EQUIVALENCE face=%d (nonzero=%d) diff=%d listonly_violations=%d trunc_risk=%d'
          % (len(face), len(nonzero_face), len(diffs), len(list_violations), len(trunc_risk)))
    print('NEG-CONTROL remove_file: %s' % (c2_detect,))
    print('CONSERVATION %s' % conservation)
    print('VERDICT=%s out=%s' % ('PASS' if ok else 'FAIL', os.path.relpath(OUT, ROOT)))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
