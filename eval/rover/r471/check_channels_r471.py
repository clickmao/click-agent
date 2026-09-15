#!/usr/bin/env python3
# R471 证据 + 机检: 分通道聚合器读**产品实发字段** (缺字段 fail-closed)
#
# 用法: python3 eval/rover/r471/check_channels_r471.py
# 产出: eval/rover/r471/{channel-fixtures.json, asserts-r471.json, negctl-r471.json, real-feed-r471.json}
# 退出码: 0 = C1..C6 全绿; 1 = 有判据未通过 (门禁可用)
#
# 口径来源 (逐字派生, 不手写猜测):
#   src/agent.modelqueue/PromptCacheKpi.cs:117-118 Channel / :121-125 SharedPrefixHitTokens
#   / :128-132 SharedPrefixHitRate / :135-140 ChannelFields
import collections, hashlib, importlib.util, io, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(ROOT, "eval", "rover", "r471")
TEL = os.path.join(ROOT, "data", "telemetry", "host.jsonl")
SCRIPT = os.path.join(ROOT, "scripts", "kpi_cache_hit.py")
SRC_SHA = "2a9e34490b2d92e776d5a9c364daa64adc9168cbc9bc69a1787bf2438cd59a13"
CHANNELS = ("same_session", "shared_prefix", "unknown")


