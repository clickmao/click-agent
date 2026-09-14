#!/usr/bin/env python3
"""R435 修复臂探针 — 判官 prompt 形状 (F3) × 预算 (F1) × 解析层 的**单次生成、多重归因**。

为什么这样设计:
  probe_j1 已用**产品实发 prompt**(旧文本) 在 r1 上复现本地 1/7, 并与产品遥测 6×remote_fallback 逐位吻合。
  现在要回答「修哪个变量能把 1/7 抬起来」, 而**不能**靠猜:
    - prompt 变量: 新文本由产品**同一函数** `CorrectionDetector.BuildJudgePrompt` 产出
      (经 `AGENTFRAMEWORK_R435_DUMP` 由单测落盘 ⇒ 探针与产品共文本, 无双份实现漂移);
    - 预算变量: 512 vs 1024 (产品 R435 已改为 1024);
    - 解析变量: **同一份 raw** 分别用旧解析器与新解析器判定 ⇒ 解析层的贡献 0 额外生成成本。

判据 (预注册, 见 docs/plans/v0.56.0-r435-relation-judge-localization.md §4):
  J2a 新 prompt + 1024 的本地可解析率 ≥ 6/9 (旧档 1/9 或接近); 否则记负结论。
  J2b **语义正确率**不得下降: 解析出的字母须等于预注册真值表 (§3), 误判 = 由 1 例 C/A/N 换另一例错 ⇒ 不算增益。
  J2c 负控: 结论区回声指令片段的样本必须仍判失败 (不允许靠放宽解析把回声当判定)。
输出: eval/rover/r435/probe-j2-arms.json (逐条 raw 全文 + 两种解析器判定)。
"""
import json, os, pathlib, re, signal, subprocess, sys, time, urllib.request

PORT = int(os.environ.get("R435_PORT", "47981"))
ROOT = pathlib.Path("/home/agentuser/AgentFramework")
OUT = ROOT / "eval/rover/r435"
MODEL = "/tmp/models/r1-distill-qwen-1.5b-q4km.gguf"
BIN = os.environ.get("AGENTFRAMEWORK_LLAMA_BIN",
                     "/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server")
BASE = f"http://127.0.0.1:{PORT}"
LOG = open("/tmp/r435b_server.log", "w")


def _product_markers():
    """R435 教训 (两次踩同一坑): 绝不手打 think 标记 —— 字面量里会混入不可见 U+200B,
    导致 close 检测恒 False ⇒ 分类器读推理正文 ⇒ 假阳性 (探针 8/9 而产品 1/7)。
    改为从产品源码按 C# \\uXXXX 转义还原真常量并硬断言。"""
    s = (ROOT / "src/agent.modelqueue/LocalGenerationPort.cs").read_text(encoding="utf-8")
    def grab(name):
        m = re.search(name + r'\s*=\s*"((?:[^"\\]|\\.)*)"', s)
        v = re.sub(r"\\u([0-9a-fA-F]{4})", lambda mm: chr(int(mm.group(1), 16)), m.group(1))
        return v
    o, c = grab("ThinkOpen"), grab("ThinkClose")
    assert (o, c) == ("<think>", "</think>") and "\u200b" not in o and "\u200b" not in c, (repr(o), repr(c))
    return o, c


THINK_OPEN, THINK_CLOSE = _product_markers()
SYS = "只输出一个字母。"
BUDGET_S = int(os.environ.get("R435_BUDGET_S", "1500"))

# 旧判官 prompt（R434 产品实发形状, probe_j1 已与产品 prompt_len 逐位校验）
OLD_P1 = "判定用户消息相对上一轮回答: 纠正否定上一轮=C, 认可采纳=A, 新话题无关=N。"

# 真值表（语义判定, 与产品分类定义 §3 一致；模型自己的链上也写着同一结论）
TRUTH = {"turn1": "N", "turn3": "N", "turn5": "N", "turn6": "A", "turn7": "N",
         "turn8": "A", "turn9": "N", "syn-c": "C", "syn-a": "A"}

WORDS = (("纠正", "C"), ("否定", "C"), ("认可", "A"), ("采纳", "A"), ("新话题", "N"), ("无关", "N"))
LETTER_RE = re.compile(r"(?<![A-Za-z])([CcAaNn])(?![A-Za-z])")


def parse_old(raw):
    """R434 解析器逐行忠实重实现（字母正则 + 全文搜索, 不看 64 字符窗口, 无词表）。"""
    if not raw or not raw.strip():
        return None, "empty"
    text = raw.strip()
    close = text.rfind(THINK_CLOSE)
    if close >= 0:
        text = text[close + len(THINK_CLOSE):]
    elif text.rfind(THINK_OPEN) >= 0:
        return None, "thinking_truncated"
    text = text.strip()
    if not text:
        return None, "empty_conclusion"
    last, pick = -1, None
    for m in LETTER_RE.finditer(text):
        last, pick = m.start(), m.group(1).upper()
    if last < 0:
        return None, "no_marker"
    return pick, "ok"


