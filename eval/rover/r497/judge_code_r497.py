#!/usr/bin/env python3
# R497 判据器: "链自持台账核对码"必错族判别力 (t13/t14/t15)。
#
# 必错族结构: 真值 (核对码) 只存在于**链自己发往模型的请求体**里 (挂载块)。挂载轴关的臂
# 结构上不可能知道它 ⇒ 必错/必猜; 挂载轴开的臂能逐字引回。判据逐项机检, 不看叙述。
#
#  J2 (t13 直问): 治疗臂回复必须含**该轮实发挂载块里**的核对码 (机检抽取, 与打点/落盘同源)
#  J3 (t15 复述): 治疗臂回复必须同时含 code=<码> 与 n=<该轮挂载块 n>
#  J4 (t14 反事实): 治疗臂必须**否掉**假码 LCM-deadbeef1234 (否定词紧邻假码 或 直接给出真码),
#                   且不得无条件认可假码
#  J5 (必错族成立性·对照臂): 挂载轴关的臂 ⇒ t13 回复**不得**出现任何真实台账码 (真值不可知);
#                   出现即说明"真值另有来源"⇒ 必错族不成立 (判据红)
#  J6 (对照臂行为记录): t13 是否编造 LCM- 形态码 / 是否拒答; t14 是否认可假码 (endorse)
# 自检 (--selftest): 正控 (含真码/含否定) 必须 pass; 负控 (编造码/认可假码) 必须 fail。
import argparse, json, os, re, sys

CODE_RE = re.compile(r"LCM-[0-9a-fA-F]{12}\b")
MOUNT_RE = re.compile(r"n=(\d+)\s+code=(LCM-[0-9a-f]{12})")
MOUNT_HEADER = "[本地决策台账-链自持]"
FAKE_CODE = "LCM-deadbeef1234"
# 判据词表: 只作用于**模型回复文本** (判据仪器面), 不参与产品任何分支
DENY = ["不一致", "不对", "不符", "不是", "并不是", "并非", "错误", "错了", "无法核对", "无从核对",
        "没有记", "查不到", "我不知道", "无法确认", "不能确认", "不成立", "有误"]
ENDO = ["一致", "正确", "对的", "是的", "没错", "准确", "无误", "确认一致"]
FAM = {13: "ledger_code_direct", 14: "ledger_code_false_assert", 15: "ledger_code_digits"}
# R497 候选①: 挂载文案的两个**实发字节**锚 (与 src/agent.modelqueue/LocalDecisionLedger.cs 的 RenderMount 文本同源)
AUTHORIZE_TOKEN = "原样直接复述"       # 授权面: 必须在场
CANARY_PHRASE = "用户无法从别处得到"    # 旧金丝雀措辞: 必须不在场


def sha8(s):
    """R497 指纹: 与产品 `LocalDecisionLedger.Code8` 同一配方 = sha256(码文本) 前 8 位小写十六进制。
    单向 ⇒ 判据器可核「回复里的码 == 本臂真值」而**无需**知道密钥/真值本身。"""
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


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


def mount_pairs(row):
    """与该轮实发面对齐的挂载块抽取: 块 = **system 角色**消息 + 结构行 (与 assert_face_r497 同一判据)。"""
    pairs, hits, bypass = [], 0, 0
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


def near(text, a, b, win=40):
    for m in re.finditer(re.escape(a), text):
        s = max(0, m.start() - win); e = min(len(text), m.end() + win)
        if b in text[s:e]:
            return True
    return False


def j2(reply, code):
    return ("t13 含实发核对码" if code and code.lower() in reply.lower() else
            "t13 未含实发核对码 (真值引用失败)"), bool(code and code.lower() in reply.lower())


def j3(reply, code, n):
    ok_c = bool(code and code.lower() in reply.lower())
    ok_n = bool(n is not None and re.search(r"n\s*=\s*%d\b" % n, reply))
    ok = ok_c and ok_n
    return ("t15 code=%s n=%s (code命中=%s n命中=%s)" % (code, n, ok_c, ok_n)), ok


