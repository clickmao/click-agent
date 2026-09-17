#!/usr/bin/env python3
"""C# 结构重构器具: 顶层类型外移 (Move Type to own file) + 类内 partial 拆分.

用途 (R526 完全重构):
  report  [--min-lines N] [路径...]   列出含 >1 顶层类型的文件
  extract --apply [--paths P...]      把次要顶层类型外移为 <TypeName>.cs (同目录同命名空间)
  members <file> <Type>               列出该类型的成员边界 (供 partial 切分规划)
  partial --apply <file> <Type> <cut 规格>  按成员切分为 <Type>.<后缀>.cs

切分只做**机械位移**, 不改一字节语义:
  * 命名空间判定: 优先文件级 (namespace X;) 否则块级;
  * 字符串/注释感知的括号深度扫描 (跳过 // /* */ "..." @"..." $"..."; 处理 \" 转义与 {{ }});
  * 类型块 = 声明行 + 上文连续 /// 文档与 [特性] 行 + 配对右花括号行;
  * 成员块 = 深度1 且以上一行以 } 或 ; 结束的那些行.
"""
import io, json, os, re, sys

RX_TYPE = re.compile(
    r"^(?P<mods>(?:(?:public|internal|private|protected|static|sealed|abstract|partial|readonly|ref|unsafe|file)\s+)*)"
    r"(?P<kind>record\s+struct|record\s+class|class|record|struct|interface|enum)\s+(?P<name>\w+)")
RX_NS = re.compile(r"^[ \t]*namespace\s+([\w.]+)\s*([;{])", re.M)
RX_DOC = re.compile(r"^\s*(///|\[|\s*$)")


def scan_depths(text):
    """返回每行起始处的括号深度 (字符串/注释感知)."""
    depths = []
    depth = 0
    i, n = 0, len(text)
    line_start_depth = 0
    at_line_start = True
    while i < n:
        c = text[i]
        if at_line_start:
            depths.append(depth)
            at_line_start = False
        if c == "\n":
            at_line_start = True
            i += 1
            continue
        # 行注释
        if text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        # 块注释
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        # 原始字符串 """
        if text.startswith('"""', i):
            j = text.find('"""', i + 3)
            while j >= 0 and j + 3 < n and text[j + 3] == '"' and text[j + 4:j + 5] == '"':
                j += 1
            i = n if j < 0 else j + 3
            continue
        # 逐字/普通字符串
        if c == "@" and text.startswith('@"', i):
            i += 2
            while i < n:
                if text[i] == '"':
                    if i + 1 < n and text[i + 1] == '"':
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue
        if c == '"':
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if c == "'":  # 字符字面量
            i += 1
            while i < n and text[i] != "'":
                i += 2 if text[i] == "\\" else 1
            i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    while len(depths) < text.count("\n") + 1:
        depths.append(depth)
    return depths


def read(path):
    return io.open(path, encoding="utf-8").read()


def ns_of(text):
    m = RX_NS.search(text)
    return m.group(1) if m else None


def ns_form(text):
    """返回 ('file'|'block'|'none', 文件头 `namespace X[;{]` 的原文或 'namespace X')."""
    head = text[:text.find("{")] if "{" in text else text
    m = RX_NS.search(head)
    if not m:
        return ("none", None)
    if m.group(2) == ";":
        return ("file", m.group(0).strip())
    return ("block", "namespace " + m.group(1))


def collect_head(t):
    """新文件头: usings 原样 + 命名空间声明 (块级附左花括号). 返回 (头文本, 尾文本, 是否需缩进)."""
    lines = t.split("\n")
    usings = [l for l in lines if l.strip().startswith("using ")]
    h = "\n".join(usings) + ("\n\n" if usings else "")
    form, ns = ns_form(t)
    if form == "file":
        return (h + ns + "\n\n", "", False)
    if form == "block":
        return (h + ns + "\n{\n", "\n}\n", True)
    return (h, "", False)


def emit(t, body_lines):
    """把类型块文本包装成独立文件内容 (补 usings + 命名空间)."""
    head, tail, indent = collect_head(t)
    if indent:
        body_lines = ["    " + l if l.strip() else l for l in body_lines]
    return head + "\n".join(body_lines) + tail


def top_types(text):
    """返回 [(name, start_line, end_line, start_char, end_char)] (0-based, end 含)."""
    lines = text.split("\n")
    if not lines:
        return []
    offs = [0]
    for l in lines:
        offs.append(offs[-1] + len(l) + 1)
    depths = scan_depths(text)
    nd = 0  # 文件级命名空间 => 类型深度 0
    form, _ = ns_form(text)
    if form == "block":
        nd = 0  # 块级: 命名空间自身 depth 从 0 进入, 类型在 depth 1
    out = []
    for idx, l in enumerate(lines):
        if depths[idx] != (1 if form == "block" else 0):
            continue
        m = RX_TYPE.match(l.lstrip())
        if not m:
            continue
        # 上文文档/特性块
        s = idx
        while s - 1 >= 0 and RX_DOC.match(lines[s - 1]) and not lines[s - 1].strip().startswith("}"):
            s -= 1
        # 找配对右括号 (类型体内部深度 = nd + 1, 收尾 } 所在行的行首深度即 nd + 1)
        e = idx
        nd = 1 if form == "block" else 0
        body_depth = nd + 1
        while e < len(lines):
            if depths[e] == body_depth and lines[e].strip().startswith("}"):
                break
            e += 1
        if e >= len(lines):
            e = len(lines) - 1
        out.append((m.group("name"), s, e, offs[s], offs[e] + len(lines[e])))
    return out


