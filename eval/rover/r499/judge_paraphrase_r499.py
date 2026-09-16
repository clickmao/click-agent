#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R499 本地改写通道判据器 (通用代码逻辑, 语言无关)。

口径来源: src/agent/IndustrialAgentV2.cs:1607-1728 + src/agent.modelqueue/LocalParaphraseChannel.cs
  · 门态  : local_turn_gate.kv.basis ∈ {mechanical:paraphrase, mechanical:paraphrase→local,
            gate:paraphrase_no_replayable_prev, gate:paraphrase_guard_rejected, ...}
  · 降级  : point == "paraphrase_degrade_remote" (kv.reason)
  · 成本  : point == "llm_call" / "llm_call_continue" (kv.turn, kv.request_id, kv.total_tokens)
  · 答复  : turns-<arm>.jsonl (单 JSON: {stats,turns:[{turn,text,reply,ok,events}]})

判据 (预注册 eval/rover/r499/prereg_r499.json):
  J1 门态正控 —— C 臂: turn8 无 paraphrase 类 basis 且 turn8 有远端调用;
                  P 臂: turn8 basis 含 "paraphrase" (absorb 或 degrade 均算门生效)
  J2 改写质量 —— P 臂 absorb 轮答复: 非空/非模板原文/非逐字复读/长度带内/无动作宣称/无新增标识符
  J3 成本面  —— 逐臂 调用数(按 request_id 去重, 含 continue) / 付费 token(usage 求和) / 空正文数
  J4 族回归  —— 逐轮 basis 与远端调用对照 (ack 族仍 skip; 复述族不变; 必错族不背书粗判)
用法:
  python3 judge_paraphrase_r499.py --dir <round_dir> --arm C --mode C [--json out.json]
  python3 judge_paraphrase_r499.py --dir <round_dir> --nc <nc_drop_gate_row|nc_template_reply|nc_c_absorb>
