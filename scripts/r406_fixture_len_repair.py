#!/usr/bin/env python3
"""R406 P0-2: 归一金标夹具的**长度字段** (expected_len + len_unit="utf8_bytes")。

背景 (实测):
  - chat_golden.jsonl (deepseek): schema = name/messages/add_generation_prompt/bos_token/rendered/
    rendered_plain_env/env_options(字符串)/rendered_sha256 —— **原本没有长度字段**。
  - r1_chat_golden.jsonl: 有 expected_len, 但存的是 **Python 字符数** (10/10 行旧值==字符数)。
  - qwen25math_chat_golden.jsonl: 有 expected_len, 单位已是 UTF-8 字节数 (0 漂移)。
  ⇒ 三套 schema 不一致, 长度单位漂移。本脚本把它归一为 UTF-8 字节数 + 显式 len_unit。

判据 (运行前预注册):
  D1. 每行必须有 `rendered`; 缺失即计入 missing 并原样保留 (不猜)。
  D2. 分类计数: 旧值**不存在** → added; 旧值存在且 ≠ 新值 → drift; 旧值与 Python 字符数相等 → char_matches (漂移归因证据)。
  D3. `expected_len := len(rendered.encode('utf-8'))` —— `rendered` 的可信度由 R406 探针
      (scripts/r406_jinja_env_probe.py, jinja2 3.1.6 独立实现) 背书; 本脚本不重新渲染。
  D4. 每行补 `len_unit="utf8_bytes"` (机检: JinjaChatTemplateTests.J1 强制)。
  D5. `--apply` 前备份到 eval/rover/tokref/_backup_<name>.<ts>.jsonl (不覆盖); 缺省 dry-run 只报告。
  D6. added>0 时自动往日志追加更正说明 (防止把「新增字段」误读成「修复漂移」)。
用法: python3 scripts/r406_fixture_len_repair.py [--apply]
"""

from __future__ import annotations

import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOKREF = ROOT / "eval" / "rover" / "tokref"
LOG = ROOT / "eval" / "rover" / "r405" / "fixture-len-normalize-2026-09-14.log"

SETS: list[str] = [
    "chat_golden.jsonl",
    "r1_chat_golden.jsonl",
    "qwen25math_chat_golden.jsonl",
]


def normalize(apply: bool) -> int:
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines: list[str] = [f"# R406 夹具长度字段归一 ({'APPLY' if apply else 'DRY-RUN'}) @ {ts}"]
    total = drift_all = added_all = 0
    for golden in SETS:
        path = TOKREF / golden
        raw = path.read_text(encoding="utf-8")
        rows = [json.loads(ln) for ln in raw.splitlines() if ln.strip()]
        out: list[dict] = []
        drift = added = char_matches = missing = 0
        for row in rows:
            if "rendered" not in row:
                missing += 1
                out.append(row)
                continue
            text = row["rendered"]
            nbytes = len(text.encode("utf-8"))
            old = row.get("expected_len")
            if old is None:
                added += 1
            elif old != nbytes:
                drift += 1
            if old is not None and old == len(text):
                char_matches += 1
            row["expected_len"] = nbytes
            row["len_unit"] = "utf8_bytes"
            out.append(row)
        total += len(rows)
        drift_all += drift
        added_all += added
        report = (
            f"{golden}: 行数={len(rows)} 真漂移={drift} 新增字段={added} "
            f"旧值==字符数={char_matches} 缺rendered={missing}"
        )
        print(report)
        lines.append(report)
        if apply:
            backup = TOKREF / f"_backup_{golden}.{ts}.jsonl"
            if not backup.exists():
                backup.write_text(raw, encoding="utf-8")
            body = "\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n"
            path.write_text(body, encoding="utf-8")
            lines.append(f"  备份 -> {backup.relative_to(ROOT)}")
    summary = f"合计: 行数={total} 真漂移={drift_all} 新增字段={added_all}"
    print(summary)
    lines.append(summary)
    if added_all > 0:
        lines.append(
            "更正: 新增字段 ≠ 修复漂移。deepseek 套原 schema 无长度字段 (其校验字段是 rendered_sha256), "
            "本次仅为它补 expected_len/len_unit; 真正修单位漂移的只有 r1 套 (旧值=字符数)。"
        )
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(normalize("--apply" in sys.argv))
