#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R449 · 真实流量门判探针 (外部效度通道 A').

预注册: eval/rover/r449/prereg-probe.json (先落盘后读数).
语料  : eval/rover/r449/real-corpus.jsonl (state.db 真实用户轮)
器具  : TurnGateJudge.BuildPrompt 程序化重现 (r443 模块; 已与遥测 sha16 逐位互证)
唯一变量: 语料 (合成网格 -> 真实流量). 解码档/服务端档 = R447 J0 同源.
判官输出字母解析 = TurnGateJudge.Parse 逐字重现 (ThinkOpen/Close + 字母正则 + 词组表 全部源码派生).
只读; 输出 probe-r449-real.jsonl (逐调用) + probe-r449-real.json (汇总).
"""
import collections
import hashlib
import json
import os
import pathlib
import random
import re
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
R449 = ROOT / "eval/rover/r449"
SRC = ROOT / "src/agent.modelqueue/LocalGenerationPort.cs"
MODEL = "/tmp/models/r1-distill-qwen-1.5b-q4km.gguf"
BIN = os.environ.get("AGENTFRAMEWORK_LLAMA_BIN",
                     "/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server")
PORT = int(os.environ.get("R449_PORT", "47982"))
BASE = f"http://127.0.0.1:{PORT}"
SRV_ARGS_TAIL = ["-c", "4608", "-t", "1", "-np", "1", "--cache-type-k", "f32",
                 "--cache-type-v", "f32", "--flash-attn", "off", "--jinja"]
OUTJ = R449 / "probe-r449-real.jsonl"
OUTD = R449 / "probe-r449-real.json"
SRVLOG = R449 / "probe-r449-server.log"
CORPUS = R449 / "real-corpus.jsonl"
GRID = ROOT / "eval/rover/r441/turns-BRJ-M20.jsonl"
ALLOC = {"D": 40, "S": 24, "O": 8}
LEN_FILTER = 1024

sys.path.insert(0, str(ROOT / "eval/rover/r443"))
sys.path.insert(0, str(ROOT / "eval/rover/r431"))
from reconstruct_gate_prompt import csharp_unescape, derive_template, build_prompt, render_growth, sha16  # noqa: E402
from precheck_rbin import load as rbin_load  # noqa: E402
import filter_and_validate as fav  # noqa: E402

PROC = None


def fail(msg):
    print(f"[fail-closed] {msg}")
    sys.exit(2)


# ---------------- 源码派生 (禁手打) ----------------
def src_text():
    return SRC.read_text(encoding="utf-8")


def const(name):
    m = re.search(name + r"\s*=\s*((?:\"[^\"]*\")|(?:'[^']*'))", src_text())
    if not m:
        fail(f"源码未找到常量 {name}")
    return csharp_unescape(m.group(1)[1:-1])


def letter_re():
    m = re.search(r'@"([^"]*\[SsPp\][^"]*)"', src_text())
    if not m:
        fail("源码未找到判官字母正则")
    return re.compile(csharp_unescape(m.group(1)))


def word_patterns():
    m = re.search(r'new\[\]\s*\{([^{}]*"无新增"[^{}]*)\}', src_text(), re.S)
    if not m:
        fail("源码未找到判官词组表")
    return re.findall(r'"([^"]+)"', m.group(1))


def _u16(s):
    """按 .NET 索引口径: UTF-16 码元 (emoji 代理对 = 2 码元). C# LastIndexOf/index 都跑在码元上."""
    return str(s).encode("utf-16-le", "surrogatepass")


def gate_parse(raw, think_open, think_close, letter, words):
    """TurnGateJudge.Parse 逐字重现 (含 UTF-16 码元口径): 思考区之后取结论; 字母与词组各取『最后出现』, 位置大者胜."""
    if raw is None or not str(raw).strip():
        return None, "empty"
    text = _u16(str(raw).strip())
    close = text.rfind(_u16(think_close))
    if close >= 0:
        concl = text[close + len(_u16(think_close)):]
    elif text.rfind(_u16(think_open)) >= 0:
        return None, "thinking_truncated"
    else:
        concl = text[-128:]          # 64 码元
    concl = concl.decode("utf-16-le", "surrogatepass").strip()
    if not concl:
        return None, "empty_conclusion"
    c16 = _u16(concl)
    i_s = i_p = -1
    for m in letter.finditer(concl):
        if m.group(1).upper() == "S":
            i_s = max(i_s, len(_u16(concl[:m.start()])))
        else:
            i_p = max(i_p, len(_u16(concl[:m.start()])))
    for w in words:
        k = c16.rfind(_u16(w))
        if k < 0:
            continue
        if w in ("无新增", "无新", "无需", "跳过", "认可", "采纳"):
            i_s = max(i_s, k)
        else:
            i_p = max(i_p, k)
    if i_s < 0 and i_p < 0:
        return None, "no_marker"
    return ("S" if i_s > i_p else "P"), "ok"


