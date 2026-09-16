#!/usr/bin/env python3
"""R502 对照判分（**只读落盘，不重跑**）。

输入（全部为已落盘的机械产物）:
  --codex  外部真值 probe 摘要（codex 侧, solver=command:...codex_solver_r502.py）
  --agent  本侧 probe 摘要（AOT agenthost, solver=agent）
  --prereg eval/rover/r502/prereg_r502.json
  --adapter-log  adapter 落盘目录（side-codex-*.json / side-agent-*.json；缺 ⇒ H4 记 unreported）
输出: verdict-r502.json + 终端对照表。

rc: 0 = 绿（两侧产物齐 + H3 同输入成立）; 1 = 判据红; 3 = fail-closed（缺侧/缺预注册）
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys


def load(p):
    d = json.load(open(p, encoding="utf-8-sig"))
    return d


def side_rows(d):
    rows = {}
    for t in d.get("per_task") or []:
        rows[t.get("tid")] = {"mode": t.get("mode"), "family": t.get("family"), "kind": t.get("kind"),
                              "passed": t.get("passed"), "total": t.get("total"),
                              "reply_chars": t.get("reply_chars")}
    return rows


def _model_counts(logdir, side):
    """从 adapter 落盘取**真实模型名**（`request.upstream_request.model`）—— r502 首跑实测唯一落点。

    v2 修 (读写契约不一致): 原实现读顶层 `models` 字段（落盘里并不存在）⇒ 恒空 ⇒ H4 假红。
    """
    out = {}
    for p in glob.glob(os.path.join(logdir or "", "side-%s-*.json" % side)):
        try:
            d = json.load(open(p, encoding="utf-8-sig"))
        except Exception:
            continue
        m = (((d.get("request") or {}).get("upstream_request") or {}).get("model")) or ""
        if m:
            out[m] = out.get(m, 0) + 1
    return out


def usage_sum(logdir, side):
    tot_in = tot_out = 0
    calls = 0
    models = set()
    for p in sorted(glob.glob(os.path.join(logdir or "", "side-%s-*.json" % side))):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        u = ((d.get("response") or {}).get("usage") or {})
        tot_in += int(u.get("prompt_tokens") or u.get("input_tokens") or 0)
        tot_out += int(u.get("completion_tokens") or u.get("output_tokens") or 0)
        calls += 1
        m = ((d.get("extra") or {}).get("upstream_model") or
             ((d.get("request") or {}).get("model")))
        if m:
            models.add(str(m))
    return {"calls": calls, "in_tokens": tot_in, "out_tokens": tot_out,
            "total_tokens": tot_in + tot_out, "models": sorted(models)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--codex")
    ap.add_argument("--agent")
    ap.add_argument("--prereg", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "prereg_r502.json"))
    ap.add_argument("--adapter-log", default="/tmp/r502_env/adapter")
    ap.add_argument("--out", default="/tmp/r502_env/verdict-r502.json")
    a = ap.parse_args()

    missing = [n for n, p in (("codex", a.codex), ("agent", a.agent), ("prereg", a.prereg)) if not p or not os.path.exists(p)]
    if missing:
        print("[致命] 输入缺失: %s ⇒ fail-closed (rc=3, 不算绿)" % ", ".join(missing))
        return 3

    pre = load(a.prereg)
    cj, aj = load(a.codex), load(a.agent)
    crit = []
    rc = 0

    # H3 同输入（E2）: 两侧 taskset_sha 相等且 == 预注册值（probe 口径 _canon_sha）
    ts_exp = pre.get("probe_taskset_sha") or (pre.get("files_sha256") or {}).get("taskset")
    ts_c, ts_a = cj.get("taskset_sha"), aj.get("taskset_sha")
    h3 = bool(ts_exp) and ts_c == ts_a == ts_exp
    crit.append({"id": "H3", "name": "同输入机检", "pass": h3,
                 "measured": {"codex": ts_c, "agent": ts_a, "prereg": ts_exp,
                              "n_tasks_codex": cj.get("n_tasks"), "n_tasks_agent": aj.get("n_tasks")}})
    if not h3:
        rc = 1

    rc_rows, ra_rows = side_rows(cj), side_rows(aj)
    tids = sorted(set(rc_rows) | set(ra_rows))
    table = []
    for tid in tids:
        c, r = rc_rows.get(tid, {}), ra_rows.get(tid, {})
        table.append({"tid": tid, "kind": c.get("kind") or r.get("kind"), "family": c.get("family") or r.get("family"),
                      "codex_mode": c.get("mode"), "agent_mode": r.get("mode"),
                      "codex_passed": c.get("passed"), "codex_total": c.get("total"),
                      "agent_passed": r.get("passed"), "agent_total": r.get("total")})

    # H2 外部真值可用性（0 不折算成 0 能力, 记 unreported）
    c_ok = sum(1 for t in rc_rows.values() if t.get("mode") == "ok")
    a_ok = sum(1 for t in ra_rows.values() if t.get("mode") == "ok")
    h2_status = "pass" if c_ok >= 1 else "unreported"
    crit.append({"id": "H2", "name": "外部真值可用性", "pass": c_ok >= 1, "status": h2_status,
                 "measured": {"codex_ok": c_ok, "codex_n": len(rc_rows), "agent_ok": a_ok, "agent_n": len(ra_rows)}})

    # H4 同模型（E3）: 真值取 adapter 落盘 `request.upstream_request.model`（两侧必须同一模型）
    uc = usage_sum(a.adapter_log, "codex")
    ua = usage_sum(a.adapter_log, "agent")
    uc["model_counts"] = _model_counts(a.adapter_log, "codex")
    ua["model_counts"] = _model_counts(a.adapter_log, "agent")
    mo_c, mo_a = set(uc["model_counts"]), set(ua["model_counts"])
    same_model = bool(mo_c) and mo_c == mo_a and len(mo_c) == 1
    h4_status = "pass" if same_model else ("unreported" if not (uc["calls"] and ua["calls"]) else "fail")
    crit.append({"id": "H4", "name": "同模型机检", "pass": same_model, "status": h4_status,
                 "measured": {"codex": uc, "agent": ua,
                              "prereg_label": (pre.get("external_reference") or {}).get("upstream_model"),
                              "note": "prereg 记的是本仓侧标签; adapter 落盘是供应商侧名(deepseek-chat) —— 判据只要求两侧同一模型"}})
    if h4_status == "fail":
        rc = 1

    # H5 对照读数分列（禁总量断言）
    assert "winner" not in json.dumps({"t": table, "u": [uc, ua]}), "H5: 禁在产物里放 winner 字段"
    crit.append({"id": "H5", "name": "对照读数分列（禁总量断言）", "pass": True,
                 "measured": {"rows": len(table)}}) 

    h1 = ((pre.get("checks_prefirstrun") or {}).get("nc1_instrument")
          or (pre.get("checks_negative") or {}).get("nc1_instrument"))
    crit.append({"id": "H1", "name": "仪器判别力（首跑前负控）", "pass": bool(h1 and h1.get("pass")),
                 "status": "pass" if h1 else "not_in_prereg", "measured": h1 or {}})

    verdict = {
        "round": "R502", "rc": rc,
        "criteria": crit,
        "table": table,
        "totals": {
            "codex": {"whole_ok": c_ok, "n": len(rc_rows), "elapsed_s": cj.get("elapsed_s"),
                      "usage": uc, "per_family": cj.get("by_family")},
            "agent": {"whole_ok": a_ok, "n": len(ra_rows), "elapsed_s": aj.get("elapsed_s"),
                      "usage": ua, "per_family": aj.get("by_family")},
        },
        "note": "两侧读数分列; 静态面不同源 ⇒ 禁据 token 总量断言优劣 (H5)",
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(verdict, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    print("tid  kind    family                      codex            agent")
    for r in table:
        print("%-5s %-7s %-26s %-16s %s" % (
            r["tid"], r["kind"], r["family"],
            "%s(%s/%s)" % (r["codex_mode"], r["codex_passed"], r["codex_total"]),
            "%s(%s/%s)" % (r["agent_mode"], r["agent_passed"], r["agent_total"])))
    print("整题全对: codex %d/%d | agent %d/%d  (H2 status=%s)" % (c_ok, len(rc_rows), a_ok, len(ra_rows), h2_status))
    print("用量分列: codex calls=%d tok=%d | agent calls=%d tok=%d  (H4=%s)" % (
        uc["calls"], uc["total_tokens"], ua["calls"], ua["total_tokens"], h4_status))
    print("墙钟: codex %ss | agent %ss" % (cj.get("elapsed_s"), aj.get("elapsed_s")))
    print("H3 同输入: %s (%s)" % ("PASS" if h3 else "FAIL", (ts_c or "")[:16]))
    for c in crit:
        print("  %-3s %-28s %s" % (c["id"], c["name"], "PASS" if c["pass"] else "NOT"))
    print("verdict -> %s (rc=%d)" % (a.out, rc))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