退出码: 0 = 判据全绿; 1 = 有红; 2 = 仪器/输入问题 (fail-closed, 禁当绿)
"""
import argparse, io, json, os, re, shutil, sys, tempfile

TEMPLATE_LITERALS = ("收到。",)
ACTION_CLAIM = re.compile(r"(我已|已经|将执行|已执行|已写入|已创建|已删除|已修改|已提交|跑通|执行了|rc\s*=\s*-?\d+)")
IDENT = re.compile(r"`([^`]{2,80})`|([A-Za-z0-9_./@-]{4,})")
ENDORSE = re.compile(r"(不对|不准|错了|错误|否|不是|有误|应该?是|前提不成立|不成立)")


def load_jsonl(p):
    rows = []
    with io.open(p, encoding="utf-8-sig") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                rows.append(json.loads(ln))
            except Exception as e:
                print("[致命] JSONL 解析失败 %s: %s" % (os.path.basename(p), e))
                sys.exit(2)
    return rows


def load_turns(p):
    with io.open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="/home/agentuser/AgentFramework/eval/rover/r499")
    ap.add_argument("--arm", default="")
    ap.add_argument("--mode", default="", choices=["", "C", "P"])
    ap.add_argument("--nc", default="")
    ap.add_argument("--json", default="")
    a = ap.parse_args()

    if a.nc:
        if not a.arm or not a.mode:
            print("[致命] 负控需同时给 --arm 与 --mode (源臂)")
            sys.exit(2)
        tmp = tempfile.mkdtemp(prefix="nc_r499_")
        src = a.arm
        # 统一重命名到 C/P 规范名, 便于负控注入
        for pre, ext in (("turns-", ".jsonl"), ("usage-", ".jsonl"), ("calls-", ".jsonl"), ("flags-", ".json")):
            s = os.path.join(a.dir, pre + src + ext)
            if os.path.isfile(s):
                shutil.copy2(s, os.path.join(tmp, pre + a.mode + ext))
        st = os.path.join(a.dir, "tel-" + src)
        if os.path.isdir(st):
            shutil.copytree(st, os.path.join(tmp, "tel-" + a.mode))
        tgt_arm = "P" if a.nc in ("nc_drop_gate_row", "nc_template_reply") else "C"
        mode = "P" if tgt_arm == "P" else "C"
        if tgt_arm != a.mode:
            print("[致命] 负控目标臂 %s 与源臂类别 %s 不符" % (tgt_arm, a.mode))
            sys.exit(2)
        tp = os.path.join(tmp, "turns-%s.jsonl" % tgt_arm)
        gp = os.path.join(tmp, "tel-%s" % tgt_arm, "host.jsonl")
        if a.nc == "nc_drop_gate_row":
            rows = load_jsonl(gp)
            seen, out = 0, []
            for r in rows:
                if r.get("point") == "local_turn_gate":
                    seen += 1
                    if seen == 8:
                        continue
                out.append(r)
            with io.open(gp, "w", encoding="utf-8") as f:
                for r in out:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
        elif a.nc == "nc_template_reply":
            t = load_turns(tp)
            for tr in t["turns"]:
                if tr["turn"] == 8:
                    tr["reply"] = t["turns"][6]["reply"]
            with io.open(tp, "w", encoding="utf-8") as f:
                json.dump(t, f, ensure_ascii=False, indent=1)
        else:
            rows = load_jsonl(gp)
            seen = 0
            for r in rows:
                if r.get("point") == "local_turn_gate":
                    seen += 1
                    if seen == 8:
                        r["kv"]["basis"] = "mechanical:paraphrase"
            with io.open(gp, "w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
        rc = run_dir(tmp, tgt_arm, mode, "")
        print("[NC %s] rc=%d (期望 1)" % (a.nc, rc))
        shutil.rmtree(tmp, ignore_errors=True)
        sys.exit(0 if rc == 1 else 1)

    if not a.arm or not a.mode:
        print("[致命] 需要 --arm 与 --mode")
        sys.exit(2)
    rc = run_dir(a.dir, a.arm, a.mode, a.json)
    sys.exit(rc)


def run_dir(d, arm, mode, jout):
    need = ["turns-%s.jsonl" % arm, "usage-%s.jsonl" % arm, "tel-%s/host.jsonl" % arm, "flags-%s.json" % arm]
    miss = [f for f in need if not os.path.isfile(os.path.join(d, f))]
    if miss:
        print("[致命] 输入缺失: %s ⇒ fail-closed (不算绿)" % ",".join(miss))
        return 2
    T = load_turns(os.path.join(d, "turns-%s.jsonl" % arm))
    turns = T["turns"]
    usage = load_jsonl(os.path.join(d, "usage-%s.jsonl" % arm))
    tel = load_jsonl(os.path.join(d, "tel-%s/host.jsonl" % arm))
    flags = json.load(io.open(os.path.join(d, "flags-%s.json" % arm), encoding="utf-8-sig"))
    gate = [r for r in tel if r.get("point") == "local_turn_gate"]
    degr = [r for r in tel if r.get("point") == "paraphrase_degrade_remote"]
    calls = [r for r in tel if r.get("point") in ("llm_call", "llm_call_continue")]

    red = []
    info = {}

    def chk(cid, ok, detail):
        (red.append((cid, detail)) if not ok else None)
        print("%-4s %-4s %s" % (cid, "OK" if ok else "RED", detail))

    # 仪器自检: 三门读数不得为空 (禁静默通过)
    if len(gate) != T["stats"]["turns"]:
        print("[致命] local_turn_gate 行数 %d != turns %d ⇒ 仪器口径不符 ⇒ fail-closed"
              % (len(gate), T["stats"]["turns"]))
        return 2
    if not usage:
        print("[致命] usage 空 ⇒ fail-closed")
        return 2

    # J1 门态正控
    g8 = gate[7]["kv"] if len(gate) > 7 else {}
    b8 = str(g8.get("basis", ""))
    t8_remote = [c for c in calls if str(c.get("kv", {}).get("turn", "")) == "8"]
    if mode == "C":
        chk("J1a", "paraphrase" not in b8, "C 臂 turn8 basis=%r (期望不含 paraphrase)" % b8)
        chk("J1b", len(t8_remote) >= 1, "C 臂 turn8 远端调用数=%d (期望>=1)" % len(t8_remote))
        chk("J1c", len(degr) == 0, "C 臂 paraphrase_degrade_remote 行数=%d (期望0)" % len(degr))
    else:
        chk("J1a", "paraphrase" in b8, "P 臂 turn8 basis=%r (期望含 paraphrase)" % b8)
        info["p_turn8_basis"] = b8
        info["p_degrade_rows"] = len(degr)
        info["p_turn8_remote_calls"] = len(t8_remote)
        if "paraphrase" in b8 and "remote" in b8:
            info["p_turn8_outcome"] = "degrade_remote"
        elif "paraphrase" in b8:
            info["p_turn8_outcome"] = "absorb_local"

    # J2 改写质量 (仅 absorb 轮)
    if mode == "P" and info.get("p_turn8_outcome") == "absorb_local":
        r8 = turns[7]["reply"]
        r7 = turns[6]["reply"]
        chk("J2a", len(r8.strip()) > 8 and r8.strip() not in TEMPLATE_LITERALS,
            "P 臂 turn8 答复非空/非模板 len=%d" % len(r8))
        chk("J2b", r8.strip() != r7.strip(), "P 臂 turn8 答复 != 上一条逐字复读")
        ratio = (len(r8) / max(1, len(r7)))
        chk("J2c", 0.15 <= ratio <= 4.0, "P 臂 turn8 长度比=%.2f (带 0.15..4.0)" % ratio)
        m = ACTION_CLAIM.search(r8)
        chk("J2d", m is None, "P 臂 turn8 无动作宣称 (命中=%r)" % (m.group(0) if m else ""))
        src = r7 + "\n" + "\n".join(t["text"] for t in turns)
        newids = set()
        for mm in IDENT.finditer(r8):
            tok = mm.group(1) or mm.group(2) or ""
            if len(tok) >= 4 and tok not in src:
                newids.add(tok)
        chk("J2e", not newids, "P 臂 turn8 无新增标识符 (新增=%s)" % (sorted(newids)[:6],))

    # J3 成本面
    rid = {}
    for c in calls:
        kv = c.get("kv", {})
        k = kv.get("request_id") or ("%s#%s" % (kv.get("turn"), c.get("seq")))
        rid.setdefault(k, c)
    n_calls = len(rid)
    tot = sum(int(u.get("usage", {}).get("total_tokens") or 0) for u in usage)
    empty = sum(1 for u in usage if u.get("empty_body"))
    info.update({"calls_dedup": n_calls, "paid_total_tokens": tot, "empty_body": empty,
                 "usage_rows": len(usage)})
    print("J3   info arm=%s calls=%d tokens=%d empty=%d" % (arm, n_calls, tot, empty))

    # J4 族回归: ack 族 (2..5) 必须本地消化 (无远端调用) —— basis 允许 机械/本地门 两种载体
    for tn in (2, 3, 4, 5):
        if tn - 1 < len(gate):
            b = str(gate[tn - 1]["kv"].get("basis", ""))
            rem = [c for c in calls if str(c.get("kv", {}).get("turn", "")) == str(tn)]
            consumed = ("ack" in b or "repeat" in b or "paraphrase" in b or "local" in b or "skip" in b.lower())
            chk("J4t%d" % tn, consumed and not rem,
                "turn%d basis=%r 远端调用=%d (期望本地消化且 0 远端)" % (tn, b, len(rem)))

    # 必错族粗判 (t14/t15 在 grid 中的假前提轮: 记录答复开场, 不做断言绿)
    adv = []
    for tn in (13, 14, 15, 16, 17):
        if tn <= len(turns):
            rr = turns[tn - 1]["reply"]
            adv.append({"turn": tn, "endorse_hit": bool(ENDORSE.search(rr[:120])), "head": rr[:80]})
    info["adv_head"] = adv

    print("== J1/J2/J3 摘要 arm=%s mode=%s ==" % (arm, mode))
    print(json.dumps(info, ensure_ascii=False)[:1200])
    res = {"arm": arm, "mode": mode, "red": [{"id": c, "detail": d} for c, d in red],
           "info": info, "turns": T["stats"]["turns"], "gate_rows": len(gate)}
    if jout:
        with io.open(jout, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
    print("VERDICT=%s red=%d" % ("GREEN" if not red else "RED", len(red)))
    return 0 if not red else 1


if __name__ == "__main__":
    sys.exit(main())
