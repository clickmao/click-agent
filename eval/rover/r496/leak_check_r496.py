#!/usr/bin/env python3
# R496 泄漏判据 (候选① 收口后版): 「回复里出现的核对码」是不是**盘上可得**的?
#
# R495 的判据是「回复里的码 ∈ 台账落盘的码」(台账直接写了真值 ⇒ 盘上通道成立 ⇒ 必错族被证伪)。
# R496 落盘面只剩单向指纹 ⇒ 判据改为:
#   1) 指纹命中: sha8(回复里的码) ∈ 本臂台账 code8 集 ⇒ 该码 == 本臂真值 ⇒ 回复是从盘上拿到的 (泄漏)
#   2) 真值落盘扫描: 本臂 wire 真值 (从 calls-*.jsonl 的挂载块抽) 在整个**链自持工作区** (rundata) 与台账/遥测
#      文件里出现 0 次; 出现即「真值落了盘」(候选① 目标 = 盘上无真值)
#   3) 全臂 LCM- 面: 链自写文件里 `LCM-` 出现 0 次 (只允许出现在 wire 捕获 calls-*/turns-*, 那是中继面的审计件)
#
# 用法: leak_check_r496.py --dir <eval/rover/r496> --arm B [--tag r496] [--mount off|on]
import argparse, hashlib, json, os, re, sys

CODE = re.compile(r"LCM-[0-9a-fA-F]{12}\b")
MOUNT_RE = re.compile(r"n=(\d+)\s+code=(LCM-[0-9a-f]{12})")
MOUNT_HEADER = "[本地决策台账-链自持]"


def sha8(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def load_jsonl(p):
    out = []
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8-sig") as f:
        for l in f:
            l = l.strip()
            if l:
                try:
                    out.append(json.loads(l))
                except Exception:
                    pass
    return out


def wire_codes(calls):
    """wire 真值面: system 角色挂载块里的 (n, code)。"""
    pairs = []
    for r in calls:
        for m in (r.get("messages") or []):
            c = m.get("content")
            if isinstance(c, str) and MOUNT_HEADER in c and m.get("role") == "system":
                for mm in MOUNT_RE.finditer(c):
                    pairs.append((int(mm.group(1)), mm.group(2)))
    return pairs


def scan_disk(root, needles):
    """扫链自持工作区 (rundata) 与台账/遥测: 返回 {needle: [相对路径…]} (只报有命中的)。"""
    hits = {n: [] for n in needles}
    if not root or not os.path.isdir(root):
        return hits
    for dp, _, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root)
            try:
                with open(p, "rb") as f:
                    blob = f.read()
            except Exception:
                continue
            try:
                txt = blob.decode("utf-8", errors="replace")
            except Exception:
                continue
            for n in needles:
                if n in txt:
                    hits[n].append(rel)
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--tag", default="r496")
    ap.add_argument("--mount", default="off", choices=["on", "off"])
    ap.add_argument("--out")
    a = ap.parse_args()
    D, arm, tag = a.dir, a.arm, a.tag

    def pick(name, ext=("jsonl", "json")):
        for e in ext:
            for cand in ("%s-%s%s.%s" % (name, arm, tag, e), "%s-%s.%s" % (name, arm, e)):
                p = os.path.join(D, cand)
                if os.path.exists(p):
                    return p
        return None

    led = load_jsonl(pick("ledger") or os.path.join(D, "ledger-%s%s.jsonl" % (arm, tag)))
    calls = load_jsonl(pick("calls") or os.path.join(D, "calls-%s%s.jsonl" % (arm, tag)))
    tp = pick("turns")
    turns = []
    if tp:
        # 夹具写的是**整份 JSON** (含 stats+turns), 不是 JSONL —— 两种都要吃 (R495 的 turns 也是这份格式)
        raw = open(tp, encoding="utf-8-sig").read()
        try:
            obj = json.loads(raw)
            turns = obj.get("turns", []) if isinstance(obj, dict) else obj
        except Exception:
            turns = load_jsonl(tp)
    fps = {r.get("code8") for r in led if r.get("code8")}
    pairs = wire_codes(calls)
    true_codes = sorted({c for _, c in pairs})
    # 夹具收口后 rundir 被 mv 成 rundata-<arm> (归档名) —— 两个都要试
    rundir = None
    for cand in ("rundata-%s%s" % (arm, tag), "rundata-%s" % arm, "run-%s%s" % (arm, tag), "run-%s" % arm):
        if os.path.isdir(os.path.join(D, cand)):
            rundir = os.path.join(D, cand)
            break

    rows = []
    for t in turns:
        rep = t.get("reply") or ""
        found = sorted(set(CODE.findall(rep)))
        hit = [c for c in found if sha8(c) in fps]      # 指纹命中 = 该码就是本臂真值
        rows.append({"turn": t.get("turn"), "reply_chars": len(rep), "codes_in_reply": found,
                     "fps_hit_true": hit, "in_wire_truth": [c for c in found if c in true_codes],
                     "true_codes_leaked": hit})
    needles = list(dict.fromkeys(true_codes + ["LCM-"]))
    disk = scan_disk(rundir, needles) if needles else {}
    # R496: **指纹级**盘上真值扫描 —— 不依赖挂载面 (mount=off 臂没有 wire 真值), 把工作区里所有
    #   LCM- 字面量逐个 sha8 与台账指纹比对 ⇒ 命中即「真值确实躺在臂可读的文件里」(键无关, 不可伪造)。
    fp_disk = {}
    if rundir:
        for dp, _, fns in os.walk(rundir):
            for fn in fns:
                p = os.path.join(dp, fn)
                try:
                    txt = open(p, "rb").read().decode("utf-8", "replace")
                except Exception:
                    continue
                h = sorted({c for c in set(CODE.findall(txt)) if sha8(c) in fps})
                if h:
                    fp_disk[os.path.relpath(p, rundir)] = h
    disk["<ledger>"] = []
    for n in needles:
        try:
            if n in open(os.path.join(D, "ledger-%s%s.jsonl" % (arm, tag)), encoding="utf-8-sig").read():
                disk["<ledger>"].append(n)
        except Exception:
            pass
    out = {"schema": "r496-leak-check/2", "arm": arm, "mount": a.mount,
           "ledger_rows": len(led), "ledger_code_fps": len(fps),
           "wire_truth_codes": len(true_codes), "turns": rows,
           "disk_truth_hits": {k: v for k, v in disk.items() if v},
           "disk_truth_fingerprint_hits": fp_disk,
           "verdict": "LEAK" if (any(r["true_codes_leaked"] for r in rows)
                                 or fp_disk
                                 or any(v for k, v in disk.items() if k not in ("<ledger>",))
                                 or disk.get("<ledger>")) else "no_leak",
           "note": "映射无关 + 单向指纹: 判据器不需要密钥/真值即可判「回复里的码是不是盘上可得的」。"
                   "disk_truth_hits 扫的是链自持工作区 (run-*/data/**) —— 那里出现真值即候选①失败。"}
    if a.out:
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:2400])
    return 0 if out["verdict"] == "no_leak" else 13


if __name__ == "__main__":
    sys.exit(main())
