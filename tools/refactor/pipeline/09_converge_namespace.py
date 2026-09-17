#!/usr/bin/env python3
"""R527 候选① — 命名空间收敛: agent.userinteraction / agent.subagent → agent.core, 撤销两条豁免。

口径 (机械, fail-closed):
  * 声明侧: src/agent.core/{userinteraction,subagent}/*.cs 的 `namespace agent.userinteraction;` / `agent.subagent;` → `namespace agent.core;`
  * 引用侧: 其余 .cs 的 `using agent.userinteraction;` / `using agent.subagent;` → 已有 `using agent.core;` 则删行, 否则改写为 `using agent.core;`
  * 全限定侧: `agent.userinteraction.` / `agent.subagent.` → `agent.core.`
  * 前置撞名闸: 被并入的类型名若已存在于 agent.core 其他文件 ⇒ 拒收 (合并会撞类型)
用法: --selfcheck | (默认只读报告) | --apply
"""
import io, os, re, subprocess, sys, collections

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                      cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
os.chdir(ROOT)
OLD_NS = ["agent.userinteraction", "agent.subagent"]
NEW_NS = "agent.core"
DECL_DIRS = ["src/agent.core/userinteraction", "src/agent.core/subagent"]
RX_TYPE = re.compile(r"^(?:(?:public|internal|private|protected|static|sealed|abstract|partial|readonly|ref|unsafe|file)\s+)*"
                     r"(?:record\s+struct|record\s+class|class|record|struct|interface|enum)\s+(?P<n>\w+)", re.M)


def cs_files():
    p = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "src"],
                       capture_output=True, text=True)
    return [f for f in p.stdout.split("\n") if f.endswith(".cs") and "/obj/" not in f and "/bin/" not in f]


def precheck(files):
    """撞名闸: 并入类型名 vs agent.core 既有类型名 (排除声明目录自身)。"""
    moved, existing = set(), set()
    for f in files:
        t = io.open(f, encoding="utf-8", errors="replace").read()
        ns = re.search(r"^[ \t]*namespace\s+([\w.]+)\s*;", t, re.M)
        names = {m.group("n") for m in RX_TYPE.finditer(t)}
        if f.startswith(tuple(DECL_DIRS)):
            moved |= names
        elif ns and ns.group(1) == NEW_NS:
            existing |= names
    clash = sorted(moved & existing)
    return moved, existing, clash


def converge(files, apply):
    decl_n = use_drop = use_rew = fq_n = 0
    for f in files:
        t = io.open(f, encoding="utf-8", errors="replace").read()
        o = t
        if f.startswith(tuple(DECL_DIRS)):
            for ns in OLD_NS:
                t = re.sub(rf"^([ \t]*)namespace\s+{re.escape(ns)}\s*;", rf"\1namespace {NEW_NS};", t, flags=re.M)
        else:
            lines = t.split("\n")
            keep = []
            for l in lines:
                s = l.strip()
                if s in (f"using {OLD_NS[0]};", f"using {OLD_NS[1]};"):
                    if f"using {NEW_NS};" in t:
                        use_drop += 1
                        continue
                    use_rew += 1
                    keep.append(l.replace(s, f"using {NEW_NS};"))
                    continue
                keep.append(l)
            t = "\n".join(keep)
            for ns in OLD_NS:
                n = len(re.findall(rf"(?<![\w.]){re.escape(ns)}\.", t))
                if n:
                    fq_n += n
                    t = re.sub(rf"(?<![\w.]){re.escape(ns)}\.", NEW_NS + ".", t)
        if t != o:
            decl_n += 1
            if apply:
                io.open(f, "w", encoding="utf-8", newline="").write(t)
    return decl_n, use_drop, use_rew, fq_n


def residual():
    p = subprocess.run(["grep", "-rn", "-e", "agent.userinteraction", "-e", "agent.subagent", "src"], capture_output=True, text=True)
    return [l for l in p.stdout.split("\n") if l and "/obj/" not in l and "/bin/" not in l]


def main(argv):
    files = cs_files()
    moved, existing, clash = precheck(files)
    print(f"声明目录类型 {len(moved)} 个 / agent.core 既有类型 {len(existing)} 个 / 撞名 {len(clash)}: {clash[:8]}")
    if clash:
        print("ABORT 撞名 ⇒ 拒收")
        return 1
    n, drop, rew, fq = converge(files, "--apply" in argv)
    print(f"改写文件 {n} / 删冗余 using {drop} / 改写 using {rew} / 全限定替换 {fq}")
    left = residual()
    print(f"残留引用 {len(left)}")
    for l in left[:10]:
        print("   ", l[:150])
    if "--apply" in argv:
        print("APPLY", "OK" if (n > 0 and not left) else "INCOMPLETE")
        return 0 if (n > 0 and not left) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