def selftest_cases():
    """跨语言同位夹具: 与 src/agent.tests/TurnGateParseTests.cs 逐条同形 (同一批用例钉两侧)."""
    to = chr(60) + "think" + chr(62)
    tc = chr(60) + "/think" + chr(62)
    return [
        ("empty", "", None, "empty"),
        ("blank", "   \n ", None, "empty"),
        ("truncated", to + "用户说好", None, "thinking_truncated"),
        ("skip", to + "分析" + tc + "\nS", "S", "ok"),
        ("pass", to + "分析" + tc + "\nP", "P", "ok"),
        ("word_ack", to + "分析" + tc + "\n纯认可", "S", "ok"),
        ("word_new", to + "分析" + tc + "\n有新增诉求", "P", "ok"),
        ("last_wins_b", to + "分析" + tc + "\nS 然后 P", "P", "ok"),
        ("last_wins_a", to + "分析" + tc + "\nP 然后 S", "S", "ok"),
        ("tail64_no_think", "纯认可", "S", "ok"),
        ("empty_conclusion", to + "分析" + tc, None, "empty_conclusion"),
        ("no_marker", to + "分析" + tc + "\n没有标记", None, "no_marker"),
        ("astral", to + "分析" + tc + "\n\U0001F600S", "S", "ok"),
    ]


def run_selftest():
    to, tc = markers()
    exp_to = chr(60) + "think" + chr(62)
    exp_tc = chr(60) + "/think" + chr(62)
    bad = 0
    if (to, tc) != (exp_to, exp_tc):
        print(f"[selftest] FAIL 标记派生 {to!r}/{tc!r} != {exp_to!r}/{exp_tc!r}")
        bad += 1
    letter = letter_re()
    words = word_patterns()
    for name, raw, exp_letter, exp_reason in selftest_cases():
        got_letter, got_reason = gate_parse(raw, to, tc, letter, words)
        good = (got_letter == exp_letter and got_reason == exp_reason)
        bad += (not good)
        print(f"[selftest] {'OK  ' if good else 'FAIL'} {name}: letter={got_letter} reason={got_reason}")
    print(f"[selftest] 夹具 {len(selftest_cases())} 条, 失败 {bad}")
    return bad == 0


def markers():
    return const('ThinkOpen'), const('ThinkClose')


