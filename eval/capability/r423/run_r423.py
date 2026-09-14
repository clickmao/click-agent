#!/usr/bin/env python3
"""R423 harness — 词元频次饱和打分 (分子 ×(1+ln tf)): 治疗臂(R423 AOT) vs 负控臂(R422 AOT)。

登记靶点 (R422 收窄宣称后的残差候选): 打分为「词元是否命中 + 长度归一」= presence 口径 ⇒
「提到 1 次」与「提到 N 次」的文档同分 (族内可用信号未被使用)。

本轮**先做可分性预检** (设计前 sanity check, 见 README-evidence §1):
  对 R422 真机并列对做特征向量逐项对照 ⇒ 两份长文档 distinct 词元数 87/87 ∧ tf(存在) 2/2
  **逐项相等** ⇒ 频次信号对该对**恒为空操作** (数学上不可分, 不是「效果有限」)。
  ⇒ 该并列登记为**词袋计数信号族的不可分边界**; 本轮宣称收窄为:
     「频次信号可区分**等长但出现次数不同**的文档; 次数与词元数皆相同者仍并列」。

外部真值: 每臂每语料 = 独立 cwd 的冻结语料副本 + 通道级遥测 + stdout 渲染原文; 两臂语料逐字节相同。
闭式对账 (与实现独立可算 ⇒ 防「自算错而自洽」):
  单词元查询下 分数 = Idf(t)·(1+ln tf)/sqrt(|q|·|d|) ⇒
   · 语料 B (等长 |d|=2, tf 3 vs 1): T 臂比值 == 1+ln3 = 2.098612; N 臂必须**全等** (臂身份自证)
   · 语料 A (R422 冻结语料): tf=1 文档分数**逐位不变**; tf=2 文档 == R422 登记值 ×(1+ln2)=1.693147

用法: python3 eval/capability/r423/run_r423.py
产出: eval/capability/r423/verdict-r423.json + stdout-<arm>-<corpus>-<query>.txt (证据归档)
"""
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
HERE = os.path.join(REPO, "eval", "capability", "r423")
R422_VERDICT = os.path.join(REPO, "eval", "capability", "r422", "verdict-r422.json")
FIXTURES = {
    "A": os.path.join(REPO, "eval", "capability", "r422", "fixture-sessions"),  # R422 冻结语料 (回归)
    "B": os.path.join(HERE, "fixture-tf"),                                      # R423 等长可分对 (主靶)
}
ARMS = {
    "T_treated": "/tmp/pub_r423/agenthost",   # R423 = presence + 长度归一 + 频次饱和
    "N_pre_fix": "/tmp/pub_r422/agenthost",   # R422 = presence + 长度归一 (无频次)
}
QUERIES = {
    "A": ["存在", "不存在", "外星词根zzq不存在", "zzq"],
    "B": ["存在", "不存在"],
}
# R421 判决书记录的同批语料 sha256 (语料非变量; R422 已核过, 本轮复核)
R421_DIGEST = {
    "cli-6bf6dc8d_memory.json": "282bf6a66e0cf08549f9c74aa67079dcd9f8bce3475ea82deb1ae77f065d0784",
    "probe-0914125816-p004_memory.json": "b9d47da7a95494da2d6134882b7d767eeb0857d3d338e03331531050ead931ac",
    "probe-0914125831-p005_memory.json": "c048bf912fa09fc477212184def68f25fc556f7a52e5a90f8d9d45fd0c034974",
}
LONG_DOCS = ["probe-0914125816-p004", "probe-0914125831-p005"]
SHORT_DOC = "cli-6bf6dc8d"
# 冻结语料特征向量 (distinct 词元数, tf(存在)) —— **机检钉死** (单测
# R423_FrozenCorpus_FeatureVector_IsMachinePinned_NotHandCounted: 真实存储 Load + 文档构建 + 真实分词器)。
# 严禁人工复算: 首版手算只读了长期记忆段、漏了目标/里程碑段 ⇒ tf 算成 2 (真值 4), 被 C4 当场证伪。
FROZEN_FEATURE = {
    SHORT_DOC: (4, 1),
    "probe-0914125816-p004": (90, 4),
    "probe-0914125831-p005": (90, 4),
}
TOL = 0.015          # F4 渲染 (4 位小数) ⇒ 相对容差 1.5%
TOL_EXACT = 0.002    # tf=1 ⇒ 因子恒 1 ⇒ 只允许渲染舍入


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def fixture_digest(d):
    """只对**文件**取摘要 (目录被计入会让'语料未变'的判据被目录副作用掩盖, 见 README §5 事故)"""
    return {n: sha256(os.path.join(d, n)) for n in sorted(os.listdir(d)) if os.path.isfile(os.path.join(d, n))}


