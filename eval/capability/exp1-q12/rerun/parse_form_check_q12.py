#!/usr/bin/env python3
"""EXP1-Q12 形式校验解析器/判定器 —— 三态退出码。

0 = 断言通过（全绿）
2 = 断言失败（测试真红）
3 = 测量或环境失败（并发闸/build 失败/trx 缺失/解析失败/计数两源不一致/证据陈旧）

判据 C1..C7 的原文冻结在 prereg_q12.json；本文件只是它们的可执行形态。
负控：`--selftest` 用合成 trx 夹具回放（含注入缺陷必须判红）。
"""
import argparse
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "run_form_check.log")
TRX = os.path.join(HERE, "trx", "form_check_q12.trx")
PREREG = os.path.join(HERE, "prereg_q12.json")
OUTJSON = os.path.join(HERE, "form_check_q12.json")
NS = "{http://microsoft.com/schemas/VisualStudio/TeamTest/2010}"
FAMILIES = ("VerificationForm", "SkillGeneralization", "DevPlanDocRef")
MIN_TOTAL = 13  # exp1-q2 已登记基线


class MeasurementError(Exception):
    """环境/测量层失败 ⇒ 退出码 3，不得与断言失败同码。"""


def parse_trx(path):
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        raise MeasurementError(f"trx parse error: {e}")
    results = []
    for r in root.iter(NS + "UnitTestResult"):
        results.append({
            "name": r.get("testName") or "",
            "outcome": (r.get("outcome") or "").strip(),
            "start": r.get("startTime") or "",
            "duration": r.get("duration") or "",
        })
    counters = {}
    for c in root.iter(NS + "Counters"):
        counters = {
            "total": int(c.get("total") or 0),
            "executed": int(c.get("executed") or 0),
            "passed": int(c.get("passed") or 0),
            "failed": int(c.get("failed") or 0),
            "notExecuted": int(c.get("notExecuted") or 0),
            "aborted": int(c.get("aborted") or 0),
            "inconclusive": int(c.get("inconclusive") or 0),
        }
    return results, counters


def tally(results):
    t = {"total": len(results), "passed": 0, "failed": 0, "skipped": 0, "other": 0}
    for r in results:
        o = r["outcome"].lower()
        if o == "passed":
            t["passed"] += 1
        elif o == "failed":
            t["failed"] += 1
        elif o in ("notexecuted", "skipped", "notexecuted:", ""):
            t["skipped"] += 1
        else:
            # Inconclusive/TimeoutAborted 等：既非通过也非失败 ⇒ 记 other 并判不合格
            t["other"] += 1
    return t


def read_gate(log_path):
    g = {}
    if not os.path.exists(log_path):
        return g
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.match(r"^(gate_concurrent_procs|gate_MemAvailable_MB|observed_orphan_stubs|"
                         r"head_short|registry_sha256|skills_md_count|build_server_shutdown_exit|"
                         r"dotnet_test_exit)=(.*)$", line.strip())
            if m:
                g[m.group(1)] = m.group(2)
    return g


def effective_gate_threshold():
    """环境闸阈值单一权威源：prereg 修正件 > 原始 prereg（禁止在两处各写一个字面量）。"""
    amend = os.path.join(HERE, "prereg_q12_amend1.json")
    if os.path.exists(amend):
        with open(amend, "r", encoding="utf-8") as f:
            d = json.load(f)
        return int(d.get("change", {}).get("to_threshold", 2800)), os.path.basename(amend)
    return 2800, "prereg_q12.json"


def peak_memory_posthoc():
    """本类测量的实际内存占用峰值 —— 信息字段（不作红绿判据）。"""
    p = os.path.join(HERE, "mem_samples.txt")
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        vals = [int(x) for x in f.read().split() if x.strip().isdigit()]
    if not vals:
        return None
    return {"start_MB": vals[0], "min_MB": min(vals), "end_MB": vals[-1],
            "peak_drop_MB": vals[0] - min(vals), "n_samples": len(vals),
            "note": "informational; 对比 C7 档位是否留足余量"}


