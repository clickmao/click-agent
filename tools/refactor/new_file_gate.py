#!/usr/bin/env python3
"""R527 候选⑤ — 新增文件前置闸 (机械, fail-closed)。

动机: R526 的结构不变式 (I1 单类型单文件 / I2 文件名=类型名 / I3 命名空间) 只在"全仓机检"里判,
新文件是**先落地后被发现**, 归属错标与 ns 漂移都已进树。前置闸把它们挡在提交之前。

判据 (全部机械, 逐文件):
  G1 单类型单文件      — 顶层类型 >1 ⇒ 红
  G2 文件名=类型名      — 主类型名与文件名不符 (非 "前缀." 形式) ⇒ 红  (Program.cs 豁免)
  G3 命名空间必在      — 无 namespace ⇒ 红
  G4 同目录命名空间唯一 — 新文件 ns ≠ 同目录既有 ns (且未被豁免) ⇒ 红
  G5 region 配平       — #region / #endregion 不配对 ⇒ 红  (R527 实证: 分段工具截断过 region)
  G6 花括号配平        — 朴素计数不等 ⇒ 红  (解析前的粗筛)
  G7 covers 同步       — 无任何登记行 covers 命中该路径 ⇒ **告警**(非红; 目录级 covers 合法)

用法:
  python3 tools/refactor/new_file_gate.py                 # 闸门: 扫 git 未提交的新增 .cs (src/)
  python3 tools/refactor/new_file_gate.py <path> [...]    # 只查给定文件
  python3 tools/refactor/new_file_gate.py --selfcheck     # 正/负控自检 (必须 正控绿 / 负控红)
rc: 0 = 全绿 / 1 = 有红 / 2 = 用法错
"""
import io, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)

RX_TYPE = re.compile(r"^(?:(?:public|internal|private|protected|static|sealed|abstract|partial|readonly|ref|unsafe|file)\s+)*"
                     r"(?:record\s+struct|record\s+class|class|record|struct|interface|enum)\s+(?P<n>\w+)", re.M)
RX_NS = re.compile(r"^[ \t]*namespace\s+([\w.]+)\s*(?:;|\{)?\s*$", re.M)
EXEMPT = set()          # R527 候选①: 命名空间收敛后豁免清单为空 (原两条 agent.core/{userinteraction,subagent})
REGISTRY = "docs/verification-registry.json"


def covers_rows():
    """登记行的 covers 路径集合 (解析失败 ⇒ 空集 = 只告警不判红)。"""
    out = []
    if not os.path.exists(REGISTRY):
        return out
    try:
        import json
        for r in json.load(io.open(REGISTRY, encoding="utf-8")).get("rows", []):
            for c in (r.get("covers") or []):
                if isinstance(c, str) and c.strip():
                    out.append(c.strip().strip("`"))
    except Exception:
        return []
    return out