def run_arm(arm, corpus_key, binary):
    fixture = FIXTURES[corpus_key]
    files = [n for n in sorted(os.listdir(fixture)) if os.path.isfile(os.path.join(fixture, n))]
    cwd = f"/tmp/r423-cwd-{arm}-{corpus_key}"
    shutil.rmtree(cwd, ignore_errors=True)
    os.makedirs(os.path.join(cwd, "data", "sessions"), exist_ok=True)
    for n in files:
        shutil.copy2(os.path.join(fixture, n), os.path.join(cwd, "data", "sessions", n))
    before = fixture_digest(os.path.join(cwd, "data", "sessions"))

    telemetry = os.path.join(cwd, "data", "telemetry", "host.jsonl")
    readings = {}
    for q in QUERIES[corpus_key]:
        if os.path.exists(telemetry):
            os.remove(telemetry)
        p = subprocess.run(
            [binary, "-q", f"/recall {q}"],
            cwd=cwd, capture_output=True, text=True, timeout=180,
            env={k: v for k, v in os.environ.items() if k != "DOTNET_ROOT"},
        )
        points = []
        if os.path.exists(telemetry):
            with open(telemetry, encoding="utf-8-sig", errors="replace") as f:
                for ln in f:
                    ln = ln.strip()
                    if ln:
                        try:
                            points.append(json.loads(ln))
                        except json.JSONDecodeError:
                            points.append({"raw": ln})
        rq = [x for x in points if x.get("point") == "recall_query"]
        llm = [x for x in points if x.get("point") == "llm_call"]
        header = [l for l in p.stdout.splitlines() if "跨会话检索" in l]
        ranked = [(m.group(1), float(m.group(2)))
                  for m in re.finditer(r"(\S+)\s+score=([0-9.]+)\s+entries=", p.stdout)]
        readings[q] = {
            "rc": p.returncode,
            "recall_points": rq,
            "llm_call_points": len(llm),
            "render_header": header[0] if header else None,
            "hit_ids": [i for i, _ in ranked],
            "ranked": ranked,
            "stdout_tail": p.stdout[-240:],
        }
        with open(os.path.join(HERE, f"stdout-{arm}-{corpus_key}-{q}.txt"), "w", encoding="utf-8") as f:
            f.write(p.stdout)
    after = fixture_digest(os.path.join(cwd, "data", "sessions"))
    return {
        "binary": binary,
        "binary_sha256": sha256(binary),
        "corpus_digest": before,
        "corpus_untouched": before == after,
        "telemetry_points_per_query": [len(readings[q]["recall_points"]) for q in QUERIES[corpus_key]],
        "readings": readings,
    }


def rel(a, b):
    return abs(a - b) / max(1e-12, abs(b))


