#!/usr/bin/env python3
"""R443 器具 — 从**源码程序化派生**门判 prompt 模板 (禁手打), 并用遥测 prompt_sha 互证重建精确性。

派生源:
  * `src/agent.modelqueue/LocalGenerationPort.cs` → `TurnGateJudge.BuildPrompt` 方法体内的
    `sb.Append("...")` 字面量 (顺序拼接; C# 转义解码)。**模板文字一律从源码抽取**。
  * role 种子 = RoleBinaryFile 的 profile (`skeptic.rbin` 用 master.key 解密; 与遥测
    role_seed_sha=0aa656fa7eafd93a 互证)。
  * 成长块 = `RoleGrowthLedger.RenderForPrompt()` 的格式 (同源抽取), 内容由 rbin 的 `g:` 域播种。

判据 (机检): len(prompt) == 遥测 gate_prompt_len ∧ sha16(prompt) == 遥测 prompt_sha。
命中 ⇒ 该轮 gate prompt **逐位重建**, 可直接送真实 tokenizer 计数 (无估算)。
"""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path('/home/agentuser/AgentFramework')
sys.path.insert(0, str(ROOT / 'eval/rover/r431'))
from precheck_rbin import load as rbin_load  # noqa: E402


def sha16(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:16]


def csharp_unescape(s: str) -> str:
    # R449 器具缺陷修正: 原实现把 `\uXXXX` 里的 'u' 当普通字符 ⇒ '\\u003cthink\\u003e' 变 'u003cthinku003e'
    #   (门判的 ThinkOpen/ThinkClose 就是这么派生的) ⇒ 必须按 C# 规则解 4 位十六进制转义。
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            n = s[i + 1]
            if n == 'u' and i + 5 < len(s) + 1 and len(s) >= i + 6:
                try:
                    out.append(chr(int(s[i + 2:i + 6], 16)))
                    i += 6
                    continue
                except ValueError:
                    pass
            out.append({'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', '"': '"', '0': '\0'}.get(n, n))
            i += 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def derive_template() -> str:
    src = (ROOT / 'src/agent.modelqueue/LocalGenerationPort.cs').read_text(encoding='utf-8')
    i = src.index('public static string BuildPrompt(')
    j = src.index('public static bool MechanicalAck(', i)
    body = src[i:j]
    lits = re.findall(r'sb\.Append\("((?:[^"\\]|\\.)*)"\)', body)
    if len(lits) < 10:
        raise SystemExit(f'模板字面量抽取失败: {len(lits)}')
    return ''.join(csharp_unescape(x) for x in lits)


def derive_growth_format():
    """RenderForPrompt 的格式串从源码抽取 (常量 '观察中'/'⚠先怀疑'/'✓信任'/'—' + 阈值)。"""
    src = (ROOT / 'src/agent.roles/RoleGrowthLedger.cs').read_text(encoding='utf-8')
    th = dict(re.findall(r'private const double (\w+) = ([0-9.]+);', src))
    head = re.search(r'new System\.Text\.StringBuilder\("([^"]*)"\)', src).group(1)
    line = re.search(r'sb\.Append\(\$"(\\n\{d\}[^"]*)"\)', src).group(1)
    # R449 器具缺陷修正: 该正则含 3 个捕获组, 原 `dict(...)` 在三元组上抛 ValueError
    #   (字段 label_triple 在 render_growth 中并未被使用 ⇒ 修正不改渲染结果)
    labels = {a: (b, c) for a, b, c in re.findall(r'\?\s*"([^"]+)"\s*:\s*conf\s*>\s*ConfidenceThreshold\s*\?\s*"([^"]+)"\s*:\s*"([^"]+)"', src)}
    return {'head': head, 'line_tpl': line, 'thresholds': th, 'label_triple': labels}


