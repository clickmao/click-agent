#!/usr/bin/env python3
"""EXP1-Q26 / R473: 登记表证据绑定字段 evidence_generated_with 的填充与机检.

字段语义 (与 src/agent.tests/VerificationFormTests.cs 的 R2e/R2f 同口径, 两侧必须一致):
  evidence_kind     artifact | directory | self-derived   —— 证据本体形态
  pin_status        frozen | live                           —— 是否对"证据字节"上闸
  pin_reason        frozen 固定 archived-per-round; live 记原因 (词表见下)
  artifact_sha12    frozen 时 = 证据文件字节 sha256[:12] (闸); live 时为 null
  instrument        生成该证据的器具 (仓库相对路径) 或 null (缺口单列, 不猜)
  instrument_sha12  器具字节 sha256[:12] (闸) 或 null
  binding           self-attested (产物自己声明了来源, 我方逐字段核对) | audit-pin (审计时绑定)
  audited_by_round  本字段被写入/复核的轮号

为什么这样切 (数据先行):
  - 74/77 artifact 是已入库且工作区未改的归档产物 -> 冻结可 pin (本字段真正的闸);
  - 追加式台账 (kpi.jsonl) / 未入库产物 / 目录聚合 -> 字节每次运行都会变, 强 pin 只会产出恒红假警,
    故记 live + 原因 (不冒充冻结, 缺口作读数单列);
  - 器具 sha 是闸: 器具一改, 引用它的证据就必须重审 (Q24 缺陷族 = 证据静默易主);
  - 源码/测试文件作为证据的行不纳入 (pin 源码 sha 会让每次代码改动判红) —— 覆盖面按产品面切.

写盘纪律 (承 R409/R473): 写前断言序列化器逐字节复现原文件; 幂等; 写后读回复核; 打印 git numstat.
"""
import argparse, hashlib, json, os, re, subprocess, sys

REG = "docs/verification-registry.json"
AUDITED_BY_ROUND = "R473"
PRODUCT_PREFIXES = ("eval/", "docs/reports/")
COVER_LEVELS = ("L1", "L2", "L3", "L4")
KINDS = ("artifact", "directory", "self-derived")
PIN_STATUSES = ("frozen", "live")
PIN_REASONS = ("archived-per-round", "append-only-ledger", "worktree-only", "directory-aggregate", "self-derived")
BINDINGS = ("self-attested", "audit-pin")
FIELD_KEYS = ("evidence_kind", "pin_status", "pin_reason", "artifact_sha12", "instrument",
              "instrument_sha12", "binding", "audited_by_round")
# 追加式台账: 每轮都会追加行, 字节可变 -> 不上闸 (原因词表里显式登记)
LIVE_LEDGERS = {"eval/capability/kpi.jsonl": "append-only-ledger"}
SELF_DERIVED = {"docs/reports/status.json": "self-derived"}
SRC_EXT = (".py", ".sh", ".cs", ".ps1", ".js", ".ts")
CMD_PATH = re.compile(r"(?<![\w/.-])((?:src|scripts|eval|docs|tests|website|tools)/[A-Za-z0-9_./-]+)")
HEX12 = re.compile(r"^[0-9a-f]{12}$")


def repo_root():
    return subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()


def sha12_bytes(b):
    return hashlib.sha256(b).hexdigest()[:12]


def sha12_file(root, rel):
    p = os.path.join(root, rel)
    if not os.path.isfile(p):
        return None
    with open(p, "rb") as f:
        return sha12_bytes(f.read())


def isdir(root, rel):
    return os.path.isdir(os.path.join(root, rel))


def git_state(root):
    tracked = set(subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True).stdout.split())
    dirty = set()
    for line in subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True).stdout.splitlines():
        p = line[3:].strip().strip('"')
        dirty.add(p)
        dirty.add(p.split(" -> ")[-1])
    return tracked, dirty


def instrument_from_cmd(root, cmd):
    """从 evidence_cmd 派生器具: 首个"存在且带源码扩展名"的仓库相对路径。不猜: 无则 None。"""
    for m in CMD_PATH.finditer(cmd or ""):
        tok = m.group(1)
        if tok.endswith(SRC_EXT) and os.path.isfile(os.path.join(root, tok)):
            return tok
    return None