def code_only(t):
    """去掉字符串字面量/字符字面量/注释后的代码正文 (G6 粗筛必须不看字面量里的花括号;
    局限: 内插串 `$"{...}"` 的洞内花括号一并被去掉 —— 洞内花括号自平衡, 且**编译**才是语法真值)。"""
    out, i, n = [], 0, len(t)
    while i < n:
        c = t[i]
        if c == "/" and i + 1 < n and t[i + 1] == "/":
            j = t.find("\n", i)
            i = n if j < 0 else j
        elif c == "/" and i + 1 < n and t[i + 1] == "*":
            j = t.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif c == "@" and i + 1 < n and t[i + 1] == '"':
            i += 2
            while i < n:
                if t[i] == '"' and i + 1 < n and t[i + 1] == '"':
                    i += 2
                elif t[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
        elif c in '"\'':
            q, i = c, i + 1
            while i < n:
                if t[i] == "\\":
                    i += 2
                elif t[i] == q:
                    i += 1
                    break
                else:
                    i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def covered(rel, covers):
    """covers 命中判定 (partial-aware): 覆盖 `a/B.cs` 的登记行同时覆盖 `a/B.Suffix.cs` 分片。"""
    d = os.path.dirname(rel)
    for x in covers:
        x = x.rstrip("/")
        if rel == x or rel.startswith(x + "/"):
            return True
        if d and (x == d or x.startswith(d + "/")):
            return True
        if x.endswith(".cs"):
            base = x[:-3]
            if rel == base + ".cs" or (rel.startswith(base + ".") and rel.endswith(".cs")):
                return True
    return False


def check(path, covers):
    rel = os.path.relpath(path, "src").replace(os.sep, "/")
    t = io.open(path, encoding="utf-8", errors="replace").read()
    stem = os.path.basename(path)[:-3]
    red, warn = [], []
    ts = [m.group("n") for m in RX_TYPE.finditer(t) if m.start() == 0 or t[m.start() - 1] == "\n"]
    if len(ts) > 1:
        red.append(f"G1 顶层类型 {len(ts)} 个: {ts}")
    elif stem != "Program" and ts and not (stem == ts[0] or stem.startswith(ts[0] + ".")):
        red.append(f"G2 文件名 {stem} ≠ 类型 {ts[0]}")
    m = RX_NS.search(t)
    ns = m.group(1) if m else None
    if not ns and stem != "Program":
        red.append("G3 无命名空间")
    if ns:
        d = os.path.dirname(path)
        rel_dir = os.path.relpath(d, "src").replace(os.sep, "/")
        sib = set()
        for f in os.listdir(d):
            fp = os.path.join(d, f)
            if not f.endswith(".cs") or fp == path:
                continue
            mm = RX_NS.search(io.open(fp, encoding="utf-8", errors="replace").read())
            if mm:
                sib.add(mm.group(1))
        if sib and ns not in sib and (rel_dir, ns) not in EXEMPT and (rel_dir, sorted(sib)[0]) not in EXEMPT:
            red.append(f"G4 同目录命名空间不一致: 本文件 {ns} vs 既有 {sorted(sib)}")
    o = sum(1 for l in t.split("\n") if l.strip().startswith("#region"))
    c = sum(1 for l in t.split("\n") if l.strip().startswith("#endregion"))
    if o != c:
        red.append(f"G5 region 不配对 {o}/{c}")
    if code_only(t).count("{") != code_only(t).count("}"):
        red.append(f"G6 花括号不配对 (去字面量后)")
    if covers and not covered(rel, covers):
        warn.append(f"G7 无 covers 命中 (登记表 {REGISTRY})")
    return rel, red, warn


def new_files():
    p = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    out = []
    for line in p.stdout.split("\n"):
        if len(line) < 4:
            continue
        st, rest = line[:2], line[3:].strip().strip('"')
        if st.strip() in ("A", "??", "AM") and rest.endswith(".cs") and rest.startswith("src/"):
            if os.path.exists(rest):
                out.append(rest)
    return sorted(set(out))


def selfcheck():
    """正控 (干净文件) 必绿; 负控 (逐条注入) 必红。"""
    cases = [("干净", "class Foo {\n    #region A\n    #endregion\n}\n", False),
             ("G5 region", "class Foo {\n    #region A\n}\n", True),
             ("G6 花括号", "class Foo {\n", True),
             ("G2 名不符", "// x\npublic sealed class Bar {\n}\n", True)]
    bad = []
    with tempfile.TemporaryDirectory() as d:
        for name, body, want_red in cases:
            p = os.path.join(d, "Foo.cs")
            io.open(p, "w", encoding="utf-8").write(f"namespace probe;\n\n{body}")
            _, red, _ = check(p, [])
            if bool(red) != want_red:
                bad.append(f"{name}: 期望红={want_red} 实得 {red}")
    for b in bad:
        print("  自检失败", b)
    # G7 (告警级) 机检: covers 判定必须 partial-aware, 且空 covers 不告警
    for rel, cov, want in [("src/agent/Ia.cs", ["src/agent/Ia.cs"], True),
                           ("src/agent/Ia.Pipe.cs", ["src/agent/Ia.cs"], True),
                           ("src/agent/Ia.Pipe.cs", ["src/agent"], True),
                           ("src/agent/Ia.Pipe.cs", ["src/other"], False)]:
        got = covered(rel, cov)
        if got != want:
            bad.append(f"G7 covers 判定 {rel} vs {cov}: 期望 {want} 实得 {got}")
    for b in bad:
        if "G7" in b:
            print("  自检失败", b)
    print("SELFCHECK", "OK" if not bad else "FAIL")
    return 1 if bad else 0


def main(argv):
    if "--selfcheck" in argv:
        return selfcheck()
    paths = [a for a in argv if not a.startswith("-")]
    if not paths:
        paths = new_files()
        if not paths:
            print("闸门: 无新增 .cs ⇒ 放行")
            return 0
        print(f"闸门: 新增 .cs {len(paths)} 个")
    covers = covers_rows()
    red_n = 0
    for p in paths:
        rel, red, warn = check(p, covers)
        if red:
            red_n += 1
            print(f"RED  {rel}")
            for r in red:
                print(f"     {r}")
        else:
            print(f"OK   {rel}" + (f"  [告警] {'; '.join(warn)}" if warn else ""))
    print(f"GATE {len(paths)} 文件 / 红 {red_n}")
    return 1 if red_n else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
