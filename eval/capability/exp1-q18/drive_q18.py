#!/usr/bin/env python3
"""EXP1-Q18 双臂驱动器: 在**同深度**的自洽臂目录里跑完整器具链
   probe --> kind_table --> unit_axis_guard(C1 重放保真)

臂目录必须在 eval/capability/<dir> 深度 (aux 件内 REPO = HERE.parent^3)。
语料 = /tmp/q18_corpus (冻结快照, 本脚本不做任何写入语料的动作)。
"""
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path("/home/agentuser/AgentFramework")
Q18 = ROOT / "eval/capability/exp1-q18"
CORPUS = "/tmp/q18_corpus"
GUARD = ROOT / "eval/capability/exp1-q16/unit_axis_guard.py"
KIND_SRC = ROOT / "eval/capability/exp1-q10/kind_table_v260.py"
ARMS = {
    "v260": {"probe": ROOT / "eval/capability/exp1-q10/probe_v260.py", "dir": ROOT / "eval/capability/q18a-v260"},
    "v270": {"probe": Q18 / "probe_v270.py", "dir": ROOT / "eval/capability/q18a-v270"},
}


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def run(cmd, cwd, log):
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=900)
    pathlib.Path(log).write_text(r.stdout + "\n---STDERR---\n" + r.stderr, encoding="utf-8")
    return r


def main():
    report = {"driver": "drive_q18.py v1.0", "corpus": CORPUS, "arms": {}}
    for name, a in ARMS.items():
        d = a["dir"]
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        probe_dst = d / a["probe"].name
        shutil.copy2(a["probe"], probe_dst)
        entry = {"dir": str(d.relative_to(ROOT)), "probe": probe_dst.name,
                 "probe_sha256": sha(probe_dst), "probe_sha_match_src": sha(probe_dst) == sha(a["probe"])}

        # 1) probe -> attribution_q10.json (+ citations.jsonl / continuations.jsonl)
        r = run([sys.executable, a["probe"].name, "--repo", CORPUS, "--out", "attribution_q10.json"],
                d, Q18 / f"drive_{name}_probe.log")
        entry["probe_rc"] = r.returncode
        entry["attribution_sha256"] = sha(d / "attribution_q10.json")
        entry["citations_sha256"] = sha(d / "citations.jsonl")
        entry["citations_bytes"] = (d / "citations.jsonl").stat().st_size

        # 2) kind_table (辅件: 仅一行改为按臂选探针文件名; 判据器具 guard 零改动)
        kt = d / "kind_table_arm.py"
        src = KIND_SRC.read_text(encoding="utf-8")
        anchor = 'spec_from_file_location("probe_v260", HERE / "probe_v260.py")'
        if anchor not in src:
            entry["kind_table_adapt"] = "ANCHOR_MISSING"
        else:
            repl = ('spec_from_file_location("probe_arm", HERE / ('
                    '"probe_v270.py" if (HERE / "probe_v270.py").is_file() else "probe_v260.py"))')
            kt.write_text(src.replace(anchor, repl), encoding="utf-8")
            entry["kind_table_adapt"] = "one_line_probe_name"
        r = run([sys.executable, "kind_table_arm.py"], d, Q18 / f"drive_{name}_kind.log")
        entry["kind_rc"] = r.returncode
        entry["weak_kind_table_sha256"] = sha(d / "weak_kind_table.json") if (d / "weak_kind_table.json").is_file() else None

        # 3) guard: 重放保真 (C1) —— 逐臂自洽三元组 (src, cites, emit)
        out_json = Q18 / (f"verdict_q18_replay{'_old' if name == 'v260' else ''}.json")
        r = run([sys.executable, str(GUARD), "--run", "--src", probe_dst.name,
                 "--cites", "citations.jsonl", "--emit", "attribution_q10.json",
                 "--json", str(out_json)], d, Q18 / f"drive_{name}_guard.log")
        entry["guard_rc"] = r.returncode
        entry["guard_tail"] = (r.stdout or "").strip().splitlines()[-3:]
        report["arms"][name] = entry
        print(json.dumps(report["arms"][name], ensure_ascii=False))
    (Q18 / "drive_q18.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("DRIVER_DONE")


if __name__ == "__main__":
    main()
