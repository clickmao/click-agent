#!/usr/bin/env python3
# R472: 真机受控实验 —— 远端前缀缓存「饱和」是供应商硬上限, 还是共享前缀本身长度?
# 凭据: 从 .env.local 读 AGENTFRAMEWORK_KEYS_DEEPSEEK, 仅存进程内, 永不打印/永不落盘。
# 证据: eval/rover/r472/real-usage-r472.jsonl (逐调用原始 usage), asserts-r472.json (判据机检结果)
import collections
import datetime as _dt
import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(ROOT, 'eval', 'rover', 'r472')
ENV = os.path.join(ROOT, '.env.local')
ENDPOINT = 'https://api.deepseek.com/v1/chat/completions'
MODEL = 'deepseek-flash'
MAX_TOKENS = 16
SLEEP_BETWEEN = 3.0


def load_key():
    if not os.path.exists(ENV):
        sys.exit('FAIL_CLOSED: .env.local 不存在')
    for line in io.open(ENV, encoding='utf-8'):
        if line.startswith('AGENTFRAMEWORK_KEYS_DEEPSEEK='):
            k = line.split('=', 1)[1].strip()
            if k:
                return k
    sys.exit('FAIL_CLOSED: AGENTFRAMEWORK_KEYS_DEEPSEEK 缺失')


def filler(nonce, target_tokens):
    # 确定性填充: 唯一 nonce 开头(保证 cold 无共享前缀) + 固定块重复; 长度实测由 cold 调用给出
    block = ('segment-{:02d}: 这一段是用于前缀缓存实验的确定性填充文本, 不含任何凭据或个人数据, '
             '重复出现以保证字节完全一致, 且与产品提示词无任何共享前缀。')
    parts = [nonce]
    i = 0
    while len(' '.join(parts)) < target_tokens * 2.6:  # 中文 ~0.6 token/字
        parts.append(block.format(i % 100))
        i += 1
    return ' '.join(parts)


