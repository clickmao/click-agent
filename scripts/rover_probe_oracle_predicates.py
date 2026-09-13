#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""R400: 用 oracle 逐**阶段隔离**探测两条判定谓词, 产出 predicates.json (C# 常量表来源)。

教训 (R400 实测): 不能用整条预分词流水线探测单条谓词 —— 后续阶段会二次切分, 导致
把 Zs 类空白误判为「非 \s」(CJK 阶段会把 U+3000 单独切出来, 看起来像 \s 不匹配)。
正确做法: 从 tokenizer.json 重建**单个** Split/Digits 句柄, 只喂该阶段, 再判。
  \s     : trailing 阶段 `\s+$` 判据 "a{X}" → 2 片 (X 为空白)
  数字   : Digits 阶段      判据 "a{X}b" → 3 片 (X 为逐位数字)
探测域: 空白 = 全 BMP 穷举 (65536-2048 代理项) + 增补平面候选; 数字 = 全平面 category∈{Nd,Nl,No} 候选 + 非候选取样负控。
"""
import argparse, json, sys, hashlib, unicodedata
from tokenizers import Tokenizer, Regex
from tokenizers.pre_tokenizers import Split, Digits

ROOT = "/home/agentuser/AgentFramework/"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest()


def to_ranges(cps):
    """排序 + 合并 (并集): 二分查找前提 = 严格升序互不重叠。"""
    out = []
    for cp in sorted(cps):
        if out and cp <= out[-1][1] + 1:
            out[-1] = (out[-1][0], max(out[-1][1], cp))
        else:
            out.append((cp, cp))
    for i in range(1, len(out)):
        assert out[i][0] > out[i - 1][1]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizer-json", required=True)
    ap.add_argument("--out", default=ROOT + "eval/rover/tokref/tables/predicates.json")
    a = ap.parse_args()

    tk = Tokenizer.from_file(a.tokenizer_json)
    tj = json.load(open(a.tokenizer_json, encoding="utf-8"))
    sts = tj["pre_tokenizer"]["pretokenizers"]
    trailing = None
    digits = None
    for p in sts:
        if p["type"] == "Split" and p["pattern"]["Regex"] == "\\s+$":
            trailing = Split(Regex(p["pattern"]["Regex"]), "isolated")
        if p["type"] == "Digits":
            digits = Digits(individual_digits=bool(p.get("individual_digits", False)))
    assert trailing is not None and digits is not None, "未找到 trailing/Digits 阶段"

    def is_space(cp):
        return len(trailing.pre_tokenize_str("a" + chr(cp))) == 2

    def is_digit(cp):
        return len(digits.pre_tokenize_str("a" + chr(cp) + "b")) == 3

    # --- 空白: 全 BMP 穷举 + 增补候选 ---
    space_cps = []
    for cp in range(0x0000, 0x10000):
        if 0xD800 <= cp <= 0xDFFF:
            continue
        if is_space(cp):
            space_cps.append(cp)
    astral_candidates = [cp for cp in range(0x10000, 0x110000) if unicodedata.category(chr(cp)) in ("Zs", "Zl", "Zp")]
    astral_probed = 0
    for cp in astral_candidates:
        astral_probed += 1
        if is_space(cp):
            space_cps.append(cp)

    # --- 数字: category ∈ {Nd,Nl,No} 全候选 (含增补) + 非候选取样负控 ---
    cand = [cp for cp in range(0, 0x110000)
            if not (0xD800 <= cp <= 0xDFFF) and unicodedata.category(chr(cp)) in ("Nd", "Nl", "No")]
    digit_cps = []
    for cp in cand:
        if is_digit(cp):
            digit_cps.append(cp)

    neg_violations = []
    step = max(1, len(range(0, 0x10000)) // 4000)
    neg_probed = 0
    cand_set = set(cand)
    for cp in range(0x0000, 0x10000, step):
        if 0xD800 <= cp <= 0xDFFF or cp in cand_set:
            continue
        neg_probed += 1
        if is_digit(cp):
            neg_violations.append(cp)

    out = {
        "oracle": "huggingface tokenizers (阶段隔离探测)",
        "tokenizer_json_sha256": sha256_file(a.tokenizer_json),
        "method": "stage-isolated: trailing '\\s+$' → 'a{X}'==2片; Digits → 'a{X}b'==3片",
        "space": {
            "probe": "trailing Split(\\s+$), text='a'+chr(cp), 2 片 ⇔ 空白",
            "probed_bmp": 65536 - 2048,
            "probed_astral_candidates": astral_probed,
            "hits": len(space_cps),
            "ranges": [list(r) for r in to_ranges(space_cps)],
        },
        "digit": {
            "probe": "Digits(individual_digits), text='a'+chr(cp)+'b', 3 片 ⇔ 数字",
            "probed_candidates": len(cand),
            "hits": len(digit_cps),
            "negative_probed": neg_probed,
            "negative_violations": neg_violations,
            "ranges": [list(r) for r in to_ranges(digit_cps)],
        },
    }
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"space: hits={len(space_cps)} ranges={len(out['space']['ranges'])} "
          f"[{', '.join(hex(r[0]) + '-' + hex(r[1]) for r in out['space']['ranges'])}]")
    print(f"digit: candidates={len(cand)} hits={len(digit_cps)} ranges={len(out['digit']['ranges'])} "
          f"neg_probed={neg_probed} neg_violations={len(neg_violations)}")
    print(f"negative control verdict = {'SOUND' if not neg_violations else 'VIOLATED'}")
    print("写:", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
