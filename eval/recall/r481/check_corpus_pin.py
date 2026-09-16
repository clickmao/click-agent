#!/usr/bin/env python3
"""R481-G: 语料钉健康检查 (跨读数可比性门)。

背景 (R481-G 发现): `eval/recall/links_port_r482.py` 的读数只绑定
`corpus.files_sha16` (语料内容指纹), **不绑定 commit / 工作树状态**; 实测两次读数
files_sha16 不同 (1000893f7926c08c@08:04 files=6662 vs 737b2cca752d55bc@08:2x
files=6683) => 同一器具的读数在语料漂移后**不可直接比较**, 而现器具在漂移发生时
无任何机制报警。本器具补这一环。

判定 (fail-closed, 三态):
  rc=0  UNIFORM  全部读数同钉且字段齐全 => 读数之间可比
  rc=1  DRIFT    读数组 files_sha16 不唯一 => 跨读数『不可比』(弃权, 不判红也不判绿)
  rc=3  MISSING  缺钉字段 / 文件不可读 / 无输入 => 弃权 (不入红绿)

语言无关: 不依赖任何后缀或语言分支; 只读 json 的固定字段 + git 三元组诊断。
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
REQUIRED = ("corpus.files_sha16", "corpus.files", "instrument.rule_source_sha16")


def _get(doc, dotted):
    cur = doc
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _git(args):
    try:
        r = subprocess.run(["git", "-C", ROOT] + args, capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def main(argv):
    paths = argv[1:]
    if not paths:
        print("usage: check_corpus_pin.py <port.json> [<port.json> ...]")
        return 3

    rows = []
    for p in paths:
        if not os.path.isfile(p):
            print("MISSING_FILE %s" % p)
            return 3
        try:
            with open(p, encoding="utf-8-sig") as fh:
                doc = json.load(fh)
        except Exception as exc:  # noqa: BLE001 - 器具必须 fail-closed 且留可见失败
            print("UNREADABLE %s: %s" % (p, exc))
            return 3
        row: dict = {"file": os.path.relpath(p, ROOT).replace(os.sep, "/")}
        for key in REQUIRED:
            row[key] = _get(doc, key)
        row["by_origin"] = sorted((_get(doc, "by_origin") or {}).keys())
        rows.append(row)

    missing = [r["file"] for r in rows if r["corpus.files_sha16"] is None
               or r["instrument.rule_source_sha16"] is None]
    if missing:
        print("PIN_MISSING %s" % missing)
        return 3

    print("%-46s %-10s %-8s %-18s %s" % ("reading", "corpus", "files", "files_sha16", "rule_sha16"))
    for r in rows:
        print("%-46s %-10s %-8s %-18s %s" % (
            r["file"], "port", r["corpus.files"], r["corpus.files_sha16"], r["instrument.rule_source_sha16"]))

    corpus_pins = sorted({r["corpus.files_sha16"] for r in rows})
    rule_pins = sorted({r["instrument.rule_source_sha16"] for r in rows})
    head = _git(["rev-parse", "--short", "HEAD"])
    dirty = _git(["status", "--porcelain"])
    dirty_n = len([ln for ln in (dirty or "").splitlines() if ln.strip()])
    print("distinct_corpus_pins=%d distinct_rule_pins=%d head=%s worktree_dirty_files=%d"
          % (len(corpus_pins), len(rule_pins), head, dirty_n))

    if len(corpus_pins) > 1 or len(rule_pins) > 1:
        print("PIN_VERDICT=DRIFT  跨读数不可比: 语料/规则漂移; 本组读数只可各自作诊断, 禁作同批次对照或回归基线")
        for pin in corpus_pins:
            fs = sorted(r["file"] for r in rows if r["corpus.files_sha16"] == pin)
            print("  pin %s <- %s" % (pin, fs))
        return 1

    print("PIN_VERDICT=UNIFORM  同钉; 读数组可比 (files_sha16=%s, rule_sha16=%s, head=%s, dirty=%d)"
          % (corpus_pins[0], rule_pins[0], head, dirty_n))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
