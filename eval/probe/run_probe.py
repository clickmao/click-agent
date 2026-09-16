#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""随机能力自检编排器 (R398 长期任务)

作用: 题集(tasks.py) → 解法适配器 → 判定(grade.py) → 结构化摘要(JSON) + 归因表。

解法适配器契约 (与语言/实现无关, 只认文本进文本出):
    oracle              参考解: 程序题走内置参考实现, 数学题回填已知答案 ⇒ 必须 100%
                        (用途: 验证流水线本身, **不是**能力读数, 摘要里标 oracle=true)
    mutation:<kind>     缺陷注入: offbyone / loop / syntax / nocode / hardcode
                        (用途: 负控 —— 流水线必须能把它们判红)
    agent               本 agent 真机自检: 调 AOT agenthost -q <prompt> 取回复
                        (环境: AGENTFRAMEWORK_PY_RUN=1 打开 py 插件; .env.local 提供 keys)
    command:<shell>     外部解法: prompt 从 stdin 进, 回复从 stdout 出
    file:<dir>          从目录读 <tid>.txt 作为回复 (用途: 离线/人工收集)

输出: data/probe/probe-<solver>-<seed>.json
      含 per_task 明细 + 按 kind/family 的通过率 + 失败模式分布 taxonomy
      ⇒ 归因面必须能落到"题族 × 失败模式", 否则无法沉淀经验。

用法
----
    python3 eval/probe/run_probe.py --selftest
    python3 eval/probe/run_probe.py --kind program --n 4 --seed 7 --solver oracle|agent|rover|mutation:<kind>|file:<dir>|command:<cmd>
"""

from __future__ import annotations

import argparse
import datetime
import glob
import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import grade  # noqa: E402
import tasks as taskgen  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.dirname(HERE)), "data", "probe")


# ---------------------------------------------------------------- 参考解 (oracle)

_REF_MAXSUB = """
import sys
d=sys.stdin.read().split(); n=int(d[0]); a=[int(x) for x in d[1:1+n]]
best=cur=a[0]
for x in a[1:]: cur=max(x,cur+x); best=max(best,cur)
print(best)"""

_REF_LONGEST = """
import sys
s=sys.stdin.read().strip(); last={}; st=0; best=0
for i,ch in enumerate(s):
    if ch in last and last[ch]>=st: st=last[ch]+1
    last[ch]=i; best=max(best,i-st+1)
print(best)"""

_REF_BRACKET = """
import sys
s=sys.stdin.read().strip(); no=nc=0
for ch in s:
    if ch=='(': no+=1
    elif no: no-=1
    else: nc+=1
print(no+nc)"""

_REF_INTERVAL = """
import sys
d=sys.stdin.read().split(); n=int(d[0]); q=int(d[1]); a=[int(x) for x in d[2:2+n]]
p=[0]
for x in a: p.append(p[-1]+x)
out=[]; idx=2+n
for _ in range(q):
    l=int(d[idx]); r=int(d[idx+1]); idx+=2; out.append(str(p[r+1]-p[l]))
print('\\n'.join(out))"""

_REF_SPIRAL = """
import sys
d=sys.stdin.read().split(); R=int(d[0]); C=int(d[1]); v=[int(x) for x in d[2:]]
m=[v[i*C:(i+1)*C] for i in range(R)]; out=[]
while m:
    out+=m.pop(0)
    if m and m[0]:
        for row in m: out.append(row.pop())
    if m: out+=reversed(m.pop())
    if m and m[0]:
        for row in reversed(m): out.append(row.pop(0))
print(' '.join(map(str,out)))"""

_REF_CSV = """
import sys
from itertools import groupby
pairs=sorted((ln.split(',')[0], int(ln.split(',')[1])) for ln in sys.stdin.read().strip().splitlines())
print(';'.join('%s=%d'%(k,sum(v for _,v in g)) for k,g in groupby(pairs,key=lambda t:t[0])))"""

_REF_PAIRCLOSE = """
import sys
d = sys.stdin.read().split()
n = int(d[0])
a = [int(x) for x in d[1:1 + n]]
best = None
for i in range(n):
    for j in range(i + 1, n):
        s = a[i] + a[j]
        k = (abs(s), s)
        if best is None or k < best[0]:
            best = (k, s)
print(best[1])
"""

_REF_TOPO = """
import sys, heapq
d = sys.stdin.read().split()
n = int(d[0]); m = int(d[1])
adj = [[] for _ in range(n)]; deg = [0] * n
i = 2
for _ in range(m):
    u = int(d[i]); v = int(d[i + 1]); i += 2
    adj[u].append(v); deg[v] += 1
h = [x for x in range(n) if deg[x] == 0]; heapq.heapify(h)
out = []
while h:
    u = heapq.heappop(h); out.append(u)
    for v in adj[u]:
        deg[v] -= 1
        if deg[v] == 0: heapq.heappush(h, v)
print(-1 if len(out) < n else ' '.join(map(str, out)))"""

_REF_VM = """
import sys
L = sys.stdin.read().splitlines()
k = int(L[0].split()[0])
P = [ln.split() for ln in L[1:1 + k]]
st = []; pc = 0; out = []; steps = 0
while True:
    if pc < 0 or pc >= k:
        print('ERR'); break
    steps += 1
    if steps > 10000:
        print('ERR'); break
    op = P[pc][0]; arg = P[pc][1:]; pc += 1
    if op == 'PUSH':
        st.append(int(arg[0]))
    elif op == 'POP':
        if not st: print('ERR'); break
        st.pop()
    elif op in ('ADD', 'SUB', 'MUL'):
        if len(st) < 2: print('ERR'); break
        a = st.pop(); b = st.pop()
        st.append(b + a if op == 'ADD' else (b - a if op == 'SUB' else b * a))
    elif op == 'DUP':
        if not st: print('ERR'); break
        st.append(st[-1])
    elif op == 'SWAP':
        if len(st) < 2: print('ERR'); break
        st[-1], st[-2] = st[-2], st[-1]
    elif op == 'PRINT':
        if not st: print('ERR'); break
        out.append(st.pop())
    elif op == 'JNZ':
        if not st: print('ERR'); break
        v = st.pop(); t = int(arg[0])
        if t < 0 or t >= k: print('ERR'); break
        if v != 0: pc = t
    elif op == 'HALT':
        print(chr(10).join(map(str, out))); break
    else:
        print('ERR'); break"""

REF_SRC = {
    "pair_closest_abs_sum": _REF_PAIRCLOSE.strip(),
    "max_subarray": _REF_MAXSUB.strip(),
    "longest_unique": _REF_LONGEST.strip(),
    "bracket_fix": _REF_BRACKET.strip(),
    "interval_sum": _REF_INTERVAL.strip(),
    "matrix_spiral": _REF_SPIRAL.strip(),
    "csv_agg": _REF_CSV.strip(),
    "topo_min": _REF_TOPO.strip(),
    "vm_run": _REF_VM.strip(),
    "json_mini": None,      # 由下方 (定义顺序: _REF_JSON 晚于本字面量) 注入
}

PROG_MUTATIONS = ("extra", "loop", "syntax", "nocode", "hardcode")   # 程序题缺陷注入族

# ---------------------------------------------------------------- 族专属缺陷注入 (R417 判别力自证)
# 用途: 证明新族的隐藏判据**真的能**把"看似实现、实则不合规"的解判红 (整题全对=0)。
# 与通用 mutation 分开, 因为只对特定族有意义 ⇒ 只允许 --families 定向跑。

_MUT_TOPO_DFS = """
import sys
d = sys.stdin.read().split()
n = int(d[0]); m = int(d[1])
adj = [[] for _ in range(n)]; i = 2
for _ in range(m):
    u = int(d[i]); v = int(d[i + 1]); i += 2
    adj[u].append(v)
seen = [0] * n; out = []; cyc = [False]
def dfs(u):
    seen[u] = 1
    for v in adj[u]:
        if seen[v] == 1: cyc[0] = True
        elif seen[v] == 0: dfs(v)
    seen[u] = 2; out.append(u)
for x in range(n):
    if seen[x] == 0: dfs(x)
