#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q41 · 写侧尾 LF 探针: 现行写入器 (登记表 --apply / 行追加器) 产出的字节是否**规范形**。

动机: 历史回放显示 37 次提交态缺尾 LF (全部是登记表) ⇒ 转正 (默认开) 的价值/代价取决于
      **现行写入器是否仍产出非规范形**。本探针在 /tmp scratch 上跑真实写入路径, 断言:
        ① 真登记表字节逐位不变 (sha256 before == after) —— 探针自排除 (语料守恒)
        ② 写入器产出末字节 = LF ⇒ 判 CANONICAL
        ③ 负控: 把 scratch 尾 LF 去掉再判 ⇒ 必须 NONCANONICAL (证明判据非恒真)

三态退出码: 0 全绿 / 2 判据红 / 3 环境不可判。
"""
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REG = ROOT / 'docs' / 'verification-registry.json'
SCRATCH = pathlib.Path('/tmp/q41_scratch')
ROUND_TAG = 'EXP1-Q41T'


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:12]


def run(args):
    p = subprocess.run(['python3'] + args, cwd=str(ROOT), capture_output=True, text=True)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def tail_byte(p):
    raw = pathlib.Path(p).read_bytes()
    return raw[-1:], len(raw)


def pick_row_id():
    """自定位一个真实行 id (优先 semantic-projection 行, 否则首行): 不写死 id。"""
    reg = json.loads(REG.read_text(encoding='utf-8'))
    for r in reg['rows']:
        g = r.get('evidence_generated_with')
        if isinstance(g, dict) and g.get('pin_kind') == 'semantic-projection':
            return r['id'], 'semantic-projection'
    return reg['rows'][0]['id'], 'first-row'


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    before = sha(REG)
    row_id, row_why = pick_row_id()
    results = {'real_registry_sha12_before': before, 'round_tag': ROUND_TAG,
               'probe_row_id': row_id, 'probe_row_choice': row_why}

    # ① 写入器 A: bind_evidence --apply (登记表刷新路径)
    reg_a = SCRATCH / 'reg_apply.json'
    shutil.copyfile(REG, reg_a)
    rc, out = run(['eval/capability/bind_evidence.py', '--apply', '--round', ROUND_TAG,
                   '--only', row_id, '--registry', str(reg_a)])
    tb, n = tail_byte(reg_a)
    results['writer_bind_evidence_apply'] = {'rc': rc, 'tail_byte': tb.decode('latin1'),
                                             'canonical': tb == b'\n', 'bytes': n,
                                             'stdout_tail': out.strip().splitlines()[-3:] if out.strip() else []}

    # ② 写入器 B: 行追加器 (exp1-q40 append_rows_q40.py 若可空跑)
    app = ROOT / 'eval' / 'capability' / 'exp1-q40' / 'append_rows_q40.py'
    if app.is_file():
        reg_b = SCRATCH / 'reg_append.json'
        shutil.copyfile(REG, reg_b)
        rc_b, out_b = run([str(app.relative_to(ROOT)), '--registry', str(reg_b)])
        if rc_b != 0:      # 该器可能不支持 --registry/environment: 只记读数, 不判红
            results['writer_append_rows'] = {'rc': rc_b, 'note': '不可空跑 (不判红, 如实记录)',
                                             'stdout_tail': out_b.strip().splitlines()[-3:]}
        else:
            tbb, nb = tail_byte(reg_b)
            results['writer_append_rows'] = {'rc': rc_b, 'tail_byte': tbb.decode('latin1'),
                                             'canonical': tbb == b'\n', 'bytes': nb}

    # ③ 负控: 去掉 scratch 尾 LF ⇒ 判据必须翻面
    nc = SCRATCH / 'reg_nc.json'
    raw = reg_a.read_bytes()
    nc.write_bytes(raw.rstrip(b'\n'))
    tb_nc, _ = tail_byte(nc)
    results['negative_control_tail_stripped'] = {'tail_byte': tb_nc.decode('latin1'),
                                                 'canonical_if_judged': tb_nc == b'\n'}

    after = sha(REG)
    results['real_registry_sha12_after'] = after
    results['real_registry_untouched'] = (before == after)

    w = results.get('writer_bind_evidence_apply', {})
    results['verdict'] = {
        'writer_canonical': bool(w.get('canonical')),
        'negative_control_flips': results['negative_control_tail_stripped']['canonical_if_judged'] is False,
        'real_registry_untouched': results['real_registry_untouched'],
    }
    ok = (results['verdict']['writer_canonical'] and results['verdict']['negative_control_flips']
          and results['verdict']['real_registry_untouched'])
    results['exit_code'] = 0 if ok else 2
    (HERE / 'writer_tail_probe_q41.json').write_text(
        json.dumps(results, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    print('WRITER bind_evidence --apply: rc=%s tail=%s canonical=%s bytes=%s'
          % (w.get('rc'), w.get('tail_byte'), w.get('canonical'), w.get('bytes')))
    if 'writer_append_rows' in results:
        print('WRITER append_rows: %s' % json.dumps(results['writer_append_rows'], ensure_ascii=False)[:200])
    print('WRITER negative_control tail=%s canonical=%s'
          % (results['negative_control_tail_stripped']['tail_byte'],
             results['negative_control_tail_stripped']['canonical_if_judged']))
    print('WRITER real_registry_untouched=%s (%s -> %s)'
          % (results['real_registry_untouched'], before, after))
    print('WRITER_EXIT=%d' % results['exit_code'])
    return results['exit_code']


if __name__ == '__main__':
    sys.exit(main())
