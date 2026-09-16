#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""面记录**确定化**层 (EXP1-Q33 · C3) —— 把运行期非语义字段移出被 pin 的字节面。

动因 (Q32 §AG.6.2): `r444.instrument-acceptance` 的冻结 pin 语义是「**提交时点快照**」——
面记录内含 `side_effect_attribution.window.{t0,t1,trace_dir}` (墙钟 + 随机 mkdtemp 目录名),
⇒ **同一命令重跑必然改字节** ⇒ 任何重跑都把冻结 pin 打红 (`bind_evidence --check` 转红, 实证 AG.5.6)。
判定缺陷不是「pin 太严」, 而是**被 pin 的字节面里混进了非语义字段** (skill 铁律: 「逐位相等」判据
必须先声明**非语义字段白名单**)。

本模块 = 唯一实现 (面写出方 `instruments_check.py` 调 `write_record`), 契约:
  · `RUNTIME_FIELDS` —— **声明的**非语义字段清单 (JSON 路径), 值移入侧车 `<record>.runtime.json`;
    记录里原位写哨兵 `<runtime>` ⇒ 记录本身只剩语义内容。
  · 内嵌的同一随机串 (trace_dir 值) 全量替换为哨兵 (防同一随机串散落多处)。
  · 侧车缺/不可解析 ⇒ 调用方判**弃权**(rc=3), 不判绿 (见 instruments_check.py 集成点)。
  · 自检 `--selftest`: ①运行期置换 ⇒ 摘要相同; ②语义扰动 ⇒ 摘要必不同 (非平凡); ③哨兵声明的字段
    必须真实存在于记录 (防「声明了不存在的字段」的空心白名单); ④侧车可回读且含被移出的值。