def evaluate(raw_rc, trx_path, prereg_mtime, trx_mtime, log_path=LOG):
    checks = {}
    detail = {}
    gate = read_gate(log_path)
    detail["gate"] = gate

    # C7 环境闸：闸门不满足 ⇒ 测量失败（退出码 3），不是断言失败
    thr, thr_src = effective_gate_threshold()
    detail["gate_mem_threshold"] = thr
    detail["gate_threshold_source"] = thr_src
    gconc = gate.get("gate_concurrent_procs")
    gmem_raw = gate.get("gate_MemAvailable_MB")
    if gconc is None or gmem_raw is None:
        raise MeasurementError("gate 读数缺失 ⇒ 无法证明起手闸曾满足（字段不全）")
    if gconc != "0":
        raise MeasurementError(f"gate_concurrent_procs={gconc} != 0（对侧并发在跑 ⇒ 读数不纯净）")
    if int(gmem_raw) < thr:
        raise MeasurementError(f"gate_MemAvailable_MB={gmem_raw} < {thr}（来源 {thr_src}）")

    has_trx = os.path.exists(trx_path)
    if not has_trx:
        raise MeasurementError("trx missing (dotnet test 未产出结果文件)")

    results, counters = parse_trx(trx_path)
    tal = tally(results)
    detail["results"] = tal
    detail["counters"] = counters
    detail["families"] = {f: sum(1 for r in results if f in r["name"]) for f in FAMILIES}

    # 两源交叉（结果列表 vs Counters）——不一致即测量失败，不做猜测
    if counters:
        if counters.get("total") != tal["total"]:
            raise MeasurementError(
                f"counters.total={counters.get('total')} != results={tal['total']}")
        if counters.get("failed") != tal["failed"]:
            raise MeasurementError(
                f"counters.failed={counters.get('failed')} != results failed={tal['failed']}")
    else:
        raise MeasurementError("trx 无 Counters 节点（第二数据源缺失 ⇒ 无法交叉）")

    # C5 新鲜度：trx 落盘时间不得早于 prereg（防复用旧证据）
    # 判定器缺陷修正 (Q12 selftest 抓出): 首版用严格 `>`，而 mtime 粒度为秒 ——
    # 同秒落盘会被误判「陈旧」(green 夹具假红)。语义是「不被复用」，故取 `>=`；
    # 边界行为由夹具 same_second_not_stale 长期钉住。
    checks["C5_freshness"] = trx_mtime >= prereg_mtime
    detail["trx_mtime"] = trx_mtime
    detail["prereg_mtime"] = prereg_mtime
    detail["trx_mtime_minus_prereg_s"] = round(trx_mtime - prereg_mtime, 3)
    if not checks["C5_freshness"]:
        raise MeasurementError(
            f"stale evidence: trx mtime {trx_mtime:.0f} < prereg {prereg_mtime:.0f}")

    # C1：显式退出码（无结果 + 非零退出码 ⇒ build/环境失败，不是断言失败）
    if raw_rc != 0 and tal["total"] == 0:
        raise MeasurementError(f"dotnet test rc={raw_rc} 且零测试结果 ⇒ 构建/环境失败")
    checks["C1_exit_zero"] = (raw_rc == 0)
    checks["C2_no_fail_no_skip"] = (tal["failed"] == 0 and tal["skipped"] == 0 and tal["other"] == 0)
    checks["C3_nondegenerate"] = (tal["total"] >= MIN_TOTAL)
    checks["C4_three_families"] = all(detail["families"][f] >= 1 for f in FAMILIES)
    checks["C6_attribution"] = bool(gate.get("head_short")) and bool(gate.get("registry_sha256"))

    failed_names = [r["name"] for r in results if r["outcome"].lower() == "failed"]
    detail["failed_names"] = failed_names
    for k, v in checks.items():
        detail.setdefault("check_detail", {})[k] = v

    verdict_all = all(checks.values())
    exit_code = 0 if verdict_all else 2
    return checks, detail, exit_code