out.reverse()
print(-1 if cyc[0] else ' '.join(map(str, out)))"""

_MUT_VM_NOERR = """
import sys
L = sys.stdin.read().splitlines()
k = int(L[0].split()[0])
P = [ln.split() for ln in L[1:1 + k]]
st = []; pc = 0; out = []
while True:
    op = P[pc][0]; arg = P[pc][1:]; pc += 1
    if op == 'PUSH':
        st.append(int(arg[0]))
    elif op == 'POP':
        st.pop()
    elif op in ('ADD', 'SUB', 'MUL'):
        a = st.pop(); b = st.pop()
        st.append(b + a if op == 'ADD' else (b - a if op == 'SUB' else b * a))
    elif op == 'DUP':
        st.append(st[-1])
    elif op == 'SWAP':
        st[-1], st[-2] = st[-2], st[-1]
    elif op == 'PRINT':
        out.append(st.pop())
    elif op == 'JNZ':
        v = st.pop()
        if v != 0: pc = int(arg[0])
    elif op == 'HALT':
        print(chr(10).join(map(str, out))); break"""

_REF_JSON = """
import sys
BS = chr(92); NL = chr(10); TAB = chr(9)
s = sys.stdin.read()

def norm(v):
    if v is None: return "null"
    if v is True: return "true"
    if v is False: return "false"
    if isinstance(v, int): return "%d" % v
    if isinstance(v, str):
        out = ['"']
        for ch in v:
            if ch == '"': out.append(BS + '"')
            elif ch == BS: out.append(BS + BS)
            elif ch == NL: out.append(BS + "n")
            elif ch == TAB: out.append(BS + "t")
            else: out.append(ch)
        out.append('"')
        return "".join(out)
    if isinstance(v, list): return "[" + ",".join(norm(x) for x in v) + "]"
    return "{" + ",".join(norm(k) + ":" + norm(v[k]) for k in sorted(v)) + "}"

def parse(t):
    i = [0]; n = len(t)
    def ws():
        while i[0] < n and t[i[0]] in " " + chr(9) + chr(13) + chr(10): i[0] += 1
    def bad(): raise ValueError()
    def st():
        i[0] += 1; buf = []
        while True:
            if i[0] >= n: bad()
            c = t[i[0]]
            if c == '"':
                i[0] += 1; return "".join(buf)
            if c == BS:
                i[0] += 1
                if i[0] >= n: bad()
                e = t[i[0]]
                if e == '"': buf.append('"')
                elif e == BS: buf.append(BS)
                elif e == "/": buf.append("/")
                elif e == "n": buf.append(NL)
                elif e == "t": buf.append(TAB)
                elif e == "u":
                    h = t[i[0] + 1:i[0] + 5]
                    if len(h) != 4: bad()
                    cp = int(h, 16)
                    if cp < 0x20: bad()
                    buf.append(chr(cp)); i[0] += 4
                else: bad()
                i[0] += 1
            else:
                if ord(c) < 0x20: bad()
                buf.append(c); i[0] += 1
    def num():
        a = i[0]; j = a
        if j < n and t[j] == "-": j += 1
        if j >= n or t[j] not in "0123456789": bad()
        if t[j] == "0": j += 1
        else:
            while j < n and t[j] in "0123456789": j += 1
        i[0] = j
        return int(t[a:j])
    def arr():
        i[0] += 1; out = []
        ws()
        if i[0] < n and t[i[0]] == "]":
            i[0] += 1; return out
        while True:
            out.append(val()); ws()
            if i[0] >= n: bad()
            c = t[i[0]]; i[0] += 1
            if c == "]": return out
            if c != ",": bad()
    def obj():
        i[0] += 1; d = {}
        ws()
        if i[0] < n and t[i[0]] == "}":
            i[0] += 1; return d
        while True:
            ws()
            if i[0] >= n or t[i[0]] != '"': bad()
            k = st(); ws()
            if i[0] >= n or t[i[0]] != ":": bad()
            i[0] += 1
            d[k] = val(); ws()
            if i[0] >= n: bad()
            c = t[i[0]]; i[0] += 1
            if c == "}": return d
            if c != ",": bad()
    def val():
        ws()
        if i[0] >= n: bad()
        c = t[i[0]]
        if c == "{": return obj()
        if c == "[": return arr()
        if c == '"': return st()
        for lit, v in (("null", None), ("true", True), ("false", False)):
            if t.startswith(lit, i[0]):
                i[0] += len(lit); return v
        return num()
    v = val(); ws()
    if i[0] != n: bad()
    return v

try:
    print(norm(parse(s)))