def cli_paths(args):
    """去掉 --flag 与其取值, 返回路径列表 (默认 src)."""
    out = []
    skip = False
    for a in args:
        if skip:
            skip = False
            continue
        if a == "--manifest":
            skip = True
            continue
        if a.startswith("--"):
            continue
        out.append(a)
    return out or ["src"]


def cmd_report(args):
    min_lines = 0
    paths = cli_paths(args)
    if "--min-lines" in args:
        min_lines = int(args[args.index("--min-lines") + 1])
        paths = [p for p in paths if p != str(min_lines)]
    if not paths:
        paths = ["src"]
    files = []
    for p in paths:
        if os.path.isfile(p):
            files.append(p)
            continue
        for dp, dn, fn in os.walk(p):
            dn[:] = [d for d in dn if d not in ("obj", "bin")]
            files += [os.path.join(dp, f) for f in fn if f.endswith(".cs")]
    multi, moved = [], 0
    for f in sorted(files):
        t = read(f)
        ts = top_types(t)
        if len(ts) > 1:
            multi.append((f, t.count("\n") + 1, [x[0] for x in ts]))
            moved += len(ts) - 1
    print(f"[多类型文件] {len(multi)} 个 / 可外移类型 {moved} 个")
    for f, n, names in multi:
        if n >= min_lines:
            print(f"  {n:5d} 行  {f}  -> {', '.join(names)}")
    return 0


def cmd_extract(args):
    apply_ = "--apply" in args
    paths = cli_paths(args)
    files = []
    for p in paths:
        if os.path.isfile(p):
            files.append(p)
            continue
        for dp, dn, fn in os.walk(p):
            dn[:] = [d for d in dn if d not in ("obj", "bin")]
            files += [os.path.join(dp, f) for f in fn if f.endswith(".cs")]
    total = 0
    skipped_file_scoped = []
    manifest = []
    man_path = None
    if "--manifest" in args:
        man_path = args[args.index("--manifest") + 1]
    for f in sorted(files):
        t = read(f)
        ts = top_types(t)
        if len(ts) < 2:
            continue
        stem = os.path.basename(f)[:-3]
        # 主类型: 名字 == 文件名的优先; 否则最长的那个
        named = [x for x in ts if x[0] == stem]
        keep = named[0] if named else max(ts, key=lambda x: x[2] - x[1])
        others = [x for x in ts if x is not keep]
        if not named:
            # 文件名不是任何类型名 (如 *Types.cs / *Enums.cs) => 全部外移, 原文件删除
            others = list(ts)
        # file 作用域类型不可外移 (只在本文件可见)
        lines0 = t.split("\n")
        movable = []
        for x in others:
            dl = ""
            for i in range(x[1], min(x[2], len(lines0) - 1) + 1):
                if RX_TYPE.match(lines0[i].lstrip()):
                    dl = lines0[i].strip()
                    break
            if re.match(r"^file\s", dl):
                skipped_file_scoped.append((f, x[0]))
                continue
            movable.append(x)
        others = movable
        if not others:
            continue
        d = os.path.dirname(f)
        parts = []
        for name, s, e, cs, ce in others:
            dst = os.path.join(d, name + ".cs")
            if os.path.exists(dst):
                print(f"  [跳过] {dst} 已存在")
                continue
            block_lines = t[cs:ce].rstrip().split("\n")
            body = emit(t, block_lines)
            parts.append((s, e, name, dst, body))
        if not parts:
            continue
        deletable = not named
        print(f"  {f}: 外移 {', '.join(p[2] for p in parts)}" + ("  [并删除原文件]" if deletable else ""))
        manifest.append({"src": f, "new": [p[3] for p in parts], "delete_src": deletable})
        total += len(parts)
        if not apply_:
            continue
        offs = [0]
        for l in t.split("\n"):
            offs.append(offs[-1] + len(l) + 1)
        nt = t
        for s, e, name, dst, body in sorted(parts, key=lambda p: -p[1]):
            ce = offs[e + 1] if e + 1 < len(offs) else len(t)
            nt = nt[:offs[s]] + nt[ce:]
            with io.open(dst, "w", encoding="utf-8") as fh:
                fh.write(body)
        if deletable:
            res = nt.split("\n")
            danger = [l for l in res if re.match(r"^\s*(\[assembly:|\[module:|global using|#if|#region|#pragma)", l)]
            code = [l for l in res if l.strip()
                    and not l.strip().startswith(("using ", "//", "namespace "))
                    and not re.match(r"^\s*namespace\s+[\w.]+\s*;$", l.strip())]
            if danger or code:
                with io.open(f, "w", encoding="utf-8") as fh:
                    fh.write(nt)
                print(f"  [保留原文件] {f} 残留: {(danger or code)[:2]}")
            else:
                os.remove(f)
        else:
            with io.open(f, "w", encoding="utf-8") as fh:
                fh.write(nt)
    if skipped_file_scoped:
        print(f"[file 作用域跳过] {len(skipped_file_scoped)}: " + ", ".join(f"{a}:{b}" for a, b in skipped_file_scoped[:10]))
    if man_path:
        with io.open(man_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(manifest, ensure_ascii=False, indent=1))
        print(f"[清单] {man_path}  ({len(manifest)} 个源文件)")
    print(f"[{'已写入' if apply_ else '演练'}] 共外移 {total} 个类型")
    return 0


