#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prereg_amend.py — 预注册文件的**增补**器具（R539 转正；来源 = R536 §6.7 过程缺陷）。

背景（R536 §6.7 实测缺陷，如实登记）：
  写 `prereg-r536.json` 的 A1 增补时，脚本的「序列化器逐字节复现原文件」断言返回 False，
  但脚本**没有中止**，仍然写盘 ⇒ 该文件被整篇重排（内容不变、格式由内联改成块展开）。
  纪律本应是「断言失败即 fail-closed 退出」——本器具把该纪律做成**唯一代码路径**。

设计（三条不可协商）：
  1. **只插入，不重写**：新文件 = 原文件字节的一个**连续插入**（new = raw[:i] + ins + raw[i:]），
     任何「整篇 re-serialize」路径都不存在（re-serialize 是 R536 事故的根因）。
  2. **每条不变式失败 ⇒ 不写盘**（fail-closed）：先在内存里跑完全部断言，全部通过才
     `os.replace` 原子落地；失败时目标文件字节不变（自测里有 NC 证明这一点）。
  3. 语义保真：插入位置必须使「除 amendments 外的所有键」深度相等于原文档，且旧 amendments 顺序保留。

用法:
  python3 tools/prereg_amend.py --file eval/rover/rNNN/prereg-rNNN.json --amend amend.json [--dry-run]
  python3 tools/prereg_amend.py --file <prereg.json> --amend-json '{"id":"A2",...}' --dry-run
  python3 tools/prereg_amend.py --self-test          # 正向 + 4 个负控（不碰仓内文件）

