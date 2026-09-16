#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q31 · C5: `bind_evidence --only` 定向重审的**自足等价闸** (长驻 L2 器具面形态)。

Q30 的等价性结论 (两条独立写路径逐字节等价) 当时由轮内探针 + 轮内 scratch 对照件证明。本器把它做成
**自足长驻闸**: 不依赖任何轮内 scratch 文件、不写仓库 (全程 tempfile), 夹具锚**从当前登记表现场派生**
(防「控制期望有时效性」—— 旧轮钉的 12 位 pin 字面量会随证据刷新失效)。
判据:
  P1 器具序列化器路径 (`--apply --only`) 与**文本外科手术**路径 (不整份序列化) 产物 sha 逐位相同;
  P2 作用域: 仅目标行字段变 (其余行逐字段不变, 行数不变);
  P3 幂等: 再跑 `--only` 产物 sha 不变 ∧ 打印 IDEMPOTENT=OK;
  P4 未知 id ⇒ rc=3 ∧ 零写入;  P5 缺 `--round` ⇒ rc=3 ∧ 零写入;
  P6 反证 (去作用域): 全表 `--apply` 产物与 `--only` 产物**字节不同** ⇒ 作用域收窄非空转;
  P7 真登记表零副作用 (跑前后 sha 相同)。
负控: `--inject-defect round-param-mismatch` ⇒ 路径 B 用不同轮号参数 ⇒ P1 必红 ⇒ 打印 NC_DETECTED (rc=0)。
退出码: 0 通过 / 2 断言失败 / 3 环境失败。
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
TOOL = 'eval/capability/bind_evidence.py'
REG = 'docs/verification-registry.json'
ROUND = 'EXP1-Q31'
OTHER_ROUND = 'R471'          # 负控用: 与 ROUND 不同的合法轮号命名段


def sha12(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]


def rd(p):
    with open(p, encoding='utf-8', newline='') as f:
        return f.read()


