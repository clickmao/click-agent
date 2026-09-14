#!/usr/bin/env python3
"""R371 D2 真机验收判据（预注册）—— 从 `run_d2_acceptance.sh` 的外部真值出裁决。

外部真值来源（不是自证）：① 磁盘上发布产物的 config/ 内容；② 各臂进程的 stdout 与其退出码。
判据形态 = 合取（治疗臂否 ∧ 两个负控臂是），三态判决：PASS / BREACH / ABSTAIN（缺失或超范围）。
越线报文点名未达标项。缺字段记 n/a（不记 0）。
"""
import json, os, re, sys, pathlib

DIR = pathlib.Path(__file__).resolve().parent
LOG = DIR / "acceptance.log"
PUB = pathlib.Path("/tmp/pub_d2")
MARK = "模型目录为空"

info = {}
cases = {}
sha = {}

text = LOG.read_text(encoding="utf-8", errors="replace") if LOG.exists() else ""
for line in text.splitlines():
    m = re.match(r"CASE=(\S+) RC=(\d+) SIZE=(\d+) EMPTY_CATALOG_HIT=(\d+)", line.strip())
    if m:
        cases[m.group(1)] = {"rc": int(m.group(2)), "size": int(m.group(3)), "empty_catalog_hit": int(m.group(4))}
    m = re.match(r"CFG_SHA (\S+) pub=(\S+) repo=(\S+) identical=(\d)", line.strip())
    if m:
        sha[m.group(1)] = {"pub": m.group(2), "repo": m.group(3), "identical": int(m.group(4)) == 1}

info["cases"] = cases
info["ancestor_config_hit"] = "ANCESTOR_CONFIG_HIT" in text
info["cfg_sha"] = sha

# ── 判据 ──
proc = []


def add(aid, desc, ok, detail=""):
    proc.append({"id": aid, "desc": desc, "ok": bool(ok), "detail": detail})


models_yaml = PUB / "config" / "base" / "models.yaml"
add("A1", "发布产物自带 config/base/models.yaml（静态）", models_yaml.is_file(),
    f"path={models_yaml} exists={models_yaml.is_file()}")
add("A2", "自带 config 与仓库 config/base 逐字节相同（非陈旧副本）",
    sha.get("models.yaml", {}).get("identical", False),
    json.dumps(sha.get("models.yaml", {}), ensure_ascii=False))
add("A3", "探针环境洁净：仓库外 cwd 的祖先链中无 config 可被上溯命中（排除行为被 cwd 解释）",
    not info["ancestor_config_hit"], f"ancestor_hit={info['ancestor_config_hit']}")

t = cases.get("treatment")
n1 = cases.get("neg_remove")
n2 = cases.get("neg_prefix")
add("A4", "治疗臂（自包含产物，仓库外 cwd）输出不含『模型目录为空』",
    t is not None and t["empty_catalog_hit"] == 0,
    f"treatment={t}")
add("A5", "负控 N1（仅移走产物自带 config，其余不变）必须复现『模型目录为空』",
    n1 is not None and n1["empty_catalog_hit"] == 1, f"neg_remove={n1}")
add("A6", "负控 N2（D2 修复前的发布产物）必须复现『模型目录为空』",
    n2 is not None and n2["empty_catalog_hit"] == 1, f"neg_prefix={n2}")

# 三态：任一臂缺失 ⇒ ABSTAIN（不判红也不判绿）
missing = [k for k in ("treatment", "neg_remove", "neg_prefix") if k not in cases]
if missing:
    verdict = "abstain"
elif all(p["ok"] for p in proc):
    verdict = "pass"
else:
    verdict = "breach"

failed = [p["id"] for p in proc if not p["ok"]]
out = {"plan_item": "R371-D2 发布产物自包含 config（仓库外 cwd 真机验收）",
       "verdict": verdict, "abstain_reason": ("臂缺失: " + ",".join(missing)) if missing else None,
       "assertions": proc, "assertions_pass": sum(1 for p in proc if p["ok"]), "assertions_total": len(proc),
       "failed": failed, "readings": info}
path = DIR / "verdict-r371d2.json"
path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"verdict": verdict, "pass": out["assertions_pass"], "total": out["assertions_total"],
                  "failed": failed, "cases": cases, "verdict_path": str(path)}, ensure_ascii=False))
sys.exit(0 if verdict == "pass" else 1)
