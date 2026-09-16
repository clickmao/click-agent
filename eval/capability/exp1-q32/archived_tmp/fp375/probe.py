
import json, os, re, socket, subprocess, sys, threading, time, glob
ROOT = "/home/agentuser/AgentFramework"
PORT = 48637
OUT = "/tmp/fp375/report.txt"
lines_out = []
def log(s):
    print(s, flush=True); lines_out.append(s)

ENV = dict(os.environ); ENV["PATH"] = os.path.expanduser("~/.dotnet") + ":" + ENV["PATH"]
envf = ROOT + "/.env.local"
if os.path.exists(envf):
    for raw in open(envf, encoding="utf-8"):
        raw = raw.strip()
        if raw and not raw.startswith("#") and "=" in raw:
            k, v = raw.split("=", 1); ENV[k] = v.strip().strip('"').strip("'")

dlls = glob.glob(ROOT + "/src/agent.host/bin/Release/net10.0/agenthost.dll")
if not dlls:
    dlls = glob.glob(ROOT + "/src/agent.host/bin/Release/net10.0/*host*.dll")
log("host dll = " + str(dlls))
p = subprocess.Popen(["dotnet", dlls[0], "--frontend-api", str(PORT)], cwd=ROOT,
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
        if m: token = m.group(1)
        if "READY" in l: ready.set()
t = threading.Thread(target=reader, daemon=True); t.start()
ready.wait(120)
_deadline = time.time() + 25
while token is None and time.time() < _deadline:
    time.sleep(0.2)  # READY 行早于 token 行打印 → 等 reader 线程补齐
if token is None:
    log("!! 未取到 token (host 未就绪?)"); p.terminate(); sys.exit(2)
log("token acquired, ready")

s = socket.create_connection(("127.0.0.1", PORT), timeout=20)
s.settimeout(20)
f = s.makefile("rwb")
def send(obj):
    f.write((json.dumps(obj, ensure_ascii=False) + chr(10)).encode()); f.flush()
def read_until_resp(req_id=None, max_lines=25):
    for _ in range(max_lines):
        raw = f.readline()
        if not raw: return None
        line = raw.decode().strip()
        if not line: continue
        log("[client<-] " + line[:220])
        try: o = json.loads(line)
        except Exception: continue
        if o.get("type") == "resp" and (req_id is None or o.get("req_id") == req_id):
            return o
    return None

send({"type": "auth", "token": token})
time.sleep(0.8)  # 握手单次读取会吞掉同批字节 (已记为发现项) → 等握手读完再发请求
def req(rid, api, payload):
    send({"v":1,"type":"req","req_id":rid,"api":api,"payload":payload})
    return read_until_resp(rid)

log("--- P1 确定性: 真机接线证据 ---")
r = req("p1", "meta.ping", {})
log("P1.1 meta.ping ok=" + str((r or {}).get("ok")))
r = req("p2", "ask.reply", {"ask_id": "ask-forged0"})
log("P1.2 伪造 ask_id 回复 -> " + json.dumps((r or {}).get("payload"), ensure_ascii=False))
r = req("p3", "ask.cancel", {"ask_id": "ask-forged1"})
log("P1.3 伪造 ask_id 取消 -> " + json.dumps((r or {}).get("payload"), ensure_ascii=False))
r = req("p4", "ask.reply", {})
log("P1.4 空 envelope -> error=" + json.dumps((r or {}).get("error"), ensure_ascii=False))
r = req("p5", "state.snapshot", {})
log("P1.5 state.snapshot ok=" + str((r or {}).get("ok")))

log("--- P2 真机: chat.send 抢真实 ask 事件 (最多 150s) ---")
send({"v":1,"type":"req","req_id":"c1","api":"chat.send",
      "payload":{"text":"帮我把当前项目推送到 GitHub 仓库 clickmao/click-agent（需要凭据时请直接问我）"}})
s.settimeout(150)
ask_seen = []
t0 = time.time()
done = False
while time.time() - t0 < 150 and not done:
    try:
        raw = f.readline()
    except Exception as e:
        log("读超时/异常: %r" % (e,)); break
    if not raw:
        log("连接关闭"); break
    line = raw.decode().strip()
    if not line: continue
    log("[client<-] " + line[:400])
    try: o = json.loads(line)
    except Exception: continue
    if o.get("type") == "event" and o.get("event") in ("ask", "ask_closed"):
        ask_seen.append(o)
    if o.get("type") == "resp" and o.get("req_id") == "c1":
        done = True
log("P2 ask 事件数 = %d ; chat.send 响应已收 = %s" % (len(ask_seen), done))
for a in ask_seen:
    pl = a.get("payload", {})
    qs = pl.get("questions") or []
    log("  ask payload: ask_id=%s service=%s timeout_s=%s questions=%d options=%s" % (
        pl.get("ask_id"), pl.get("service"), pl.get("timeout_s"), len(qs),
        [len(q.get("options") or []) for q in qs]))

try: s.close()
except Exception: pass
p.terminate()
time.sleep(1)
open(OUT, "w", encoding="utf-8").write(chr(10).join(lines_out))
log("报告已写 " + OUT)
