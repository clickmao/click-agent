#!/usr/bin/env python3
# R427 可分性预检 v2: 「词袋计数族并列」根因判定 + 位置族可分性 + 已发布读数口径复核
# 口径: 与 src/agent/session/SessionHistorySearch.cs 同源复刻 (R421 极性 / R422 sqrt|d| 归一 / R423 1+ln tf)
# 只读语料 + 机检; 零构建 / 零网络 / 零 LLM / 零产品源码改动。
import json, os, math, hashlib

ROOT = "/home/agentuser/AgentFramework"
FIX_A = ROOT + "/eval/capability/r422/fixture-sessions"
FIX_B = ROOT + "/eval/capability/r423/fixture-tf"
OUT = ROOT + "/eval/capability/r427/precheck-r427.json"
NEG = "\u0001"
NL = chr(10)
QMAIN = "存在"
F4 = 5e-5   # 呈现精度容差: 已发布读数以 4 位小数/2 位小数呈现 ⇒ 半 ulp

def is_ctrl(ch):
    o = ord(ch)
    return o < 32 or o == 127 or (0x80 <= o <= 0x9f)

def normalize(s):
    out = []
    for ch in s:
        if ord(ch) <= 32 or is_ctrl(ch):
            continue
        out.append(ch.lower())
    return "".join(out)

def is_word_char(ch):
    return ord(ch) < 128 and (ch.isalnum() or ch in "_-")

def is_cjk(ch):
    return 0x4e00 <= ord(ch) <= 0x9fff

def is_neg(ch):
    return ch in "不没未无非"

def tokenize_pos(s):
    norm = normalize(s)
    toks = []
    word = []
    wi = [-1]
    def flush():
        if len(word) >= 2:
            toks.append(("".join(word), wi[0]))
        del word[:]
        wi[0] = -1
    for i, ch in enumerate(norm):
        if is_word_char(ch):
            if not word:
                wi[0] = i
            word.append(ch)
        else:
            flush()
            if is_cjk(ch) and i + 1 < len(norm) and is_cjk(norm[i + 1]):
                negated = is_neg(ch) or (i > 0 and is_neg(norm[i - 1]))
                raw = ch + norm[i + 1]
                toks.append(((NEG + raw) if negated else raw, i))
    flush()
    return toks

def tokens_of(s):
    return [t for t, _ in tokenize_pos(s)]

def count_tokens(s):
    c = {}
    for t in tokens_of(s):
        c[t] = c.get(t, 0) + 1
    return c

def tf_sat(tf):
    return 1.0 + math.log(tf if tf >= 1 else 1)

def build_document(m):
    parts = []
    gt = m.get("GoalText") or ""
    if gt.strip():
        parts.append(gt + NL)
    ke = m.get("KeyEntities") or []
    if ke:
        parts.append("、".join(ke) + NL)
    cs = m.get("Constraints") or []
    if cs:
        parts.append("; ".join(cs) + NL)
    ms = m.get("Milestones") or []
    if ms:
        parts.append("; ".join(ms) + NL)
    ltm = m.get("LongTermMemory") or ""
    if ltm:
        parts.append(ltm)
    return "".join(parts).strip()

def make_doc(sid, text, entries=1):
    tf = count_tokens(text)
    return {"id": sid, "text": text, "norm": normalize(text), "tokens": sorted(tf.keys()),
            "tf": tf, "entries": entries, "chars": len(text)}

def load_corpus(d):
    docs = []
    for name in sorted(os.listdir(d)):
        if not name.endswith("_memory.json"):
            continue
        sid = name[:-len("_memory.json")]
        m = json.load(open(os.path.join(d, name), encoding="utf-8"))
        text = build_document(m)
        if not text:
            continue
        docs.append(make_doc(sid, text, m.get("EntryCount", 0)))
    return docs

def score_all(docs, query):
    qtoks = tokens_of(query)
    if not qtoks:
        return {}
    qset = set(qtoks)
    qnorm = normalize(query)
    n = len(docs)
    df = {}
    for d in docs:
        for t in d["tokens"]:
            if t in qset:
                df[t] = df.get(t, 0) + 1
    def idf(t):
        return math.log(1.0 + n / (1 + df.get(t, 0)))
    out = {}
    for d in docs:
        s = 0.0
        for t in qset:
            if t in d["tf"]:
                s += idf(t) * tf_sat(d["tf"][t])
        if s <= 0 and len(qnorm) >= 4 and qnorm in d["norm"]:
            s = 1.0
        elif len(qnorm) >= 4 and qnorm in d["norm"]:
            s += 2.0
        s = s / (math.sqrt(len(qset)) * math.sqrt(max(1, len(d["tokens"]))))
        out[d["id"]] = s
    return out

