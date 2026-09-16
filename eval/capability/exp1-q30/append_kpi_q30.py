#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q30 · 把本轮读数**幂等**追加进 eval/capability/kpi.jsonl (按 round 去重)。

纪律: 读数一律从**落盘 verdict/census 文件机取**, 不手抄 (防转录错误与「凑数」)。
"""
import datetime
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
KPI = os.path.join(ROOT, 'eval/capability/kpi.jsonl')
Q = os.path.join(ROOT, 'eval/capability/exp1-q30')
ROUND = 'EXP1-Q30'


def jload(rel):
    p = os.path.join(ROOT, rel)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None


def main():
    rows = []
    for line in open(KPI, encoding='utf-8-sig'):
        if line.strip():
            rows.append(json.loads(line))
    if any(r.get('round') == ROUND for r in rows):
        print('IDEMPOTENT=OK (round %s 已在台账中)' % ROUND)
        return 0
    only = jload('eval/capability/exp1-q30/verdict_q30_only.json') or {}
    part = jload('eval/capability/exp1-q30/verdict_q30_face_partition.json') or {}
    cens = jload('eval/capability/exp1-q30/instrument_gap_census_q30.json') or {}
    probe = jload('eval/capability/exp1-q30/full_face_trace_probe_q30.json') or {}
    extra = jload('eval/capability/exp1-q30/verdict_q30_extra.json') or {}
    rec = {
        'round': ROUND,
        'ts': datetime.datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M%z'),
        'kind': 'self-check / 候选①-b 定向重审粒度收窄 (--only) + 面别分区 (scoped 不再覆盖全量面记录) + '
                '器具面扩容 (3 条新器具) + 未派生器具行普查分类 + 跨写者提交闸 (60m 自检作业, 不占主线轮号)',
        'artifact': 'eval/capability/exp1-q30/{prereg_q30.json,verify_q30_only.py,verdict_q30_only.json,'
                    'verify_q30_face_partition.py,verdict_q30_face_partition.json,check_committed_state_q30.py,'
                    '_nc_bind_evidence_pin.sh,_nc_wl_identity_q30.py,rewrite_evidence_cmd_q30.py,'
                    'instrument_gap_census_q30.py,instrument_gap_census_q30.json,apply_repin_rows_q30.py,'
                    'stage_guard_q30.py,measure_full_face_q30.py,edit_*.py,round_artifact_list_q30.txt}; '
                    'eval/capability/{bind_evidence.py,instruments_check.py,instruments.json,'
                    'instruments-check.json,instruments-check-scoped.json}; docs/verification-registry.json; '
                    'docs/plans/v0.22.0-exp1-local-index-and-code-graph.md (附录 AE)',
        'change': '① 候选①-b: bind_evidence 加 `--only <ids>` 定向重审 + `--registry` scratch 入口; '
                  '与 --apply 同用必须显式 --round (否则 rc=3 零写入, 防审计戳回退), 未知 id 亦 rc=3 零写入。'
                  '② 候选② 前提核验: Q28 记的 6 条陈旧 worktree-only 声明已由主线 R481 (e3f7a44「96 行纯归属漂移回退」) '
                  '闭合 ⇒ 重算口径 0 条 ⇒ 本轮零改动收口 (not 重复劳动)。'
                  '③ 候选③: 4 行未派生器具改为指向仓库内**真实生产者** (逐条 grep 机检「该脚本确实写这个产物」才改; '
                  '首版误把 r462_run.sh 当 verdict 写入者 ⇒ 机检拒改, 已换 judge_r462.py), 9 → 5 条残留 (分类普查)。'
                  '④ 候选④: 全量面首跑 (Q21 后首次, 21 器具) —— 归因闸 LOG_SOFT_CAP=8MiB 对全量面结构性过小 '
                  '(实测 trace-capped ⇒ 弃权 rc=3), 按实测重定阈值 (数据先行)。'
                  '⑤ 候选⑤: instruments_check 面别分区 (full/scoped/negative-control + --out + 产物自带 face/器具 sha)。'
                  '⑥ 候选⑥: 3 条新器具进 L2 (bind_evidence.check / committed-state / whitelist-coverage), 各配注入负控。'
                  '⑦ 候选⑦: stage_guard (staged == 本轮清单; 对侧在飞文件多出即拒绝提交)。',
        'readings': {
            '候选①-b 判据 (verdict_q30_only.json)': '%s checks, verdict=%s' % (only.get('n_checks'), only.get('verdict')),
            '①-b 关键等价': {'A_sha12': only.get('readings', {}).get('A_sha12'),
                             'B_sha12': only.get('readings', {}).get('B_sha12'),
                             'diff_keys': only.get('readings', {}).get('block_changed_keys'),
                             '旧器具全表对照 TOUCHED': only.get('readings', {}).get('C_stdout_touched')},
            '①-b 作用域': only.get('readings', {}).get('changed_rows'),
            '①-b 无参零回归': {'check_stdout_equal': only.get('checks', {}).get('P8_无参零回归_check'),
                               'apply_sha_equal': only.get('readings', {}).get('zeroregress_apply')},
            '面别分区 (verdict_q30_face_partition.json)': part.get('checks'),
            '面别分区读数': part.get('readings', {}).get('nc_old'),
            'scoped 面产物': part.get('readings', {}).get('scoped'),
            '残留未派生器具 (census)': {k: cens.get(k) for k in ('derived_instrument', 'no_instrument', 'by_reason_class')},
            '全量面 trace 体量探针': {k: probe.get(k) for k in ('commands', 'log_bytes', 'capped', 'probe_rc',
                                                              'passed', 'total', 'failed_ids')},
            '其余读数': extra,
        },
        'honest_boundaries': [
            '候选② (6 条陈旧声明) 前提**已为假**: 重算 0 条 ⇒ 本轮零改动, 归属 = 对侧/前序提交 (R481 e3f7a44), 本侧自跑复核。',
            '残留 **5 行**未派生器具 (engine.retired.no_local_gguf / llamacpp.prompt.template_gate / r420.recall-command-wiring / '
            'r462.weight-probe / r463.model-cleanup): 证据面是文档/目录/一次性 /tmp 脚本/python3 -c 读表达式 ⇒ 无单一仓库内器具可绑定, '
            '本轮只做分类普查与计数 (不猜器具); 其中 2 行 (r462.weight-probe, r463.model-cleanup) 的产物写入者不在仓库内 = 真实缺口。',
            'verify_q30_only 首跑 2 红 (A_rc / P1) 均为**我方判据实现缺陷** (真值化写错 + 路径 B 未对齐轮号), 照原样入档后修正重跑; '
            '等价判定因此只对「同一轮号参数」成立。',
            'rewrite_evidence_cmd_q30 的 CHANGED_ROWS 不变式是**空转**: 它与就地改过的同一批 dict 比较 ⇒ 恒为空; '
            '真实证据 = numstat 8/8 + 写后读回 + 幂等重跑 IDEMPOTENT。',
            '两处自引用行 (r444/r476) 的重审按**文件字节**算 pin (未提交态; 提交后该字节即冻结态), 走块级替换而非 --only —— '
            '--only 的 derive 读 git 状态, 未提交文件结构性只能派生成 live/worktree-only。',
            '--only 的轮号戳 churn 语义: 4 行 (首次) + 3 行 (器具变更后) 的审计戳更新为 EXP1-Q30, 其中内容无变化的行是纯归属更新 '
            '(最小 diff 纪律只保证「派生内容不变则不动」, 不覆盖显式换轮号的复核语义)。',
        ],
        'next': '候选③ 剩余 5 行的处置裁定 (是否接受「文档/目录/一次性脚本」为永久口径, 或改证据面形态); '
                '全量面在新阈值下的稳定复跑 (跨日/跨会话) 与 r444 证据行的下一轮重审; '
                '把 stage_guard 纳入提交前钩子面 (与 pre-commit 器具同批) 并机检其对对侧在飞文件的拒绝能力。',
        'owner_round': ROUND,
    }
    with open(KPI, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    back = [json.loads(x) for x in open(KPI, encoding='utf-8-sig') if x.strip()]
    ok = back[-1].get('round') == ROUND and len(back) == len(rows) + 1
    print('APPEND=%s (行数 %d -> %d)' % ('OK' if ok else 'FAIL', len(rows), len(back)))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
