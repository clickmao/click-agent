#!/usr/bin/env python3
"""R406 P0: 用「存档模板 + 金标夹具」反解 jinja2 渲染 env (判据预注册)。

判据 (预注册, 运行前写死):
  D1. 对每个模板, 枚举 (trim_blocks, lstrip_blocks, keep_trailing_newline) 共 8 种组合,
      渲染全部金标用例, 报「逐字节相等」条数; **只有全等于用例数的组合才算确定解**。
  D2. 若存在多个全等组合 ⇒ 判定为「env 不可分辨」, 不得任选其一, 必须记录歧义集合并终止。
  D3. 输出的确定解将作为 C# 解释器的默认 env (写入 JinjaTemplate.DefaultOptions) —— 不许反过来改夹具去迁就实现。
  D4. 金标 missing/error 用例不计入分母, 但必须打印其条数 (不得静默丢弃)。

用法: python3 scripts/r406_jinja_env_probe.py
"""
from __future__ import annotations

import itertools
import json
import pathlib
import sys

import jinja2

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOKREF = ROOT / "eval" / "rover" / "tokref"

BOS = "<｜begin▁of▁sentence｜>"

# (标签, 模板文件, 夹具文件, 是否传 bos_token)
CASES = [
    ("deepseek", "chat_template.jinja", "chat_golden.jsonl", True),
    ("r1-distill", "r1_chat_template.jinja", "r1_chat_golden.jsonl", True),
    ("qwen25-math", "qwen25math_chat_template.jinja", "qwen25math_chat_golden.jsonl", True),
]


def load_rows(path: pathlib.Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def render_one(tpl_text: str, row: dict, bos: bool, flags: tuple[bool, bool, bool]) -> str:
    trim_blocks, lstrip_blocks, keep_trailing_newline = flags
    env = jinja2.Environment(
        trim_blocks=trim_blocks,
        lstrip_blocks=lstrip_blocks,
        keep_trailing_newline=keep_trailing_newline,
        # HF transformers 同款: 未定义变量宽松 (message.tool_calls 等)
        undefined=jinja2.Undefined,
    )
    tpl = env.from_string(tpl_text)
    ctx = {
        "messages": row["messages"],
        "add_generation_prompt": row["add_generation_prompt"],
    }
    if bos:
        ctx["bos_token"] = BOS
    return tpl.render(**ctx)


def main() -> int:
    combos: list[tuple[bool, bool, bool]] = list(itertools.product([False, True], repeat=3))  # type: ignore[assignment]
    out: dict[str, dict] = {}
    for name, tpl_file, fix_file, bos in CASES:
        tpl_text = (TOKREF / tpl_file).read_text(encoding="utf-8")
        rows = load_rows(TOKREF / fix_file)
        usable = [r for r in rows if r.get("rendered") is not None and not r.get("error")]
        skipped = len(rows) - len(usable)
        print(f"\n=== {name}: 模板 {len(tpl_text)} 字符 / 夹具 {len(rows)} 条 (可用 {len(usable)}, 跳过 {skipped}) ===")
        winners = []
        for flags in combos:
            ok = 0
            for r in usable:
                try:
                    got = render_one(tpl_text, r, bos, flags)
                except Exception as exc:  # noqa: BLE001 - 探针需报全部失败面
                    got = f"<EXC {type(exc).__name__}: {exc}>"
                if got == r["rendered"]:
                    ok += 1
            tb, lb, ktn = flags
            mark = "  <== 全等" if ok == len(usable) else ""
            print(f"  trim_blocks={int(tb)} lstrip_blocks={int(lb)} keep_trailing_newline={int(ktn)}  {ok}/{len(usable)}{mark}")
            if ok == len(usable):
                winners.append(flags)
        out[name] = {"usable": len(usable), "skipped": skipped, "winners": [list(w) for w in winners]}

    print("\n=== 判定 ===")
    rc = 0
    for name, info in out.items():
        w = info["winners"]
        if len(w) == 1:
            tb, lb, ktn = w[0]
            print(f"{name}: 确定解 trim_blocks={int(tb)} lstrip_blocks={int(lb)} keep_trailing_newline={int(ktn)}  ({info['usable']}/{info['usable']})")
        elif not w:
            print(f"{name}: FAIL 无任何 env 组合可全等 ⇒ 夹具/模板/上下文不匹配, 必须查因")
            rc = 2
        else:
            print(f"{name}: AMBIGUOUS {w} ⇒ env 不可分辨 (D2), 不得任选")
            rc = 3
    return rc


if __name__ == "__main__":
    sys.exit(main())