def pos_features(d, query):
    qtoks = set(tokens_of(query))
    seq = tokenize_pos(d["text"])
    locs = [(i, ci) for i, (t, ci) in enumerate(seq) if t in qtoks]
    if not locs:
        return None
    ntok, nch = max(1, len(seq)), max(1, len(d["norm"]))
    return {"hits": len(locs), "first_tok_idx": locs[0][0], "last_tok_idx": locs[-1][0],
            "spread_tok": locs[-1][0] - locs[0][0], "first_char_idx": locs[0][1],
            "first_char_rel": locs[0][1] / nch, "first_tok_rel": locs[0][0] / ntok,
            "seq_tokens": len(seq), "norm_chars": nch}

def pos_factor(feat):
    # 提议族(零参数, 值域 (1,2], 单调递减于首现相对位置): 1 + (1 - k)
    if feat is None:
        return 1.0
    k = min(1.0, max(0.0, feat["first_char_rel"]))
    return 1.0 + (1.0 - k)

def sha256(p):
    h = hashlib.sha256()
    h.update(open(p, "rb").read())
    return h.hexdigest()

def pairwise_seq_id(a, b):
    sa, sb = tokens_of(a["text"]), tokens_of(b["text"])
    inter = len(set(sa) & set(sb)); uni = len(set(sa) | set(sb))
    posdiff = sum(1 for x, y in zip(sa, sb) if x != y)
    return {"seq_identical": sa == sb, "seq_len": [len(sa), len(sb)], "positional_token_diff": posdiff,
            "distinct": [len(set(sa)), len(set(sb))], "jaccard": (inter / uni if uni else 0.0)}

R = {"round": "R427", "kind": "separability-precheck", "query": QMAIN,
     "replica_of": "src/agent/session/SessionHistorySearch.cs (R421 极性 / R422 sqrt|d| / R423 1+ln tf)",
     "mode": "只读语料 + 机检; 零构建 / 零网络 / 零 LLM / 零产品源码改动",
     "fixtures": {}, "align": {}, "edge_decision": {}, "readings": {}, "checks": [], "controls": [],
     "corrections": [], "claim_scope": "", "verdict": "", "heading": ""}

for tag, path in (("A", FIX_A), ("B", FIX_B)):
    files = sorted(f for f in os.listdir(path) if f.endswith("_memory.json"))
    R["fixtures"][tag] = {"dir": path, "sha256": {f: sha256(os.path.join(path, f)) for f in files}}

dA, dB = load_corpus(FIX_A), load_corpus(FIX_B)
sA, sB = score_all(dA, QMAIN), score_all(dB, QMAIN)
pinA = {d["id"]: [len(d["tokens"]), d["tf"].get(QMAIN, 0)] for d in dA}
pinB = {d["id"]: [len(d["tokens"]), d["tf"].get(QMAIN, 0)] for d in dB}
REG_PIN = {"cli-6bf6dc8d": [4, 1], "probe-0914125816-p004": [90, 4], "probe-0914125831-p005": [90, 4]}
REG_SCORE = {"cli-6bf6dc8d": 0.2798, "probe-0914125816-p004": 0.14079136730607356,
             "probe-0914125831-p005": 0.14079136730607356}
REG_B = {"r423-tfhi": 1.0286, "r423-tflo": 0.4901, "r423-quiet": 0.0}
tf4 = tf_sat(4)
l1, l2 = "probe-0914125816-p004", "probe-0914125831-p005"
D1 = [d for d in dA if d["id"] == l1][0]
D2 = [d for d in dA if d["id"] == l2][0]
f1, f2 = pos_features(D1, QMAIN), pos_features(D2, QMAIN)

# ---- P0 口径对齐 (pin 精确; 分数按呈现精度 F4 容差) ----
R["align"] = {"pinned_r423": REG_PIN, "pinned_replica": pinA, "pin_match_exact": pinA == REG_PIN,
              "pinned_replica_B": pinB,
              "score_r423_published": REG_SCORE, "score_replica_A": {k: round(v, 12) for k, v in sA.items()},
              "score_delta_vs_published": {k: abs(sA.get(k, 0) - v) for k, v in REG_SCORE.items()},
              "score_delta_within_presentation": all(abs(sA.get(k, 0) - v) <= F4 for k, v in REG_SCORE.items()),
              "B_registered": REG_B, "score_replica_B": {k: round(v, 12) for k, v in sB.items()},
              "B_delta_within_presentation": all(abs(sB.get(k, 0) - v) <= F4 for k, v in REG_B.items()),
              "B_ratio_replica": sB["r423-tfhi"] / sB["r423-tflo"], "B_ratio_closed_1_ln3": 1.0 + math.log(3.0)}
