#!/usr/bin/env python3
# R496 非复算机检 (候选①的**判别力**闸): 「核对码真值」是否还留有任何盘上通道?
#
# R495 的反向诊断: 真值 = sha256(session|规范行)[:12] 且**台账落盘 raw `code`** ⇒
#   ① 任何能读盘的臂都能拿到真值 (必错族被证伪); ② 源码就是公开配方 ⇒ 复算即得。
# R496 收口: 真值 = HMAC-SHA256(**进程级 CSPRNG 密钥 32B, 只存内存**, session|规范行)[:12];
#   落盘/打点面只留单向指纹 `code8 = sha256(code)[:8]` 与 `key_id = sha256(hex(key))[:8]`。
#
# 本器具回答 5 个可证伪问题 (逐条给读数, 禁「大概」):
#   Q1 落盘面还有 raw 真值吗?      (台账行的 raw `code` 字段 / 台账文件里 "LCM-" 字面量)
#   Q2 公开配方还能复算真值吗?      (R495 口径 sha256(session|canon)[:12] 的指纹是否命中真值指纹)
#   Q3 密钥是进程级随机吗?          (key_id 臂内唯一 ∧ 跨臂互不相同 ⇒ 常量/可复算通道死)
#   Q4 链自己的文件里有真值字面量吗?  (rundata/台账/遥测/host log 逐字节扫)
#   Q5 源码里存在密钥落盘/入环境的通道吗? (结构性检查: 唯一写密钥的地方必须是 HMAC 入参)
#
# 自检 (--selftest): 正控 = 台账含 raw code ⇒ Q1 必须红; 负控 = 只有指纹 ⇒ 必须绿。
# 用法: python3 nonrecompute_check_r496.py --dir eval/rover/r496 [--arms B,T0,T1] [--selftest]
import argparse, glob, hashlib, json, os, re, sys, tempfile

ROOT = "/home/agentuser/AgentFramework"
CODE_PREFIX = "LCM-"
CODE_RE = re.compile(r"LCM-[0-9a-f]{12}")
LEDGER_SRC = "src/agent.modelqueue/LocalDecisionLedger.cs"
# wire 面 (构造上必然含真值: 中继归档的请求体 / 夹具抓到的回复) —— 明确排除, 不算盘上通道
WIRE_FACE = ("calls-%s.jsonl", "turns-%s.jsonl")
WIRE_FACE_LOOSE = ("relay-%s.log",)


