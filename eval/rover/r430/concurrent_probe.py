#!/usr/bin/env python3
"""R430 机制探针 — 「同一 prompt + cache_prompt=false + 并发在途请求」的逐位可复现性。

背景 (已机检, 见 verdict-C-k8r-r430post1.json):
  门判 4 次的 prompt 指纹 / 请求体指纹 / 角色种子指纹**逐位相同**, 而输出 raw_len 有 4 种取值
  (122/129/113/111) ⇒ 输入可复现性成立, 不确定在**引擎侧** (H2)。
  产品侧变量: correction_judge 的本地 r1 调用与门判**同时在途** (判官 47–119 s, 门判被排队 19–46 s)。

预注册判据:
  P1 (控制): 串行 A,A,A (cache off) ⇒ token ids 逐位相同 (复现 R429 探针)。
  P2 (机制): A 与 B (长生成) **同时在途** ⇒ 若 A 出现 >1 种 ids ⇒ 引擎侧漂移由并发在途引起。
  P3 (隔离): 若 P2 坐实 ⇒ 测总槽位分离 (-np 2 + id_slot) 能否恢复逐位相同 ⇒ 修法有了传输级背书。
  记录 server /props (total_slots / n_threads) 作为环境真值。
"""
import json, os, threading, time, urllib.request, subprocess, pathlib, sys, signal

PORT = int(os.environ.get("R430C_PORT", "8951"))
OUT = pathlib.Path("/home/agentuser/AgentFramework/eval/rover/r430")
MODEL = "/tmp/models/r1-distill-qwen-1.5b-q4km.gguf"
BIN = "/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server"
BASE = f"http://127.0.0.1:{PORT}"
LOG = open("/tmp/r430c_server.log", "w")

ROLE_SEED = "skeptic|质疑优先：先确认结论依赖的前提是否成立，再判断结论；对跳步与含糊表述保持低容忍。"
GATE_HEAD = (
    "判别用户这一条消息是否携带新的诉求或新信息。\n"
    "- S = 无新增: 纯认可/确认/寒暄/致谢/重复上一轮内容/只有表情。\n"
    "- P = 有新增: 新问题/新要求/补充条件/纠正/提供新信息。\n"
    "示例:\n用户: 好，按这个来。 → S\n用户: 嗯。 → S\n用户: 收到，谢谢。 → S\n"
    "用户: 另外，测试命令是什么？ → P\n用户: 不对，你上一轮不准确，请重新确认。 → P\n"
    "先思考, 思考结束后必须另起一行只写一个字母 (S 或 P), 不要写其他内容。\n"
    "无法确定时也必须写 P (宁可多走一次远端)。\n")
def gate_prompt(u): return GATE_HEAD + "【角色设定】" + ROLE_SEED[:300] + "\n【用户消息】" + u.strip() + "\n答案:\n"
JUDGE_SYS = "只输出一个字母。"
JUDGE_PREV = "已按你要求把前置门接进链里，跳过轮的 token 已降下来。"
JUDGE_USER = "好，按这个来。"
def judge_prompt(prev, user):
    return ("判定用户消息相对上一轮回答: 纠正否定上一轮=C, 认可采纳=A, 新话题无关=N。\n"
            f"上一轮: {prev}\n用户: {user}\n只输出一个字母。")

def post(path, body, timeout=1800):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read().decode())

def start_server(np_slots=1):
    global PROC
    args = [BIN, "-m", MODEL, "--host", "127.0.0.1", "--port", str(PORT), "-c", "4608", "-t", "1",
            "--cache-type-k", "f32", "--cache-type-v", "f32", "--flash-attn", "off", "--jinja"]
    if np_slots != 1: args += ["-np", str(np_slots)]
    PROC = subprocess.Popen(args, stdout=LOG, stderr=subprocess.STDOUT)
    for _ in range(180):
        try:
            with urllib.request.urlopen(BASE + "/health", timeout=2) as r:
                if r.status == 200: return True
        except Exception: time.sleep(1)
    return False

def stop_server():
    try: PROC.send_signal(signal.SIGTERM); PROC.wait(timeout=20)
    except Exception:
        try: PROC.kill()
        except Exception: pass

def render(turns): return post("/apply-template", {"messages": turns, "add_generation_prompt": True})["prompt"]