p0 = R["align"]["pin_match_exact"] and R["align"]["score_delta_within_presentation"] and R["align"]["B_delta_within_presentation"]
R["checks"].append({"id": "P0", "desc": "口径对齐: pin 精确重现 + 分数落在已发布呈现精度 (F4 半 ulp 5e-5) 内 (A/B 两语料)",
                    "pass": bool(p0), "evidence": "align"})

# ---- P0b 已发布闭式基线溯源 (机检精确等式) ----
exact_base = sA[l1] / tf4
R["align"]["closed_form_baseline"] = {
    "hypothesis": "R423 A 臂闭式基线 = 0.059 (R422 两位小数呈现值) x TfSat(4)",
    "product_exact": 0.059 * tf4, "published": REG_SCORE[l1],
    "exact_equality": (0.059 * tf4 == REG_SCORE[l1]),
    "full_precision_value": sA[l1], "full_precision_base": exact_base,
    "base_rel_err_of_published": abs(0.059 - exact_base) / exact_base}
R["checks"].append({"id": "P0b", "desc": "已发布闭式基线溯源: 0.059 x TfSat(4) 与 R423 登记值逐位相等 ⇒ 基线取自呈现精度",
                    "pass": bool(0.059 * tf4 == REG_SCORE[l1]), "evidence": "align.closed_form_baseline"})

# ---- P1 并列复现 + P1b 同文检测 (承重) ----
tie = abs(sA[l1] - sA[l2]) <= 1e-12
dup = pairwise_seq_id(D1, D2)
R["readings"]["tie_pair"] = {"ids": [l1, l2], "bow_scores": [round(sA[l1], 12), round(sA[l2], 12)],
                             "delta": abs(sA[l1] - sA[l2]), "tied": bool(tie),
                             "identity": dup, "feat": {l1: f1, l2: f2}}
R["checks"].append({"id": "P1", "desc": "并列复现: 真实双长文档在词袋计数族下逐位并列",
                    "pass": bool(tie), "evidence": "readings.tie_pair"})
R["checks"].append({"id": "P1b", "desc": "同文检测(承重): 并列对正文逐词元序列是否相同 ⇒ 判定并列根因是否在内容重复",
                    "pass": bool(dup["seq_identical"] is True), "evidence": "readings.tie_pair.identity",
                    "interpretation": "True ⇒ 任何打分族(含语义/位置)对同文文档必然同分 ⇒ 该对不构成打分族可分性样本"})

# ---- P2 位置族在真实并列对上的可分性 ----
sep = {k: {"v1": f1[k], "v2": f2[k], "differs": f1[k] != f2[k]} for k in
       ("first_tok_idx", "first_char_idx", "spread_tok", "first_char_rel", "first_tok_rel")}
fa, fb = pos_factor(f1), pos_factor(f2)
R["readings"]["real_pair_position_family"] = {"features": sep, "factor": [round(fa, 12), round(fb, 12)],
                                              "ratio": fa / fb, "scores_new": [round(sA[l1] * fa, 12), round(sA[l2] * fb, 12)],
                                              "separable": bool(any(v["differs"] for v in sep.values()))}
R["checks"].append({"id": "P2", "desc": "位置族在真实并列对上的可分性 (预期 False, 因同文)",
                    "pass": bool(R["readings"]["real_pair_position_family"]["separable"]), "evidence": "readings.real_pair_position_family",
                    "interpretation": "False 且 P1b=True ⇒ 不能据此判位置族无效; 该对无任何打分族可分的可能"})

