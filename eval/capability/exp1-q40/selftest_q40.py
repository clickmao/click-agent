#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q40 · 候选③ 成对控制: 「已声明 frozen 的行在证据脏时不得被 apply 静默降级」。

判据 (预注册见 eval/capability/exp1-q40/prereg_q40.json)：
  C1 非定向 apply: 修前 ⇒ 该行被降级为 live/worktree-only (缺陷复现);
                    修后 ⇒ 该行**逐字段不变** (仍 frozen/pin 不动) 且印出 FROZEN_EVIDENCE_DIRTY_SKIP>=1。
  C2 定向重审 (契约里的处置命令): 修前 ⇒ 同样降级 (修法不可用 = 比缺陷更坏);
                                  修后 ⇒ frozen + pin == **现盘字节** sha12 (显式重审生效)。
  C3 可见性: 归档自洽 ∧ 现盘漂移 ⇒ FROZEN_EVIDENCE_DRIFT>=1 且**不判红**;
             同一 scratch 上把 pin 改成假值 ⇒ 必须 VIOLATION 判红 (成对控制: 红路没被关掉)。

夹具纪律: 全部走 /tmp scratch 登记表 (真登记表零写入); 脏件**从现盘现场选取** (不写死路径,
防「控制期望有时效性」); 找不到脏的已跟踪件 ⇒ 弃权 rc=3 (不伪造)。
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
HERE = pathlib.Path(__file__).resolve().parent
SCRATCH = pathlib.Path('/tmp/q40_scratch')
NC_ID = 'nc.q40.frozen-evidence-dirty'
ROUND = 'EXP1-Q40'
# 前态器具的**提交 sha** (修复前最后一次提交)。禁写 HEAD: 修复一旦提交, HEAD 即是修复态,
# 该锚会让「缺陷复现」臂静默失效 (EXP1-Q40 实测: 提交后三个成对控制同批 rc=2)。
PRE_STATE = '2718f9fc85a38b509feb781185fc494e14f586c8'


def sh12(b):
    return hashlib.sha256(b).hexdigest()[:12]


def run(args, env=None, cwd=ROOT):
    e = dict(os.environ)
    e['PYTHONPATH'] = os.path.join(ROOT, 'eval', 'capability')      # 前态副本也能解析规则模块
    if env:
        e.update(env)
    p = subprocess.run(['python3'] + args, cwd=cwd, capture_output=True, text=True, env=e)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def dirty_tracked_file():
    """现场选一个**已跟踪且脏**的证据件 (M 态), 返回 (rel, head_sha12, disk_sha12) 或 None。"""
    p = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True)
    for line in p.stdout.splitlines():
        st, path = line[:2], line[3:].strip().strip('"')
        if ' -> ' in path:
            path = path.split(' -> ')[1]
        if st != ' M':
            continue
        if not os.path.isfile(os.path.join(ROOT, path)):
            continue
        blob = subprocess.run(['git', 'show', 'HEAD:%s' % path], cwd=ROOT, capture_output=True)
        if blob.returncode != 0:
            continue
        disk = open(os.path.join(ROOT, path), 'rb').read()
        if sh12(disk) == sh12(blob.stdout):
            continue                                               # 名义脏但字节相同 ⇒ 不是漂移
        return path, sh12(blob.stdout), sh12(disk)
    return None


def scratch_registry(path, ev_rel, pin):
    """真登记表逐字节复制 + 追加一行 (格式与登记表一致: indent=1 / ensure_ascii=False / 尾 LF)。

    行形态 = 真登记的 L2 行 (level ∈ COVER_LEVELS ∧ evidence_path ∈ PRODUCT_PREFIXES ⇒
    进 `needs_field` scope —— 否则夹具行会被粒度收窄直接排除, 成对控制变成空跑)。
    """
    raw = open(os.path.join(ROOT, REG), encoding='utf-8').read()
    doc = json.loads(raw)
    doc['rows'].append({
        "id": NC_ID,
        "owner_round": "EXP1-Q40",
        "level": "L2",
        "capability": "EXP1-Q40 夹具行: 已声明 frozen 的证据在工作区脏 (非产品能力, 仅供成对控制)",
        "evidence_cmd": "python3 eval/capability/exp1-q40/selftest_q40.py",
        "evidence_path": ev_rel,
        "evidence_generated_with": {
            "evidence_kind": "artifact", "pin_status": "frozen", "pin_reason": "archived-per-round",
            "artifact_sha12": pin, "instrument": None, "instrument_sha12": None,
            "binding": "audit-pin", "audited_by_round": "EXP1-Q39",
        },
        "negative_control": "同一 scratch 上把 pin 改成假值 ⇒ --check 必须判红 (见 C3_bogus_pin)",
        "covers": [ev_rel],
        "note": "夹具行: 只活在 /tmp scratch 登记表; 真登记表零写入",
    })
    out = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    path.write_text(out, encoding='utf-8', newline='')
    return out


def row_of(path):
    doc = json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
    return next(r for r in doc['rows'] if r['id'] == NC_ID)


