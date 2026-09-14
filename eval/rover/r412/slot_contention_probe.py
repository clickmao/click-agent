#!/usr/bin/env python3
"""R412 探针: 多会话 slot 争用（本地长驻 llama-server 的第二 regime）。

判据**先于本文件运行**写死在
  docs/plans/v0.34.0-r412-multi-session-slot-contention.md §2
（C1 争用签名 / C2 静默vs显式分类 / C3 绝对长度 / N1 负控 ⇒ A 不达标即 INCONCLUSIVE）。

独立实现: 直连 llama-server HTTP，不经过产品代码（R402 独立通道取证）。

臂:
  A 同会话连续      S1t1→S1t2→S2t1→S2t2          （基线，期望 ≥0.97）
  B 会话交替(串行)  S1t1→S2t1→S1t2→S2t2
  C 会话交替(并发)  (S1t1∥S2t1) → (S1t2∥S2t2)
  D -np 2 -c 12288 重跑 C                        （处置候选；每 slot 6144 ≥ 4224 才可判）

携带复用率口径（与 LocalSessionCacheLedger 同构，分母不用远端 64 单元界）:
  ceiling    = 上一轮 prompt 总长 + 上一轮生成
  carryOver  = min(本轮 prompt 总长, ceiling)
  carryReuse = cache_n / carryOver
"""
import json
import os
import pathlib
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

BIN = os.environ.get("AGENTFRAMEWORK_LLAMA_BIN", "")
MODEL = "/tmp/models/r1-distill-qwen-1.5b-q4km.gguf"
ROOT = pathlib.Path("/home/agentuser/AgentFramework")
D = ROOT / "eval/rover/r412"
D.mkdir(parents=True, exist_ok=True)
P1 = (ROOT / "eval/rover/r412/prefix-p1.txt").read_text(encoding="utf-8")
P2 = (ROOT / "eval/rover/r412/prefix-p2.txt").read_text(encoding="utf-8")
# 修正记录（冒烟后、正式臂之前）: 原设计 P2 = P1 + 唯一标记 ⇒ 两会话共享超长公共子序列，
# 判别力为 0（冒烟实测 A/B/C 三臂复用率完全相同 0.9863/0.9878）。现改为一对**不同文档**语料
# （P1 = R411 长前缀 4320 token；P2 = improvements.md 独立语料 4300 token），长度均 ≥ 4224 红线。

Q1 = "用一句话回答: 1+1 等于几?"
Q2 = "用一句话回答: 2+2 等于几?"
GEN = {"n_predict": 4, "temperature": 0, "cache_prompt": True,
       "top_k": 1, "top_p": 1.0, "min_p": 0.0, "repeat_penalty": 1.0}
PORT = 8952
BASE = f"http://127.0.0.1:{PORT}"
CTX = int(os.environ.get("R412_CTX", "4608"))       # 内存约束: 6144 实测 server RSS 2.08 GB ⇒ 被 OOM 杀
NP2_CTX = CTX * 2                                    # 2 slot 时保持**每 slot** CTX
if os.environ.get("R412_SMOKE"):                     # 端到端管道验证用（前缀截短；正式臂不得设此变量）
    P1, P2 = P1[:420], P2[:420]
    if "R412_CTX" not in os.environ:
        CTX = 2048
        NP2_CTX = 4096
LOCK = threading.Lock()
ROWS = []
PORT_SLOTS = {}
assert BIN and pathlib.Path(BIN).exists(), f"缺 llama-server: {BIN!r}"


