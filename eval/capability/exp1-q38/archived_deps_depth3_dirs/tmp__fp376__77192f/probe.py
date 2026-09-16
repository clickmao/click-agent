import json, os, re, socket, subprocess, sys, threading, time

ROOT = "/home/agentuser/AgentFramework"
PORT = 48711
OUT = "/tmp/fp376/report.txt"
TEL = ROOT + "/data/telemetry/host.jsonl"
BIN = "/tmp/pub_r376/agenthost"
lines_out = []


def log(s):
    print(s, flush=True)
    lines_out.append(s)


ENV = dict(os.environ)
ENV["PATH"] = os.path.expanduser("~/.dotnet") + ":" + ENV["PATH"]
envf = ROOT + "/.env.local"
if os.path.exists(envf):
    for raw in open(envf, encoding="utf-8"):
        raw = raw.strip()
        if raw and not raw.startswith("#") and "=" in raw:
            k, v = raw.split("=", 1)
            ENV[k] = v.strip().strip('"').strip("'")

if not os.path.exists(BIN):
    log("!! AOT 二进制缺失: " + BIN)
    sys.exit(2)

tel_before = sum(1 for _ in open(TEL, encoding="utf-8-sig", errors="replace")) if os.path.exists(TEL) else 0
p = subprocess.Popen([BIN, "--frontend-api", str(PORT)], cwd=ROOT,
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=ENV)

token = None
ready = threading.Event()


def reader():
    global token
    for line in p.stdout:
        l = line.rstrip()
        if l:
            log("[host] " + l)
        m = re.search(r"AUTH token = ([0-9a-fA-F]+)", l)
        if m:
            token = m.group(1)
        if "READY" in l:
            ready.set()


threading.Thread(target=reader, daemon=True).start()
ready.wait(120)
_d = time.time() + 25
while token is None and time.time() < _d:
    time.sleep(0.2)
if token is None:
    log("!! 未取到 token"); p.terminate(); sys.exit(2)
log("token acquired, host ready")

s = socket.create_connection(("127.0.0.1", PORT), timeout=20)
s.settimeout(30)
f = s.makefile("rwb")


def send_raw(text):
    f.write(text.encode()); f.flush()


def send(obj):
    send_raw(json.dumps(obj, ensure_ascii=False) + chr(10))


def read_line():
    raw = f.readline()
    return raw.decode().strip() if raw else None


# ============ H: 握手残包修复 (auth 与首个请求同一次 write, 无 sleep) ============
log("--- H 真机握手残包: auth + 首个请求合并为一次写入 (无 sleep 绕行) ---")
send_raw(json.dumps({"type": "auth", "token": token}, ensure_ascii=False) + chr(10)
         + json.dumps({"v": 1, "type": "req", "req_id": "h1", "api": "meta.ping", "payload": {}}, ensure_ascii=False) + chr(10))
h_ok, h_seen = False, None
t0 = time.time()
while time.time() - t0 < 8:
    line = read_line()
    if line is None:
        log("连接关闭 (修复失败?)"); break
    log("[client<-] " + line[:200])
    try:
        o = json.loads(line)
    except Exception:
        continue
    if o.get("type") == "resp" and o.get("req_id") == "h1":
        h_ok = bool(o.get("ok")); h_seen = o; break
log("H 同段握手+请求 -> 收到响应 = %s (ok=%s)" % (h_seen is not None, h_ok))


def req(rid, api, payload):
    send({"v": 1, "type": "req", "req_id": rid, "api": api, "payload": payload})
    for _ in range(30):
        line = read_line()
        if line is None:
            return None
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("type") == "resp" and o.get("req_id") == rid:
            return o
    return None


# ============ P1: 随机 id 拒绝仍成立 ============
r = req("p1", "ask.reply", {"ask_id": "ask-forged376"})
log("P1 伪造 ask_id -> " + json.dumps((r or {}).get("payload"), ensure_ascii=False))