def provenance_of(root, rel):
    """产物自证检索: 仅 JSON 且顶层含 provenance 对象时返回它 (否则 None)。"""
    p = os.path.join(root, rel)
    if not rel.endswith(".json") or not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8-sig") as f:
            j = json.load(f)
    except Exception:
        return None
    if isinstance(j, dict) and isinstance(j.get("provenance"), dict):
        return j["provenance"]
    return None


def derive(root, row, tracked, dirty):
    ep = row.get("evidence_path", "")
    if isdir(root, ep):
        kind, status, reason, pin = "directory", "live", "directory-aggregate", None
    elif ep in SELF_DERIVED:
        kind, status, reason, pin = "self-derived", "live", "self-derived", None
    elif ep in LIVE_LEDGERS:
        kind, status, reason, pin = "artifact", "live", LIVE_LEDGERS[ep], None
    elif ep in tracked and ep not in dirty:
        kind, status, reason, pin = "artifact", "frozen", "archived-per-round", sha12_file(root, ep)
    else:
        kind, status, reason, pin = "artifact", "live", "worktree-only", None

    prov = provenance_of(root, ep)
    if prov is not None and prov.get("instrument"):
        inst, isha, binding = prov.get("instrument"), prov.get("instrument_sha12"), "self-attested"
    else:
        inst = instrument_from_cmd(root, row.get("evidence_cmd", ""))
        isha = sha12_file(root, inst) if inst else None
        binding = "audit-pin"
    return {"evidence_kind": kind, "pin_status": status, "pin_reason": reason,
            "artifact_sha12": pin, "instrument": inst, "instrument_sha12": isha,
            "binding": binding, "audited_by_round": AUDITED_BY_ROUND}


def needs_field(row):
    ep = row.get("evidence_path", "")
    return row.get("level") in COVER_LEVELS and ep.startswith(PRODUCT_PREFIXES)


