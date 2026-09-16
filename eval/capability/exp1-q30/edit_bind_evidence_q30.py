#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q30 · 候选①-b: 给 eval/capability/bind_evidence.py 加 `--only <ids>` 定向重审 + `--registry <path>`。

动机 (承 EXP1-Q29 AD.4③ 粒度缺口):
  Q29 恢复了整文件序列化通路 (可写), 但 `--apply` 的粒度仍是**全表 needs_field 重审**
  (TOUCHED=104 = 103 行只动 audited_by_round 的纯 churn)。单行重审此前只能走块级文本插入 ⇒
  「同一条通路, 两种写法」, 判据无法机检。本步把粒度收窄到目标行, 并加 scratch 副本入口。

设计约束 (fail-closed):
  1. `--only` 与 `--apply` 同用时**必须显式给 `--round`** —— 否则默认常量 R473 会把目标行的审计戳
     写成**更早的轮号**(归属回退); 缺省 ⇒ rc=3 且零字节写入。
  2. 未知 id ⇒ rc=3 且零字节写入 (不静默忽略 —— 静默忽略会让「定向重审」变成空转绿)。
  3. 无参调用 (无 --only/--registry) ⇒ 行为**逐字不变** (本脚本改完立即以 scratch 副本做零回归比对)。

本脚本幂等: 已应用则报 ALREADY_APPLIED 并 rc=0, 不重复改写。
"""
import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]   # eval/capability/exp1-q30 -> repo root
TARGET = ROOT / 'eval/capability/bind_evidence.py'

P_ARGS_OLD = '''    ap.add_argument("--round", default=AUDITED_BY_ROUND,
                    help="写入/复核 audited_by_round 的轮号 (默认 %s ⇒ 历史行为逐字不变)" % AUDITED_BY_ROUND)
    a = ap.parse_args()
    AUDITED_BY_ROUND = a.round   # 默认 = 历史常量 ⇒ 无参调用行为逐字不变'''

P_ARGS_NEW = '''    ap.add_argument("--round", default=None,
                    help="写入/复核 audited_by_round 的轮号 (默认 %s ⇒ 历史行为逐字不变)" % AUDITED_BY_ROUND)
    ap.add_argument("--only", default=None,
                    help="定向范围: 逗号分隔的登记行 id; 与 --apply 同用时必须同时显式给 --round, "
                         "未知 id 或缺少轮号 ⇒ rc=3 且零字节写入")
    ap.add_argument("--registry", default=REG,
                    help="登记表路径 (默认 %s; 供 scratch 副本核验 —— 真登记表不被触碰)" % REG)
    a = ap.parse_args()
    explicit_round = a.round is not None
    AUDITED_BY_ROUND = a.round if explicit_round else AUDITED_BY_ROUND   # 默认 = 历史常量 ⇒ 无参调用行为逐字不变'''

P_REG_OLD = '''    reg_abs = os.path.join(root, REG)'''
P_REG_NEW = '''    reg_rel = a.registry
    reg_abs = reg_rel if os.path.isabs(reg_rel) else os.path.join(root, reg_rel)'''

P_SCOPE_OLD = '''    if a.apply:'''
P_SCOPE_NEW = '''    ids = None
    if a.only:
        ids = [s.strip() for s in a.only.split(",") if s.strip()]
    if ids is not None:
        # 定向范围的前置核验 (fail-closed): 未知 id / --apply 缺显式轮号 一律 rc=3 零写入。
        known = {r.get("id") for r in rows}
        unknown = [i for i in ids if i not in known]
        if unknown:
            print("ONLY_SCOPE=UNKNOWN_IDS %s (fail-closed, 零字节写入)" % sorted(unknown))
            return 3
        if a.apply and not explicit_round:
            print("ONLY_SCOPE=REQUIRES_EXPLICIT_ROUND (定向重审缺显式 --round ⇒ rc=3, 零字节写入)")
            return 3
        print("ONLY_SCOPE=n=%d %s" % (len(ids), ",".join(ids)))

    if a.apply:'''

P_LOOP_OLD = '''        tracked, dirty = git_state(root)
        n_before = sum(1 for r in rows if "evidence_generated_with" in r)
        unchanged = 0
        for row in rows:
            if needs_field(row):
                f = derive(root, row, tracked, dirty)
                if row.get("evidence_generated_with") == f:
                    # EXP1-Q27 最小 diff 纪律: 派生内容逐字段相同 ⇒ 一个字节都不动。
                    #   (此前每次 --apply 会重刷全部行的 audited_by_round ⇒ 92 行 churn 淹没真实改动;
                    #    且会把并发写者上一轮的审计戳改成自己的轮号 = 归属篡改。)
                    unchanged += 1
                    continue
                if "evidence_generated_with" in row:
                    row["evidence_generated_with"] = f
                else:
                    # 保序插入: 置于 evidence_path 之后 (与它绑定的字段相邻)
                    keys = list(row.keys())
                    pos = keys.index("evidence_path") + 1 if "evidence_path" in keys else len(keys)
                    items = list(row.items())
                    row.clear()
                    for i, (k, v) in enumerate(items):
                        if i == pos:
                            row["evidence_generated_with"] = f
                        row[k] = v
                    if "evidence_generated_with" not in row:
                        row["evidence_generated_with"] = f'''

P_LOOP_NEW = '''        tracked, dirty = git_state(root)
        # EXP1-Q30: 粒度收窄 —— needs_field ∧ (无 --only ∨ id ∈ --only)。无 --only 时 scope == 全表 ⇒ 历史行为不变。
        scope_rows = [r for r in rows if needs_field(r) and (ids is None or r.get("id") in ids)]
        n_before = sum(1 for r in scope_rows if "evidence_generated_with" in r)
        unchanged = 0
        for row in scope_rows:
            f = derive(root, row, tracked, dirty)
            if row.get("evidence_generated_with") == f:
                # EXP1-Q27 最小 diff 纪律: 派生内容逐字段相同 ⇒ 一个字节都不动。
                #   (此前每次 --apply 会重刷全部行的 audited_by_round ⇒ 92 行 churn 淹没真实改动;
                #    且会把并发写者上一轮的审计戳改成自己的轮号 = 归属篡改。)
                unchanged += 1
                continue
            if "evidence_generated_with" in row:
                row["evidence_generated_with"] = f
            else:
                # 保序插入: 置于 evidence_path 之后 (与它绑定的字段相邻)
                keys = list(row.keys())
                pos = keys.index("evidence_path") + 1 if "evidence_path" in keys else len(keys)
                items = list(row.items())
                row.clear()
                for i, (k, v) in enumerate(items):
                    if i == pos:
                        row["evidence_generated_with"] = f
                    row[k] = v
                if "evidence_generated_with" not in row:
                    row["evidence_generated_with"] = f'''

P_COUNT_OLD = '''        n_after = sum(1 for r in rows if "evidence_generated_with" in r)
        print("COVERED %d -> %d" % (n_before, n_after))
        print("UNCHANGED=%d / TOUCHED=%d" % (unchanged, n_after - unchanged))
        print(subprocess.run(["git", "diff", "--numstat", REG], cwd=root, capture_output=True, text=True).stdout.strip())'''

P_COUNT_NEW = '''        n_after = sum(1 for r in scope_rows if "evidence_generated_with" in r)
        n_total = sum(1 for r in rows if "evidence_generated_with" in r)
        print("SCOPE=%s" % ("full" if ids is None else "only(n=%d)" % len(ids)))
        print("COVERED %d -> %d (scope); 全表 COVERED=%d" % (n_before, n_after, n_total))
        print("UNCHANGED=%d / TOUCHED=%d (scope)" % (unchanged, n_after - unchanged))
        if os.path.isabs(reg_rel):
            print("NUMSTAT=skip (scratch 副本, 非仓内路径)")
        else:
            print(subprocess.run(["git", "diff", "--numstat", reg_rel], cwd=root,
                                 capture_output=True, text=True).stdout.strip())'''

P_CHECK_OLD = '''    v, dist, cert = check(root, json.loads(open(reg_abs, encoding="utf-8").read())["rows"])
    print("CHECKED_WITH_FIELD=%d" % cert)'''

P_CHECK_NEW = '''    crows = json.loads(open(reg_abs, encoding="utf-8").read())["rows"]
    if ids is not None:
        crows = [r for r in crows if r.get("id") in ids]
    v, dist, cert = check(root, crows)
    print("CHECKED_WITH_FIELD=%d" % cert)
    if ids is not None:
        print("DIST_SCOPE=only(n=%d) —— 与全表口径分布不可比" % len(crows))'''

PATCHES = [('args', P_ARGS_OLD, P_ARGS_NEW), ('reg', P_REG_OLD, P_REG_NEW),
           ('scope', P_SCOPE_OLD, P_SCOPE_NEW), ('loop', P_LOOP_OLD, P_LOOP_NEW),
           ('count', P_COUNT_OLD, P_COUNT_NEW), ('check', P_CHECK_OLD, P_CHECK_NEW)]


def main():
    raw = TARGET.read_text(encoding='utf-8')
    if 'ONLY_SCOPE=n=' in raw and 'scope_rows' in raw:
        print('ALREADY_APPLIED (幂等, rc=0); sha256[:12]=%s'
              % hashlib.sha256(raw.encode()).hexdigest()[:12])
        return 0
    shas = {}
    for name, o, n in PATCHES:
        c = raw.count(o)
        if c != 1:
            print('PATCH_FAIL %s: old_text 出现 %d 次 (要求 1) ⇒ 零字节写入' % (name, c))
            return 1
        raw = raw.replace(o, n, 1)
        shas[name] = 'applied'
    TARGET.write_text(raw, encoding='utf-8')
    back = TARGET.read_text(encoding='utf-8')
    assert back == raw, 'readback mismatch'
    print('APPLIED 6/%d patches: %s' % (len(PATCHES), sorted(shas)))
    print('sha256[:12]=%s' % hashlib.sha256(back.encode()).hexdigest()[:12])
    return 0


if __name__ == '__main__':
    sys.exit(main())