def parse_new(raw):
    """R435 解析器逐行忠实重实现（LocalGenerationPort.cs RelationLetterJudge.TryNormalize）。"""
    if not raw or not raw.strip():
        return None, "empty"
    text = raw.strip()
    close = text.rfind(THINK_CLOSE)
    if close >= 0:
        text = text[close + len(THINK_CLOSE):]
    elif text.rfind(THINK_OPEN) >= 0:
        return None, "thinking_truncated"
    elif len(text) > 64:
        text = text[-64:]
    text = text.strip()
    if not text:
        return None, "empty_conclusion"
    last, pick = -1, None
    for m in LETTER_RE.finditer(text):
        last, pick = m.start(), m.group(1).upper()
    for w, ch in WORDS:
        k = text.rfind(w)
        if k > last:
            last, pick = k, ch
    if last < 0:
        return None, "no_marker"
    return pick, "ok"


def old_prompt(prev, user):
    return f"{OLD_P1}\n上一轮: {prev[:160]}\n用户: {user[:120]}\n只输出一个字母。"


def post(path, body, timeout=1800):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def start():
    global PROC
    args = [BIN, "-m", MODEL, "--host", "127.0.0.1", "--port", str(PORT), "-c", "4608", "-t", "1",
            "-np", "1", "--cache-type-k", "f32", "--cache-type-v", "f32",
            "--flash-attn", "off", "--jinja"]
    print("[start]", " ".join(args), flush=True)
    PROC = subprocess.Popen(args, stdout=LOG, stderr=subprocess.STDOUT)
    for _ in range(180):
        try:
            with urllib.request.urlopen(BASE + "/health", timeout=2) as r:
                if r.status == 200:
                    print("[ready]", flush=True)
                    return True
        except Exception:
            time.sleep(1)
    return False


def stop():
    try:
        PROC.send_signal(signal.SIGTERM); PROC.wait(timeout=20)
    except Exception:
        try: PROC.kill()
        except Exception: pass


def gen(prompt, n_predict):
    turns = [{"role": "system", "content": SYS}, {"role": "user", "content": prompt}]
    rendered = post("/apply-template", {"messages": turns, "add_generation_prompt": True})["prompt"]
    body = {"prompt": rendered, "n_predict": n_predict, "temperature": 0.0,
            "samplers": ["temperature"], "cache_prompt": False, "stream": False,
            "return_tokens": True, "seed": 0}
    t0 = time.time()
    r = post("/completion", body)
    return r, round(time.time() - t0, 2), len(rendered)


def main():
    cases = [json.loads(l) for l in (OUT / "judge-prompt-golden.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"[cases] {len(cases)} (golden prompt 由产品单测落盘)", flush=True)
    if not start():
        print("[致命] 服务未就绪"); sys.exit(4)
    arms = [("A1", "new", 1024), ("A0", "old", 512), ("A2", "new", 512), ("A3", "old", 1024)]
    t_start = time.time()
    results = {}
    try:
        for arm, kind, npred in arms:
            if time.time() - t_start > BUDGET_S:
                print(f"[skip] {arm} 超出预算 {BUDGET_S}s", flush=True); break
            recs = []
            for c in cases:
                prompt = c["prompt"] if kind == "new" else old_prompt(c["prev"], c["user"])
                r, wall, rlen = gen(prompt, npred)
                raw = r.get("content", "")
                t = r.get("timings", {}) or {}
                lo, ro = parse_old(raw)
                ln, rn = parse_new(raw)
                truth = TRUTH.get(c["case"])
                rec = {"case": c["case"], "arm": arm, "prompt_kind": kind, "n_predict": npred,
                       "prompt_len": len(prompt), "rendered_len": rlen, "raw": raw, "raw_len": len(raw),
                       "predicted_n": t.get("predicted_n"), "stop_type": r.get("stop_type"),
                       "wall_s": wall, "has_close": THINK_CLOSE in raw,
                       "old_letter": lo, "old_reason": ro, "new_letter": ln, "new_reason": rn,
                       "truth": truth,
                       "old_ok": ro == "ok", "new_ok": rn == "ok",
                       "old_correct": lo == truth, "new_correct": ln == truth}
                recs.append(rec)
                print(f"[{arm}/{c['case']}] L={len(prompt)} pred={rec['predicted_n']} stop={rec['stop_type']} "
                      f"close={rec['has_close']} old={lo}/{ro} new={ln}/{rn} truth={truth} wall={wall}s", flush=True)
            results[arm] = recs
            okn = sum(1 for x in recs if x["new_ok"]); cor = sum(1 for x in recs if x["new_correct"])
            oko = sum(1 for x in recs if x["old_ok"])
            print(f"[{arm} 汇总] 解析 ok(旧解析)={oko}/{len(recs)} ok(新解析)={okn}/{len(recs)} 语义正确(新解析)={cor}/{len(recs)}", flush=True)
    finally:
        stop()

    summary = {}
    for arm, recs in results.items():
        summary[arm] = {
            "prompt_kind": recs[0]["prompt_kind"], "n_predict": recs[0]["n_predict"], "n": len(recs),
            "parse_ok_oldparser": sum(1 for x in recs if x["old_ok"]),
            "parse_ok_newparser": sum(1 for x in recs if x["new_ok"]),
            "semantic_ok_newparser": sum(1 for x in recs if x["new_correct"]),
            "semantic_ok_oldparser": sum(1 for x in recs if x["old_correct"]),
            "reasons_new": sorted({x["new_reason"] for x in recs}),
            "letters_new": {x["case"]: x["new_letter"] for x in recs},
        }
    doc = {"probe": "R435 fix arms: prompt-shape x budget x parser", "model": MODEL, "bin": BIN,
           "truth_table": TRUTH, "arms": results, "summary": summary}
    (OUT / "probe-j2-arms.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[done] summary =", json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