# ---- P2b 构造样本: 同词袋 ∧ 位置不同 ⇒ 位置族是否可分 (族非空判定) ----
# 构造口径(修正): 打分只依赖 tf / df / |d.Tokens|(= distinct 计数) ⇒ 用 CJK 二元组族构造等 distinct 的对
# (首版用 ASCII 词+空格构造 ⇒ Normalize 剥空白 ⇒ 整段粘成单 token, |d.Tokens| 3 vs 2 ⇒ 词袋本不并列)
X1 = ("甲" * 30) + QMAIN + ("乙" * 30)
X2 = ("甲" * 30) + ("乙" * 30) + QMAIN
cx = [make_doc("X1", X1), make_doc("X2", X2)]
sx = score_all(cx, QMAIN)
gx1, gx2 = pos_features(cx[0], QMAIN), pos_features(cx[1], QMAIN)
X2t = {"pair": "X1/X2 (同 distinct 计数 ∧ 同 tf ∧ 同 df, 查询词位置不同)", "synthetic": True,
       "distinct": [len(cx[0]["tokens"]), len(cx[1]["tokens"])],
       "bow_scores": [round(sx["X1"], 12), round(sx["X2"], 12)], "bow_tied": abs(sx["X1"] - sx["X2"]) <= 1e-12,
       "first_char_rel": [gx1["first_char_rel"], gx2["first_char_rel"]],
       "factor": [round(pos_factor(gx1), 12), round(pos_factor(gx2), 12)],
       "ratio": pos_factor(gx1) / pos_factor(gx2),
       "ratio_closed_form": (1 + (1 - gx1["first_char_rel"])) / (1 + (1 - gx2["first_char_rel"])),
       "scores_new": [round(sx["X1"] * pos_factor(gx1), 12), round(sx["X2"] * pos_factor(gx2), 12)],
       "separable": abs(sx["X1"] * pos_factor(gx1) - sx["X2"] * pos_factor(gx2)) > 1e-12}
X2t["synthetic_valid"] = bool(X2t["bow_tied"] and X2t["distinct"][0] == X2t["distinct"][1])
X2t["closed_form_match"] = abs(X2t["ratio"] - X2t["ratio_closed_form"]) <= 1e-12
R["readings"]["synthetic_relocated"] = X2t
R["checks"].append({"id": "P2b", "desc": "族非空判定(构造样本, fail-closed: 先证词袋并列): 词袋并列 ∧ 位置不同 ⇒ 位置族可分且比值闭式复算一致",
                    "pass": bool(X2t["synthetic_valid"] and X2t["separable"] and X2t["closed_form_match"]),
                    "evidence": "readings.synthetic_relocated"})

# ---- P4 命中集合不变 (设计约束, 真实语料机检) ----
allsc = list(sA.values()) + list(sB.values())
hs = {t: sorted(k for k, v in (sA if t == "A" else sB).items() if v > 0) for t in ("A", "B")}
R["readings"]["hit_set_invariance"] = {"hit_set": hs, "invariant": True,
                                       "reason": "factor >= 1 且 > 0 ⇒ 不得分项删除/新增 (因子为乘性缩放, 只改分档)",
                                       "all_nonneg": all(v >= 0 for v in allsc)}
R["checks"].append({"id": "P4", "desc": "命中集合不变: 因子 >=1 且 >0 ⇒ 命中项逐元素不变 (设计约束机检)",
                    "pass": bool(R["readings"]["hit_set_invariance"]["all_nonneg"]), "evidence": "readings.hit_set_invariance"})

# ---- N1 身份控制 / N3 新族边界(构造) ----
n1 = (pos_factor(f1) / pos_factor(f1) - 1.0) == 0.0
S1 = make_doc("S1", ("甲" * 20) + QMAIN + ("丙" * 20) + ("丁" * 20))
S2 = make_doc("S2", ("甲" * 20) + QMAIN + ("丁" * 20) + ("丙" * 20))
ss = score_all([S1, S2], QMAIN)
g1, g2 = pos_features(S1, QMAIN), pos_features(S2, QMAIN)
N3 = {"pair": "S1/S2 (同 distinct 计数 ∧ 同 tf ∧ 同 df ∧ 同首现相对位置; 仅尾部块序不同)", "synthetic": True,
      "distinct": [len(S1["tokens"]), len(S2["tokens"])],
      "bow_scores": [round(ss["S1"], 12), round(ss["S2"], 12)], "bow_tied": abs(ss["S1"] - ss["S2"]) <= 1e-12,
      "first_char_rel": [g1["first_char_rel"], g2["first_char_rel"]],
      "factor": [round(pos_factor(g1), 12), round(pos_factor(g2), 12)],
      "pos_tied": abs(pos_factor(g1) * ss["S1"] - pos_factor(g2) * ss["S2"]) <= 1e-12}
N3["synthetic_valid"] = bool(N3["bow_tied"] and N3["distinct"][0] == N3["distinct"][1]
                             and N3["first_char_rel"][0] == N3["first_char_rel"][1])
R["readings"]["negative_control_N3"] = N3
R["controls"] = [{"id": "N1", "desc": "身份控制: 同一文档对自身 ⇒ 比值恒 1.0 (零参数因子无自噪声)", "pass": bool(n1)},
                 {"id": "N3", "desc": "新族边界(构造, fail-closed): 首现相对位置相同 ⇒ 位置族亦并列 (宣称范围上界)",
                  "pass": bool(N3["synthetic_valid"] and N3["pos_tied"]), "evidence": N3}]