退出码: 0 = 已写入(或 dry-run 通过) / 1 = 断言失败（未写盘） / 2 = 用法或输入错误 / 3 = 自测有不通过项
"""
import argparse
import copy
import hashlib
import io
import json
import os
import sys
import tempfile


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _find_span(text, key):
    """在 JSON 文本里定位 `"key": <value>` 的 value 区间（尊重字符串/转义）。返回 (start, end) 或 None。"""
    needle = '"%s"' % key
    pos = 0
    n = len(text)
    while True:
        i = text.find(needle, pos)
        if i < 0:
            return None
        # 必须是**键**（前面除空白/逗号/花括号外无他），且其后紧跟冒号
        j = i + len(needle)
        k = j
        while k < n and text[k] in " \t\r\n":
            k += 1
        if k >= n or text[k] != ":":
            pos = j
            continue
        # 键的边界: 前一非空白字符须是 { 或 ,
        p = i - 1
        while p >= 0 and text[p] in " \t\r\n":
            p -= 1
        if p >= 0 and text[p] not in "{,":
            pos = j
            continue
        v = k + 1
        while v < n and text[v] in " \t\r\n":
            v += 1
        if v >= n:
            return None
        return _value_span(text, v)


def _value_span(text, start):
    """从 value 起始字符开始，返回 (start, end)：end 为 value 之后首个非空白字符位置（不含其后的逗号）。"""
    ch = text[start]
    if ch in '[{':
        depth = 0
        i = start
        in_str = False
        esc = False
        while i < len(text):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == '\\':
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c in '[{':
                    depth += 1
                elif c in ']}':
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
            i += 1
        return (start, i)
    if ch == '"':
        i = start + 1
        esc = False
        while i < len(text):
            c = text[i]
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                i += 1
                break
            i += 1
        return (start, i)
    i = start
    while i < len(text) and text[i] not in ',]} \t\r\n':
        i += 1
    return (start, i)


def _root_close(text):
    """根对象的 `}` 位置（文本级）。"""
    start = text.index('{')
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("根对象未闭合")


def plan_amendment(raw_bytes, amendment):
    """只算不动：返回 (new_bytes, info) 或抛 AmendmentError。"""
    try:
        raw = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        raise AmendmentError("非 UTF-8 字节: %s" % e)
    try:
        doc = json.loads(raw)
    except ValueError as e:
        raise AmendmentError("原文件不是合法 JSON: %s" % e)
    if not isinstance(doc, dict):
        raise AmendmentError("根不是对象")
    old = doc.get("amendments")
    if old is not None and not isinstance(old, list):
        raise AmendmentError("amendments 不是数组")
    old = old or []
    if any(isinstance(a, dict) and a.get("id") == amendment.get("id") for a in old):
        raise AmendmentError("amendments 里已有同 id 增补: %s" % amendment.get("id"))

    piece = json.dumps(amendment, ensure_ascii=False, indent=2).replace("\n", "\n  ")
    span = _find_span(raw, "amendments")
    if span is not None:
        a_start, a_end = span
        inner = raw[a_start + 1:a_end - 1]
        if inner.strip() == "":
            ins = piece if inner == "" else "\n  " + piece + "\n"
            at = a_start + 1
        else:
            # 插到数组末尾（就地追加，保留原有元素字节不动）
            at = a_end - 1
            ins = "" if raw[at - 1] == "[" else ","
            ins += "\n  " + piece + "\n"
    else:
        at = _root_close(raw)
        # 根对象闭合 `}` 之前插入新键（保留其余字节）
        tail = raw[:at]
        sep = "" if tail.rstrip().endswith("{") else ","
        ins = sep + "\n  \"amendments\": [\n  " + piece + "\n  ]\n"
    new = (raw[:at] + ins + raw[at:]).encode("utf-8")
    b_at = len(raw[:at].encode("utf-8"))
    b_ins = len(ins.encode("utf-8"))

    if new[:b_at] != raw_bytes[:b_at]:
        raise AmendmentError("前缀字节不守恒")
    if new[b_at + b_ins:] != raw_bytes[b_at:]:
        raise AmendmentError("后缀字节不守恒")

    doc2 = json.loads(new.decode("utf-8"))
    if doc2.get("amendments") != old + [amendment]:
        raise AmendmentError("amendments 语义不等于 旧+新（插入点错了）")
    rest_old = {k: v for k, v in doc.items() if k != "amendments"}
    rest_new = {k: v for k, v in doc2.items() if k != "amendments"}
    if rest_old != rest_new:
        raise AmendmentError("除 amendments 外的键语义被改动")
    if not new.decode("utf-8").endswith("\n"):
        raise AmendmentError("新文件未以 LF 收尾（规范形）")
    info = {"insert_at": at, "insert_bytes": len(ins.encode("utf-8")),
            "raw_bytes": len(raw_bytes), "new_bytes": len(new),
            "raw_sha256_12": _sha(raw_bytes)[:12], "new_sha256_12": _sha(new)[:12],
            "prefix_conserved": True, "suffix_conserved": True,
            "amendment_id": amendment.get("id"), "created_amendments_key": span is None}
    return new, info


class AmendmentError(Exception):
    pass


def do_amend(path, amendment, dry_run=False):
    with io.open(path, "rb") as f:
        raw = f.read()
    try:
        new, info = plan_amendment(raw, amendment)
    except AmendmentError as e:
        print("AMEND_REFUSED %s" % e)
        with io.open(path, "rb") as f:
            after = f.read()
        print("WRITE=0 file_unchanged=%s sha=%s" % (after == raw, _sha(after)[:12]))
        return 1
    print("AMEND_PLAN " + json.dumps(info, ensure_ascii=False, sort_keys=True))
    if dry_run:
        print("DRY_RUN=1 WRITE=0")
        return 0
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".prereg_amend.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(new)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)          # 原子; 断言全过后才走到这里
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    with io.open(path, "rb") as f:
        back = f.read()
    if back != new:
        print("AMEND_FAIL 落地字节与计划不符")
        return 1
    print("AMEND_OK wrote=%d bytes sha12=%s" % (len(back), _sha(back)[:12]))
    return 0


def _write(p, s):
    with io.open(p, "wb") as f:
        f.write(s.encode("utf-8"))


def self_test():
    ok = True
    tmpdir = tempfile.mkdtemp(prefix="prereg_amend_selftest_")

    # ---- PC: 单行内联空数组 ⇒ 只插入、其余字节不动
    pc = os.path.join(tmpdir, "prereg-pc.json")
    original = ('{\n "round": "r539", "amendments": [], "note": "原文件格式须被保留",\n'
                ' "arms": ["A1-on", "R1nr"]\n}\n')
    _write(pc, original)
    h0 = _sha(io.open(pc, "rb").read())
    rc = do_amend(pc, {"id": "A1", "kind": "arm_amendment", "reason": "增补"})
    raw1 = io.open(pc, "rb").read().decode("utf-8")
    d1 = json.loads(raw1)
    checks = [
        ("PC-rc0", rc == 0),
        ("PC-旧键保留", d1["round"] == "r539" and d1["arms"] == ["A1-on", "R1nr"] and d1["note"] == "原文件格式须被保留"),
        ("PC-amendments", [a["id"] for a in d1["amendments"]] == ["A1"]),
        ("PC-尾LF", raw1.endswith("\n")),
        ("PC-行守恒", raw1.count("\n") == original.count("\n") + json.dumps({"id": "A1", "kind": "arm_amendment", "reason": "增补"}, ensure_ascii=False, indent=2).count("\n")),
        ("PC-旧行保留", ' "round": "r539", "amendments": [' in raw1 and ' "arms": ["A1-on", "R1nr"]' in raw1),
    ]
    for name, good in checks:
        print("SELFTEST %-16s %s" % (name, "PASS" if good else "FAIL"))
        ok = ok and good

    # ---- NC1: 非 JSON（尾逗号）⇒ 拒写且文件字节不变（**R536 事故的负控**）
    nc1 = os.path.join(tmpdir, "prereg-nc1.json")
    _write(nc1, '{"round": "r539", "amendments": [],}\n')
    h1 = _sha(io.open(nc1, "rb").read())
    rc1 = do_amend(nc1, {"id": "A1"})
    h1b = _sha(io.open(nc1, "rb").read())
    good = (rc1 != 0) and (h1 == h1b)
    print("SELFTEST %-16s %s" % ("NC1-非法JSON拒写", "PASS" if good else "FAIL"))
    ok = ok and good

    # ---- NC2: 同 id 重复增补 ⇒ 拒
    nc2 = os.path.join(tmpdir, "prereg-nc2.json")
    _write(nc2, '{"round": "r539", "amendments": [{"id": "A1"}], "x": 1}\n')
    h2 = _sha(io.open(nc2, "rb").read())
    rc2 = do_amend(nc2, {"id": "A1"})
    good = (rc2 != 0) and (h2 == _sha(io.open(nc2, "rb").read()))
    print("SELFTEST %-16s %s" % ("NC2-重复id拒", "PASS" if good else "FAIL"))
    ok = ok and good

    # ---- NC3: amendments 不是数组 ⇒ 拒（不得"顺手"改写）
    nc3 = os.path.join(tmpdir, "prereg-nc3.json")
    _write(nc3, '{"round": "r539", "amendments": {"a": 1}}\n')
    h3 = _sha(io.open(nc3, "rb").read())
    rc3 = do_amend(nc3, {"id": "A1"})
    good = (rc3 != 0) and (h3 == _sha(io.open(nc3, "rb").read()))
    print("SELFTEST %-16s %s" % ("NC3-类型错拒写", "PASS" if good else "FAIL"))
    ok = ok and good

    # ---- NC4: 非 UTF-8 字节 ⇒ 拒写且不变
    nc4 = os.path.join(tmpdir, "prereg-nc4.json")
    with io.open(nc4, "wb") as f:
        f.write(b'{"round": "r539", "amendments": [], "note": "\xff\xfe"}\n')
    h4 = _sha(io.open(nc4, "rb").read())
    rc4 = do_amend(nc4, {"id": "A1"})
    good = (rc4 != 0) and (h4 == _sha(io.open(nc4, "rb").read()))
    print("SELFTEST %-16s %s" % ("NC4-非UTF8拒写", "PASS" if good else "FAIL"))
    ok = ok and good

    # ---- PC2: 无 amendments 键 ⇒ 新键插入（其余字节保持不变）
    pc2 = os.path.join(tmpdir, "prereg-pc2.json")
    _write(pc2, '{\n "round": "r539",\n "arms": ["A"]\n}\n')
    rc5 = do_amend(pc2, {"id": "Z9", "note": "新键"})
    d5 = json.loads(io.open(pc2, "rb").read().decode("utf-8"))
    good = (rc5 == 0) and d5.get("amendments") == [{"id": "Z9", "note": "新键"}] and d5["arms"] == ["A"]
    print("SELFTEST %-16s %s" % ("PC2-新键", "PASS" if good else "FAIL"))
    ok = ok and good

    # ---- PC3: 已有元素 ⇒ 追加保序
    pc3 = os.path.join(tmpdir, "prereg-pc3.json")
    _write(pc3, '{\n "amendments": [\n  {\n   "id": "A0"\n  }\n ]\n}\n')
    rc6 = do_amend(pc3, {"id": "A1", "note": "追加"})
    d6 = json.loads(io.open(pc3, "rb").read().decode("utf-8"))
    good = (rc6 == 0) and [a["id"] for a in d6["amendments"]] == ["A0", "A1"]
    print("SELFTEST %-16s %s" % ("PC3-追加保序", "PASS" if good else "FAIL"))
    ok = ok and good

    print("SELFTEST_RESULT %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--amend")
    ap.add_argument("--amend-json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.file:
        print("用法: --file <prereg.json> --amend <amend.json> [--dry-run] | --self-test")
        return 2
    if a.amend:
        with io.open(a.amend, encoding="utf-8") as f:
            am = json.load(f)
    elif a.amend_json:
        am = json.loads(a.amend_json)
    else:
        print("缺 --amend / --amend-json")
        return 2
    if not isinstance(am, dict):
        print("增补必须是 JSON 对象")
        return 2
    return do_amend(a.file, am, a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