# ============ P2': 真机 E2E 闭环 (vague prompt → ask 事件 → ask.reply → 续跑) ============
VAGUE = "帮我看下这个"
log("--- P2' 真机 E2E: 低置信触发 (text=%s, 含指代词+General -> conf 0.55 < 0.60) ---" % VAGUE)
send({"v": 1, "type": "req", "req_id": "c1", "api": "chat.send", "payload": {"text": VAGUE}})
s.settimeout(200)
ask, closed, final, replied = None, None, None, False
t0 = time.time()
while time.time() - t0 < 220:
    line = read_line()
    if line is None:
        log("连接关闭"); break
    log("[client<-] " + line[:500])
    try:
        o = json.loads(line)
    except Exception:
        continue
    if o.get("type") == "event" and o.get("event") == "ask" and ask is None:
        ask = o
        pl = o.get("payload", {})
        qs = pl.get("questions") or []
        log("  >>> ask 事件: ask_id=%s service=%s timeout_s=%s questions=%d" % (
            pl.get("ask_id"), pl.get("service"), pl.get("timeout_s"), len(qs)))
        for q in qs:
            opts = q.get("options") or []
            log("      Q: %s | data_type=%s multi=%s options=%d %s" % (
                (q.get("key") or q.get("parameter_name") or "")[:40], q.get("data_type"),
                q.get("multi_select"), len(opts), [x.get("value") for x in opts][:6]))
        # 用事件里给出的第一个选项回复 (真机闭环: 选择回填 → 续跑)
        pick = None
        for q in qs:
            for x in (q.get("options") or []):
                pick = x.get("value"); break
            if pick: break
        if pick is None:
            pick = "读文件"
        log("  >>> ask.reply 选择 = %s" % pick)
        # 契约: answers 是对象映射 {key: value} (见 FrontendAskFlowTests:170-176)
        key0 = (qs[0].get("key") if qs else None) or "q"
        send({"v": 1, "type": "req", "req_id": "a1", "api": "ask.reply",
              "payload": {"ask_id": pl.get("ask_id"), "answers": {key0: pick}}})
        replied = True
    elif o.get("type") == "event" and o.get("event") == "ask_closed":
        closed = o
    elif o.get("type") == "resp" and o.get("req_id") == "c1":
        final = o
        break
    elif o.get("type") == "resp" and o.get("req_id") == "a1":
        log("  >>> ask.reply 响应: ok=%s payload=%s" % (o.get("ok"), json.dumps(o.get("payload"), ensure_ascii=False)[:160]))

log("P2' 结果: ask_事件=%s replied=%s ask_closed=%s chat.send_响应=%s" % (
    ask is not None, replied, json.dumps((closed or {}).get("payload"), ensure_ascii=False),
    (final or {}).get("ok")))
if final:
    body = json.dumps(final.get("payload"), ensure_ascii=False)
    log("  chat.send payload 摘要: " + body[:400])

# ============ 遥测: evidence_gate 触发 + 续跑证据 ============
time.sleep(1.5)
new = []
try:
    with open(TEL, encoding="utf-8-sig", errors="replace") as fh:
        for i, l in enumerate(fh):
            if i >= tel_before and l.strip().startswith("{"):
                new.append(json.loads(l))
except Exception as e:
    log("遥测读取失败: %r" % (e,))
pts = {}
for e in new:
    pts.setdefault(e.get("point"), []).append(e)
log("--- 遥测 (本轮新增 %d 行) ---" % len(new))
for g in pts.get("evidence_gate", []):
    log("  evidence_gate: " + json.dumps(g.get("kv"), ensure_ascii=False))
for c in pts.get("llm_call", []):
    kv = c.get("kv", {})
    log("  llm_call: model=%s tokens=%s truncated=%s" % (kv.get("model"), kv.get("total_tokens"), kv.get("truncated")))
for a in pts.get("script_artifact", []):
    log("  script_artifact: " + json.dumps(a.get("kv"), ensure_ascii=False)[:160])
log("  点分布: " + json.dumps({k: len(v) for k, v in pts.items()}, ensure_ascii=False))

ans = "PASS" if (h_ok and ask is not None and replied) else "FAIL"
log("=== R376 判定: %s (H同段握手=%s / P2' ask闭环=%s) ===" % (ans, h_ok, ask is not None))

try:
    s.close()
except Exception:
    pass
p.terminate()
time.sleep(1)
os.makedirs("/tmp/fp376", exist_ok=True)
open(OUT, "w", encoding="utf-8").write(chr(10).join(lines_out))
log("报告已写 " + OUT)
