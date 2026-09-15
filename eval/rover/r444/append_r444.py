#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R444 台账双写 (并发追加安全): eval/capability/kpi.jsonl + docs/verification-registry.json.

铁律要点:
  - kpi.jsonl 并发追加 ⇒ 只 append, 禁取末行做定位;
  - registry 原文 EOF 无换行 ⇒ 必须按原尾还原 (json.dumps 会加换行, 须核对);
  - 写后 roundtrip 校验 (行数 + 末行 id), 失败即非零退出。
用法: python3 eval/rover/r444/append_r444.py [--dry-run]
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
KPI = ROOT / 'eval/capability/kpi.jsonl'
REG = ROOT / 'docs/verification-registry.json'

KPI_ROW = {
    "round": "R444",
    "ts": __import__('datetime').datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
    "kind": "cheap-necessary-condition-prefilter(provably-equivalent)+short-tier-token-truth",
    "artifact": ("eval/rover/r444/{README-evidence.md,verdict-r444-analysis.json,precheck_prefilter.py,"
                 "analyze_r444.py,run_arm_r444.sh,run_all_r444.sh,settle_r444.py,"
                 "verdict-A-M20-s4.json,verdict-BRJ-M20-s4.json,verdict-BRJL-M20-s4.json,"
                 "verdict-A-V2b-s4.json,verdict-BRJ-V2b-s4.json,verdict-A-W8-s4.json,verdict-BRJ-W8-s4.json}"),
    "grid": "M20+V2b+W8",
    "bin_sha": "e36d04d1988cdda1f56021c80d22b684e3815121bd03e8d40602f621af2c0658",
    "readouts": {}   # 由 --readouts-json 传入
}

REG_ROWS = [
    {"id": "r444.prefilter-equivalence",
     "capability": ("**廉价必要条件前置 (¬Ack ⇒ Pass) — 可证等价 + 含本地真值口径首次转正**: "
                    "把既有的后置否决 `Skip ∧ ¬MechanicalAck ⇒ Pass` 反解为不变量 `Skip ⇒ Ack`, "
                    "其逆否 `¬Ack ⇒ Pass`(与 r1 输出无关) ⇒ 把 Ack 前置为调用前守门, 判决路径逐位等价地省掉该轮本地 r1。"
                    "默认开 + AGENTFRAMEWORK_GATE_PREFILTER=0 消融。M20 同网格同 NS 三臂 A/B**RJ/B**RJL = "
                    "61256/32968/32972; 门 r1 调用 **7 vs 17**(−59%); 本地真值 7880 vs 12775(省 **4895 tok / 10 次 = 489.5/次**); "
                    "口径三档 远端 **46.18%** / +本地折算 39.24% / **+本地真值 33.32%**(R443 同口径 25.32%) ⇒ **≥30% 达标**; "
                    "D4 逐轮差异 **0/20 轮**; 质量 BRJ/BRJL fn=0∧fp=0∧acc=1.0。"
                    "附带负向发现与修复: R443 真值遥测**粘滞继承**上次调用值 ⇒ 机械行虚增 6 行/2382 tok(会把 33.32% 压成 29.43%), "
                    "修复版 c28e86d3 单变量复跑 ⇒ 粘滞 6→0、逐轮 0 差异。"),
     "level": "L3", "owner_round": "R444",
     "evidence_cmd": "python3 eval/rover/r444/analyze_r444.py",
     "evidence_path": "eval/rover/r444/verdict-r444-analysis.json",
     "negative_control": "BRJL 臂(AGENTFRAMEWORK_GATE_PREFILTER=0)必须观测到 gate:skip_rejected_nonack ≥3(否则'不变量不可达'空心); BRJ 臂必须 0 条且 prefilter_violations=0",
     "covers": ["src/agent/IndustrialAgentV2.cs", "src/agent.modelqueue/LocalGenerationPort.cs"]},
    {"id": "r444.prefilter-cost", "capability": "前置门本地 r1 成本下降(真值口径)",
     "level": "L3", "owner_round": "R444",
     "evidence_cmd": "python3 eval/rover/r444/analyze_r444.py",
     "evidence_path": "eval/rover/r444/verdict-r444-analysis.json",
     "negative_control": "门 r1 调用数必须 BRJ<BRJL 且真值 token 差 >0; 用「字符/2」折算复算必须方向一致但幅度不同(证折算低估)",
     "covers": ["src/agent/IndustrialAgentV2.cs"]},
    {"id": "r444.separability-precheck", "capability": "R423 可分性预检(Skip⇒Ack 必要性)",
     "level": "L4", "owner_round": "R444",
     "evidence_cmd": "python3 eval/rover/r444/precheck_prefilter.py",
     "evidence_path": "eval/rover/r444/precheck-prefilter.json",
     "negative_control": "--neg-control 注入非 ack 的 Skip 轮必须检出 ≥1 反例; --grid-dir /nonexistent 必须 fail-closed 非零",
     "covers": ["eval/rover/r444/precheck_prefilter.py"]},
    {"id": "r444.status-single-audit", "capability": "L3 单一审计面(registry 派生)",
     "level": "L4", "owner_round": "R444",
     "evidence_cmd": "python3 eval/capability/status_gen.py --check",
     "evidence_path": "docs/reports/status.json",
     "negative_control": "bash eval/capability/_nc_status_gen.sh —— 注入 evidence_path 分号串联坏行必须判 FAIL 非零",
     "covers": ["eval/capability/status_gen.py"]},
    {"id": "r444.instrument-acceptance", "capability": "L2 器具验收面(正控+负控成对)",
     "level": "L4", "owner_round": "R444",
     "evidence_cmd": "python3 eval/capability/instruments_check.py",
     "evidence_path": "eval/capability/instruments-check.json",
     "negative_control": "每条器具必带 nc_cmd 且必须非零; 缺负控的器具不许进面",
     "covers": ["eval/capability/instruments_check.py", "eval/capability/instruments.json"]},
    {"id": "r444.writer-arbitration", "capability": "L4 写者仲裁(心跳+pre-commit)",
     "level": "L4", "owner_round": "R444",
     "evidence_cmd": "bash eval/capability/_nc_hook_claim.sh",
     "evidence_path": "tools/hooks/pre-commit",
     "negative_control": "伪造另一写者的新鲜心跳 ⇒ pre-commit 必须非零拒绝; 无心跳时必须 0(正控)",
     "covers": ["tools/hooks/pre-commit", "tools/round_claim.sh"]},
    {"id": "r444.short-tier-truth", "capability": "短档/单跳档本地真值补列",
     "level": "L3", "owner_round": "R444",
     "evidence_cmd": "python3 eval/rover/r444/analyze_r444.py",
     "evidence_path": "eval/rover/r444/verdict-r444-analysis.json",
     "negative_control": "缺臂(无同网格同 NS 分母臂)时分析器必须非零退出, 禁跨网格代理",
     "covers": ["eval/rover/r444/analyze_r444.py"]},
]


