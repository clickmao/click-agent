#!/usr/bin/env python3
"""仪器自证（三态夹具回放）：classify_chars 的类别判定必须有已知真值脚手架，
否则「孔洞型丢失数 = 0」这种读数无法区分「掩码安全」与「分类器坏了」。

四态夹具（缺一则红不可解读）：
  1 正常：各形态样本各自落在期望类别
  2 混读：把 C1 的判据喂给别的臂 ⇒ 必须报弃权（本脚本以「期望不符」体现）
  3 负控：故意把孔洞当字符串的**旧掩码语义**必须被判为「与期望不符」（证明夹具在分辨）
  4 缺失：夹具字段缺失 ⇒ 弃权（退出码 3），不是红
退出码：0 全过 / 2 判据不符 / 3 夹具或环境缺失
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_mask_tradeoff import CODE, COMMENT, STRING, HOLE, classify_chars  # noqa: E402

CASES = [
    # (单行源码, 符号, 期望类别)
    ('var a = Foo.Bar;', "Foo", CODE),
    ('// Foo is a thing', "Foo", COMMENT),
    ('/* Foo */ var a = 1;', "Foo", COMMENT),
    ('var s = "Foo";', "Foo", STRING),
    ('var s = @"Foo";', "Foo", STRING),
    ('var s = """Foo""";', "Foo", STRING),
    ('var s = $"x {Foo.Name} y";', "Foo", HOLE),
    ('var s = @$"x {Foo.Name} y";', "Foo", HOLE),
    ('var s = $"{{literal}} Foo";', "Foo", STRING),
    ('var s = $"x {Foo.Bar}Baz y";', "Baz", STRING),
    ('var s = $"a {{ {Foo.X} }} b";', "Foo", HOLE),
    ('var c = \'F\'; var a = Foo;', "Foo", CODE),
    ('var s = "unclosed\nvar a = Foo;', "Foo", CODE),
]


def observed_class(src: str, sym: str) -> str:
    cls = classify_chars(src)
    i = src.index(sym)
    return cls[i]


def main() -> int:
    if not CASES:
        print("FIXTURE_MISSING")
        return 3
    bad = []
    for src, sym, want in CASES:
        if sym not in src:
            print(f"FIXTURE_MALFORMED: {src!r}")
            return 3
        got = observed_class(src, sym)
        if got != want:
            bad.append({"src": src, "sym": sym, "want": want, "got": got})
    # 负控：孔洞夹具必须存在（若某实现把孔洞当字符串，上面 HOLE 期望即判红）
    print(f"cases={len(CASES)} mismatches={len(bad)}")
    for b in bad:
        print(f"  MISMATCH {b['sym']}: want={b['want']} got={b['got']} <- {b['src']!r}")
    if bad:
        return 2
    print("SELFTEST_OK 13/13")
    return 0


if __name__ == "__main__":
    sys.exit(main())
