#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q20 · exp1q13 外部注入入口的**三态读数**驱动 (可一条命令复跑 ⇒ L3-证据可复现)。

判据 (预注册见 ../exp1-q20/prereg_q20.json):
  正控  : --selftest 7/7 rc=0  ∧ 全量跑 rc=0
  零回归: 全量跑 verdict 与已归档 verdict_q13.json **除白名单 {instrument_version} 外逐位相同**
          ∧ evidence 逐字节相同 (白名单单键, 显式声明为非语义字段)
  负控  : 8 个注入 kind, 每个的 primary_red 判据必须变红 (cascade 如实记录)
  fail-closed: 未知 kind rc=3; phantom-ineffective rc=3 (期望红未红); 注入运行不落盘
  自洁  : 本轮矩阵跑完, eval/capability/exp1-q13/ 内文件 sha256 逐一不变 (不弄脏 Q13 轮次产物)

退出码: 0 判据全过 / 2 判据失败 / 3 测量或环境失败。结论由显式标记 `Q20_EXIT=<code>` 决定。
用法: python3 eval/capability/exp1-q20/run_q20.py
"""
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SELF = pathlib.Path(__file__).resolve().parent
Q13DIR = ROOT / 'eval/capability/exp1-q13'
Q13 = Q13DIR / 'index_scope_out_classify.py'
ARCH_VERDICT = Q13DIR / 'verdict_q13.json'
ARCH_EVIDENCE = Q13DIR / 'evidence_q13.txt'
BACKUP = pathlib.Path('/tmp/q20_backup')
WHITELIST = {'instrument_version'}          # 显式声明: 非语义字段 (版本声明), 唯一允许不同
RERUN_VERDICT = SELF / 'q13_rerun_verdict.json'
RERUN_EVIDENCE = SELF / 'q13_rerun_evidence.txt'

INJ = [
    ('kind-count-drift', 'C1_conservation', 2, 'INJECT_APPLIED'),
    ('strength-registry-drift', 'C2_zero_regression', 2, 'INJECT_APPLIED'),
    ('caliber-delta-applied', 'C3_ruling_A_landed', 2, 'INJECT_APPLIED'),
    ('suffix-set-hardcoded', 'C4_language_set_from_source', 2, 'INJECT_APPLIED'),
    ('bucket-one-sided', 'C5_nontrivial', 2, 'INJECT_APPLIED'),
    ('payoff-overflow', 'C6_payoff_ceiling', 2, 'INJECT_APPLIED'),
    ('phantom-noop', None, 0, 'INJECT_APPLIED_NOOP_OK'),
    ('phantom-ineffective', 'C1_conservation', 3, 'INJECT_NOT_RED'),
]


def sha256(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def sh(cmd):
    p = subprocess.run(['bash', '-lc', cmd], cwd=str(ROOT), capture_output=True, text=True, timeout=900)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def q13(args):
    return sh(f'python3 {Q13.relative_to(ROOT)} {args}')


def judge_injection(spec, rc, marker, red):
    """期望编码 (driver 侧): 依 expect_marker 分三型 ——
    INJECT_APPLIED        : primary 必须**在**红集合内;
    INJECT_NOT_RED        : primary 必须**不在**红集合内 (fail-closed 分支可达的证明);
    INJECT_APPLIED_NOOP_OK: 红集合必须为**空** (审计桩: 未改输入 ⇒ 不应有判据变红)。
    首版只按「primary 必须在红集合」编码 ⇒ 把 fail-closed 的证明反判成假红 (见 honest_boundaries)。"""
    _kind, prim, exp_rc, exp_marker = spec
    if exp_marker == 'INJECT_APPLIED':
        pred_ok = (prim in red)
    elif exp_marker == 'INJECT_NOT_RED':
        pred_ok = (prim not in red) and len(red) == 0
    else:
        pred_ok = (len(red) == 0)
    return bool(rc == exp_rc and marker == exp_marker and pred_ok)


def main():
    lines, ev = [], []

    def log(s):
        lines.append(s)
        ev.append(s)

    q13dir_before = {p.name: sha256(p) for p in sorted(Q13DIR.iterdir()) if p.is_file()}

    # 0) 前置: 备份齐备 + 归档未被上一跑污染
    pre = {}
    for n, src in (('verdict_q13.json', ARCH_VERDICT), ('evidence_q13.txt', ARCH_EVIDENCE),
                   ('index_scope_out_classify.py', BACKUP / 'index_scope_out_classify.py')):
        pre[n] = {'archived_sha256': sha256(src) if src.exists() else None,
                  'backup_sha256': sha256(BACKUP / n) if (BACKUP / n).exists() else None}
        pre[n]['identical'] = bool(pre[n]['archived_sha256'] and
                                   pre[n]['archived_sha256'] == pre[n]['backup_sha256'])
    if not all(v['identical'] for k, v in pre.items() if k != 'index_scope_out_classify.py'):
        print('MEASUREMENT_FAIL: 归档 Q13 产物与备份不一致 (上一跑污染?) ⇒ 不解读数')
        return 3
    log(f"[pre] Q13 归档与备份 sha256 一致: verdict={pre['verdict_q13.json']['archived_sha256'][:12]} "
        f"evidence={pre['evidence_q13.txt']['archived_sha256'][:12]}")

    # 1) 正控 A: selftest
    rc, out = q13('--selftest --no-write')
    try:
        st = json.loads(out[out.index('{'):out.rindex('}') + 1])
    except Exception:
        print('MEASUREMENT_FAIL: selftest 输出不可解析');  print(out[-400:]);  return 3
    st_pass = (rc == 0 and st.get('all_pass') is True and len(st.get('selftest', {})) == 7)
    log(f"[正控A] selftest rc={rc} n={len(st.get('selftest', {}))} all_pass={st.get('all_pass')} ⇒ {'PASS' if st_pass else 'FAIL'}")

    # 2) 正控 B: 全量跑 (输出指向本轮 scratch, 不回写 Q13 轮次证据)
    rc, out = q13(f'--out {RERUN_VERDICT.relative_to(ROOT)} --evidence-out {RERUN_EVIDENCE.relative_to(ROOT)}')
    main_pass = (rc == 0 and RERUN_VERDICT.is_file())
    log(f"[正控B] 全量跑 rc={rc} ⇒ {'PASS' if main_pass else 'FAIL'}  {out.strip().splitlines()[-1][:160] if out.strip() else ''}")

    # 3) 零回归: 逐键比对 (白名单单键)
    zr = {'pass': False, 'diffs': {}, 'added_keys': [], 'whitelist': sorted(WHITELIST)}
    if RERUN_VERDICT.is_file():
        a = json.loads(ARCH_VERDICT.read_text(encoding='utf-8'))
        b = json.loads(RERUN_VERDICT.read_text(encoding='utf-8'))
        zr['added_keys'] = sorted(set(b) - set(a))
        zr['removed_keys'] = sorted(set(a) - set(b))
        for k in sorted(set(a) & set(b)):
            if k in WHITELIST:
                zr['whitelisted'] = [k, a[k], b[k]]
                continue
            if json.dumps(a[k], sort_keys=True, ensure_ascii=False) != json.dumps(b[k], sort_keys=True, ensure_ascii=False):
                zr['diffs'][k] = {'archived': a[k], 'rerun': b[k]}
        ev_bytes_same = (RERUN_EVIDENCE.is_file() and
                         sha256(RERUN_EVIDENCE) == sha256(ARCH_EVIDENCE))
        zr['evidence_bytes_identical'] = bool(ev_bytes_same)
        zr['pass'] = (not zr['diffs'] and not zr['removed_keys'] and zr['added_keys'] == []
                      and ev_bytes_same and 'whitelisted' in zr)
    log(f"[零回归] 除白名单外逐位相同={not zr['diffs']} 白名单={zr.get('whitelisted')} "
        f"新增键={zr['added_keys']} evidence 逐字节相同={zr.get('evidence_bytes_identical')} ⇒ {'PASS' if zr['pass'] else 'FAIL'}")

    # 4) 负控: 注入矩阵
    inj_rows, inj_pass = [], True
    for kind, prim, exp_rc, exp_marker in INJ:
        nrc, nout = q13(f'--inject-defect={kind}')
        # 判定行 = 含 primary_red= 的那一行 (INJECT_NO_WRITE_ENFORCED 是前置提示行, 不是结论行)
        marker = next((ln.split()[0] for ln in nout.splitlines() if 'primary_red=' in ln), None)
        red = []
        for ln in nout.splitlines():
            if 'observed_red=' in ln:
                try:
                    red = json.loads(ln.split('observed_red=')[1].split(' expect_rc=')[0].replace("'", '"'))
                except Exception:
                    red = ln.split('observed_red=')[1].split(' expect_rc=')[0]
        spec = (kind, prim, exp_rc, exp_marker)
        primary_red_ok = bool((len(red) == 0) if prim is None else (prim in red))
        ok = judge_injection(spec, nrc, marker, red)
        inj_pass &= ok
        inj_rows.append({'kind': kind, 'primary_red': prim, 'expect_rc': exp_rc, 'rc': nrc,
                         'marker': marker, 'expect_marker': exp_marker, 'observed_red': red, 'ok': bool(ok)})
        log(f"[负控] {kind:24s} rc={nrc}(期望{exp_rc}) marker={marker} primary_in_red={primary_red_ok} red={red} ⇒ {'OK' if ok else 'FAIL'}")

    # 4b) driver 编码器自检: 反向喂入必须判 False (证明编码器有判别力, 而不是恒真)
    enc_neg = judge_injection(('phantom-ineffective', 'C1_conservation', 3, 'INJECT_NOT_RED'),
                              3, 'INJECT_NOT_RED', ['C1_conservation'])
    enc_pos = judge_injection(('phantom-noop', None, 0, 'INJECT_APPLIED_NOOP_OK'), 0,
                              'INJECT_APPLIED_NOOP_OK', [])
    enc_red = judge_injection(('caliber-delta-applied', 'C3_ruling_A_landed', 2, 'INJECT_APPLIED'),
                              2, 'INJECT_APPLIED', ['C3_ruling_A_landed'])
    encoder_selftest = {'inverted_case_judged_false': (enc_neg is False),
                        'noop_case_judged_true': (enc_pos is True),
                        'applied_case_judged_true': (enc_red is True)}
    encoder_selftest['pass'] = all(encoder_selftest.values())
    log(f"[编码器自检] 反向喂入判 False={enc_neg is False} 空红桩=True={enc_pos is True} "
        f"缺陷注入桩=True={enc_red is True} ⇒ {'OK' if encoder_selftest['pass'] else 'FAIL'}")

    # 5) fail-closed: 未知 kind
    urc, uout = q13('--inject-defect=__not-a-kind__')
    uok = (urc == 3 and 'INJECT_UNKNOWN_KIND' in uout)
    log(f"[fail-closed] 未知 kind rc={urc} marker={uout.splitlines()[0][:60] if uout else None} ⇒ {'OK' if uok else 'FAIL'}")

    # 6) 自洁: Q13 轮次目录未被本轮矩阵改动
    q13dir_after = {p.name: sha256(p) for p in sorted(Q13DIR.iterdir()) if p.is_file()}
    dirty = sorted(k for k in set(q13dir_before) | set(q13dir_after)
                   if q13dir_before.get(k) != q13dir_after.get(k))
    log(f"[自洁] eval/capability/exp1-q13/ 内容变化={dirty} ⇒ {'OK' if not dirty else 'FAIL'}")

    all_pass = bool(st_pass and main_pass and zr['pass'] and inj_pass and uok and not dirty
                    and encoder_selftest['pass'])
    code = 0 if all_pass else 2
    log('')
    log(f"Q20_EXIT={code}  (0 判据全过 / 2 判据失败 / 3 测量或环境失败)")
    log(f"汇总: 正控A={st_pass} 正控B={main_pass} 零回归={zr['pass']} 负控{sum(r['ok'] for r in inj_rows)}/{len(inj_rows)} "
        f"fail-closed={uok} 自洁={not dirty}")

    verdict = {
        'round': 'EXP1-Q20', 'marker': f'Q20_EXIT={code}',
        'object': 'eval/capability/exp1-q13/index_scope_out_classify.py (2.7.0 -> 2.8.0, 纯加性)',
        'change': '外部可调用缺陷注入入口 --inject-defect=<kind> (8 kind: 6 缺陷注入 + 2 审计桩) + 输出面 --out/--evidence-out; 判据表达式零改动',
        'prereg': 'eval/capability/exp1-q20/prereg_q20.json',
        'readings': {
            'preflight_archive_sha256': pre,
            'selftest': {'rc': rc, 'n': len(st.get('selftest', {})), 'all_pass': st.get('all_pass'), 'pass': st_pass},
            'main_run': {'pass': main_pass, 'rerun_verdict': str(RERUN_VERDICT.relative_to(ROOT))},
            'zero_regression': zr,
            'injections': inj_rows,
            'fail_closed_unknown_kind': {'rc': urc, 'ok': uok},
            'driver_encoder_selftest': encoder_selftest,
            'self_clean_q13_dir': {'dirty': dirty, 'ok': not dirty},
            'q13_artifact_sha256': {k: v for k, v in q13dir_after.items()},
        },
        'criterion': '正控(signature 7/7 ∧ 全量 rc=0) ∧ 零回归(除白名单单键外逐位相同 ∧ evidence 逐字节相同) ∧ 8/8 注入按预注册红 ∧ fail-closed rc=3 ∧ 不弄脏 Q13 轮次产物',
        'verdict': 'PASS' if all_pass else 'FAIL',
        'evidence_level': 'L2-static (真机执行 + 注入矩阵 + 逐位比对; 无编译/测试/AOT ⇒ 不报 L3/L4)',
        'driver_defects_fixed_in_round': [
            'driver 首版缺陷①: 结论行取「首个以 INJECT_ 开头的行」⇒ 取到前置提示 INJECT_NO_WRITE_ENFORCED ⇒ 8/8 假红; 修 = 取含 primary_red= 的行',
            'driver 首版缺陷②: 期望编码只判「primary 必须在红集合内」⇒ 把 phantom-ineffective 的 fail-closed 证明反判为 FAIL (读数 7/8); 修 = 按 expect_marker 分三型编码 + 编码器自检 (反向喂入必须判 False)',
            '两处均为 driver(测量层)缺陷, 非判据变更: 预注册判据/prereg_q20.json 逐字未动, 修正后仍按同一判据判定',
        ],
        'honest_boundaries': [
            '注入面只证明**既有判据**对已知缺陷有判别力; 不证明判据口径本身完整 (词法代理量的既有边界不变)',
            'suffix-set-hardcoded 注入按预注册产生 cascade (桶划分随之变化 ⇒ C3/C5 一并红), 已逐条如实记录, 不以「只红一条」为通过条件',
            'phantom-* 两个审计桩证明 fail-closed 分支可达, 不构成产品侧能力',
            '形式校验 (dotnet) 仍结转: 对侧 R462 W 臂探针 + llama-server 在场, MemAvailable 低于 2800MB 闸',
        ],
        'next': '形式校验结转清账 (对侧空闲时) → 旧 11 行输入指纹补全 → relocated 面正例语料 / 阶段B 可配语言集 (各独立预注册轮次)',
    }
    (SELF / 'verdict_q20.json').write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding='utf-8')
    (SELF / 'evidence_q20.txt').write_text('\n'.join(ev) + '\n', encoding='utf-8')
    print('\n'.join(lines))
    print(f"落盘 {SELF.relative_to(ROOT)}/verdict_q20.json + evidence_q20.txt")
    return code


if __name__ == '__main__':
    sys.exit(main())