def append_kpi(readouts):
    row = dict(KPI_ROW)
    row['readouts'] = readouts
    line = json.dumps(row, ensure_ascii=False) + '\n'
    with KPI.open('a', encoding='utf-8') as f:
        f.write(line)
        f.flush()
    # roundtrip: 该行必须能被读回
    back = json.loads(KPI.read_text(encoding='utf-8').splitlines()[-1])
    assert back['round'] == 'R444', 'kpi 追加回读失败'
    return {'lines': len([l for l in KPI.read_text(encoding='utf-8').splitlines() if l.strip()]),
            'appended': row['kind']}


def append_registry():
    raw = REG.read_text(encoding='utf-8')
    had_nl = raw.endswith('\n')
    d = json.loads(raw)
    ids = {r.get('id') for r in d['rows']}
    added = 0
    for r in REG_ROWS:
        if r['id'] in ids:
            continue
        d['rows'].append(r)
        added += 1
    d['updated_round'] = 'R444'
    txt = json.dumps(d, ensure_ascii=False, indent=2)
    if had_nl:
        txt += '\n'
    REG.write_text(txt, encoding='utf-8')
    # roundtrip
    back = json.loads(REG.read_text(encoding='utf-8'))
    assert len(back['rows']) == len(d['rows']), 'registry 行数回读不一致'
    tail = REG.read_text(encoding='utf-8')[-2:]
    assert (tail.endswith('\n') if had_nl else not tail.endswith('\n')), f'EOF 尾形状被改: {tail!r}'
    return {'added': added, 'rows': len(back['rows']), 'eof_newline': had_nl, 'tail': tail}


if __name__ == '__main__':
    readouts = {}
    if '--readouts-json' in sys.argv:
        readouts = json.loads(pathlib.Path(sys.argv[sys.argv.index('--readouts-json') + 1]).read_text(encoding='utf-8'))
    if '--dry-run' in sys.argv:
        print('DRY-RUN readouts =', json.dumps(readouts, ensure_ascii=False)[:300])
        print('registry 将追加', len(REG_ROWS), '行')
        sys.exit(0)
    print('kpi:', json.dumps(append_kpi(readouts), ensure_ascii=False))
    print('registry:', json.dumps(append_registry(), ensure_ascii=False))