def cmd_members(args):
    f, typ = args[0], args[1]
    t = read(f)
    ts = {x[0]: x for x in top_types(t)}
    if typ not in ts:
        print("类型未找到:", typ, list(ts))
        return 2
    _, s, e, _, _ = ts[typ]
    lines = t.split("\n")
    depths = scan_depths(t)
    depth_in = depths[s + 1] if s + 1 < len(depths) else 1
    print(f"{f} :: {typ}  行 {s+1}..{e+1}  (体内深度={depth_in})")
    cur = None
    for i in range(s, min(e, len(lines) - 1) + 1):
        l = lines[i]
        lst = l.strip()
        if depths[i] == depth_in and lst and not lst.startswith(("//", "///", "#")):
            if cur:
                print(f"      ^ 到 {i} 行 (共 {i - cur} 行)")
            cur = i
            print(f"  {i+1:5d} 起: {lst[:110]}")
    if cur:
        print(f"      ^ 到 {e} 行 (共 {e - cur} 行)")
    return 0


def cmd_partial(args):
    apply_ = "--apply" in args
    f, typ, spec = args[0], args[1], args[2]
    t = read(f)
    ts = {x[0]: x for x in top_types(t)}
    if typ not in ts:
        print("类型未找到")
        return 2
    _, s, e, _, _ = ts[typ]
    lines = t.split("\n")
    depths = scan_depths(t)
    depth_in = depths[s + 1]
    # 成员起点
    starts = []
    for i in range(s + 1, e + 1):
        lst = lines[i].strip()
        if depths[i] == depth_in and lst and not lst.startswith(("//", "///", "#")):
            j = i
            while j - 1 > s and (lines[j - 1].strip().startswith(("///", "//", "[")) or not lines[j - 1].strip()):
                j -= 1
            starts.append((i, j))
    # 成员名 = 起点行的签名尾名
    def mname(i):
        sig = lines[i].strip()
        m = re.search(r"(\w+)\s*\(", sig)
        name = m.group(1) if m else re.split(r"[=;{]", sig)[0].strip().split()[-1]
        return name
    names = [mname(i) for i, _ in starts]
    print("成员数:", len(starts))
    cuts = {}
    for pair in spec.split(","):
        k, v = pair.split("=")
        if k not in names:
            print("!! 成员名未找到:", k, "候选:", names[:40])
            return 2
        cuts[starts[names.index(k)][1]] = v
    order = sorted(cuts)
    print("切点行:", [(c + 1, cuts[c]) for c in order])
    if not apply_:
        return 0
    head_ns = ns_form(t)
    # 主体: 先把 class 声明行改 partial
    decl_i = None
    for i in range(s, min(s + 40, e)):
        lm = RX_TYPE.match(lines[i].lstrip())
        if lm and lm.group("name") == typ:
            decl_i = i
            break
    if decl_i is None:
        print("!! 未定位类声明行")
        return 2
    if "partial" not in lines[decl_i]:
        lines[decl_i] = lines[decl_i].replace("class " + typ, "partial class " + typ, 1)
    head, tail, _ind = collect_head(t)
    brace_i = decl_i
    while brace_i <= e and "{" not in lines[brace_i]:
        brace_i += 1
    decl_no_brace = "\n".join(lines[decl_i:brace_i]).rstrip()
    header = head + decl_no_brace + "\n{\n"
    segs = []
    prev = starts[0][1]
    for c in order:
        segs.append((prev, c))
        prev = c
    segs.append((prev, e + 1))
    base = f[:-3]
    for k, (a, b) in enumerate(segs):
        suffix = "主" if k == 0 else None
        # 找出该段所属后缀
        for c in order:
            if c == a:
                suffix = cuts[c]
        if suffix is None:
            print("!! 段无后缀", a, b)
            return 2
        dst = base + ("" if k == 0 else "." + suffix) + ".cs"
        body = "\n".join(lines[a:b]).rstrip()
        out = header + body + "\n" + tail
        with io.open(dst, "w", encoding="utf-8") as fh:
            fh.write(out)
        print("写入", dst, b - a, "行")
    # 原文件保留前半 (到第一个切点) => 由上面 k==0 段写入同路径 base + ".cs"
    print("done")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd, args = sys.argv[1], sys.argv[2:]
    return {"report": cmd_report, "extract": cmd_extract, "members": cmd_members, "partial": cmd_partial}[cmd](args)


if __name__ == "__main__":
    sys.exit(main())
