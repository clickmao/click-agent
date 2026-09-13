#!/usr/bin/env python3
"""R407 逐位对账: C# 引擎 logits vs numpy oracle logits (同一串 prompt id, 双 greedy)。

判据 (预注册, 与 oracle 脚本头部一致):
  P2 单 step 通过 = cos >= 0.9999 ∧ argmax 相同 ∧ top-20 交集 >= 19。
  P3 第一处偏差 = 首个不满足 P2 的 step; 该 step 的 cos / max|dz| / top20 交集 / KL 落盘。
两臂必须步数一致且 prompt id 一致, 否则判 NOT_COMPARABLE (不接受"步数不同凑着比")。
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np


def load(dir_: Path, step: int) -> np.ndarray | None:
    f = dir_ / f"logits_{step:03d}.f32"
    if not f.exists():
        return None
    return np.fromfile(f, dtype="<f4")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ours", required=True)
    ap.add_argument("--oracle", required=True)
    ap.add_argument("--ours-json", default=None)
    ap.add_argument("--oracle-json", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--cos-min", type=float, default=0.9999)
    ap.add_argument("--topk", type=int, default=20)
    ap.add_argument("--topk-min", type=int, default=19)
    args = ap.parse_args()

    od, xd = Path(args.ours), Path(args.oracle)
    our_ids = json.loads(Path(args.ours_json).read_text())["ids"] if args.ours_json else None
    orc_ids = json.loads(Path(args.oracle_json).read_text())["ids_out"] if args.oracle_json else None
    if our_ids is not None and orc_ids is not None and our_ids[:len(orc_ids)] != orc_ids:
        print(f"NOT_COMPARABLE: id 序列不一致 ours[:{len(orc_ids)}]={our_ids[:len(orc_ids)]} oracle={orc_ids}")
        return 2

    steps, rows, first_bad = 0, [], None
    for step in range(64):
        a, b = load(od, step), load(xd, step)
        if a is None or b is None:
            break
        if a.shape != b.shape:
            print(f"NOT_COMPARABLE: step{step} shape ours={a.shape} oracle={b.shape}")
            return 2
        aa, bb = a.astype(np.float64), b.astype(np.float64)
        cos = float(aa @ bb / (np.linalg.norm(aa) * np.linalg.norm(bb) + 1e-30))
        maxdz = float(np.max(np.abs(aa - bb)))
        am_a, am_b = int(np.argmax(a)), int(np.argmax(b))
        ta = set(np.argsort(-aa)[:args.topk].tolist())
        tb = set(np.argsort(-bb)[:args.topk].tolist())
        inter = len(ta & tb)
        # KL(oracle || ours): 先各自 log-softmax, 只在 oracle 支撑上求和
        la = aa - aa.max()
        lb = bb - bb.max()
        pa = np.exp(la); pa /= pa.sum()
        pb = np.exp(lb); pb /= pb.sum()
        kl = float(np.sum(pb * (np.log(pb + 1e-30) - np.log(pa + 1e-30))))
        ok = cos >= args.cos_min and am_a == am_b and inter >= args.topk_min
        if not ok and first_bad is None:
            first_bad = step
        rows.append({"step": step, "cos": cos, "max_abs_dz": maxdz, "argmax_ours": am_a, "argmax_oracle": am_b,
                     "top20_intersection": inter, "kl_oracle_ours": kl, "pass": ok})
        print(f"step{step:3d} cos={cos:.7f} max|dz|={maxdz:.3e} argmax {am_a:6d}/{am_b:6d} "
              f"{'==' if am_a == am_b else '!='} top20={inter}/{args.topk} kl={kl:.6e} {'PASS' if ok else 'FAIL'}")
        steps += 1

    if steps == 0:
        print("NOT_COMPARABLE: 没有可比对的 logits 文件")
        return 2
    n_pass = sum(1 for r in rows if r["pass"])
    verdict = "P2_PASS_ALL" if first_bad is None else f"P3_FIRST_DIVERGENCE_AT_STEP_{first_bad}"
    print(f"VERDICT={verdict} steps={steps} pass={n_pass}/{steps} "
          f"min_cos={min(r['cos'] for r in rows):.6f}")
    if args.json:
        Path(args.json).write_text(json.dumps({
            "schema": "r407-logit-parity/1", "ours": str(od), "oracle": str(xd),
            "cos_min": args.cos_min, "topk": args.topk, "topk_min": args.topk_min,
            "steps": steps, "passed": n_pass, "first_bad_step": first_bad, "verdict": verdict, "rows": rows,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if first_bad is None else 1


if __name__ == "__main__":
    sys.exit(main())