def complete(prompt, cache=False, n_predict=512, id_slot=None):
    body = {"prompt": prompt, "n_predict": n_predict, "temperature": 0.0, "samplers": ["temperature"],
            "cache_prompt": bool(cache), "stream": False, "return_tokens": True, "seed": 0}
    if id_slot is not None: body["id_slot"] = id_slot
    t0 = time.time()
    r = post("/completion", body)
    t = r.get("timings", {})
    return {"ids": r.get("tokens"), "content": r.get("content", ""), "cache_n": t.get("cache_n"),
            "prompt_n": t.get("prompt_n"), "predicted_n": t.get("predicted_n"),
            "wall_s": round(time.time() - t0, 2)}

def main():
    res = {"probe": "R430 concurrent", "port": PORT}

    # 顺序修正 (v1 仪器错): prompt 渲染走 /apply-template ⇒ **必须先起 server**。
    ok = start_server(1)
    res["server_up_np1"] = ok
    if not ok:
        print("server start failed"); sys.exit(1)
    A = render([{"role": "user", "content": gate_prompt("好，按这个来。")}])
    B = render([{"role": "system", "content": JUDGE_SYS}, {"role": "user", "content": judge_prompt(JUDGE_PREV, JUDGE_USER)}])
    res["prompt_A_chars"] = len(A); res["prompt_B_chars"] = len(B)
    # ---- 组 1: 串行控制 (np=1) ----
    try:
        props = post("/props", {}) if False else json.loads(urllib.request.urlopen(BASE + "/props", timeout=10).read().decode())
    except Exception as e:
        props = {"error": str(e)[:80]}
    res["props_np1"] = {k: props.get(k) for k in ("total_slots", "n_ctx") if isinstance(props, dict)}
    dgs = props.get("default_generation_settings", {}) if isinstance(props, dict) else {}
    res["props_np1"]["n_threads"] = dgs.get("n_threads")
    g1 = [complete(A, False) for _ in range(3)]
    res["G1_serial_np1"] = g1
    # ---- 组 2: 并发在途 (np=1) ----
    g2 = []
    for i in range(3):
        box = {}
        th = threading.Thread(target=lambda: box.update(b=complete(B, False, 256)), daemon=True)
        th.start(); time.sleep(0.4)
        a = complete(A, False)
        th.join(timeout=600)
        g2.append({"A": a, "B_ids": len(box.get("b", {}).get("ids") or []), "B_wall": box.get("b", {}).get("wall_s")})
        print(f"[G2 {i}] A_ids={len(a['ids'])} A_cache_n={a['cache_n']} A_wall={a['wall_s']} B_tok={len(box.get('b',{}).get('ids') or [])}", flush=True)
    res["G2_concurrent_np1"] = g2
    stop_server()

    # ---- 组 3: 独立槽位 (np=2 + id_slot 分离) ----
    ok2 = start_server(2)
    res["server_up_np2"] = ok2
    if ok2:
        try:
            props2 = json.loads(urllib.request.urlopen(BASE + "/props", timeout=10).read().decode())
        except Exception as e:
            props2 = {"error": str(e)[:80]}
        res["props_np2"] = {k: props2.get(k) for k in ("total_slots", "n_ctx") if isinstance(props2, dict)}
        g3 = []
        for i in range(3):
            box = {}
            th = threading.Thread(target=lambda: box.update(b=complete(B, False, 256, id_slot=1)), daemon=True)
            th.start(); time.sleep(0.4)
            a = complete(A, False, 512, id_slot=0)
            th.join(timeout=600)
            g3.append({"A": a, "B_ids": len(box.get("b", {}).get("ids") or [])})
            print(f"[G3 {i}] A_ids={len(a['ids'])} A_cache_n={a['cache_n']} A_wall={a['wall_s']}", flush=True)
        res["G3_slot_isolated_np2"] = g3
        stop_server()

    def id_sets(rows, key=lambda r: r["A"]):
        return [tuple(x[key]["ids"] or []) for x in rows]
    s1 = id_sets(res["G1_serial_np1"])
    res["verdict"] = {
        "P1_serial_identical": len(set(s1)) == 1, "P1_variants": len(set(s1)),
        "P2_concurrent_variants": len(set(id_sets(res.get("G2_concurrent_np1", [])))) if res.get("G2_concurrent_np1") else None,
        "P2_reproduced": (len(set(id_sets(res["G2_concurrent_np1"]))) > 1) if res.get("G2_concurrent_np1") else None,
        "P3_slot_isolated_variants": (len(set(id_sets(res.get("G3_slot_isolated_np2", [])))) if res.get("G3_slot_isolated_np2") else None),
    }
    (OUT / "probe-r430-concurrent.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"verdict": res["verdict"], "len_A": [len(x) for x in s1],
                      "props_np1": res.get("props_np1"), "props_np2": res.get("props_np2")}, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
