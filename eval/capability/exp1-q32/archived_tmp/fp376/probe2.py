import datetime, io, json, os, socket, subprocess, sys, time

ROOT = "/home/agentuser/AgentFramework"
PORT = 48723
BIN = "/tmp/pub_r376/agenthost"
TS0 = "1970-01-01T00:00:00"
TEL = ROOT + "/data/telemetry/host.jsonl"
OUT = "/tmp/fp376/report2.txt"

LOGS = []


def log(m):
    print(m, flush=True)
    LOGS.append(str(m))


def tel_lines():
    try:
        with open(TEL, "rb") as f:
            f.seek(0, 2)
            return f.tell()
    except Exception:
        return 0


def tel_all_since_ts(ts0):
    """R376: 遥测按时间戳过滤 (字节偏移在本 host 上不可靠: 启动期会改写文件)。"""
    rows = []
    try:
        with open(TEL, "rb") as f:
            data = f.read().decode("utf-8-sig", "replace")
        for l in data.splitlines():
            l = l.strip()
            if not l.startswith("{"):
                continue
            try:
                o = json.loads(l)
            except Exception:
                continue
            if str(o.get("ts", "")) >= ts0:
                rows.append(o)
    except Exception:
        pass
    return rows


def tel_since(off):
    rows = []
    try:
        with open(TEL, "rb") as f:
            f.seek(off)
            data = f.read().decode("utf-8-sig", "replace")
        for l in data.splitlines():
            l = l.strip()
            if not l.startswith("{"):
                continue
            try:
                rows.append(json.loads(l))
            except Exception:
                pass
    except Exception:
        pass
    return rows


class Conn:
    def __init__(self, port, token):
        self.s = socket.create_connection(("127.0.0.1", port), timeout=10)
        self.s.settimeout(20)
        self.buf = b""
        self.token = token

    def send_raw(self, text):
        self.s.sendall(text.encode("utf-8"))

    def req(self, api, payload, req_id):
        self.send_raw(json.dumps({"v": 1, "type": "req", "req_id": req_id,
                                  "api": api, "payload": payload},
                                 ensure_ascii=False, separators=(",", ":")) + "\n")

    def read_line(self, deadline):
        """返回一行 (str) 或 None(超时/断开)。按字节收行再整体 UTF-8 解码。"""
        while True:
            nl = self.buf.find(b"\n")
            if nl >= 0:
                line = self.buf[:nl]
                self.buf = self.buf[nl + 1:]
                return line.decode("utf-8", "replace")
            if time.time() > deadline:
                return None
            try:
                self.s.settimeout(15)
                chunk = self.s.recv(65536)
            except socket.timeout:
                continue
            except OSError:
                return None
            if not chunk:
                return None
            self.buf += chunk


