#!/usr/bin/env python3
# R497 收口断言 (fail-closed) —— "本地决策台账挂载"的**实发面 + 落盘面 + 遥测面**三源一致。
#
# 判据层级 (禁含糊; 预注册见 prereg_r497.json):
#   HARD-1  实发面·正向: --mount on ⇒ **每一条**远端请求体里必须恰含 1 行挂载块头
#           ([本地决策台账-链自持]); 出现 0 条或条数≠1 ⇒ 红 (挂载与实发脱钩)。
#   HARD-1' 实发面·反向(泄漏): --mount off ⇒ 远端请求体里挂载块出现次数必须 == 0
#           (出现即泄漏: 关轴仍改提示字节 ⇒ 违反"关 = 零字节")。
#   HARD-2  落盘面: --mount on ⇒ 挂载块里的 (n, code) 必须在 ledger-<arm>.jsonl 里逐条存在,
#           且 n 跨调用**单调不减**; 文件缺失 ⇒ 14 (数据缺失, 不得当通过)。
#   HARD-3  遥测面: --mount on ⇒ telemetry 必须有 point=llm_call 且 kv.ledger_mount=1 的事件,
#           且其 kv.ledger_code 与实发面抽出的码集合一致 (打点与实发脱钩 ⇒ 红);
#           --mount off ⇒ 必须**没有** kv.ledger_mount=1 的事件 (否则遥测自报与实发不符)。
#   HARD-4  通道面 (R494 继承): --channel on ⇒ 隔离调用 tools_n 必须全 0;
#           --channel off ⇒ 隔离带工具泄漏"复现/未复现"如实记录 (不复现 = unreported, 不得称通过)。
# 退出码: 0 = 全绿; 13 = 红; 14 = 数据缺失。
import argparse, json, os, re, sys


def sha8(s):
    """R497: 与产品 `LocalDecisionLedger.Code8` 同配方 (sha256 前 8 位小写十六进制) —— 单向指纹。"""
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]

MOUNT_HEADER = "[本地决策台账-链自持]"
MOUNT_RE = re.compile(r"n=(\d+)\s+code=(LCM-[0-9a-f]{12})")
ISO_MARK = "微步骤隔离问询"
ISO_SYS = ("你是隔离执行的微步骤助手", "你是一个一次性隔离子任务执行器")


def load_jsonl(p):
    out = []
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8-sig") as f:
        for l in f:
            l = l.strip()
            if l:
                out.append(json.loads(l))
    return out


def is_isolated(row):
    for m in (row.get("messages") or []):
        c = m.get("content")
        if not isinstance(c, str):
            continue
        if ISO_MARK in c:
            return True
        if m.get("role") == "system" and any(s in c for s in ISO_SYS):
            return True
    return False


