#!/usr/bin/env python3
"""R429 传输级机制探针 v2 —— 决策 prompt 在前缀缓存「全量评估 / 部分复用 / 交错」下的可复现性。

v2 修正 (冒烟 n=1 后, 全量前):
  ① 解析器镜像产物 TurnGateJudge.Parse (LocalGenerationPort.cs:283-333): 只认 </think> 之后结论区,
     think 未闭合 => thinking_truncated(未判定); 结论区无标记 => no_marker。绝不在推理正文里找字母。
  ② 同 prompt 分组比较 (v1 误把兄弟消息当同 prompt ⇒ 假阳性)。
  ③ 加同缓存态的重复 (mix2) 以区分「给定缓存态确定性」与「缓存态依赖调用序列」。
  ④ 落 raw content + stop_type, 便于机检复核。
判据: 见 docs/plans/v0.50.0-r429-decision-cache-pin.md (P1/P2/P2b/P3/P4)
"""
import json, os, re, sys, time, urllib.request, pathlib

PORT = int(os.environ.get("R429_PORT", "8941"))
OUT = pathlib.Path("/home/agentuser/AgentFramework/eval/rover/r429")
BASE = f"http://127.0.0.1:{PORT}"
CYCLES = int(sys.argv[1]) if len(sys.argv) > 1 else 5
TAG = sys.argv[2] if len(sys.argv) > 2 else f"n{CYCLES}"

THINK_OPEN, THINK_CLOSE = "<think>", "</think>"
SKIP_WORDS = ("无新增", "无新", "无需", "跳过", "认可", "采纳")
PASS_WORDS = ("有新增", "新要求", "新问题", "纠正", "继续", "需要")
SP = re.compile(r"(?<![A-Za-z])([SsPp])(?![A-Za-z])")

def gate_parse(raw):
    """镜像产物 TurnGateJudge.Parse ⇒ (state, verdict)；state ∈ decided/thinking_truncated/no_marker/empty*"""
    if not raw or not raw.strip(): return ("empty", None)
    text = raw.strip()
    conclusion = text
    close = text.rfind(THINK_CLOSE)
    if close >= 0: conclusion = text[close + len(THINK_CLOSE):]
    else:
        if text.rfind(THINK_OPEN) >= 0: return ("thinking_truncated", None)
    if len(conclusion) > 64: conclusion = conclusion[-64:]
    conclusion = conclusion.strip()
    if not conclusion: return ("empty_conclusion", None)
    lastSkip = lastPass = -1
    for m in SP.finditer(conclusion):
        if m.group(1) in "Ss": lastSkip = max(lastSkip, m.start())
        else: lastPass = max(lastPass, m.start())
    for pat in SKIP_WORDS + PASS_WORDS:
        k = conclusion.rfind(pat)
        if k < 0: continue
        if pat in SKIP_WORDS: lastSkip = max(lastSkip, k)
        else: lastPass = max(lastPass, k)
    if lastSkip < 0 and lastPass < 0: return ("no_marker", None)
    return ("decided", "S" if lastSkip > lastPass else "P")

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
def judge_prompt(prev, user):
    return ("判定用户消息相对上一轮回答: 纠正否定上一轮=C, 认可采纳=A, 新话题无关=N。\n"
            f"上一轮: {prev}\n用户: {user}\n只输出一个字母。")
P1_USER, P2_USER, P3_USER = "不对，你上一轮不准确，请重新确认。", "好，按这个来。", "另外，测试命令是什么？"
JUDGE_SYS = "只输出一个字母。"
JUDGE_PREV = "已按你要求把前置门接进链里，跳过轮的 token 已降下来。"
JUDGE_USER = "好，按这个来。"

def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1200) as r: return json.loads(r.read().decode())
def render(turns): return post("/apply-template", {"messages": turns, "add_generation_prompt": True})["prompt"]

def complete(prompt, cache, n_predict=512):
    t0 = time.time()
    r = post("/completion", {"prompt": prompt, "n_predict": n_predict, "temperature": 0.0, "samplers": ["temperature"],
                             "cache_prompt": bool(cache), "stream": False, "return_tokens": True})
    st, verdict = gate_parse(r.get("content", ""))
    return {"cache_on": bool(cache), "cache_n": r.get("timings", {}).get("cache_n"),
            "prompt_n": r.get("timings", {}).get("prompt_n"), "predicted_n": r.get("timings", {}).get("predicted_n"),
            "stop_type": r.get("stop_type"), "tokens": r.get("tokens"), "content": r.get("content", ""),
            "gate_state": st, "gate_verdict": verdict, "wall_s": round(time.time() - t0, 2)}

