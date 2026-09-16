#!/usr/bin/env python3
"""EXP1-Q26 / R473: 登记表证据绑定字段 evidence_generated_with 的填充与机检.

字段语义 (与 src/agent.tests/VerificationFormTests.cs 的 R2e/R2f 同口径, 两侧必须一致):
  evidence_kind     artifact | directory | self-derived   —— 证据本体形态
  pin_status        frozen | live                           —— 是否对"证据字节"上闸
  pin_reason        frozen 固定 archived-per-round; live 记原因 (词表见下)
  artifact_sha12    frozen 时 = 证据字节 sha256[:12] (闸); live 时为 null
                     · artifact  : 该文件字节 sha256[:12]
                     · directory : **目录清单摘要** (EXP1-Q27) = sha256[:12] over 按 relpath 排序的
                                   "<relpath>:<size>:<sha12>\\n"; 文件集取自 `git ls-files` (索引, 忽略件/未跟踪不入闸);
                                   目录内已跟踪文件被改写/增删 ⇒ 摘要变化 ⇒ 判红 (证据易主可见)
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

写盘纪律 (承 R409/R473, EXP1-Q29): 写前断言序列化器逐字节复现原文件; 尾形态二态容忍而回写规范化到 LF
(缺 LF 时补 1 B 并显式报告 —— 不再让尾字节风格差异静默禁用整条通路); 幂等; 写后读回复核; 打印 git numstat.
"""
import argparse, hashlib, json, os, re, subprocess, sys

REG = "docs/verification-registry.json"
AUDITED_BY_ROUND = "R473"
PRODUCT_PREFIXES = ("eval/", "docs/reports/")
COVER_LEVELS = ("L1", "L2", "L3", "L4")
KINDS = ("artifact", "directory", "self-derived")
PIN_STATUSES = ("frozen", "live")
PIN_REASONS = ("archived-per-round", "append-only-ledger", "worktree-only", "directory-aggregate",
               "self-derived", "evidence-overtaken")
BINDINGS = ("self-attested", "audit-pin")
FIELD_KEYS = ("evidence_kind", "pin_status", "pin_reason", "artifact_sha12", "instrument",
              "instrument_sha12", "binding", "audited_by_round")
# 追加式台账: 每轮都会追加行, 字节可变 -> 不上闸 (原因词表里显式登记)
LIVE_LEDGERS = {"eval/capability/kpi.jsonl": "append-only-ledger"}
SELF_DERIVED = {"docs/reports/status.json": "self-derived"}
SRC_EXT = (".py", ".sh", ".cs", ".ps1", ".js", ".ts")
CMD_PATH = re.compile(r"(?<![\w/.-])((?:src|scripts|eval|docs|tests|website|tools)/[A-Za-z0-9_./-]+)")
HEX12 = re.compile(r"^[0-9a-f]{12}$")
# EXP1-Q27: 轮号命名段 —— 主线轮号 R<n> 与能力自检作业轮号 EXP1-Q<n> 互不占号 (承 unattended-job-reliability
#   「作业与前台循环的命名空间碰撞」铁律: 作业用**自己的命名段**, 而不是偷主线轮号)。
ROUND_RE = re.compile(r"^(?:R\d+|EXP1-Q\d+)$")


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


def dir_manifest(root, rel):
    """EXP1-Q27: 目录清单摘要 — 目录聚合证据的字节闸 (可算则返回 (sha12, n_files), 否则 None)。

    语义 (与 C# VerificationFormTests.DirManifestSha12 逐位同口径):
      文件集 = `git ls-files -- <rel>` (索引来源) ∩ 现盘存在  —— 索引来源是关键:
        .gitignore 的产物 (__pycache__/日志/临时配置) 与未跟踪 scratch 天然不入闸, 不会被当成"未入库证据";
        (首版按现盘 walk - ls-files 判"未跟踪" ⇒ 把 119 个忽略件误报成缺证据, 见 Q27 仪器缺陷记录)
      digest = sha256[:12] of concat("<relpath>:<size>:<sha12>\n") 按 relpath 排序 —— 字节取自工作区。
      n_files == 0 ⇒ None (空清单不是闸, 判红)。
    任何改写/删除/新增已跟踪文件 ⇒ digest 变化 ⇒ 该行判红 (证据易主必须说话)。
    """
    files = subprocess.run(["git", "ls-files", "--", rel], cwd=root, capture_output=True,
                           text=True).stdout.split()
    rows, n = [], 0
    for p in sorted(set(files)):
        abs_p = os.path.join(root, p)
        if not os.path.isfile(abs_p):
            continue
        with open(abs_p, "rb") as fh:
            b = fh.read()
        rows.append("%s:%d:%s\n" % (p, len(b), sha12_bytes(b)))
        n += 1
    if n == 0:
        return None
    return sha12_bytes("".join(rows).encode()), n


