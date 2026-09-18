#!/usr/bin/env python3
"""R549 摄取: 把 R548 的**仓外**运行树固化为仓内不可变快照 (铁律 11 前置条件)。

缺陷(R548 遗留): R548 的读数来自 `/tmp/r548_{d,c2}/r1_{1,2,3}/work`, 运行树落在仓外
⇒ 前置器无法发现 ⇒ 该轮一切降幅只能标「参考(未可验收)」。本轮按字节复制入仓, 并逐文件
记 (bytes, sha256) 供事后校验不可变性; 题面/用例逐字节复用 R547 夹具(sha256 断言)。
"""
import hashlib
import io
import json
import os
import shutil
import sys

REPO = "/home/agentuser/AgentFramework"
R549 = os.path.join(REPO, "eval/rover/r549")
R547 = os.path.join(REPO, "eval/rover/r547")
SRC = {
    "r548b": {1: "/tmp/r548_c2/r1_1/work", 2: "/tmp/r548_c2/r1_2/work", 3: "/tmp/r548_c2/r1_3/work"},
    "r548base": {1: "/tmp/r548_d/r1_1/work", 2: "/tmp/r548_d/r1_2/work", 3: "/tmp/r548_d/r1_3/work"},
}
ARM_DIR = {"r548b": "agentR548b-g1", "r548base": "agentR548base-g1"}
PROMPT_SHA_EXP = "516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def main():
    man = {"round": "R549", "kind": "ingest-outside-run-tree", "source": SRC,
           "note": "仓外运行树 ⇒ 按字节复制(含 __pycache__)入仓; 排除项: 无(逐文件全量)",
           "files": [], "fixture": {}, "prompt_sha256": None}
    for tag, wins in SRC.items():
        for w, srcwork in wins.items():
            dst = os.path.join(R549, "snapshots", "w%d" % w, ARM_DIR[tag], "g1")
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(srcwork, dst)
            for root, _dirs, files in os.walk(dst):
                for fn in sorted(files):
                    p = os.path.join(root, fn)
                    if "/__pycache__/" in p or p.endswith(".pyc"):
                        man["files"].append({"rel": os.path.relpath(p, R549), "bytes": os.path.getsize(p),
                                             "sha256": sha(p), "kind": "pyc(如实在盘, 不判分)"})
                    else:
                        man["files"].append({"rel": os.path.relpath(p, R549), "bytes": os.path.getsize(p),
                                             "sha256": sha(p), "kind": "artifact"})
            print("ingested %-9s w%d -> %s" % (tag, w, os.path.relpath(dst, REPO)))

    # 夹具逐字节复用 R547
    os.makedirs(os.path.join(R549, "cases"), exist_ok=True)
    for fn in ("run_cases_r521.py", "cases-r521.json"):
        s = os.path.join(R547, "cases", fn)
        d = os.path.join(R549, "cases", fn)
        shutil.copy2(s, d)
        man["fixture"][fn] = {"bytes": os.path.getsize(d), "sha256": sha(d), "same_as_r547": sha(s) == sha(d)}

    with io.open(os.path.join(R547, "taskset-r547.json"), encoding="utf-8-sig") as fh:
        ts = json.load(fh)
    prompt = ts["tasks"][0]["prompt"]
    man["prompt_sha256"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    assert man["prompt_sha256"] == PROMPT_SHA_EXP, "题面 sha 与 R547 不一致 ⇒ 非同输入, 停"
    # 与 R548 运行树实际入模的 prompt 逐字节对照 (同输入硬条件)
    with io.open("/tmp/r548_c2/task-g1-prompt.txt", encoding="utf-8") as fh:
        run_prompt = fh.read()
    man["prompt_vs_r548_run_tree"] = {"match": run_prompt.strip() == prompt.strip(),
                                      "run_tree_sha256": hashlib.sha256(run_prompt.encode("utf-8")).hexdigest()}
    ts["round"] = "r549"
    ts["tasks"][0]["cases"] = "cases/run_cases_r521.py"
    ts["note"] = "R549: 题面/用例逐字节复用 R547(g1, 58 用例); 快照为 R548 新契约(r548b)与旧契约(r548base)运行树入仓"
    with io.open(os.path.join(R549, "taskset-r549.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(ts, ensure_ascii=False, indent=1))

    with io.open(os.path.join(R549, "snapshot-manifest.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(man, ensure_ascii=False, indent=1))
    print(json.dumps({k: man[k] for k in ("prompt_sha256", "prompt_vs_r548_run_tree", "fixture")},
                     ensure_ascii=False, indent=1))
    print("files_in_manifest:", len(man["files"]))
    # 自校验: 复算 sha 一致
    bad = []
    for e in man["files"]:
        p = os.path.join(R549, e["rel"])
        if not os.path.isfile(p) or os.path.getsize(p) != e["bytes"] or sha(p) != e["sha256"]:
            bad.append(e["rel"])
    print("MANIFEST_SELFCHECK:", "OK" if not bad else "MISMATCH %s" % bad)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
