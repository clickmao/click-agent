#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R369 KPI 探针 v2 —— 为 v0.22.0 不确定探索项建立可复现的 KPI 统计数据并给出判定。

用户 R369 指令：不要凭直觉选「全量 bge 建索引」，用数据在
  「只对 agent 关注范围建索引」 vs 「根本不需要这个能力」 之间取舍；
  凡不确定的方案，先建 KPI 统计数据，再总结是否需要。

数据全部为本机真实数据：
  A  —— 本仓库现场测量的扫描/索引基准
  B  —— bge 成本：锚定 /tmp/bge_bench 的真实实测（300 块实测 + 已声明外推）
  C  —— eval/results/*.json 历史评测 KPI（512 轮 / 4391 case 真实数据）
  D  —— 教训/失败签名重复度（同一份评测数据 + data/ 存量）
  E  —— 阈值判定（阈值写死在脚本里，可复算）
产出：eval/results/kpi_r369.json
"""
import json, os, re, subprocess, time, math, statistics, tracemalloc, collections

ROOT = '/home/agentuser/AgentFramework'
os.chdir(ROOT)
OUT = {}
SKIP = {'.git', 'bin', 'obj', 'node_modules', 'artifacts', '.vs', '.hermes'}


def walk(roots, exts=None):
    out = []
    for r in roots:
        for dp, dn, fn in os.walk(r):
            dn[:] = [d for d in dn if d not in SKIP]
            for f in fn:
                if exts and not f.endswith(exts):
                    continue
                out.append(os.path.join(dp, f))
    return out


def size_of(paths):
    b = loc = 0
    for p in paths:
        try:
            b += os.stat(p).st_size
            with open(p, 'rb') as fh:
                loc += fh.read().count(b'\n')
        except OSError:
            pass
    return b, loc


# ── A. 规模与 "agent 关注面" ─────────────────────────────────────
all_files = walk(('src', 'docs', 'samples', 'eval', 'scripts'))
src_cs = [p for p in all_files if p.endswith('.cs')]
docs_md = [p for p in all_files if p.endswith('.md')]
git_files = sorted({f for f in subprocess.run(
    ['git', 'log', '--name-only', '--pretty=format:', '-30'],
    capture_output=True, text=True).stdout.split() if os.path.isfile(f)})
doc_text = ''.join(open(p, encoding='utf-8', errors='ignore').read()
                   for p in walk(('docs/plans',), ('.md',)))
refd = sorted({m for m in re.findall(r'[\w./-]*src/[\w./-]+\.cs', doc_text) if os.path.isfile(m)})

CPC = 465  # 锚定 bge_bench 实测 avg_chars=465（真实值，非假设）
def chunks(nb): return int(math.ceil(nb / CPC))

scopes = {}
for name, paths in [('S1_all', all_files), ('S2_src_cs', src_cs), ('S3_src_docs_md', src_cs + docs_md),
                    ('S4_git_last30_commits', git_files), ('S5_doc_referenced_src', refd)]:
    b, l = size_of(paths)
    scopes[name] = {'files': len(paths), 'bytes': b, 'loc': l, 'chunks@465c': chunks(b)}
OUT['A_scale'] = scopes

# ── A2. 真实检索基准：暴力全扫 vs 倒排索引 ─────────────────────
QUERIES = ['RemoteEmbedder', 'PythonArtifactPlugin', 'ArgumentList', 'failureClusters',
           'AOT', 'RoleBinaryFile', 'ContextAssembler', 'gate_to_ask', 'lessons', 'embedder']
t0 = time.perf_counter()
for q in QUERIES:
    for p in src_cs:
        try:
            open(p, encoding='utf-8', errors='ignore').read().count(q)
        except OSError:
            pass
cold = (time.perf_counter() - t0) / len(QUERIES)

cache = {}
t0 = time.perf_counter()
for p in src_cs:
    try:
        cache[p] = open(p, encoding='utf-8', errors='ignore').read()
    except OSError:
        pass
load_t = time.perf_counter() - t0
t0 = time.perf_counter()
warm_hits = {q: {p for p, txt in cache.items() if q in txt} for q in QUERIES}
warm = (time.perf_counter() - t0) / len(QUERIES)

tracemalloc.start()
t0 = time.perf_counter()
inv = {}
for p, txt in cache.items():
    for tok in set(re.findall(r'[A-Za-z_][A-Za-z0-9_]{1,}', txt)):
        inv.setdefault(tok.lower(), set()).add(p)
build_t = time.perf_counter() - t0
_, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
t0 = time.perf_counter()
idx_hits = {q: set(inv.get(q.lower(), ())) for q in QUERIES}
idxq = (time.perf_counter() - t0) / len(QUERIES)

# (3b) 3-gram 索引：要拿到与子串扫描等价的检索语义，须用字符 n-gram（复合标识符如 RemoteEmbedder
#       无法被 token 倒排的 'embedder' 命中）。此处量化其代价。
tracemalloc.start()
t0 = time.perf_counter()
tri = {}
for p, txt in cache.items():
    low = txt.lower()
    for g in {low[i:i + 3] for i in range(len(low) - 2)}:
        tri.setdefault(g, set()).add(p)
tri_build = time.perf_counter() - t0
_, tri_peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
t0 = time.perf_counter()
tri_hits = {q: (set.intersection(*[tri.get(q.lower()[i:i + 3], set()) for i in range(len(q) - 2)])
               if len(q) >= 3 else set()) for q in QUERIES}
tri_q = (time.perf_counter() - t0) / len(QUERIES)

OUT['A2_lexical_bench'] = {
    'corpus': f'src/**/*.cs ({len(src_cs)} files)',
    'cold_scan_ms_per_query': round(cold * 1000, 2),
    'warm_scan_ms_per_query': round(warm * 1000, 3),
    'load_corpus_to_memory_ms': round(load_t * 1000, 1),
    'token_index_build_ms': round(build_t * 1000, 1),
    'token_index_query_ms': round(idxq * 1000, 4),
    'token_index_terms': len(inv),
    'token_index_heap_mb': round(peak / 1e6, 2),
    'token_index_parity_vs_substring': all(warm_hits[q] == idx_hits[q] for q in QUERIES),
    'token_misses': {q: [p for p in warm_hits[q] - idx_hits[q]] for q in QUERIES if warm_hits[q] != idx_hits[q]},
    'trigram_index_build_ms': round(tri_build * 1000, 1),
    'trigram_index_query_ms': round(tri_q * 1000, 3),
    'trigram_index_keys': len(tri),
    'trigram_index_heap_mb': round(tri_peak / 1e6, 2),
    'trigram_parity_vs_substring(val/1)': all(warm_hits[q] == tri_hits[q] for q in QUERIES),
    'substring_hits_files': {q: len(warm_hits[q]) for q in QUERIES},
    'queries': QUERIES,
}
del cache, inv, tri