def load_mod(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def read_calls(path):
    """utf-8-sig 逐行 (BOM 行不得被吞 —— R470 预检已踩)."""
    rows = []
    for line in io.open(path, encoding="utf-8-sig"):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("point") == "llm_call":
            rows.append(d)
    return rows


# ── 夹具 (与产品 ChannelFields 同形: 三字段键名/取值语义逐字) ──────────────────
def fixture_rows():
    """正控夹具: 每行给出期望聚合值, 由聚合器读回 ⇒ 器具非空心。

    形态全部取自产品 Channel()/SharedPrefixHitTokens()/SharedPrefixHitRate() 的取值域:
      prompt>0 ∧ prev==0  ⇒ shared_prefix, 两字段 = hit / hit(hit+miss)
      prompt>0 ∧ prev>0   ⇒ same_session,  两字段 = -1
      prompt==0           ⇒ unknown,       两字段 = -1
    """
    fx = []
    # A 组: 会话 s1 三轮 —— 首轮 shared_prefix(命中 2048/5553), 二三轮 same_session(-1)
    fx.append({"ts": "2026-09-16T00:00:01Z", "kv": dict(
        agent_session="s1", turn=1, prompt_tokens=5553, cache_hit_tokens=2048, cache_miss_tokens=3505,
        cache_channel="shared_prefix", shared_prefix_hit_tokens=2048,
        shared_prefix_hit_rate=round(2048 / 5553, 4)), "expect": {"channel": "shared_prefix", "hit": 2048}})
    fx.append({"ts": "2026-09-16T00:00:02Z", "kv": dict(
        agent_session="s1", turn=2, prompt_tokens=6100, cache_hit_tokens=4096, cache_miss_tokens=2004,
        cache_channel="same_session", shared_prefix_hit_tokens=-1,
        shared_prefix_hit_rate=-1), "expect": {"channel": "same_session", "hit": None}})
    fx.append({"ts": "2026-09-16T00:00:03Z", "kv": dict(
        agent_session="s1", turn=3, prompt_tokens=6400, cache_hit_tokens=5120, cache_miss_tokens=1280,
        cache_channel="same_session", shared_prefix_hit_tokens=-1,
        shared_prefix_hit_rate=-1), "expect": {"channel": "same_session", "hit": None}})
    # B 组: 会话 s2 首轮 shared_prefix, 提供方未上报命中(-1) ⇒ 不得当 0
    fx.append({"ts": "2026-09-16T00:00:04Z", "kv": dict(
        agent_session="s2", turn=1, prompt_tokens=2304, cache_hit_tokens=-1, cache_miss_tokens=-1,
        cache_channel="shared_prefix", shared_prefix_hit_tokens=-1,
        shared_prefix_hit_rate=-1), "expect": {"channel": "shared_prefix", "hit": None}})
    # C 组: 无 prompt ⇒ unknown, 两字段 -1
    fx.append({"ts": "2026-09-16T00:00:05Z", "kv": dict(
        agent_session="s3", turn=1, prompt_tokens=0, cache_hit_tokens=-1, cache_miss_tokens=-1,
        cache_channel="unknown", shared_prefix_hit_tokens=-1,
        shared_prefix_hit_rate=-1), "expect": {"channel": "unknown", "hit": None}})
    return fx


def run_script(script_path, tel, out_json):
    env = dict(os.environ)
    env.pop("AGENTFRAMEWORK_PY_RUN", None)
    env.pop("AGENTFRAMEWORK_ARTIFACT_REPAIR", None)
    p = subprocess.run([sys.executable, script_path, "--file", tel, "--json", out_json],
                       capture_output=True, text=True, env=env, cwd=ROOT)
    return p.returncode, p.stdout, p.stderr


def main():
    os.makedirs(OUT, exist_ok=True)
    checks = []

    def add(cid, desc, ok, value):
        checks.append({"id": cid, "desc": desc, "ok": bool(ok), "value": value})

    raw = open(TEL, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()
    calls = read_calls(TEL)

    # ── C1 源未改 + BOM 行未被吞 ──
    add("C1", "源 sha256 == R470 记录值 ∧ llm_call 行数 == 43 (utf-8-sig 首行 BOM 不得吞)",
        sha == SRC_SHA and len(calls) == 43, {"sha256": sha, "n_calls": len(calls)})

    mod = load_mod(SCRIPT, "kpi_cache_hit_r471")
    real = mod.aggregate_channels(calls)

    # ── C2 实发面诚实: 真实流 0 行含通道字段 ⇒ 不得冒充 shared_prefix ──
    em, un, dv = real["emitted"], real["unreported"], real["derived_recompute"]
    add("C2", "实发面: emitted.rows == 0 ∧ unreported.absent_field == 43 ∧ shared_prefix 行数 == 0 (≠43)",
        em["rows"] == 0 and un["absent_field"] == 43 and em["by_channel"]["shared_prefix"] == 0,
        {"emitted_rows": em["rows"], "absent_field": un["absent_field"],
         "emitted_shared_prefix": em["by_channel"]["shared_prefix"]})

    # ── C3 两列分离且守恒: 派生列单列 == 43, 且守恒式闭合 ──
    add("C3", "派生对照列分离: derived.shared_prefix == 43 ∧ 守恒 emitted+unreported == calls ∧ 派生命中 == 59518 (R470 值)",
        dv["by_channel"]["shared_prefix"] == 43 and real["conservation"]["ok"]
        and dv["shared_prefix_hit_tokens"] == 59518,
        {"derived_shared_prefix": dv["by_channel"]["shared_prefix"],
         "derived_hit_tokens": dv["shared_prefix_hit_tokens"],
         "conservation": real["conservation"]})

    # ── C4 正控: 同形夹具 ⇒ 聚合器逐值读回 ──
    fx = fixture_rows()
    fxcalls = [{"ts": f["ts"], "kv": f["kv"]} for f in fx]
    fxres = mod.aggregate_channels(fxcalls)
    exp_by_chan = collections.Counter(f["expect"]["channel"] for f in fx)
    exp_hit = sum(f["expect"]["hit"] for f in fx if f["expect"]["hit"])
    exp_reported = sum(1 for f in fx if f["expect"]["hit"] is not None)
    exp_na = sum(1 for f in fx if f["expect"]["channel"] == "shared_prefix" and f["expect"]["hit"] is None)
    got = fxres["emitted"]
    pos_ok = (fxres["emitted"]["rows"] == len(fx)
              and got["by_channel"] == dict(exp_by_chan)
              and got["shared_prefix"]["hit_tokens"] == exp_hit
              and got["shared_prefix"]["hit_reported"] == exp_reported
              and got["shared_prefix"]["hit_na"] == exp_na
              and fxres["unreported"]["total"] == 0
              and fxres["verdict"] == "PASS")
    # 逐行 rate 语义: 夹具里 shared_prefix 且已上报的行的 rate == round(hit/(hit+miss),4)
    rate_ok = True
    for f in fx:
        if f["expect"]["channel"] == "shared_prefix" and f["expect"]["hit"] is not None:
            kv = f["kv"]
            if abs(kv["shared_prefix_hit_rate"] - round(kv["cache_hit_tokens"] / (kv["cache_hit_tokens"] + kv["cache_miss_tokens"]), 4)) > 1e-9:
                rate_ok = False
    add("C4", "正控(器具非空心): 同形夹具 emitted.rows==5 ∧ 分通道计数精确 ∧ 命中求和精确 ∧ 未上报不计入 ∧ rate 逐行同式",
        pos_ok and rate_ok,
        {"rows": fxres["emitted"]["rows"], "by_channel": got["by_channel"],
         "exp_by_channel": dict(exp_by_chan), "hit_tokens": got["shared_prefix"]["hit_tokens"],
         "exp_hit_tokens": exp_hit, "hit_na": got["shared_prefix"]["hit_na"],
         "unreported": fxres["unreported"], "verdict": fxres["verdict"], "rate_semantics_ok": rate_ok})
    json.dump({"fixtures": [{"kv": f["kv"], "expect": f["expect"]} for f in fx],
               "aggregated": fxres},
              io.open(os.path.join(OUT, "channel-fixtures.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # ── C5 负控 (必须判红 / 不得冒充) ──
    nc = {}
    # (a) same_session 行带非 -1 的 shared_prefix_* ⇒ double_count 判红
    a = [{"ts": "n1", "kv": dict(agent_session="s1", turn=2, prompt_tokens=3000, cache_hit_tokens=2000,
                                 cache_miss_tokens=1000, cache_channel="same_session",
                                 shared_prefix_hit_tokens=2000, shared_prefix_hit_rate=0.6667)}]
    ra = mod.aggregate_channels(a)
    nc["a_double_count"] = {"verdict": ra["verdict"], "violations": [v["kind"] for v in ra["violations"]],
                            "red": ra["verdict"] == "FAIL_CHANNEL_SEMANTICS"
                                   and any(v["kind"] == "double_count" for v in ra["violations"])}
    # (b) shared_prefix 行 hit=-1 ⇒ 不入求和, 计 hit_na
    b = [{"ts": "n2", "kv": dict(agent_session="s1", turn=1, prompt_tokens=2304, cache_hit_tokens=-1,
                                 cache_miss_tokens=-1, cache_channel="shared_prefix",
                                 shared_prefix_hit_tokens=-1, shared_prefix_hit_rate=-1)}]
    rb = mod.aggregate_channels(b)
    nc["b_unreported_not_zero"] = {"hit_tokens": rb["emitted"]["shared_prefix"]["hit_tokens"],
                                   "hit_na": rb["emitted"]["shared_prefix"]["hit_na"],
                                   "ok": rb["emitted"]["shared_prefix"]["hit_tokens"] == 0
                                         and rb["emitted"]["shared_prefix"]["hit_na"] == 1,
                                   "note": "hit_tokens 求和为 0 但 hit_na=1 ⇒ 「0 命中」与「未上报」可分"}
    # (c) prompt=0 ⇒ unknown ∧ 两字段 -1
    c = [{"ts": "n3", "kv": dict(agent_session="s1", turn=1, prompt_tokens=0, cache_hit_tokens=-1,
                                 cache_miss_tokens=-1, cache_channel="unknown",
                                 shared_prefix_hit_tokens=-1, shared_prefix_hit_rate=-1)}]
    rc = mod.aggregate_channels(c)
    nc["c_unknown_zero_prompt"] = {"by_channel": rc["emitted"]["by_channel"], "violations": len(rc["violations"]),
                                   "ok": rc["emitted"]["by_channel"]["unknown"] == 1 and not rc["violations"]}
    # (d) 无字段行 ⇒ unreported.absent_field, 不得 0 不得 shared_prefix
    d = [{"ts": "n4", "kv": dict(agent_session="s1", turn=1, prompt_tokens=2304, cache_hit_tokens=2048,
                                 cache_miss_tokens=256)}]
    rd = mod.aggregate_channels(d)
    nc["d_absent_field"] = {"absent_field": rd["unreported"]["absent_field"],
                            "emitted_rows": rd["emitted"]["rows"],
                            "by_channel": rd["emitted"]["by_channel"],
                            "ok": rd["unreported"]["absent_field"] == 1 and rd["emitted"]["rows"] == 0}
    # (e) 归因反写 (last>0 才算 shared_prefix) ⇒ 原判据不成立
    rev = [{"ts": "n5", "kv": dict(agent_session="s1", turn=1, prompt_tokens=5553, cache_hit_tokens=2048,
                                   cache_miss_tokens=3505, cache_channel="shared_prefix",
                                   shared_prefix_hit_tokens=2048, shared_prefix_hit_rate=0.3688)}]
    rrev = mod.aggregate_channels(rev)
    inv_ok = rrev["derived_recompute"]["by_channel"]["shared_prefix"] == 1
    nc["e_attribution_rewrite"] = {"normal": rrev["derived_recompute"]["by_channel"],
                                  "note": "反写规则下该行应为 same_session ⇒ derived 通道计数改变 ⇒ 判据有判别力",
                                  "ok": inv_ok}
    # (f) 非 shared_prefix 通道缺字段 (接线不完整) ⇒ wiring_hole 判红 (fail-closed)
    f = [{"ts": "n6", "kv": dict(agent_session="s1", turn=2, prompt_tokens=3000, cache_hit_tokens=2000,
                                 cache_miss_tokens=1000, cache_channel="same_session")}]
    rf = mod.aggregate_channels(f)
    nc["f_wiring_hole"] = {"verdict": rf["verdict"], "kinds": [v["kind"] for v in rf["violations"]],
                           "ok": rf["verdict"] == "FAIL_CHANNEL_SEMANTICS"
                                 and any(v["kind"] == "wiring_hole" for v in rf["violations"])}
    nc_ok = all(v.get("ok") or v.get("red") for v in nc.values())
    add("C5", "负控 6 例: (a)双计判红 (b)未上报不入和 (c)unknown (d)缺字段不冒充 (e)归因反写有判别力 (f)接线洞判红",
        nc_ok, {k: {kk: vv for kk, vv in v.items()} for k, v in nc.items()})
    json.dump(nc, io.open(os.path.join(OUT, "negctl-r471.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ── C6 零回归: 新脚本 legacy 键 vs HEAD 版脚本逐键相同 ──
    head = subprocess.run(["git", "show", "HEAD:scripts/kpi_cache_hit.py"], capture_output=True, text=True, cwd=ROOT)
    old_ok_run = head.returncode == 0
    reg = {"head_available": old_ok_run}
    if old_ok_run:
        with tempfile.TemporaryDirectory() as td:
            old_py = os.path.join(td, "old_kpi.py")
            open(old_py, "w", encoding="utf-8").write(head.stdout)
            new_json = os.path.join(td, "new.json")
            old_json = os.path.join(td, "old.json")
            rc_new, so_new, se_new = run_script(SCRIPT, TEL, new_json)
            rc_old, so_old, se_old = run_script(old_py, TEL, old_json)
            n = json.load(io.open(new_json, encoding="utf-8"))
            o = json.load(io.open(old_json, encoding="utf-8"))
            legacy_keys = sorted(set(o.keys()))
            diffs = [k for k in legacy_keys if json.dumps(n.get(k), sort_keys=True, ensure_ascii=False)
                     != json.dumps(o.get(k), sort_keys=True, ensure_ascii=False)]
            reg.update({"rc_new": rc_new, "rc_old": rc_old, "legacy_keys": len(legacy_keys), "diffs": diffs,
                        "new_only_keys": sorted(set(n.keys()) - set(o.keys())),
                        "old_had_channels": "channels" in o})
            # 行为面: 旧脚本在该输入上的判定必须一致
            reg["verdict_same"] = n["verdict"] == o["verdict"]
            print(so_new)
    add("C6", "零回归: 新脚本 legacy 键逐键 == HEAD 版脚本 (只增不改, 新增键仅 channels/channel_verdict)",
        bool(old_ok_run and reg.get("diffs") == [] and reg.get("verdict_same")
             and set(reg.get("new_only_keys", [])) <= {"channels", "channel_verdict"}),
        reg)

    # ── 真实流落盘 ──
    json.dump({"source": os.path.relpath(TEL, ROOT), "source_sha256": sha, "n_calls": len(calls),
               "emitted_present_rows": sum(1 for c in calls if "cache_channel" in (c.get("kv") or {})),
               "aggregated": real},
              io.open(os.path.join(OUT, "real-feed-r471.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    passed = sum(1 for c in checks if c["ok"])
    out = {"round": "R471", "prereg": "eval/rover/r471/prereg-r471.json",
           "script": "scripts/kpi_cache_hit.py",
           "script_sha256": hashlib.sha256(open(SCRIPT, "rb").read()).hexdigest(),
           "checks": checks, "passed": passed, "total": len(checks),
           "verdict": "PASS" if passed == len(checks) else "FAIL"}
    json.dump(out, io.open(os.path.join(OUT, "asserts-r471.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for c in checks:
        print(f"  [{'OK ' if c['ok'] else 'RED'}] {c['id']} {c['desc'][:78]}")
    print(f"R471 {out['verdict']} {passed}/{len(checks)}  script_sha256={out['script_sha256'][:16]}")
    return 0 if out["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
