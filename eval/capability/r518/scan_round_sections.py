#!/usr/bin/env python3
"""R518 器具: improvements.md 轮节覆盖与**分区内**排序机检 (只读; 带自检负控)。

口径契约 (写入前已 dump 真实形态, 见 eval/capability/r518/README-census.md):
  - 节头行形如: "## R514 · 2026-09-17 · ..." / "## v0.98.0 · R501 · ..." / "## R507 补测 · ..."
    / "## R403 — chat template 裁定：自研 Jinja 子集随 R408 退役 ..."(标题内可**提到别的轮号**)
  - ⇒ 节轮号 = 节头行内**第一个** `R\\d{3}`。v1 用「取最大」⇒ 把 R403 节读成 R408 (误报 R403 缺失
    + 误报 408 重复)。该口径已作废并留痕 (自检 A 臂覆盖此分支)。
  - 排序: 文档全程**多分区** (顶部版本段 / R4xx 段 / 历史段各有自己的序) ⇒ 全局严格递减**不是**判据
    (v1 误报 37 条违例)。判据改为**分区内**: 轮号 ∈ [zone_lo, zone_hi] 的节按**行序**必须非递增。

判据:
  C1 覆盖  : git log 提交标题中出现的 R<lo..hi> 轮号, 必须在文档有同名节 ⇒ 缺失逐条点名
  C2 分区序: [lo..hi] 段内节轮号沿行序非递增 ⇒ 违例逐条点名
  C3 信息项: 全局序违例数 / 同轮号多节 (多分区下可为合法, 不作判据)
rc: 0 全过 / 1 判据不成立 / 2 器具缺陷 (fail-closed: 文档或 git 不可读)
"""
import re
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

REPO = Path(__file__).resolve().parents[3]
DOC = REPO / "docs" / "improvements.md"
ROUND_RE = re.compile(r"R(\d{3})")
ZONE_LO, ZONE_HI = 401, 421
WINDOW_LO, WINDOW_HI = 401, 421


def rc_fail(msg: str) -> NoReturn:
    print(msg)
    print("SCAN_EXIT=2")
    sys.exit(2)


def plan_rounds(lo: int = WINDOW_LO, hi: int = WINDOW_HI) -> dict:
    """计划文档面: docs/plans/*r<NNN>*.md 文件名中的轮号。
    必要性 (R518 实测): R405/R406 的产物在 R407 的**同批提交**里 (提交标题不含 R405/R406)
    ⇒ 只扫 git 标题的语料根**看不见**这两轮 ⇒ 判据可达面 < 语料面。两源并取 + 分源报数。"""
    out = {}
    name_re = re.compile(r"[Rr](\d{3})")
    for p in sorted((REPO / "docs" / "plans").glob("*.md")):
        for m in name_re.finditer(p.name):
            n = int(m.group(1))
            if lo <= n <= hi and n not in out:
                out[n] = (p.name, "", "plan-doc")
    return out


def git_rounds(lo: int = WINDOW_LO, hi: int = WINDOW_HI) -> dict:
    try:
        out = subprocess.run(
            ["git", "log", "--pretty=%h%x09%ad%x09%s", "--date=short"],
            cwd=REPO, capture_output=True, text=True, timeout=180,
        )
        if out.returncode != 0:
            rc_fail(f"DEVICE_DEFECT git log rc={out.returncode}")
    except Exception as e:  # noqa: BLE001
        rc_fail(f"DEVICE_DEFECT git log 不可读: {e}")
    seen = {}
    for line in out.stdout.splitlines():
        parts = line.split("\t", 2)
        if len(parts) < 3:
            continue
        sha, date, subj = parts
        for m in ROUND_RE.finditer(subj):
            n = int(m.group(1))
            if lo <= n <= hi and n not in seen:
                seen[n] = (sha, date, subj[:160])
    return seen


def parse_sections(text: str) -> list:
    """节头 -> (轮号, 行号, 行文本); 轮号 = 节头行内第一个 R\\d{3}。"""
    secs = []
    for i, line in enumerate(text.splitlines(), 1):
        if not line.startswith("## "):
            continue
        m = ROUND_RE.search(line)
        if m:
            secs.append((int(m.group(1)), i, line[:110]))
    return secs


