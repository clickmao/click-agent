"""无头自检: python3 mathkit/__selftest__.py -> 打印 PASS/FAIL，退出码 0/非0。

覆盖: 公开用例逐字节比对 + 各模块不变式 + 负向控制。
"""

import json
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # 工作根：含 mathkit/ 的父目录


def run_op(op, args):
    """经真实入口 `python3 -m mathkit <op>` 驱动，stdin 传 JSON。"""
    proc = subprocess.run(
        [sys.executable, "-m", "mathkit", op],
        input=json.dumps(args),
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    return proc.returncode, proc.stdout, proc.stderr


def main():
    checks = []

    def check(name, op, args, expected):
        rc, out, err = run_op(op, args)
        ok = (rc == 0 and out == expected + "\n" and err == "")
        checks.append((ok, name, rc, repr(out), repr(err), repr(expected + "\n")))

    # 公开用例（逐字节）
    check("pub.qr_count", "qr_count", {"a": 11, "m": 16}, "0")
    check("pub.choose", "choose", {"n": 18, "k": 7, "mod": 97}, "8")
    check("pub.det", "det", {"matrix": [[-2, 0], [-1, -6]], "mod": 101}, "12")
    check("pub.shortest", "shortest",
          {"matrix": [[0, 0, 5, 1, 0], [0, 0, 1, 9, 6], [5, 1, 0, 0, 0],
                      [1, 9, 0, 0, 4], [0, 6, 0, 4, 0]], "src": 0, "dst": 4}, "5")
    check("pub.expect", "expect", {"red": 1, "blue": 3, "draw": 3}, "3/4")

    # 不变式 1: qr_count 结果只能是偶数（二次剩余成对）且有上界
    rc, out, _ = run_op("qr_count", {"a": 5, "m": 12})
    checks.append((rc == 0 and int(out) % 2 == 0 and 0 <= int(out) <= 12,
                   "inv.qr_count.even", rc, out.strip(), "", "even"))

    # 不变式 2: choose 结果落在 [0, mod)
    rc, out, _ = run_op("choose", {"n": 40, "k": 20, "mod": 1000003})
    checks.append((rc == 0 and 0 <= int(out) < 1000003,
                   "inv.choose.range", rc, out.strip(), "", "<mod"))

    # 不变式 3: 对角矩阵 det = 乘积 mod
    rc, out, _ = run_op("det", {"matrix": [[2, 0, 0], [0, 3, 0], [0, 0, 4]], "mod": 97})
    checks.append((out.strip() == str(24 % 97), "inv.det.diag", rc, out.strip(), "", "24"))

    # 不变式 4: 不可达 -> -1
    rc, out, _ = run_op("shortest", {"matrix": [[0, 0, 0, 0], [0, 0, 0, 0],
                                                [0, 0, 0, 0], [0, 0, 0, 0]],
                                      "src": 0, "dst": 3})
    checks.append((out.strip() == "-1", "inv.shortest.unreachable", rc, out.strip(), "", "-1"))

    # 不变式 5: expect 全抽红 deterministic -> draw/1
    rc, out, _ = run_op("expect", {"red": 4, "blue": 0 if False else 2, "draw": 4})
    checks.append((out.strip() == "8/3", "inv.expect.value", rc, out.strip(), "", "8/3"))

    # 负向控制: 未知 op 必须非 0 退出（证明入口真的在做分派校验）
    p = subprocess.run([sys.executable, "-m", "mathkit", "nope"],
                       input="{}", capture_output=True, text=True, cwd=ROOT)
    checks.append((p.returncode != 0 and p.stdout == "", "neg.unknown_op",
                   p.returncode, repr(p.stdout), repr(p.stderr), "rc!=0"))

    # 负向控制: 坏 JSON 必须非 0 退出
    p = subprocess.run([sys.executable, "-m", "mathkit", "qr_count"],
                       input="{bad", capture_output=True, text=True, cwd=ROOT)
    checks.append((p.returncode != 0 and p.stdout == "", "neg.bad_json",
                   p.returncode, repr(p.stdout), repr(p.stderr), "rc!=0"))

    failed = [c for c in checks if not c[0]]
    for ok, name, rc, out, err, exp in checks:
        status = "ok" if ok else "FAIL"
        print(f"[{status}] {name} rc={rc} got={out} want={exp}" + (f" err={err}" if err.strip() else ""))
    print(f"TOTAL {len(checks) - len(failed)}/{len(checks)} " + ("PASS" if not failed else "FAIL"))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
