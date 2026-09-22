#!/usr/bin/env python3
"""R630 · 冻结前缀读数（四档 chars/sha + **只加厚**不变量机检）。

派生纪律: 一切数字**由产物自身派生**（import tools/r1gen/r1prompt），禁手写常量；
`checks.append_only` 的判据 = `spec == default[:start] + <插入块> + default[start:]`
（即: 前段逐位相同 ∧ 尾段逐位相同 ⇒ 插入点唯一 ⇒ 只加厚）。

用法: python3 eval/rover/r630/gen_prefix_r630.py
"""
import hashlib
import io
import json
import os
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
sys.path.insert(0, os.path.join(REPO, "tools/r1gen"))
import r1prompt as rp  # noqa: E402


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha12(rel):
    with io.open(os.path.join(REPO, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:12]


def first_divergence(a, b):
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    return i


def body_append_only(base, neu):
    """只加厚（插入）不变量，**无需下标算术**：去掉末尾闭合标签后，
    新块正文必须以旧块正文**逐位为前缀**（严格更长）⇒ 旧内容一字未改、新内容只追加在闭合标签之前。"""
    tag = "</prefix>"
    assert base.endswith(tag) and neu.endswith(tag)
    bd, nd = base[:-len(tag)], neu[:-len(tag)]
    return nd.startswith(bd) and len(nd) > len(bd), bd, nd


def main():
    base = rp.PREFIX
    spec = rp.PREFIX_SPEC
    start = first_divergence(base, spec)
    ok, bd, nd = body_append_only(base, spec)
    inserted = nd[len(bd):]
    ins_lines = [ln for ln in inserted.split("\n") if ln.strip()]

    tiers = {
        "default": (base, "产品缺省 = R617 现盘块（轴关/近似拼写档）"),
        "r615": (rp.PREFIX_R615, "第一锚 = R615 冻结块（由 git show 派生）"),
        "legacy": (rp.PREFIX_LEGACY, "第二锚 = R610–R614 冻结 pin"),
        "spec": (spec, "R630 治疗档 = 缺省块正文 + 规格保真自检尾块（**只加厚**）"),
    }
    shas = [sha(t[0]) for t in tiers.values()]
    checks = {
        "body_append_only": bool(ok),
        "four_tiers_distinct": len(set(shas)) == 4,
        "spec_longer_than_default": len(spec) > len(base),
        "default_bytes_unchanged": sha(base) == rp.prefix_sha(),
        "closing_tag_preserved": spec.endswith("</prefix>") and base.endswith("</prefix>"),
        "min_chars_gate": len(spec) >= 15800,
        "inserted_block_wellformed": bool(inserted.startswith("<spec_fidelity>")
                                          and inserted.rstrip().endswith("</spec_fidelity>")),
        "inserted_block_substantive": len(ins_lines) >= 5,
    }
    rc = 0 if all(checks.values()) else 2
    out = {
        "round": "R630",
        "instrument": "tools/r1gen/r1prompt.py + tools/r1gen/gen_csharp.py",
        "source_sha12": {
            "tools/r1gen/r1prompt.py": sha12("tools/r1gen/r1prompt.py"),
            "tools/r1gen/gen_csharp.py": sha12("tools/r1gen/gen_csharp.py"),
            "src/agent/contract/StructuredPrompt.cs": sha12("src/agent/contract/StructuredPrompt.cs"),
        },
        "pin_current": {"chars": len(base), "sha256": sha(base), "role": tiers["default"][1]},
        "pin_r615_anchor": {"chars": len(rp.PREFIX_R615), "sha256": sha(rp.PREFIX_R615), "role": tiers["r615"][1]},
        "pin_legacy_anchor": {"chars": len(rp.PREFIX_LEGACY), "sha256": sha(rp.PREFIX_LEGACY), "role": tiers["legacy"][1]},
        "pin_spec_tier": {"chars": len(spec), "sha256": sha(spec), "role": tiers["spec"][1]},
        "block_analysis": {
            "first_divergence_at": start,
            "insert_at_body_end": len(base) - len("</prefix>"),
            "inserted_chars": len(inserted),
            "inserted_lines": len(ins_lines),
            "delta_chars": len(spec) - len(base),
            "identical_before_insert": starts_with_equal(base, spec, start),
        },
        "checks": checks,
        "verdict": {"rc": rc, "label": ("PASS（只加厚 ∧ 四档互异 ∧ 前段/尾段逐位保留）" if rc == 0
                                        else "FAIL（只加厚或互异性不成立 ⇒ 轴不合法）")},
        "honest_bounds": [
            "本件只证**前缀结构与轴锚**；不证任何质量/成本收益（收益面在真机臂）",
            "尾块是唯一被测自由度；到达面遥测（R1Transcript）为器具，两臂同开",
            "跨轮禁相减：R615/R617 pin 与 R630 各档并列",
            "R1Transcript 的 `prefix_pinned` 布尔字段仍按**缺省档**钉值比较 ⇒ spec 档恒 false（标签面缺陷，本轮只登记不改，见 report 遗留）",
        ],
        "written_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    }
    p = os.path.join(REPO, "eval/rover/r630/prefix-r630.json")
    json.dump(out, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"rc": rc, "checks": checks, "chars": {k: len(v[0]) for k, v in tiers.items()},
                      "insert_at": start, "inserted_chars": len(inserted)}, ensure_ascii=False))
    return rc


def starts_with_equal(a, b, n):
    return a[:n] == b[:n]


if __name__ == "__main__":
    sys.exit(main())
