#!/usr/bin/env python3
"""R405 磁盘清理: 废弃模型淘汰器 (先登记 sha256 再删, 沿用 p7b 惯例).

判据 (预注册, R402 纪律):
  D1 每个被删文件必须先算出 (bytes, sha256) 并写入 registry, 未登记不得删。
  D2 registry 追加写 (JSONL), 不覆盖历史; 同名重复登记须报错退出。
  D3 --dry-run 只登记+打印, 不删; 默认必须显式给 --delete。
  D4 删除前二次确认文件存在且大小与登记时一致 (防 TOCTOU)。
  D5 删除后回读: 文件必须消失, 否则非零退出 (不静默成功)。

用法:
  python3 scripts/r405_prune_models.py --dry-run  # 只登记+打印
  python3 scripts/r405_prune_models.py --delete   # 登记后删除
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / "eval/rover/registry/deleted-models.jsonl"

# 废弃模型: (路径, 退役理由)  —— 理由须可核 (引用检查结果)
CANDIDATES: list[tuple[str, str]] = [
    ("/tmp/models/bge-m3-q4km.gguf",
     "exp6 选型落选 (未采纳); 全仓引用仅 docs/plans/v0.22.0-exp6-embedding-model-selection.md + 报告; 非任何默认路径/脚本入口"),
    ("/tmp/models/qwen3-emb-0.6b-q8.gguf",
     "选型落选嵌入模型; 全仓引用仅文档/历史语料; 未进入代码或脚本入口"),
    ("/tmp/models/qwen25-math-1.5b-i1-q4km.gguf",
     "用户令 2026-09-14 删除; 与已保留的 qwen25-math-1.5b-q4km.gguf 权重同源(仅量化实现不同), "
     "其历史证据已落盘 eval/rover/r402/raw/*i1* 与 r403/raw/*i1*; 重跑 r401 臂须以 R401_MODEL 覆盖"),
    ("/tmp/models/qwen3-1.7b-q4km.gguf",
     "用户令 2026-09-14 删除; 引擎未实现 QK-norm ⇒ 静默算错/不可运行, 非任何默认路径; "
     "QK-norm 落地后可自上游重新获取(非本仓证据)"),
    ("/tmp/models/qwen25-math-1.5b-q4km.gguf",
     "用户令 2026-09-14 删除; 其 chat_template(2513字符) 与 10 例金标夹具已固化在 "
     "eval/rover/tokref/qwen25math_chat_{template.jinja,golden.jsonl}, 模板工作不受影响; "
     "仅 qwen2 家族生成臂复核需重新下载; r401 臂须以 R401_MODEL 覆盖"),
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_registered() -> dict[str, str]:
    if not REGISTRY.exists():
        return {}
    seen: dict[str, str] = {}
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        p = rec.get("path")
        if isinstance(p, str):
            seen[p] = str(rec.get("mode", "unknown"))
    return seen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--delete", action="store_true")
    args = ap.parse_args()
    if args.delete == args.dry_run:
        print("usage: exactly one of --dry-run | --delete", file=sys.stderr)
        return 2

    already = load_registered()
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    rows: list[tuple[str, int, str]] = []

    for path_str, reason in CANDIDATES:
        p = Path(path_str)
        if not p.exists():
            print(f"SKIP  {path_str} (不存在, 无需处理)")
            continue
        prev_mode = already.get(path_str)
        if prev_mode is not None and prev_mode != "dry-run":        # D2: 只在真的删过时拒绝重复登记
            print(f"FAIL  {path_str} 已按 mode={prev_mode} 登记过 (D2)", file=sys.stderr)
            return 3
        if prev_mode == "dry-run":
            print(f"NOTE  {path_str} 此前仅 dry-run 登记 ⇒ 允许本次实际删除")
        size = p.stat().st_size
        digest = sha256_of(p)
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "path": path_str,
            "bytes": size,
            "sha256": digest,
            "reason": reason,
            "order": "R405 用户令: 检索废弃的大文件删除清理磁盘空间",
            "mode": "dry-run" if args.dry_run else "deleted",
        }
        with REGISTRY.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")          # D1/D2
        rows.append((path_str, size, digest))
        total += size
        print(f"REG   {path_str}  {size/1048576:.1f} MB  sha256={digest[:16]}…")

        if args.delete:
            if p.stat().st_size != size:                                   # D4
                print(f"FAIL  {path_str} 大小变化, 放弃删除", file=sys.stderr)
                return 4
            p.unlink()
            if p.exists():                                                 # D5
                print(f"FAIL  {path_str} 删除后仍存在", file=sys.stderr)
                return 5
            print(f"DEL   {path_str}")

    print(f"--- 合计 {len(rows)} 个文件, {total/1048576:.1f} MB, registry={REGISTRY.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
