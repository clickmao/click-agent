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
  pin_kind          **可选** —— 缺省 (None) = pin 绑**文件字节** (历史行为);
                    'semantic-projection' = pin 绑**语义投影摘要** (EXP1-Q34): 面记录里由设计决定的
                    非语义字段族 (墙钟/随机目录/邻居面/采样) 先按 `eval/capability/projection_rules.json`
                    剔除, 再对剩余叶流取 sha256[:12] ⇒ 面**重跑不再打红冻结 pin**。
                    该值必须由与本仓测试侧**同一规则文件**的独立实现复算得到 (跨语言同口径);
                    锚规则 (运行期窗口族) 缺席 ⇒ 弃权 (非本类面记录不得判绿); 值形态未定义 (浮点) ⇒ 弃权。

为什么这样切 (数据先行):
  - 74/77 artifact 是已入库且工作区未改的归档产物 -> 冻结可 pin (本字段真正的闸);
  - 追加式台账 (kpi.jsonl) / 未入库产物 / 目录聚合 -> 字节每次运行都会变, 强 pin 只会产出恒红假警,
    故记 live + 原因 (不冒充冻结, 缺口作读数单列);
  - 器具 sha 是闸: 器具一改, 引用它的证据就必须重审 (Q24 缺陷族 = 证据静默易主);
  - 源码/测试文件作为证据的行不纳入 (pin 源码 sha 会让每次代码改动判红) —— 覆盖面按产品面切.
    EXP1-Q39 细化: 「源码证据 ∧ 该文件就是本行器具」⇒ **显式**归 self-derived/live (与工作区脏净无关);
    该文件字节仍由 instrument_sha12 钉 (闸等价, 见 source_self_gated); 声明了另一个器具的行不改判。

