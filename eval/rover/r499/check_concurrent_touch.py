#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""共享登记表并发守卫 (通用代码逻辑, 语言无关)。

用途: 本回合要写 docs/verification-registry.json, 但对侧会话可能同时在写同一文件。
纪律 (R492→R499 传承): 写回**前后**比对「非本回合的其他行」逐字节不变 —— 任何并发改动触发拒写,
避免「替对侧声明」/覆盖对侧产物 (R476 事故族)。

用法:
    tok = guard_or_die(REG, "R499")   # 写前: 取指纹, 且断言本回合旧行可安全替换
    ... 写盘 ...
    verify_or_die(REG, "R499", tok)   # 写后: 其他行必须逐字节未变
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _foreign_fingerprint(path: Path, round_id: str) -> tuple[str, int]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    foreign = [r for r in doc.get("rows", []) if r.get("owner_round") != round_id]
    blob = json.dumps(foreign, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16], len(foreign)


def guard_or_die(path, round_id: str) -> dict:
    p = Path(path)
    if not p.is_file():
        raise SystemExit(f"[致命] 登记表不存在: {p}")
    tok, n = _foreign_fingerprint(p, round_id)
    print(f"[守卫] 写前 foreign_rows={n} foreign_sha16={tok}")
    return {"path": str(p), "round": round_id, "foreign_sha16": tok, "foreign_n": n}


def verify_or_die(path, round_id: str, token: dict) -> None:
    p = Path(token.get("path", path))
    tok, n = _foreign_fingerprint(p, round_id)
    if tok != token["foreign_sha16"] or n != token["foreign_n"]:
        raise SystemExit(
            f"[致命] 并发写入检测: 非本回合行发生变化 (写前 {token['foreign_sha16']}/{token['foreign_n']} "
            f"→ 写后 {tok}/{n}) ⇒ 拒绝收口, 人工复核后再提交")
    print(f"[守卫] 写后 foreign_rows={n} foreign_sha16={tok} 未变 ⇒ OK")