def analyse(text: str, rounds: dict) -> dict:
    secs = parse_sections(text)
    present = {}
    for r, ln, t in secs:
        present.setdefault(r, ln)

    missing = sorted(n for n in rounds if n not in present)

    zone = [(r, ln, t) for r, ln, t in secs if ZONE_LO <= r <= ZONE_HI]
    zone_violations = []
    prev = None
    for r, ln, t in zone:
        if prev is not None and r > prev[0]:
            zone_violations.append((prev[0], ln, r, t))
        prev = (r, ln)

    global_violations = []
    prev = None
    for r, ln, t in secs:
        if prev is not None and r > prev[0]:
            global_violations.append((prev[0], ln, r, t))
        prev = (r, ln)

    dup = {}
    for r, ln, t in secs:
        dup.setdefault(r, []).append(ln)
    dup = {r: l for r, l in dup.items() if len(l) > 1}
    return {
        "sections": len(secs), "missing": missing, "zone_violations": zone_violations,
        "global_violations": global_violations, "duplicates": dup, "zone_len": len(zone),
    }


def report(a: dict, rounds: dict) -> int:
    print(f"ROUNDS_IN_GIT={len(rounds)}  SECTIONS={a['sections']}  ZONE[{ZONE_LO}-{ZONE_HI}]={a['zone_len']}")
    print(f"C1 MISSING n={len(a['missing'])}: " + ", ".join(f"R{n}" for n in a["missing"]))
    for n in a["missing"]:
        sha, date, subj = rounds[n]
        print(f"  missing R{n} | {date} | {sha} | {subj}")
    print(f"C2 ZONE_ORDER_VIOLATIONS n={len(a['zone_violations'])}")
    for prev_r, ln, r, t in a["zone_violations"]:
        print(f"  line {ln}: R{r} 在 R{prev_r} 之后 (分区内应非递增) | {t}")
    print(f"C3 INFO global_violations={len(a['global_violations'])} duplicates={a['duplicates']}")
    ok = not a["missing"] and not a["zone_violations"]
    print("SCAN_EXIT=" + ("0" if ok else "1"))
    return 0 if ok else 1


def selftest() -> int:
    """负控: ① 缺节必被抓 ② 分区序违例必被抓 ③ 合规基线必绿。"""
    rounds = {401: ("deadbeef", "2026-09-14", "R401 x"), 402: ("deadbee2", "2026-09-14", "R402 y")}
    good = "## R402 — b\n\nx\n\n## R401 — a\n\ny\n"
    bad_order = "## R402 — b\n\nx\n\n## R401 — a\n\ny\n\n## R402 — dup\n\nz\n"
    missing = "## R402 — b\n\nx\n"
    cases = [
        ("baseline_pass", good, 0, 0),
        ("missing_detected", missing, 1, 0),
        ("zone_order_detected", bad_order, 0, 1),
    ]
    fails = 0
    for name, text, want_missing, want_vio in cases:
        a = analyse(text, rounds)
        ok = (len(a["missing"]) == want_missing) and (len(a["zone_violations"]) == want_vio)
        print(f"  selftest {name}: missing={len(a['missing'])} want={want_missing} "
              f"zone_vio={len(a['zone_violations'])} want={want_vio} -> {'OK' if ok else 'FAIL'}")
        fails += 0 if ok else 1
    # 报告路径冒烟: v1 自检只覆盖 analyse ⇒ report() 的键类型错误漏检, 真机首跑即崩 ⇒ 补此臂
    try:
        smoke_rc = report(analyse(good, rounds), rounds)
    except Exception as e:  # noqa: BLE001
        print(f"  selftest report_path: EXCEPTION {e!r} -> FAIL")
        fails += 1
    else:
        ok = smoke_rc == 0
        print(f"  selftest report_path: rc={smoke_rc} -> {'OK' if ok else 'FAIL'}")
        fails += 0 if ok else 1
    print(f"SELFTEST_EXIT={'0' if fails == 0 else '1'} n={len(cases) + 1} fails={fails}")
    return 0 if fails == 0 else 1


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    if not DOC.exists():
        rc_fail(f"DEVICE_DEFECT 文档不存在: {DOC}")
    raw = DOC.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    g, p = git_rounds(), plan_rounds()
    rounds = dict(p)
    rounds.update(g)  # git 面优先 (带 sha 便于点名)
    a = analyse(text, rounds)
    print(f"UNIVERSE: git={len(g)} plan_only={len(set(p) - set(g))} "
          f"plan_only_rounds={sorted(set(p) - set(g))}")
    return report(a, rounds)


if __name__ == "__main__":
    sys.exit(main())