写盘纪律 (承 R409/R473, EXP1-Q29): 写前断言序列化器逐字节复现原文件; 尾形态二态容忍而回写规范化到 LF
(缺 LF 时补 1 B 并显式报告 —— 不再让尾字节风格差异静默禁用整条通路); 幂等; 写后读回复核; 打印 git numstat.
"""
import argparse, hashlib, json, os, re, subprocess, sys
from datetime import datetime, timezone

REG = "docs/verification-registry.json"
AUDITED_BY_ROUND = "R473"
PRODUCT_PREFIXES = ("eval/", "docs/reports/")
COVER_LEVELS = ("L1", "L2", "L3", "L4")
KINDS = ("artifact", "directory", "self-derived")
PIN_STATUSES = ("frozen", "live")
PIN_REASONS = ("archived-per-round", "append-only-ledger", "worktree-only", "directory-aggregate",
               "self-derived", "evidence-overtaken")
BINDINGS = ("self-attested", "audit-pin")
# EXP1-Q34: pin_kind 可选值 —— 缺省 (键缺席) = 文件字节; 'semantic-projection' = 语义投影摘要。
PIN_KINDS = ("semantic-projection",)
FIELD_KEYS = ("evidence_kind", "pin_status", "pin_reason", "artifact_sha12", "instrument",
              "instrument_sha12", "binding", "audited_by_round")
# EXP1-Q38 候选③: 尾换行契约 (R481) 违反的**可见化**。契约违反此前只打一行 stdout ——
#   机器读不到, 该轮产物因此无法按「输入规范形 / 非规范形」归属。现落**一等字段**:
#   stdout 恒打 `NONCANONICAL_INPUT=<0|1> reason=<...>` (字段不因模式而消失), 并可由
#   `--run-record <path>` 落一份机器可读运行记录 (供该轮产物归属 + 后续追溯)。
TAIL_CONTRACT = "R481-tail-lf"
RUN_RECORD_SCHEMA = "evidence-binding-run/v1"
NONCANON_REASON = "tail_lf_missing"


class ProjectionPinUnavailable(RuntimeError):
    """申明 pin_kind=semantic-projection 的行在当前盘面**无法复算投影摘要** ——
    apply 时跳过该行 (fail-visible), 绝不写入 artifact_sha12=null 的假冻结行。"""


class FrozenEvidenceDirty(RuntimeError):
    """EXP1-Q40 ③: 行上已声明 frozen 但证据文件在工作区**脏** —— **非定向** apply 路径上
    拒绝把它静默降级为 live/worktree-only (闸的丢失必须是一次显式决策)。

    为什么不是「保持 frozen + 按现盘字节重钉」: 那等于把**未经重审的新字节**悄悄记为已审
    (洗白)。为什么不判红就了事: 提交闸默认开 ⇒ 判红无人可提交 ⇒ 该证据永远无法入库
    (死锁)。⇒ 正解 = 跳过并**出声** (打印现盘/归档两侧读数 + 处置命令), 由操作者显式
    跑定向重审 (`--only <id> --round <轮> --apply`) 完成「记录 → 重审」工序。
    """


def emit_run_record(rec, path):
    """EXP1-Q38 候选③: 落一份**机器可读**运行记录 (供该轮产物归属)。

    写盘纪律同登记表: 写后读回比对; 不一致 ⇒ 出声并把 rc 置 3 (fail-visible, 不静默)。
    返回落盘路径 (未给 path ⇒ None)。
    """
    if not path:
        return None
    p = path if os.path.isabs(path) else os.path.join(repo_root(), path)
    out = json.dumps(rec, ensure_ascii=False, indent=1) + "\n"
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    with open(p, encoding="utf-8", newline="") as fh:
        back = fh.read()
    ok = (back == out)
    print("RUN_RECORD=%s (%s)" % (p, "OK" if ok else "MISMATCH"))
    if not ok:
        rec["rc"] = 3
    return p


def projection_digest(root, rel):
    """pin_kind=semantic-projection 的 pin 值 = 语义投影摘要 (与本仓测试侧同一规则文件同口径)。

    返回 (digest|None, reason)。**所有** None 都由 check 判红 (fail-closed): 冻结 pin 不可复算 =
    没有任何一侧能验证该声明, 与「证据不可读」同族 (弃权只留给环境不可判类, 这里不是)。
    """
    if not rel or not os.path.isfile(os.path.join(root, rel)):
        return None, "record_missing"
    try:
        import face_record_canon as frc
    except ImportError as exc:                      # 规则层不可用 = 判据不可用 ⇒ 判红, 不静默降绿
        return None, "rules_module_unavailable:%s" % exc
    try:
        d, _meta = frc.proj_digest_file(os.path.join(root, rel), strict=False)
        return d, None
    except frc.ProjectionRulesError as exc:
        return None, "rules_unavailable:%s" % exc
    except KeyError as exc:
        return None, "projection_abstain:%s" % exc
    except ValueError as exc:
        return None, "record_unreadable:%s" % exc
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


def dir_manifest_head(root, rel):
    """EXP1-Q40 ③ 附属: 目录聚合行的**归档(HEAD)清单摘要** —— 同 dir_manifest 的格式与单位,
    文件集取 `git ls-tree -r HEAD -- <rel>` (归档树), 字节取 `git show HEAD:<p>`。
    仅在「现盘清单 ≠ 声明 pin」时调用一次 (解释该不符是**工作区漂移**还是**真失效**)。
    不可算 (git 失败) ⇒ None (调用方照旧判红: 证明不了不是漂移)。
    """
    p = subprocess.run(["git", "ls-tree", "-r", "--name-only", "HEAD", "--", rel], cwd=root,
                       capture_output=True, text=True)
    if p.returncode != 0:
        return None
    rows, n = [], 0
    for rel_p in sorted(set(x for x in p.stdout.split("\n") if x.strip())):
        b = blob_bytes(root, rel_p)
        if b is None:
            continue
        rows.append("%s:%d:%s\n" % (rel_p, len(b), sha12_bytes(b)))
        n += 1
    if n == 0:
        return None
    return sha12_bytes("".join(rows).encode()), n


def blob_bytes(root, rel, rev="HEAD"):
    """归档(HEAD)里该路径的原始字节; 不在归档树 ⇒ None。"""
    p = subprocess.run(["git", "show", "%s:%s" % (rev, rel)], cwd=root, capture_output=True)
    if p.returncode != 0:
        return None
    return p.stdout


def sha12_blob(root, rel, rev="HEAD"):
    """归档(HEAD)字节的 sha256[:12]; 不可得 ⇒ None。"""
    b = blob_bytes(root, rel, rev)
    return None if b is None else sha12_bytes(b)


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


def source_self_gated(root, row, ep, inst):
    """EXP1-Q39: 证据本体是**源码文件**且**它自己就是本行的器具** ⇒ 归 self-derived/live。

    缺陷动机 (Q38 AM.5.5 实测侧效): 原判据只看「已入库 ∧ 工作区干净」⇒ 同一条行在脏/净两态下
    分类**不同** (live/worktree-only ⇄ frozen/archived-per-round), 一次 `--apply` 的侧效即可翻转其语义。
    本规则把它改成**由行自身结构决定**、与工作区状态无关的类。

    闸不丢 (机检, 不是口头保证): 该文件字节由 `instrument_sha12` 继续钉 —— 与 frozen 档下
    `artifact_sha12` **同源同值** (同一个文件), 变异字节 ⇒ 两侧都判红 (Q39 census 夹具 c6/c8)。

    例外 (P4): 行上**声明**了另一个器具 (或从 evidence_cmd 现算出另一个器具) 时**不改判** ——
    那种情形下源码 pin 是唯一闸, 改类会静默丢闸 (实测 `r492.arm-runner-derive-aux-carry`:
    声明器具 = `eval/rover/r491/run_arm_real_r491.sh` ≠ 证据文件)。
    """
    if not ep or not inst or inst != ep:
        return False
    if not ep.endswith(SRC_EXT) or not os.path.isfile(os.path.join(root, ep)):
        return False
    f = row.get("evidence_generated_with")
    declared = f.get("instrument") if isinstance(f, dict) else None
    return declared in (None, ep)


def derive(root, row, tracked, dirty, targeted=False):
    """派生一行的 evidence_generated_with。

    targeted=True (EXP1-Q40 ②/③): 该行在本轮被 `--only` **显式点名** ⇒ 允许对现盘字节重钉
    (这是登记表契约里写明的「记录 → 重审」工序)。缺省 False 与历史行为一致 (供 Q27 普查器等调用方)。
    """
    ep = row.get("evidence_path", "")
    # EXP1-Q39: 器具/绑定**先算** —— 新规则 (源码自拄) 需要知道器具是谁才判类。
    prov = provenance_of(root, ep)
    if prov is not None and prov.get("instrument"):
        inst, isha, binding = prov.get("instrument"), prov.get("instrument_sha12"), "self-attested"
    else:
        inst = instrument_from_cmd(root, row.get("evidence_cmd", ""))
        isha = sha12_file(root, inst) if inst else None
        binding = "audit-pin"
    proj_declared = existing_pin_kind(row) == "semantic-projection"
    frozen_declared = existing_pin_status(row) == "frozen"
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
    elif source_self_gated(root, row, ep, inst):
        kind, status, reason, pin = "self-derived", "live", "self-derived", None
    elif ep in tracked and (ep not in dirty or proj_declared or targeted):
        # EXP1-Q40 ②: 声明 pin_kind=semantic-projection 的行按**声明语义**判类 —— 证据已入库即
        #   frozen/artifact, 与工作区脏净无关 (pin 值随后由投影摘要覆盖; 投影口径本身已遮蔽
        #   运行期读数)。修前: 记录脏 ⇒ 落到末尾 else 支 ⇒ 该行抛 ProjectionPinUnavailable
        #   被跳过 ⇒ 「记录 → 重审」出现次序依赖 (Q39 附录 AN.4.3 实测)。
        # EXP1-Q40 ③-t: **定向**路径 (--only 点名) = 显式重审决策 ⇒ 按现盘字节重钉 (契约里的
        #   处置命令), 与修前干净态语义一致。
        kind, status, reason, pin = "artifact", "frozen", "archived-per-round", sha12_file(root, ep)
    elif frozen_declared:
        # EXP1-Q40 ③: 已声明 frozen 的行在**非定向**路径上证据脏 ⇒ 不得静默降级为
        #   live/worktree-only (一次 `--apply` 的侧效就把闸丢掉, 且 live 行无 pin 可判 ⇒ 无声)。
        #   出声跳过, 保留行上原声明 (pin 不动), 由操作者显式定向重审。
        raise FrozenEvidenceDirty(
            "%s: 证据在工作区脏 (现盘 %s / 归档 %s) ⇒ 保持 frozen 原声明不变; 处置: "
            "--only %s --round <轮号> --apply (记录 → 重审)"
            % (row.get("id"), sha12_file(root, ep) or "缺失", sha12_blob(root, ep) or "不在归档树",
               row.get("id")))
    else:
        kind, status, reason, pin = "artifact", "live", "worktree-only", None

    out = {"evidence_kind": kind, "pin_status": status, "pin_reason": reason}
    # EXP1-Q34: pin_kind 是**行上已声明**的语义属性, derive 只尊重不发明 ——
    #   声明了语义投影且该行确实是 frozen/artifact ⇒ pin 值改为投影摘要 (跨语言同口径);
    #   复算不可得 ⇒ 抛 ProjectionPinUnavailable (调用方跳过该行, fail-visible, 不写 null 假冻结)。
    if existing_pin_kind(row) == "semantic-projection":
        if status != "frozen" or kind != "artifact":
            raise ProjectionPinUnavailable(
                "%s: pin_kind=semantic-projection 只适用于 frozen/artifact (实=%s/%s)"
                % (row.get("id"), status, kind))
        dg, why = projection_digest(root, ep)
        if dg is None:
            raise ProjectionPinUnavailable("%s: %s" % (row.get("id"), why))
        out["pin_kind"] = "semantic-projection"
        pin = dg
    out.update({"artifact_sha12": pin, "instrument": inst, "instrument_sha12": isha,
                "binding": binding, "audited_by_round": AUDITED_BY_ROUND})
    return out


def existing_pin_kind(row):
    """行上已声明的 pin_kind (缺省 None = 文件字节)。derive 只尊重不发明。"""
    f = row.get("evidence_generated_with")
    return f.get("pin_kind") if isinstance(f, dict) else None


def existing_pin_status(row):
    """行上已声明的 pin_status (缺省 None = 未声明)。derive 只尊重不发明 (EXP1-Q40 ③)。"""
    f = row.get("evidence_generated_with")
    return f.get("pin_status") if isinstance(f, dict) else None


def needs_field(row):
    ep = row.get("evidence_path", "")
    return row.get("level") in COVER_LEVELS and ep.startswith(PRODUCT_PREFIXES)


def check(root, rows, drift=None):
    """与 C# R2e/R2f 同口径的机检: 返回 (违规列表, 分布, 带字段行数)。

    drift (EXP1-Q40 ③, 可选): 传入 list 时, 把「**归档自洽 ∧ 工作区漂移**」的冻结行记进它
    —— 该态**不判红** (committed 态自洽 ⇒ 提交闸不得被工作区半成品卡死), 但必须**可见**;
    处置 = 显式定向重审 (登记表契约里的工序)。判红只留给「连归档也不自洽」的真失效。
    """
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
        pk = f.get("pin_kind")
        if pk is not None and pk not in PIN_KINDS:
            v.append("%s: pin_kind 非法 '%s' (R2e —— 未知 pin 语义不可验证 ⇒ fail-closed)" % (rid, pk))
        if status == "frozen" and pk == "semantic-projection":
            # EXP1-Q34: pin 绑**语义投影摘要** (非文件字节) —— 面重跑不再打红。
            if kind != "artifact":
                v.append("%s: pin_kind=semantic-projection 只允许 artifact (实=%s) (R2e)" % (rid, kind))
            else:
                cur, why = projection_digest(root, ep)
                if cur is None:
                    # 值形态未定义 / 锚族缺席 / 规则层不可用 —— 一律**判红**: 冻结 pin 不可复算 =
                    # 该声明没有任何一侧能验证它 (与「证据不可读」同族)。弃权只留给「环境不可判」类,
                    # 这里不是; 且本仓测试侧 Validate 无弃权通道 ⇒ 两侧判据必须同形 (EXP1-Q34)。
                    v.append("%s: 语义投影 pin 不可复算 (%s) (R2e —— fail-closed)" % (rid, why))
                elif not isinstance(a, str) or not HEX12.match(a) or a != cur:
                    v.append("%s: 语义投影 pin 与现盘不符 (声明 %s / 实际 %s) (R2e —— 语义内容已变或未重审)"
                             % (rid, a, cur))
        elif status == "frozen":
            if kind not in ("artifact", "directory"):
                v.append("%s: frozen 只允许 artifact/directory (实=%s) (R2e)" % (rid, kind))
            if kind == "directory":
                # EXP1-Q27: 目录聚合行的清单式闸 (文件集来自索引, 字节来自工作区)
                man = dir_manifest(root, ep)
                if man is None:
                    v.append("%s: frozen 但目录清单不可算 (无已跟踪文件或不可读) '%s' (R2e)" % (rid, ep))
                elif not isinstance(a, str) or not HEX12.match(a) or a != man[0]:
                    hm = dir_manifest_head(root, ep)
                    if (isinstance(a, str) and HEX12.match(a) and hm is not None and a == hm[0]
                            and man[0] != hm[0]):
                        # EXP1-Q40 ③: 归档清单自洽 ∧ 工作区目录漂移 ⇒ 可见项 (不判红)
                        if drift is not None:
                            drift.append({"id": rid, "kind": "directory", "pin": a, "disk": man[0],
                                          "evidence_path": ep,
                                          "why": "worktree-drift (归档自洽; 处置: --only %s --round <轮> --apply)" % rid})
                    else:
                        v.append("%s: 目录清单 pin 与现盘不符 (声明 %s / 实际 %s) (R2e —— 目录内已跟踪文件被改写/增删, 证据已易主或未重审)"
                                 % (rid, a, man[0]))
            else:
                cur = sha12_file(root, ep)
                if cur is None:
                    v.append("%s: frozen 但证据文件不可读 '%s' (R2e)" % (rid, ep))
                elif not isinstance(a, str) or not HEX12.match(a) or a != cur:
                    if (isinstance(a, str) and HEX12.match(a) and cur != a
                            and a == sha12_blob(root, ep)):
                        # EXP1-Q40 ③: 归档字节自洽 ∧ 工作区漂移 ⇒ 可见项 (不判红)
                        if drift is not None:
                            drift.append({"id": rid, "kind": "artifact", "pin": a, "disk": cur,
                                          "evidence_path": ep,
                                          "why": "worktree-drift (归档自洽; 处置: --only %s --round <轮> --apply)" % rid})
                    else:
                        v.append("%s: 冻结 pin 与现盘字节不符 (声明 %s / 实际 %s) (R2e —— 证据已被改写或未重审)" % (rid, a, cur))
        else:
            if a is not None:
                v.append("%s: live 行不得带 artifact_sha12 (R2e)" % rid)
            if pk is not None:
                v.append("%s: live 行不得带 pin_kind (R2e —— 投影 pin 只对 frozen 有意义)" % rid)

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
    ap.add_argument("--round", default=None,
                    help="写入/复核 audited_by_round 的轮号 (默认 %s ⇒ 历史行为逐字不变)" % AUDITED_BY_ROUND)
    ap.add_argument("--only", default=None,
                    help="定向范围: 逗号分隔的登记行 id; 与 --apply 同用时必须同时显式给 --round, "
                         "未知 id 或缺少轮号 ⇒ rc=3 且零字节写入")
    ap.add_argument("--registry", default=REG,
                    help="登记表路径 (默认 %s; 供 scratch 副本核验 —— 真登记表不被触碰)" % REG)
    # EXP1-Q38 候选③: 机器可读运行记录 (含 noncanonical_input 一等字段)
    ap.add_argument("--run-record", default=None,
                    help="把本次运行的机器可读记录落到该路径 (仓库相对或绝对; 供该轮产物归属)")
    a = ap.parse_args()
    explicit_round = a.round is not None
    AUDITED_BY_ROUND = a.round if explicit_round else AUDITED_BY_ROUND   # 默认 = 历史常量 ⇒ 无参调用行为逐字不变
    print("AUDITED_BY_ROUND=%s" % AUDITED_BY_ROUND)
    root = repo_root()
    reg_rel = a.registry
    reg_abs = reg_rel if os.path.isabs(reg_rel) else os.path.join(root, reg_rel)
    with open(reg_abs, encoding="utf-8", newline="") as fh:
        raw = fh.read()
    doc = json.loads(raw)
    rows = doc["rows"]

    # EXP1-Q38 候选③: 尾契约违反 → 一等可见字段。两种模式都报 (字段不因模式而消失);
    #   「补 1 B」不再是 stdout 里的一句人话, 而是可被该轮产物归属消费的结构化事实。
    ser = json.dumps(doc, indent=1, ensure_ascii=False)
    tail = "\n" if raw.endswith("\n") else ""
    noncanonical = (tail == "")
    print("TAIL_CONTRACT=%s registry_tail=%s" % (TAIL_CONTRACT, "LF" if tail else "NONE"))
    print("NONCANONICAL_INPUT=%d reason=%s (input=%s; 契约=%s = 登记表 JSON 尾须为 LF; "
          "缺 LF ⇒ 本次写盘补 1 B, 语义零变化)"
          % (1 if noncanonical else 0, NONCANON_REASON if noncanonical else "none", reg_rel, TAIL_CONTRACT))
    runrec = {
        "schema": RUN_RECORD_SCHEMA, "round": AUDITED_BY_ROUND, "round_explicit": explicit_round,
        "mode": "apply" if a.apply else ("check" if a.check else "noop"),
        "registry": reg_rel, "registry_is_scratch": os.path.isabs(reg_rel),
        "ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),   # 信息项 (非语义)
        "tail_contract": TAIL_CONTRACT, "registry_tail_input": "LF" if tail else "NONE",
        "noncanonical_input": bool(noncanonical),
        "noncanonical_reason": NONCANON_REASON if noncanonical else None,
        "ser_assert": None, "scope": None, "covered_before": None, "covered_after": None,
        "covered_total": None, "unchanged": None, "touched": None, "idempotent": None,
        "write_readback": None, "proj_pin_skipped": [], "frozen_evidence_dirty_skipped": [],
        "frozen_evidence_drift": [], "numstat": None,
        "violations": [], "violations_total": None, "rc": None,
    }

    def finish(rc):
        runrec["rc"] = rc
        emit_run_record(runrec, a.run_record)
        return rc

    ids = None
    if a.only:
        ids = [s.strip() for s in a.only.split(",") if s.strip()]
    if ids is not None:
        # 定向范围的前置核验 (fail-closed): 未知 id / --apply 缺显式轮号 一律 rc=3 零写入。
        known = {r.get("id") for r in rows}
        unknown = [i for i in ids if i not in known]
        if unknown:
            print("ONLY_SCOPE=UNKNOWN_IDS %s (fail-closed, 零字节写入)" % sorted(unknown))
            return finish(3)
        if a.apply and not explicit_round:
            print("ONLY_SCOPE=REQUIRES_EXPLICIT_ROUND (定向重审缺显式 --round ⇒ rc=3, 零字节写入)")
            return finish(3)
        print("ONLY_SCOPE=n=%d %s" % (len(ids), ",".join(ids)))

    if a.apply:
        # EXP1-Q29: 尾换行约定 = **有(LF)** —— 已由主线在 R481 按器具自身契约修复并登记
        #   (docs/reports/r480-recall-test-ledger.md「尾部换行 1 B 修复」: 缺 LF ⇒ 本断言 fail-closed 拒写).
        #   但断言**不得因形态差异静默禁用整条通路** (EXP1-Q28 实证: 缺 LF ⇒ rc=3 ⇒ 所有程序化改写退化为
        #   文本插入, 而通路失效本身无人看见). 故判据 = 规范串 + 尾形态二态容忍, 回写规范化到 LF 并把
        #   「补 1 B」显式打进 stdout; 缩进漂移/键序重排照旧 rc=3 (非空心).
        ser = json.dumps(doc, indent=1, ensure_ascii=False)
        tail = "\n" if raw.endswith("\n") else ""
        if ser + tail != raw:
            runrec["ser_assert"] = "FAIL"
            print("SER_ASSERT=FAIL 序列化器未能逐字节复现原文件 (禁改写)")
            print("  TAIL=%s RAWLEN=%d SERLEN=%d (差异不止尾换行 ⇒ 格式漂移)"
                  % ("LF" if tail else "NONE", len(raw), len(ser)))
            return finish(3)
        runrec["ser_assert"] = "OK"
        print("SER_ASSERT=OK (indent=1, ensure_ascii=False, tail=%s)"
              % ("LF" if tail else "NONE->LF 补 1 B 承 R481 契约 语义零变化"))
        tracked, dirty = git_state(root)
        # EXP1-Q30: 粒度收窄 —— needs_field ∧ (无 --only ∨ id ∈ --only)。无 --only 时 scope == 全表 ⇒ 历史行为不变。
        scope_rows = [r for r in rows if needs_field(r) and (ids is None or r.get("id") in ids)]
        n_before = sum(1 for r in scope_rows if "evidence_generated_with" in r)
        unchanged = 0
        proj_skipped = []
        frozen_skipped = []
        for row in scope_rows:
            try:
                f = derive(root, row, tracked, dirty,
                           targeted=(ids is not None and row.get("id") in ids))
            except ProjectionPinUnavailable as exc:
                # 声明了投影 pin 但当前盘面复算不可得 ⇒ 跳过该行并**出声** (不写 null 假冻结行)
                proj_skipped.append(str(exc))
                continue
            except FrozenEvidenceDirty as exc:
                # EXP1-Q40 ③: 已声明 frozen 而行证据脏 ⇒ 非定向路径不出声改类, 保留原声明并**出声**。
                frozen_skipped.append(str(exc))
                continue
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
            runrec["idempotent"] = True
            runrec["write_readback"] = "NOT_WRITTEN"
        else:
            with open(reg_abs, "w", encoding="utf-8", newline="") as fh:
                fh.write(out)
            with open(reg_abs, encoding="utf-8", newline="") as fh:
                back = fh.read()
            print("WRITE_READBACK=%s" % ("OK" if back == out else "MISMATCH"))
            runrec["idempotent"] = False
            runrec["write_readback"] = "OK" if back == out else "MISMATCH"
        n_after = sum(1 for r in scope_rows if "evidence_generated_with" in r)
        n_total = sum(1 for r in rows if "evidence_generated_with" in r)
        runrec.update({"scope": "full" if ids is None else "only(n=%d)" % len(ids),
                       "covered_before": n_before, "covered_after": n_after, "covered_total": n_total,
                       "unchanged": unchanged, "touched": n_after - unchanged,
                       "proj_pin_skipped": list(proj_skipped),
                       "frozen_evidence_dirty_skipped": list(frozen_skipped)})
        print("SCOPE=%s" % ("full" if ids is None else "only(n=%d)" % len(ids)))
        print("COVERED %d -> %d (scope); 全表 COVERED=%d" % (n_before, n_after, n_total))
        print("UNCHANGED=%d / TOUCHED=%d (scope)" % (unchanged, n_after - unchanged))
        if proj_skipped:
            print("PROJ_PIN_SKIPPED=%d" % len(proj_skipped))
            for s in proj_skipped[:10]:
                print("  PROJ_PIN_SKIP %s" % s)
        if frozen_skipped:
            print("FROZEN_EVIDENCE_DIRTY_SKIP=%d (非定向路径不得静默改类; 保留原声明)" % len(frozen_skipped))
            for s in frozen_skipped[:10]:
                print("  FROZEN_DIRTY_SKIP %s" % s)
        if os.path.isabs(reg_rel):
            print("NUMSTAT=skip (scratch 副本, 非仓内路径)")
            runrec["numstat"] = "skip (scratch 副本)"
        else:
            ns = subprocess.run(["git", "diff", "--numstat", reg_rel], cwd=root,
                                capture_output=True, text=True).stdout.strip()
            print(ns)
            runrec["numstat"] = ns

    crows = json.loads(open(reg_abs, encoding="utf-8").read())["rows"]
    if ids is not None:
        crows = [r for r in crows if r.get("id") in ids]
    drift = []
    v, dist, cert = check(root, crows, drift)
    n_proj = sum(1 for r in crows if isinstance(r.get("evidence_generated_with"), dict)
                 and r["evidence_generated_with"].get("pin_kind") == "semantic-projection")
    print("PIN_KIND_SEMANTIC_PROJECTION=%d" % n_proj)
    print("CHECKED_WITH_FIELD=%d" % cert)
    if ids is not None:
        print("DIST_SCOPE=only(n=%d) —— 与全表口径分布不可比" % len(crows))
    for k in sorted(dist, key=lambda t: (str(t[0]), str(t[1]), str(t[2]))):
        print("  dist %-12s %-6s %-22s x%d" % (k[0], k[1], k[2], dist[k]))
    print("FROZEN_EVIDENCE_DRIFT=%d (归档自洽 ∧ 工作区漂移; 可见项, 不判红)" % len(drift))
    for d in drift[:10]:
        print("  FROZEN_DRIFT %s kind=%s pin=%s disk=%s" % (d["id"], d["kind"], d["pin"], d["disk"]))
    for s in v[:20]:
        print("VIOLATION", s)
    print("R2E_R2F_EXIT=%d" % (0 if not v else 2))
    runrec["violations"] = v[:20]
    runrec["violations_total"] = len(v)
    runrec["frozen_evidence_drift"] = drift
    return finish(0 if not v else 2)


if __name__ == "__main__":
    sys.exit(main())