def check(root, rows):
    """与 C# R2e/R2f 同口径的机检: 返回违规列表。"""
    v, dist = [], {}
    cert = 0
    for row in rows:
        rid = row.get("id", "?")
        f = row.get("evidence_generated_with")
        if f is None:
            if needs_field(row):
                v.append("%s: 产品面证据行缺 evidence_generated_with (R2f)" % rid)
            continue
        cert += 1
        if not isinstance(f, dict):
            v.append("%s: evidence_generated_with 非对象 (R2e)" % rid); continue
        for k in FIELD_KEYS:
            if k not in f:
                v.append("%s: evidence_generated_with 缺键 %s (R2e)" % (rid, k))
        kind, status = f.get("evidence_kind"), f.get("pin_status")
        if kind not in KINDS:
            v.append("%s: evidence_kind 非法 '%s' (R2e)" % (rid, kind))
        if status not in PIN_STATUSES:
            v.append("%s: pin_status 非法 '%s' (R2e)" % (rid, status))
        if f.get("pin_reason") not in PIN_REASONS:
            v.append("%s: pin_reason 非法 '%s' (R2e)" % (rid, f.get("pin_reason")))
        if f.get("binding") not in BINDINGS:
            v.append("%s: binding 非法 '%s' (R2e)" % (rid, f.get("binding")))
        if not re.match(r"^R\d+$", str(f.get("audited_by_round", ""))):
            v.append("%s: audited_by_round 非法 (R2e)" % rid)
        dist[(kind, status, f.get("pin_reason"))] = dist.get((kind, status, f.get("pin_reason")), 0) + 1

        ep = row.get("evidence_path", "")
        a = f.get("artifact_sha12")
        if status == "frozen":
            if kind != "artifact":
                v.append("%s: frozen 只允许 artifact (实=%s) (R2e)" % (rid, kind))
            cur = sha12_file(root, ep)
            if cur is None:
                v.append("%s: frozen 但证据文件不可读 '%s' (R2e)" % (rid, ep))
            elif not isinstance(a, str) or not HEX12.match(a) or a != cur:
                v.append("%s: 冻结 pin 与现盘字节不符 (声明 %s / 实际 %s) (R2e —— 证据已被改写或未重审)" % (rid, a, cur))
        else:
            if a is not None:
                v.append("%s: live 行不得带 artifact_sha12 (R2e)" % rid)

        inst, isha = f.get("instrument"), f.get("instrument_sha12")
        if (inst is None) != (isha is None):
            v.append("%s: instrument 与 instrument_sha12 必须同存同缺 (R2e)" % rid)
        if inst is not None:
            cur = sha12_file(root, inst)
            if cur is None:
                v.append("%s: instrument 路径不存在 '%s' (R2e)" % (rid, inst))
            elif not isinstance(isha, str) or not HEX12.match(isha) or isha != cur:
                v.append("%s: 器具绑定与现盘不符 (声明 %s / 实际 %s) (R2e —— 器具已改, 引用它的证据须重审)" % (rid, isha, cur))

        prov = provenance_of(root, ep)
        if f.get("binding") == "self-attested":
            if prov is None:
                v.append("%s: binding=self-attested 但产物无 provenance 自证 (R2e)" % rid)
            else:
                if prov.get("instrument_sha12") != isha:
                    v.append("%s: 自证器具 sha 与声明不符 (产物 %s / 声明 %s) (R2e)" % (rid, prov.get("instrument_sha12"), isha))
                if prov.get("instrument") and inst and prov.get("instrument") != inst:
                    v.append("%s: 自证器具路径与声明不符 (R2e)" % rid)
                if not prov.get("arm"):
                    v.append("%s: 产物 provenance 缺 arm, 不足以为自证 (R2e)" % rid)
        else:
            if prov is not None:
                v.append("%s: 产物已自证来源, 登记行不得降级为 audit-pin (R2f)" % rid)
    return v, dist, cert


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    root = repo_root()
    reg_abs = os.path.join(root, REG)
    with open(reg_abs, encoding="utf-8", newline="") as fh:
        raw = fh.read()
    doc = json.loads(raw)
    rows = doc["rows"]

    if a.apply:
        ser = json.dumps(doc, indent=1, ensure_ascii=False)
        if ser + "\n" != raw:
            print("SER_ASSERT=FAIL 序列化器未能逐字节复现原文件 (禁改写)"); return 3
        print("SER_ASSERT=OK (indent=1, ensure_ascii=False, 尾换行)")
        tracked, dirty = git_state(root)
        n_before = sum(1 for r in rows if "evidence_generated_with" in r)
        for row in rows:
            if needs_field(row):
                f = derive(root, row, tracked, dirty)
                if "evidence_generated_with" in row:
                    row["evidence_generated_with"] = f
                else:
                    # 保序插入: 置于 evidence_path 之后 (与它绑定的字段相邻)
                    keys = list(row.keys())
                    pos = keys.index("evidence_path") + 1 if "evidence_path" in keys else len(keys)
                    items = list(row.items())
                    row.clear()
                    for i, (k, v) in enumerate(items):
                        if i == pos:
                            row["evidence_generated_with"] = f
                        row[k] = v
                    if "evidence_generated_with" not in row:
                        row["evidence_generated_with"] = f
        out = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
        if out == raw:
            print("IDEMPOTENT=OK (字节不变, 无需写盘)")
        else:
            with open(reg_abs, "w", encoding="utf-8", newline="") as fh:
                fh.write(out)
            with open(reg_abs, encoding="utf-8", newline="") as fh:
                back = fh.read()
            print("WRITE_READBACK=%s" % ("OK" if back == out else "MISMATCH"))
        n_after = sum(1 for r in rows if "evidence_generated_with" in r)
        print("COVERED %d -> %d" % (n_before, n_after))
        print(subprocess.run(["git", "diff", "--numstat", REG], cwd=root, capture_output=True, text=True).stdout.strip())

    v, dist, cert = check(root, json.loads(open(reg_abs, encoding="utf-8").read())["rows"])
    print("CHECKED_WITH_FIELD=%d" % cert)
    for k in sorted(dist, key=lambda t: (str(t[0]), str(t[1]), str(t[2]))):
        print("  dist %-12s %-6s %-22s x%d" % (k[0], k[1], k[2], dist[k]))
    for s in v[:20]:
        print("VIOLATION", s)
    print("R2E_R2F_EXIT=%d" % (0 if not v else 2))
    return 0 if not v else 2


if __name__ == "__main__":
    sys.exit(main())
