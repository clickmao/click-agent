#!/usr/bin/env python3
"""R462-W 四档对比表生成 (只读 /tmp/r462_w/w-*.json, 器具 v2 口径)。
用法: python3 /tmp/r462_w_report.py [--md /tmp/r462_w/report.md]
"""
import argparse
import glob
import json
import os

ORDER = ["1.5b-q4", "1.5b-q8", "paw2b-q4", "3b-q4", "3b-q5"]


def load():
    out = {}
    for p in glob.glob("/tmp/r462_w/w-*.json"):
        try:
            d = json.load(open(p, encoding="utf-8"))
            out[d["tag"]] = d
        except Exception as e:
            print("SKIP", p, e)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default="/tmp/r462_w/report.md")
    a = ap.parse_args()
    arms = load()
    tags = [t for t in ORDER if t in arms] + [t for t in arms if t not in ORDER]
    lines = ["| 臂 | 权重GiB | acc | 假跳(P→S) | 漏跳(S→P) | 未判定 | S精度 | S召回 | 判定数 | gen tok | s |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for t in tags:
        d = arms[t]
        rows = d.get("rows", [])
        sz = os.path.getsize(d["model"]) / 1024 ** 3 if os.path.exists(d["model"]) else 0
        dec = sum(1 for r in rows if str(r.get("got")) in ("S", "P"))
        lines.append("| {tag} | {sz:.2f} | {acc} | {fs} | {ms} | {ud} | {sp} | {sr} | {dec}/{n} | {gen} | {el} |".format(
            tag=t, sz=sz, acc=d.get("acc"), fs=f"{d.get('false_skip_n')}/14", ms=f"{d.get('miss_skip_n')}/14",
            ud=d.get("undecided_n"), sp=d.get("skip_precision"), sr=d.get("skip_recall"),
            dec=dec, n=d.get("n"), gen=d.get("gen_truth_sum"), el=d.get("elapsed_s")))
    txt = "\n".join(lines)

    # 判据裁决: 预注册 P1 (假跳率 ≤0.10 ∧ 漏跳率 ≤0.20 ∧ 解析失败 = 0); P2/P3/P4 单列
    def p1(rec):
        return (rec.get("false_skip_rate", 1) <= 0.10) and ((rec.get("miss_skip_n") or 0) / 14 <= 0.20) \
               and (rec.get("unparsed_n", 1) == 0)
    verdicts = []
    for t in tags:
        d = arms[t]
        fs = d.get("false_skip_n") or 0
        fsr = d.get("false_skip_rate") or 0
        msr = (d.get("miss_skip_n") or 0) / 14
        dec = sum(1 for r in d.get("rows", []) if str(r.get("got")) in ("S", "P"))
        verdicts.append(f"- `{t}`: 假跳率={fsr:.3f}({fs}/14) {'≤' if fsr <= 0.10 else '>'}0.10, "
                        f"漏跳率={msr:.3f} {'≤' if msr <= 0.20 else '>'}0.20, 解析失败={d.get('unparsed_n')} "
                        f"⇒ **{'P1 达标' if p1(d) else 'P1 不达标'}** (判定覆盖 {dec}/{d.get('n')})")
    b = arms.get("1.5b-q4") or {}
    g3 = arms.get("3b-q4") or {}
    gq = arms.get("1.5b-q8") or {}
    if b and g3:
        dd = (g3.get("acc") or 0) - (b.get("acc") or 0)
        verdicts.append(f"- P2(参数档): 3b-q4 acc {g3.get('acc')} − 1.5b-q4 {b.get('acc')} = {dd:.3f} "
                        f"{'≥' if dd >= 0.15 else '<'}0.15 ⇒ **{'参数规模是瓶颈' if dd >= 0.15 else '未证'}**")
    if b and gq:
        dd = (gq.get("acc") or 0) - (b.get("acc") or 0)
        verdicts.append(f"- P3(量化档): 1.5b-q8 acc {gq.get('acc')} − 1.5b-q4 {b.get('acc')} = {dd:.3f} "
                        f"{'≥' if dd >= 0.10 else '<'}0.10 ⇒ **{'量化是瓶颈' if dd >= 0.10 else '量化非主因(且仍未达 P1)'}**")
    for t in tags:
        d = arms[t]
        n = d.get("n", 28) or 28
        per = (d.get("gen_truth_sum") or 0) / n
        wall = (d.get("elapsed_s") or 0) / n
        verdicts.append(f"- P4(成本/单次): `{t}` gen={per:.1f} tok {'≤' if per <= 256 else '>'}256, "
                        f"wall={wall:.1f}s {'≤' if wall <= 60 else '>'}60 ⇒ **{'达标' if per <= 256 and wall <= 60 else '不达标'}**")
    txt += "\n\n判据 (预注册 P1): 假跳率 ≤0.10 ∧ 漏跳率 ≤0.20 ∧ 解析失败 = 0\n" + "\n".join(verdicts)
    txt += "\n\n事后(post-hoc, 非预注册): 判定覆盖率 / S精度 / S召回 单列, 不计入裁决。"
    open(a.md, "w", encoding="utf-8").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
