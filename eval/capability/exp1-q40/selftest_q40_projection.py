#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q40 · 候选② 成对控制: 「pin_kind=semantic-projection 行的分类与工作区脏净解耦」。

判据 (预注册见 eval/capability/exp1-q40/prereg_q40.json H1–H3)：
  H2 (缺陷复现, 前态器具, HEAD 版本): 该行记录未入库/字节漂移 ⇒ 分类落到 live/worktree-only ⇒
     投影复算前提不成立 ⇒ **被跳过** (PROJ_PIN_SKIPPED=1) 且 audited_by_round 未变
     —— 这就是 AN.4.3 的「记录 → 重审」次序依赖 (必须先提交记录才敢重审)。
  H1 (修复生效, 现盘器具): 同态 ⇒ 仍按**声明语义**判 frozen/artifact ∧ 投影摘要可复算 ⇒
     该行被真实重审 (audited_by_round == EXP1-Q40 ∧ pin_kind 保留)。
  H3 (脏/净同值): 同一记录的两态 (入库字节 / 重排版字节 / 顶层键序反转) ⇒ 投影摘要**逐字符相同**,
     且等于登记表里已登记的那个值 (跨态、跨路径同口径)。
  成对控制 (C4): 同 scratch 上的**非投影**干净行 ⇒ 前/后态器具逐字段相同 (零回归; ② 只作用于声明行)。

夹具纪律: 登记表一律走 /tmp scratch (真登记表零写入); 唯一触碰的真件 = ③ 夹具列出的**已跟踪且脏**件
(与 ② 无关), 本脚本对真件只做「读 + 原字节复原 + 复原后 sha 断言」, 不改语义、不留痕。
退出码: 0 全绿 / 2 判据红 / 3 弃权。
"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
REG = 'docs/verification-registry.json'
TOOL = 'eval/capability/bind_evidence.py'
REAL_RECORD = 'eval/capability/instruments-check.json'   # r444 行声明的记录 (已跟踪)
REAL_ROW = 'r444.instrument-acceptance'
HERE = pathlib.Path(__file__).resolve().parent
SCRATCH = pathlib.Path('/tmp/q40_proj_scratch')
NC_ID = 'nc.q40.projection-dirty'
ROUND = 'EXP1-Q40'
REGISTERED_PIN = None                                    # 运行期从登记表读, 不手打


def sha(b):
    return hashlib.sha256(b).hexdigest()


def sh12(b):
    return sha(b)[:12]


def run(args, env=None):
    e = dict(os.environ)
    e['PYTHONPATH'] = os.path.join(ROOT, 'eval', 'capability')
    if env:
        e.update(env)
    p = subprocess.run(['python3'] + args, cwd=ROOT, capture_output=True, text=True, env=e)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def registry_with(path, extra_rows, ids=None):
    """真登记表**解析后重排**成 scratch (语义复制: 缩进/键序与真件一致, 便于器具的 SER_ASSERT 通过)。"""
    raw = open(os.path.join(ROOT, REG), encoding='utf-8').read()
    doc = json.loads(raw)
    if ids is not None:
        doc['rows'] = [r for r in doc['rows'] if r.get('id') in ids]
    doc['rows'].extend(extra_rows)
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding='utf-8', newline='')


def row_of(path, rid):
    return next(r for r in json.loads(pathlib.Path(path).read_text(encoding='utf-8'))['rows']
                if r['id'] == rid)


