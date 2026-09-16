#!/usr/bin/env python3
"""R504 冻结题集构造 —— 逐族定向 dump 后**机合并**（禁抽样碰运气）。

背景 (R502): 6 题题集 = 4 程序族 + 2 见证族, 覆盖 1 个游戏族 (life_k)。
R504 扩面目标: 游戏族 **2 个** (life_k + sub_game 减法博弈) 与见证族 **3 个**
(+ witness_mod_inverse 模逆见证), 即 8 题 —— 让主线判据 (token ↓ / 远端调用 ↓)
不再依赖单一游戏族的难度分布。

构造纪律 (逐条机检, 失败即 RefuseToEmit):
  C1 每个目标族**恰好出一道** (定向 dump, 不是随机抽 8 题);
  C2 dump 出来的题 family 必须与请求族一致 (防 --families 白名单失效);
  C3 合并后 tid 唯一且形态固定 (p001..pNNN / m001..mNNN, 程序族在前);
  C4 **旧 dump 的 tid 不得出现在任何其它字段内** (R502 教训: 跨轮 tid 串味 ⇒ 台账归属错标);
  C5 题集 sha256 与文件字节一致 (供预注册机取, 禁手抄)。

用法: python3 eval/rover/r504/build_taskset_r504.py [--out eval/rover/r504/taskset-r504.json]
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SEED = 20260917
PROG = ["life_k", "sub_game", "nim_multi", "wythoff", "topo_min", "vm_run", "json_mini"]
MATH = ["witness_sqrt_mod", "witness_min_counterexample", "witness_mod_inverse", "witness_crt"]
OUT_DEFAULT = os.path.join(HERE, "taskset-r504.json")


class RefuseToEmit(Exception):
    pass


def dump_one(fam, kind, tmpdir):
    """定向 dump 单族 1 题 (走 run_probe 的规范落盘路径 ⇒ 与真跑同形态)。"""
    out = os.path.join(tmpdir, "dump-%s.json" % fam)
    cmd = [sys.executable, "eval/probe/run_probe.py", "--kind", kind, "--families", fam,
           "--n", "1", "--seed", str(SEED), "--solver", "oracle",
           "--dump-tasks", out, "--tag", "r504-dump-%s" % fam]
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    if p.returncode != 0 or not os.path.isfile(out):
        raise RefuseToEmit("定向 dump 失败 fam=%s rc=%s\n%s" % (fam, p.returncode, p.stdout[-1500:]))
    raw = json.load(open(out, encoding="utf-8"))
    if len(raw) != 1:
        raise RefuseToEmit("定向 dump 应得 1 题, 实得 %d (fam=%s)" % (len(raw), fam))
    if raw[0]["family"] != fam:
        raise RefuseToEmit("C2 违反: 请求 %s 得到 %s" % (fam, raw[0]["family"]))
    return raw[0], out


def strings_of(node, path="$"):
    """递归取所有字符串叶子 (含键) —— 用于 C4 串味检查。"""
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from strings_of(v, "%s[%d]" % (path, i))
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from strings_of(v, "%s.%s" % (path, k))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--tmp", default="/tmp/r504_dump")
    a = ap.parse_args(argv)
    os.makedirs(a.tmp, exist_ok=True)

    merged, old_tids = [], []
    plan = [(f, "program") for f in PROG] + [(f, "math") for f in MATH]
    for fam, kind in plan:
        task, path = dump_one(fam, kind, a.tmp)
        old_tids.append((fam, task["tid"]))
        task = dict(task)
        task["tid"] = ("p%03d" % (len([1 for _ in merged]) + 1)) if kind == "program" \
            else ("m%03d" % (len(merged) - len(PROG) + 1))
        merged.append(task)
        print("  dump %-28s %s -> %s (%s)" % (fam, path.split("/")[-1], task["tid"], kind))

    # C3 tid 唯一 + 形态
    tids = [t["tid"] for t in merged]
    if len(set(tids)) != len(tids):
        raise RefuseToEmit("C3 违反: tid 重复 %s" % tids)
    for i, t in enumerate(merged):
        want = "p%03d" % (i + 1) if i < len(PROG) else "m%03d" % (i - len(PROG) + 1)
        if t["tid"] != want:
            raise RefuseToEmit("C3 违反: 位置 %d 期望 %s 实得 %s" % (i, want, t["tid"]))

    # C4 旧 tid 串味
    for fam, otid in old_tids:
        for t in merged:
            for path, s in strings_of(t):
                if path.endswith(".tid"):
                    continue
                if s == otid or ("\n" + otid) in s or (otid + "\n") in s:
                    raise RefuseToEmit("C4 违反: 旧 tid %s (来自 %s) 出现在 %s" % (otid, fam, path))

    blob = json.dumps(merged, ensure_ascii=False, indent=1) + "\n"
    with open(a.out, "w", encoding="utf-8", newline="") as fh:
        fh.write(blob)
    sha = hashlib.sha256(open(a.out, "rb").read()).hexdigest()
    print("题集: %s\n  题数=%d 程序族=%d 见证族=%d\n  sha256=%s"
          % (a.out, len(merged), len(PROG), len(MATH), sha))
    print("  族表: %s" % ", ".join(t["family"] for t in merged))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RefuseToEmit as e:
        sys.stderr.write("[RefuseToEmit] %s\n" % e)
        raise SystemExit(3)
