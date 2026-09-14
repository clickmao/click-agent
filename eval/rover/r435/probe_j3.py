#!/usr/bin/env python3
"""R435 臂 A4 —— 判官 prompt v2 (同族实例, **不含 grid 原句**) @512 (产品档)。

科学纪律:
  * 归因已在 probe_j2 完成 (A0 旧@512=1/7 与产品逐例一致 ⇒ 器具可信; A2 新v1@512=6/7 解析但语义 3/7)。
  * 本轮只测**一个**变量: prompt 文本 v1 → v2。预算回到产品档 512 (A1==A2 已证 512 足够)。
  * 训练/测试分离: v2 的示例是**同族不同实例** (详细说说。/ 换一种说法。), 与 grid 原句
    (再讲一遍。/ 讲细一点。/ 换个说法。/ 从头再说。) 不重合 —— 否则就是「教到考卷上」。
  * 基线复用 A0/A2 (同器具同参数, 且 A0 经产品遥测逐例钉证 = 可跨次比较)。
"""
import json, os, pathlib, re, subprocess, sys, time, urllib.request

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
OUT = ROOT / "eval/rover/r435"
BIN = os.environ.get("R435_LLAMA_SERVER",
                     "/tmp/pipprobe/llama_cpp_python-0.3.35/vendor/llama.cpp/build/bin/llama-server")
MODEL = "/tmp/models/r1-distill-qwen-1.5b-q4km.gguf"
PORT = 8135
BASE = f"http://127.0.0.1:{PORT}"
SYS = "只输出一个字母。"
NPRED = 512

SRC = ROOT / "src/agent.modelqueue/LocalGenerationPort.cs"


def markers():
    s = SRC.read_text(encoding="utf-8")
    def grab(n):
        m = re.search(n + r'\s*=\s*"((?:[^"\\]|\\.)*)"', s)
        v = re.sub(r"\\u([0-9a-fA-F]{4})", lambda mm: chr(int(mm.group(1), 16)), m.group(1))
        return v
    return grab("ThinkOpen"), grab("ThinkClose")


OPEN, CLOSE = markers()
assert (OPEN, CLOSE) == ("<think>", "</think>"), (repr(OPEN), repr(CLOSE))
LETTER_RE = re.compile(r"(?<![A-Za-z])([CcAaNn])(?![A-Za-z])")
WORDS = (("纠正", "C"), ("否定", "C"), ("认可", "A"), ("采纳", "A"), ("新话题", "N"), ("无关", "N"))
TRUTH = {"turn1": "N", "turn3": "N", "turn5": "N", "turn6": "A", "turn7": "N",
         "turn8": "A", "turn9": "N", "syn-c": "C", "syn-a": "A"}


def parse(raw):
    text = (raw or "").strip()
    if not text:
        return None, "empty"
    c = text.rfind(CLOSE)
    if c >= 0:
        concl, st = text[c + len(CLOSE):], "closed"
    elif text.rfind(OPEN) >= 0:
        return None, "thinking_truncated"
    else:
        concl, st = text, "no_markers"
        if len(concl) > 64:
            concl = concl[-64:]
    t = concl.strip()
    if not t:
        return None, "empty_conclusion"
    pos, pick = -1, None
    for m in LETTER_RE.finditer(t):
        pos, pick = m.start(), m.group(1).upper()
    for w, ch in WORDS:
        k = t.rfind(w)
        if k > pos:
            pos, pick = k, ch
    return (pick, "ok") if pos >= 0 else (None, "no_marker")


def v2_prompt(prev, user):
    """与 CorrectionDetector.BuildJudgePrompt v2 **逐字同形** (由 dump 探针校验长度/内容)。"""
    def trunc(s, n):
        return s[:n] if len(s) > n else s
    return ("判定用户消息相对上一轮回答: 纠正否定上一轮=C, 认可采纳=A, 新话题无关=N。\n"
            "- C = 指出上一轮错了/不对/不准确, 要求改 (如: 好像不太对。)。\n"
            "- A = 只是认可/确认/致谢, 没有提出任何新要求 (如: 嗯，知道了。 / 好，就这样。)。\n"
            "- N = 提出新要求, 或要求重复/细化/换说法, 既没认可也没纠正 (如: 详细说说。 / 换一种说法。)。\n"
            "先思考, 思考结束后必须另起一行只写一个字母 (C 或 A 或 N), 不要写其他内容。\n"
            "无法确定时也必须写 N。\n"
            f"上一轮: {trunc(prev, 160)}\n用户: {trunc(user, 120)}\n答案:\n")


def post(path, body):
    r = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=900).read().decode())


def main():
    cases = [json.loads(l) for l in (OUT / "judge-prompt-golden.jsonl")
             .read_text(encoding="utf-8").strip().splitlines() if l.strip()]
    log = open("/tmp/r435c_server.log", "w")
    srv = subprocess.Popen([BIN, "-m", MODEL, "--host", "127.0.0.1", "--port", str(PORT),
                            "-c", "4608", "-t", "1", "-np", "1", "--jinja",
                            "--cache-type-k", "f32", "--cache-type-v", "f32", "--flash-attn", "off"],
                           stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(120):
            try:
                urllib.request.urlopen(BASE + "/health", timeout=2).read()
                break
            except Exception:
                time.sleep(1)
        else:
            sys.exit("[致命] llama-server 未就绪")
        recs = []
        for c in cases:
            p = v2_prompt(c["prev"], c["user"])
            rendered = post("/apply-template", {"messages": [{"role": "system", "content": SYS},
                                                             {"role": "user", "content": p}]})["prompt"]
            t0 = time.time()
            r = post("/completion", {"prompt": rendered, "n_predict": NPRED, "temperature": 0.0,
                                     "seed": 0, "cache_prompt": False, "samplers": ["temperature"]})
            wall = round(time.time() - t0, 2)
            raw = r.get("content", "")
            letter, reason = parse(raw)
            truth = TRUTH[c["case"]]
            recs.append({"case": c["case"], "prompt_kind": "v2", "n_predict": NPRED,
                         "prompt_len": len(p), "rendered_len": len(rendered),
                         "predicted_n": r.get("tokens_predicted"), "stop_type": r.get("stop_type"),
                         "wall_s": wall, "truth": truth, "parsed_letter": letter,
                         "parse_reason": reason, "raw": raw,
                         "closed": CLOSE in raw, "raw_len": len(raw)})
            print(f"[A4/{c['case']}] L={len(p)} pred={r.get('tokens_predicted')} stop={r.get('stop_type')} "
                  f"close={CLOSE in raw} parse={letter}/{reason} truth={truth} "
                  f"{'✓' if letter == truth else '✗'} wall={wall}s")
        real = [x for x in recs if not x["case"].startswith("syn")]
        ok = sum(1 for x in recs if x["parse_reason"] == "ok")
        sem = sum(1 for x in real if x["parsed_letter"] == x["truth"])
        print(f"[A4 汇总] 解析 ok={ok}/9  real7={sum(1 for x in real if x['parse_reason']=='ok')}/7  "
              f"语义正确 real7={sem}/7  letters={ {x['case']: x['parsed_letter'] for x in recs} }")
        (OUT / "probe-j3-arms.json").write_text(json.dumps(
            {"arms": {"A4": recs}}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[done] ->", OUT / "probe-j3-arms.json")
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=20)
        except Exception:
            srv.kill()


if __name__ == "__main__":
    main()