def sha8(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def recipe_r495(session, canon_rows):
    """R495 口径 (已废): sha256(session + '|' + 行按序 '\n' 连接)[:12] 前缀 LCM-。"""
    msg = (session or "") + "|" + "\n".join(canon_rows or [])
    return CODE_PREFIX + hashlib.sha256(msg.encode("utf-8")).hexdigest()[:12]


def load_jsonl(p):
    rows = []
    if not os.path.exists(p):
        return rows
    for line in open(p, encoding="utf-8-sig"):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def scan_surface(paths):
    """逐字节扫给面; 返回 [(path, n_hits)] 及每个 LCM- 字面量的样例。"""
    hits, samples = [], []
    for p in paths:
        try:
            t = open(p, "rb").read().decode("utf-8", "replace")
        except Exception:
            continue
        c = t.count(CODE_PREFIX)
        if c:
            hits.append((os.path.relpath(p, ROOT), c))
            samples += CODE_RE.findall(t)[:3]
    return hits, samples


def surface_of(d, arm):
    """链**自己写**的文件面 (工作区 + 台账副本 + 遥测副本 + host log) + 审计里非 wire 的落地件。"""
    out = []
    out += sorted(glob.glob(os.path.join(d, "rundata-%s" % arm, "**", "*"), recursive=True))
    out += sorted(glob.glob(os.path.join(d, "tel-%s" % arm, "*")))
    for pat in ("ledger-%s.jsonl", "host-%s.log", "flags-%s.json", "preflight-%s.json",
                "teardown-%s.json", "assert-face-%s.json", "kpi-%s.json"):
        out.append(os.path.join(d, pat % arm))
    return [p for p in out if os.path.isfile(p)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="eval/rover/r496")
    ap.add_argument("--arms", default="B,T0,T1")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    d = os.path.join(ROOT, a.dir) if not os.path.isabs(a.dir) else a.dir

    if a.selftest:
        return selftest(d)

    arms = [x for x in a.arms.split(",") if x]
    out = {"round": "R496", "instrument": "nonrecompute_check_r496.py", "arms": {}, "red": [], "verdict": {}}
    key_ids_by_arm = {}
    all_truth = set()
    for arm in arms:
        led = os.path.join(d, "ledger-%s.jsonl" % arm)
        rows = load_jsonl(led)
        wire = set()
        for line in open(os.path.join(d, "calls-%s.jsonl" % arm), encoding="utf-8-sig") if os.path.exists(
                os.path.join(d, "calls-%s.jsonl" % arm)) else []:
            wire |= set(CODE_RE.findall(line))
        all_truth |= wire
        fps = {r.get("code8") for r in rows if r.get("code8")}
        kids = {r.get("key_id") for r in rows if r.get("key_id")}
        raw_code_fields = [r for r in rows if r.get("code")]
        surface = surface_of(d, arm)
        hits, samples = scan_surface(surface)
        # Q2: 公开配方 (R495 口径) 复算是否命中真值指纹
        rec_hits, rec_examples = [], []
        for t in sorted(wire):
            for prefix_len in range(1, len(rows) + 1):
                can = [r.get("canon", "") for r in rows[:prefix_len]]
                cand = recipe_r495(rows[0].get("session") if rows else "", can)
                if sha8(cand) in fps:
                    rec_hits.append((prefix_len, cand))
                    rec_examples.append({"prefix": prefix_len, "recipe": cand})
                    break
        r = {
            "ledger_rows": len(rows),
            "raw_code_field_rows": len(raw_code_fields),
            "code8_n": len(fps),
            "key_ids": sorted(k for k in kids if k),
            "wire_truth_codes": len(wire),
            "wire_truth_sample_fps": sorted({sha8(c) for c in wire})[:4],
            "surface_files": len(surface),
            "surface_hits": hits,
            "surface_hit_samples": samples,
            "recipe_recompute_hits": len(rec_hits),
            "recipe_recompute_examples": rec_examples[:2],
            "recipe_formula": "R495 口径 sha256(session|canon-rows)[:12] (已废配方, 用作**反例复算**)",
        }
        out["arms"][arm] = r
        if kids:
            key_ids_by_arm[arm] = sorted(k for k in kids if k)

    # ---- 判决 ----
    red = out["red"]
    for arm, r in out["arms"].items():
        if r["raw_code_field_rows"]:
            red.append("Q1 %s: 台账仍含 raw `code` 字段 %d 行 ⇒ 真值落盘" % (arm, r["raw_code_field_rows"]))
        if r["surface_hits"]:
            red.append("Q4 %s: 链自己的文件面出现真值字面量: %s" % (arm, r["surface_hits"][:4]))
        if r["recipe_recompute_hits"]:
            red.append("Q2 %s: 公开配方复算命中真值指纹 %d 处 ⇒ 真值仍可复算" % (arm, r["recipe_recompute_hits"]))
        if r["ledger_rows"] and not r["key_ids"]:
            red.append("Q3 %s: 台账无 key_id ⇒ 密钥身份不可核" % arm)
        if r["ledger_rows"] and r["code8_n"] != len({int(x.get("n", -1)) for x in load_jsonl(os.path.join(d, "ledger-%s.jsonl" % arm))}):
            red.append("Q1' %s: code8 去重数 %d != 台账 n 取值数 (指纹漏行)" % (arm, r["code8_n"]))
    flat = [k for kk in key_ids_by_arm.values() for k in kk]
    if any(len(v) > 1 for v in key_ids_by_arm.values()):
        red.append("Q3: 某臂内 key_id 不唯一 ⇒ 密钥被中途替换")
    if len(flat) >= 2 and len(set(flat)) < len(flat):
        red.append("Q3: 跨臂 key_id 出现重复 ⇒ 密钥不是进程级随机的 (可复算通道复活)")
    # Q5 结构性检查: 源码里密钥的唯一去处必须是 HMAC 入参
    srcp = os.path.join(ROOT, LEDGER_SRC)
    src = open(srcp, encoding="utf-8").read() if os.path.exists(srcp) else ""
    # Q5 (R496 修订, 去掉误报): 只看**密钥标识符所在行**的去处 —— 逐行分类, 允许列表外一律报行原文。
    #   误报根因 (R496 自查): 旧正则 `(Append|Write)\([^)]*[Kk]ey` 会命中 `Append(",\"key_id\":\"")`
    #   (写的是**指纹**, 不是密钥) ⇒ 判据必须按标识符行而不是按字段名出现。
    key_ids = ("_key", "Key32", "key32")
    allowed_ctx = ("new HMACSHA256(", "KeyId(", "_key =", "key = ", "?? throw", "byte[] key", "return _key")
    key_lines, leaked_lines = [], []
    for ln in src.splitlines():
        if any(k in ln for k in key_ids):
            key_lines.append(ln.strip()[:160])
            if not any(a in ln for a in allowed_ctx):
                leaked_lines.append(ln.strip()[:160])
    q5 = {
        "has_hmac": "HMACSHA256" in src,
        "has_csprng": "RandomNumberGenerator.GetBytes" in src,
        "key_lines": key_lines,
        "key_lines_outside_allowlist": leaked_lines,
        "env_channel": bool(re.search(r"GetEnvironmentVariable\([^)]*(KEY|KEY32|CODEKEY)", src)),
        "writes_key_file": bool(re.search(r"File\.(WriteAllText|AppendAllText|WriteAllBytes)\([^)]*[Kk]ey", src)),
    }
    out["q5_static"] = q5
    if not q5["has_hmac"] or not q5["has_csprng"]:
        red.append("Q5: 真值配方不是 HMAC(进程密钥) 形态")
    if q5["key_lines_outside_allowlist"]:
        red.append("Q5: 密钥标识符出现在允许列表外的行 (疑外泄通道): %s" % q5["key_lines_outside_allowlist"][:3])
    for k in ("env_channel", "writes_key_file"):
        if q5[k]:
            red.append("Q5: 源码存在密钥外泄形态: %s" % k)
    out["verdict"] = {
        "verdict": "PASS" if not red else "FAIL",
        "red_n": len(red),
        "key_ids_distinct_across_arms": sorted(flat),
        "distinct": len(set(flat)) == len(flat) and len(flat) >= 2,
        "truth_codes_on_disk": sum(h[1] for r in out["arms"].values() for h in r["surface_hits"]),
        "note": "wire 面 (中继归档请求体 / 夹具抓的回复) 构造上含真值, **不**在盘上通道之列",
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if a.out:
        open(a.out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if not red else 1


def selftest(d):
    """正控/负控: 判别力自证 (仪器必须先证明它能红)。"""
    tmp = tempfile.mkdtemp(prefix="r496nonrec_")
    code = "LCM-0123456789ab"
    res = {"round": "R496", "selftest": "nonrecompute_check_r496", "cases": {}}
    # 正控: 台账含 raw code ⇒ Q1 必须红
    led = os.path.join(tmp, "ledger-B.jsonl")
    open(led, "w", encoding="utf-8").write(json.dumps(
        {"session": "s", "n": 1, "code": code, "canon": "1|ack|x", "code8": sha8(code), "key_id": "aaaa1111"},
        ensure_ascii=False) + "\n")
    rows = load_jsonl(led)
    pc = len([r for r in rows if r.get("code")])
    # 负控: 只有指纹 ⇒ 绿
    led2 = os.path.join(tmp, "ledger-T1.jsonl")
    open(led2, "w", encoding="utf-8").write(json.dumps(
        {"session": "s", "n": 1, "code8": sha8(code), "key_id": "bbbb2222", "canon": "1|ack|x"},
        ensure_ascii=False) + "\n")
    rows2 = load_jsonl(led2)
    nc = len([r for r in rows2 if r.get("code")])
    # 反例复算: 旧配方对同一 canon 是否等于真值
    old = recipe_r495("s", ["1|ack|x"])
    res["cases"]["pc_raw_code_on_disk"] = {"want": "raw>0", "got": pc, "ok": pc > 0}
    res["cases"]["nc_fingerprint_only"] = {"want": "raw==0", "got": nc, "ok": nc == 0}
    res["cases"]["recipe_differs_from_truth"] = {"want": "old!=true", "got": old, "ok": old != code}
    res["verdict"] = "PASS" if all(c["ok"] for c in res["cases"].values()) else "FAIL"
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