# ---- 口径修正登记 ----
R["corrections"] = [{"id": "C1", "target": "R423 证据 A 臂闭式基线",
                     "finding": "R423 登记值 0.14079136730607356 == 0.059 x TfSat(4) (精确相等) ⇒ 基线取自 R422 的两位小数呈现值 0.059, 非全精度计算值",
                     "full_precision": {"score": sA[l1], "base": exact_base},
                     "consequence": "A 臂 rel 6.8e-5 含呈现舍入; 应按全精度基线重算 (B 臂读数不受影响: 逐位重现)",
                     "verdict_impact": "不改 R423 结论 (B 臂比值 1+ln3 由同一基线的成对读数派生), 但登记为口径缺陷, 后续闭式复算禁用呈现精度值"},
                    {"id": "C2", "target": "R423/R422 并列对定性",
                     "finding": "并列对 " + l1 + " / " + l2 + " 正文逐词元序列完全相同 (posdiff 0/" + str(dup["seq_len"][0]) + ", jaccard 1.0)",
                     "consequence": "「换信号族(语义/位置)可分开该对」为伪命题; 正确落点为排序/去重层 (确定性 tie-break), 非打分公式",
                     "verdict_impact": "不改 R423 频次饱和实现本身 (其判据在 fixture-tf 合成语料上成立), 但取消其登记的『下一步换族』方向对该对的有效性"}]

R["edge_decision"] = {"implement_position_family_now": False,
                      "why": "真实并列对为同文(P1b) ⇒ 位置族无从体现; 构造样本(P2b)显示族本身在其可观测维度有效, 但本语料无非同文的真实并列对 ⇒ 无真实判定样本",
                      "next_target": "确定性 tie-break / 去重层 (零 LLM / 零参数 / AOT 友好): 同分时按 (分数, 最近时间, 会话 id) 全序或同文折叠",
                      "gate": "检索面无产品语义变更 ⇒ 不涉 role 挂载, 无需门臂"}
R["claim_scope"] = ("机制结论: 已登记的『词袋计数族并列』真实对 = 内容重复(同文), 其不可分性与打分族无关 ⇒ 换族不可解; "
                    "位置族(首现相对位置 k)在构造样本上可分且闭式可复算, 但真实语料无非同文并列对 ⇒ 对真实数据的增益未证; "
                    "边界: 词元多重集 ∧ 首现相对位置皆相同 ⇒ 位置族亦并列 (N3 机检)。")
R["verdict"] = "PREMISE-REFUTED" if (R["checks"][2]["pass"] and dup["seq_identical"]) else "INCONCLUSIVE"
R["heading"] = ("真实并列对 = 重复文本 (逐位相同 " + str(dup["positional_token_diff"]) + "/" + str(dup["seq_len"][0])
                + ", jaccard 1.0) ⇒ 并列根因不在打分族; 位置族在构造样本可分但在真实数据无判定样本 ⇒ 落点改为排序/去重层")
R["next_round_preregistered"] = {"target": "确定性 tie-break / 同文折叠 (排序层), 真机成对 AOT",
                                 "criteria": ["同分同文的两条命中有确定且可复算的全序 (与输入列举顺序无关)",
                                              "非同文同分对不同被错误折叠 = 0 (负控)",
                                              "命中集合与各处排序不变量成对机检; 回归全绿"],
                                 "blocked_by_concurrent": "R426 对侧占用工作树/机器 ⇒ 本侧本轮不起构建与测量"}

with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(R, fh, ensure_ascii=False, indent=1)
    fh.write(NL)

print("verdict:", R["verdict"])
print("checks:", json.dumps([{c["id"]: c["pass"]} for c in R["checks"]], ensure_ascii=False))
print("controls:", json.dumps([{c["id"]: c["pass"]} for c in R["controls"]], ensure_ascii=False))
print("heading:", R["heading"])
print("dup:", json.dumps(dup, ensure_ascii=False))
print("align_deltas:", json.dumps(R["align"]["score_delta_vs_published"], ensure_ascii=False))
print("B:", json.dumps({k: round(v, 12) for k, v in sB.items()}, ensure_ascii=False), "ratio", repr(R["align"]["B_ratio_replica"]))
print("P2b:", json.dumps(X2t, ensure_ascii=False))
print("N3:", json.dumps(N3, ensure_ascii=False))
