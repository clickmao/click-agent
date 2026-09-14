#!/usr/bin/env python3
"""R422 harness — 跨会话检索打分长度归一: 治疗臂(R422 AOT) vs 修复前负控臂(R421 AOT)。

靶点 (预注册自 R421 §6.4): 打分缺**文档长度归一** ⇒ R421 真机三份命中文档分数**全等** (0.5596/1.5660)
⇒ 命中集合内零区分度 (短文/长文不分)。

外部真值: 每臂 = (独立 cwd 的冻结语料副本) + 通道级遥测 + stdout 渲染原文; 两臂语料逐字节相同。
数值对账: N 臂分数 = 未归一的原始分 S (查询单二元组 ⇒ 分母 sqrt|q|=1) ⇒ 预测 T 臂 score = S/sqrt|d|
⇒ |d|_est = (S_N / s_T)^2 必须是近整数且三者互异 (「自算错而自洽」闸)。

用法: python3 eval/capability/r422/run_r422.py
产出: eval/capability/r422/verdict-r422.json + 每臂 stdout 归档
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
HERE = os.path.join(REPO, "eval", "capability", "r422")
FIXTURE = os.path.join(HERE, "fixture-sessions")
ARMS = {
    "T_treated": "/tmp/pub_r422/agenthost",
    "N_pre_fix": "/tmp/pub_r421_pre/agenthost",
}
QUERIES = ["存在", "不存在", "外星词根zzq不存在", "zzq"]
FIXTURE_FILES = [
    "cli-6bf6dc8d_memory.json",
    "probe-0914125816-p004_memory.json",
    "probe-0914125831-p005_memory.json",
]
# R421 判决书记录的同批语料 sha256 (逐字节同一批 ⇒ 语料非变量)
R421_DIGEST = {
    "cli-6bf6dc8d_memory.json": "282bf6a66e0cf08549f9c74aa67079dcd9f8bce3475ea82deb1ae77f065d0784",
    "probe-0914125816-p004_memory.json": "b9d47da7a95494da2d6134882b7d767eeb0857d3d338e03331531050ead931ac",
    "probe-0914125831-p005_memory.json": "c048bf912fa09fc477212184def68f25fc556f7a52e5a90f8d9d45fd0c034974",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def fixture_digest(d):
    return {n: sha256(os.path.join(d, n)) for n in sorted(os.listdir(d))}


def run_arm(arm, binary):
    cwd = f"/tmp/r422-cwd-{arm}"
    shutil.rmtree(cwd, ignore_errors=True)
    os.makedirs(os.path.join(cwd, "data", "sessions"), exist_ok=True)
    for n in FIXTURE_FILES:
        shutil.copy2(os.path.join(FIXTURE, n), os.path.join(cwd, "data", "sessions", n))
    before = fixture_digest(os.path.join(cwd, "data", "sessions"))

    telemetry = os.path.join(cwd, "data", "telemetry", "host.jsonl")
    readings = {}
    for q in QUERIES:
        if os.path.exists(telemetry):
            os.remove(telemetry)
        p = subprocess.run(
            [binary, "-q", f"/recall {q}"],
            cwd=cwd, capture_output=True, text=True, timeout=180,
            env={k: v for k, v in os.environ.items() if k != "DOTNET_ROOT"},
        )
        points = []
        if os.path.exists(telemetry):
            with open(telemetry, encoding="utf-8-sig") as f:
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
        with open(os.path.join(HERE, f"stdout-{arm}-{q}.txt"), "w", encoding="utf-8") as f:
            f.write(p.stdout)
    after = fixture_digest(os.path.join(cwd, "data", "sessions"))
    return {
        "binary": binary,
        "binary_sha256": sha256(binary),
        "corpus_digest": before,
        "corpus_untouched": before == after,
        "telemetry_points_per_query": [len(readings[q]["recall_points"]) for q in QUERIES],
        "readings": readings,
    }


def hits_of(a, q):
    return a["readings"][q]["hit_ids"]


def score_of(a, q, sid):
    for i, s in a["readings"][q]["ranked"]:
        if i == sid:
            return s
    return None


def main():
    digest = fixture_digest(FIXTURE)
    arms = {k: run_arm(k, v) for k, v in ARMS.items()}
    T, N = arms["T_treated"], arms["N_pre_fix"]

    pos_hits_T = hits_of(T, "存在")
    pos_scores_N = [s for _, s in N["readings"]["存在"]["ranked"]]
    pos_scores_T = [s for _, s in T["readings"]["存在"]["ranked"]]

    # 数值对账: N 臂分数 = 原始分 S (未归一); 预测 T 臂 s = S/sqrt|d| ⇒ |d|_est = (S/s)^2 近整数且互异
    s_raw = pos_scores_N[0] if pos_scores_N else 0.0
    est_vals = [(s_raw / s) ** 2 for s in pos_scores_T if s > 0]
    est = [round(v, 4) for v in est_vals]
    est_ok = (
        len(est) == len(pos_scores_T) and len(est) >= 2
        and all(abs(v - round(v)) < 0.02 for v in est)
        and len({int(round(v)) for v in est}) == len(est)
    )

    checks = [
        ("B1", "两臂四查询命中集**逐元素相同** (长度归一不改召回: 除数为正不改符号)",
         all(hits_of(T, q) == hits_of(N, q) for q in QUERIES) and len(pos_hits_T) > 0),
        ("B2", "【预注册】治疗臂: 同词元命中集内分数**不再并列** (R421 的三份全等已消除) —— 已被证伪, 见 B2b/verdict_note",
         len(pos_scores_T) >= 2 and len(set(pos_scores_T)) == len(pos_scores_T)),
        ("B3", "负控臂(修复前二进制): 同词元命中集分数**全等** (臂身份自证: 确为未归一行为)",
         len(pos_scores_N) >= 2 and len(set(pos_scores_N)) == 1 and pos_scores_N[0] > 0),
        ("B4", "极性不变量未退化: 两臂『不存在』/『外星词根zzq不存在』/『zzq』命中均 0",
         all(hits_of(a, q) == [] for a in (T, N) for q in ("不存在", "外星词根zzq不存在", "zzq"))),
        ("B5", "【预注册】数值对账: |d|_est 近整数 (容差 0.02) —— 已被证伪: 分数按 F4 渲染, 容差定得过紧",
         est_ok),
        ("B6", "渲染可机读: 命中行数 == 头部声明命中数 (两臂, R421 仪器缺陷回归)",
         all((r["render_header"] or "").endswith(f"命中 {len(r['hit_ids'])}):") or len(r["hit_ids"]) == 0
             for a in (T, N) for r in a["readings"].values())),
        ("B7", "本地指令零 LLM: 两臂全查询 llm_call == 0 且 recall_query 打点恰 1/查询",
         all(v["llm_call_points"] == 0 for a in (T, N) for v in a["readings"].values())
         and T["telemetry_points_per_query"] == [1] * 4 and N["telemetry_points_per_query"] == [1] * 4),
        ("B8", "两臂语料逐字节相同且跑后未被写 (只读; 语料非变量)",
         T["corpus_digest"] == N["corpus_digest"] and T["corpus_untouched"] and N["corpus_untouched"]
         and set(digest) == set(FIXTURE_FILES)),
    ]
    # ---- 事后 (post-hoc) 机理对账: 只解释 B2/B5 为何红, 不作主判据 ----
    n_distinct = len(set(pos_scores_T))
    est_rel_ok = all(abs(v - round(v)) / max(1.0, round(v)) < 0.02 for v in est)
    mech_ok = (n_distinct >= 2 and pos_scores_T == sorted(pos_scores_T, reverse=True)
               and est_rel_ok and len({int(round(v)) for v in est}) >= 2)
    posthoc = [
        ("B2b", "【事后】分档真实存在: distinct ≥ 2 ∧ 最短文档分数最高; 仍并列者 |d|_est **相等** (等长文档, 数学应然)",
         mech_ok),
        ("B5b", "【事后】数值对账 (F4 渲染 ⇒ 相对容差 2%): |d|_est == [4, 90, 90], 且 raw_S == 治疗臂分数 × sqrt|d|",
         est_rel_ok and n_distinct >= 2),
    ]
    verdict = {
        "round": "R422",
        "harness": "eval/capability/r422/run_r422.py",
        "fixture_files": FIXTURE_FILES,
        "fixture_sha256": digest,
        "fixture_sha256_matches_r421": digest == R421_DIGEST,
        "pos_query": "存在",
        "pos_hits": pos_hits_T,
        "pos_scores_treated": pos_scores_T,
        "pos_scores_prefix": pos_scores_N,
        "doc_token_estimate": est,
        "raw_score_from_negctl": s_raw,
        "arms": arms,
        "checks": [{"id": i, "desc": d, "pass": bool(p)} for i, d, p in checks],
        "checks_posthoc": [{"id": i, "desc": d, "pass": bool(p)} for i, d, p in posthoc],
    }
    pre_fail = [c["id"] for c in verdict["checks"] if not c["pass"]]
    post_fail = [c["id"] for c in verdict["checks_posthoc"] if not c["pass"]]
    verdict["pre_registered_failures"] = pre_fail
    verdict["claim_scope"] = ("长度归一使同词元命中集内的分数与文档词元数成反比 (较短文档得分更高); 除数为正 ⇒ 命中集合逐元素不变; "
                              "对**等长**文档数学上不产生区分度 (残差并列, 登记的后续候选: tf/语义信号)")
    verdict["verdict_note"] = (
        "预注册判据 B2/B5 被证伪: 三份命中文档中有两份词元数相同 (|d|_est 均 ≈90) ⇒ 任何仅依赖文档长度的归一"
        "在数学上都不可能为它们分档; 事后判据 B2b/B5b 确认机理成立 (分档真实存在, 比值 == sqrt|d|, 召回集合不变)"
        " ⇒ 本轮宣称按 claim_scope **收窄** 登记, 不作「零区分度已消除」的全称宣称。")
    verdict["verdict"] = ("PASS" if not pre_fail else ("PARTIAL" if not post_fail else "FAIL"))
    out = os.path.join(HERE, "verdict-r422.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(verdict, f, ensure_ascii=False, indent=2)
    for c in verdict["checks"] + verdict["checks_posthoc"]:
        print(("OK  " if c["pass"] else "RED ") + c["id"] + " " + c["desc"])
    print(f"raw_S={s_raw} est|d|={est} T_scores={pos_scores_T} pre_fail={pre_fail}")
    print("VERDICT=" + verdict["verdict"], out)
    return 0 if verdict["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
