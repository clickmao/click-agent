#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q30 · 候选⑥: 提交态内部一致性核验 (登记行 `-c Release` 变体的口径落地 = 冻结/提交档)。

与 worktree 档的分工:
  * worktree 档 (`bind_evidence.py --check`)  —— 查**现盘**: 声明 pin vs 工作区字节;
  * 提交态档 (本器具)                         —— 查**HEAD**: HEAD 版登记表的每条 frozen/artifact 主张
    vs HEAD blob 重算 (按该行**声明的 pin 语义**: 字节 pin ⇒ sha256[:12]; 语义投影 pin ⇒ 投影摘要)。
提交期缺口 (worktree 档结构性查不出): 「器具/证据已改但登记表未重审」——改动一旦 `git add` 后提交,
工作区与声明**都**变成新的 (工作区档自然绿), 而**HEAD 里那一步是否自洽**无人核验。
取字节用一次 `git cat-file --batch` (不逐文件起进程)。

EXP1-Q35 修复 (判据口径分叉): 本器曾对**全部** frozen/artifact 主张按**字节** sha256[:12] 比对 ——
而 Q34 把 `r444.instrument-acceptance` 的 pin 语义迁到 `pin_kind=semantic-projection` (pin = 语义投影摘要)。
两条口径都「自洽」, 合起来必红 (实测: 声明=28005ef21a80 / HEAD 字节=74f53cda3f23)。
修法 = **尊重行上声明的 pin 语义**(derive 侧同款纪律): pin_kind=semantic-projection ⇒ 用 HEAD blob 的
**语义投影摘要**比对; 复算不可得 (非 JSON / 规则表不可用) ⇒ **fail-closed 判红** (不静默跳过)。
负控成对 (--selftest): ①只改运行期字段 ⇒ 该主张必须**不**变红; ②改语义叶 ⇒ 必须变红; ③投影不可算 ⇒ 判红。

用法:
  python3 eval/capability/exp1-q30/check_committed_state_q30.py
  python3 eval/capability/exp1-q30/check_committed_state_q30.py --inject-defect unpinned-drift   # 负控
  python3 eval/capability/exp1-q30/check_committed_state_q30.py --selftest                        # 成对控制