def dump():
    with LOCK:
        (D / "slot_contention.json").write_text(
            json.dumps({"rows": ROWS, "slots": PORT_SLOTS}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")


def post(path, body, timeout=1200):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def get(path, timeout=60):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def start_server(parallel, ctx):
    args = [BIN, "-m", MODEL, "--host", "127.0.0.1", "--port", str(PORT),
            "-c", str(ctx), "-t", "2", "-np", str(parallel),
            "--cache-type-k", "f32", "--cache-type-v", "f32", "--flash-attn", "off",
            "-b", "512", "-ub", "512", "--jinja"]
    log = (D / f"server-np{parallel}.log").open("wb")
    proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    for _ in range(180):
        try:
            get("/health")
            break
        except Exception:  # noqa: BLE001
            time.sleep(1)
    else:
        raise SystemExit(f"server(np={parallel}) 未就绪")
    try:
        PORT_SLOTS[f"np{parallel}_slots"] = len(get("/slots"))
    except Exception as e:  # noqa: BLE001
        PORT_SLOTS[f"np{parallel}_slots"] = f"n/a: {type(e).__name__}"
    try:
        pr = get("/props")
        PORT_SLOTS[f"np{parallel}_props"] = {"n_ctx": pr.get("default_generation_settings", {}).get("n_ctx"),
                                            "total_slots": pr.get("total_slots")}
    except Exception as e:  # noqa: BLE001
        PORT_SLOTS[f"np{parallel}_props"] = f"n/a: {type(e).__name__}"
    dump()
    return proc


def one(arm, sid, turn, prefix, prev_total, prev_gen, reply_prev, q):
    """单次请求；返回 row（含原始字段与独立算出的 carrying 复用率）。"""
    turns = [{"role": "system", "content": prefix}, {"role": "user", "content": q}]
    if reply_prev is not None:
        turns = [{"role": "system", "content": prefix},
                 {"role": "user", "content": Q1},
                 {"role": "assistant", "content": reply_prev},
                 {"role": "user", "content": q}]
    row = {"arm": arm, "session": sid, "turn": turn}
    t0 = time.time()
    try:
        p = post("/apply-template", {"messages": turns})["prompt"]
        tk = len(post("/tokenize", {"content": p})["tokens"])
        r = post("/completion", dict(GEN, prompt=p))
        row.update({"ok": True, "render_tokens": tk, "tokens_evaluated": r["tokens_evaluated"],
                    "prompt_n": r["timings"]["prompt_n"], "cache_n": r["timings"]["cache_n"],
                    "prompt_ms": r["timings"].get("prompt_ms"),
                    "predicted_n": r["timings"].get("predicted_n", len(r.get("content") or "")),
                    "content": (r.get("content") or "")[:80]})
    except urllib.error.HTTPError as e:
        row.update({"ok": False, "kind": "http_error", "status": e.code,
                    "error": e.read()[:300].decode("utf-8", "replace")})
    except Exception as e:  # noqa: BLE001
        row.update({"ok": False, "kind": type(e).__name__, "error": str(e)[:300]})
    row["wall_ms"] = int((time.time() - t0) * 1000)
    # 独立算的携带复用率（不依赖产品代码/服务端任何命名）
    if row.get("ok") and prev_total > 0:
        ceiling = prev_total + max(0, prev_gen)
        carry = min(row["tokens_evaluated"], ceiling)
        row.update({"ceiling": ceiling, "carry_over": carry,
                    "carry_reuse": round(row["cache_n"] / carry, 4) if carry else None,
                    "abs_cached": row["cache_n"], "abs_ge_4224": row["cache_n"] >= 4224})
    else:
        row.update({"ceiling": prev_total + max(0, prev_gen) if prev_total > 0 else 0,
                    "carry_over": None, "carry_reuse": None})
    with LOCK:
        ROWS.append(row)
    dump()
    print(f"{arm} {sid} t{turn} ok={row['ok']} total={row.get('tokens_evaluated')} "
          f"cache_n={row.get('cache_n')} reuse={row.get('carry_reuse')} wall={row['wall_ms']}ms", flush=True)
    return row


def arm_continuous(tag):
    st = {}
    for sid, px in (("S1", P1), ("S2", P2)):
        r1 = one(tag, sid, 1, px, 0, 0, None, Q1)
        st[sid] = {"prev": r1.get("tokens_evaluated", 0), "gen": r1.get("predicted_n") or 0}
        r2 = one(tag, sid, 2, px, st[sid]["prev"], st[sid]["gen"], r1.get("content", ""), Q2)
        st[sid] = {"prev": r2.get("tokens_evaluated", 0), "gen": r2.get("predicted_n") or 0}


def arm_alternating(tag, concurrent):
    st = {}
    r1 = {}
    if concurrent:
        ths = [threading.Thread(target=lambda s=s, p=p: r1.__setitem__(s, one(tag, s, 1, p, 0, 0, None, Q1)))
               for s, p in (("S1", P1), ("S2", P2))]
    else:
        ths = []
        for s, p in (("S1", P1), ("S2", P2)):
            r1[s] = one(tag, s, 1, p, 0, 0, None, Q1)
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    for s in ("S1", "S2"):
        st[s] = {"prev": r1[s].get("tokens_evaluated", 0), "gen": r1[s].get("predicted_n") or 0}
    r2 = {}
    if concurrent:
        ths = [threading.Thread(target=lambda s=s: r2.__setitem__(s, one(tag, s, 2, P1 if s == "S1" else P2,
                                                                         st[s]["prev"], st[s]["gen"], r1[s].get("content", ""), Q2)))
               for s in ("S1", "S2")]
    else:
        ths = []
        for s in ("S1", "S2"):
            r2[s] = one(tag, s, 2, P1 if s == "S1" else P2, st[s]["prev"], st[s]["gen"], r1[s].get("content", ""), Q2)
    for t in ths:
        t.start()
    for t in ths:
        t.join()


def ratio(arm, sid):
    for r in ROWS:
        if r["arm"] == arm and r["session"] == sid and r["turn"] == 2 and r.get("carry_reuse") is not None:
            return r["carry_reuse"]
    return None


def mem_available_mb():
    try:
        return int(subprocess.run(["free", "-m"], capture_output=True, text=True).stdout.split("\n")[1].split()[6])
    except Exception:  # noqa: BLE001
        return -1


def main():
    free = subprocess.run(["free", "-m"], capture_output=True, text=True).stdout.split("\n")[1]
    print(f"start free: {free}  CTX={CTX} NP2_CTX={NP2_CTX}  P1/P2 chars={len(P1)}/{len(P2)}", flush=True)
    servers = {}
    servers["np1"] = start_server(1, CTX)
    try:
        for tag, fn in (("A", lambda: arm_continuous("A")),
                        ("B", lambda: arm_alternating("B", concurrent=False)),
                        ("C", lambda: arm_alternating("C", concurrent=True))):
            try:
                fn()
            except Exception as e:  # noqa: BLE001
                PORT_SLOTS[f"arm_{tag}_error"] = f"{type(e).__name__}: {str(e)[:200]}"
                print(f"ARM {tag} 失败: {type(e).__name__}: {str(e)[:200]}", flush=True)
            dump()
    finally:
        servers["np1"].terminate()
        try:
            servers["np1"].wait(timeout=30)
        except Exception:  # noqa: BLE001
            servers["np1"].kill()
    # 处置候选臂 D: 每 slot CTX ≥ 4224 才可判（内存不足则明确跳过，不冒充通过）
    if mem_available_mb() < 1100:
        PORT_SLOTS["np2_skipped"] = f"low_mem(available={mem_available_mb()}MB)"
        print("ARM D 跳过: 内存不足", flush=True)
    else:
        server_d = None
        try:
            server_d = start_server(2, NP2_CTX)
            arm_alternating("D", concurrent=True)
        except Exception as e:  # noqa: BLE001
            PORT_SLOTS["arm_D_error"] = f"{type(e).__name__}: {str(e)[:200]}"
            print(f"ARM D 失败: {type(e).__name__}: {str(e)[:200]}", flush=True)
        finally:
            if server_d is not None:
                server_d.terminate()
                try:
                    server_d.wait(timeout=30)
                except Exception:  # noqa: BLE001
                    server_d.kill()
            dump()

    A = {s: ratio("A", s) for s in ("S1", "S2")}
    Bv = {s: ratio("B", s) for s in ("S1", "S2")}
    C = {s: ratio("C", s) for s in ("S1", "S2")}
    Dv = {s: ratio("D", s) for s in ("S1", "S2")}
    neg_ok = all(v is not None and v >= 0.97 for v in A.values())
    cont_B = any(v is not None and v < 0.97 for v in Bv.values())
    cont_C = any(v is not None and v < 0.97 for v in C.values())
    errors = [r for r in ROWS if not r.get("ok")]
    verdict = {
        "A_carry_reuse": A, "B_carry_reuse": Bv, "C_carry_reuse": C, "D_carry_reuse": Dv,
        "N1_negative_control_ok": neg_ok,
        "D_slot_ctx": NP2_CTX // 2, "D_judgeable": (NP2_CTX // 2) >= 4224,
        "C1_contention_in_B": cont_B, "C1_contention_in_C": cont_C,
        "C2_explicit_failures": len(errors),
        "C2_explicit_failure_kinds": sorted({r.get("kind") for r in errors}),
        "C3_abs_cached_per_arm": {a: {r["session"]: r.get("abs_cached") for r in ROWS
                                     if r["arm"] == a and r["turn"] == 2 and r.get("ok")}
                                  for a in ("A", "B", "C", "D")},
        "verdict": ("INCONCLUSIVE(负控不达标: A<0.97 ⇒ 探针/环境无效)" if not neg_ok else
                    ("CONTENTION_CONFIRMED" if (cont_B or cont_C) else "NO_CONTENTION")),
    }
    dump()
    (D / "verdict.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\n=== 裁决 ===\n" + json.dumps(verdict, ensure_ascii=False, indent=2), flush=True)
    return 0 if neg_ok else 3


if __name__ == "__main__":
    sys.exit(main())