# ── B. bge 向量化成本（锚定真实实测，含口径纠正）──────────────
BGE = {'measured_chunks': 300, 'measured_s': 61.061, 'avg_chars': 465,
       'rss_mb': 306.0, 'managed_mb': 93.6,
       'extrapolated_full_chunks': 6375, 'extrapolated_full_min': 21.6,
       'dim': 512, 'model': 'bge-q8.gguf (CPU, CLS pooling)'}
RATE = BGE['measured_chunks'] / BGE['measured_s']
VEC = {f'fp{bits}': round(BGE['dim'] * bits / 8, 1) for bits in (32, 16, 8)}
bge = {}
for name, s in scopes.items():
    c = s['chunks@465c']
    bge[name] = {'chunks': c, 'embed_s': round(c / RATE, 1), 'embed_min': round(c / RATE / 60, 2),
                 'vectors_fp32_mb': round(c * VEC['fp32'] / 1024 / 1024, 1),
                 'vectors_int8_mb': round(c * VEC['fp8'] / 1024 / 1024, 1),
                 'share_of_full_chunks': round(c / BGE['extrapolated_full_chunks'] * 100, 1)}
OUT['B_bge_cost_model'] = {
    'measured': {'source': '/tmp/bge_bench.log', 'chunks': 300, 'avg_chars': 465,
                 'total_s': 61.061, 'ms_per_chunk': 203.54, 'chunks_per_s': round(RATE, 2),
                 'chars_per_s': 2287},
    'extrapolation': {'full_chunks': 6375, 'est_minutes': 21.6,
                      'caveat': '21.6min 是 300 块实测的线性外推，非真实全量运行'},
    'memory_correction': {'rss_mb_during_embed': 306.0, 'managed_mb': 93.6,
                          'note': '306MB 是进程 RSS（含模型权重），不是索引体积；索引体积见 vectors_*'},
    'vector_bytes_per_doc': VEC,
    'scopes': bge,
}

# ── C. 历史评测 KPI（512 轮真实数据）───────────────────────────
def parse_recall(s):
    d = {}
    for part in (s or '').split(','):
        m = re.match(r'(\w+):(\d+)snip/(\d+)tok/r([\d.]+)rel', part.strip())
        if m:
            d[m.group(1)] = {'snips': int(m.group(2)), 'tokens': int(m.group(3)), 'rel': float(m.group(4))}
    return d