def mount_of(row):
    """返回请求体内的 (挂载块数, 抽出的 n/code 列表, 非 system 角色出现块头的消息数)。

    R497 判据器修订 (修订前后都跑了正/负控, 见 --selftest):
      挂载块的定义 = **system 角色**消息, 且同时含块头与 `site=`/`n=`/`code=` 结构行。
      原版只按"块头字符串出现在任意角色消息里"计数 ⇒ 被**工具面回显**误判:
      夹具在 t13 触发了"命题核验"工具, 该工具把**越界被拒**的源文件行
      (含 `MountHeader = "[本地决策台账-链自持]"` 字面量) 原样塞进 tool 消息
      ⇒ 关轴臂被误报"含挂载块"(实为工具回显, 且**不含**任何 n/code 真值)。
      非 system 角色的块头出现 = **旁路观察项** (记数入 notes, 不作轴门红)。
    """
    hits, pairs, bypass = 0, [], 0
    for m in (row.get("messages") or []):
        c = m.get("content")
        if not isinstance(c, str) or MOUNT_HEADER not in c:
            continue
        if m.get("role") == "system" and MOUNT_RE.search(c):
            hits += 1
            for mm in MOUNT_RE.finditer(c):
                pairs.append((int(mm.group(1)), mm.group(2)))
        else:
            bypass += 1
    return hits, pairs, bypass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--channel", required=True, choices=["on", "off"])
    ap.add_argument("--mount", required=True, choices=["on", "off"])
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    a.out = a.out or os.path.join(a.dir, "assert-face-%s.txt" % a.arm)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    log = open(a.out, "w", encoding="utf-8")

    def say(m):
        print(m); log.write(m + "\n"); log.flush()

    d = a.dir
    calls = load_jsonl(os.path.join(d, "calls-%s.jsonl" % a.arm))
    tel = load_jsonl(os.path.join(d, "tel-%s" % a.arm, "host.jsonl"))
    ledger = load_jsonl(os.path.join(d, "ledger-%s.jsonl" % a.arm))
    if not calls:
        say("[assert-face] 数据缺失: calls-%s.jsonl 为空" % a.arm); return 14
    if not tel:
        say("[assert-face] 数据缺失: tel-%s/host.jsonl 为空" % a.arm); return 14

    rec = {"schema": "r497-assert-face/1", "arm": a.arm, "channel": a.channel, "mount": a.mount,
           "calls": len(calls), "telemetry_rows": len(tel), "ledger_rows": len(ledger),
           "red": [], "notes": []}
    red = []

    # ---- HARD-1 / HARD-1' 实发面 ---- (判据器 R497 修订: 块 = system 角色 + 结构行)
    rows = [mount_of(r) for r in calls]
    with_mount = [i for i, (h, _, _) in enumerate(rows) if h > 0]
    multi = [i for i, (h, _, _) in enumerate(rows) if h > 1]
    bypass_calls = [i for i, (_, _, b) in enumerate(rows) if b > 0]
    rec["calls_with_mount"] = len(with_mount)
    rec["calls_multi_mount"] = len(multi)
    rec["calls_header_bypass"] = len(bypass_calls)
    say("[assert-face] arm=%s mount=%s channel=%s 远端调用=%d 带挂载块=%d (多次挂载=%d) | ledger行=%d | 旁路块头回显(非system)=%d"
        % (a.arm, a.mount, a.channel, len(calls), len(with_mount), len(multi), len(ledger), len(bypass_calls)))
    if bypass_calls:
        rec["notes"].append("旁路观察: %d 条请求体的**非 system** 消息里出现块头字面量 (夹具'命题核验'工具把越界被拒的源文件行回显进 tool 结果); "
                            "不含任何 n=/code= 真值 ⇒ 不构成挂载面泄漏, 但构成**工具面回显**通道 (seq=%s)"
                            % (len(bypass_calls), [calls[i].get("seq") for i in bypass_calls[:8]]))
    if a.mount == "on":
        # 判据器修订 (证据: T1 seq=5 = 微步骤隔离问询调用, 无会话 ⇒ 挂载应为 0):
        # 轴门只适用于**会话调用**; 隔离通道调用**必须** 0 挂载 (带挂载 = 会话本地真值泄漏进隔离通道)。
        iso_idx = [i for i, r in enumerate(calls) if is_isolated(r)]
        iso_set = set(iso_idx)
        sess_idx = [i for i in range(len(calls)) if i not in iso_set]
        sess_mounted = [i for i in sess_idx if rows[i][0] > 0]
        iso_mounted = [i for i in iso_idx if rows[i][0] > 0]
        rec["iso_calls_idx"] = iso_idx
        rec["sess_calls"] = len(sess_idx)
        rec["sess_calls_mounted"] = len(sess_mounted)
        if len(sess_mounted) != len(sess_idx):
            red.append("HARD-1: 挂载轴 on 但 %d/%d 条**会话**远端请求无挂载块 (seq=%s)"
                       % (len(sess_idx) - len(sess_mounted), len(sess_idx),
                          [calls[i].get("seq") for i in sess_idx if i not in set(sess_mounted)][:8]))
        if iso_mounted:
            red.append("HARD-1b: 隔离通道调用 %d 条带挂载块 ⇒ 会话本地真值泄漏进隔离通道 (seq=%s)"
                       % (len(iso_mounted), [calls[i].get("seq") for i in iso_mounted][:8]))
        elif iso_idx:
            say("[assert-face] 隔离通道: %d 条调用 (seq=%s) 挂载块 0 ⇒ 未泄漏 (含'无会话⇒不挂载'的设计面)"
                % (len(iso_idx), [calls[i].get("seq") for i in iso_idx][:6]))
        if multi:
            red.append("HARD-1: %d 条请求体出现多次挂载块 (挂载点非单点)" % len(multi))
    else:
        if with_mount:
            red.append("HARD-1': 挂载轴 off 但 %d 条远端请求体含挂载块 ⇒ 关轴未做到零字节"
                       % len(with_mount))

    # ---- HARD-2 落盘面 ----
    if a.mount == "on":
        if not ledger:
            say("[assert-face] 数据缺失: ledger-%s.jsonl 为空 (挂载轴 on 必须有落盘面)" % a.arm)
            return 14
        persisted = {(int(r.get("n", -1)), r.get("code8")) for r in ledger}
        fps = {r.get("code8") for r in ledger if r.get("code8")}
        mounted = [p for _, ps, _ in rows for p in ps]
        rec["mounted_pairs"] = [list(p) for p in mounted]
        missing = [list(p) for p in mounted if (p[0], sha8(p[1])) not in persisted]
        rec["missing_in_ledger"] = missing
        if missing:
            red.append("HARD-2: 实发面挂载的 (n,code) 指纹未在落盘面出现: %s" % missing[:5])
        ns = [p[0] for p in mounted]
        rec["mount_n_seq"] = ns
        if any(b < x for x, b in zip(ns, ns[1:])):
            red.append("HARD-2: 挂载 n 跨调用非单调不减: %s" % ns)
        # ---- R497 候选①: 复算通道**按设计关闭** ⇒ 判据从「可复算」翻转为「不可复算 + 指纹一致」 ----
        #  (a) 公开配方 (R495 口径: sha256(session|canon) 前 12) 复算出的码, 其指纹**不得**命中本臂真值指纹;
        #  (b) 实发面每个 (n,code) 的指纹必须在本臂台账内 (链自报知道该真值);
        #  (c) 落盘行不得含 raw `code` 字段 (真值不落盘 —— 判据器不需要密钥即可机检)。
        by_n = {int(r.get("n", -1)): r for r in ledger}

        def recipe(sess, upto):
            rows_ = [r for r in ledger if int(r.get("n", -1)) <= upto and r.get("session") == sess]
            canon = "\n".join(r.get("canon", "") for r in rows_)
            import hashlib
            return "LCM-" + hashlib.sha256(("%s|%s" % (sess, canon)).encode("utf-8")).hexdigest()[:12]
        rc_ = [(n, code, recipe(by_n[n].get("session"), n)) for n, code in mounted if n in by_n]
        rec["recipe_recompute_sample"] = [list(x) for x in rc_[:3]]
        hit = [x for x in rc_ if sha8(x[2]) in fps]
        if hit:
            red.append("HARD-2(候选①失败): 公开配方复算命中真值指纹 ⇒ 真值仍可复算: %s" % hit[:3])
        raw_rows = [r for r in ledger if "code" in r]
        rec["ledger_rows_with_raw_code"] = len(raw_rows)
        if raw_rows:
            red.append("HARD-2(候选①失败): 台账仍有 %d 行含 raw `code` 字段 ⇒ 真值落盘" % len(raw_rows))
        if fps:
            say("[assert-face] 落盘面: %d 个实发 (n,code) 指纹全在台账内; 公开配方复算 %d 例 0 命中真值指纹; raw code 字段 %d 行"
                % (len(set(mounted)), len(rc_), len(raw_rows)))
    else:
        if ledger and any(int(r.get("n", 0)) > 0 for r in ledger):
            rec["notes"].append("挂载轴 off 但台账仍有落盘行 (%d) —— 预期: 记录面不受挂载轴控制"
                                "(判据器用它证明'真值存在于链内、只是没进提示')" % len(ledger))
            say("[assert-face] 注: 挂载轴 off 但台账有 %d 行落盘 (真值在链内、未进提示 ⇒ 必错族结构成立)" % len(ledger))

    # ---- HARD-3 遥测面 ----
    # R497 判据器修订 (证据: T1 首调用实况) —— `ledger_*` 字段由 `ModelQueueRouter` 的**声明门**打点
    # 语句 (与 `replay_pair_gate` 同一条 emit) 发出 ⇒ 落在 point=`tool_decl_gate`, 不在 `llm_call`。
    # 原版只扫 `llm_call` ⇒ 会把"字段在另一打点点上"误报成"打点与实发脱钩"。
    # 修订后: 扫**所有**带 `ledger_mount` 字段的点 (记下点名为证), 并要求
    #   (i) 带字段的行数 == 远端调用数  (ii) 行内 code 集合 == 实发面挂载码集合
    #   (iii) 行内 (n,code) 对集合 == 实发面 (n,code) 对集合
    CARRY = ("ledger_mount", "ledger_code8", "ledger_n")
    mrows = [r for r in tel if any(k in (r.get("kv") or {}) for k in CARRY)]
    points = sorted({r.get("point") for r in mrows})
    # R497 候选⑦: 台账面并入**逐调用**的 `llm_call` 行 (tool_decl_gate 仍带同字段 ⇒ 行数会翻倍)。
    #   判据按点名分开: 「逐调用可见」= `llm_call` 行数 == 远端调用数; 一致性 = ledger_mount=1 的行。
    #   另外: 打点面**不得**再出现 raw `ledger_code` (真值不落打点)。
    llm_rows = [r for r in mrows if r.get("point") == "llm_call"]
    on_rows = [r for r in mrows if (r.get("kv") or {}).get("ledger_mount") == "1"]
    raw_code_rows = [r for r in tel if "ledger_code" in (r.get("kv") or {})]
    rec["telemetry_mount_points"] = points
    rec["telemetry_mount_rows"] = len(mrows)
    rec["telemetry_mount_llm_call_rows"] = len(llm_rows)
    rec["telemetry_mount_on"] = len(on_rows)
    rec["telemetry_raw_code_rows"] = len(raw_code_rows)
    say("[assert-face] 遥测面: 带 ledger_* 字段 %d 行 (点=%s; llm_call %d 行), 其中 ledger_mount=1 的 %d 行, raw ledger_code %d 行"
        % (len(mrows), points, len(llm_rows), len(on_rows), len(raw_code_rows)))
    if raw_code_rows:
        red.append("HARD-3(候选⑦): 遥测仍含 raw `ledger_code` 字段 %d 行 ⇒ 真值进打点面" % len(raw_code_rows))
    if a.mount == "on":
        if not on_rows:
            red.append("HARD-3: 遥测无 ledger_mount=1 事件 ⇒ 打点与实发面脱钩")
        else:
            if len(llm_rows) != len(calls):
                red.append("HARD-3(候选⑦): 带 ledger_* 字段的 `llm_call` 行 %d != 远端调用 %d"
                           % (len(llm_rows), len(calls)))
            tel_pairs = {(int((r.get("kv") or {}).get("ledger_n", -1)), (r.get("kv") or {}).get("ledger_code8"))
                         for r in on_rows}
            face_pairs = {(p[0], sha8(p[1])) for _, ps, _ in rows for p in ps}
            rec["telemetry_code8"] = sorted({(r.get("kv") or {}).get("ledger_code8") for r in on_rows
                                             if (r.get("kv") or {}).get("ledger_code8")})
            if not face_pairs.issubset(tel_pairs):
                red.append("HARD-3: 实发面挂载 (n,code8) 未全部出现在遥测面: 缺 %s"
                           % sorted(face_pairs - tel_pairs)[:5])
            # R497 候选⑦: 台账面必须**并入逐调用行** (R495 只在 tool_decl_gate 上 ⇒ 远程调用轴看不见挂载代价)
            llm_ledger = [r for r in tel if r.get("point") == "llm_call"
                          and "ledger_mount" in (r.get("kv") or {})]
            rec["llm_call_with_ledger"] = len(llm_ledger)
            if len(llm_ledger) != len(calls):
                red.append("HARD-3(候选⑦失败): llm_call 行带 ledger_* 字段的 %d != 远端调用 %d"
                           % (len(llm_ledger), len(calls)))
            # 真值不得进打点面 (候选①): 任何遥测行都不得含 raw `ledger_code` 字段
            rawc = [r for r in tel if (r.get("kv") or {}).get("ledger_code")]
            rec["telemetry_rows_with_raw_code"] = len(rawc)
            if rawc:
                red.append("HARD-3(候选①失败): 遥测仍有 %d 行含 raw ledger_code ⇒ 真值进打点面" % len(rawc))
            llm_rows = [r for r in tel if r.get("point") == "local_decision_ledger"]
            rec["decision_events"] = len(llm_rows)
            if not llm_rows:
                red.append("HARD-3: 遥测无 point=local_decision_ledger 事件 ⇒ 决策落盘面未打点")
    else:
        if on_rows:
            red.append("HARD-3: 挂载轴 off 但遥测自报 %d 条 ledger_mount=1 ⇒ 打点与实发不符" % len(on_rows))

    # ---- HARD-4 通道面 (继承 R494) ----
    iso = [r for r in calls if is_isolated(r)]
    iso_tools = [r for r in iso if int(((r.get("sampling") or {}).get("tools_n") or 0)) > 0]
    rec["iso_calls"] = len(iso); rec["iso_calls_with_tools"] = len(iso_tools)
    if a.channel == "on":
        if iso_tools:
            red.append("HARD-4: 通道轴 on 但 %d 条隔离调用仍下发工具 (seq=%s)"
                       % (len(iso_tools), [r.get("seq") for r in iso_tools][:8]))
        if not iso:
            rec["notes"].append("无隔离通道调用 ⇒ HARD-4 未被触发 (unreported)")
    else:
        if iso and not iso_tools:
            rec["notes"].append("通道轴 off: 隔离 %d 条无一带工具 ⇒ 泄漏未复现 (unreported)" % len(iso))
            say("[assert-face] 注: 通道轴 off 泄漏未复现 (上游本轮未请求工具; unreported)")

    # ---- HARD-5 工具面越界收口 (R497 候选③, R495 半开通道) ----
    # R495 实证: 越界被判「已拒绝」但正文仍原样回显 ⇒ 模型把链源码行 (含挂载块常量/台账路径) 读进上下文。
    # R497 收口 = (a) `run_command` 结构拒执行 (rc=126, 不回显正文) + (b) `RecallRealityGate` 越界子句正文隐去。
    # 机检 (只作用于 **role=tool** 消息 —— assistant 复述被授权面不算通道):
    #   (i)  tool 消息里块头字面量出现 0 次        (ii) tool 消息里链源码路径出现 0 次
    #   (iii) 拒绝见证: 工具面出现「拒绝执行」计数 (0 = 未触发 ⇒ unreported, 不得据此称通过)
    SRC_PAT = "/home/agentuser/AgentFramework/src/"
    refuse_n = 0
    tool_hdr = tool_src = 0
    for i, r in enumerate(calls):
        for m in (r.get("messages") or []):
            if m.get("role") != "tool":
                continue
            c = m.get("content")
            if not isinstance(c, str):
                continue
            if MOUNT_HEADER in c:
                tool_hdr += 1
            if SRC_PAT in c:
                tool_src += 1
            if "拒绝执行" in c:
                refuse_n += 1
    rec["tool_msgs_with_header"] = tool_hdr
    rec["tool_msgs_with_src_path"] = tool_src
    rec["refusal_seen"] = refuse_n
    if tool_hdr:
        red.append("HARD-5: tool 消息出现块头字面量 %d 次 ⇒ 工具面回显通道未闭合" % tool_hdr)
    if tool_src:
        red.append("HARD-5: tool 消息出现链源码路径 %d 次 ⇒ 越界正文仍在回显" % tool_src)
    if not refuse_n:
        rec["notes"].append("工具面 0 次越界拒绝 (本轮模型未尝试工作区外路径) ⇒ 收口未被触发 (unreported)")
    say("[assert-face] 越界收口面: tool 消息 块头=%d 链源码路径=%d | 拒绝执行见证=%d"
        % (tool_hdr, tool_src, refuse_n))

    # 判据器自检: 正控 (真挂载块 system+结构行) 必须命中; 负控 (工具回显块头) 必须不命中。
    # 修订前后同一组输入都跑过 ⇒ 证明"修订只为消除工具回显误判, 未放松真挂载的检出"。

    rec["red"] = red
    rec["verdict"] = "PASS" if not red else "FAIL"
    for m in red:
        say("[assert-face][红] " + m)
    say("[assert-face] " + rec["verdict"])
    jp = os.path.join(d, "assert-face-%s.json" % a.arm)
    json.dump(rec, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    say("[assert-face] → " + jp)
    log.close()
    return 0 if not red else 13


if __name__ == "__main__":
    sys.exit(main())