"""
import hashlib
import json
import os
import sys

SENTINEL = '<runtime>'
# 声明的非语义字段 (JSON 路径); 判据只比较**去掉这些字段后**的字节
RUNTIME_FIELDS = (
    ('side_effect_attribution', 'window', 't0'),
    ('side_effect_attribution', 'window', 't1'),
    ('side_effect_attribution', 'window', 'trace_dir'),
)
RUNTIME_NOTE = ('t0/t1 = 墙钟采样; trace_dir = tempfile.mkdtemp 随机目录 ⇒ 同命令重跑必变, 非语义。'
                '移入侧车后, 记录字节只随**语义内容** (器具结果/读数/守恒式) 变化。')


def sha12(blob):
    if isinstance(blob, str):
        blob = blob.encode('utf-8')
    return hashlib.sha256(blob).hexdigest()[:12]


# ── 语义投影 (C3-b): 由**两次真跑实测差分**得出的运行期字段族 (不是猜的) ──────────────
# 证据: `/tmp/q33_A.json` vs `/tmp/q33_B.json` (同面 `--only probe.grade`, 同树, 相隔 2 s),
# 74 条差异叶子全部落在下表路径族内; 其余 (results/manifest_sha12/conservation/trace 计数…) 逐位相同。
# 模式: scalar = 值换哨兵; array_count = 整族换 {_nonsemantic, n} (保留基数, 去掉邻居/随机内容)。
#
# **单一事实源 (EXP1-Q34)**: 规则表移入数据文件 `projection_rules.json` —— 本模块与仓库测试侧
# (登记表 R2e 的 pin_kind=semantic-projection 判据) **读同一文件**复算同一摘要, 跨语言口径靠构造一致,
# 而非靠两份手抄保持一致 (手抄会静默漂移)。文件缺失/不可解析 ⇒ 抛错 (fail-closed, 空规则表=空心投影)。
RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'projection_rules.json')


class ProjectionRulesError(RuntimeError):
    """规则表不可用 (缺失/非法) —— 投影判据 fail-closed, 绝不退化为空规则表。"""


def _load_projection_rules(path=RULES_PATH):
    try:
        with open(path, encoding='utf-8') as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ProjectionRulesError('RULES_UNREADABLE: %s (%s)' % (path, exc))
    rules = doc.get('rules')
    if not isinstance(rules, list) or not rules:
        raise ProjectionRulesError('RULES_EMPTY: %s' % path)
    out = []
    for r in rules:
        if not isinstance(r, dict) or not r.get('path') or r.get('mode') not in MODES:
            raise ProjectionRulesError('RULE_MALFORMED: %r' % (r,))
        item = {'path': r['path'], 'mode': r['mode']}
        if r['mode'] == 'drop_by_id':
            # 成员级选择性遮蔽 (EXP1-Q36): selector 用**同形**的数组路径取成员身份字段。
            sel = r.get('selector')
            if not isinstance(sel, dict) or not isinstance(sel.get('path'), str) \
                    or not isinstance(sel.get('values'), list) or not sel['values'] \
                    or not all(isinstance(v, str) and v for v in sel['values']):
                raise ProjectionRulesError('RULE_SELECTOR_MALFORMED: %r' % (r,))
            rparts, rpos = _rule_shape(item['path'])
            sparts, spos = _rule_shape(sel['path'])
            if (rpos != spos or rparts[:rpos] != sparts[:spos]
                    or rparts[rpos][:-3] != sparts[spos][:-3] or spos == len(sparts) - 1):
                raise ProjectionRulesError('RULE_SELECTOR_SHAPE_MISMATCH: %r' % (r,))
            item['selector'] = {'path': sel['path'], 'values': list(sel['values'])}
            item['selector_tail'] = sparts[spos + 1:]
        out.append(item)
    return tuple(out)


MODES = ('scalar', 'array_count', 'drop', 'drop_by_id')


def _rule_shape(rule_path):
    """`<前缀>/<名>[*]` 单通配形态 ⇒ (段表, 通配段下标); 其它形态抛错 (fail-closed)。

    为什么限制到这一形态: 成员级选择器必须能把「通配处命中的数组序号」映射到**同一个成员**的
    身份字段上 —— 多通配/独立段形态下该映射不唯一, 猜一个就是静默错锚。形态不符即拒载规则表。
    """
    parts = rule_path.split('/')
    pos = [i for i, s in enumerate(parts) if s == '[*]' or s.endswith('[*]')]
    if len(pos) != 1 or parts[pos[0]] == '[*]' or not parts[pos[0]].endswith('[*]'):
        raise ProjectionRulesError('RULE_SHAPE: %s (仅支持 <前缀>/<名>[*] 单通配形态)' % rule_path)
    return parts, pos[0]


PROJECTION_RULES = _load_projection_rules()
# 锚规则 (整组 fail-closed 的判据): 记录必须含**运行期窗口族**, 否则它不是「这一类面记录」⇒ 弃权。
WINDOW_RULES = ('side_effect_attribution/window/t0', 'side_effect_attribution/window/t1',
                'side_effect_attribution/window/trace_dir')
NONSEMANTIC_SENTINEL = '<nonsemantic>'


def _walk_paths(doc, spec):
    """按 'a/b[*]/c' 形态返回 [(container, key)] 命中点。"""
    parts = spec.split('/')
    out = []

    def rec(cur, i):
        if i == len(parts):
            return
        key = parts[i]
        if key.endswith('[*]'):
            key = key[:-3]
            if isinstance(cur, dict) and key in cur and isinstance(cur[key], list):
                if i == len(parts) - 1:
                    out.append(cur)
                    return
                for item in cur[key]:
                    rec(item, i + 1)
            return
        if isinstance(cur, dict) and key in cur:
            if i == len(parts) - 1:
                out.append((cur, key))
            else:
                rec(cur[key], i + 1)

    rec(doc, 0)
    return out


def _drop_by_id_in_doc(doc, rule):
    """在**可变副本**里做成员级选择性剔除 (与叶流实现同口径); 返回被剔除成员数。"""
    parts, pos = _rule_shape(rule['path'])
    key = parts[pos][:-3]
    parent = doc
    if pos:
        ok, parent = _path_value(doc, '/'.join(parts[:pos]))
        if not ok:
            return 0
    if not isinstance(parent, dict) or not isinstance(parent.get(key), list):
        return 0
    tail = rule.get('selector_tail') or []
    vals = set(rule['selector']['values'])
    base = '/'.join(parts[:pos] + [key])
    keep, n = [], 0
    for i, item in enumerate(parent[key]):
        ok, v = _path_value(doc, '%s/%d' % (base, i) + ('/' + '/'.join(tail) if tail else ''))
        if ok and isinstance(v, str) and v in vals:
            n += 1
            continue
        keep.append(item)
    parent[key] = keep
    return n


def project(doc, strict=True):
    """返回 (proj_doc, report)。strict: 每条规则都必须命中至少一处, 否则抛 KeyError
    (防「声明了不存在的字段」的空心投影 —— 同 RUNTIME_FIELDS 纪律)。"""
    proj = json.loads(json.dumps(doc, ensure_ascii=False))
    report = {'rules': [], 'n_applied': 0}
    for rule in PROJECTION_RULES:
        if rule['mode'] == 'drop_by_id':
            n = _drop_by_id_in_doc(proj, rule)
            if not n and strict:
                raise KeyError('PROJECTION_RULE_UNMATCHED: %s (规则空心 ⇒ 判弃权)' % rule['path'])
            report['rules'].append({'path': rule['path'], 'mode': rule['mode'], 'hits': n})
            report['n_applied'] += n
            continue
        hits = _walk_paths(proj, rule['path'])
        if not hits:
            if strict:
                raise KeyError('PROJECTION_RULE_UNMATCHED: %s (规则空心 ⇒ 判弃权)' % rule['path'])
            report['rules'].append({'path': rule['path'], 'mode': rule['mode'], 'hits': 0})
            continue
        for h in hits:
            if rule['mode'] == 'scalar':
                container, key = h
                container[key] = NONSEMANTIC_SENTINEL
            elif rule['mode'] == 'drop':
                container, key = h                  # 整子树含基数: 键直接删, 不留占位
                del container[key]
            else:                                    # array_count
                container, key = h
                val = container[key]
                container[key] = {'_nonsemantic': True,
                                  'n': len(val) if isinstance(val, (list, dict)) else 1}
        report['rules'].append({'path': rule['path'], 'mode': rule['mode'], 'hits': len(hits)})
        report['n_applied'] += len(hits)
    return proj, report


def project_sha12(doc, strict=True):
    proj, report = project(doc, strict=strict)
    return sha12(canonical_bytes(proj)), report


def canonical_bytes(doc):
    return (json.dumps(doc, ensure_ascii=False, indent=1) + '\n').encode('utf-8')


# ── 跨语言语义投影摘要 (EXP1-Q34): `pin_kind=semantic-projection` 的判据本体 ──────────
# 为什么不复用 project_sha12: 后者依赖 Python 的 json 序列化字节 (indent=1 / 键序 / 转义 / 数字形态),
# 要求另一语言逐位复现是**脆弱**的 —— 浮点、转义、代理对任一环节分叉都是**静默**的。
# 本摘要改为**长度前缀叶流**: 每叶 emit "<len(path)>:<path><len(val)>:<val>" (UTF-8 字节),
# 只依赖 (a) 叶路径按**字节序**排序 (b) 值渲染规则; 两处都可被另一语言逐条实现并交叉复算。
# fail-closed 面 (未定义即拒算, 绝不猜): 浮点/其它非标量值 (渲染规则未定义)。
# 排序序: 按**路径的 UTF-8 字节序** (等价于码点序; 两端都按此实现 ⇒ 非 ASCII 键亦安全,
# 但**不得**改用另一语言的默认字符串序 —— 旁 culture/编码差异会静默分叉)。
def _leaf_walk(doc, prefix=''):
    """叶集 = [(路径, 值)]; 数组元素路径用序号 (/0 /1 …), 与另一语言实现逐位同形。"""
    out = []
    if isinstance(doc, dict):
        for k, v in doc.items():
            out.extend(_leaf_walk(v, '%s/%s' % (prefix, k)))
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            out.extend(_leaf_walk(v, '%s/%d' % (prefix, i)))
    else:
        out.append((prefix.lstrip('/'), doc))
    return out


def _render_scalar(v, path):
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return v
    if v is None:
        return 'null'
    raise KeyError('UNRENDERABLE_VALUE (float/其它): %s = %r' % (path, v))


def _rule_matches(rule_path, leaf_path):
    """规则路径 vs 叶路径。`[*]` 消费**恰好一个**数组序号段 (纯数字) —— 与另一语言实现逐步骤同形
    (朴素「按 / 切分后逐段比较」会把 [*] 当成字面段 ⇒ 规则永不命中, 实测首跑即被空心规则闸拦下)。"""
    rp, lp = rule_path.split('/'), leaf_path.split('/')
    i = j = 0
    while i < len(rp) and j < len(lp):
        seg = rp[i]
        if seg == '[*]':                        # 独立段形态: 消费任意一段
            i += 1
            j += 1
            continue
        if seg.endswith('[*]'):                 # 附着形态 `名字[*]`: 本段名字 + 紧随的数组序号段
            if seg[:-3] != lp[j]:
                return False
            j += 1
            if j >= len(lp) or not lp[j].isdigit():
                return False
            i += 1
            j += 1
            continue
        if seg != lp[j]:
            return False
        i += 1
        j += 1
    return i == len(rp) and j == len(lp)


def _path_value(doc, path):
    cur = doc
    for seg in path.split('/'):
        if isinstance(cur, dict):
            if seg not in cur:
                return False, None
        elif isinstance(cur, list):
            if not seg.isdigit() or int(seg) >= len(cur):
                return False, None
            cur = cur[int(seg)]
            continue
        else:
            return False, None
        cur = cur[seg] if isinstance(cur, dict) else cur
    return True, cur


def _members_of(doc, rule_path):
    """`<前缀>/<名>[*]` ⇒ (数组基路径, [成员路径…]); 数组缺席 ⇒ 空表 (规则空心可容忍)。"""
    parts, pos = _rule_shape(rule_path)
    base = '/'.join(parts[:pos] + [parts[pos][:-3]])
    found, val = _path_value(doc, base)
    if not found or not isinstance(val, list):
        return base, []
    return base, ['%s/%d' % (base, i) for i in range(len(val))]


def _drop_selected_members(doc, leaves, rule):
    """成员级选择性遮蔽: 身份的取值 ∈ selector.values 的成员 ⇒ 整成员剔除。返回 (叶集, 命中成员数)。

    身份取值由 selector.path 的**同通配位置**解析到该成员自己的身份字段 (不是按位置猜邻居)。
    """
    sel = rule['selector']
    tail = rule.get('selector_tail') or []
    _base, members = _members_of(doc, rule['path'])
    vals = set(sel['values'])
    hit, selected = [], []
    for mp in members:
        sp = mp + ('/' + '/'.join(tail) if tail else '')
        found, v = _path_value(doc, sp)
        if found and isinstance(v, str) and v in vals:
            selected.append(mp)
    if selected:
        hit = [p for p, _v in leaves
               if any(p == m or p.startswith(m + '/') for m in selected)]
    # 未选中的同族成员**保持在场** —— 选择性由调用方按「未选中成员仍在叶流里」反向断言。
    return set(hit), len(selected)


def proj_leaf_stream(doc, rules=None, strict=True, require=None):
    """产语义投影叶流 (bytes) —— 与仓库测试侧同口径。

    `strict=True`  : 每条规则都必须命中 (Q33 差分派生时的**证明**模式; 规则空心即抛错)。
    `strict=False` : 逐规则**容忍空心**, 但整组仍 fail-closed —— `require` 里的**锚规则**
                     (默认 window 三件套) 任一未命中 ⇒ 抛错 (记录不是这一类面 ⇒ 弃权)。
    为什么两态都要: 真面记录里 `foreign_writes` 可以是**空数组**、`canon` 可以是 **null**
    (规则按设计只在有内容时生效), 若按 strict 逐条要求命中, 判据会把正常记录判成弃权 (实测首跑)。
    """
    rules = PROJECTION_RULES if rules is None else rules
    anchor = WINDOW_RULES if require is None else require
    leaves = _leaf_walk(doc)
    extra, applied, hollow = [], {}, []
    for rule in rules:
        rp, mode = rule['path'], rule['mode']
        if mode == 'scalar':
            hit = [p for p, _v in leaves if _rule_matches(rp, p)]
            if not hit and strict:
                raise KeyError('PROJECTION_RULE_UNMATCHED: %s (规则空心 ⇒ 判弃权)' % rp)
            drop = set(hit)
        elif mode == 'drop':
            # 整子树剔除, **含基数** —— 用于基数自身逐跑增长的环境族 (保留计数=恒不稳)。
            base = rp.rstrip('/')
            drop = {p for p, _v in leaves if p == base or p.startswith(base + '/')}
            if not drop and strict:
                raise KeyError('PROJECTION_RULE_UNMATCHED: %s (规则空心 ⇒ 判弃权)' % rp)
        elif mode == 'drop_by_id':
            # 成员级**按身份选择性**遮蔽: 仅当成员的身份字段取声明值时才整成员剔除。
            drop, n_sel = _drop_selected_members(doc, leaves, rule)
            if not n_sel and strict:
                raise KeyError('PROJECTION_RULE_UNMATCHED: %s (规则空心 ⇒ 判弃权)' % rp)
        else:                                   # array_count: 整族剔除 + 基数占位
            found, val = _path_value(doc, rp)
            if not found:
                if strict:
                    raise KeyError('PROJECTION_RULE_UNMATCHED: %s (规则空心 ⇒ 判弃权)' % rp)
                drop = set()
            else:
                n = len(val) if isinstance(val, (list, dict)) else 1
                extra.append((rp, '#n=%d' % n))
                drop = {p for p, _v in leaves if p == rp or p.startswith(rp + '/')}
                if not drop and strict:
                    raise KeyError('PROJECTION_RULE_UNMATCHED: %s (规则空心 ⇒ 判弃权)' % rp)
        applied[rp] = len(drop)
        if not drop:
            hollow.append(rp)
        leaves = [lv for lv in leaves if lv[0] not in drop]
    missing = [r for r in anchor if not applied.get(r)]
    if missing:
        raise KeyError('PROJECTION_ANCHOR_RULES_ABSENT: %s (非该类面记录 ⇒ 弃权, 不当绿)' % missing)
    entries = [(p, _render_scalar(v, p)) for p, v in leaves] + extra
    entries.sort(key=lambda t: t[0].encode('utf-8'))
    parts = []
    for p, v in entries:
        pb, vb = p.encode('utf-8'), v.encode('utf-8')
        parts.append(b'%d:' % len(pb) + pb + b'%d:' % len(vb) + vb)
    return b''.join(parts), {'rules_applied': applied, 'hollow_rules': hollow}


def proj_digest(doc, rules=None, strict=True, require=None):
    """语义投影摘要 = sha256[:12] over 叶流 (跨语言同口径; 另一语言按同一规则文件复算)。"""
    stream, meta = proj_leaf_stream(doc, rules=rules, strict=strict, require=require)
    meta['leaf_stream_bytes'] = len(stream)
    return sha12(stream), meta


def proj_digest_file(path, rules=None, strict=True, require=None):
    """对**记录文件**算投影摘要 (登记表 pin 用); 不可解析 ⇒ 抛 ValueError (调用方判弃权)。"""
    try:
        with open(path, encoding='utf-8-sig') as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ValueError('RECORD_UNREADABLE: %s (%s)' % (path, exc))
    return proj_digest(doc, rules=rules, strict=strict, require=require)


# 跨语言测试向量: 两端**各自独立实现**必须复算出同一 sha12 才算口径一致 (任一侧漂移 ⇒ 该断言红)。
# 形状与真面记录同族 (含被遮蔽的运行期族 + 邻居面族 + 普通语义字段 + 布尔/空值/数组)。
TEST_VECTOR_DOC = {
    'schema': 'semantic-projection-vector/1',
    'out': 'eval/capability/vector.json',
    'canon': {'runtime_sidecar': 'eval/capability/vector.runtime.json'},
    'side_effect_attribution': {
        'window': {'t0': 1789535818.11, 't1': 1789536018.22, 'trace_dir': '/tmp/vector-abcdef'},
        'trace': {'commands': 7, 'events': 3, 'raw_events': 11, 'raw_paths_n': 4, 'log_bytes': 4096,
                  'raw_paths_sample': ['/tmp/a.py', '/tmp/b.py']},
        'census_in_repo_cwd': [{'pid': 11, 'cmd': 'sleep'}, {'pid': 12, 'cmd': 'sleep'}],
        'old_gate_delta': ['docs/x.md'],
        'old_gate_false_reds': ['docs/x.md'],
        'foreign_writes': [{'path': 'docs/x.md', 'sha_before': 'aaaa', 'sha_after': 'bbbb',
                            'note': 'changed-in-window',
                            'live_fd': [{'pid': 13, 'fd': '1', 'accmode': 1, 'path': 'docs/x.md'}]}],
        'pre_existing': ['eval/a.json', 'docs/b.md'],
        'self_writes': [{'path': 'eval/capability/vector.runtime.json',
                         'evidence': {'cmd': 12, 'pid': '999', 'syscall': 'openat'}}],
        'live_fd_scan': {'scanned': 5, 'errors': 0},
        'conservation': {'classified': 9, 'expected': 9, 'in_scope_after': 9, 'ok': True},
        'verdict': 'clean', 'red': False, 'measurement_ok': True, 'reasons': [],
    },
    'results': [{'id': 'i0', 'rc': 0, 'pass': True}, {'id': 'i1', 'rc': 3, 'pass': False},
                {'id': 'bind_evidence.check', 'rc': 0, 'pass': True},
                {'id': 'bind_evidence.committed-state', 'rc': 0, 'pass': True},
                {'id': 'bind_evidence.other', 'rc': 0, 'pass': True}],
    'nested': {'n': None, 'flag': False},
}
TEST_VECTOR_SHA12 = '07ffb38d2500'   # EXP1-Q36: 新增 drop / drop_by_id 两模式 + 向量的自指成员两侧样例
                                     #   (Q35 = b989a219bcf4, Q34 = bbd6b93aa9f0; 口径断点逐轮登记)


def _get(doc, path):
    cur = doc
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return False, None
        cur = cur[k]
    return True, cur


def _set(doc, path, value):
    cur = doc
    for k in path[:-1]:
        cur = cur[k]
    cur[path[-1]] = value


def split_runtime(doc, strict=True):
    """返回 (canon_doc, runtime_block)。strict=True 时, 声明字段必须在场 (空心白名单即抛错)。"""
    canon = json.loads(json.dumps(doc, ensure_ascii=False))
    runtime = {'schema': 'face-record-runtime/1', 'note': RUNTIME_NOTE,
               'fields': ['/'.join(p) for p in RUNTIME_FIELDS], 'values': {}}
    trace_dir_val = None
    for path in RUNTIME_FIELDS:
        present, val = _get(canon, path)
        if not present:
            if strict:
                raise KeyError('RUNTIME_FIELD_MISSING: %s (声明的非语义字段不在记录里 ⇒ 白名单空心)'
                               % '/'.join(path))
            continue
        _set(canon, path, SENTINEL)
        runtime['values']['/'.join(path)] = val
        if path[-1] == 'trace_dir':
            trace_dir_val = val
    if trace_dir_val:
        blob = json.dumps(canon, ensure_ascii=False)
        n = blob.count(trace_dir_val)
        if n:
            canon = json.loads(blob.replace(trace_dir_val, SENTINEL))
            runtime['embedded_replacements'] = n
    runtime['canon_sha12'] = sha12(canonical_bytes(canon))
    return canon, runtime


def write_record(doc, target, runtime_target, strict=True):
    """面写出方入口: 记录落 `target` (确定化字节), 运行期字段落 `runtime_target`。"""
    canon, runtime = split_runtime(doc, strict=strict)
    blob = canonical_bytes(canon)
    with open(target, 'wb') as fh:
        fh.write(blob)
    with open(runtime_target, 'wb') as fh:
        fh.write(canonical_bytes(runtime))
    return {'target': str(target), 'runtime_target': str(runtime_target),
            'canon_sha12': sha12(blob), 'canon_bytes': len(blob),
            'runtime_fields': runtime['fields']}


def main():
    args = sys.argv[1:]
    if '--selftest' in args:
        return selftest()
    if '--digest' in args:
        target = args[args.index('--digest') + 1] if args.index('--digest') + 1 < len(args) else None
        if not target or not os.path.exists(target):
            print('ENV_FAIL: --digest 目标缺失 %r ⇒ 弃权' % target)
            return 3
        try:
            d, meta = proj_digest_file(target)
        except (ValueError, KeyError) as exc:
            print('PROJECTION_ABSTAIN (%s)' % exc)
            return 3
        print('PROJ_DIGEST=%s rules_applied=%d leaf_stream_bytes=%d target=%s'
              % (d, len(meta['rules_applied']), meta['leaf_stream_bytes'], target))
        return 0
    inp = args[args.index('--in') + 1] if '--in' in args else None
    out = args[args.index('--out') + 1] if '--out' in args else None
    rout = args[args.index('--runtime-out') + 1] if '--runtime-out' in args else None
    if not (inp and out and rout):
        print('usage: face_record_canon.py --in <record.json> --out <canon.json> --runtime-out <rt.json>')
        return 3
    if not os.path.exists(inp):
        print('ENV_FAIL: %s 不存在 ⇒ 弃权' % inp)
        return 3
    doc = json.loads(open(inp, encoding='utf-8').read())
    rep = write_record(doc, out, rout)
    print('CANON %s sha12=%s bytes=%d runtime=%s'
          % (out, rep['canon_sha12'], rep['canon_bytes'], rout))
    return 0


def selftest():
    import tempfile
    tmp = tempfile.mkdtemp(prefix='q33-canon-')
    bad = 0
    cases = {}

    def rec(t0, t1, td, rc0=0, neigh='p1'):
        # 夹具形状与真记录同族 (含邻居面/活体面字段, 否则投影规则会被判空心)
        return {'schema': 'instruments-check/5', 'passed': 1, 'total': 1, 'out': 'eval/x.json',
                'side_effect_attribution': {
                    'window': {'t0': t0, 't1': t1, 'trace_dir': td},
                    'trace': {'commands': 59, 'events': 19, 'raw_events': 6158, 'raw_paths_n': 3104,
                              'log_bytes': 591408,
                              'log_path': td + '/cmd000.log',
                              'raw_paths_sample': ['/tmp/probe_%s/sol.py' % neigh]},
                    'census_in_repo_cwd': [{'pid': 1, 'cmd': 'sleep 10', 'cwd': '.'}],
                    'foreign_writes': [{'path': 'a', 'sha_before': 'x', 'sha_after': 'y'}],
                    # EXP1-Q35: 新增遮蔽族 (pre_existing / self_writes / conservation 计数 / errors)
                    'pre_existing': ['eval/a.json'],
                    'self_writes': [{'path': 'eval/x.runtime.json',
                                     'evidence': {'cmd': 3, 'pid': '77', 'syscall': 'openat'}}],
                    'conservation': {'classified': 5, 'expected': 5, 'in_scope_after': 5, 'ok': True},
                    'live_fd_scan': {'scanned': 277, 'errors': 105},
                    # EXP1-Q36: 新增遮蔽族 (old_gate_delta / old_gate_false_reds 计数)
                    'old_gate_delta': ['docs/x.md'],
                    'old_gate_false_reds': ['docs/y.md']},
                'canon': {'runtime_sidecar': 'eval/x.runtime.json'},
                'results': [{'id': 'i0', 'rc': rc0, 'pass': rc0 == 0, 'cmd': 'python3 x.py --selftest'},
                            {'id': 'bind_evidence.check', 'rc': 0, 'pass': True},
                            {'id': 'bind_evidence.committed-state', 'rc': 0, 'pass': True},
                            {'id': 'bind_evidence.other', 'rc': 0, 'pass': True}]}
    try:
        a = rec(1789535818.11, 1789536018.22, '/tmp/q22gate-aaaaaa')
        b = rec(1789539999.99, 1789540000.01, '/tmp/q22gate-bbbbbb', neigh='p2')
        ca, ra = split_runtime(a)
        cb, rb = split_runtime(b)
        cases['window_detached_from_record'] = ('/tmp/q22gate-aaaaaa' not in json.dumps(ca)
                                                and SENTINEL in json.dumps(ca))
        # 实测结论 (照原样入档): 仅摘窗口**不足以**让记录字节跨跑相同 —— 邻居面仍在
        cases['record_bytes_still_differ_without_projection'] = (sha12(canonical_bytes(ca))
                                                                 != sha12(canonical_bytes(cb)))
        cases['runtime_values_captured'] = (ra['values']['side_effect_attribution/window/trace_dir']
                                            == '/tmp/q22gate-aaaaaa')
        cases['embedded_random_string_replaced'] = '/tmp/q22gate-aaaaaa' not in json.dumps(ca)
        c = rec(1789535818.11, 1789536018.22, '/tmp/q22gate-aaaaaa', rc0=1)
        cc, _ = split_runtime(c)
        cases['semantic_perturbation_changes_sha12'] = (sha12(canonical_bytes(ca))
                                                        != sha12(canonical_bytes(cc)))
        bad_doc = rec(1789535818.11, 1789536018.22, '/tmp/q22gate-aaaaaa')
        del bad_doc['side_effect_attribution']['window']['t1']
        try:
            split_runtime(bad_doc)
            cases['declared_field_missing_raises'] = False
        except KeyError:
            cases['declared_field_missing_raises'] = True
        # 投影摘要 (C3-b): 对**写出后的记录** (已摘窗口) 计算 —— 运行期/邻居面置换 ⇒ 摘要相同;
        # 语义扰动 ⇒ 必不同; 规则空心 ⇒ 抛错
        pa, ra = project_sha12(ca)
        pb, rb = project_sha12(cb)
        cases['projection_ignores_runtime_and_neighbourhood'] = (pa == pb)
        pc, _ = project_sha12(cc)
        cases['projection_changes_on_semantic_perturbation'] = (pa != pc)
        cases['projection_rules_all_matched'] = all(r['hits'] > 0 for r in ra['rules'])
        try:
            project_sha12({'results': []})
            cases['hollow_projection_rule_rejected'] = False
        except KeyError:
            cases['hollow_projection_rule_rejected'] = True
        # 跨语言语义投影摘要 (EXP1-Q34): 运行期/邻居面置换 ⇒ 同摘要; 语义扰动 ⇒ 必变;
        # 规则单一事实源来自数据文件; 未定义值形态 (浮点) ⇒ fail-closed 抛错
        da, _ = proj_digest(ca)
        db, _ = proj_digest(cb)
        dc, _ = proj_digest(cc)
        cases['proj_digest_ignores_runtime_and_neighbourhood'] = (da == db)
        cases['proj_digest_changes_on_semantic_perturbation'] = (da != dc)
        cases['proj_rules_loaded_from_data_file'] = (len(PROJECTION_RULES) == 23 and os.path.exists(RULES_PATH))
        cases['proj_digest_cross_language_vector'] = (proj_digest(TEST_VECTOR_DOC)[0] == TEST_VECTOR_SHA12)
        # EXP1-Q36: 两个新模式 (drop 整子树含基数 / drop_by_id 成员级按身份选择性遮蔽) 的**两侧样例**:
        #   ① drop: 被剔除族连基数占位一起消失 (Q35 的 array_count 会留 `#n=` 计数, 而该基数逐跑增长)
        #   ② drop_by_id: 声明身份的两个成员消失, **同族未声明身份**的成员逐叶保留 (防「整数组误伤」)
        st_a, meta_a = proj_leaf_stream(ca)
        txt = st_a.decode('utf-8')
        cases['drop_mode_removes_subtree_and_cardinality'] = ('pre_existing' not in txt)
        cases['drop_by_id_masks_selected_members_only'] = ('results/1/rc' not in txt and 'results/2/rc' not in txt
                                                          and 'results/0/rc' in txt and 'results/3/rc' in txt)
        cases['drop_by_id_keeps_cardinality_signal'] = ('old_gate_delta' in txt and '#n=1' in txt)
        try:
            _rule_shape('a[*]/b[*]')
            cases['rule_shape_multi_wildcard_rejected'] = False
        except ProjectionRulesError:
            cases['rule_shape_multi_wildcard_rejected'] = True
        bad_rules = os.path.join(tmp, 'bad_rules.json')
        with open(bad_rules, 'w', encoding='utf-8') as fh:
            fh.write(json.dumps({'rules': [{'path': 'results[*]', 'mode': 'drop_by_id',
                                            'selector': {'path': 'other[*]/id', 'values': ['x']}}]},
                                ensure_ascii=False))
        try:
            _load_projection_rules(bad_rules)
            cases['drop_by_id_selector_mismatch_rejected'] = False
        except ProjectionRulesError:
            cases['drop_by_id_selector_mismatch_rejected'] = True
        bad_rules2 = os.path.join(tmp, 'bad_rules2.json')
        with open(bad_rules2, 'w', encoding='utf-8') as fh:
            fh.write(json.dumps({'rules': [{'path': 'results[*]', 'mode': 'drop_by_id'}]}, ensure_ascii=False))
        try:
            _load_projection_rules(bad_rules2)
            cases['drop_by_id_missing_selector_rejected'] = False
        except ProjectionRulesError:
            cases['drop_by_id_missing_selector_rejected'] = True
        try:
            proj_leaf_stream(a, rules=({'path': 'results[*]', 'mode': 'drop_by_id', 'selector_tail': ['id'],
                                        'selector': {'path': 'results[*]/id', 'values': ['no.such.id']}},),
                             strict=True, require=WINDOW_RULES)
            cases['drop_by_id_hollow_strict_rejected'] = False
        except KeyError:
            cases['drop_by_id_hollow_strict_rejected'] = True
        # EXP1-Q35: 干净窗口 (foreign_writes/self_writes/pre_existing 皆空) —— 真面在「零他人写入」时
        #   必然出现; strict 模式会因规则空心判弃权 ⇒ 非 strict (锚规则仍 fail-closed) 必须能出摘要。
        clean = json.loads(json.dumps(ca))
        for k in ('foreign_writes', 'self_writes', 'pre_existing', 'census_in_repo_cwd'):
            clean['side_effect_attribution'][k] = []
        dc2, mc2 = proj_digest(clean, strict=False)
        cases['clean_window_projection_computable'] = (dc2 is not None and dc2 != pa)
        cases['clean_window_hollow_rules_listed'] = (set(mc2['hollow_rules']) >= {
            'side_effect_attribution/foreign_writes', 'side_effect_attribution/self_writes',
            'side_effect_attribution/pre_existing'})
        noanchor = json.loads(json.dumps(clean))
        del noanchor['side_effect_attribution']['window']['t0']
        try:
            proj_digest(noanchor, strict=False)
            cases['anchor_rule_missing_rejected'] = False
        except KeyError:
            cases['anchor_rule_missing_rejected'] = True
        try:
            proj_digest({'results': [{'rc': 1.5}]})
            cases['proj_digest_unrenderable_fail_closed'] = False
        except KeyError:
            cases['proj_digest_unrenderable_fail_closed'] = True
        # 锚规则缺席 ⇒ 弃权 (非该类面记录); 非锚规则空心 ⇒ 容忍且可见 (真面记录 foreign_writes 可空)
        try:
            proj_digest({'results': []})
            cases['proj_digest_anchor_rules_absent_rejected'] = False
        except KeyError:
            cases['proj_digest_anchor_rules_absent_rejected'] = True
        try:
            dty, mty = proj_digest(TEST_VECTOR_DOC)
            cases['proj_digest_hollow_non_anchor_tolerated_and_visible'] = (
                len(mty['hollow_rules']) == 0 and len(mty['rules_applied']) == len(PROJECTION_RULES))
        except KeyError:
            cases['proj_digest_hollow_non_anchor_tolerated_and_visible'] = False
        # 回读: 侧车 + 记录都能解析, 且记录里不含墙钟值
        p = os.path.join(tmp, 'rec.json')
        rp = os.path.join(tmp, 'rec.runtime.json')
        rep = write_record(a, p, rp)
        cases['write_readback_ok'] = (json.loads(open(p, encoding='utf-8').read())['passed'] == 1
                                      and json.loads(open(rp, encoding='utf-8').read())['schema']
                                      == 'face-record-runtime/1'
                                      and rep['canon_sha12'] == sha12(open(p, 'rb').read()))
        for k, v in cases.items():
            print('  %-40s %s' % (k, 'OK' if v else 'FAIL'))
            bad += 0 if v else 1
        n = len(cases)
        print('SELFTEST %s (%d/%d)' % ('PASS' if bad == 0 else 'FAIL', n - bad, n))
        return 0 if bad == 0 else 2
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
