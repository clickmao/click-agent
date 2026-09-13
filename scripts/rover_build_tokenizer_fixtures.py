#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R400: 从权威 GGUF 抽取分词器表快照 + 生成跨实现对账夹具 (oracle = HF tokenizers, 独立实现)。

用法:
  python3 scripts/rover_build_tokenizer_fixtures.py --tokenizer-json <tokenizer.json> \
      [--gguf /tmp/models/prover7b-q4km.gguf] [--out-dir eval/rover/tokref]

产物:
  eval/rover/tokref/tables/merges.txt         99757 条合并规则 (一行一条)
  eval/rover/tokref/tables/tokens.jsonl.gz    102400 条 {id,type,t}
  eval/rover/tokref/tables/meta.json          sha256 / 计数 / 来源模型 sha256
  eval/rover/tokref/tables/specials.txt       特殊符号 (由 rover_gen_tokenizer_assets.py 生成)
  eval/rover/tokref/fixtures.jsonl            文本 -> 期望 ids          (199 条)
  eval/rover/tokref/pretok_fixtures.jsonl     文本 -> 期望预分词分片   (199 条, 与词表无关)
  eval/rover/tokref/chat_template.jinja       GGUF 内 chat template 原文
  eval/rover/tokref/manifest.json             夹具来源/数量/sha256