def run():
    with open(PREREG, "r", encoding="utf-8") as f:
        prereg = json.load(f)
    raw_rc = 3
    p = os.path.join(HERE, "raw_rc.txt")
    if os.path.exists(p):
        raw_rc = int(open(p).read().strip() or 3)
    try:
        checks, detail, code = evaluate(
            raw_rc, TRX, os.path.getmtime(PREREG),
            os.path.getmtime(TRX) if os.path.exists(TRX) else 0.0)
        failure_class = "none" if code == 0 else "assertion"
    except MeasurementError as e:
        checks, detail, code = {}, {"measurement_error": str(e)}, 3
        failure_class = "measurement"
    out = {
        "owner_round": "EXP1-Q12",
        "prereg_id": prereg.get("prereg_id"),
        "raw_rc": raw_rc,
        "checks": checks,
        "detail": detail,
        "peak_memory_posthoc": peak_memory_posthoc(),
        "verdict": "PASS" if code == 0 else ("FAIL" if code == 2 else "MEASUREMENT_FAILURE"),
        "failure_class": failure_class,
        "exit_code": code,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    with open(OUTJSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"VERDICT={out['verdict']} failure_class={failure_class} exit={code}")
    print("checks=" + json.dumps(checks, ensure_ascii=False))
    if detail.get("measurement_error"):
        print("measurement_error=" + detail["measurement_error"])
    if detail.get("failed_names"):
        print("failed_names=" + json.dumps(detail["failed_names"], ensure_ascii=False))
    print(f"VERDICT_EXIT={code}")
    return code


# ---------------- 负控自检：合成 trx 夹具回放 ----------------
def _mk_trx(results, counters=None, with_counters=True):
    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;")
    body = []
    for name, outcome in results:
        body.append(f'<UnitTestResult testName="{esc(name)}" outcome="{outcome}" '
                    f'startTime="2026-09-15T03:22:00.0000000+00:00" duration="00:00:00.0100000" />')
    if counters is None:
        p = sum(1 for _, o in results if o == "Passed")
        f = sum(1 for _, o in results if o == "Failed")
        ne = len(results) - p - f
        counters = {"total": len(results), "executed": len(results), "passed": p,
                    "failed": f, "notExecuted": ne, "aborted": 0, "inconclusive": 0}
    cnt = ""
    if with_counters:
        cnt = ("<Counters total=\"{total}\" executed=\"{executed}\" passed=\"{passed}\" "
               "failed=\"{failed}\" notExecuted=\"{notExecuted}\" aborted=\"{aborted}\" "
               "inconclusive=\"{inconclusive}\" />").format(**counters)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010">'
            f'<Results>{"".join(body)}</Results><ResultSummary outcome="Completed">{cnt}</ResultSummary>'
            '</TestRun>')


def _green(n_per=5):
    r = []
    for f in FAMILIES:
        for i in range(n_per):
            r.append((f"AgentFramework.Tests.{f}.Case{i}", "Passed"))
    return r