def dir_rewritten(root, rel):
    """EXP1-Q27: 目录沿革里是否出现过**改写(M)/删除(D)** (只看 M/D, 首见 A=加入不算)。

    为什么这是 frozen 的前置条件: 归档目录的清单闸只在「目录不再变」时才是有意义的闸;
    按设计每轮都变的目录 (实测 eval/probe: 10 提交 / 5 处改写) 上闸 ⇒ 恒红假警,
    观测面噪声会把真信号淹掉 ⇒ 该留 live/evidence-overtaken (先量后定, 见 Q27 普查读数)。

    仪器纪律 (本轮自己踩过): 首版写 `--format=@` —— 非法格式, git 直接 fatal, stdout 为空 ⇒
    本函数对**所有**目录恒返回 False (空心闸: 闸永远开着而没人知道)。修法两条:
      ① 用合法格式 `--pretty=format:%H`; ② **检查返回码**, 非 0 = 无法证明「沿革只有追加」⇒ fail-closed 返回 True
         (证明不了就别上闸, 而不是默认放行)。
    """
    p = subprocess.run(["git", "log", "--no-renames", "--name-status", "--pretty=format:%H", "--", rel],
                       cwd=root, capture_output=True, text=True)
    if p.returncode != 0:
        return True                      # fail-closed: 派生失败 ⇒ 不许上冻结闸
    for line in p.stdout.splitlines():
        if not line.strip() or line.startswith("commit "):
            continue
        parts = line.split("\t")
        if parts and parts[0][:1] in ("M", "D"):
            return True
    return False


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
        man = dir_manifest(root, ep)
        if man is None:
            kind, status, reason, pin = "directory", "live", "directory-aggregate", None
        elif dir_rewritten(root, ep):
            kind, status, reason, pin = "directory", "live", "evidence-overtaken", None
        else:
            kind, status, reason, pin = "directory", "frozen", "archived-per-round", man[0]
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
        if not ROUND_RE.match(str(f.get("audited_by_round", ""))):
            v.append("%s: audited_by_round 非法 (R2e —— 允许主线 R<n> 或能力自检 EXP1-Q<n> 两个命名段)" % rid)
        dist[(kind, status, f.get("pin_reason"))] = dist.get((kind, status, f.get("pin_reason")), 0) + 1

        ep = row.get("evidence_path", "")
        a = f.get("artifact_sha12")
        if status == "frozen":
            if kind not in ("artifact", "directory"):
                v.append("%s: frozen 只允许 artifact/directory (实=%s) (R2e)" % (rid, kind))
            if kind == "directory":
                # EXP1-Q27: 目录聚合行的清单式闸 (文件集来自索引, 字节来自工作区)
                man = dir_manifest(root, ep)
                if man is None:
                    v.append("%s: frozen 但目录清单不可算 (无已跟踪文件或不可读) '%s' (R2e)" % (rid, ep))
                elif not isinstance(a, str) or not HEX12.match(a) or a != man[0]:
                    v.append("%s: 目录清单 pin 与现盘不符 (声明 %s / 实际 %s) (R2e —— 目录内已跟踪文件被改写/增删, 证据已易主或未重审)"
                             % (rid, a, man[0]))
            else:
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
    global AUDITED_BY_ROUND
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--round", default=AUDITED_BY_ROUND,
                    help="写入/复核 audited_by_round 的轮号 (默认 %s ⇒ 历史行为逐字不变)" % AUDITED_BY_ROUND)
    a = ap.parse_args()
    AUDITED_BY_ROUND = a.round   # 默认 = 历史常量 ⇒ 无参调用行为逐字不变
    print("AUDITED_BY_ROUND=%s" % AUDITED_BY_ROUND)
    root = repo_root()
    reg_abs = os.path.join(root, REG)
    with open(reg_abs, encoding="utf-8", newline="") as fh:
        raw = fh.read()
    doc = json.loads(raw)
    rows = doc["rows"]

    if a.apply:
        # EXP1-Q29: 尾换行约定 = **有(LF)** —— 已由主线在 R481 按器具自身契约修复并登记
        #   (docs/reports/r480-recall-test-ledger.md「尾部换行 1 B 修复」: 缺 LF ⇒ 本断言 fail-closed 拒写).
        #   但断言**不得因形态差异静默禁用整条通路** (EXP1-Q28 实证: 缺 LF ⇒ rc=3 ⇒ 所有程序化改写退化为
        #   文本插入, 而通路失效本身无人看见). 故判据 = 规范串 + 尾形态二态容忍, 回写规范化到 LF 并把
        #   「补 1 B」显式打进 stdout; 缩进漂移/键序重排照旧 rc=3 (非空心).
        ser = json.dumps(doc, indent=1, ensure_ascii=False)
        tail = "\n" if raw.endswith("\n") else ""
        if ser + tail != raw:
            print("SER_ASSERT=FAIL 序列化器未能逐字节复现原文件 (禁改写)")
            print("  TAIL=%s RAWLEN=%d SERLEN=%d (差异不止尾换行 ⇒ 格式漂移)"
                  % ("LF" if tail else "NONE", len(raw), len(ser)))
            return 3
        print("SER_ASSERT=OK (indent=1, ensure_ascii=False, tail=%s)"
              % ("LF" if tail else "NONE->LF 补 1 B 承 R481 契约 语义零变化"))
        tracked, dirty = git_state(root)
        n_before = sum(1 for r in rows if "evidence_generated_with" in r)
        unchanged = 0
        for row in rows:
            if needs_field(row):
                f = derive(root, row, tracked, dirty)
                if row.get("evidence_generated_with") == f:
                    # EXP1-Q27 最小 diff 纪律: 派生内容逐字段相同 ⇒ 一个字节都不动。
                    #   (此前每次 --apply 会重刷全部行的 audited_by_round ⇒ 92 行 churn 淹没真实改动;
                    #    且会把并发写者上一轮的审计戳改成自己的轮号 = 归属篡改。)
                    unchanged += 1
                    continue
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
        print("UNCHANGED=%d / TOUCHED=%d" % (unchanged, n_after - unchanged))
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