夹具构成: 60 条手工边界 + 79 条随机池 + 60 条按派生区间/非区间定向采样 (含增补平面)。
表快照使 C# 侧测试可脱离 4.2GB 模型复跑; --gguf 省略时只重建夹具 (校验现有表未变)。
"""
import argparse, gzip, hashlib, importlib.util, json, os, random, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/"
SIZE = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
FMT = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<B", 10: "<Q", 11: "<q", 12: "<d"}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest()


def load_assets_module():
    p = ROOT + "scripts/rover_gen_tokenizer_assets.py"
    spec = importlib.util.spec_from_file_location("rover_gen_tokenizer_assets", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_gguf_tokenizer(gguf):
    """独立解析实现 (与 C# GgufReader 非共享代码): 读分词器 KV。"""
    f = open(gguf, "rb")

    def rd(fmt, n):
        return struct.unpack(fmt, f.read(n))[0]

    def rv(kind):
        if kind == 8:
            n = rd("<Q", 8)
            return f.read(n).decode("utf-8", "replace")
        if kind == 9:
            ek = rd("<I", 4)
            n = rd("<Q", 8)
            return [rv(ek) for _ in range(n)]
        return rd(FMT[kind], SIZE[kind])

    rd("<I", 4); rd("<I", 4); rd("<Q", 8)
    n_kv = rd("<Q", 8)
    kv = {}
    for _ in range(n_kv):
        k = rv(8); t = rd("<I", 4); kv[k] = rv(t)
    f.close()
    return kv


HAND = [
    "", "a", "ab", "hello", "Hello, world!", "  leading", "trailing   ", "mid  dle",
    "a\nb", "a\r\nb", "a\rb", "tab\there", "line1\nline2\n", "\n\n\n", "   ",
    "1234567890", "0", "007", "3.14159", "1e-9", "1_000_000", "12 + 34 = 46",
    "中文", "你好，世界！", "中文标点：；、。", "汉字与English混合", "普通话测试二〇二五",
    "日本語のテキスト", "한국어 텍스트", "русский текст", "Ελληνικά", "العربية",
    "emoji 😀🎉🚀", "组合 é (e+́)", "café", "naïve", "Ω≈ç√∫", "「引号」【括号】",
    "def f(x):\n    return x*2\n", "x = [i**2 for i in range(10)]", "SELECT * FROM t WHERE a=1;",
    "https://example.com/path?q=1&r=2", "user@example.com", "C:\\Windows\\System32",
    "#!/bin/bash\necho hi", "\\n 转义字面量", "制表\t与 空格　全角空格",
    "   缩进四空格", "…—–“”‘’", "①②③①", "½ ¾ ⅓", "™ © ®", "→ ← ↑ ↓ ⇒ ∀ ∃",
    "Смешанный 混合 Mixed 123", "多行\n中文\n第三行", "<｜begin▁of▁sentence｜>", "文本<｜end▁of▁sentence｜>尾巴",
    "a" * 200, "字" * 100, "🙂" * 40,
]
assert len(HAND) == 60, len(HAND)

POOLS = [
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "0123456789",
    " \t\n\r",
    "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~",
    "的一是不了人我在有他这为之大来以个中上们到说国和地也子时道出而要于就下得可你年生",
    "！？。，、；：（）《》【】“”‘’　",
    "😀🎉🚀✨🔥💡🧠🐍∑∆π≠≤",
    "αβγδεζηθικλμνξοπρστυφχψω",
    "абвгдежзийклмнопрстуфхцчшщ",
    "①②③④⑤⑥⑦⑧⑨",
]


def sample_from_range(lo, hi, rng):
    if hi - lo <= 4096:
        return chr(rng.randint(lo, hi))
    # 大区间: 只取端点与其邻域 (避免抽到未分配码点导致 oracle 行为不可复核)
    return chr(rng.choice([lo, lo + 1, hi - 1, hi]))


def build_targets(ranges_letter, ranges_punct, ranges_cjk, rng):
    """60 条定向用例: 区间内 (含增补平面) 与非区间/对抗形态。"""
    out = []
    for rs in (ranges_letter, ranges_punct, ranges_cjk):
        for lo, hi in rs:
            if len(out) >= 30:
                break
            ch = sample_from_range(lo, hi, rng)
            shape = rng.choice([f"a{ch}b", f"{ch} x", f"x {ch}y", f"{ch}{ch}", f"1{ch}2"])
            out.append(shape)
    OUTSIDE = ["\u0590\u05d0\u05d1", "\u0641\u0642", "\u0e01\u0e02", "\u0905\u0906",
               "\u0301\u0302", "\u200b\u200c", "\ud7b0\ud7b1", "\u2028\u2029",
               "\u00a0\u2000\u2001", "\u3000\u3001\u3002", "\uff01\uff5e", "\u2018\u201f",
               "\u0080\u009f", "\u00ad", "\ufeff", "\ufffd"]
    while len(out) < 60:
        base = rng.choice(OUTSIDE)
        shape = rng.choice([base, f"a{base}b", f"{base} ", f" {base}", f"{base}\n{base}",
                            f"{base}中", f"中{base}文", f"{base}123"])
        out.append(shape)
    return out[:60]


STRESS_POOLS = [
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "0123456789",
    " \t\n\r",
    "，。！？；：、“”‘’（）《》【】…—·\u3000",
    "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~",
    "中文测试普通话随机程序数学难题求证证明",
    "éàüßñçøåæœðþµÀÖØöøƺ",
    "αβγδεζηθικλμνξοπρστυφχψω",
    "абвгдежзийклмнопрстуфхцчшщъыьэюя",
    "अआइईउऊएऐओऔकखगघ",
    "١٢٣٤٥٦٧٨٩٠",
    "\u0300\u0301\u0302\u0308\u0327",
    "😀😁😂🤣😃😄😅😆😉😊😋😎😍😘",
    "½¼¾²³¹①②③④ⅠⅡⅢⅣⅤⅥ",
    "一二三四五六七八九十百千万亿〇",
    "\u200b\ufeff\u00a0\u2028\u2029",
    "\U00010400\U00010437\U0001e900\U0001e943\U00010c80",
    "</|><｜fim▁hole｜><｜User｜><｜Assistant｜><|EOT|>",
    "for (int i = 0; i < n; i++) { sum += a[i]; }",
    "```python\nprint(1 + 1)\n```",
    "\\frac{a}{b} = \\sqrt{x^2 + y^2}",
    "http://example.com/path?a=1&b=2#frag",
    "SELECT * FROM t WHERE id = 42;",
]

SPECIAL_IDS = [100000, 100001, 100008, 100006, 100007]


def gen_stress(tk, n, seed=20260914):
    """压力夹具: 确定性随机文本 (对抗字符集混合), 覆盖跨字符类边界与增补平面。"""
    rnd = random.Random(seed)
    rows = []
    for i in range(n):
        parts = []
        for _ in range(rnd.randint(1, 6)):
            pool = rnd.choice(STRESS_POOLS)
            ln = rnd.randint(1, min(24, len(pool)))
            st = rnd.randrange(0, max(1, len(pool) - ln + 1))
            parts.append(pool[st:st + ln])
            if rnd.random() < 0.25:
                parts.append(" " * rnd.randint(1, 2))
        if rnd.random() < 0.12:
            parts.append(rnd.choice(["<｜end▁of▁sentence｜>", "<|EOT|>", "<｜Assistant｜>"]))
        text = "".join(parts)
        ids = tk.encode(text, add_special_tokens=False).ids
        pieces = [p[0] for p in tk.pre_tokenizer.pre_tokenize_str(text)]
        rows.append({"i": i, "text": text, "ids": ids, "pieces": pieces})
    return rows


def gen_decode(tk, stress_rows, seed=20260914):
    """解码夹具: id 序列 → 文本 (skip_special_tokens 两口径), 覆盖跨 token 多字节复原与特殊符号跳过。"""
    rnd = random.Random(seed + 1)
    cases = []
    for r in stress_rows[:400]:
        ids = list(r["ids"])
        if rnd.random() < 0.25 and ids:
            pos = rnd.randrange(0, len(ids) + 1)
            ids = ids[:pos] + [rnd.choice(SPECIAL_IDS)] + ids[pos:]
        cases.append({"i": len(cases), "ids": ids,
                      "text": tk.decode(ids), "text_raw": tk.decode(ids, skip_special_tokens=False)})
    for sid in SPECIAL_IDS:
        cases.append({"i": len(cases), "ids": [sid], "text": tk.decode([sid]),
                      "text_raw": tk.decode([sid], skip_special_tokens=False)})
    return cases


def build_fixtures(tok_path, out, assets, stress_n=2000):
    from tokenizers import Tokenizer
    tj = json.load(open(tok_path, encoding="utf-8"))
    parsed = [assets.parse_stage(p["pattern"]["Regex"]) for p in tj["pre_tokenizer"]["pretokenizers"] if p["type"] == "Split"]
    letter = next(r for k, r, _ in parsed if k == "class" and len(r) > 50)
    punct = next(r for k, r, _ in parsed if k == "class" and 3 <= len(r) <= 20)
    cjk = next(r for k, r, _ in parsed if k == "class" and len(r) == 3)

    rng = random.Random(20260914)
    rand = []
    while len(rand) < 79:
        pool = rng.choice(POOLS)
        n = rng.randint(1, 40)
        rand.append("".join(rng.choice(pool) for _ in range(n)))
    targets = build_targets(letter, punct, cjk, rng)
    texts = HAND + rand + targets
    assert len(texts) == 199, len(texts)

    tk = Tokenizer.from_file(tok_path)
    pre = tk.pre_tokenizer
    rows, pre_rows = [], []
    for i, t in enumerate(texts):
        ids = tk.encode(t, add_special_tokens=False).ids
        rows.append({"i": i, "text": t, "ids": ids, "tokens": [tk.id_to_token(j) for j in ids]})
        pieces = pre.pre_tokenize_str(t)
        pre_rows.append({"i": i, "text": t, "pieces": [p[0] for p in pieces],
                         "offsets": [[p[1], p[2]] if len(p) > 2 else None for p in pieces]})

    with open(out + "fixtures.jsonl", "w", encoding="utf-8") as w:
        for r in rows:
            w.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(out + "pretok_fixtures.jsonl", "w", encoding="utf-8") as w:
        for r in pre_rows:
            w.write(json.dumps(r, ensure_ascii=False) + "\n")

    stress = gen_stress(tk, stress_n)
    with open(out + "stress_fixtures.jsonl", "w", encoding="utf-8") as w:
        for r in stress:
            w.write(json.dumps(r, ensure_ascii=False) + "\n")
    dec = gen_decode(tk, stress)
    with open(out + "decode_fixtures.jsonl", "w", encoding="utf-8") as w:
        for r in dec:
            w.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "oracle": f"huggingface tokenizers {__import__('tokenizers').__version__} (独立实现, 非本仓代码)",
        "stress_fixtures": len(stress),
        "stress_fixtures_sha256": sha256_file(out + "stress_fixtures.jsonl"),
        "stress_seed": 20260914,
        "decode_fixtures": len(dec),
        "decode_fixtures_sha256": sha256_file(out + "decode_fixtures.jsonl"),
        "oracle_tokenizer_json_sha256": sha256_file(tok_path),
        "fixtures": len(rows),
        "fixtures_sha256": sha256_file(out + "fixtures.jsonl"),
        "pretok_fixtures_sha256": sha256_file(out + "pretok_fixtures.jsonl"),
        "split_pattern_sha256": [hashlib.sha256(p["pattern"]["Regex"].encode()).hexdigest()
                                 for p in tj["pre_tokenizer"]["pretokenizers"] if p["type"] == "Split"],
        "composition": {"hand": 60, "random_pool": 79, "targeted_range": 60},
        "note": "offsets 仅作记录不对账 (不同实现偏移口径不同); 断言对象 = ids 与预分词分片",
    }
    json.dump(manifest, open(out + "manifest.json", "w"), ensure_ascii=False, indent=2)
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizer-json", required=True)
    ap.add_argument("--gguf", default=None)
    ap.add_argument("--out-dir", default=ROOT + "eval/rover/tokref/")
    ap.add_argument("--stress", type=int, default=2000)
    a = ap.parse_args()
    out = a.out_dir if a.out_dir.endswith("/") else a.out_dir + "/"
    os.makedirs(out + "tables", exist_ok=True)
    assets = load_assets_module()

    meta0 = json.load(open(out + "tables/meta.json")) if os.path.exists(out + "tables/meta.json") else None
    if a.gguf:
        kv = read_gguf_tokenizer(a.gguf)
        tokens, types, merges = kv["tokenizer.ggml.tokens"], kv["tokenizer.ggml.token_type"], kv["tokenizer.ggml.merges"]
        assert len(tokens) == len(types) == 102400, (len(tokens), len(types))
        tpl = kv.get("tokenizer.chat_template", "")
        with open(out + "tables/merges.txt", "w", encoding="utf-8") as w:
            for m in merges:
                assert "\n" not in m, "merge 含换行 ⇒ 行式存储不安全"
                w.write(m + "\n")
        with gzip.open(out + "tables/tokens.jsonl.gz", "wt", encoding="utf-8") as w:
            for i, (t, ty) in enumerate(zip(tokens, types)):
                w.write(json.dumps({"id": i, "type": ty, "t": t}, ensure_ascii=False) + "\n")
        open(out + "chat_template.jinja", "w", encoding="utf-8").write(tpl)
        meta = {
            "source_gguf": a.gguf,
            "source_gguf_sha256": sha256_file(a.gguf),
            "source_gguf_size": os.path.getsize(a.gguf),
            "general_architecture": kv["general.architecture"],
            "general_name": kv["general.name"],
            "tokenizer_model": kv["tokenizer.ggml.model"],
            "tokenizer_pre": kv["tokenizer.ggml.pre"],
            "bos_token_id": kv["tokenizer.ggml.bos_token_id"],
            "eos_token_id": kv["tokenizer.ggml.eos_token_id"],
            "add_bos_token": kv["tokenizer.ggml.add_bos_token"],
            "add_eos_token": kv["tokenizer.ggml.add_eos_token"],
            "n_tokens": len(tokens), "n_merges": len(merges),
            "n_control": sum(1 for t in types if t == 3),
            "n_unused": sum(1 for t in types if t == 5),
            "n_normal": sum(1 for t in types if t == 1),
            "tokens_jsonl_gz_sha256": sha256_file(out + "tables/tokens.jsonl.gz"),
            "merges_txt_sha256": sha256_file(out + "tables/merges.txt"),
            "merges_sha256": hashlib.sha256("\n".join(merges).encode()).hexdigest(),
            "chat_template_sha256": hashlib.sha256(tpl.encode()).hexdigest(),
            "chat_template_len": len(tpl),
        }
        json.dump(meta, open(out + "tables/meta.json", "w"), ensure_ascii=False, indent=2)
        print("表快照: tokens", len(tokens), "merges", len(merges), "| meta sha256", meta["source_gguf_sha256"][:16])
        if meta0 and meta0["merges_sha256"] != meta["merges_sha256"]:
            sys.exit("merges sha256 与既有登记不一致 ⇒ 停止 (请人工确认是否换了模型)")
    else:
        if meta0 is None:
            sys.exit("--gguf 未给且无既有 meta.json ⇒ 无法登记来源")
        print("保留既有表快照 (meta sha256", meta0["source_gguf_sha256"][:16], ")")

    man = build_fixtures(a.tokenizer_json, out, assets, a.stress)
    print("夹具:", man["fixtures"], "条 | fixtures_sha256", man["fixtures_sha256"][:16],
          "| pretok_sha256", man["pretok_fixtures_sha256"][:16])
    print("压力夹具:", man["stress_fixtures"], "条 | 解码夹具:", man["decode_fixtures"], "条")
    print("split 正则 sha256:", [h[:12] for h in man["split_pattern_sha256"]])


if __name__ == "__main__":
    main()