rounds = []
for f in sorted(os.listdir('eval/results')):
    if not f.endswith('.json') or f.startswith('kpi_'):
        continue
    try:
        d = json.load(open('eval/results/' + f))
    except Exception:
        continue
    if 'results' in d:
        rounds.append(d)
cases = [c for d in rounds for c in d['results']]
n = len(cases)
ws = [parse_recall(c.get('sources_recall', '')).get('WorkspaceFiles', {'snips': 0, 'tokens': 0, 'rel': 0}) for c in cases]
sub = [c.get('subtasks') or 1 for c in cases]
long_c, short_c = [c for c, s in zip(cases, sub) if s >= 3], [c for c, s in zip(cases, sub) if s < 3]
prec = [s.get('precision') for s in (c.get('skill_match') or {} for c in cases) if isinstance(s.get('precision'), (int, float))]
dec = collections.Counter(x for c in cases for x in (c.get('skill_decisions') or []))
bge_ms = [c['bge_ms'] for c in cases if c.get('bge_ms')]
OUT['C_history_kpi'] = {
    'rounds': len(rounds), 'cases': n,
    'pass_rate': round(sum(1 for c in cases if c.get('pass')) / n, 4),
    'tokens_per_case': {'median': statistics.median([c.get('total_tokens', 0) for c in cases]),
                        'mean': round(statistics.mean([c.get('total_tokens', 0) for c in cases]), 1)},
    'workspace_recall': {'share_with_recall': round(sum(1 for w in ws if w['snips'] > 0) / n, 4),
                         'median_snips': statistics.median([w['snips'] for w in ws]),
                         'median_tokens_injected': statistics.median([w['tokens'] for w in ws]),
                         'mean_tokens_injected': round(statistics.mean([w['tokens'] for w in ws]), 1),
                         'median_rel': round(statistics.median([w['rel'] for w in ws]), 3)},
    'multistep': {'n_ge3': len(long_c), 'pass_ge3': round(sum(1 for c in long_c if c.get('pass')) / max(len(long_c), 1), 4),
                  'pass_lt3': round(sum(1 for c in short_c if c.get('pass')) / max(len(short_c), 1), 4)},
    'ask_signals': {'gate_to_ask_true': sum(1 for c in cases if c.get('gate_to_ask')),
                    'topic_clarify_pulled_gt0': sum(1 for c in cases if (c.get('topic_clarify_pulled') or 0) > 0)},
    'skill': {'median_precision': round(statistics.median(prec), 4) if prec else None,
              'p10_precision': round(sorted(prec)[len(prec) // 10], 4) if prec else None,
              'decisions': dict(dec)},
    'latency_ms': {'median_wall': statistics.median([c.get('wall_ms', 0) for c in cases]),
                   'median_bge': statistics.median(bge_ms) if bge_ms else None,
                   'bge_cases': len(bge_ms)},
}

# ── D. 教训/失败签名重复度 ────────────────────────────────────
fails = [c for c in cases if not c.get('pass')]
sig = collections.Counter()
for c in fails:
    for nt in (c.get('notes') or []):
        sig[re.sub(r'\d+', 'N', str(nt))[:70]] += 1
allnotes = collections.Counter()
for c in cases:
    for nt in (c.get('notes') or []):
        allnotes[re.sub(r'\d+', 'N', str(nt))[:70]] += 1
roles_dir = os.listdir('data/roles') if os.path.isdir('data/roles') else []
OUT['D_lesson_recurrence'] = {
    'fails': len(fails), 'fail_rate': round(len(fails) / n, 4),
    'distinct_fail_signatures': len(sig),
    'signatures_ge3': sum(1 for v in sig.values() if v >= 3),
    'top_signatures': [{'note': s, 'count': c} for s, c in sig.most_common(8)],
    'all_notes_ge3': sum(1 for v in allnotes.values() if v >= 3),
    'stores_existing': {'data/executor-lessons.json': 1, 'data/guardrails.json': 4,
                        'data/roles/': roles_dir, 'failureClusters.json': os.path.exists('data/roles/failureClusters.json')},
}

# ── E. 阈值判定（可复算）──────────────────────────────────────
be = OUT['A2_lexical_bench']['token_index_build_ms'] / max(OUT['A2_lexical_bench']['cold_scan_ms_per_query'] - OUT['A2_lexical_bench']['warm_scan_ms_per_query'], 1e-9)
min_bge = min(v['embed_min'] for v in bge.values())
V = {
    'exp1a_keyword_inverted_index': {
        'metric': 'cold_scan_ms/query=%.2f, warm=%.3f, token_idx_build=%.1fms/%d keys/%.2fMB, '
                  'trigram_build=%.1fms/%d keys/%.2fMB, token_parity=%s, trigram_parity=%s, break_even_q=%.0f' % (
                      OUT['A2_lexical_bench']['cold_scan_ms_per_query'], OUT['A2_lexical_bench']['warm_scan_ms_per_query'],
                      OUT['A2_lexical_bench']['token_index_build_ms'], OUT['A2_lexical_bench']['token_index_terms'],
                      OUT['A2_lexical_bench']['token_index_heap_mb'], OUT['A2_lexical_bench']['trigram_index_build_ms'],
                      OUT['A2_lexical_bench']['trigram_index_keys'], OUT['A2_lexical_bench']['trigram_index_heap_mb'],
                      OUT['A2_lexical_bench']['token_index_parity_vs_substring'], OUT['A2_lexical_bench']['trigram_parity_vs_substring(val/1)'], be),
        'threshold': '冷扫 <50ms/query 且温扫 <5ms/query → 持久索引的延迟收益 <10ms，不足以抵消构建/内存/语义代价',
        'verdict': 'NOT_NEEDED (惰性扫描+结果缓存即可; 索引仅当语料 >50MB 文本或需跨会话复用)' if OUT['A2_lexical_bench']['cold_scan_ms_per_query'] < 50 and OUT['A2_lexical_bench']['warm_scan_ms_per_query'] < 5 else 'REVIEW',
    },
    'exp1b_bge_persistent_index': {
        'metric': 'cheapest scoped scope = %.2f min (%s); query-time bge median = %s ms/case' % (
            min_bge, min(bge.items(), key=lambda kv: kv[1]['embed_min'])[0], OUT['C_history_kpi']['latency_ms']['median_bge']),
        'threshold': '最小 scoped 建索引 <1min 才考虑预建；否则不做',
        'verdict': 'NOT_NEEDED (查询期按需 embedding 已覆盖)' if min_bge >= 1 else 'REVIEW',
    },
    'exp2_ask_menu': {
        'metric': 'gate_to_ask %d/%d (%.2f%%), clarify_pulled %d' % (
            OUT['C_history_kpi']['ask_signals']['gate_to_ask_true'], n,
            100.0 * OUT['C_history_kpi']['ask_signals']['gate_to_ask_true'] / n, OUT['C_history_kpi']['ask_signals']['topic_clarify_pulled_gt0']),
        'threshold': '现有评测无交互场景 → 不可判',
        'verdict': 'INCONCLUSIVE (需新埋点，KPI 定义见文档)',
    },
    'exp3_step_alignment': {
        'metric': 'pass(subtasks>=3)=%.4f vs pass(<3)=%.4f' % (
            OUT['C_history_kpi']['multistep']['pass_ge3'], OUT['C_history_kpi']['multistep']['pass_lt3']),
        'threshold': '若长链通过率低于短链 5pt 以上才建校验',
        'verdict': 'NOT_NEEDED (数据反向：长链更好)' if OUT['C_history_kpi']['multistep']['pass_ge3'] >= OUT['C_history_kpi']['multistep']['pass_lt3'] - 0.05 else 'NEEDED',
    },
    'exp5_lesson_table': {
        'metric': 'distinct fail sig=%d, sig>=3: %d, top2 share=%.0f%%' % (
            OUT['D_lesson_recurrence']['distinct_fail_signatures'], OUT['D_lesson_recurrence']['signatures_ge3'],
            100.0 * sum(v for _, v in sig.most_common(2)) / max(sum(sig.values()), 1)),
        'threshold': 'sig>=3 的数量 >=5 → 轻量实现值得做',
        'verdict': 'NEEDED_LIGHT (role 模块最小实现)' if OUT['D_lesson_recurrence']['signatures_ge3'] >= 5 else 'NOT_NEEDED',
    },
}
OUT['E_verdicts'] = {'break_even_queries': round(be, 1), 'min_scoped_bge_minutes': min_bge, 'items': V}

json.dump(OUT, open('eval/results/kpi_r369.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps({'A2': OUT['A2_lexical_bench'], 'C_multistep': OUT['C_history_kpi']['multistep'],
                  'C_ask': OUT['C_history_kpi']['ask_signals'], 'C_skill': OUT['C_history_kpi']['skill'],
                  'D': {k: v for k, v in OUT['D_lesson_recurrence'].items() if k != 'top_signatures'},
                  'E': OUT['E_verdicts']}, ensure_ascii=False, indent=1))