def render_growth(domains) -> str:
    """domains: dict[name]=(reward,penalty) —— 与 C# RenderForPrompt 同序 (total desc, 稳定)。"""
    fmt = derive_growth_format()
    susp = float(fmt['thresholds']['SuspicionThreshold'])
    conf_th = float(fmt['thresholds']['ConfidenceThreshold'])
    min_s = float(fmt['thresholds']['MinSamplesForTendency'])
    sb = fmt['head']
    for d, (r, p) in sorted(domains.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))[:5]:
        total = r + p
        conf = (r + 1.0) / (total + 2.0)
        tend = '观察中' if total < min_s else ('⚠先怀疑' if conf < susp else ('✓信任' if conf > conf_th else '—'))
        sb += f"\n{d}: 赏{r}/罚{p} → {tend}"
    return sb[:400]


def build_prompt(user_message: str, seed: str, growth: str, tpl: str) -> str:
    s = tpl + '【角色设定】' + seed + '\n'
    if growth.strip():
        s += growth.strip()[:300] + '\n'
    s += '【用户消息】' + (user_message or '').strip() + '\n' + '答案:\n'
    return s


def main() -> int:
    tpl = derive_template()
    seed = 'skeptic|' + rbin_load(str(ROOT / 'skeptic.rbin'), str(ROOT / 'data/master.key'))['profile']
    print(f'[derive] tpl_len={len(tpl)} seed_len={len(seed)} seed_sha16={sha16(seed)} (遥测 role_seed_sha=0aa656fa7eafd93a)')
    doc = rbin_load(str(ROOT / 'eval/rover/r431/fixture/skeptic-growth.rbin'), str(ROOT / 'data/master.key'))
    doms = {}
    for k, v in doc.items():
        if k.startswith('g:'):
            r, p = v.split('|')
            doms[k[2:]] = (int(r), int(p))
    growth = render_growth(doms)
    print(f'[derive] growth_len={len(growth)} domains={doms}')
    print(f'[derive] growth_repr={growth!r}')
    # 互证: 用遥测 (gate_prompt_len, prompt_sha) 逐条核对
    tele = ROOT / 'eval/rover/r441/run-BRJ-M20/data/telemetry/host.jsonl'
    recs = []
    for line in tele.read_text(encoding='utf-8-sig', errors='replace').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get('point') == 'local_turn_gate' and int(r['kv'].get('gate_prompt_len') or 0) > 0:
            recs.append(r['kv'])
    turns = json.load(open(ROOT / 'eval/rover/r441/turns-BRJ-M20.jsonl', encoding='utf-8'))['turns']
    out = []
    for kv in recs:
        hit = None
        for t in turns:
            p = build_prompt(t['text'], seed, growth, tpl)
            if len(p) == int(kv['gate_prompt_len']) and sha16(p) == kv['prompt_sha']:
                hit = {'turn': t['turn'], 'text': t['text'], 'len': len(p), 'sha16': sha16(p)}
                break
        out.append({'tele_pinned': kv.get('pinned'), 'tele_len': int(kv['gate_prompt_len']),
                    'tele_sha': kv['prompt_sha'], 'tele_growth_chars': kv.get('growth_chars'),
                    'growth_len_now': len(growth), 'reconstructed': hit})
    n_ok = sum(1 for o in out if o['reconstructed'])
    print(f'[verify] 逐位重建命中 {n_ok}/{len(out)} (仅用**初始**成长块 {len(growth)} 字符)')
    for o in out:
        print('   ', o['tele_pinned'], o['tele_len'], o['tele_sha'], 'growth', o['tele_growth_chars'], '->',
              (o['reconstructed'] or {}).get('turn'))
    pathlib.Path('/tmp/r443_recon.json').write_text(json.dumps(
        {'tpl_len': len(tpl), 'seed_sha16': sha16(seed), 'growth_initial': growth, 'domains': doms,
         'records': out}, ensure_ascii=False, indent=1), encoding='utf-8')
    return 0 if n_ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