def selftest():
    import tempfile
    tmp = tempfile.mkdtemp(prefix="q12-selftest-")
    prereg = os.path.join(tmp, "prereg.json")
    open(prereg, "w").write("{}")
    p_mtime = os.path.getmtime(prereg)
    def _mk_log(path, conc=0, mem=2916, head="b441616", sha="deadbeef"):
        with open(path, "w") as f:
            f.write(f"gate_concurrent_procs={conc}\ngate_MemAvailable_MB={mem}\n"
                    f"head_short={head}\nregistry_sha256={sha}\n")

    log = os.path.join(tmp, "log.txt")
    _mk_log(log)

    def case(name, results, raw_rc, counters=None, with_counters=True,
             fresh="later", gate=None, expect_code=None, expect_class=None):
        t = os.path.join(tmp, f"{name}.trx")
        open(t, "w").write(_mk_trx(results, counters, with_counters))
        if fresh == "later":
            os.utime(t, (p_mtime + 10, p_mtime + 10))
        elif fresh == "same":
            os.utime(t, (p_mtime, p_mtime))
        else:
            os.utime(t, (p_mtime - 100, p_mtime - 100))
        lg = log
        if gate is not None:
            lg = os.path.join(tmp, f"{name}.log")
            _mk_log(lg, **gate)
        try:
            checks, detail, code = evaluate(raw_rc, t, p_mtime, os.path.getmtime(t), lg)
            cls = "none" if code == 0 else "assertion"
        except MeasurementError as e:
            checks, detail, code, cls = {}, {"measurement_error": str(e)}, 3, "measurement"
        ok = (expect_code is None or code == expect_code) and \
             (expect_class is None or cls == expect_class)
        return {"fixture": name, "exit": code, "class": cls, "expected_exit": expect_code,
                "expected_class": expect_class, "as_expected": ok,
                "checks": checks, "err": detail.get("measurement_error")}

    fixtures = [
        # 绿：3 族各 5 条全过（15 >= 13），rc=0，新鲜
        case("green", _green(), 0, expect_code=0, expect_class="none"),
        # 真红：一条 Failed ⇒ 断言失败
        case("inject_failed", _green() + [("AgentFramework.Tests.VerificationForm.Bad", "Failed")],
             1, expect_code=2, expect_class="assertion"),
        # 跳过冒充通过 ⇒ 必须判红
        case("inject_skipped", _green() + [("AgentFramework.Tests.VerificationForm.Skip", "NotExecuted")],
             0, expect_code=2, expect_class="assertion"),
        # 缺一族（过滤器漏族）⇒ 必须判红
        case("missing_family",
             [(f"AgentFramework.Tests.{f}.C{i}", "Passed") for f in FAMILIES[:2] for i in range(7)],
             0, expect_code=2, expect_class="assertion"),
        # 非平凡：总数 < 13
        case("below_min_total", _green(3), 0, expect_code=2, expect_class="assertion"),
        # 计数两源不一致 ⇒ 测量失败（不是断言失败）
        case("counters_mismatch", _green(), 0,
             counters={"total": 99, "executed": 99, "passed": 99, "failed": 0,
                       "notExecuted": 0, "aborted": 0, "inconclusive": 0},
             expect_code=3, expect_class="measurement"),
        # 无 Counters 第二数据源 ⇒ 测量失败
        case("no_counters", _green(), 0, with_counters=False,
             expect_code=3, expect_class="measurement"),
        # 构建/环境失败：rc!=0 且零结果 ⇒ 测量失败（不得冒充断言失败）
        case("build_failure_zero_results", [], 1, expect_code=3, expect_class="measurement"),
        # 陈旧证据（复用旧 trx）⇒ 测量失败
        case("stale_evidence", _green(), 0, fresh="older",
             expect_code=3, expect_class="measurement"),
        # 边界回归：同秒落盘不算陈旧（判定器缺陷修正后的长期护栏）
        case("same_second_not_stale", _green(), 0, fresh="same",
             expect_code=0, expect_class="none"),
        # 环境闸未满足 ⇒ 测量失败（既不冒充断言失败，也不静默放行）
        case("gate_concurrent_nonzero", _green(), 0, gate={"conc": 1},
             expect_code=3, expect_class="measurement"),
        case("gate_mem_below_threshold", _green(), 0, gate={"mem": 2500},
             expect_code=3, expect_class="measurement"),
        # 归属指纹缺失 ⇒ 断言失败（C6）
        case("no_attribution", _green(), 0, gate={"head": "", "sha": ""},
             expect_code=2, expect_class="assertion"),
    ]
    n_pass = sum(1 for x in fixtures if x["as_expected"])
    out = {"n_fixtures": len(fixtures), "n_pass": n_pass,
           "exit": 0 if n_pass == len(fixtures) else 1, "fixtures": fixtures}
    with open(os.path.join(HERE, "selftest_q12.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    for x in fixtures:
        print(f"[{'OK ' if x['as_expected'] else 'BAD'}] {x['fixture']}: exit={x['exit']} "
              f"class={x['class']} (want {x['expected_exit']}/{x['expected_class']})"
              + (f" err={x['err']}" if x.get("err") else ""))
    print(f"SELFTEST {n_pass}/{len(fixtures)}  exit={out['exit']}")
    return out["exit"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if a.run:
        sys.exit(run())
    ap.print_help()
    sys.exit(3)