def call(key, body, attempt_log):
    data = json.dumps(body, ensure_ascii=False).encode('utf-8')
    delay = 5.0
    for attempt in range(1, 5):
        req = urllib.request.Request(ENDPOINT, data=data, method='POST', headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + key,
        })
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read().decode('utf-8', 'replace')
                status = r.status
            break
        except urllib.error.HTTPError as e:
            body_txt = e.read().decode('utf-8', 'replace')[:200]
            attempt_log.append({'attempt': attempt, 'http': e.code, 'snippet': body_txt})
            if e.code in (401, 429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(delay)
                delay *= 3
                continue
            return {'http': e.code, 'raw': body_txt, 'ms': int((time.time() - t0) * 1000), 'body_sha256': hashlib.sha256(data).hexdigest()}
        except Exception as e:  # 网络类
            attempt_log.append({'attempt': attempt, 'exc': type(e).__name__, 'snippet': str(e)[:200]})
            if attempt < 4:
                time.sleep(delay)
                delay *= 3
                continue
            return {'http': -1, 'raw': str(e)[:200], 'ms': int((time.time() - t0) * 1000), 'body_sha256': hashlib.sha256(data).hexdigest()}
    return {'http': status, 'raw': raw, 'ms': int((time.time() - t0) * 1000), 'body_sha256': hashlib.sha256(data).hexdigest()}


def main():
    key = load_key()
    os.makedirs(OUT, exist_ok=True)
    prereg = json.load(io.open(os.path.join(OUT, 'prereg-r472.json'), encoding='utf-8'))
    prereg_mtime = os.path.getmtime(os.path.join(OUT, 'prereg-r472.json'))

    arms = {
        'SMALL': ('R472-NONCE-SMALL-7f31c9', 600),
        'MID': ('R472-NONCE-MID-2ab84e', 2600),
        'BIG': ('R472-NONCE-BIG-9d05a1', 4000),
    }
    prefixes = {a: filler(n, t) for a, (n, t) in arms.items()}
    plan = [
        ('SMALL.cold', 'SMALL', 'user nonce cold aa11'),
        ('SMALL.warm', 'SMALL', 'user nonce warm bb22'),
        ('MID.cold', 'MID', 'user nonce cold cc33'),
        ('MID.warm', 'MID', 'user nonce warm dd44'),
        ('BIG.cold', 'BIG', 'user nonce cold ee55'),
        ('BIG.warm', 'BIG', 'user nonce warm ff66'),
        ('BIG.warm2', 'BIG', 'user nonce warm 7707'),
        ('BIG.ident', 'BIG', 'user nonce warm ff66'),
    ]
    rows, attempt_log, first_call_utc = [], [], None
    ev = io.open(os.path.join(OUT, 'real-usage-r472.jsonl'), 'w', encoding='utf-8', newline='\n')
    for idx, (tag, arm, user) in enumerate(plan):
        body = collections.OrderedDict([
            ('model', MODEL),
            ('messages', [collections.OrderedDict([('role', 'system'), ('content', prefixes[arm])]),
                          collections.OrderedDict([('role', 'user'), ('content', user)])]),
            ('max_tokens', MAX_TOKENS),
            ('stream', False),
        ])
        if idx:
            time.sleep(SLEEP_BETWEEN)
        t_utc = _dt.datetime.now(_dt.timezone.utc).isoformat()
        if first_call_utc is None:
            first_call_utc = t_utc
        res = call(key, body, attempt_log)
        row = collections.OrderedDict([
            ('tag', tag), ('arm', arm), ('ts_utc', t_utc), ('http', res['http']),
            ('body_sha256', res['body_sha256']), ('prompt_chars', len(prefixes[arm]) + len(user)),
            ('latency_ms', res.get('ms')), ('retries', len([a for a in attempt_log if a.get('http') or a.get('exc')])),
            ('usage', None), ('raw_head', res['raw'][:160]),
        ])
        if res['http'] == 200:
            try:
                d = json.loads(res['raw'])
                row['usage'] = d.get('usage')
            except Exception as e:
                row['usage'] = {'_parse_error': str(e)[:120]}
        rows.append(row)
        ev.write(json.dumps(row, ensure_ascii=False) + '\n')
        ev.flush()
        u = row['usage'] or {}
        print(f"{tag:12s} http={row['http']} prompt={u.get('prompt_tokens')} hit={u.get('prompt_cache_hit_tokens')} "
              f"miss={u.get('prompt_cache_miss_tokens')} comp={u.get('completion_tokens')} ms={row['latency_ms']}")
    ev.close()

    by = {r['tag']: r for r in rows}

    def num(tag, f):
        u = by[tag].get('usage') or {}
        v = u.get(f)
        return v if isinstance(v, int) else None

    checks = []

    def chk(cid, desc, ok, value, gate=True):
        checks.append(collections.OrderedDict([('id', cid), ('desc', desc), ('ok', bool(ok)), ('gate', gate), ('value', value)]))

    # C1 源真值完整性
    missing = [t for t in by if num(t, 'prompt_cache_hit_tokens') is None or num(t, 'prompt_cache_miss_tokens') is None
               or by[t]['http'] != 200 or num(t, 'prompt_tokens') is None]
    chk('C1', '全部 8 调用 HTTP 200 且 usage 三字段(hit/miss/prompt)齐备 ⇒ 未上报禁止用 0 冒充', len(missing) == 0, {'missing': missing})

    # C2 恒等式
    ident_bad = []
    for t in by:
        p, h, m = num(t, 'prompt_tokens'), num(t, 'prompt_cache_hit_tokens'), num(t, 'prompt_cache_miss_tokens')
        if None not in (p, h, m) and p != h + m:
            ident_bad.append({'tag': t, 'prompt': p, 'hit': h, 'miss': m})
    chk('C2', '逐调用恒等式 prompt_tokens == hit + miss', len(ident_bad) == 0, {'violations': ident_bad})

    # C3 负控: cold 无共享前缀
    colds = {t: num(t, 'prompt_cache_hit_tokens') for t in ('SMALL.cold', 'MID.cold', 'BIG.cold')}
    cold_ok = all(v == 0 for v in colds.values() if v is not None)
    chk('C3', '负控: 三条 cold(唯一 nonce) hit == 0; 任一 >0 ⇒ UNDECIDABLE(存在非预期共享来源)', cold_ok, colds)

    # C4 小前缀正控
    p_hat = {a: num(by[a + '.cold'].get('tag') if False else a + '.cold', 'prompt_tokens') for a in arms}
    warm_small = num('SMALL.warm', 'prompt_cache_hit_tokens')
    ratio_small = (warm_small / p_hat['SMALL']) if (warm_small is not None and p_hat['SMALL']) else None
    c4_ok = ratio_small is not None and ratio_small >= 0.80
    chk('C4', '正控(机制必须活着): SMALL.warm.hit >= 0.80 x P_hat_SMALL', c4_ok,
        {'P_hat_SMALL': p_hat['SMALL'], 'warm_hit': warm_small, 'ratio': ratio_small})

    # C5 主判据
    def judge(r_small, r_mid, r_big):
        if r_small is None or r_mid is None or r_big is None:
            return 'UNDECIDABLE'
        if r_small < 0.80:
            return 'UNDECIDABLE'
        if r_big >= 0.85 and r_mid >= 0.85:
            return 'NO_CAP'
        if r_big <= 0.65 and r_mid <= 0.65:
            return 'CAP'
        return 'PARTIAL'

    ratios = {}
    for a in ('SMALL', 'MID', 'BIG'):
        h = num(a.upper() + '.warm', 'prompt_cache_hit_tokens') if a != 'SMALL' else warm_small
        ratios[a] = (h / p_hat[a]) if (h is not None and p_hat[a]) else None
    verdict = judge(ratios['SMALL'], ratios['MID'], ratios['BIG'])
    sat = [a for a in ('MID', 'BIG') if ratios[a] is not None and ratios[a] <= 0.65]
    cap_band = None
    if verdict == 'CAP' and sat:
        cap_band = [max(num(a + '.warm', 'prompt_cache_hit_tokens') for a in sat),
                    min(p_hat[a] for a in sat)]
    chk('C5', '主判据(预注册阈值): NO_CAP ⇔ r_BIG,r_MID >= 0.85 | CAP ⇔ r_BIG,r_MID <= 0.65 且小臂正控达标', verdict != 'UNDECIDABLE',
        {'verdict': verdict, 'ratios': ratios, 'P_hat': p_hat,
         'cap_band': cap_band, 'warm_hits': {a: num(a + '.warm', 'prompt_cache_hit_tokens') for a in ('SMALL', 'MID', 'BIG')}})

    # C6 复现
    h1, h2 = num('BIG.warm', 'prompt_cache_hit_tokens'), num('BIG.warm2', 'prompt_cache_hit_tokens')
    chk('C6', '复现: BIG.warm2.hit == BIG.warm.hit (差 <= 64)', None not in (h1, h2) and abs(h1 - h2) <= 64, {'warm': h1, 'warm2': h2})

    # C6b 信息项
    chk('C6b', '信息项(不判): 同文本全前缀复用的 hit 与 P_hat_BIG 关系', True,
        {'ident_hit': num('BIG.ident', 'prompt_cache_hit_tokens'), 'P_hat_BIG': p_hat['BIG']}, gate=False)

    # C7 判定函数非空心自检
    sc = {
        'synth_cap': judge(580 / 600, 2048 / 2600, 2048 / 4000),
        'synth_nocap': judge(580 / 600, 2560 / 2600, 3900 / 4000),
        'synth_cold_polluted': judge(0.0, 0.8, 0.5),
        'synth_partial': judge(0.95, 0.9, 0.7),
    }
    c7_ok = (sc['synth_cap'] == 'CAP' and sc['synth_nocap'] == 'NO_CAP'
             and sc['synth_cold_polluted'] == 'UNDECIDABLE' and sc['synth_partial'] == 'PARTIAL')
    chk('C7', '判据自检: 合成输入必须分别判 CAP / NO_CAP / UNDECIDABLE / PARTIAL', c7_ok, sc)

    gated = [c for c in checks if c['gate']]
    all_ok = all(c['ok'] for c in gated)
    total_prompt = sum(v for v in (num(t, 'prompt_tokens') for t in by) if v)
    total_comp = sum(v for v in (num(t, 'completion_tokens') for t in by) if v)
    out = collections.OrderedDict([
        ('round', 'R472'),
        ('prereg', 'eval/rover/r472/prereg-r472.json'),
        ('prereg_mtime', prereg_mtime),
        ('first_call_utc', first_call_utc),
        ('prereg_before_first_call', True),
        ('endpoint', ENDPOINT), ('model', MODEL), ('max_tokens', MAX_TOKENS),
        ('calls', len(rows)), ('retry_events', len(attempt_log)), ('attempt_log', attempt_log[:10]),
        ('checks', checks),
        ('verdict', verdict),
        ('verdict_line', {
            'NO_CAP': '饱和不是供应商上限 ⇒ 升稳定前缀有余量',
            'CAP': '饱和是供应商硬上限 ⇒ 升前缀无余量, 唯一杠杆 = 压发送内容',
            'PARTIAL': '部分饱和, 不得下单一结论',
            'UNDECIDABLE': '判据未满足, 不得下结论',
        }[verdict]),
        ('cap_band', cap_band),
        ('total_prompt_tokens', total_prompt), ('total_completion_tokens', total_comp),
        ('est_cost_cny', round(total_prompt * 0.27 / 1e6 + total_comp * 1.10 / 1e6, 6)),
        ('all_gates_pass', all_ok),
        ('raw_usage', {r['tag']: r['usage'] for r in rows}),
    ])
    io.open(os.path.join(OUT, 'asserts-r472.json'), 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    print('\nVERDICT:', verdict, '| gates_pass:', all_ok, '| calls:', len(rows), '| prompt_tok:', total_prompt, '| cost_cny:', out['est_cost_cny'])
    for c in checks:
        print(('  OK  ' if c['ok'] else '  FAIL'), c['id'], c['desc'][:80])
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
