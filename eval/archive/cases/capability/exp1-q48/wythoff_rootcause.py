#!/usr/bin/env python3
"""EXP1-Q48 只读定因探针: R531 g1(58 例) 中两例稳定的 stdout 不匹配 = 何因?

零产品改动 / 零主线目录写入: 只读 snapshots + grade JSON, 输出落本作业自有命名空间。
判据(见 prereg_q48.json):
  C1 正控: 题面字面规则 + 字典序最小解出的期望, 必须逐例复现 cases-r521.json 的全部 15 条 wythoff 期望
           (复现 ⇒ 夹具与题面自洽; 否则 ⇒ 夹具缺陷候选, 本探针判"夹具"分支)
  C2 机理: 每条臂的实际输出必须被两类语义之一解释
           legal = 题面字面合法性 (只动一堆 / 两堆同取) + 字典序最小 (先 i 后 j)
           noleg = 枚举全部 (i,j) 不加合法性过滤 + 字典序最小  (= 会吐出非法着法)
           并断言 predicted_fail(noleg) == observed_fail
  C3 合法性普查 + 负控: 逐臂统计"非法着法"条数; 失败臂须 >=1, 全过臂须 ==0 (证明检查器有牙)
  C4 题面自证: 题面公开用例里是否逐字含失败例的输入/期望 (含 ⇒ 被测方零成本自检即可避免)
  C5 留痕: 任何臂的 tie-break 与题面不一致时登记为 latent (不作失败判据)
退出码: 0 = C1..C4 全过 / 2 = 判据不成立(fail-closed) / 3 = 输入缺失
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
N = 25


def build_cold(limit=N):
    """题面字面规则下的必败点集合 (backward induction, 无闭式)."""
    cold = [[False] * (limit + 1) for _ in range(limit + 1)]
    for s in range(0, 2 * limit + 1):
        for x in range(0, limit + 1):
            y = s - x
            if y < 0 or y > limit:
                continue
            if x == 0 and y == 0:
                cold[x][y] = True
                continue
            ok = True
            for i in range(1, x + 1):
                if cold[x - i][y]:
                    ok = False; break
            if ok:
                for j in range(1, y + 1):
                    if cold[x][y - j]:
                        ok = False; break
            if ok:
                for t in range(1, min(x, y) + 1):
                    if cold[x - t][y - t]:
                        ok = False; break
            cold[x][y] = ok
    return cold


COLD = build_cold()


def legal(i, j, a, b):
    if i == 0 and j == 0:
        return False
    if i > a or j > b:
        return False
    return (i == 0) or (j == 0) or (i == j)


def answer(a, b, mode):
    """mode: 'legal' (题面字面) | 'noleg' (无合法性过滤). 返回该语义下的输出串。"""
    if COLD[a][b]:
        return "LOSE"
    best = None
    for i in range(0, a + 1):
        for j in range(0, b + 1):
            if i == 0 and j == 0:
                continue
            if mode == "legal" and not legal(i, j, a, b):
                continue
            if not COLD[a - i][b - j]:
                continue
            key = (i, j)
            if best is None or key < best:
                best = key
    return "LOSE" if best is None else "WIN %d %d" % best


def load_arm(snapdir, w):
    p = ROOT / f"eval/rover/r531/snapshots/{w}/{snapdir}/g1/games/wythoff.py"
    if not p.exists():
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"w_{w}_{snapdir}", p)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def main():
    cases = json.loads((ROOT / "eval/rover/r531/cases/cases-r521.json").read_text())
    wc = [c for c in cases if c["game"] == "wythoff"]
    if len(wc) != 15:
        print(json.dumps({"rc": 3, "error": "wythoff cases != 15", "n": len(wc)}))
        return 3

    checks, detail = {}, {}

    # C1 正控
    c1 = []
    for idx, c in enumerate(wc):
        a, b = map(int, c["stdin"].split())
        got = answer(a, b, "legal")
        c1.append({"case": idx, "stdin": c["stdin"].strip(), "expected": c["expected_stdout"], "oracle": got, "ok": got == c["expected_stdout"]})
    checks["C1_oracle_reproduces_fixture_15_15"] = all(r["ok"] for r in c1)
    detail["C1"] = c1

    # C2/C3 逐臂
    arms = {}
    for w in ("w1", "w2", "w3"):
        for snapdir, tag in (("agentA0-off", "A0-off"), ("agentA1-on", "A1-on"), ("agentA2-merge", "A2-merge"), ("codex", "C-codex")):
            m = load_arm(snapdir, w)
            if m is None:
                continue
            rows, illegal, buggy_match, legal_match = [], 0, 0, 0
            for idx, c in enumerate(wc):
                a, b = map(int, c["stdin"].split())
                try:
                    got = m.solve(c["stdin"]).strip()
                except Exception as e:  # noqa
                    got = "ERR:" + repr(e)
                exp = c["expected_stdout"]
                ok = got == exp
                if got.startswith("WIN "):
                    _, si, sj = got.split()
                    i, j = int(si), int(sj)
                    if not legal(i, j, a, b):
                        illegal += 1
                        rows.append({"case": idx, "stdin": c["stdin"].strip(), "got": got, "exp": exp, "legality": "ILLEGAL(unstated move)"})
                buggy_match += (got == answer(a, b, "noleg"))
                legal_match += (got == answer(a, b, "legal"))
                if not ok and not rows:
                    rows.append({"case": idx, "stdin": c["stdin"].strip(), "got": got, "exp": exp})
            g = ROOT / f"eval/rover/r531/evidence/windows/{w}/grade-{tag}-g1.json"
            observed = []
            if g.exists():
                gd = json.loads(g.read_text())
                observed = [i for i, c in enumerate([x for x in gd["cases"] if x["game"] == "wythoff"]) if not c["ok"]]
            pred_buggy = [idx for idx, c in enumerate(wc) if answer(*map(int, c["stdin"].split()), mode="noleg") != c["expected_stdout"]]
            arms[f"{w}/{tag}"] = {
                "n_illegal_moves": illegal,
                "semantics": ("noleg" if buggy_match == 15 else "legal" if legal_match == 15 else "mixed/other"),
                "observed_fail_cases": observed,
                "predicted_fail_if_noleg": pred_buggy,
                "fail_matches_prediction": observed == pred_buggy,
                "rows": rows,
            }

    checks["C2_every_arm_explained_by_one_semantics"] = all(v["semantics"] in ("noleg", "legal") for v in arms.values())
    checks["C2_fail_set_matches_prediction"] = all(v["fail_matches_prediction"] for v in arms.values())
    failing = {k: v for k, v in arms.items() if v["observed_fail_cases"]}
    passing = {k: v for k, v in arms.items() if not v["observed_fail_cases"]}
    checks["C3_failing_arms_have_illegal_moves"] = all(v["n_illegal_moves"] >= 1 for v in failing.values()) and len(failing) > 0
    checks["C3_negative_control_passing_arms_zero_illegal"] = all(v["n_illegal_moves"] == 0 for v in passing.values()) and len(passing) > 0
    detail["arms"] = arms

    # C4 题面自证
    ts = json.loads((ROOT / "eval/rover/r531/taskset-r531.json").read_text())
    g1 = next(t for t in ts["tasks"] if t["tid"] == "g1")
    prompt = g1["prompt"]
    checks["C4_public_example_in_prompt_verbatim"] = ("21 25" in prompt and "WIN 15 15" in prompt and "25 25" in prompt)
    detail["C4"] = {"has_21_25_WIN_15_15": ("21 25" in prompt and "WIN 15 15" in prompt),
                    "has_25_25": "25 25" in prompt,
                    "prompt_sha256": g1["prompt_sha256"]}

    # C5 留痕: tie-break 与题面不一致
    latent = []
    for k, v in arms.items():
        if v["semantics"] == "legal" and v["n_illegal_moves"] == 0:
            src = (ROOT / f"eval/rover/r531/snapshots/{k.split('/')[0]}/{'agentA0-off' if k.endswith('A0-off') else 'agentA1-on' if k.endswith('A1-on') else 'agentA2-merge' if k.endswith('A2-merge') else 'codex'}/g1/games/wythoff.py").read_text(errors="replace")
            if "i + j" in src or "i+j" in src:
                latent.append({"arm": k, "note": "tie-break 自陈 i+j 最小 != 题面 字典序(先 i 后 j); 15 例不可分 ⇒ 潜在过拟合"})
    detail["C5_latent"] = latent

    ok = all(v for k, v in checks.items() if k.startswith(("C1", "C2", "C3", "C4")))
    verdict = {
        "label": "EXP1-Q48",
        "subject": "R531 g1 wythoff 两例稳定 stdout 不匹配的机理定因 (只读快照几何)",
        "root_cause": "被测侧在必胜着法枚举中未施加题面写明的着法合法性约束 (只动一堆 / 两堆同取), 从而吐出非法着法 (21 25 -> WIN 1 13 取两堆不等量; 25 25 -> WIN 2 11); 题面公开用例已逐字给出 21 25 -> WIN 15 15 ⇒ 非夹具缺陷",
        "fixture_verdict": "题面/夹具自洽 (C1 15/15) ⇒ 夹具缺陷不成立",
        "observed_fail_set": sorted({tuple(v["observed_fail_cases"]) for v in arms.values() if v["observed_fail_cases"]}),
        "checks": checks,
        "rc": 0 if ok else 2,
    }
    (OUT / "verdict_q48.json").write_text(json.dumps({"verdict": verdict, "detail": detail}, ensure_ascii=False, indent=1))
    print(json.dumps(verdict, ensure_ascii=False, indent=1))
    return verdict["rc"]


if __name__ == "__main__":
    sys.exit(main())