def main():
    reg = json.load(open(R422_VERDICT, encoding="utf-8"))
    reg_scores = {sid: s for sid, s in zip(reg["pos_hits"], reg["pos_scores_treated"])}

    fixtures_sha = {k: fixture_digest(v) for k, v in FIXTURES.items()}
    arms = {(arm, ck): run_arm(arm, ck, bin_) for arm in ARMS for ck in FIXTURES for bin_ in [ARMS[arm]]}
    T = {ck: arms[("T_treated", ck)] for ck in FIXTURES}
    N = {ck: arms[("N_pre_fix", ck)] for ck in FIXTURES}

    def sc(a, ck, q, sid):
        for i, s in a[ck]["readings"][q]["ranked"]:
            if i == sid:
                return s
        return None

    def hits(a, ck, q):
        return a[ck]["readings"][q]["hit_ids"]

    # ---- 语料 B (主靶): 等长 (|d|=2) ∧ tf 3 vs 1 ----
    b_T_hi, b_T_lo = sc(T, "B", "存在", "r423-tfhi"), sc(T, "B", "存在", "r423-tflo")
    b_N_hi, b_N_lo = sc(N, "B", "存在", "r423-tfhi"), sc(N, "B", "存在", "r423-tflo")
    ratio = (b_T_hi / b_T_lo) if (b_T_hi and b_T_lo) else 0.0
    tf_implied = math.exp(ratio - 1.0) if ratio > 0 else 0.0
    pred_ratio = 1.0 + math.log(3.0)

    # ---- 语料 A (R422 冻结语料, 回归 + 闭式对账) ----
    a_short_T = sc(T, "A", "存在", SHORT_DOC)
    a_short_N = sc(N, "A", "存在", SHORT_DOC)
    tf_short = FROZEN_FEATURE[SHORT_DOC][1]
    tf_long = FROZEN_FEATURE[LONG_DOCS[0]][1]
    assert tf_short == 1, "冻结语料 tf=1 是 TOL_EXACT 口径的前提"
    factor_long = 1.0 + math.log(tf_long)
    long_T = [sc(T, "A", "存在", d) for d in LONG_DOCS]
    long_N = [sc(N, "A", "存在", d) for d in LONG_DOCS]
    reg_short, reg_long = reg_scores.get(SHORT_DOC), reg_scores.get(LONG_DOCS[0])
    # 实测隐含 tf (与机检钉死值两源对账): 分数比 == 1 + ln(tf) ⇒ tf = exp(ratio - 1)
    tf_implied_long = [math.exp(v / n - 1.0) for v, n in zip(long_T, long_N) if v and n]

    checks = [
        ("C0", "冻结语料目录**条目集纯净** (只含预期文件, 无子目录/多余条目) —— 事后加的机检:"
               " 被测组件构造副作用曾在语料目录内建出空子目录 (C7 同族污染)",
         all(sorted(n for n in os.listdir(FIXTURES[ck]) if os.path.isfile(os.path.join(FIXTURES[ck], n)))
             == (sorted(R421_DIGEST) if ck == "A" else sorted(
                 ["r423-quiet_memory.json", "r423-tfhi_memory.json", "r423-tflo_memory.json"]))
             and len(os.listdir(FIXTURES[ck])) == 3 for ck in FIXTURES)),
        ("C1", "两臂全查询命中集**逐元素相同** (语料 A 4 查询 + 语料 B 2 查询; 因子 ≥1 不改符号)",
         all(hits(T, ck, q) == hits(N, ck, q) for ck in FIXTURES for q in QUERIES[ck])
         and len(hits(T, "A", "存在")) == 3),
        ("C2", "【主·预注册】语料 B: N 臂两命中文档分数**全等** (臂身份自证: R422 无频次) ∧ T 臂严格分档且 tf 高者高",
         b_N_hi is not None and b_N_hi == b_N_lo and b_T_hi is not None and b_T_hi > b_T_lo),
        ("C3", "【主·预注册】语料 B: T 臂分数比值 == 1+ln3 = 2.098612 (闭式预测, 相对容差 1.5%)",
         ratio > 0 and rel(ratio, pred_ratio) <= TOL),
        ("C4", "【主·预注册】语料 A 闭式对账: tf=1 文档分数**逐位不变** ∧ tf=4 文档 == R422 登记值 ×(1+ln4)"
               " ∧ 实测隐含 tf == 机检钉死值 (两源一致; 预检输入取自机检而非人工复算)",
         a_short_T is not None and a_short_N is not None and reg_short is not None and reg_long is not None
         and rel(a_short_T, reg_short) <= TOL_EXACT
         and all(v is not None and rel(v, reg_long * factor_long) <= TOL for v in long_T)
         and len(tf_implied_long) == 2 and all(abs(v - tf_long) <= 0.05 for v in tf_implied_long)),
        ("C4b", "【臂身份自证】N 臂(R422 二进制) 在语料 A 上读数 == R422 判决书登记值 (逐位: 0.2798/0.059/0.059)"
                " ⇒ 语料与基线臂均为同一物, 差分有意义",
         reg_scores != {} and all(
             sc(N, "A", "存在", sid) is not None and rel(sc(N, "A", "存在", sid), v) <= TOL_EXACT
             for sid, v in reg_scores.items())),
        ("C5", "极性不变量未退化: 负查询 (A: 不存在/外星词根zzq不存在/zzq, B: 不存在) 两臂命中均 0",
         all(hits(a, ck, q) == [] for a in (T, N) for ck in FIXTURES
             for q in QUERIES[ck] if q in ("不存在", "外星词根zzq不存在", "zzq"))),
        ("C6", "渲染可机读 (命中行数 == 头部声明) ∧ 本地指令零 LLM ∧ recall_query 打点恰 1/查询",
         all((r["render_header"] or "").endswith(f"命中 {len(r['hit_ids'])}):") or len(r["hit_ids"]) == 0
             for a in (T, N) for ck in FIXTURES for r in a[ck]["readings"].values())
         and all(v["llm_call_points"] == 0 for a in (T, N) for ck in FIXTURES for v in a[ck]["readings"].values())
         and all(a[ck]["telemetry_points_per_query"] == [1] * len(QUERIES[ck])
                 for a in (T, N) for ck in FIXTURES)),
        ("C7", "两臂语料逐字节相同且跑后未被写 (只读; 语料非变量) ∧ R422 冻结语料 sha 未变 (== R421 登记)",
         all(T[ck]["corpus_digest"] == N[ck]["corpus_digest"] for ck in FIXTURES)
         and all(a[ck]["corpus_untouched"] for a in (T, N) for ck in FIXTURES)
         and fixtures_sha["A"] == R421_DIGEST),
    ]
    # 边界登记 (单列, 非主判据): 词元数与出现次数**皆相同** ⇒ 词袋计数族不可分
    boundary = [
        ("C8", "【边界登记·非缺陷】语料 A 两份长文档 (distinct |d|=90 ∧ tf(存在)=4 逐项相等) 在 R423 下**仍并列**"
               " ⇒ 词袋计数信号族不可分; 需换信号族 (语义/位置), 不再投入同类调参",
         len(long_T) == 2 and long_T[0] is not None and long_T[0] == long_T[1]),
    ]

    verdict = {
        "round": "R423",
        "harness": "eval/capability/r423/run_r423.py",
        "target": "词元频次饱和 (分子 ×(1+ln tf)) + 可分性预检 (频次对等长同频次对恒为空操作)",
        "fixtures": {k: {"dir": v, "sha256": fixtures_sha[k]} for k, v in FIXTURES.items()},
        "fixture_A_sha256_matches_r421": fixtures_sha["A"] == R421_DIGEST,
        "queries": QUERIES,
        "readings_summary": {
            "B_T_tfhi": b_T_hi, "B_T_tflo": b_T_lo, "B_N_tfhi": b_N_hi, "B_N_tflo": b_N_lo,
            "B_ratio_T": ratio, "B_ratio_predicted": pred_ratio, "B_tf_implied_from_ratio": tf_implied,
            "A_short_T": a_short_T, "A_short_N": a_short_N, "A_short_registered_r422": reg_short,
            "A_long_T": long_T, "A_long_registered_r422_x_factor": [reg_long * factor_long if reg_long else None] * 2,
            "A_tf_implied_from_ratio": tf_implied_long,
            "frozen_feature_pinned": FROZEN_FEATURE,
            "factor_tf4": factor_long,
        },
        "arms": {f"{arm}|{ck}": arms[(arm, ck)] for arm, ck in arms},
        "checks": [{"id": i, "desc": d, "pass": bool(p)} for i, d, p in checks],
        "checks_boundary": [{"id": i, "desc": d, "pass": bool(p)} for i, d, p in boundary],
    }
    pre_fail = [c["id"] for c in verdict["checks"] if not c["pass"]]
    verdict["pre_registered_failures"] = pre_fail
    verdict["predictor_correction"] = {
        "run1_artifact": "eval/capability/r423/verdict-r423-run1-predictor-error.json (已归档, 不覆盖)",
        "run1_red": ["C4"],
        "wrong_input": "冻结语料 tf(存在)=2 —— 人工复算时只读了长期记忆段, 漏了目标/里程碑段",
        "corrected_input": f"tf(存在)={tf_long}, distinct 词元数={FROZEN_FEATURE[LONG_DOCS[0]][0]}"
                           " (机检钉死: 真实存储 Load + 文档构建 + 真实分词器, 见单测 R423_FrozenCorpus_FeatureVector_*)",
        "independent_confirmation": "run1 实测隐含 tf = exp(0.1408/0.059 - 1) ≈ 4.000 ⇒ 实现行为符合闭式, 错的是预测输入",
        "criterion_changed": False,
    }
    verdict["claim_scope"] = (
        "词元频次饱和加权 (1+ln tf, 因子 ≥1) 使「等长但出现次数不同」的文档分档, 比值 == 1+ln(tf) (闭式); "
        "因子 ≥1 ⇒ 命中集合逐元素不变 ∧ 极性不变量保持; "
        "对**词元数与出现次数皆相同**的文档对无区分度 (词袋计数信号族不可分边界, 需换信号族)")
    verdict["verdict_note"] = (
        "主判据 C1–C7 全部通过; C8 单列为边界登记 (非缺陷, 不参与红绿)。"
        "本轮先做可分性预检并据其改写靶点: R422 残留并列对的两份文档特征向量逐项相等 "
        "(distinct 90/90 ∧ tf(存在) 4/4, 机检钉死, 首版人工复算的 87/2 已作废) "
        "⇒ 频次信号对该对恒为空操作, 故**未**宣称「R422 残留零区分度已消除」, 只宣称可区分对上的分档 + 闭式对账。"
        "首跑 C4 红且已归档: 红因是**预测输入错** (人工复算 tf=2 vs 真值 4), 判据结构 (比值 == 1+ln tf) 未改。")
    verdict["verdict"] = "PASS" if not pre_fail else "FAIL"
    out = os.path.join(HERE, "verdict-r423.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(verdict, f, ensure_ascii=False, indent=2)
    for c in verdict["checks"] + verdict["checks_boundary"]:
        print(("OK  " if c["pass"] else "RED ") + c["id"] + " " + c["desc"])
    print(f"B: T={b_T_hi}/{b_T_lo} N={b_N_hi}/{b_N_lo} ratio={ratio:.6f} pred={pred_ratio:.6f} tf_implied={tf_implied:.3f}")
    print(f"A: short T={a_short_T} (reg {reg_short}) long T={long_T} (pred {[round(reg_long*factor_long,4) if reg_long else None]*2}) tf_implied={tf_implied_long}")
    print("VERDICT=" + verdict["verdict"], out)
    return 0 if verdict["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
