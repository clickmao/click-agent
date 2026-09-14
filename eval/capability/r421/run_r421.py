#!/usr/bin/env python3
"""R421 harness — /recall 否定极性: 治疗臂 vs 撤销修复负控臂 (同 harness, 只换二进制)。

外部真值: 每臂 = (独立 cwd 的冻结语料副本) + 通道级遥测 (recall_query / llm_call) + stdout 渲染原文。
两臂语料**逐字节相同** (sha256 记录) ⇒ 读数差异只能来自二进制差异 (R420 两臂跨时间跑, 语料漂移不可控 = 本轮修正项)。

用法: python3 eval/capability/r421/run_r421.py
产出: eval/capability/r421/verdict-r421.json + 每臂 host.jsonl / stdout 归档
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

REPO = "/home/agentuser/AgentFramework"
HERE = os.path.join(REPO, "eval", "capability", "r421")
FIXTURE = os.path.join(HERE, "fixture-sessions")
ARMS = {
    "T_treated": "/tmp/pub_r421/agenthost",
    "N_pre_fix": "/tmp/pub_r420_pre/agenthost",
}
QUERIES = ["存在", "不存在", "外星词根zzq不存在", "zzq"]
# 冻结语料 = R420 真机命中文档 (原样快照, 不含任何构造语料)
FIXTURE_FILES = [
    "cli-6bf6dc8d_memory.json",
    "probe-0914125816-p004_memory.json",
    "probe-0914125831-p005_memory.json",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def dir_digest(d):
    items = sorted((n, sha256(os.path.join(d, n))) for n in os.listdir(d))
    return {n: s for n, s in items}


def fixture_digest(d):
    return dir_digest(os.path.join(d, "sessions"))


def run_arm(arm, binary):
    cwd = f"/tmp/r421-cwd-{arm}"
    shutil.rmtree(cwd, ignore_errors=True)
    os.makedirs(os.path.join(cwd, "data", "sessions"), exist_ok=True)
    for n in FIXTURE_FILES:
        shutil.copy2(os.path.join(FIXTURE, n), os.path.join(cwd, "data", "sessions", n))
    digest_before = fixture_digest(os.path.join(cwd, "data"))

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
        rq = [p for p in points if p.get("point") == "recall_query"]
        llm = [p for p in points if p.get("point") == "llm_call"]
        recall_lines = [l for l in p.stdout.splitlines() if "跨会话检索" in l]
        # 逐命中行解析: `N. <id>  score=<f>  entries=<n>` (R421: 渲染曾把命中行与片段粘成一行 ⇒ 读数不可机读)
        ranked = [(m.group(1), float(m.group(2)))
                  for m in re.finditer(r"(\S+)\s+score=([0-9.]+)\s+entries=", p.stdout)]
        hit_ids = [i for i, _ in ranked]
        readings[q] = {
            "rc": p.returncode,
            "recall_points": rq,
            "llm_call_points": len(llm),
            "render_header": recall_lines[0] if recall_lines else None,
            "hit_ids": hit_ids,
            "ranked": ranked,
            "stdout_tail": p.stdout[-260:],
        }
        with open(os.path.join(HERE, f"stdout-{arm}-{q}.txt"), "w", encoding="utf-8") as f:
            f.write(p.stdout)
    # 语料未被写: 检索为只读 + 本地指令不回写会话记忆 (探针不得污染被测语料)
    digest_after = fixture_digest(os.path.join(cwd, "data"))
    return {
        "binary": binary,
        "binary_sha256": sha256(binary),
        "binary_bytes": os.path.getsize(binary),
        "cwd": cwd,
        "corpus_digest": digest_after,
        "corpus_untouched": digest_before == digest_after,
        "telemetry_points_per_query": [len(v["recall_points"]) for v in readings.values()],
        "readings": readings,
    }


def hits_of(arm, q):
    return sorted(arm["readings"][q]["hit_ids"])


def main():
    if not os.path.isdir(FIXTURE):
        print("FIXTURE 缺失: " + FIXTURE)
        return 2
    arms = {k: run_arm(k, v) for k, v in ARMS.items()}
    T, N = arms["T_treated"], arms["N_pre_fix"]

    POS = ["probe-0914125816-p004", "probe-0914125831-p005"]

    def has_pos(arm, q):
        return all(p in hits_of(arm, q) for p in POS)

    def score(arm, q, sid):
        for i, s in arm["readings"][q]["ranked"]:
            if i == sid:
                return s
        return None

    checks = [
        ("A1", "治疗臂: 正控查询『存在』仍召回**两个真实正样本** (召回未被打死)",
         has_pos(T, "存在")),
        ("A2", "治疗臂: 否定查询『不存在』命中 0 (R420 缺陷判据)",
         hits_of(T, "不存在") == []),
        ("A3", "治疗臂: 『外星词根zzq不存在』命中 0",
         hits_of(T, "外星词根zzq不存在") == []),
        ("A4", "治疗臂: 无关词『zzq』命中 0 (阴性对照不退化)",
         hits_of(T, "zzq") == []),
        ("A5", "负控臂(修复前二进制): 『存在』召回到同样两个正样本 (臂有效, 非环境问题)",
         has_pos(N, "存在") and hits_of(N, "存在") == hits_of(T, "存在")),
        ("A6", "负控臂: 『不存在』命中原样复现缺陷 (≥2 真实正样本)",
         has_pos(N, "不存在")),
        ("A7", "负控臂: 『不存在』与『存在』命中集**逐元素相同** (打分对否定无感 = 判别力实证)",
         hits_of(N, "不存在") == hits_of(N, "存在") and has_pos(N, "存在")),
        ("A8", "两臂『不存在』读数相反 ⇒ 差异只能来自二进制 (语料逐字节相同)",
         hits_of(T, "不存在") != hits_of(N, "不存在")),
        ("A9", "两臂语料摘要相同且跑后未被写 (探针不污染被测语料)",
         T["corpus_digest"] == N["corpus_digest"] and T["corpus_untouched"] and N["corpus_untouched"]),
        ("A10", "两臂全查询 llm_call == 0 (本地指令零 LLM, 通道级打点)",
         all(v["llm_call_points"] == 0 for v in T["readings"].values())
         and all(v["llm_call_points"] == 0 for v in N["readings"].values())),
        ("A11", "每查询 recall_query 打点恰 1 (读数非缺省/非重复)",
         T["telemetry_points_per_query"] == [1] * 4 and N["telemetry_points_per_query"] == [1] * 4),
        ("A12", "渲染可机读: 命中行数 == 头部声明的命中数 (R421 仪器缺陷回归)",
         all(
             (r["render_header"] or "").endswith(f"命中 {len(r['hit_ids'])}):") or len(r["hit_ids"]) == 0
             for a in (T, N) for r in a["readings"].values()
         )),
        ("A13", "R420 口径更正: 负控臂两查询**集合相同但分数不同** (非『分数相同』)",
         hits_of(N, "存在") == hits_of(N, "不存在")
         and score(N, "存在", POS[0]) != score(N, "不存在", POS[0])),
    ]
    verdict = {
        "round": "R421",
        "harness": "eval/capability/r421/run_r421.py",
        "fixture_files": FIXTURE_FILES,
        "fixture_sha256": dir_digest(FIXTURE),
        "arms": arms,
        "checks": [{"id": i, "desc": d, "pass": bool(p)} for i, d, p in checks],
    }
    verdict["verdict"] = "PASS" if all(c["pass"] for c in verdict["checks"]) else "FAIL"
    out = os.path.join(HERE, "verdict-r421.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(verdict, f, ensure_ascii=False, indent=2)
    for c in verdict["checks"]:
        print(("OK  " if c["pass"] else "RED ") + c["id"] + " " + c["desc"])
    print("VERDICT=" + verdict["verdict"], out)
    return 0 if verdict["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
