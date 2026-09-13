#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""R400: 从权威 tokenizer.json 机器生成 C# 分词器常量资产 (禁止手抄正则/区间)。

用法:
  python3 scripts/rover_gen_tokenizer_assets.py --tokenizer-json <path> [--check]

产物:
  src/agent.rover/token/TokenizerAssets.g.cs   5 条 Split 正则原文 + sha256 + 派生区间表 + 摘要 + 特殊符号
  eval/rover/tokref/chat_golden.jsonl                jinja2(transformers 同参) 渲染的模板黄金样本
  eval/rover/tokref/tables/specials.txt              特殊符号表 (special=True 的 added tokens)

为什么不用 .NET Regex: 正则内含增补平面(Deseret/Medefaidrin 等)区间, .NET 按 UTF-16 码元解析
会把 `𐐀-𐑏` 拆成孤立代理项 + 反向区间, 造成静默过量匹配 (与 Rust regex 的标量语义不同)。
故生成器把字符类解析成**标量区间表**, C# 侧用标量扫描器精确复刻, 并以摘要自校验防漂移。

--check: 只比对磁盘产物与当前输入是否一致 (不一致 ⇒ 退出码 1)。
"""
import argparse, hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/"
OUT_CS = ROOT + "src/agent.rover/token/TokenizerAssets.g.cs"
OUT_GOLDEN = ROOT + "eval/rover/tokref/chat_golden.jsonl"
OUT_SPLIT_TOKENS = ROOT + "eval/rover/tokref/tables/split_tokens.txt"
OUT_SPECIAL_TOKENS = ROOT + "eval/rover/tokref/tables/special_tokens.txt"
OLD_CS = ROOT + "src/agent.rover/token/PretokenizerPatterns.g.cs"


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest()


def cs_literal(s):
    out = []
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 0x20:
            out.append("\\u%04x" % ord(ch))
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def unescape_class(content):
    """把正则字符类内容按 Unicode 标量分解为 (lo, hi) 区间表。支持 \\r \\n \\t \\- \\] \\\\ 转义。"""
    toks = []
    i = 0
    while i < len(content):
        c = content[i]
        if c == "\\":
            i += 1
            e = content[i]
            esc = {"r": ord("\r"), "n": ord("\n"), "t": ord("\t"),
                   "-": ord("-"), "]": ord("]"), "\\": ord("\\")}
            toks.append(esc.get(e, ord(e)))
        else:
            toks.append(ord(c))
        i += 1
    ranges = []
    j = 0
    while j < len(toks):
        if j + 2 < len(toks) and toks[j + 1] == ord("-") and toks[j + 2] != ord("]"):
            ranges.append((toks[j], toks[j + 2]))
            j += 3
        else:
            ranges.append((toks[j], toks[j]))
            j += 1
    return ranges


def parse_stage(pat):
    """把 Split 正则解析为 (kind, ranges, space_prefix)。kind ∈ newline / class / trailing_space。"""
    if pat == "[" + "\r" + "\n" + "]":
        return ("newline", [], False)
    if pat == "\\s+$":
        return ("trailing_space", [], False)
    body = pat
    prefix = False
    if body.startswith("\\s?"):
        body = body[3:]
        prefix = True
    assert body.startswith("[") and body.endswith("]+"), f"无法解析: {pat!r}"
    rs = unescape_class(body[1:-2])
    return ("class", rs, prefix)


def normalize_ranges(rs):
    """排序 + 合并 (并集), 并断言严格升序互不重叠 —— 二分查找的前提, 否则静默漏判。"""
    out = []
    for lo, hi in sorted(rs):
        if out and lo <= out[-1][1] + 1:
            out[-1] = (out[-1][0], max(out[-1][1], hi))
        else:
            out.append((lo, hi))
    for i in range(1, len(out)):
        assert out[i][0] > out[i - 1][1], f"区间未归一化: {out[i-1]} {out[i]}"
    return out


def ranges_digest(*tables):
    """区间表的规范化摘要 (跨语言一致: "lo-hi" 列表以 ';' 连接后取 UTF-8 sha256)。"""
    parts = []
    for t in tables:
        parts.append(",".join(f"{lo}-{hi}" for lo, hi in t))
    return sha256_bytes("|".join(parts).encode("utf-8"))


def build(tok_path, tpl_path):
    tj = json.load(open(tok_path, encoding="utf-8"))
    src_sha = sha256_file(tok_path)
    stages = [(p["pattern"]["Regex"], p.get("behavior")) for p in tj["pre_tokenizer"]["pretokenizers"] if p["type"] == "Split"]
    if len(stages) != 5:
        sys.exit(f"期望 5 条 Split 正则, 实际 {len(stages)}")
    for pat, beh in stages:
        if beh != "Isolated":
            sys.exit(f"未预期的 Split behavior: {beh} (只支持 Isolated)")
    parsed = [parse_stage(p) for p, _ in stages]
    letter = next(r for k, r, _ in parsed if k == "class" and len(r) > 50)
    punct = next(r for k, r, _ in parsed if k == "class" and 3 <= len(r) <= 20)
    cjk = next(r for k, r, _ in parsed if k == "class" and len(r) == 3)
    prefixes = [pre for _, _, pre in parsed]
    letter, punct, cjk = normalize_ranges(letter), normalize_ranges(punct), normalize_ranges(cjk)
    # --- 谓词表: 由 oracle 穷举探测产出 (见 rover_probe_oracle_predicates.py), 不按文档猜 ---
    pred_path = ROOT + "eval/rover/tokref/tables/predicates.json"
    pred = json.load(open(pred_path, encoding="utf-8"))
    if pred["tokenizer_json_sha256"] != src_sha:
        sys.exit(f"predicates.json 与 tokenizer.json 不同源: {pred['tokenizer_json_sha256'][:16]} != {src_sha[:16]}")
    space = normalize_ranges([tuple(r) for r in pred["space"]["ranges"]])
    digit = normalize_ranges([tuple(r) for r in pred["digit"]["ranges"]])
    if pred["digit"]["negative_violations"]:
        sys.exit("数字谓词负控违规")
    digest = ranges_digest(letter, punct, cjk, space, digit)
    pred_digest = sha256_file(pred_path)

    def rows(name, rs, indent="        "):
        return [f"{indent}{lo}, {hi}," for lo, hi in rs]

    L = []
    L.append("// <auto-generated>")
    L.append("//   由 scripts/rover_gen_tokenizer_assets.py 从权威 tokenizer.json 机器生成 — 禁止手工编辑。")
    L.append("//   手抄正则/区间会自我印证 (R389 教训): 常量必须由源头生成并带 sha256 自校验。")
    L.append(f"//   源: {os.path.basename(tok_path)} sha256={src_sha}")
    L.append("// </auto-generated>")
    L.append("")
    L.append("namespace agent.rover.token;")
    L.append("")
    L.append("/// <summary>")
    L.append("/// DeepSeek(deepseek-llm) 分词器常量资产: 预分词 Split 正则原文 + 派生标量区间表 + 特殊符号。")
    L.append("/// 区间表是正则的机器派生 (标量语义), C# 侧用 Pretokenizer 的扫描器消费 —— 不使用 .NET Regex,")
    L.append("/// 因为 .NET 按 UTF-16 码元解析字符类, 对增补平面区间会静默过量匹配。")
    L.append("/// </summary>")
    L.append("public static class TokenizerAssets")
    L.append("{")
    L.append(f'    public const string SourceSha256 = "{src_sha}";')
    L.append("")
    L.append("    /// <summary>Split 正则原文 (顺序 = 流水线顺序), 用于对外输出与 sha256 自校验。</summary>")
    L.append("    public static readonly string[] Splits =")
    L.append("    [")
    for p, _ in stages:
        L.append(f"        {cs_literal(p)},")
    L.append("    ];")
    L.append("")
    L.append("    /// <summary>每条 Split 正则 UTF-8 sha256 (与权威源逐条比对)。</summary>")
    L.append("    public static readonly string[] SplitSha256 =")
    L.append("    [")
    for p, _ in stages:
        L.append(f'        "{sha256_bytes(p.encode("utf-8"))}",')
    L.append("    ];")
    L.append("")
    L.append("    /// <summary>每条 Split 是否带 \\s? 可选空白前缀 (机器派生, 决定扫描器起始语义)。</summary>")
    L.append("    public static readonly bool[] StageSpacePrefix =")
    L.append("    [")
    L.append("        " + ", ".join("true" if p else "false" for p in prefixes) + ",")
    L.append("    ];")
    L.append("")
    L.append("    /// <summary>字母类区间 (第 2 条 Split: \\s?[字母集]+), (lo,hi) 成对, 标量码点。</summary>")
    L.append("    public static readonly int[] LetterRanges =")
    L.append("    [")
    L.extend(rows("letter", letter))
    L.append("    ];")
    L.append("")
    L.append("    /// <summary>标点类区间 (第 3 条 Split: \\s?[标点集]+)。</summary>")
    L.append("    public static readonly int[] PunctRanges =")
    L.append("    [")
    L.extend(rows("punct", punct))
    L.append("    ];")
    L.append("")
    L.append("    /// <summary>CJK/谚文类区间 (第 5 条 Split: [一-龥ࠀ-一가-퟿]+)。</summary>")
    L.append("    public static readonly int[] CjkRanges =")
    L.append("    [")
    L.extend(rows("cjk", cjk))
    L.append("    ];")
    L.append("")
    L.append("    /// <summary>空白判定表 (\\s 语义; oracle 阶段隔离探测: trailing 单独喂 'a{X}', 全 BMP 穷举+增补候选 = 25 码点 = Unicode White_Space)。</summary>")
    L.append("    public static readonly int[] SpaceRanges =")
    L.append("    [")
    L.extend(rows("space", space))
    L.append("    ];")
    L.append("")
    L.append(f"    /// <summary>数字判定表 (Digits 逐位个体化; oracle 阶段隔离探测: 候选 {pred['digit']['probed_candidates']} 命中 {pred['digit']['hits']}, 负控 {pred['digit']['negative_probed']} 例 0 违规)。</summary>")
    L.append("    public static readonly int[] DigitRanges =")
    L.append("    [")
    L.extend(rows("digit", digit))
    L.append("    ];")
    L.append("")
    L.append(f'    /// <summary>谓词表来源文件 sha256 (eval/rover/tokref/tables/predicates.json)。</summary>')
    L.append(f'    public const string PredicatesSourceSha256 = "{pred_digest}";')
    L.append("")
    L.append(f'    /// <summary>三张区间表的规范化摘要 (防 C# 侧被手改: 运行时重算比对)。</summary>')
    L.append(f'    public const string RangesDigest = "{digest}";')
    L.append("")
    added = tj.get("added_tokens", [])
    split_toks = [a["content"] for a in added]
    special_toks = [a["content"] for a in added if a.get("special")]
    L.append("    /// <summary>编码前需切分的符号: tokenizer.json added_tokens 全体 (实测: 与 special 标志无关, 18/18 均切)。</summary>")
    L.append("    public static readonly string[] SplitTokens =")
    L.append("    [")
    for s in split_toks:
        L.append(f"        {cs_literal(s)},")
    L.append("    ];")
    L.append("")
    L.append(f'    /// <summary>切分集 sha256 (UTF-8 逐行 join 后)。</summary>')
    L.append(f'    public const string SplitTokensDigest = "{sha256_bytes(chr(10).join(split_toks).encode("utf-8"))}";')
    L.append("")
    L.append("    /// <summary>decode(skip_special_tokens=true) 时跳过的符号: added_tokens 中 special=true 者 (3/18)。</summary>")
    L.append("    public static readonly string[] SpecialTokens =")
    L.append("    [")
    for s in special_toks:
        L.append(f"        {cs_literal(s)},")
    L.append("    ];")
    L.append("")
    L.append(f'    /// <summary>特殊符号表 sha256 (UTF-8 逐行 join 后)。</summary>')
    L.append(f'    public const string SpecialTokensDigest = "{sha256_bytes(chr(10).join(special_toks).encode("utf-8"))}";')
    L.append("}")
    cs = "\n".join(L) + "\n"

    # --- 切分集 / 特殊符号表 (纯文本, 供测试/工具读取) ---
    sp_txt = "\n".join(split_toks) + "\n"
    sp_special_txt = "\n".join(special_toks) + "\n"

    # --- chat template 黄金样本 (jinja2 = transformers 同引擎同参数) ---
    import jinja2
    from jinja2.sandbox import ImmutableSandboxedEnvironment
    tpl = open(tpl_path, encoding="utf-8").read()
    env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
    env_plain = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
    t = env.from_string(tpl)
    t_plain = env_plain.from_string(tpl)
    BOS = "<｜begin▁of▁sentence｜>"

    cases = [
        {"name": "system+user+gen", "messages": [{"role": "system", "content": "你是助手。"},
                                                 {"role": "user", "content": "你好"}], "agp": True},
        {"name": "system+user+no-gen", "messages": [{"role": "system", "content": "你是助手。"},
                                                     {"role": "user", "content": "你好"}], "agp": False},
        {"name": "user-only+gen", "messages": [{"role": "user", "content": "1+1=?"}], "agp": True},
        {"name": "user-only+no-gen", "messages": [{"role": "user", "content": "1+1=?"}], "agp": False},
        {"name": "multi-turn+gen", "messages": [{"role": "user", "content": "写个函数"},
                                                {"role": "assistant", "content": "def f(): pass"},
                                                {"role": "user", "content": "改成两倍"}], "agp": True},
        {"name": "assistant-last+gen", "messages": [{"role": "user", "content": "hi"},
                                                     {"role": "assistant", "content": "hello"}], "agp": True},
        {"name": "multi-system+gen", "messages": [{"role": "system", "content": "规则A"},
                                                   {"role": "system", "content": "规则B"},
                                                   {"role": "user", "content": "开始"}], "agp": True},
        {"name": "empty-user+gen", "messages": [{"role": "user", "content": ""}], "agp": True},
        {"name": "whitespace-user+gen", "messages": [{"role": "user", "content": "  \n\t"}], "agp": True},
        {"name": "assistant-only+gen", "messages": [{"role": "assistant", "content": "开头是助手"}], "agp": True},
        {"name": "assistant-only+no-gen", "messages": [{"role": "assistant", "content": "开头是助手"}], "agp": False},
        {"name": "specials-in-content", "messages": [{"role": "user", "content": "x<｜end▁of▁sentence｜>y"}], "agp": True},
    ]
    golden = []
    for c in cases:
        ctx = {"messages": c["messages"], "add_generation_prompt": c["agp"], "bos_token": BOS}
        rendered = t.render(**ctx)
        golden.append({"name": c["name"], "messages": c["messages"], "add_generation_prompt": c["agp"],
                       "bos_token": BOS, "rendered": rendered, "rendered_plain_env": t_plain.render(**ctx),
                       "env_options": "trim_blocks=True,lstrip_blocks=True",
                       "rendered_sha256": sha256_bytes(rendered.encode("utf-8"))})
    differing = [g["name"] for g in golden if g["rendered"] != g["rendered_plain_env"]]
    return cs, sp_txt, sp_special_txt, "\n".join(json.dumps(g, ensure_ascii=False) for g in golden) + "\n", differing, digest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizer-json", required=True)
    ap.add_argument("--chat-template", default=ROOT + "eval/rover/tokref/chat_template.jinja")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    meta_path = ROOT + "eval/rover/tokref/tables/meta.json"
    if os.path.exists(meta_path):
        want = json.load(open(meta_path))["chat_template_sha256"]
        have = sha256_bytes(open(a.chat_template, "rb").read())
        if want != have:
            sys.exit(f"chat template 与 GGUF 登记不符: meta={want} file={have}")
    cs, sp, sp_special, golden, differing, digest = build(a.tokenizer_json, a.chat_template)
    if a.check:
        bad = []
        for path, want in ((OUT_CS, cs), (OUT_SPLIT_TOKENS, sp), (OUT_SPECIAL_TOKENS, sp_special), (OUT_GOLDEN, golden)):
            have = open(path, encoding="utf-8").read() if os.path.exists(path) else None
            if have != want:
                bad.append(path)
        print("assets_check =", "STALE" if bad else "FRESH", "| stale:", bad)
        sys.exit(1 if bad else 0)
    os.makedirs(os.path.dirname(OUT_CS), exist_ok=True)
    open(OUT_CS, "w", encoding="utf-8").write(cs)
    open(OUT_SPLIT_TOKENS, "w", encoding="utf-8").write(sp)
    open(OUT_SPECIAL_TOKENS, "w", encoding="utf-8").write(sp_special)
    open(OUT_GOLDEN, "w", encoding="utf-8").write(golden)
    if os.path.exists(OLD_CS):
        os.remove(OLD_CS)
        print("移除过时产物:", OLD_CS)
    print("生成:", OUT_CS, os.path.getsize(OUT_CS), "B | RangesDigest =", digest)
    print("生成:", OUT_SPLIT_TOKENS, os.path.getsize(OUT_SPLIT_TOKENS), "B | split_tokens =", len(sp.strip().splitlines()))
    print("生成:", OUT_SPECIAL_TOKENS, os.path.getsize(OUT_SPECIAL_TOKENS), "B | special_tokens =", len(sp_special.strip().splitlines()))
    print("生成:", OUT_GOLDEN, os.path.getsize(OUT_GOLDEN), "B | cases =", len(golden.strip().splitlines()))
    print("trim 参数差异样本:", differing if differing else "无差异")


if __name__ == "__main__":
    main()