def get(path, timeout=30):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, payload, timeout=900):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def wait_ready(timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if PROC is not None and PROC.poll() is not None:
            fail(f"llama-server 退出 rc={PROC.returncode} (见 {SRVLOG})")
        try:
            post("/apply-template", {"messages": [{"role": "user", "content": "x"}],
                                     "add_generation_prompt": True}, timeout=10)
            return True
        except Exception:
            time.sleep(2)
    return False


def start_server():
    global PROC
    args = [BIN, "-m", MODEL, "--host", "127.0.0.1", "--port", str(PORT)] + SRV_ARGS_TAIL
    SRVLOG.write_text("argv=" + json.dumps(args) + "\n", encoding="utf-8")
    PROC = subprocess.Popen(args, stdout=open(SRVLOG, "a"), stderr=subprocess.STDOUT)
    if not wait_ready():
        fail("llama-server 起不来")
    props = get("/props")
    return props


def stop_server():
    global PROC
    if PROC is None:
        return
    try:
        PROC.terminate()
        PROC.wait(timeout=30)
    except Exception:
        try:
            PROC.kill()
        except Exception:
            pass
    PROC = None


# ---------------- 采样 (预注册规则) ----------------
def build_items():
    rows = [json.loads(l) for l in CORPUS.read_text(encoding="utf-8").splitlines() if l.strip()]
    for r in rows:
        msg = r["user_msg"] or ""
        r["klass"] = "D" if fav.DRIVE_RE.search(msg[:60]) else ("O" if fav.OPS_RE.search(msg[:200]) else "S")
    keep = [r for r in rows if r["user_len"] <= LEN_FILTER]
    items = []
    cover = {}
    for k, n in ALLOC.items():
        pool = sorted([r for r in keep if r["klass"] == k], key=lambda r: (str(r["session"]), str(r["mid"])))
        cover[k] = {"pool": len(pool), "of_class": sum(1 for r in rows if r["klass"] == k), "k": min(n, len(pool))}
        for r in random.Random(449).sample(pool, min(n, len(pool))):
            items.append({"arm": "real", "klass": k, "label": r["label"], "user_len": r["user_len"],
                          "session": r["session"], "mid": r["mid"], "user_msg": r["user_msg"]})
    ack_chars = fav.load_ack_family()
    turns = [t["text"] for t in json.loads(GRID.read_text(encoding="utf-8"))["turns"]]
    n_ack = 0
    for i, t in enumerate(turns):
        a = fav.mechanical_ack(t, ack_chars)
        n_ack += 1 if a else 0
        items.append({"arm": "grid", "klass": "ack" if a else "nonack", "turn": i,
                      "user_len": len(t), "user_msg": t})
    return items, rows, cover, n_ack


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return [round(100 * max(0.0, c - h), 1), round(100 * min(1.0, c + h), 1)]


def main():
    items, rows, cover, n_ack = build_items()
    tpl = derive_template()
    seed = "skeptic|" + rbin_load(str(ROOT / "skeptic.rbin"), str(ROOT / "data/master.key"))["profile"]
    doc_g = rbin_load(str(ROOT / "eval/rover/r431/fixture/skeptic-growth.rbin"), str(ROOT / "data/master.key"))
    doms = {}
    for k, v in doc_g.items():
        if k.startswith("g:"):
            d_r, d_p = v.split("|")
            doms[k[2:]] = (int(d_r), int(d_p))
    growth = render_growth(doms)
    t_open, t_close = const("ThinkOpen"), const("ThinkClose")
    letter, words = letter_re(), word_patterns()
    sha = hashlib.sha256(CORPUS.read_bytes()).hexdigest()
    pre = json.loads((R449 / "prereg-probe.json").read_text(encoding="utf-8"))
    pre["corpus"]["sha256"] = sha
    (R449 / "prereg-probe.json").write_text(json.dumps(pre, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[form] tpl_len={len(tpl)} seed_len={len(seed)} growth_len={len(growth)} "
          f"think=({len(t_open)},{len(t_close)}) words={len(words)} corpus_sha={sha[:16]}")
    # 忠实性正控: 与 r443 重建记录**按 turn 对齐** (r443 的 tpl=280, 本树 tpl 已变 => 期望逐题恒差 = Δtpl)
    recon = json.loads((ROOT / "eval/rover/r443/prompt-reconstruction.json").read_text(encoding="utf-8"))
    by_pin = {int(r["pinned"]): r for r in recon.get("records", [])}
    deltas, pairs = [], []
    for it in items:
        if it["arm"] != "grid":
            continue
        pin = int(it["turn"]) + 1
        if pin not in by_pin:
            continue
        mine = len(build_prompt(it["user_msg"], seed, growth, tpl))
        tele = int(by_pin[pin]["gate_prompt_len"])
        deltas.append(mine - tele)
        pairs.append({"pinned": pin, "mine": mine, "tele": tele, "growth_tele": by_pin[pin].get("growth_chars")})
    dtpl = len(tpl) - int(recon.get("tpl_len", 0))
    fidelity = {"r443_tpl_len": recon.get("tpl_len"), "now_tpl_len": len(tpl), "delta_tpl": dtpl,
                "pinned_compared": len(deltas), "deltas": sorted(set(deltas)),
                "delta_uniform": len(set(deltas)) == 1,
                "delta_equals_tpl_delta": (len(set(deltas)) == 1 and deltas[0] == dtpl),
                "seed_sha16_now": sha16(seed), "seed_sha16_r443": recon.get("seed_sha16"),
                "growth_len_now": len(growth), "pairs": pairs}
    print(f"[fidelity] {json.dumps(fidelity, ensure_ascii=False)}")
    print(f"[form] items={len(items)} (real={sum(1 for i in items if i['arm']=='real')} grid=20, grid_ack={n_ack})")
    OUTJ.write_text("", encoding="utf-8")
    start_server()
    res = []
    try:
        for idx, it in enumerate(items, 1):
            prompt = build_prompt(it["user_msg"], seed, growth, tpl)
            t0 = time.time()
            out = post("/completion", {"prompt": prompt, "n_predict": 512, "temperature": 0.0,
                                       "samplers": ["temperature"], "cache_prompt": False,
                                       "seed": 0, "stream": False})
            wall = round(time.time() - t0, 2)
            raw = out.get("content") or ""
            v, reason = gate_parse(raw, t_open, t_close, letter, words)
            rec = dict(it, prompt_len=len(prompt), letter=v, reason=reason,
                       wall_s=wall, tok_eval=out.get("tokens_evaluated"), tok_gen=out.get("tokens_predicted"),
                       raw_head=raw[:200], raw_tail=raw[-120:])
            rec.pop("user_msg", None)
            res.append(rec)
            with open(OUTJ, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"[{idx}/{len(items)}] {it['arm']}/{it['klass']} len={it['user_len']} -> {v} ({reason}) "
                  f"{wall}s gen={out.get('tokens_predicted')}")
    finally:
        stop_server()

    grid = [r for r in res if r["arm"] == "grid"]
    g_ack = [r for r in grid if r["klass"] == "ack"]
    g_non = [r for r in grid if r["klass"] == "nonack"]
    real = [r for r in res if r["arm"] == "real"]
    strat = {}
    for k in ("D", "S", "O"):
        sub = [r for r in real if r["klass"] == k]
        s = sum(1 for r in sub if r["letter"] == "S")
        strat[k] = {"n": len(sub), "S": s, "S_pct": round(100 * s / len(sub), 1) if sub else None,
                    "S_wilson95": wilson(s, len(sub)),
                    "labels": dict(collections.Counter(r["label"] for r in sub)),
                    "letter_dist": dict(collections.Counter(str(r["letter"]) for r in sub))}
    weights = {k: sum(1 for r in rows if r["klass"] == k) / len(rows) for k in ("D", "S", "O")}
    wsum = sum(weights[k] for k in strat if strat[k]["S_pct"] is not None)
    overall = round(sum(weights[k] * strat[k]["S_pct"] for k in strat if strat[k]["S_pct"] is not None) / wsum, 1) if wsum else None
    d_s = strat["D"]["S"]
    doc = {
        "round": "R449", "instrument": "real_gate_probe", "corpus_sha256": sha,
        "form": {"tpl_len": len(tpl), "seed_len": len(seed), "growth_len": len(growth),
                 "think_open_len": len(t_open), "think_close_len": len(t_close), "word_patterns": words,
                 "letter_regex": letter.pattern, "srv_args": SRV_ARGS_TAIL, "model": MODEL,
                 "fidelity_vs_r441_telemetry": fidelity},
        "sample": {"alloc": ALLOC, "len_filter": LEN_FILTER, "coverage": cover, "seed": 449},
        "controls": {"I1_ack_n": len(g_ack), "I1_ack_S": sum(1 for r in g_ack if r["letter"] == "S"),
                     "I2_nonack_n": len(g_non), "I2_nonack_P": sum(1 for r in g_non if r["letter"] == "P"),
                     "declared_ack_family": n_ack},
        "readings": {"strata": strat, "class_weights": {k: round(v, 4) for k, v in weights.items()},
                     "overall_S_pct_weighted": overall,
                     "D_false_S_pct": strat["D"]["S_pct"],
                     "local_cost_per_call": {"tok_eval_mean": round(sum(r["tok_eval"] or 0 for r in res) / len(res), 1),
                                             "tok_gen_mean": round(sum(r["tok_gen"] or 0 for r in res) / len(res), 1),
                                             "wall_mean_s": round(sum(r["wall_s"] for r in res) / len(res), 2)}},
        "raw_file": str(OUTJ), "prereg": str(R449 / "prereg-probe.json"),
    }
    i1_ok = len(g_ack) and sum(1 for r in g_ack if r["letter"] == "S") >= max(1, -(-5 * len(g_ack) // 7))
    i2_ok = len(g_non) and sum(1 for r in g_non if r["letter"] == "P") >= max(1, -(-9 * len(g_non) // 13))
    doc["criteria"] = {
        "V0_void": (not i1_ok),
        "I1_pass": bool(i1_ok), "I2_pass": bool(i2_ok),
        "V1_verdict": ("STATE_DB_CANNOT_IMPROVE_KPI" if (i1_ok and strat["D"]["S_pct"] is not None
                                                       and strat["D"]["S_pct"] >= 50.0)
                       else ("CANDIDATE_NEEDS_EQUIVALENCE_TEST" if i1_ok else "VOID_INSTRUMENT")),
    }
    OUTD.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(doc["controls"], ensure_ascii=False))
    print(json.dumps(doc["readings"]["strata"], ensure_ascii=False))
    print("overall_S_pct_weighted=", overall, "| criteria=", json.dumps(doc["criteria"], ensure_ascii=False))
    print(f"[out] {OUTD}")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if run_selftest() else 1)
    sys.exit(main())