"""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

REG = 'docs/verification-registry.json'
HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.dirname(os.path.dirname(HERE))          # <root>/eval
FRC_PATH = os.path.join(EVAL, 'capability', 'face_record_canon.py')


def load_frc():
    spec = importlib.util.spec_from_file_location('q35_frc', FRC_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(*args, data=None):
    return subprocess.run(['git'] + list(args), capture_output=True, input=data, check=True).stdout


def sha12_bytes(body):
    return hashlib.sha256(body).hexdigest()[:12]


def digest_for(f, body):
    """按该行声明的 pin 语义算 HEAD blob 的摘要。返回 (digest|None, reason|None)。

    投影分支用 strict=False: 真面记录在「干净窗口」下 foreign_writes/self_writes/pre_existing 可为空,
    逐规则容忍空心; **锚规则 (window 三件套) 仍 fail-closed** (缺席 ⇒ 抛错 ⇒ 本器判不可验证 ⇒ 红)。
    """
    if f.get('pin_kind') == 'semantic-projection':
        try:
            frc = load_frc()
            doc = json.loads(body.decode('utf-8'))
            dg, _meta = frc.proj_digest(doc, strict=False)
            return dg, None
        except Exception as exc:                     # 非 JSON / 规则表不可用 / 锚规则缺席 ⇒ 不可验证
            return None, 'PROJECTION_UNCOMPUTABLE(%s)' % type(exc).__name__
    return sha12_bytes(body), None


def collect(rows, inject, mode):
    want, claims = [], []
    for r in rows:
        f = r.get('evidence_generated_with')
        if not isinstance(f, dict):
            continue
        if f.get('pin_status') != 'frozen':
            continue
        if f.get('evidence_kind') == 'directory':
            continue        # 目录聚合行的清单式 pin 另有器具 (本器只核 artifact 字节)
        ep, pin = r.get('evidence_path'), f.get('artifact_sha12')
        inst, ipin = f.get('instrument'), f.get('instrument_sha12')
        if inject and mode == 'unpinned-drift' and not claims:
            pin = 'deadbeef0000'          # 只在内存里改一条主张 ⇒ 模拟「改了没重审就提交」
        claims.append((r.get('id'), 'artifact', ep, pin, f.get('pin_kind')))
        want.append(ep)
        if inst:
            claims.append((r.get('id'), 'instrument', inst, ipin, None))
            want.append(inst)
    return want, claims


def fetch_blobs(paths):
    sha, bodies = {}, {}
    req = '\n'.join('HEAD:%s' % p for p in paths) + '\n'
    out = git('cat-file', '--batch', data=req.encode())
    i = 0
    for p in paths:
        j = out.index(b'\n', i)
        header = out[i:j].decode('utf-8', 'replace').split()
        i = j + 1
        if len(header) != 3:
            sha[p] = None
            continue
        size = int(header[2])
        body = out[i:i + size]
        i += size + 1
        bodies[p] = body
        sha[p] = sha12_bytes(body)
    return sha, bodies


def main():
    inject = '--inject-defect' in sys.argv
    mode = sys.argv[sys.argv.index('--inject-defect') + 1] if inject else None
    raw = git('show', 'HEAD:%s' % REG)
    doc = json.loads(raw.decode('utf-8'))
    rows = doc['rows']

    want, claims = collect(rows, inject, mode)
    paths = sorted({p for p in want if p})
    sha, bodies = fetch_blobs(paths)

    viol, unverifiable = [], []
    for rid, kind, p, pin, pk in claims:
        if p is None:
            viol.append((rid, kind, p, pin, None))
            continue
        body = bodies.get(p)
        if body is None:
            viol.append((rid, kind, p, pin, None))
            continue
        if kind == 'artifact':
            got, why = digest_for({'pin_kind': pk}, body)
            if got is None:
                unverifiable.append((rid, kind, p, pin, why))
                continue
        else:
            got = sha12_bytes(body)
        if got != pin:
            viol.append((rid, kind, p, pin, got + ('/%s' % pk if pk else '')))
    viol += unverifiable
    if inject:
        if viol:
            print('NC_DETECTED (注入 %s ⇒ %d 条违反: %s)' % (mode, len(viol), viol[0]))
            return 0
        print('NC_NOT_DETECTED (注入未被检出 ⇒ 器具空心)')
        return 1
    n_proj = sum(1 for c in claims if c[4] == 'semantic-projection')
    print('COMMITTED_STATE rows=%d claims=%d blobs=%d projection_claims=%d'
          % (len(rows), len(claims), len(paths), n_proj))
    for v in viol[:10]:
        print('  VIOLATION %s/%s %s 声明=%s HEAD=%s' % v)
    if viol:
        print('COMMITTED_STATE_CHECK=FAIL (%d 条)' % len(viol))
        return 2
    print('COMMITTED_STATE_CHECK=OK (HEAD 登记表主张与 HEAD blob 逐条一致; 口径=各行声明的 pin 语义)')
    return 0


def selftest():
    """成对控制 (EXP1-Q35): 只在检查器**自己用的那个函数**上判定, 保证「宽松」与「敏感」同时成立。"""
    frc_path = FRC_PATH
    rec_path = os.path.join(EVAL, 'capability', 'instruments-check.json')
    if not os.path.exists(rec_path):
        print('SELFTEST=ABSTAIN (缺 record fixture)')
        return 3
    with open(rec_path, 'rb') as fh:
        body = fh.read()
    # strict=False: 真面记录在「干净窗口」下 foreign_writes/self_writes 可为空 ⇒ 逐规则容忍空心
    #   (锚规则仍 fail-closed, 由 face_record_canon 保证)。用 strict=True 会让本自检在干净窗口恒红 (实测 T5)。
    dg0, _ = digest_for({'pin_kind': 'semantic-projection'}, body)
    dg_byte = sha12_bytes(body)
    checks = {}
    checks['projection_differs_from_byte'] = (dg0 is not None and dg0 != dg_byte)
    # ① 只改运行期字段 ⇒ 投影摘要必须不变 (宽松性成立)
    doc = json.loads(body.decode('utf-8'))
    doc['side_effect_attribution']['window']['t0'] = 111111111.0
    doc['side_effect_attribution']['window']['t1'] = 222222222.0
    doc['side_effect_attribution']['window']['trace_dir'] = '/tmp/q35_selftest_runtime'
    dg_rt, _ = digest_for({'pin_kind': 'semantic-projection'},
                          json.dumps(doc, ensure_ascii=False, indent=1).encode('utf-8'))
    checks['runtime_only_change_keeps_digest'] = (dg_rt == dg0)
    # ② 改语义叶 ⇒ 投影摘要必须变 (敏感性成立)
    doc2 = json.loads(body.decode('utf-8'))
    first = doc2['results'][0]
    first['pass'] = (not first.get('pass'))
    dg_sem, _ = digest_for({'pin_kind': 'semantic-projection'},
                           json.dumps(doc2, ensure_ascii=False, indent=1).encode('utf-8'))
    checks['semantic_change_flips_digest'] = (dg_sem is not None and dg_sem != dg0)
    # ③ config 形状改动: 证书声明面 (结果条数) 变 ⇒ 摘要必须变
    doc3 = json.loads(body.decode('utf-8'))
    doc3['results'] = doc3['results'][:-1]
    dg_cnt, _ = digest_for({'pin_kind': 'semantic-projection'},
                           json.dumps(doc3, ensure_ascii=False, indent=1).encode('utf-8'))
    checks['membership_change_flips_digest'] = (dg_cnt is not None and dg_cnt != dg0)
    # ④ 非 JSON ⇒ 不可算 ⇒ 必须报不可验证 (fail-closed, 不静默跳过)
    dg_bad, why = digest_for({'pin_kind': 'semantic-projection'}, b'not json')
    checks['nonjson_is_unverifiable'] = (dg_bad is None and bool(why))
    # ⑤ 字节 pin 路径不受影响 (回归)
    dg_byte2, why2 = digest_for({}, body)
    checks['byte_pin_unchanged'] = (dg_byte2 == dg_byte and why2 is None)
    # ⑥ 投影路径确实与规则表同源 (hollow 规则自检由 frc 自身保证; 这里抽查规则数 > 0)
    try:
        frc = load_frc()
        checks['rules_nonempty'] = len(frc._load_projection_rules()) > 0
    except Exception:
        checks['rules_nonempty'] = False
    print('SELFTEST %s' % checks)
    return 0 if all(checks.values()) else 2


if __name__ == '__main__':
    sys.exit(selftest() if '--selftest' in sys.argv else main())