def wr(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def run(args):
    p = subprocess.run(['python3'] + args, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def pick_fixture_anchor(raw):
    """从**当前**登记表里现场选一条 frozen 行的 artifact pin 作为夹具锚 (防过期字面量)。"""
    doc = json.loads(raw)
    for r in doc['rows']:
        f = r.get('evidence_generated_with')
        if isinstance(f, dict) and f.get('pin_status') == 'frozen' and isinstance(f.get('artifact_sha12'), str):
            return r['id'], f['artifact_sha12']
    return None, None


def pick_second_anchor(raw, exclude_id):
    """P6 反证用的**第二个**待派生锚 (必须是别的行) —— 防「全表刚 repin 完 ⇒ 全表 apply 零变更 ⇒
    反证恒红且无判别力」(EXP1-Q35 实测的负控饱和)。"""
    doc = json.loads(raw)
    for r in doc['rows']:
        f = r.get('evidence_generated_with')
        if (r['id'] != exclude_id and isinstance(f, dict) and f.get('pin_status') == 'frozen'
                and isinstance(f.get('artifact_sha12'), str)):
            return r['id'], f['artifact_sha12']
    return None, None


def break_pin(raw, row_id, pin, newval):
    """把某行的 artifact pin 改成 newval (文本外科手术, 行块内唯一命中); 锚不在本行块内 ⇒ None。"""
    bs = raw.index('"id": "%s"' % row_id)
    be = raw.index('\n  },', bs)
    needle = '"artifact_sha12": "%s"' % pin
    k = raw.index(needle, bs)
    if k >= be:
        return None
    return raw[:k] + '"artifact_sha12": "%s"' % newval + raw[k + len(needle):]


def block_insert(raw, row_id, new_field):
    """文本外科手术 (不整份序列化): 只重写目标行的 evidence_generated_with 块。算法移植自 Q30 等价探针。"""
    i = raw.index('"id": "%s"' % row_id)
    j = raw.index('\n  },', i) + len('\n  },')
    block = raw[i:j]
    k = block.index('"evidence_generated_with": ')
    ls = block.rindex('\n', 0, k) + 1
    W = block[ls:k]
    ob = block.index('{', k)
    depth, p, in_str, esc = 0, ob, False, False
    while True:
        ch = block[p]
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                break
        p += 1
    end = block.index('\n', p + 1)
    trailing = block[p + 1:end]
    inner = json.dumps(new_field, indent=1, ensure_ascii=False).split('\n')
    lines = [W + '"evidence_generated_with": {'] + [W + l for l in inner[1:]]
    new_block = block[:ls] + '\n'.join(lines) + trailing + block[end:]
    return raw[:i] + new_block + raw[j:]


def main():
    inject = None
    if '--inject-defect' in sys.argv:
        inject = sys.argv[sys.argv.index('--inject-defect') + 1]
    if '--target-id' in sys.argv:
        target = sys.argv[sys.argv.index('--target-id') + 1]
    else:
        target = None
    reg_real = os.path.join(ROOT, REG)
    if not os.path.isfile(reg_real):
        print('ENV_FAIL: 登记表不存在')
        return 3
    raw = rd(reg_real)
    reg_sha_before = sha12(reg_real)
    row_id, pin = pick_fixture_anchor(raw)
    if target is None:
        target = row_id
    if not target or not pin:
        print('ENV_FAIL: 现登记表没有可做夹具锚的 frozen 行')
        return 3
    checks, readings = {}, {}
    tmp = tempfile.mkdtemp(prefix='q31-only-guard-')
    try:
        broken = raw[:0]
        # 夹具锚必须在**目标行块内**被改写 (防同值 pin 命中别的行 ⇒ 夹具失效)
        block_start = raw.index('"id": "%s"' % target)
        block_end = raw.index('\n  },', block_start)
        needle = '"artifact_sha12": "%s"' % pin
        k = raw.index(needle, block_start)
        if k >= block_end:
            print('ENV_FAIL: 夹具锚不在目标行块内 (row=%s pin=%s)' % (target, pin))
            return 3
        broken = raw[:k] + '"artifact_sha12": "deadbeef0001"' + raw[k + len(needle):]
        if broken == raw:
            print('ENV_FAIL: 夹具锚未命中 (pin=%s)' % pin)
            return 3
        fixture = os.path.join(tmp, 'fixture.json')
        wr(fixture, broken)
        readings['fixture_anchor'] = {'row': target, 'pin': pin, 'fixture_sha12': sha12(fixture)}

        sys.path.insert(0, os.path.join(ROOT, 'eval/capability'))
        import bind_evidence as be
        be.AUDITED_BY_ROUND = ROUND
        tracked, dirty = be.git_state(ROOT)
        rows = {r.get('id'): r for r in json.loads(broken)['rows']}
        field = be.derive(ROOT, rows[target], tracked, dirty)
        readings['derived'] = {k: field.get(k) for k in ('pin_status', 'instrument', 'audited_by_round')}
        checks['N3_夹具有效'] = (field.get('artifact_sha12') != 'deadbeef0001')

        a = os.path.join(tmp, 'out_only.json')
        wr(a, broken)
        rcA, outA = run([TOOL, '--apply', '--only', target, '--round', ROUND, '--registry', a])
        b = os.path.join(tmp, 'out_block.json')
        field_b = dict(field)
        if inject == 'round-param-mismatch':
            field_b = dict(field, audited_by_round=OTHER_ROUND)
        wr(b, block_insert(broken, target, field_b))
        readings['A_sha12'], readings['B_sha12'] = sha12(a), sha12(b)
        p1 = (sha12(a) == sha12(b) and rcA == 0)
        checks['P1_两路径逐字节等价'] = bool(p1)

        if inject == 'round-param-mismatch':
            ok = (not p1) and (sha12(a) != sha12(b))
            print('注入 round-param-mismatch: A=%s B=%s' % (readings['A_sha12'], readings['B_sha12']))
            print('P1_两路径逐字节等价 FAIL (注入生效)' if not p1 else 'P1 仍绿 ⇒ 判据空心')
            print('NC_DETECTED' if ok else 'NC_NOT_DETECTED')
            return 0 if ok else 1

        ra, rf = {r['id']: r for r in json.load(open(a, encoding='utf-8'))['rows']}, \
                 {r['id']: r for r in json.loads(broken)['rows']}
        changed = sorted(i for i in ra if ra[i] != rf[i])
        readings['changed_rows'] = changed
        checks['P2_作用域仅目标行'] = (changed == [target] and len(ra) == len(rf))
        rcA2, outA2 = run([TOOL, '--apply', '--only', target, '--round', ROUND, '--registry', a])
        checks['P3_幂等'] = (rcA2 == 0 and 'IDEMPOTENT=OK' in outA2 and sha12(a) == readings['A_sha12'])
        d = os.path.join(tmp, 'out_unknown.json')
        wr(d, broken)
        sd = sha12(d)
        rcD, _ = run([TOOL, '--apply', '--only', 'bogus.id.does-not-exist', '--round', ROUND, '--registry', d])
        checks['P4_未知id_rc3零写入'] = (rcD == 3 and sha12(d) == sd)
        e = os.path.join(tmp, 'out_noround.json')
        wr(e, broken)
        se = sha12(e)
        rcE, outE = run([TOOL, '--apply', '--only', target, '--registry', e])
        checks['P5_缺轮号_rc3零写入'] = (rcE == 3 and sha12(e) == se)
        readings['P5_line'] = outE.strip().splitlines()[:1]
        c = os.path.join(tmp, 'out_full.json')
        # EXP1-Q36: 反证去饱和 —— 全表 apply 若在「刚 repin 完」的表上跑, 零行需派生 ⇒ 前提不成立
        #   (旧版直接要求 n_touched>1 ⇒ 恒红且无判别力)。修法: scratch 副本里**再注入一行待派生**
        #   (另一行 artifact pin 置假值), 令「全表作用域」必然触及 ≥2 行。
        second_id, second_pin = pick_second_anchor(broken, target)
        broken2 = broken
        if second_id and second_pin != 'deadbeef0002':
            b2 = break_pin(broken, second_id, second_pin, 'deadbeef0002')
            if b2:
                broken2 = b2
                readings['second_anchor'] = {'row': second_id, 'pin': second_pin}
        wr(c, broken2)
        rcC, outC = run([TOOL, '--apply', '--round', ROUND, '--registry', c])
        touched = [l for l in outC.splitlines() if 'UNCHANGED=' in l]
        n_touched = int(touched[0].split('/ TOUCHED=')[1].split()[0]) if touched else -1
        readings['C_touched'] = touched[:1]
        checks['P6_反证_去作用域不同字节'] = (rcC == 0 and n_touched > 1 and sha12(c) != readings['A_sha12']
                                            and broken2 != broken)
        checks['P7_真登记表零副作用'] = (sha12(reg_real) == reg_sha_before)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    rep = {'round': ROUND, 'instrument': os.path.relpath(os.path.abspath(__file__), ROOT),
           'checks': checks, 'readings': readings,
           'n_checks': '%d/%d' % (sum(1 for v in checks.values() if v), len(checks))}
    rep['verdict'] = 'PASS' if all(checks.values()) else 'FAIL'
    for k, v in checks.items():
        print('%-28s %s' % (k, 'OK' if v else 'FAIL'))
    print('verdict=%s (%s) target=%s' % (rep['verdict'], rep['n_checks'], target))
    return 0 if rep['verdict'] == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
