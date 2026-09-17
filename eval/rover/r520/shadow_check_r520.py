#!/usr/bin/env python3
"""R520 影子路径**落盘**机检 (与端口内闸独立的一条读取路径)。

判据: 工作区内不得存在「相对路径重复了工作区自身位置」的文件 —— 即 relative path 的前 k 段
(k>=2) 等于工作区根绝对路径的后 k 段, 或以根完整路径 (去前导分隔符) 开头。
R519 实证的坏形态: <ws>/eval/rover/r519/run-.../orch/ws/games/life.py。

退出码: 0 = 无影子 (绿) / 1 = 有影子 (红, 逐条打印) / 3 = 输入缺失 (fail-closed)。
"""
import argparse
import os
import sys


def shadow_kind(root, rel):
    root_abs = os.path.abspath(root)
    tail = [s for s in root_abs.replace("\\", "/").split("/") if s]
    sans = "/".join(tail)
    rel_n = rel.replace("\\", "/").lstrip("/")
    segs = [s for s in rel_n.split("/") if s]
    if len(segs) < 2:
        return None
    if sans and rel_n.startswith(sans + "/"):
        return "form-a: 以根完整路径开头"
    for k in range(min(len(segs) - 1, len(tail)), 1, -1):
        if segs[:k] == tail[len(tail) - k:]:
            return "form-b: 前 %d 段重复根尾 %s" % (k, "/".join(segs[:k]))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    a = ap.parse_args()
    if not os.path.isdir(a.root):
        print("INPUT_MISSING: %s 不是目录" % a.root)
        return 3
    bad = []
    total = 0
    for dirpath, _dirnames, filenames in os.walk(a.root):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            total += 1
            rel = os.path.relpath(full, a.root)
            kind = shadow_kind(a.root, rel)
            if kind:
                bad.append((rel, kind))
    print("扫描文件数 = %d" % total)
    for rel, kind in bad:
        print("SHADOW  %s   (%s)" % (rel, kind))
    if bad:
        print("VERDICT=RED  影子文件 %d 条" % len(bad))
        return 1
    print("VERDICT=GREEN  无影子路径")
    return 0


if __name__ == "__main__":
    sys.exit(main())
