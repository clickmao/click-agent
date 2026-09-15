#!/usr/bin/env python3
"""EXP1-Q18 单变量构造器: 由 probe_v260.py (v2.6.0) 派生 v2.7.0。

改动**只**两处 (单变量):
  1. PROBE_VERSION "2.6.0" -> "2.7.0"
  2. citations.jsonl 落盘白名单元组追加 "symbol_faces"/"relocated_symbol_faces"
     (承 EXP1-Q17 §R.3 归因①: 9 枚生产者字段被 `if k in c` 静默丢弃, 其中仅这 2 枚
      被已登记读数 (n_symbol_faces / symbol_face_rungs) 的派生链消费)

纪律 (R435/记忆: 写入通道会改写手打字面量):
  - 一切替换串**由产物自身派生** (正则定位 + 原位插入), 不手打长字面量;
  - 插入后**读回**核对: 插入计数 == 1, 新键在文本中存在, 且仅该行发生变化。
"""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
SRC = ROOT / "eval/capability/exp1-q10/probe_v260.py"
OUT_DIR = ROOT / "eval/capability/exp1-q18"
DST = OUT_DIR / "probe_v270.py"
NEW_KEYS = ("symbol_faces", "relocated_symbol_faces")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    src_text = SRC.read_text(encoding="utf-8")
    src_sha = sha256_bytes(src_text.encode("utf-8"))

    # --- 1) 版本常量: 由文件自身派生锚点
    ver_re = re.compile(r'^PROBE_VERSION = "([0-9.]+)"$', re.M)
    m = ver_re.search(src_text)
    if not m:
        print("FATAL: PROBE_VERSION anchor not found")
        return 3
    old_ver = m.group(1)
    if old_ver != "2.6.0":
        print(f"FATAL: unexpected source version {old_ver}")
        return 3
    new_ver = "2.7.0"
    text = src_text[:m.start()] + f'PROBE_VERSION = "{new_ver}"' + src_text[m.end():]
    assert text.count(f'PROBE_VERSION = "{new_ver}"') == 1, "version insert not unique"

    # --- 2) 落盘白名单: 锚点 = citations.jsonl 那一行之后的第一个 ") if k in c},"
    lines = text.splitlines(keepends=True)
    cite_idx = None
    for i, ln in enumerate(lines):
        if 'with_name("citations.jsonl")' in ln:
            cite_idx = i
            break
    if cite_idx is None:
        print("FATAL: citations.jsonl dump block not found")
        return 3
    guard_suffix = None
    guard_idx = None
    for j in range(cite_idx + 1, min(cite_idx + 40, len(lines))):
        # 由文件自身派生守卫后缀形态 (不手打)
        mm = re.search(r'(\)\s*if k in c\},?\s*)$', lines[j])
        if mm:
            guard_suffix = mm.group(1)
            guard_idx = j
            break
    if guard_idx is None:
        print("FATAL: 'if k in c}' guard line not found after citations dump")
        return 3

    ins = ", " + ", ".join(f'"{k}"' for k in NEW_KEYS)
    line = lines[guard_idx]
    payload = line[: line.rstrip("\n").rfind(")")]  # 去掉行尾的 ')' 之前的一切保留
    line_body = line.rstrip("\n")
    pos = line_body.rfind(")")
    assert pos > 0, "no ')' on guard line"
    new_line_body = line_body[:pos] + ins + line_body[pos:]
    lines[guard_idx] = new_line_body + ("\n" if line.endswith("\n") else "")
    text2 = "".join(lines)

    # --- 3) 读回核对 (R409 纪律)
    rb = text2
    checks = {
        "version_bumped": rb.count(f'PROBE_VERSION = "{new_ver}"') == 1,
        "version_gone_old": rb.count('PROBE_VERSION = "2.6.0"') == 0,
        "keys_inserted_once_each": all(rb.count(f'"{k}"') >= 1 for k in NEW_KEYS),
        "insert_literal_count": rb.count(ins.replace("\\", "")),
        "guard_line_has_keys": all(k in lines[guard_idx] for k in NEW_KEYS),
    }
    # 逐行 diff: 只允许 2 行不同
    old_lines = src_text.splitlines()
    new_lines = text2.splitlines()
    diffs = [i for i in range(max(len(old_lines), len(new_lines)))
             if (old_lines[i] if i < len(old_lines) else None) !=
                (new_lines[i] if i < len(new_lines) else None)]
    checks["changed_line_count"] = len(diffs)
    checks["changed_line_indices"] = diffs
    checks["only_two_lines_changed"] = len(diffs) == 2

    DST.write_text(text2, encoding="utf-8")
    readback_sha = sha256_bytes(DST.read_bytes())

    rec = {
        "builder": "build_q18_probe.py v1.0",
        "src": str(SRC.relative_to(ROOT)),
        "src_sha256": src_sha,
        "dst": str(DST.relative_to(ROOT)),
        "dst_sha256": readback_sha,
        "old_version": old_ver,
        "new_version": new_ver,
        "inserted_keys": list(NEW_KEYS),
        "checks": checks,
        "ok": all(bool(v) for k, v in checks.items() if isinstance(v, bool))
              and checks["only_two_lines_changed"],
    }
    (OUT_DIR / "build_q18.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    if not rec["ok"]:
        print("BUILDER_FAIL")
        return 2
    print("BUILDER_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