except (ValueError, IndexError):
    print("ERR")"""

_MUT_JSON_LOOSE = """
import sys, json
try:
    v = json.loads(sys.stdin.read())
    print(json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
except Exception:
    print("ERR")"""

_REF_LIFE = r"""
import sys
def nbr(g, i, j):
    h, w = len(g), len(g[0])
    n = 0
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == 0 and dj == 0:
                continue
            x, y = i + di, j + dj
            if 0 <= x < h and 0 <= y < w and g[x][y] == "#":
                n += 1
    return n
data = sys.stdin.read().strip().splitlines()
h, w, k = map(int, data[0].split())
g = [list(r) for r in data[1:1 + h]]
for _ in range(k):
    g = [["#" if (nbr(g, i, j) == 3 or (g[i][j] == "#" and nbr(g, i, j) == 2)) else "." for j in range(w)] for i in range(h)]
print(chr(10).join("".join(r) for r in g))
"""

_MUT_LIFE_WRAP = r"""
import sys
def nbr(g, i, j):
    h, w = len(g), len(g[0])
    n = 0
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == 0 and dj == 0:
                continue
            if g[(i + di) % h][(j + dj) % w] == "#":
                n += 1
    return n
data = sys.stdin.read().strip().splitlines()
h, w, k = map(int, data[0].split())
g = [list(r) for r in data[1:1 + h]]
for _ in range(k):
    g = [["#" if (nbr(g, i, j) == 3 or (g[i][j] == "#" and nbr(g, i, j) == 2)) else "." for j in range(w)] for i in range(h)]
print(chr(10).join("".join(r) for r in g))
"""

REF_SRC["json_mini"] = _REF_JSON.strip()
_REF_SUB_GAME = r"""
import sys
d = sys.stdin.read().split()
n, k = int(d[0]), int(d[1])
ss = sorted(int(x) for x in d[2:2 + k])
win = [False] * (n + 1)
for i in range(1, n + 1):
    win[i] = any(not win[i - t] for t in ss if t <= i)
if not win[n]:
    print("LOSE")
else:
    print("WIN %d" % min(t for t in ss if t <= n and not win[n - t]))
"""

_MUT_SUB_GREEDY = r"""
import sys
d = sys.stdin.read().split()
n, k = int(d[0]), int(d[1])
ss = sorted(int(x) for x in d[2:2 + k])
t = max(x for x in ss if x <= n)
print("WIN %d" % t)
"""

REF_SRC["life_k"] = _REF_LIFE.strip()
REF_SRC["sub_game"] = _REF_SUB_GAME.strip()

# ---------------------------------------------------------------- R504 新游戏族 (nim_multi / wythoff) 参考解
_REF_NIM_MULTI = r"""
import sys
d = sys.stdin.read().split()
m = int(d[0])
p = [int(x) for x in d[1:1 + m]]
x = 0
for a in p:
    x ^= a
if x == 0:
    print("LOSE")
else:
    for i in range(m):
        v = p[i] ^ x
        if v < p[i]:
            print("WIN %d %d" % (i + 1, p[i] - v))
            break
"""

_REF_WYTHOFF = r"""
import sys, math
a, b = [int(x) for x in sys.stdin.read().split()[:2]]
lim = max(a, b)
phi = (1 + math.sqrt(5)) / 2
ps = set()
k = 0
while True:
    x, y = int(math.floor(k * phi)), int(math.floor(k * phi * phi))
    if x > lim or y > lim:
        break
    ps.add((x, y))
    ps.add((y, x))
    k += 1
if (a, b) in ps:
    print("LOSE")
else:
    best = None
    for i in range(a + 1):
        for j in range(b + 1):
            if i == 0 and j == 0:
                continue
            if not (i == 0 or j == 0 or i == j):
                continue
            if (a - i, b - j) in ps and (best is None or (i, j) < best):
                best = (i, j)
    print("WIN %d %d" % best)
"""

_MUT_NIM_GREEDY = r"""
import sys
d = sys.stdin.read().split()
m = int(d[0])
p = [int(x) for x in d[1:1 + m]]
i = p.index(max(p))
print("WIN %d %d" % (i + 1, p[i]))
"""

_MUT_WYTH_GREEDY = r"""
import sys
a, b = [int(x) for x in sys.stdin.read().split()[:2]]
if a == b:
    print("WIN %d %d" % (a, a))
elif a > b:
    print("WIN %d 0" % (a - b))
else:
    print("WIN 0 %d" % (b - a))
"""

REF_SRC["nim_multi"] = _REF_NIM_MULTI.strip()
REF_SRC["wythoff"] = _REF_WYTHOFF.strip()

FAMILY_MUTATIONS = {
    ("topo_min", "topo_dfs"): _MUT_TOPO_DFS.strip(),
    ("vm_run", "vm_noerr"): _MUT_VM_NOERR.strip(),
    ("json_mini", "json_loose"): _MUT_JSON_LOOSE.strip(),
    ("life_k", "life_wrap"): _MUT_LIFE_WRAP.strip(),
    ("sub_game", "sub_greedy"): _MUT_SUB_GREEDY.strip(),
    ("nim_multi", "nim_greedy"): _MUT_NIM_GREEDY.strip(),
    ("wythoff", "wyth_greedy"): _MUT_WYTH_GREEDY.strip(),
}


def oracle_reply(task: dict, mutation: str = "", turn: int = 1) -> str:
    """参考解回复; mutation 非空时注入指定缺陷 (负控用)。

    注入的缺陷都必须是**可判定**的: 多余输出 / 不终止 / 语法错 / 无代码 / 硬编码公开样例。

    turn (R419 多轮): 缺陷解的**行为按轮**定义——
      `delayfix` = 第 1 轮浅解 / 第 2 轮真解 ⇒ **正控**: 仪器必须记到「修复成功」;
      `nofix`    = 两轮同浅解       ⇒ **负控**: 修复率必须为 0。
    无此正控时,「修复率 0」分不清是「仪器坏」还是「题太难」(R415 教训)。
    """
    if mutation in ("delayfix", "nofix"):
        if mutation == "delayfix" and turn >= 2:
            return oracle_reply(task, "", turn)
        shallow = "hardcode" if task["kind"] == "program" else "wrongfinal"
        return oracle_reply(task, shallow, turn)

    if task["kind"] == "math":
        if mutation == "wrongfinal":
            num = task["answer"].split("/")[0].lstrip("-")
            rep = "FINAL: %d" % (int(num) + 1)
        elif mutation == "nofinal":
            rep = "答案是 %s" % task["answer"]
        else:
            rep = "推理: 由题设直接计算。\nFINAL: %s" % task["answer"]
        return rep

    if mutation and (task["family"], mutation) in FAMILY_MUTATIONS:
        nl = chr(10)
        return ("思路: 直接实现。" + nl + "```python" + nl
                + FAMILY_MUTATIONS[(task["family"], mutation)] + nl + "```" + nl)

    src = REF_SRC[task["family"]]
    if not mutation:
        return "思路: 直接实现。\n```python\n%s\n```\n" % src
    if mutation == "extra":
        return "```python\n%s\nprint(0)\n```" % src
    if mutation == "loop":
        return "```python\nwhile True:\n    pass\n```"
    if mutation == "syntax":
        return "```python\ndef broken(:\n    pass\n```"
    if mutation == "nocode":
        return "这题我直接口述答案, 不给代码。"
    if mutation == "hardcode":
        pub = task["public"][0]["expected_stdout"] if task["public"] else "0"
        return "```python\nprint(%r)\n```" % pub
    raise SystemExit("未知 mutation: %s" % mutation)


# ---------------------------------------------------------------- 适配器

ROOT = os.path.dirname(os.path.dirname(HERE))
AGENT_BIN = os.environ.get("PROBE_AGENT_BIN",
                           os.path.join(ROOT, "src/agent.host/bin/Release/net10.0/linux-x64/native/agenthost"))
ENV_LOCAL = os.path.join(ROOT, ".env.local")


def load_env_local(path: str = ENV_LOCAL) -> dict:
    """读 .env.local 成 env dict (值不落盘/不打印; 只用于子进程环境)。"""
    env = dict(os.environ)
    if not os.path.exists(path):
        return env
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            k, v = ln.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _telemetry_file(env: dict) -> str:
    """被测进程写入的遥测文件 (env 覆盖优先, 与产品侧 AgentTelemetry 同规则)。"""
    d = env.get("AGENTFRAMEWORK_TELEMETRY") or os.path.join(ROOT, "data", "telemetry")
    return d if str(d).endswith(".jsonl") else os.path.join(d, "host.jsonl")


_TS_RE = __import__("re").compile(
    r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:\.(\d+))?\s*(Z|[+-]\d{2}:?\d{2})?$")


def _iso_epoch(ts: str):
    """ISO8601 → epoch 秒。**必须容错**: .NET 遥测写 7 位小数 (strptime %f 只吃 6 位),
    解析失败返回 None ⇒ 调用方会跳过窗口过滤 ⇒ 可能把**旧产物**当本次结果 (归属铁律)。
    """
    m = _TS_RE.match(str(ts or "").strip())
    if not m:
        return None
    date, tm, frac, off = m.groups()
    frac = (frac or "")[:6].ljust(6, "0")
    off = (off or "Z").replace("Z", "+0000").replace(":", "")
    try:
        return datetime.datetime.strptime("%sT%s.%s%s" % (date, tm, frac, off),
                                          "%Y-%m-%dT%H:%M:%S.%f%z").timestamp()
    except ValueError:
        return None


def harvest_artifacts(t0: float, env: dict, t1: float = None) -> list:
    """R433: 从**遥测外部真值**收割本任务窗口内的 `script_artifact` 落盘产物。

    铁律 (测量外部真值): 取码通道不得依赖被测量代码自报 ⇒ 路径取自遥测 kv;
    归属用**闭区间**时间窗 `[t0-0.25, t1+0.25]` (t1 缺省=当前时刻; 单任务单进程 ⇒ 无歧义,
    见 R418 三级归属)。**缺上界 / 松 slack 会把邻题产物吸进来** ⇒ 可能拿别题的答案判本题
    (R433 实测: slack ±1.5s 时 p002/p003/m001 各多吸 1 条; 收紧到 0.25s ⇒ 恰好 1 题 1 产物)。
    缺失记 `[]` (不记 null 冒充"无产物"); `compile_valid` 由产品侧 py_compile 给出, 只作参考。
    """
    path = _telemetry_file(env)
    hi = (time.time() if t1 is None else t1) + 0.25
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        for line in fh:
            if '"script_artifact"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("point") != "script_artifact":
                continue
            tv = _iso_epoch(rec.get("ts"))
            if tv is None:
                continue                      # 时间戳不可解析 ⇒ **fail-closed** (宁缺勿错)
            if tv < t0 - 0.25 or tv > hi:
                continue
            kv = rec.get("kv") or {}
            p = kv.get("path")
            if not p:
                continue
            full = p if os.path.isabs(str(p)) else os.path.join(ROOT, str(p).lstrip("./"))
            if os.path.exists(full):
                out.append({"path": full, "bytes": kv.get("bytes"),
                            "compile_valid": bool(kv.get("compile_valid")),
                            "origin": kv.get("origin")})
    return out


def _art_paths(meta: dict) -> list:
    """产物记录 → 路径列表 (遥测收割给的是 dict; 判定器只吃路径)。"""
    out = []
    for a in (meta or {}).get("artifacts") or []:
        p = a.get("path") if isinstance(a, dict) else a
        if p:
            out.append(p)
    return out


def solve_agent(task: dict, solve_timeout: float, prompt: str | None = None, sid: str | None = None):
    """真机自检: 用 AOT agenthost 跑一题 (一次性 prompt, 独立会话 Id 便于追溯)。

    prompt/sid (R419 多轮): 修正轮显式传**修正文案** + **复用同一 session id** ⇒
    同一 sid 跨进程续上下文 (§3 微实验 PASS: turn2 在新进程里答出 turn1 记住的数字 4271)。
    sid 由调用方保存复用, 不在此处重算 (重算 = 换会话 = 多轮退化成两个单轮)。
    """
    if not os.path.exists(AGENT_BIN):
        raise SystemExit("agenthost 不存在: %s (先构建/发布或设 PROBE_AGENT_BIN)" % AGENT_BIN)
    env = load_env_local()
    env["AGENTFRAMEWORK_PY_RUN"] = "1"          # 打开 py 插件 (被测能力)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    sid = sid or ("probe-%s-%s" % (time.strftime("%m%d%H%M%S"), task["tid"]))
    ask = task["prompt"] if prompt is None else prompt
    cmd = [AGENT_BIN, "-q", ask, "--output-mode", "text", "--session-id", sid]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=solve_timeout,
                           cwd=ROOT, env=env)
        meta = {"exit": p.returncode, "elapsed_s": round(time.time() - t0, 2),
                "session": sid, "stderr_tail": (p.stderr or "")[-300:]}
        meta["artifacts"] = harvest_artifacts(t0, env)      # R433: 落盘产物 = 取码外部真值
        return p.stdout, meta
    except subprocess.TimeoutExpired:
        meta = {"exit": -9, "elapsed_s": round(time.time() - t0, 2),
                "session": sid, "stderr_tail": "solve timeout"}
        meta["artifacts"] = harvest_artifacts(t0, env)
        return "", meta


def _resolve_rover_model() -> str:
    """前置资产检查 (缺则带候选清单秒退, 不进入重试/等待)。"""
    env = os.environ.get("AGENTFRAMEWORK_ROVER_MODEL")
    if env:
        if not os.path.exists(env):
            raise SystemExit("rover 模型不存在 (AGENTFRAMEWORK_ROVER_MODEL): %s" % env)
        return env
    default = "/tmp/models/prover7b-q4km.gguf"
    if os.path.exists(default):
        return default
    cands = sorted(glob.glob("/tmp/models/*.gguf")) if os.path.isdir("/tmp/models") else []
    raise SystemExit("rover 模型不存在: 默认 %s 已不可用 (清理/删除); 现有候选 %s ⇒ 显式设 "
                     "AGENTFRAMEWORK_ROVER_MODEL (不自动换模型, 换模型会改变被测对象)" % (default, cands or "无"))


def _open_tail(text: str) -> bool:
    """结构性未闭合哨兵: 产物非空但停在半行 (悬空冒号/运算符, 括号引号未闭合)。

    R372 教训: 预算耗尽会让正文停在半行而 success=true, 长度/非空断言全过 ⇒ 需要
    **结构**判据, 不能只看长度。返回 True = 可疑未完成 (只作哨兵, 不替代判定器)。
    """
    t = (text or "").rstrip()
    if not t:
        return False
    if t[-1] in "：:,、+-*/=（([{<" or t.endswith("->"):
        return True
    for op, cl in (("(", ")"), ("[", "]"), ("{", "}"), ("```", "```")):
        if t.count(op) != t.count(cl):
            return True
    return False


def solve_rover(task: dict, solve_timeout: float) -> tuple:
    """真机自检: 用本机 agent.rover 引擎 (GGUF + 字节级 BPE + 采样 + 解码环) 跑一题。

    prompt 对等 (R401): 引擎内建 `--chat` 是硬编码 DeepSeek 版式, 对非 DeepSeek 族模型实测
    4/4 标签不在其词表 (eval/rover/r401/prompt-parity.json) ⇒ 默认走 PROBE_ROVER_PROMPT_MODE=template:
    模板取自目标 GGUF 自身 (jinja2 渲染) 并经 `--prompt` 原样送入, 引擎回报 prompt_sha256 做原样送达对账。
    需要复现旧行为 (引擎自带 chat 渲染) 时显式设 PROBE_ROVER_PROMPT_MODE=engine-chat。

    诚实边界: CPU 上每 token 需流式扫全模型, 实测 2.2 s/token (1.5B) ~ 25 s/token (7B) ⇒ meta 中
    budget_limited/max_tokens 明确标注, 避免把「预算截断」读成「能力为零」。
    """
    cli = os.environ.get("AGENTFRAMEWORK_ROVER_CLI", os.path.join(ROOT, "src/agent.rover/bin/Release/net10.0/agent.rover"))
    model = _resolve_rover_model()
    max_tokens = int(os.environ.get("PROBE_ROVER_MAX_TOKENS", "8"))
    temp = os.environ.get("PROBE_ROVER_TEMPERATURE", "0.7")
    seed = os.environ.get("PROBE_ROVER_SEED", "12345")
    mode = os.environ.get("PROBE_ROVER_PROMPT_MODE", "template")
    system = os.environ.get("PROBE_ROVER_SYSTEM", "你是严谨的编程与数学助手。请直接给出完整可运行的答案。")
    if not os.path.exists(cli):
        raise SystemExit("rover CLI 不存在: %s (先 dotnet build -c Release, 或设 AGENTFRAMEWORK_ROVER_CLI)" % cli)
    jdir = os.environ.get("PROBE_ROVER_JSON_DIR", DATA)
    os.makedirs(jdir, exist_ok=True)
    jf = os.path.join(jdir, "rover-gen-%s.json" % task["tid"])
    # 跑前清残留: 引擎崩溃时会话残留旧 json 会被误读成本轮答案 (实测踩过)
    if os.path.exists(jf):
        os.remove(jf)
    # 前置: 引擎是 apphost, 找不到共享运行时会 exit 131 (app-launch-failed) ——
    # 那是「臂不可用」, 不是「能力为零」。显式给 env, 不依赖调用方 shell 是否 export 过。
    env = dict(os.environ)
    dotnet_root = os.environ.get("DOTNET_ROOT") or os.path.expanduser("~/.dotnet")
    if os.path.isdir(dotnet_root):
        env["DOTNET_ROOT"] = dotnet_root
        env["PATH"] = dotnet_root + os.pathsep + env.get("PATH", "")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from rover_prompt import render_prompt, attest_verbatim

    attest = {}
    if mode == "engine-chat":
        cmd = [cli, "generate", model, "--chat", "--system", system, "--prompt", task["prompt"]]
        attest = {"prompt_source": "engine-chat(硬编码版式)", "parity_risk": "非 DeepSeek 族模型 prompt 不对等"}
    else:
        text_in, attest = render_prompt(model, system, task["prompt"])
        attest["prompt_head"] = text_in[:64]      # 缺陷哨兵证据: 实际送入的首 64 字符
        cmd = [cli, "generate", model, "--prompt", text_in]
    # 墙钟 × token 预算协同 (实测校准 2026-09-14): 本机引擎 ms_per_token=2157 / prefill 132s(78tok)
    # ⇒ 384 token 预算需要 ~960s 生成, 与默认 1000s harness 墙钟几乎相等: 一旦有并发负载,
    # 引擎被 SIGKILL ⇒ 零证据 (reply_chars=0, raw json 根本没落盘)。给引擎一个**小于**
    # solve_timeout 的 --max-seconds, 让它优雅停止 (stop=seconds) 并落盘部分产物 ⇒ 至少留下证据。
    wall = int(float(os.environ.get("PROBE_ROVER_MAX_SECONDS", "0") or 0))
    if wall <= 0:
        wall = max(0, int(solve_timeout) - 60)
    if wall > 0:
        cmd += ["--max-seconds", str(wall)]
    cmd += ["--max-tokens", str(max_tokens), "--temperature", temp, "--seed", seed, "--json", jf]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=solve_timeout, cwd=ROOT, env=env)
    except subprocess.TimeoutExpired:
        return "", False, {"exit": -9, "elapsed_s": round(time.time() - t0, 2), "budget_limited": True,
                           "max_tokens": max_tokens, "prompt_mode": mode, "stderr_tail": "solve timeout", **attest}
    meta = {"exit": p.returncode, "elapsed_s": round(time.time() - t0, 2),
            "budget_limited": None, "max_tokens": max_tokens, "prompt_mode": mode,
            "model": os.path.basename(model), "stderr_tail": (p.stderr or "")[-300:], **attest}
    if p.returncode != 0 and not os.path.exists(jf):
        meta["arm_status"] = "unavailable"
        meta["arm_reason"] = ("app-launch-failed(missing-runtime)" if "app-launch-failed" in (p.stderr or "")
                              else "exit=%d" % p.returncode)
    text = ""
    if os.path.exists(jf):
        try:
            # errors=replace: 引擎日志/文本混入非 UTF-8 字节时不能崩批 (遥测读取铁律)
            with open(jf, encoding="utf-8", errors="replace") as fh:
                j = json.load(fh)
            text = j.get("text", "")
            meta.update({"steps": j.get("steps"), "ms_per_token": j.get("ms_per_token"),
                         "tokens_per_s": j.get("tokens_per_s"), "stop": j.get("stop"),
                         "prompt_tokens": j.get("prompt_tokens"), "ws_delta_bytes": j.get("ws_delta_bytes")})
            # stop=seconds 同样属「预算受限」(墙钟预算): 只看 max_tokens 会把被墙钟截断的
            # 半成品读成「未受限」(实测 290<384 + stop=seconds ⇒ 报 false) = 打点语义错误。
            meta["budget_limited"] = (j.get("stop") in ("max_tokens", "seconds"))
            meta["structural_open_tail"] = _open_tail(text)
            if mode != "engine-chat":
                meta["prompt_attested"] = attest_verbatim(attest, j.get("prompt_sha256"))
        except Exception as e:  # noqa: BLE001
            meta["json_error"] = str(e)
    return text, False, meta


def _tight_case(task: dict):
    """取该题的「规格紧」隐藏用例 (R419 修正轮文案的来源)。

    生成器把 tight_gen 用例放在**生成用例组的末位** (cases 的前 n_public 是公开用例,
    其后 n_hidden 个里最后一个来自 tight_gen), 之后才追加 `hard` 组 ⇒
    索引 = len(hidden) - meta.hard - 1。取不到就退回最后一个隐藏用例 (仍是隐藏信息)。
    """
    hid = task.get("hidden") or []
    if not hid:
        return None
    k = len(hid) - int((task.get("meta") or {}).get("hard", 0) or 0) - 1
    if k < 0 or k >= len(hid):
        k = len(hid) - 1
    return hid[k], k


def correction_prompt(task: dict) -> str:
    """多轮修正文案 (确定性, 与 turn-1 的结论无关)。

    只给**隐藏用例的输入/期望输出**——这是 turn 1 拿不到的信息, 因此「答对」需要真改代码,
    而不是复述风格; 同时不含解题思路 (不泄漏答案)。
    """
    got = _tight_case(task)
    if got is None:
        return "你上一条回复不完整。请重发完整、可直接运行的最终版本。"
    case, k = got
    return ("你上一条回复未通过隐藏用例 #%d (该用例不在题面公开样例中)。\n"
            "输入:\n%s\n你程序的输出与上面的期望不符。期望输出:\n%s\n"
            "请重发**修正后的完整程序**(单个代码块, 不要解释)。" % (k + 1, case["stdin"], case["expected_stdout"]))


def solve(task: dict, solver: str, solve_timeout: float = 300.0,
          prompt: str | None = None, sid: str | None = None, turn: int = 1) -> tuple:
    if solver == "oracle":
        return oracle_reply(task, turn=turn), True, {}
    if solver.startswith("mutation:"):
        return oracle_reply(task, solver.split(":", 1)[1], turn=turn), True, {}
    if solver == "agent":
        rep, meta = solve_agent(task, solve_timeout, prompt=prompt, sid=sid)
        return rep, False, meta
    if solver == "rover":
        return solve_rover(task, solve_timeout)
    if solver.startswith("file:"):
        d = solver.split(":", 1)[1]
        p = os.path.join(d, "%s.txt" % task["tid"])
        return (open(p, encoding="utf-8").read() if os.path.exists(p) else ""), False, {}
    if solver.startswith("command:"):
        cmd = solver.split(":", 1)[1]
        t0 = time.time()
        p = subprocess.run(cmd, shell=True, input=(task["prompt"] if prompt is None else prompt),
                           capture_output=True, text=True, timeout=solve_timeout)
        return p.stdout, False, {"exit": p.returncode, "elapsed_s": round(time.time() - t0, 2)}
    raise SystemExit("未知 solver: %s" % solver)


def run(tasks_list, solver: str, timeout: float, solve_timeout: float = 300.0,
        limit: int = 0, tag: str = "", turns: int = 1, correction: str = "onfail") -> dict:
    """跑一批题并归档回复。

    归属铁律 (R418): 归档回复名必须带**命名空间**(--tag 或默认 s<seed>), 否则多臂/多轮
    同名文件互相覆盖 ⇒ 过程指标 (promptTokens/墙钟/turn) 会静默张冠李戴。

    多轮 (R419, turns>1):
      * 修正轮复用**同一 session id** (续上下文), 文案 = correction_prompt(task) (隐藏用例信息);
      * 归档名加轮次后缀 `-t<N>` ⇒ **轮数取归档文件数** (外部真值), 不读进程内 turn 标记;
      * `mode/passed/total` 记**末轮**(两轮合并终态), `t1`/`t2` 分列首轮与修正轮;
      * 汇总额外给 `first_try_*` (首轮整题全对) 与 `fix_*` (首轮未过 → 修正轮过)。
    """
    per, tax_all, t0 = [], {}, time.time()
    if limit:
        tasks_list = tasks_list[:limit]
    ns = tag or ("s%d" % int(os.environ.get("PROBE_NS_SEED", "0") or 0))
    rep_dir = os.path.join(DATA, "replies")
    os.makedirs(rep_dir, exist_ok=True)
    safe = solver.replace(":", "_").replace("/", "_")

    def _archive(t, reply, turn_idx):
        suf = ("-t%d" % turn_idx) if turns > 1 else ""
        rp = os.path.join(rep_dir, "%s%s-%s%s.txt" % (safe, ns, t["tid"], suf))
        with open(rp, "w", encoding="utf-8") as fh:      # 原始回复留档 (诊断/审计)
            fh.write(reply or "")
        return os.path.relpath(rp, ROOT)

    for t in tasks_list:
        sid = ("probe-%s-%s-%s" % (time.strftime("%m%d%H%M%S"), ns.lstrip("-"), t["tid"]))
        reply, is_oracle, smeta = solve(t, solver, solve_timeout, sid=sid, turn=1)
        smeta["reply_path"] = _archive(t, reply, 1)
        # R419 修正: reply_chars/head 必须**集中**回填 —— 只在某个 solver 分支里设 ⇒
        #   真机臂恒 0 (归档有 11.9 KB 而摘要写 0 = 答案不可见, 比缺字段更坏)。
        smeta["reply_chars"] = len(reply or "")
        smeta["reply_head"] = (reply or "")[:160].replace("\n", " ")
        reply_paths = [smeta["reply_path"]]
        sid = smeta.get("session")
        if not (reply or "").strip():
            smeta["reply_head"] = ""
        if smeta.get("arm_status") == "unavailable":
            tax_all["arm_unavailable"] = tax_all.get("arm_unavailable", 0) + 1
            per.append({"tid": t["tid"], "kind": t["kind"], "family": t["family"],
                        "mode": "arm_unavailable", "passed": 0, "total": 0,
                        "taxonomy": {"arm_unavailable": 1}, "reply_chars": 0, "reply_head": "",
                        "turns": 1, "reply_paths": reply_paths,
                        "t1": {"mode": "arm_unavailable", "passed": 0, "total": 0}, "t2": None,
                        "solve": smeta})
            print("  %-6s %-8s ARM-UNAVAILABLE (%s) — 不计分母, 不判能力" % (t["tid"], t["kind"], smeta.get("arm_reason")),
                  flush=True)
            continue
        r1 = grade.grade(t, reply, timeout, artifacts=(_art_paths(smeta) or None))
        r_final, rounds, smeta_final = r1, 1, smeta
        r2 = None
        if turns > 1 and (correction == "always" or r1["mode"] != "ok"):
            # R419 修正: 默认 onfail —— 只在**首轮未过**时发修正提示。
            #   对已达标题发「隐藏用例没过」= 前提为假 ⇒ 实测把 2/3 已对题改坏成 0/3
            #   (BatchEvidence: r419bagent-b09141437, regressed=2)。
            #   修正的前提必须为真, 否则量到的不是「修复率」而是「抗误导性」。
            rep2, _o2, smeta2 = solve(t, solver, solve_timeout,
                                      prompt=correction_prompt(t), sid=sid, turn=2)
            smeta2["reply_path"] = _archive(t, rep2, 2)
            smeta2["reply_chars"] = len(rep2 or "")
            smeta2["reply_head"] = (rep2 or "")[:160].replace("\n", " ")
            reply_paths.append(smeta2["reply_path"])
            if not (rep2 or "").strip():
                smeta2["reply_head"] = ""
            r2 = grade.grade(t, rep2, timeout, artifacts=(_art_paths(smeta2) or None))
            r_final, rounds, smeta_final = r2, 2, smeta2
            # R419 修正: 首轮行必须**原样打印** (mode/passed) —— 只打最终行 ⇒
            #   「首轮未过、被修正轮修好」在日志里不可见 (可审计性缺口)。
            print("    t1 %-6s %-24s %d/%d (首轮未过 ⇒ 发修正轮)" % (t["tid"], r1["mode"],
                                                              r1["passed"], r1["total"]), flush=True)
            print("    t2 %-6s %-24s fix=%s" % (t["tid"], r2["mode"],
                                                 "YES" if r2["mode"] == "ok" else "no"), flush=True)
        for k, v in r_final["taxonomy"].items():
            tax_all[k] = tax_all.get(k, 0) + v
        per.append({"tid": t["tid"], "kind": t["kind"], "family": t["family"],
                    "mode": r_final["mode"], "passed": r_final["passed"], "total": r_final["total"],
                    "taxonomy": r_final["taxonomy"], "reply_chars": smeta_final.get("reply_chars", 0),
                    "reply_head": (smeta_final.get("reply_head") or ""),
                    "turns": rounds, "reply_paths": reply_paths,
                    "code_source": r_final.get("code_source"),
                    "artifacts": [a.get("path") for a in (smeta_final.get("artifacts") or [])],
                    "t1": {"mode": r1["mode"], "passed": r1["passed"], "total": r1["total"],
                           "reply_chars": smeta.get("reply_chars", 0),
                           "code_source": r1.get("code_source")},
                    "t2": (None if r2 is None else {"mode": r2["mode"], "passed": r2["passed"],
                                                    "total": r2["total"]}),
                    "solve": smeta})
        print("  %-6s %-8s %-24s %-14s %d/%d  (%s)" % (t["tid"], t["kind"], t["family"],
                                                       r_final["mode"], r_final["passed"], r_final["total"],
                                                       "%.0fs" % smeta["elapsed_s"] if smeta.get("elapsed_s") else "instant"),
              flush=True)

    def agg(key):
        buckets = {}
        for p in per:
            b = buckets.setdefault(p[key], {"n": 0, "passed": 0, "total": 0, "modes": {}})
            b["n"] += 1; b["passed"] += p["passed"]; b["total"] += p["total"]
            b["modes"][p["mode"]] = b["modes"].get(p["mode"], 0) + 1
        for b in buckets.values():
            b["rate"] = round(b["passed"] / b["total"], 4) if b["total"] else 0.0
        return buckets

    # --- 多轮三读数 (R419): 轮数为**外部真值** (归档文件数), 不是进程自报
    gradable = [p for p in per if p["mode"] != "arm_unavailable"]
    first_ok = sum(1 for p in gradable if p["t1"]["mode"] == "ok")
    failed_t1 = [p for p in gradable if p["t1"]["mode"] != "ok"]
    fixed = sum(1 for p in failed_t1 if (p["t2"] or {}).get("mode") == "ok")
    final_ok = sum(1 for p in gradable if p["mode"] == "ok")
    regressed = sum(1 for p in gradable if p["t1"]["mode"] == "ok" and p["mode"] != "ok")
    # 轮数 = **归档文件数**, 且逐条回读磁盘确认存在 (不采信内存账本; 缺失可见而非静默)
    archived = [rp for p in per for rp in p["reply_paths"]]
    rounds_observed = sum(1 for rp in archived if os.path.exists(os.path.join(ROOT, rp)))

    return {
        "solver": solver,
        "tag": tag,
        "oracle": solver == "oracle",
        "solver_id": _solver_id(solver),
        "reply_ns": ns,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "elapsed_s": round(time.time() - t0, 2),
        "n_tasks": len(per),
        "passed": sum(p["passed"] for p in per),
        "total": sum(p["total"] for p in per),
        "rate": (None if per and all(p["mode"] == "arm_unavailable" for p in per)
                 else round(sum(p["passed"] for p in per) / max(1, sum(p["total"] for p in per)), 4)),
        "arm_unavailable": sum(1 for p in per if p["mode"] == "arm_unavailable"),
        "validity": ("arm-unavailable" if any(p["mode"] == "arm_unavailable" for p in per) else "ok"),
        "taxonomy": tax_all,
        "by_kind": agg("kind"),
        "by_family": agg("family"),
        "turns_arg": turns,
        "correction_mode": correction,
        "rounds_observed": rounds_observed,
        "rounds_expected": sum(p["turns"] for p in gradable),
        "rounds_missing": len(archived) - rounds_observed,
        "first_try_whole_ok": first_ok,
        "first_try_rate_whole": (round(first_ok / len(gradable), 4) if gradable else None),
        "fix_ok": fixed,
        "fix_rate": (round(fixed / len(failed_t1), 4) if failed_t1 else None),
        "regressed": regressed,
        "final_whole_ok": final_ok,
        "final_rate_whole": (round(final_ok / len(gradable), 4) if gradable else None),
        "saturated": (bool(gradable) and first_ok == len(gradable)),
        "per_task": per,
    }


def _canon_sha(raw):
    """题集规范哈希: 与生成/复用无关, 同一批题必得同一 sha (对比可追溯的前提)。"""
    return hashlib.sha256("\n".join(json.dumps(t, sort_keys=True, ensure_ascii=False) for t in raw)
                          .encode()).hexdigest()[:16]


def _pools(kind, only):
    """族池: 程序族 / (数学族 ∪ 见证型族)。only=逗号白名单(定向覆盖)。

    见证型族若不入池 ⇒ 生成了也永不抽样(死代码), 故此处必须并集。
    """
    want = [x.strip() for x in (only or "").split(",") if x.strip()]
    prog = [f for f in sorted(taskgen.PROGRAM_FAMILIES) if not want or f in want]
    mathl = [f for f in sorted(taskgen.MATH_FAMILIES) + sorted(taskgen.WITNESS_FAMILIES)
             if not want or f in want]
    if want and not prog and not mathl:
        raise SystemExit("--families 无匹配族: %s" % only)
    return (prog if kind in ("program", "both") else []), (mathl if kind in ("math", "both") else [])


def _solver_id(solver: str) -> str:
    if solver.startswith("command:"):
        return "cmd:" + hashlib.sha256(solver.encode()).hexdigest()[:12]
    return solver


def _out_name(solver: str, seed, tag: str = "", turns: int = 1) -> str:
    """摘要文件名 (R419 缺陷修复): 必须带臂 tag。

    旧写法 `probe-<solver>-seed<N>-t<K>.json` 不含 tag ⇒ 同 solver 不同臂
    写同一路径 (后被覆) 且下游按名找臂 ⇒ MISSING_ARMS 假「测量失败」。
    """
    return "probe-%s-seed%s%s%s.json" % (
        _solver_id(solver).replace("/", "_"), seed,
        ("-%s" % tag) if tag else "",
        ("-t%d" % turns) if turns > 1 else "")


# ---------------------------------------------------------------- 自检

def selftest() -> int:
    ok, fails = 0, []

    def chk(name, cond, detail=""):
        nonlocal ok
        if cond:
            ok += 1
            print("  [PASS] %s %s" % (name, detail))
        else:
            fails.append(name)
            print("  [FAIL] %s %s" % (name, detail))

    print("selftest: 流水线正控 + 缺陷注入负控")
    rnd = random.Random(4242)
    prog = [json.loads(taskgen.gen_program_task(i, sorted(taskgen.PROGRAM_FAMILIES), rnd).to_json())
            for i in range(1, 4)]
    math_ = [json.loads(taskgen.gen_math_task(i, sorted(taskgen.MATH_FAMILIES), rnd).to_json())
             for i in range(1, 3)]
    allt = prog + math_

    # 反死代码: 见证型族必须真的可达 (曾因池子只取 MATH_FAMILIES 而永不抽样)
    _prog_pool, _math_pool = _pools("both", "")
    chk("见证型族在数学池内(非死代码)",
        bool(taskgen.WITNESS_FAMILIES) and all(f in _math_pool for f in taskgen.WITNESS_FAMILIES),
        "witness=%s" % sorted(taskgen.WITNESS_FAMILIES))
    _wp = _pools("math", ",".join(sorted(taskgen.WITNESS_FAMILIES)))
    chk("--families 白名单可定向且不混入程序族",
        _wp[0] == [] and sorted(_wp[1]) == sorted(taskgen.WITNESS_FAMILIES))
    wit = [json.loads(taskgen.gen_math_task(i, sorted(taskgen.WITNESS_FAMILIES), rnd).to_json())
           for i in range(1, 3)]
    chk("见证型题 meta.witness 就位且 answer 非空(仅供 oracle 正控)",
        all(w["meta"].get("witness") and (w["answer"] or "").strip() for w in wit))
    rw = run(wit, "oracle", 5.0)
    chk("正控: 见证型题 oracle 满分", rw["rate"] == 1.0, "rate=%.4f tax=%s" % (rw["rate"], rw["taxonomy"]))
    sg = [json.loads(taskgen.gen_program_task(i, ["sub_game"], rnd).to_json()) for i in (1, 2, 3, 4)]
    rsg = run(sg, "oracle", 5.0)
    chk("正控: sub_game(新游戏族) oracle 满分", rsg["rate"] == 1.0,
        "rate=%.4f tax=%s" % (rsg["rate"], rsg["taxonomy"]))
    rmg = run(sg, "mutation:sub_greedy", 5.0)
    # 口径与 R502 NC 一致: 判红看**整题** (final_whole_ok). 用例级 rate 只是参考读数 ——
    # 「恒取最大」在多数局面上与最优手同值, 用例级必然 > 0; 若把它当判据就会误判「判据失效」。
    chk("负控: sub_game 恒取最大(贪心) 整题零通过 (用例级读数仅参考)",
        rmg["final_whole_ok"] == 0 and rmg["rate"] < rsg["rate"] and "wrong_output" in rmg["taxonomy"],
        "whole_ok=%s rate=%.4f/%s tax=%s" % (rmg["final_whole_ok"], rmg["rate"], rsg["rate"], rmg["taxonomy"]))

    rw2 = run(wit, "mutation:wrongfinal", 5.0)
    chk("负控: 见证型题错见证被判红", rw2["rate"] < 1.0 and bool(rw2["taxonomy"].get("wrong_witness")),
        "rate=%.4f tax=%s" % (rw2["rate"], rw2["taxonomy"]))

    # ---- R504 扩面: 新游戏族 (nim_multi / wythoff) + CRT 见证型, 均须「oracle 满分 + 看似实现者整题判红」
    for fam, mut, label in (("nim_multi", "nim_greedy", "恒取最大堆全取"),
                            ("wythoff", "wyth_greedy", "只消堆差(漏双堆同步取)")):
        ttf = [json.loads(taskgen.gen_program_task(i, [fam], rnd).to_json()) for i in (1, 2, 3, 4)]
        rof = run(ttf, "oracle", 5.0)
        chk("正控: %s(新游戏族) oracle 满分" % fam, rof["rate"] == 1.0,
            "rate=%.4f tax=%s" % (rof["rate"], rof["taxonomy"]))
        rmf = run(ttf, "mutation:%s" % mut, 5.0)
        chk("负控: %s %s 整题零通过" % (fam, label),
            rmf["final_whole_ok"] == 0 and rmf["rate"] < rof["rate"]
            and "wrong_output" in rmf["taxonomy"],
            "whole_ok=%s rate=%.4f/%s tax=%s" % (rmf["final_whole_ok"], rmf["rate"],
                                                 rof["rate"], rmf["taxonomy"]))
    crt = [json.loads(taskgen.gen_math_task(i, ["witness_crt"], rnd).to_json()) for i in (1, 2, 3)]
    rco = run(crt, "oracle", 5.0)
    chk("正控: witness_crt oracle 满分(判定=验同余式, 非比对标签)", rco["rate"] == 1.0,
        "rate=%.4f tax=%s" % (rco["rate"], rco["taxonomy"]))
    rcm = run(crt, "mutation:wrongfinal", 5.0)
    chk("负控: witness_crt 错见证(x+1)被判红", rcm["rate"] == 0.0
        and "wrong_witness" in rcm["taxonomy"], "rate=%.4f tax=%s" % (rcm["rate"], rcm["taxonomy"]))

    chk("oracle 参考解覆盖全部程序族(反覆盖缺口)",
        all(f in REF_SRC for f in sorted(taskgen.PROGRAM_FAMILIES)),
        "缺: %s" % [f for f in sorted(taskgen.PROGRAM_FAMILIES) if f not in REF_SRC])
    chk("规范题集哈希与复用路径一致",
        _canon_sha(allt) == _canon_sha(json.loads(json.dumps(allt))))

    r = run(allt, "oracle", 5.0)
    chk("正控: oracle 满分", r["rate"] == 1.0, "rate=%.4f tax=%s" % (r["rate"], r["taxonomy"]))

    for mut, expect_tax in (("extra", "wrong_output"), ("loop", "timeout"), ("syntax", "syntax_error"),
                            ("nocode", "no_code"), ("hardcode", "wrong_output")):
        rm = run(prog, "mutation:%s" % mut, 1.0 if mut == "loop" else 5.0)
        chk("负控: 程序题 %s 被判红" % mut,
            rm["rate"] < 1.0 and expect_tax in rm["taxonomy"],
            "rate=%.4f tax=%s" % (rm["rate"], rm["taxonomy"]))

    rm = run(math_, "mutation:wrongfinal", 5.0)
    chk("负控: 数学错答被判红", rm["rate"] == 0.0 and "wrong_final" in rm["taxonomy"], str(rm["taxonomy"]))
    rm = run(math_, "mutation:nofinal", 5.0)
    chk("负控: 数学无 FINAL 被判红", rm["rate"] == 0.0 and "no_final" in rm["taxonomy"], str(rm["taxonomy"]))

    r = run(prog[:1], "file:/nonexistent-dir-xyz", 5.0)
    chk("负控: 缺失回复判 no_code", r["rate"] == 0.0, str(r["taxonomy"]))

    r = run(prog[:1], "command:cat", 5.0)
    chk("适配器: command 通道可用(prompt 原样回灌 ⇒ 应判红)", r["rate"] == 0.0,
        "rate=%.4f" % r["rate"])

    r = run(allt, "oracle", 5.0)
    chk("可复现: 同输入同结果", r["rate"] == 1.0)

    # --- R419 多轮: 仪器判别力自证 (正控必须记到修复, 负控必须记到未修)
    rp = run(prog, "oracle", 5.0, turns=2)
    chk("多轮正控: oracle 首轮即满分 ⇒ 首次通过率=1.0 且修复率 n/a(无待修题)",
        rp["first_try_rate_whole"] == 1.0 and rp["fix_rate"] is None
        and rp["rounds_observed"] == rp["rounds_expected"] and rp["saturated"] is True,
        "first=%s fix=%s rounds=%s/%s" % (rp["first_try_rate_whole"], rp["fix_rate"],
                                          rp["rounds_observed"], rp["rounds_expected"]))
    chk("多轮 onfail: 已过题**不发**修正轮 ⇒ 归档只有 -t1, 轮数=归档文件数",
        all(p["turns"] == 1 and len(p["reply_paths"]) == 1 and p["reply_paths"][0].endswith("-t1.txt")
            for p in rp["per_task"]),
        str([p["reply_paths"] for p in rp["per_task"]][:2]))
    ra = run(prog, "oracle", 5.0, turns=2, correction="always")
    chk("多轮 always(对照臂): 每题两轮各一份 (-t1/-t2) 且 oracle 无回归",
        ra["correction_mode"] == "always"
        and all(p["turns"] == 2 and len(p["reply_paths"]) == 2 and p["reply_paths"][0].endswith("-t1.txt")
                and p["reply_paths"][1].endswith("-t2.txt") for p in ra["per_task"])
        and ra["rounds_observed"] == ra["rounds_expected"] and ra["regressed"] == 0,
        "mode=%s rounds=%s/%s regressed=%s" % (ra["correction_mode"], ra["rounds_observed"],
                                               ra["rounds_expected"], ra["regressed"]))
    chk("摘要名带臂 tag (R419 缺陷): 同 solver 不同臂不得同名互覆",
        _out_name("agent", 419, "r419a1", 2) == "probe-agent-seed419-r419a1-t2.json"
        and _out_name("agent", 419, "r419a2", 2) != _out_name("agent", 419, "r419a1", 2)
        and _out_name("agent", 419) == "probe-agent-seed419.json",
        "%s | %s | %s" % (_out_name("agent", 419, "r419a1", 2), _out_name("agent", 419, "r419a2", 2),
                         _out_name("agent", 419)))

    rd = run(prog, "mutation:delayfix", 5.0, turns=2)
    chk("多轮正控(仪器判别力): 第1轮浅解失败 + 第2轮真解 ⇒ 修复率=1.0",
        rd["first_try_rate_whole"] == 0.0 and rd["fix_rate"] == 1.0 and rd["final_whole_ok"] == len(prog),
        "first=%s fix=%s final=%d tax=%s" % (rd["first_try_rate_whole"], rd["fix_rate"],
                                             rd["final_whole_ok"], rd["taxonomy"]))
    chk("多轮: 两轮各自回复可见 (reply_chars>0) 且首轮未过原样记录 ⇒ 修复可审计",
        rd["per_task"][0]["t1"]["mode"] != "ok" and (rd["per_task"][0]["t2"] or {}).get("mode") == "ok"
        and rd["per_task"][0]["reply_chars"] > 0 and rd["per_task"][0]["t1"]["reply_chars"] > 0,
        "t1=%s t2=%s chars=%s/%s" % (rd["per_task"][0]["t1"]["mode"],
                                     (rd["per_task"][0]["t2"] or {}).get("mode"),
                                     rd["per_task"][0]["t1"]["reply_chars"],
                                     rd["per_task"][0]["reply_chars"]))

    rn = run(prog, "mutation:nofix", 5.0, turns=2)
    chk("多轮负控: 两轮同浅解 ⇒ 修复率=0.0 (不能把「没修」读成「修了」)",
        rn["first_try_rate_whole"] == 0.0 and rn["fix_rate"] == 0.0 and rn["final_whole_ok"] == 0,
        "first=%s fix=%s final=%d" % (rn["first_try_rate_whole"], rn["fix_rate"], rn["final_whole_ok"]))

    cp = correction_prompt(prog[0])
    tight = (_tight_case(prog[0]) or ({}, -1))[0]
    chk("修正文案: 含隐藏用例输入与期望输出 (turn1 拿不到的信息), 且不含题面之外的解法提示",
        tight["stdin"] in cp and tight["expected_stdout"] in cp and tight["stdin"] not in
        "".join(c["stdin"] for c in prog[0]["public"]), "len=%d" % len(cp))

    # ---- R433: 取码外部真值通道 (产物收割) 的接线与解析必须被自检钉住
    chk("产物记录→路径: 容忍 dict/str 混入且丢空值",
        _art_paths({"artifacts": [{"path": "/a.py"}, {"path": ""}, "/b.py", None]}) == ["/a.py", "/b.py"])
    chk("遥测时间戳: .NET 7 位小数可解析 (旧解析器静默返回 None ⇒ 窗口失效)",
        _iso_epoch("2026-09-14T13:00:05.8805300Z") is not None
        and _iso_epoch("bogus") is None)
    _td = tempfile.mkdtemp(prefix="probe_tel_")
    _a, _b, _c = (os.path.join(_td, n) for n in ("a.py", "b.py", "c.py"))
    for p in (_a, _b, _c):
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("print(1)\n")
    _tel = os.path.join(_td, "host.jsonl")
    with open(_tel, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": "2026-09-14T13:00:05.8805300Z", "point": "script_artifact",
                             "kv": {"path": _a, "compile_valid": True}}) + "\n")
        fh.write(json.dumps({"ts": "2026-09-14T13:00:50.0000000Z", "point": "script_artifact",
                             "kv": {"path": _b, "compile_valid": True}}) + "\n")
        fh.write(json.dumps({"ts": "not-a-ts", "point": "script_artifact",
                             "kv": {"path": _c, "compile_valid": True}}) + "\n")
        fh.write(json.dumps({"ts": "2026-09-14T13:00:07.0000000Z", "point": "script_artifact",
                             "kv": {"path": _b, "compile_valid": True}}) + "\n")
    _got = harvest_artifacts(1789390805.88, {"AGENTFRAMEWORK_TELEMETRY": _tel}, 1789390806.0)
    chk("产物收割: 窗口上界 0.25s 必须生效 (t1+1.0s 的邻题产物不得混入)",
        [os.path.basename(a["path"]) for a in _got] == ["a.py"],
        str([a["path"] for a in _got]))

    print("selftest %d/%d" % (ok, ok + len(fails)))
    return 0 if not fails else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["program", "math", "both"], default="both")
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--solver", default="oracle")
    ap.add_argument("--timeout", type=float, default=5.0)          # 候选程序执行超时
    ap.add_argument("--solve-timeout", type=float, default=300.0)  # 单题解法(LLM)超时
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--tag", default="")            # 回复留档后缀, 便于区分多轮探针
    ap.add_argument("--tasks", default="")     # 复用已生成题集 (保证题集哈希可追溯)
    ap.add_argument("--families", default="")  # 定向覆盖: 逗号分隔族白名单(含见证型族)
    ap.add_argument("--dump-tasks", default="", dest="dump_tasks")  # 落盘题集供多解法同批对比
    ap.add_argument("--turns", type=int, default=1)  # R419: >1 时加修正轮 (同 sid 续上下文)
    ap.add_argument("--correction", choices=["onfail", "always"], default="onfail",
                    help="R419: 修正轮触发条件 (onfail=仅首轮未过, 前提为真; always=对照臂)")
    ap.add_argument("--out", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    if a.tasks:
        raw = json.load(open(a.tasks, encoding="utf-8"))
        sha = _canon_sha(raw)
    else:
        rnd = random.Random(a.seed)
        raw = []
        prog_pool, math_pool = _pools(a.kind, a.families)
        for i in range(1, a.n + 1):
            if prog_pool:
                raw.append(json.loads(taskgen.gen_program_task(i, prog_pool, rnd).to_json()))
        for i in range(1, a.n + 1):
            if math_pool:
                raw.append(json.loads(taskgen.gen_math_task(i, math_pool, rnd).to_json()))
        if a.dump_tasks:
            os.makedirs(os.path.dirname(a.dump_tasks) or ".", exist_ok=True)
            with open(a.dump_tasks, "w", encoding="utf-8") as fh:
                json.dump(raw, fh, ensure_ascii=False, indent=1)
            print("题集已落盘: %s" % a.dump_tasks)
        sha = _canon_sha(raw)

    print("题集: %d 题 (kind=%s seed=%s) sha=%s" % (len(raw), a.kind, a.seed, sha))
    print("解法: %s" % a.solver)
    os.environ["PROBE_NS_SEED"] = str(a.seed or 0)   # 无 --tag 时归档名用 s<seed> 命名空间
    summary = run(raw, a.solver, a.timeout, a.solve_timeout, a.limit, a.tag,
                  turns=a.turns, correction=a.correction)
    summary["taskset_sha"] = sha
    summary["kind_arg"] = a.kind
    summary["seed"] = a.seed

    out = a.out or os.path.join(DATA, _out_name(a.solver, a.seed, a.tag, a.turns))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print("→ %s" % out)
    print("通过率: %d/%d = %.4f  (%.2fs)" % (summary["passed"], summary["total"], summary["rate"], summary["elapsed_s"]))
    if a.turns > 1:
        print("轮数: 实际落盘 %d / 期望 %d (缺 %d)" % (summary["rounds_observed"],
              summary["rounds_expected"], summary["rounds_missing"]))
        print("首次通过率(首轮整题全对): %s  修复率(首轮未过→修正轮过): %s  回归=%d  饱和=%s  修正轮=%s" % (
            summary["first_try_rate_whole"], summary["fix_rate"], summary["regressed"],
            summary["saturated"], summary["correction_mode"]))
    print("失败模式: %s" % json.dumps(summary["taxonomy"], ensure_ascii=False))
    print("按族: %s" % json.dumps({k: v["rate"] for k, v in summary["by_family"].items()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