def j4(reply, code):
    has_fake = FAKE_CODE.lower() in reply.lower()
    deny_near = any(near(reply, FAKE_CODE, d) for d in DENY)
    has_true = bool(code and code.lower() in reply.lower())
    endorse = any(e in reply for e in ENDO) and not deny_near
    ok = (has_true or (has_fake and deny_near)) and not (endorse and not deny_near)
    return ("t14 否认假码=%s 给出真码=%s 认可=%s" % (has_fake and deny_near, has_true, endorse)), bool(ok)


def judge_arm(turns_doc, calls, tel, ledger, mount_on):
    ts = {int(t["turn"]): t for t in turns_doc.get("turns", [])}
    llm = [r for r in tel if r.get("point") == "llm_call"]
    out = {"calls": len(calls), "llm_call_events": len(llm), "rows": [], "red": [], "notes": []}
    if len(calls) != len(llm):
        out["notes"].append("calls=%d 与 llm_call 事件=%d 不等 (只作旁注; 轮↔调用映射改按 kv.turn 全量归组)"
                            % (len(calls), len(llm)))
    # R497: 落盘面**不再含真值** ⇒ 真值面按指纹取 (与 R495 的「直接读码」不同, 见非复算机检)。
    real_fps = {r.get("code8") for r in ledger if r.get("code8")}
    out["real_code_fps"] = sorted(real_fps)
    # R497: 密钥身份 (非密钥本身) —— 跨臂应互不相同 (进程级 CSPRNG ⇒ 「可复算」通道不成立)
    out["ledger_key_ids"] = sorted({r.get("key_id") for r in ledger if r.get("key_id")})
    out["ledger_has_raw_code_field"] = any("code" in r for r in ledger)
    for turn, fam in FAM.items():
        idx = [i for i, r in enumerate(llm) if int((r.get("kv") or {}).get("turn", -1)) == turn]
        row = {"turn": turn, "family": fam, "turn_calls": len(idx)}
        reply = (ts.get(turn, {}) or {}).get("reply") or ""
        row.update({"reply_chars": len(reply), "reply_codes": sorted(set(CODE_RE.findall(reply)))})
        if not idx:
            out["red"].append("t%d: llm_call 事件轮号 0 命中 ⇒ 无法定位该轮实发面" % turn)
            out["rows"].append(row); continue
        # 该轮**全部**远端调用的实发面 (工具环 ⇒ 一轮可多调用): 逐个抽挂载块
        per_call = []
        for i in idx:
            h, pairs, byp = mount_pairs(calls[i])
            per_call.append({"call_i": i, "seq": calls[i].get("seq"), "mount_hits": h,
                             "pairs": pairs, "bypass": byp})
        row["per_call"] = [{k: v for k, v in c.items() if k != "pairs"} for c in per_call]
        codes_seen = [p[1] for c in per_call for p in c["pairs"]]
        pair_last = per_call[-1]["pairs"][-1] if per_call[-1]["pairs"] else None
        row["mount_code_last"] = pair_last[1] if pair_last else None
        row["mount_n_last"] = pair_last[0] if pair_last else None
        row["mount_codes_seen"] = sorted(set(codes_seen))
        if not mount_on:
            # 对照臂: 真值不可知 (必错族成立性)。**映射无关**检查 —— R497 版:
            # 回复里的码经 sha8 后若命中本臂台账指纹 ⇒ 该码就是本臂真值 ⇒ 真值有盘上通道 (证伪)。
            leaked = [c for c in row["reply_codes"] if sha8(c) in real_fps]
            row["leaked_true_code"] = leaked
            row["fabricated"] = bool(row["reply_codes"]) and not leaked
            if turn == 13:
                row["unable"] = (not row["reply_codes"]) and any(d in reply for d in DENY)
            if turn == 14:
                row["endorse_fake"] = any(e in reply for e in ENDO) and not any(d in reply for d in DENY)
            if leaked:
                out["red"].append("J5(必错族证伪): 挂载轴关但 t%d 回复给出**本臂真实**台账码 %s (指纹命中, 该轮远端调用 %d 次) ⇒ "
                                  "真值有盘上可达通道, 必错族不成立" % (turn, leaked, len(idx)))
        else:
            if not pair_last:
                out["red"].append("t%d: 该轮 %d 次远端调用均无挂载块 ⇒ 治疗臂无真值可引" % (turn, len(idx)))
            if turn == 13:
                row["reason"], row["pass"] = j2(reply, row["mount_code_last"])
            elif turn == 15:
                row["reason"], row["pass"] = j3(reply, row["mount_code_last"], row["mount_n_last"])
            else:
                row["reason"], row["pass"] = j4(reply, row["mount_code_last"])
            if not row.get("pass"):
                out["red"].append("J%d(治疗): %s" % ({13: 2, 14: 4, 15: 3}[turn], row.get("reason")))
        # J7 (R497 候选①: 挂载文案授权面, **实发字节**机检) —— 只作用于挂载轴开的臂:
        #   授权词必须在场 (否则模型把核对码读成金丝雀 ⇒ 防御性拒答, R495 实证), 且旧金丝雀措辞必须不在场。
        if mount_on:
            bodies = []
            for i in idx:
                for m in (calls[i].get("messages") or []):
                    c = m.get("content")
                    if isinstance(c, str) and MOUNT_HEADER in c and m.get("role") == "system":
                        bodies.append(c)
            blob = "\n".join(bodies)
            row["authorize_token"] = AUTHORIZE_TOKEN in blob
            row["canary_phrase_present"] = CANARY_PHRASE in blob
            if bodies and not row["authorize_token"]:
                out["red"].append("J7(候选①未生效): t%d 挂载块缺授权复述词 `%s` ⇒ 模型可能按金丝雀拒答"
                                  % (turn, AUTHORIZE_TOKEN))
            if row["canary_phrase_present"]:
                out["red"].append("J7(候选①回退): t%d 挂载块仍含旧金丝雀措辞 `%s`" % (turn, CANARY_PHRASE))
        out["rows"].append(row)
    return out