def main():
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True)
    pick = dirty_tracked_file()
    if not pick:
        print('DIRTY_FIXTURE=NONE (现盘无「已跟踪且字节漂移」的件) ⇒ rc=3 弃权 (不伪造夹具)')
        return 3
    ev_rel, head_pin, disk_pin = pick
    print('FIXTURE dirty_tracked=%s head=%s disk=%s' % (ev_rel, head_pin, disk_pin))

    # 前态器具 (缺陷态载体): 从 HEAD 取, 不改工作区任何字节
    pre = SCRATCH / 'bind_evidence_prefix.py'
    blob = subprocess.run(['git', 'show', '%s:%s' % (PRE_STATE, TOOL)], cwd=ROOT, capture_output=True)
    assert subprocess.run(['git', 'merge-base', '--is-ancestor', PRE_STATE, 'HEAD'],
                          cwd=ROOT).returncode == 0, '前态 sha 不是 HEAD 祖先'
    assert hashlib.sha256(blob.stdout).hexdigest() != \
        hashlib.sha256(open(os.path.join(ROOT, TOOL), 'rb').read()).hexdigest(), \
        '前态与现盘同字节 ⇒ 复现臂失效'
    assert blob.returncode == 0, '前态器具取不到 (前态 sha 无该件?)'
    pre.write_bytes(blob.stdout)
    pre_sha = sh12(blob.stdout)
    cur_sha = sh12(open(os.path.join(ROOT, TOOL), 'rb').read())
    print('TOOL_PRE_SHA12=%s TOOL_NOW_SHA12=%s (must differ)' % (pre_sha, cur_sha))

    checks, detail = {}, {}

    # ---- C1 非定向 (全表) apply -------------------------------------------------
    for tag, tool in (('pre', str(pre)), ('post', TOOL)):
        reg = SCRATCH / ('reg_%s.json' % tag)
        scratch_registry(reg, ev_rel, head_pin)
        rc, out = run([tool, '--apply', '--round', ROUND, '--registry', str(reg)])
        r = row_of(reg)
        f = r['evidence_generated_with']
        d = {'rc': rc, 'pin_status': f['pin_status'], 'reason': f['pin_reason'],
             'artifact_sha12': f['artifact_sha12'],
             'skip_line': ('FROZEN_EVIDENCE_DIRTY_SKIP=' in out),
             'downgraded': f['pin_status'] == 'live'}
        detail['C1_%s' % tag] = d
        # 判据**逐臂**在本轮内判定 (器具缺陷#1: 首版在循环外读 detail['C1_post'],
        #   变量取错臂 ⇒ 正控被报成 FAIL —— 变量语义归位, 断言强度未放宽)。
        if tag == 'pre':
            checks['C1_pre_downgraded(缺陷复现)'] = (d['pin_status'] == 'live'
                                                     and d['reason'] == 'worktree-only'
                                                     and not d['skip_line'])
        else:
            checks['C1_post_not_downgraded(修复生效)'] = (
                f['pin_status'] == 'frozen' and f['pin_reason'] == 'archived-per-round'
                and f['artifact_sha12'] == head_pin and f['audited_by_round'] == 'EXP1-Q39')
            checks['C1_post_visible_skip'] = d['skip_line']

    # ---- C2 定向重审 (契约里的处置命令) ------------------------------------------
    for tag, tool in (('pre', str(pre)), ('post', TOOL)):
        reg = SCRATCH / ('reg2_%s.json' % tag)
        scratch_registry(reg, ev_rel, head_pin)
        rc, out = run([tool, '--apply', '--only', NC_ID, '--round', ROUND, '--registry', str(reg)])
        f = row_of(reg)['evidence_generated_with']
        detail['C2_%s' % tag] = {'rc': rc, 'pin_status': f['pin_status'],
                                 'artifact_sha12': f['artifact_sha12']}
        if tag == 'post':
            checks['C2_post_targeted_reaudit_works'] = (f['pin_status'] == 'frozen'
                                                        and f['artifact_sha12'] == disk_pin)
        else:
            checks['C2_pre_targeted_also_downgraded(修法此前不可用)'] = (f['pin_status'] == 'live')

    # ---- C3 可见性成对 -----------------------------------------------------------
    reg = SCRATCH / 'reg3.json'
    scratch_registry(reg, ev_rel, head_pin)
    rc, out = run([TOOL, '--check', '--registry', str(reg)])
    drift_n = int(next((ln.split('=')[1].split()[0] for ln in out.splitlines()
                        if ln.startswith('FROZEN_EVIDENCE_DRIFT=')), '0'))
    detail['C3_drift'] = {'rc': rc, 'drift_n': drift_n,
                          'violation_for_nc': ('VIOLATION %s' % NC_ID) in out}
    checks['C3_archive_consistent_drift_visible_not_red'] = (drift_n >= 1
                                                             and ('VIOLATION %s' % NC_ID) not in out)
    reg_bad = SCRATCH / 'reg3_bad.json'
    scratch_registry(reg_bad, ev_rel, '000000000000')
    rc_bad, out_bad = run([TOOL, '--check', '--registry', str(reg_bad)])
    detail['C3_bogus_pin'] = {'rc': rc_bad, 'violation_for_nc': ('VIOLATION %s' % NC_ID) in out_bad}
    checks['C3_bogus_pin_still_red'] = rc_bad == 2 and ('VIOLATION %s' % NC_ID) in out_bad

    ok = all(checks.values())
    payload = {'round': ROUND, 'schema': 'selftest-q40/1',
               'prereg': 'eval/capability/exp1-q40/prereg_q40.json',
               'fixture': {'dirty_tracked': ev_rel, 'head_pin': head_pin, 'disk_pin': disk_pin,
                           'tool_pre_sha12': pre_sha, 'tool_now_sha12': cur_sha},
               'checks': checks, 'detail': detail, 'verdict': 'PASS' if ok else 'FAIL'}
    outp = HERE / 'selftest_q40.json'
    outp.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for k in sorted(checks):
        print('%-52s %s' % (k, 'PASS' if checks[k] else 'FAIL'))
    print('VERDICT=%s out=%s' % (payload['verdict'], outp))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
