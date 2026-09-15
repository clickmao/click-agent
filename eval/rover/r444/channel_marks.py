#!/usr/bin/env python3
"""R436: J/门 通道标记的**程序化派生**（禁手打 —— R435 U+200B 教训）。

来源（权威源，逐字读取，不做任何人工转录）:
  * src/agent/IndustrialAgentV2.cs      → `CorrectionJudgeSystem` 常量        = J 通道的 system 消息
  * src/agent.roles/CorrectionDetector.cs → `BuildJudgePrompt` 的字符串字面量 = J 通道的 user 消息

断言（任一失败 ⇒ 抛异常，调用方 fail-closed）:
  A1 无不可见码位（U+200B/U+200C/U+200D/U+FEFF/U+2060）—— 派生自「不可见码位集合」常量, 不手打标记本身;
  A2 BuildJudgePrompt 字面量非空且**首行含分类键 C/A/N**;
  A3 user 模板含锚点 `用户:` 与收尾行 `答案:`;
  A4 **裸片段不得出现在 user 模板内**（R435 回归闸: 尾行回声是 1/7 的根因; 片段文本由 A 的来源派生 = CorrectionJudgeSystem）;
  A5 长度/结构读数落盘（供证据引用, 供跨轮比对: 若源码形状再变, 本模块会自动反映）。

用法: python3 channel_marks.py [--json out.json]
"""
import json
import os
import re
import sys

ROOT = "/home/agentuser/AgentFramework"
CS_JUDGE = os.path.join(ROOT, "src/agent/IndustrialAgentV2.cs")
CS_DETECT = os.path.join(ROOT, "src/agent.roles/CorrectionDetector.cs")

# 不可见码位集合（源: Unicode 格式字符; 逐字符由码位构造, 避免把不可见字符写进本文件）
INVISIBLE = {chr(c) for c in (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF)}


def _decode_cs(lit: str) -> str:
    """解码 C# 字符串字面量里的转义（本仓库只用 \\n \\t \\" \\\\ \\uXXXX）。"""
    out, i = [], 0
    while i < len(lit):
        c = lit[i]
        if c != "\\":
            out.append(c)
            i += 1
            continue
        n = lit[i + 1]
        if n == "n":
            out.append("\n")
        elif n == "t":
            out.append("\t")
        elif n == "r":
            out.append("\r")
        elif n == '"':
            out.append('"')
        elif n == "\\":
            out.append("\\")
        elif n == "u":
            out.append(chr(int(lit[i + 2:i + 6], 16)))
            i += 4
        else:
            raise ValueError(f"未支持的转义 \\{n}")
        i += 2
    return "".join(out)


def _literals_of(path: str, func_name: str) -> list:
    src = open(path, encoding="utf-8").read()
    m = re.search(rf"(?:public|private|internal)\s+static\s+string\s+{func_name}\([^)]*\)\s*\{{(.*?)\n    \}}", src, re.S)
    if not m:
        raise ValueError(f"未找到 {func_name} 函数体")
    return [_decode_cs(x) for x in re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))]


def _const_of(path: str, name: str) -> str:
    src = open(path, encoding="utf-8").read()
    m = re.search(rf'const\s+string\s+{name}\s*=\s*"((?:[^"\\]|\\.)*)"', src)
    if not m:
        raise ValueError(f"未找到常量 {name}")
    return _decode_cs(m.group(1))


def _variants_of(path: str) -> dict:
    """R446: 判官 prompt 可能有多形态 (verbose/compact) —— 逐形态取字面量, 缺失即跳过。"""
    out = {}
    for name in ("BuildJudgePromptVerbose", "BuildJudgePromptCompact", "BuildJudgePrompt"):
        try:
            out[name] = [x for x in _literals_of(path, name) if x != ""]
        except ValueError:
            continue
    if not out:
        raise ValueError("未找到判官 prompt 构造点 (任一形态)")
    return out


def _common_prefix(strs) -> str:
    if not strs:
        return ""
    p = strs[0]
    for s in strs[1:]:
        while p and not s.startswith(p):
            p = p[:-1]
    return p


def derive() -> dict:
    j_system = _const_of(CS_JUDGE, "CorrectionJudgeSystem")
    vs = _variants_of(CS_DETECT)
    vname = "BuildJudgePromptVerbose" if "BuildJudgePromptVerbose" in vs else next(iter(vs))
    lits = vs[vname]
    body = "".join(lits)
    first_line = lits[0].split("\n")[0]
    tail = lits[-1]
    by_variant = {k: v[0].split("\n")[0] for k, v in vs.items()}
    mark = _common_prefix(list(by_variant.values()))
    if len(mark) < 10:
        mark = first_line

    assert not (INVISIBLE & set(j_system + body)), "A1 失败: 标记含不可见码位"
    assert len(j_system) >= 4 and j_system.endswith("。"), f"A1' 失败: system 形状异常 {j_system!r}"
    assert all(all(k in fl for k in ("C", "A", "N")) for fl in by_variant.values()), \
        f"A2 失败: 某形态首行缺分类键 {by_variant!r}"
    assert "用户:" in lits[-2] and tail.startswith("答案:"), f"A3 失败: 锚点缺失 {lits[-2]!r} / {tail!r}"
    # A4: 裸片段（= system 文本）不得出现在 user 模板中（R435 回归闸; 片段来源派生, 非手打）
    assert j_system not in body, "A4 失败: user 模板内出现裸片段（R435 回归）"

    return {
        "source_files": {"judge_const": CS_JUDGE, "prompt_fn": CS_DETECT},
        "j_system": j_system,
        "j_system_len": len(j_system),
        "j_first_line": mark,
        "j_first_line_by_variant": by_variant,
        "j_user_anchor": "用户:",
        "j_answer_tail": "答案:",
        "j_prompt_literals_n": len(lits),
        "j_prompt_static_len": len(body),   # 不含 prev/user 的静态部分长度
        "checks": {"A1_invisible_free": True, "A2_class_keys": True, "A3_anchors": True, "A4_no_bare_fragment": True},
    }


if __name__ == "__main__":
    d = derive()
    if "--json" in sys.argv:
        p = sys.argv[sys.argv.index("--json") + 1]
        json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[channel_marks] 派生完成 → {p}")
    print(f"[channel_marks] j_system={d['j_system']!r} len={d['j_system_len']}")
    print(f"[channel_marks] first_line={d['j_first_line']!r}")
    print(f"[channel_marks] 静态模板长={d['j_prompt_static_len']} 字面量={d['j_prompt_literals_n']} 断言={d['checks']}")
