#!/usr/bin/env python3
"""R527 候选① 伴随器: 命名空间收敛的**编译器驱动**收口器 (fail-closed)。

背景: 收敛把 `src/agent.core/{userinteraction,subagent}` 里的类型从 `agent.userinteraction` /
`agent.subagent` 搬到了 `agent.core`; 而 `src/agent/{userinteraction,subagent}` (另一程序集) 仍沿用旧命名空间。
命名空间唯一 ≠ 收敛,落地必须让编译器说话。本器只按编译器报错做最小修补:

  R-A (CS0234 `X does not exist in namespace 'agent.core'`): 全限定名被误改 ⇒ 若 X 声明在遗留目录,
       还原为 `agent.<遗留目录>.X`。
  R-B (CS0234 `... in namespace 'agent.subagent'|'agent.userinteraction'`): 若 X 声明在已搬走目录,
       改写为 `agent.core.X`。
  R-C (CS0246 未找到 'X'): 若 X 声明在遗留目录 ⇒ 给该文件补 `using <遗留命名空间>;`
       (收敛前靠「同命名空间免 using」解析, 搬走后必须显式)。

禁全仓猜测式改写 (会引入 CS0104 歧义 / 误伤同名类型)。用法: --apply / --selfcheck / 默认只读报告。
"""
import io, os, re, subprocess, sys

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                      cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
os.chdir(ROOT)
ENV = dict(os.environ, DOTNET_ROOT=os.path.expanduser("~/.dotnet"))
DOTNET = os.path.expanduser("~/.dotnet/dotnet")
RX_TYPE = re.compile(r"^(?:(?:public|internal|private|protected|static|sealed|abstract|partial|readonly|ref|unsafe)\s+)*"
                     r"(?:record\s+struct|record\s+class|class|record|struct|interface|enum)\s+(?P<n>\w+)", re.M)
RX_ERR = re.compile(r"^(?P<f>[^(\s]+\.cs)\((\d+),\d+\): error (?P<code>CS\d+): (?P<msg>.*)$")
MOVED_DIRS = ("src/agent.core/userinteraction", "src/agent.core/subagent")
LEGACY_NS = {"src/agent/userinteraction": "agent.userinteraction", "src/agent/subagent": "agent.subagent"}
MOVED_NS = "agent.core"
MAX_ROUNDS = 6


def decl_map():
    """类型名 → 声明所在目录 (仅 src 下, 排除 obj/bin)。"""
    d = {}
    for dp, dn, fn in os.walk("src"):
        dn[:] = [x for x in dn if x not in ("obj", "bin")]
        for f in fn:
            if f.endswith(".cs"):
                rel = os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, "/")
                for m in RX_TYPE.finditer(io.open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()):
                    if m.start() == 0 or True:
                        d.setdefault(m.group("n"), rel)
    return d


def build():
    p = subprocess.run([DOTNET, "build", "agent.sln", "-v", "q", "--nologo"], capture_output=True, text=True, env=ENV)
    out = p.stdout + p.stderr
    errs = []
    for l in out.split("\n"):
        m = RX_ERR.match(l.strip())
        if m:
            errs.append((m.group("f").replace(ROOT + "/", ""), m.group("code"), m.group("msg")))
    tot = re.findall(r"(\d+) Error\(s\)", out)
    return errs, (int(tot[0]) if tot else -1)


def main(argv):
    apply = "--apply" in argv
    decl = decl_map()
    errs, nerr = build()
    print(f"类型索引 {len(decl)} 个; 编译错误 {nerr} 条")
    if "--selfcheck" in argv:
        moved = [t for t, f in decl.items() if f.startswith(MOVED_DIRS)]
        legacy = [t for t, f in decl.items() if f.startswith(tuple(LEGACY_NS))]
        print(f"NC_SELFCHECK moved={len(moved)} legacy={len(legacy)} 编译可解读={nerr >= 0}")
        return 0 if (moved and legacy and nerr >= 0) else 1
    for rnd in range(1, MAX_ROUNDS + 1):
        acts = {}
        for f, code, msg in errs:
            m = re.search(r"name '(?P<n>[\w.]+)' does not exist in the namespace '(?P<ns>[\w.]+)'", msg) if code == "CS0234" else None
            m6 = re.search(r"name '(?P<n>[\w.]+)' could not be found", msg) if code == "CS0246" else None
            if m and m.group("ns") == MOVED_NS:
                t = m.group("n")
                for ld, lns in LEGACY_NS.items():
                    if decl.get(m.group("n"), "").startswith(ld):
                        acts.setdefault(f, []).append(("A", f"{MOVED_NS}.{t}", f"{lns}.{t}"))
            elif m and (m.group("ns") in LEGACY_NS.values() or ("agent." + m.group("ns")) in LEGACY_NS.values()):
                t = m.group("n")
                if decl.get(t, "").startswith(MOVED_DIRS):
                    ns = m.group("ns")
                    short = ns.split(".")[-1]
                    acts.setdefault(f, []).append(("B", f"{ns}.{t}", f"{MOVED_NS}.{t}"))
                    acts.setdefault(f, []).append(("B", f"{short}.{t}", f"{MOVED_NS}.{t}"))
            elif (m6 or re.search(r"The name '(?P<n>[\w.]+)' does not exist in the current context", msg)):
                mm = m6 or re.search(r"The name '(?P<n>[\w.]+)' does not exist in the current context", msg)
                t = mm.group("n")
                ld = next((k for k in LEGACY_NS if decl.get(t, "").startswith(k)), None)
                if ld:
                    acts.setdefault(f, []).append(("C", "(using)", LEGACY_NS[ld]))
                elif decl.get(t, "").startswith(MOVED_DIRS):
                    acts.setdefault(f, []).append(("C", "(using)", MOVED_NS))
        if not acts:
            print(f"轮 {rnd}: 无「可机械修补」错误 ⇒ 收口 (剩余 {nerr} 条)")
            break
        for f, ops in sorted(acts.items()):
            p = os.path.join(ROOT, f)
            if not os.path.exists(p):
                continue
            t = io.open(p, encoding="utf-8").read()
            for kind, a, b in ops:
                if kind in ("A", "B"):
                    t = t.replace(a, b)
                elif kind == "C" and not re.search(rf"^using {re.escape(b)};", t, re.M) and not re.search(rf"^namespace {re.escape(b)};", t, re.M):
                    lines = t.split("\n")
                    idx = max((i for i, l in enumerate(lines) if l.startswith("using ") and l.rstrip().endswith(";")), default=None)
                    if idx is not None:
                        lines.insert(idx + 1, f"using {b};")
                        t = "\n".join(lines)
            if apply:
                io.open(p, "w", encoding="utf-8", newline="").write(t)
            print(f"  轮 {rnd}: {f} ops={ops}")
        if not apply:
            break
        errs, nerr = build()
        print(f"  轮 {rnd}: 重编译 错误={nerr}")
        if nerr == 0:
            break
    if apply:
        errs, nerr = build()
        print(f"APPLY {'OK' if nerr == 0 else 'INCOMPLETE'} 编译错误={nerr}")
        for e in errs[:8]:
            print("   ", e)
        return 0 if nerr == 0 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