def main():
    global REGISTERED_PIN
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True)

    reg = json.loads(open(os.path.join(ROOT, REG), encoding='utf-8').read())
    r444 = next(r for r in reg['rows'] if r['id'] == REAL_ROW)
    REGISTERED_PIN = r444['evidence_generated_with']['artifact_sha12']
    rec_path = os.path.join(ROOT, REAL_RECORD)
    rec_raw = pathlib.Path(rec_path).read_bytes()
    rec_before_sha = sha(rec_raw)
    doc0 = json.loads(rec_raw.decode('utf-8'))          # H1/H2 用的「语义不变的重排版」源
    print('FIXTURE record=%s registered_pin=%s rec_sha=%s' % (REAL_RECORD, REGISTERED_PIN,
                                                             rec_before_sha[:12]))

    pre = SCRATCH / 'bind_evidence_prefix.py'
    blob = subprocess.run(['git', 'show', 'HEAD:%s' % TOOL], cwd=ROOT, capture_output=True)
    assert blob.returncode == 0, 'HEAD 无该件'
    pre.write_bytes(blob.stdout)
    print('TOOL_PRE_SHA12=%s TOOL_NOW_SHA12=%s (must differ)'
          % (sh12(blob.stdout), sh12(pathlib.Path(os.path.join(ROOT, TOOL)).read_bytes())))

    # scratch 记录 (未入库 ⇒ 与「字节漂移」同属「现盘 ≠ 归档」一类触发态)
    sc_rec = SCRATCH / 'scratch_record.json'
    sc_rec.write_bytes(rec_raw)
    sc_ev_rel = str(sc_rec)                                  # 绝对路径 (不在归档树 ⇒ tracked=false)
    fixture_row = {
        "id": NC_ID, "owner_round": "EXP1-Q40", "level": "L2",
        "capability": "EXP1-Q40 夹具行: 声明 semantic-projection 的记录未入库 (非产品能力)",
        "evidence_cmd": "python3 eval/capability/exp1-q40/selftest_q40_projection.py",
        "evidence_path": sc_ev_rel,
        "evidence_generated_with": {
            "evidence_kind": "artifact", "pin_status": "frozen", "pin_reason": "archived-per-round",
            "pin_kind": "semantic-projection", "artifact_sha12": REGISTERED_PIN,
            "instrument": None, "instrument_sha12": None, "binding": "audit-pin",
            "audited_by_round": "EXP1-Q39",
        },
        "negative_control": "同一 scratch 上把记录换成不合法 JSON ⇒ 投影复算失败 ⇒ --check 判红 (C3)",
        "covers": [sc_ev_rel], "note": "夹具行: 只活在 /tmp scratch 登记表",
    }

    checks, detail = {}, {}

    # ---- H1/H2: 声明 semantic-projection 的行, 记录**已入库但字节漂移** (AN.4.3 的次序依赖态)
    #   真件临时重排版 (语义不变) ⇒ 触发「现盘 ≠ 归档」; finally 原字节复原 + sha 断言。
    try:
        pathlib.Path(rec_path).write_bytes(variants_pending := (json.dumps(doc0, ensure_ascii=False,
                                                                          indent=2) + "\n").encode('utf-8'))
        st = subprocess.run(['git', 'status', '--porcelain', '--', REAL_RECORD], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
        for tag, tool in (('pre', str(pre)), ('post', TOOL)):
            r1 = SCRATCH / ('reg_h_%s.json' % tag)
            registry_with(r1, [], ids=[REAL_ROW])
            rc, out = run([tool, '--apply', '--only', REAL_ROW, '--round', ROUND, '--registry', str(r1)])
            f = row_of(r1, REAL_ROW)['evidence_generated_with']
            d = {'rc': rc, 'pin_status': f['pin_status'], 'reason': f['pin_reason'],
                 'artifact_sha12': f['artifact_sha12'], 'pin_kind': f.get('pin_kind'),
                 'audited_by_round': f['audited_by_round'],
                 'proj_skip_line': ('PROJ_PIN_SKIPPED=1' in out),
                 'git_status': st}
            detail['H_%s' % tag] = d
            if tag == 'pre':
                checks['H2_pre_dirty_record_reaudit_refused(次序依赖复现)'] = (
                    d['audited_by_round'] == 'EXP1-Q39' and d['artifact_sha12'] == REGISTERED_PIN)
            else:
                checks['H1_post_dirty_record_reaudited_same_pin(解耦生效)'] = (
                    d['audited_by_round'] == ROUND and d['artifact_sha12'] == REGISTERED_PIN
                    and d['pin_kind'] == 'semantic-projection' and d['pin_status'] == 'frozen')
    finally:
        pathlib.Path(rec_path).write_bytes(rec_raw)
        after = sha(pathlib.Path(rec_path).read_bytes())
        st2 = subprocess.run(['git', 'status', '--porcelain', '--', REAL_RECORD], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
        detail['H_restore'] = {'sha_before': rec_before_sha[:12], 'sha_after': after[:12],
                               'byte_identical': after == rec_before_sha, 'git_status': st2}
        checks['H_real_record_restored_byte_identical'] = (after == rec_before_sha and not st2)

    # ---- H3: 脏/净同值 (同一记录的三种字节形态) --------------------------------------
    sys.path.insert(0, os.path.join(ROOT, 'eval', 'capability'))
    import face_record_canon as frc
    doc = json.loads(rec_raw.decode('utf-8'))
    doc0 = doc
    variants = {
        'clean_committed': rec_raw,
        'dirty_reindent': (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode('utf-8'),
        'dirty_keyorder': (json.dumps(dict(reversed(list(doc.items()))), ensure_ascii=False,
                                      indent=1) + "\n").encode('utf-8'),
    }
    digs = {}
    for name, b in variants.items():
        p = SCRATCH / (name + '.json')
        p.write_bytes(b)
        dg, _ = frc.proj_digest_file(str(p), strict=False)
        digs[name] = dg
    detail['H3_digests'] = digs
    checks['H3_dirty_clean_same_value'] = (len(set(digs.values())) == 1
                                           and digs['clean_committed'] == REGISTERED_PIN)
    # 成对负控: 语义真的变了就必须换值 (否则「同值」是恒真门)
    doc2 = json.loads(json.dumps(doc))
    key = next(k for k in doc2 if isinstance(doc2[k], (dict, list)))
    if isinstance(doc2[key], dict) and doc2[key]:
        doc2[key][next(iter(doc2[key]))] = '___q40_semantic_tamper___'
    else:
        doc2[key] = '___q40_semantic_tamper___'
    p = SCRATCH / 'tampered.json'
    p.write_bytes((json.dumps(doc2, ensure_ascii=False, indent=1) + "\n").encode('utf-8'))
    dg_t, why_t = frc.proj_digest_file(str(p), strict=False)
    detail['H3_tampered'] = {'digest': dg_t, 'why': why_t}
    checks['H3_negative_control_semantic_change_moves_digest'] = (dg_t != REGISTERED_PIN)

    # ---- H4': 记录**未入库/树外** (另一触发类) ⇒ 两态都不许静默降级 -------------------
    for tag, tool in (('pre', str(pre)), ('post', TOOL)):
        r2 = SCRATCH / ('reg_h4_%s.json' % tag)
        registry_with(r2, [fixture_row])
        rc, out = run([tool, '--apply', '--only', NC_ID, '--round', ROUND, '--registry', str(r2)])
        f = row_of(r2, NC_ID)['evidence_generated_with']
        detail['H4_%s' % tag] = {'rc': rc, 'pin_status': f['pin_status'], 'reason': f['pin_reason'],
                                 'artifact_sha12': f['artifact_sha12'],
                                 'audited_by_round': f['audited_by_round'],
                                 'skip_line': ('SKIP' in out)}
    checks['H4_out_of_tree_record_no_silent_downgrade'] = (
        detail['H4_post']['pin_status'] == 'frozen'
        and detail['H4_post']['artifact_sha12'] == REGISTERED_PIN
        and detail['H4_post']['reason'] == 'archived-per-round')

    # ---- C4 成对控制: 非投影行不受 ② 影响 (前/后态逐字段相同) -------------------------
    def _clean_tracked(rel):
        full = os.path.join(ROOT, rel)
        if not os.path.isfile(full):
            return False
        blob = subprocess.run(['git', 'show', 'HEAD:%s' % rel], cwd=ROOT, capture_output=True)
        return blob.returncode == 0 and sha(blob.stdout) == sha(pathlib.Path(full).read_bytes())

    clean_frozen = next((r for r in reg['rows']
                         if isinstance(r.get('evidence_generated_with'), dict)
                         and r['evidence_generated_with'].get('pin_status') == 'frozen'
                         and r['evidence_generated_with'].get('pin_kind') is None
                         and r.get('level') in ('L1', 'L2', 'L3', 'L4')
                         and str(r.get('evidence_path', '')).startswith(('eval/', 'docs/reports/'))
                         and _clean_tracked(r['evidence_path'])), None)
    if clean_frozen is None:
        print('CLEAN_NONPROJ_ROW=NONE ⇒ rc=3 弃权 (无法构造零回归对照)')
        return 3
    cid = clean_frozen['id']
    prevs = {}
    for tag, tool in (('pre', str(pre)), ('post', TOOL)):
        r3 = SCRATCH / ('reg_c4_%s.json' % tag)
        registry_with(r3, [], ids=[cid])
        rc, out = run([tool, '--apply', '--only', cid, '--round', ROUND, '--registry', str(r3)])
        prevs[tag] = row_of(r3, cid)['evidence_generated_with']
    detail['C4'] = {'id': cid, 'pre': prevs['pre'], 'post': prevs['post']}
    checks['C4_non_projection_row_zero_regression'] = prevs['pre'] == prevs['post']

    ok = all(checks.values())
    payload = {'round': ROUND, 'schema': 'selftest-q40-projection/1',
               'prereg': 'eval/capability/exp1-q40/prereg_q40.json',
               'fixture': {'real_record': REAL_RECORD, 'registered_pin': REGISTERED_PIN,
                           'record_sha_before': rec_before_sha,
                           'tool_pre_sha12': sh12(blob.stdout),
                           'tool_now_sha12': sh12(pathlib.Path(os.path.join(ROOT, TOOL)).read_bytes())},
               'checks': checks, 'detail': detail, 'verdict': 'PASS' if ok else 'FAIL'}
    out_p = HERE / 'selftest_q40_projection.json'
    out_p.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for k in sorted(checks):
        print('%-52s %s' % (k, 'PASS' if checks[k] else 'FAIL'))
    print('VERDICT=%s out=%s' % (payload['verdict'], out_p))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