def load_env():
    """R376 探针 env 卫生: 真机段必须带 .env.local (R374 教训: 缺 key → 空正文被误读成产品缺陷)。"""
    env = dict(os.environ)
    path = os.path.join(ROOT, ".env.local")
    if os.path.exists(path):
        for l in io.open(path, encoding="utf-8"):
            l = l.strip()
            if not l or l.startswith("#") or "=" not in l:
                continue
            k, v = l.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def main():
    os.makedirs("/tmp/fp376", exist_ok=True)
    env = load_env()
    if "AGENTFRAMEWORK_KEYS_DEEPSEEK" not in env:
        log("!! 警告: .env.local 未提供 AGENTFRAMEWORK_KEYS_DEEPSEEK → 续跑必然空正文")
    off = tel_lines()
    off = 0  # host 启动会新建/轮转遥测文件, 统一启动后再取偏移
    log("=== R376 真机 E2E: 同一连接内 ask 闭环 (auth+首请求合并写入)")
    p = subprocess.Popen([BIN, "--frontend-api", str(PORT)],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         cwd=ROOT, text=True, bufsize=1, env=env)
    token = None
    t0 = time.time()
    while time.time() - t0 < 60:
        ln = p.stdout.readline()
        if not ln:
            break
        if "AUTH token" in ln:
            token = ln.split("AUTH token =", 1)[1].strip().split(" ")[0]
            break
    global TS0
    TS0 = (datetime.datetime.utcnow() - datetime.timedelta(seconds=120)).strftime("%Y-%m-%dT%H:%M:%S")
    log("  host token 就绪: %s (TS0=%s)" % ("是" if token else "否(超时)", TS0))
    time.sleep(0.5)
    off = tel_lines()  # 启动写入后再取偏移 (否则读到旧尾部)
    if not token:
        log("VERDICT: FAIL(no token)")
        p.terminate()
        return

    c = Conn(PORT, token)
    # ⑪: auth 与首个请求合并成一次写入 (同一 TCP 段) —— 修复前首请求被吞
    body = json.dumps({"v": 1, "type": "req", "req_id": "c1", "api": "chat.send",
                       "payload": {"text": "帮我看下这个", "session_id": "r376-e2e"}},
                      ensure_ascii=False, separators=(",", ":"))
    c.send_raw(json.dumps({"type": "auth", "token": token}) + "\n" + body + "\n")
    log("  已单次写入: auth + chat.send(req=c1)\n  提示词=帮我看下这个 (配方: 指代不明+通用意图 → 0.55 < 0.60)")

    deadline = time.time() + 420
    ask = None
    replied = False
    done = None
    closed = None
    a1 = None
    while time.time() < deadline:
        ln = c.read_line(deadline)
        if ln is None:
            log("  (读超时/断开)")
            break
        try:
            o = json.loads(ln)
        except Exception:
            continue
        ty = o.get("type")
        if ty == "req" or ty == "event":
            pass
        if ty == "event" and o.get("event") == "ask":
            ask = o
            pl = o.get("payload") or {}
            qs = pl.get("questions") or []
            log("  <<< ask 事件 ask_id=%s timeout_s=%s service=%s questions=%d"
                % (pl.get("ask_id"), pl.get("timeout_s"), pl.get("service"), len(qs)))
            for q in qs:
                opts = q.get("options") or []
                log("      q.key=%s data_type=%s default=%s options=%d %s"
                    % (q.get("key"), q.get("data_type"), q.get("default_value"),
                       len(opts), [x.get("label") for x in opts]))
            if not replied and qs:
                key0 = qs[0].get("key") or "q"
                opts = qs[0].get("options") or []
                pick = (opts[0].get("value") if opts else "读文件")
                c.req("ask.reply", {"ask_id": pl.get("ask_id"), "answers": {key0: pick}}, "a1")
                replied = True
                log("  >>> ask.reply key=%s value=%s" % (key0, pick))
        elif ty == "resp" and o.get("req_id") == "a1":
            a1 = o
            log("  <<< resp(a1) ok=%s payload=%s"
                % (o.get("ok"), json.dumps(o.get("payload"), ensure_ascii=False)[:160]))
        elif ty == "event" and o.get("event") == "ask_closed":
            closed = o
            log("  <<< ask_closed reason=%s"
                % ((o.get("payload") or {}).get("reason")))
        elif ty == "resp" and o.get("req_id") == "c1":
            done = o
            log("  <<< resp(c1) ok=%s payload=%s"
                % (o.get("ok"), json.dumps(o.get("payload"), ensure_ascii=False)[:300]))
            break

    rows = tel_all_since_ts(TS0)
    gate = [r for r in rows if r.get("point") == "evidence_gate"]
    calls = [r for r in rows if r.get("point") == "llm_call"]
    summ = [r for r in rows if r.get("point") == "loop_turn"]
    for sm in summ:
        log("      run_summary=%s" % json.dumps(sm.get("kv"), ensure_ascii=False)[:200])
    log("  telemetry: evidence_gate=%d llm_call=%d"
        % (len(gate), len(calls)))
    for g in gate:
        log("      gate=%s" % json.dumps(g.get("kv"), ensure_ascii=False))
    for cl in calls:
        kv = cl.get("kv") or {}
        log("      llm_call tokens=%s ms=%s origin=%s"
            % (kv.get("tokens"), kv.get("ms"), kv.get("origin")))

    ok_ask = ask is not None and len((ask.get("payload") or {}).get("questions") or []) >= 1
    ok_reply = (a1 or {}).get("ok") is True and ((a1 or {}).get("payload") or {}).get("outcome") == "answered"
    ok_cont = done is not None and done.get("ok") is True
    ok_gate = len([g for g in gate if (g.get("kv") or {}).get("to_ask")]) >= 1
    log("VERDICT: P2' ask_event=%s reply=%s continue=%s gate_to_ask=%s"
        % (ok_ask, ok_reply, ok_cont, ok_gate))
    log("  P2 结论: %s" % ("菜单式问询在真机上完成闭环 (ask→reply→续跑)" if (ok_ask and ok_reply and ok_cont)
                          else "未闭环 (见上)"))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(LOGS) + "\n")
    p.terminate()
    try:
        p.wait(timeout=10)
    except Exception:
        p.kill()
    log("报告: " + OUT)
    log("RESULT_JSON: " + json.dumps({"ask": ok_ask, "reply": ok_reply, "continue": ok_cont,
                                      "gate": ok_gate, "calls": len(calls)},
                                     ensure_ascii=False))


main()