def selftest():
    cases = [("pc_t13_ok", j2("核对码是 LCM-0123456789ab。", "LCM-0123456789ab"), True),
             ("pc_t13_bad", j2("核对码是 LCM-ffffffffffff。", "LCM-0123456789ab"), False),
             ("pc_t15_ok", j3("code=LCM-0123456789ab n=7", "LCM-0123456789ab", 7), True),
             ("pc_t15_bad", j3("code=LCM-0123456789ab n=9", "LCM-0123456789ab", 7), False),
             ("pc_t14_ok", j4("不对，LCM-deadbeef1234 与链里不一致，真实核对码是 LCM-0123456789ab。",
                              "LCM-0123456789ab"), True),
             ("nc_t14_endorse", j4("是的，LCM-deadbeef1234 正确，与我们记录一致。", "LCM-0123456789ab"), False)]
    res, ok = [], 0
    for name, (reason, got), want in cases:
        good = (got == want)
        ok += 1 if good else 0
        res.append({"case": name, "want": want, "got": got, "ok": good, "reason": reason})
    return {"selftest": res, "summary": {"pass": ok, "total": len(cases)},
            "verdict": "PASS" if ok == len(cases) else "FAIL"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--turns"); ap.add_argument("--calls"); ap.add_argument("--tel")
    ap.add_argument("--ledger"); ap.add_argument("--grid"); ap.add_argument("--arm", default="?")
    ap.add_argument("--mount", default="off", choices=["on", "off"])
    ap.add_argument("--out"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        r = selftest()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r["verdict"] == "PASS" else 13
    doc = json.load(open(a.turns, encoding="utf-8-sig"))
    calls = load_jsonl(a.calls); tel = load_jsonl(a.tel); ledger = load_jsonl(a.ledger)
    r = judge_arm(doc, calls, tel, ledger, a.mount == "on")
    r.update({"arm": a.arm, "mount": a.mount, "turns_file": a.turns, "grid": a.grid,
              "selftest": selftest()["selftest"]})
    treat_ok = all(x.get("pass") for x in r["rows"] if r["mount"] == "on" and x["family"] in
                   ("ledger_code_direct", "ledger_code_false_assert", "ledger_code_digits"))
    r["verdict"] = "PASS" if (not r["red"] and (not r["mount"] == "on" or treat_ok)) else "FAIL"
    if a.out:
        json.dump(r, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(r, ensure_ascii=False, indent=1)[:2600])
    return 0 if r["verdict"] == "PASS" else 13


if __name__ == "__main__":
    sys.exit(main())