def run_cycle(i, g1, g2, g3, jt):
    c = {"cycle": i}
    c["warm"] = complete(g1, True)      # 紧邻同 prompt ⇒ 全量评估 (cache_n≈0)
    c["back"] = complete(g1, True)      # 复用上一次 gate 前缀 ⇒ 部分复用
    c["sib"] = complete(g2, True)       # 兄弟消息 (不同 prompt, 仅作 poison)
    c["mix"] = complete(g1, True)       # 交错的 gate
    c["jmix"] = complete(jt, True)      # 判官 (另一前缀) 交错
    c["mix2"] = complete(g1, True)      # 与 mix 同前置序列 ⇒ 同态重复
    c["ctrl"] = complete(g3, True)      # 负控: 不同用户消息
    c["off1"] = complete(g1, False)
    c["joff"] = complete(jt, False)
    c["off2"] = complete(g1, False)
    c["off3"] = complete(g1, False)
    return c

def main():
    g1 = render([{"role": "user", "content": gate_prompt(P1_USER)}])
    g2 = render([{"role": "user", "content": gate_prompt(P2_USER)}])
    g3 = render([{"role": "user", "content": gate_prompt(P3_USER)}])
    jt = render([{"role": "system", "content": JUDGE_SYS}, {"role": "user", "content": judge_prompt(JUDGE_PREV, JUDGE_USER)}])
    rec = []
    for i in range(CYCLES):
        c = run_cycle(i, g1, g2, g3, jt)
        rec.append(c)
        print(f"[cycle {i}] old(warm/back/mix/mix2) ids={len(c['warm']['tokens'])}/{len(c['back']['tokens'])}/"
              f"{len(c['mix']['tokens'])}/{len(c['mix2']['tokens'])} cache_n={c['warm']['cache_n']}/{c['back']['cache_n']}/"
              f"{c['mix']['cache_n']}/{c['mix2']['cache_n']} | new(off1/2/3) ids={len(c['off1']['tokens'])}/"
              f"{len(c['off2']['tokens'])}/{len(c['off3']['tokens'])} cache_n={c['off1']['cache_n']}/{c['off2']['cache_n']}/{c['off3']['cache_n']}",
              flush=True)
        (OUT / f"probe-r429-cache-{TAG}.partial.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")

    def ids(k, n): return [x[n]["tokens"] for x in k]
    old_groups = ["warm", "back", "mix", "mix2"]; new_groups = ["off1", "off2", "off3"]
    def all_equal(k, names): return all(x[names[0]]["tokens"] == x[n]["tokens"] for x in k for n in names[1:])
    old_eq = all_equal(rec, old_groups); new_eq = all_equal(rec, new_groups)
    warm_off_eq = all(x["warm"]["tokens"] == x["off1"]["tokens"] for x in rec)
    p3 = all(x["warm"]["tokens"] != x["ctrl"]["tokens"] for x in rec)
    old_states = [{n: [x[n]["gate_state"], x[n]["gate_verdict"]] for n in old_groups} for x in rec]
    flip = [s for s in old_states if len({tuple(v) for v in s.values()}) > 1]
    verdict = {
        "cycles": CYCLES, "tag": TAG,
        "old_group_ids_equal": old_eq, "P1_pass": not old_eq,
        "new_group_ids_equal": new_eq, "P2_pass": new_eq,
        "P2b_warm_eq_off1": warm_off_eq,
        "P3_control_differs": p3,
        "P4_state_flips": flip, "P4_pass": len(flip) > 0,
        "cache_n_structure": [{n: x[n]["cache_n"] for n in old_groups + new_groups} for x in rec],
        "gate_states": old_states,
        "stop_types": [{n: x[n]["stop_type"] for n in old_groups + new_groups} for x in rec],
        "sib_ctrl": [{"cycle": x["cycle"], "sib_ids": len(x["sib"]["tokens"]), "sib_cache_n": x["sib"]["cache_n"],
                      "ctrl_cache_n": x["ctrl"]["cache_n"], "ctrl_state": x["ctrl"]["gate_state"]} for x in rec],
    }
    (OUT / f"probe-r429-cache-{TAG}.json").write_text(json.dumps({"records": rec, "verdict": verdict}, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / f"probe-r429-cache-{TAG}.partial.json").unlink(missing_ok=True)
    print(json.dumps(verdict, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
