#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""roundcheck —— 每轮有效性校对 + 方案可行性前置闸（调试器具, 非评测夹具）。

用途（两条, 对应两类翻车）:
  A) audit     校对「这一轮到底算不算有效」: 轮号唯一 / 证据文件在位 / 冻结 pin 与现盘字节一致 /
               证据文档结构(诚实边界) / 提交面卫生(禁 git add -A 的代理判据) / 提交内无 key 面 /
               读数有档(build 0 error · 形式 14/14 · 通过率 x/y) / 暂存面卫生。
  B) preflight 起臂前判「方案跑得起来么」: 依赖的 key 面是否就位(只报 set/unset, **绝不回显值**) /
               权重在盘 / 内存·磁盘余量 / 是否已有在飞执行体(兄弟会话) / 目标轮号是否被占。

设计纪律:
  · 只读——除 --selftest 在临时目录里造样本, 从不改被审仓库。
  · 每个判据都带负控(selftest 内: 错 pin ⇒ R4 红; 提交里塞 key 面 ⇒ R7 红), 器具先自证有牙。
  · 退出码: 0 = 无 FAIL(可有 WARN); 1 = ≥1 FAIL; 2 = 用法/环境错。

    python3 tools/roundcheck/roundcheck.py audit --round R582
    python3 tools/roundcheck/roundcheck.py preflight --need-key AGENTFRAMEWORK_KEYS_DEEPSEEK
    python3 tools/roundcheck/roundcheck.py --selftest
"""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile

SKIP_DIRS = {".git", "bin", "obj", "__pycache__", "node_modules", ".hermes"}
JUNK_RE = re.compile(r"(^|/)(scratch|__pycache__)/|\.(log|tmp|bak|orig|rej)$|\.orig$")
SECRET_PATTERNS = [
    (re.compile(r"(?<![A-Za-z0-9_])sk-[A-Za-z0-9]{16,}"), "openai 形 key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "私钥块"),
    (re.compile(r"AGENTFRAMEWORK_KEYS_[A-Z0-9_]+\s*=\s*\S{8,}"), "AGENTFRAMEWORK key 面赋值"),
    (re.compile(r"(?i)(api[_-]?key|access[_-]?token|secret[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}"), "key/token 赋值"),
]
MAX_SCAN_BYTES = 2 * 1024 * 1024


def sh(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def git(repo, *args):
    rc, out, _ = sh(["git", "-C", repo] + list(args))
    return (out if rc == 0 else "")


def sha12_of_file(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def read_text(path, limit=MAX_SCAN_BYTES):
    try:
        if os.path.getsize(path) > limit:
            return None
        return io.open(path, "r", encoding="utf-8").read()
    except (OSError, UnicodeDecodeError):
        return None


def load_registry(repo):
    path = os.path.join(repo, "docs", "verification-registry.json")
    if not os.path.exists(path):
        return None
    try:
        return json.loads(io.open(path, "r", encoding="utf-8").read())
    except ValueError:
        return None


def rows_for(reg, round_id):
    if not reg:
        return []
    return [r for r in reg.get("rows", []) if str(r.get("owner_round", "")).strip() == round_id]


CONTRAST_SCOPE_KIND = "contrast_zero_product_change"


def read_audit_scope(repo, round_id):
    """读本轮**独立声明件** `eval/rover/<rid>/audit-scope-<rid>.json` 的 `audit_scope` 段（R587 新增）。

    动机（R586 登记候选 ⑥）: 存在一类**零产品源码改动**的对照轮 —— 只跑外部真值 × 产品默认档、
    不新增能力 ⇒ 依据「验证登记表**缺少负控**」的通用纪律, 它**本就不该**有 `owner_round` 登记行,
    而旧 `R1` 会把「无登记行」一律判红; `R6` 的「> 40 文件」与 `R8` 的「build 0 error / 14/14」
    在对照轮上也是结构性不可达。旧处理方式（补一行假登记行 / 放宽阈值）都是**改判据凑绿**。

    本函数的纪律 = **免检只能由预注册显式声明, 且必须可机检、fail-closed**:
      · 声明缺失 ⇒ 返回 None（**旧行为逐字节不变**）;
      · 声明非法（kind 不符 / reason 过短 / readings 缺失或为空文件 / allowed_faces 为空）⇒
        返回 {"ok": False, "why": ...} 而**不是** None —— 让调用方把它写进 R1 的明细（出声, 不静默豁免）;
      · 调用方（audit）另需核「提交面**零** `src/` 文件」, 声明了却动了产品源码 ⇒ 分支不适用。
    """
    path = os.path.join(repo, "eval", "rover", round_id.lower(), "audit-scope-%s.json" % round_id.lower())
    rel = os.path.relpath(path, repo)
    if not os.path.isfile(path):
        return None
    try:
        d = json.loads(io.open(path, "r", encoding="utf-8").read())
    except (ValueError, OSError):
        return {"ok": False, "why": "声明件非法 JSON: %s" % rel, "path": rel}
    sc = d.get("audit_scope")
    if sc is None:
        return None
    if not isinstance(sc, dict):
        return {"ok": False, "why": "audit_scope 非对象", "path": rel}
    kind = str(sc.get("kind", "")).strip()
    reason = str(sc.get("reason", "")).strip()
    readings = sc.get("readings") or []
    faces = sc.get("allowed_faces") or []
    if kind != CONTRAST_SCOPE_KIND:
        return {"ok": False, "why": "kind=%r 非 %s" % (kind, CONTRAST_SCOPE_KIND), "path": rel}
    if len(reason) < 20:
        return {"ok": False, "why": "reason 缺失或过短(<20 字符)", "path": rel}
    if not isinstance(readings, list) or not readings:
        return {"ok": False, "why": "readings 为空（必须显式列出本轮读数面）", "path": rel}
    bad = [p for p in readings
           if not os.path.isfile(os.path.join(repo, p)) or os.path.getsize(os.path.join(repo, p)) == 0]
    if bad:
        return {"ok": False, "why": "读数件缺/为空: %s" % bad, "path": rel}
    if not isinstance(faces, list) or not [f for f in faces if str(f).strip()]:
        return {"ok": False, "why": "allowed_faces 为空（提交面必须显式声明, 不接受省略）", "path": rel}
    return {"ok": True, "path": rel, "kind": kind, "reason": reason,
            "readings": [str(p) for p in readings], "allowed_faces": [str(f) for f in faces],
            "require_form_gate": bool(sc.get("require_form_gate", True)),
            "declared_at": str(d.get("declared_at", "")).strip(),
            "declared_after_run": bool(d.get("declared_after_run", False))}


def commits_for(repo, round_id):
    out = git(repo, "log", "--format=%H\t%s", "-n", "400")
    hits = []
    for line in out.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2 and parts[1].startswith(round_id + ":"):
            hits.append((parts[0], parts[1]))
    return hits


def scan_secrets(text):
    found = []
    for rx, label in SECRET_PATTERNS:
        if rx.search(text):
            found.append(label)
    return found


class Report(object):
    def __init__(self):
        self.items = []

    def add(self, cid, status, detail):
        self.items.append({"id": cid, "status": status, "detail": detail})

    def fails(self):
        return [i for i in self.items if i["status"] == "FAIL"]

    def warns(self):
        return [i for i in self.items if i["status"] == "WARN"]

    def rc(self):
        return 1 if self.fails() else 0

    def render(self, title):
        lines = ["== %s ==" % title]
        for i in self.items:
            lines.append("[%s] %-24s %s" % (i["status"], i["id"], i["detail"]))
        lines.append("总结: FAIL=%d WARN=%d ⇒ rc=%d" % (len(self.fails()), len(self.warns()), self.rc()))
        return "\n".join(lines)


def audit(repo, round_id):
    rep = Report()
    reg = load_registry(repo)
    if reg is None:
        rep.add("R0_registry", "FAIL", "docs/verification-registry.json 缺失或非法 JSON")
        return rep
    rows = rows_for(reg, round_id)

    # 提交面一次性取（供 R1 对照轮分支 / R2 / R6 / R7 复用）
    commits = commits_for(repo, round_id)
    commit_files = []
    if commits:
        commit_files = [f for f in git(repo, "show", "--name-only", "--pretty=format:",
                                       commits[0][0]).splitlines() if f.strip()]
    scope = read_audit_scope(repo, round_id)
    src_touched = [f for f in commit_files if f.startswith("src/")]
    scope_ok = bool(scope and scope.get("ok")) and not src_touched

    # R1 登记行（对照轮分支: 只在「显式声明 ∧ 提交面零 src/」时可 N/A）
    if scope_ok and scope is not None:
        rep.add("R1_registry_row", "PASS",
                "N/A: 零产品源码改动对照轮（声明件 %s, kind=%s, reason=%s…）⇒ 无新能力, "
                "本就不该有登记行（免检由预注册显式声明, 非放宽判据）"
                % (scope["path"], scope["kind"], scope["reason"][:32]))
    else:
        _d = ("%d 行 owner_round=%s" % (len(rows), round_id)) if rows else \
             ("登记表无 owner_round=%s 的行" % round_id)
        if not rows and scope and not scope.get("ok"):
            _d += "（audit_scope 声明无效: %s ⇒ 不豁免）" % scope.get("why")
        if not rows and src_touched:
            _d += "（提交触碰 src/: %s ⇒ 对照轮分支不适用）" % src_touched[:3]
        rep.add("R1_registry_row", "PASS" if rows else "FAIL", _d)

    # R2 提交唯一
    if len(commits) == 1:
        rep.add("R2_commit_unique", "PASS", "1 个提交 %s" % commits[0][0][:9])
    elif not commits:
        rep.add("R2_commit_unique", "FAIL", "无 `%s: ...` 提交（轮次未落档）" % round_id)
    else:
        rep.add("R2_commit_unique", "FAIL", "轮号重号: %d 个提交 %s" % (len(commits), [c[0][:9] for c in commits]))

    # R3 证据文件在位
    missing = []
    for r in rows:
        ev = str(r.get("evidence_path", "")).strip()
        full = os.path.join(repo, ev) if ev else ""
        if not ev or not os.path.exists(full) or os.path.getsize(full) < 200:
            missing.append(ev or "(空)")
    rep.add("R3_evidence_present", "FAIL" if missing else "PASS",
            ("缺/过小: %s" % missing) if missing else ("%d 份证据文件在位" % len(rows)))

    # R4 冻结 pin 与现盘字节一致
    mism = []
    for r in rows:
        ev = str(r.get("evidence_path", "")).strip()
        full = os.path.join(repo, ev)
        eg = r.get("evidence_generated_with") or {}
        want = str(eg.get("artifact_sha12", "")).strip()
        if want and os.path.exists(full):
            got = sha12_of_file(full)
            if got != want:
                mism.append("%s 声明 %s / 实际 %s" % (ev, want, got))
        inst = str(eg.get("instrument", "")).strip()
        want_i = str(eg.get("instrument_sha12", "")).strip()
        if inst and want_i:
            ifull = os.path.join(repo, inst)
            if os.path.exists(ifull):
                got_i = sha12_of_file(ifull)
                if got_i != want_i:
                    mism.append("%s 声明 %s / 实际 %s" % (inst, want_i, got_i))
            else:
                rep.add("R4b_instrument_missing", "WARN", "器具不在盘: %s" % inst)
    rep.add("R4_pin_matches", "FAIL" if mism else "PASS",
            (" | ".join(mism)) if mism else "全部 pin 与现盘一致")

    # R5 证据文档结构
    problems = []
    for r in rows:
        ev = str(r.get("evidence_path", "")).strip()
        txt = read_text(os.path.join(repo, ev)) if ev else None
        if txt is None:
            problems.append("%s 读不到/非文本" % ev)
            continue
        if "诚实边界" not in txt:
            problems.append("%s 缺「诚实边界」段" % ev)
        if re.search(r"TODO|待填|XXX", txt):
            problems.append("%s 含占位符" % ev)
        if len(txt) < 400:
            problems.append("%s 过短(%d 字符)" % (ev, len(txt)))
    rep.add("R5_doc_shape", "FAIL" if problems else "PASS",
            (" | ".join(problems)) if problems else "证据文档结构齐(诚实边界/无占位符/够长)")

    # R6 提交面卫生
    if commits:
        files = commit_files
        junk = [f for f in files if JUNK_RE.search(f)]
        if scope_ok and scope is not None:
            # 对照轮分支: 面形状判据（「全部落在声明的面」）替代**裸计数阈值** ——
            # 逐窗归档面天然 > 40 文件, 而裸计数既不表达「是不是 git add -A 面」也不表达「面是否被声明」。
            faces = scope["allowed_faces"]
            out_of_face = [f for f in files if not any(f.startswith(p) for p in faces)]
            status = "PASS"
            detail = "%d 文件; 全部落在声明的面 %s" % (len(files), faces)
            if out_of_face:
                status, detail = "FAIL", detail + " 越界面: %s" % out_of_face[:5]
            if junk:
                status, detail = "FAIL", detail + " 含垃圾面: %s" % junk[:5]
        else:
            detail = "%d 文件" % len(files)
            status = "PASS"
            if len(files) > 40:
                status, detail = "FAIL", detail + " > 40（疑 `git add -A` 面）"
            if junk:
                status, detail = "FAIL", detail + " 含垃圾面: %s" % junk[:5]
        rep.add("R6_commit_hygiene", status, detail)

        # R7 提交内无 key 面
        hits = []
        for f in files:
            txt = read_text(os.path.join(repo, f))
            if txt is None:
                continue
            labels = scan_secrets(txt)
            if labels:
                hits.append("%s(%s)" % (f, ",".join(labels)))
        rep.add("R7_no_secret_in_commit", "FAIL" if hits else "PASS",
                (" | ".join(hits[:5])) if hits else "本轮提交内未见 key 面")
    else:
        rep.add("R6_commit_hygiene", "FAIL", "无提交可查")
        rep.add("R7_no_secret_in_commit", "FAIL", "无提交可查")

    # R8 读数有档（对照轮分支: 读**声明的读数面**）
    if scope_ok and scope is not None:
        blob = ""
        for p in scope["readings"]:
            blob += (read_text(os.path.join(repo, p)) or "") + "\n"
        lacks = []
        if not re.search(r"\"rc\"\s*[:=]|rc\s*[:=]\s*-?\d", blob):
            lacks.append("判决件 verdict.rc")
        if not re.search(r"\b\d{2,4}\s*/\s*\d{2,4}\b", blob):
            lacks.append("通过率 x/y")
        if scope.get("require_form_gate", True) and "形式门禁" not in blob:
            lacks.append("形式门禁读数（require_form_gate=true）")
        rep.add("R8_readings_backed", "FAIL" if lacks else "PASS",
                ("缺: %s（声明面 %s）" % (", ".join(lacks), scope["readings"])) if lacks else
                ("对照轮读数面齐（声明件）: %s" % scope["readings"]))
    else:
        blob = ""
        for r in rows:
            blob += json.dumps(r, ensure_ascii=False) + "\n"
            ev = str(r.get("evidence_path", "")).strip()
            t = read_text(os.path.join(repo, ev)) if ev else None
            blob += (t or "") + "\n"
        lacks = []
        if "0 error" not in blob and "0 Error" not in blob:
            lacks.append("build 读数(0 error)")
        if "14/14" not in blob:
            lacks.append("形式门禁 14/14")
        if not re.search(r"\b\d{2,4}\s*/\s*\d{2,4}\b", blob):
            lacks.append("通过率 x/y")
        rep.add("R8_readings_backed", "FAIL" if lacks else "PASS",
                ("缺: %s" % ", ".join(lacks)) if lacks else "build/形式/通过率读数在档")

    # R9 暂存面卫生（提交前用）
    staged = [f for f in git(repo, "diff", "--cached", "--name-only").splitlines() if f.strip()]
    if staged:
        junk = [f for f in staged if JUNK_RE.search(f)]
        sec = []
        for f in staged:
            txt = read_text(os.path.join(repo, f))
            if txt and scan_secrets(txt):
                sec.append(f)
        status = "FAIL" if (junk or sec) else "PASS"
        rep.add("R9_staged_hygiene", status, "%d 暂存; 垃圾=%s 敏感=%s" % (len(staged), junk[:3], sec[:3]))
    else:
        rep.add("R9_staged_hygiene", "WARN", "暂存面为空（提交前应恰好等于本轮清单）")

    # W1 工作区 key 面（允许存在, 但提醒别入库）
    dirty = [f for f in (git(repo, "status", "--porcelain").splitlines())]
    wf = []
    for line in dirty:
        f = line[3:].strip()
        txt = read_text(os.path.join(repo, f))
        if txt and scan_secrets(txt):
            wf.append(f)
    rep.add("W1_secret_in_worktree", "WARN" if wf else "PASS",
            ("工作区含 key 面(勿入库): %s" % wf[:5]) if wf else "工作区未见 key 面")
    return rep


def mem_available_mb():
    try:
        for line in io.open("/proc/meminfo", "r", encoding="utf-8"):
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except OSError:
        pass
    return -1


def busy_procs(patterns):
    """在飞执行体探测 (P5)。

    按 **argv[0]** 匹配而不是 `pgrep -f` 的整行匹配: 后者会把**调用者自己**的命令行算进去
    —— 命令串里出现 `agenthost` 字面量就自匹配 ⇒ 假 WARN (R584 实测踩到)。
    argv[0] 是脚本解释器 (dotnet/python3/mono/java) 时再看 argv[1] (被执行的 dll/脚本路径),
    这样 `bash -c "... agenthost ..."` 这类包装命令行不会被误判。
    """
    me = os.getpid()
    interpreters = ("dotnet", "python3", "python", "mono", "java")
    hits = []
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        pid = int(name)
        if pid == me:
            continue
        try:
            with io.open("/proc/%d/cmdline" % pid, "rb") as fh:
                argv = fh.read().decode("utf-8", "replace").split("\0")
        except OSError:
            continue
        argv = [a for a in argv if a.strip()]
        if not argv:
            continue
        targets = [os.path.basename(argv[0])]
        if os.path.basename(argv[0]).split(".")[0] in interpreters and len(argv) > 1:
            targets.append(argv[1])
        for pat in patterns:
            if any(pat in t for t in targets):
                hits.append("%s(pid=%d)" % (pat, pid))
                break
    return hits


def disk_free_gb(path):
    try:
        st = os.statvfs(path)
        return (st.f_bavail * st.f_frsize) // (1024 ** 3)
    except OSError:
        return -1


def preflight(repo, need_keys, min_avail_mb, min_disk_gb, round_id):
    rep = Report()
    for var in need_keys:
        val = os.environ.get(var, "")
        status = "PASS" if val else "FAIL"
        rep.add("P1_key_" + var, status, "set(%d 字符)" % len(val) if val else "UNSET —— 该臂会 VOID")
    models = []
    root = os.path.expanduser("~/.agentframework/models")
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.endswith(".gguf"):
                models.append(os.path.join(dirpath, name))
    rep.add("P2_weights", "PASS" if models else "FAIL",
            "%d 个 gguf 在盘%s" % (len(models), ("; " + os.path.basename(models[0])) if models else ""))
    avail = mem_available_mb()
    rep.add("P3_mem_available", "PASS" if avail >= min_avail_mb else "FAIL",
            "MemAvailable=%dMB (闸 %dMB)" % (avail, min_avail_mb))
    free = disk_free_gb(repo)
    rep.add("P4_disk_free", "PASS" if free >= min_disk_gb else "FAIL",
            "free=%dGB (闸 %dGB)" % (free, min_disk_gb))
    busy = busy_procs(("agenthost", "llama-server"))
    rep.add("P5_no_sibling_load", "WARN" if busy else "PASS",
            ("在飞执行体: %s ⇒ 按同仓并发纪律让行/勿写" % busy) if busy else "无在飞执行体")
    _, claim, _ = sh(["bash", "tools/round_claim.sh", "status"], cwd=repo)
    holder = ""
    for line in claim.splitlines():
        if line.startswith("round="):
            holder = line.split("=", 1)[1].strip()
    if holder and round_id and holder != round_id:
        rep.add("P6_round_claim", "FAIL", "轮号被占: %s（目标 %s）" % (holder, round_id))
    else:
        rep.add("P6_round_claim", "PASS", "轮号占用: %s" % (holder or "(空)"))
    taken = set()
    reg = load_registry(repo)
    if reg:
        for r in reg.get("rows", []):
            taken.add(str(r.get("owner_round", "")).strip())
    _, log, _ = sh(["git", "-C", repo, "log", "--format=%s", "-n", "400"])
    for line in log.splitlines():
        m = re.match(r"^(R\d+[a-zA-Z0-9\-]*)", line)
        if m:
            taken.add(m.group(1))
    if round_id:
        rep.add("P7_round_id_free", "FAIL" if round_id in taken else "PASS",
                ("%s 已被占用" % round_id) if round_id in taken else "%s 空闲" % round_id)
    paused = "yes" if os.path.exists(os.path.join(repo, ".git", "PUSH_PAUSED")) else "no"
    rep.add("P8_push_gate", "PASS", "PUSH_PAUSED=%s（推送前必核）" % paused)
    return rep


def selftest():
    """负控: 器具必须先自证有牙(错 pin 必红 / 提交内 key 面必红 / 无提交必红)。"""
    tmp = tempfile.mkdtemp(prefix="roundcheck-selftest-")
    repo = os.path.join(tmp, "repo")
    os.makedirs(os.path.join(repo, "docs", "evidence", "RF0001"))
    os.makedirs(os.path.join(repo, "tools"))
    sh(["git", "init", "-q", repo])
    git(repo, "config", "user.email", "selftest@example.invalid")
    git(repo, "config", "user.name", "selftest")
    doc = os.path.join(repo, "docs", "evidence", "RF0001", "R1-demo.md")
    body = ("# R1 证据\n读数: build 0 error · 形式 14/14 · 定向 25/25 · 全量 1920/1920。\n"
            "诚实边界: 单窗 n=1, 未跑 reps≥3。\n" + ("填充。" * 120))
    io.open(doc, "w", encoding="utf-8").write(body)
    tool = os.path.join(repo, "tools", "inst.py")
    io.open(tool, "w", encoding="utf-8").write("# instrument\n")
    reg = {"updated_round": "R1", "rows": [{
        "id": "r1.demo", "level": "L2", "owner_round": "R1", "capability": "演示",
        "evidence_cmd": "true", "evidence_path": "docs/evidence/RF0001/R1-demo.md",
        "evidence_generated_with": {"artifact_sha12": "000000000000", "instrument": "tools/inst.py",
                                    "instrument_sha12": sha12_of_file(tool)}}]}
    rp = os.path.join(repo, "docs", "verification-registry.json")
    io.open(rp, "w", encoding="utf-8").write(json.dumps(reg, ensure_ascii=False, indent=1))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "R1: 演示轮")

    fails = []
    r_bad = audit(repo, "R1")
    if not any(i["id"] == "R4_pin_matches" and i["status"] == "FAIL" for i in r_bad.items):
        fails.append("负控1失败: 错 pin 未判红")
    if r_bad.rc() != 1:
        fails.append("负控1失败: rc 应为 1")

    # 修 pin => 应全绿
    reg["rows"][0]["evidence_generated_with"]["artifact_sha12"] = sha12_of_file(doc)
    io.open(rp, "w", encoding="utf-8").write(json.dumps(reg, ensure_ascii=False, indent=1))
    git(repo, "add", "docs/verification-registry.json")
    git(repo, "commit", "-q", "--amend", "-m", "R1: 演示轮")
    r_ok = audit(repo, "R1")
    if r_ok.rc() != 0:
        fails.append("正控失败: 修 pin 后仍红 -> %s" % [i["id"] for i in r_ok.fails()])

    # 负控2: 提交里塞 key 面 => R7 必红
    leak = os.path.join(repo, "corpus.txt")
    io.open(leak, "w", encoding="utf-8").write("AGENTFRAMEWORK_KEYS_DEEPSEEK=" + "x" * 32 + "\n")
    git(repo, "add", "corpus.txt")
    git(repo, "commit", "-q", "-m", "R2: 泄漏样本")
    r_leak = audit(repo, "R2")
    if not any(i["id"] == "R7_no_secret_in_commit" and i["status"] == "FAIL" for i in r_leak.items):
        fails.append("负控2失败: 提交内 key 面未判红")

    # 负控3: 无提交的轮号 => R2 必红
    r_none = audit(repo, "R99")
    if not any(i["id"] == "R2_commit_unique" and i["status"] == "FAIL" for i in r_none.items):
        fails.append("负控3失败: 无提交轮号未判红")

    # 假红控制: 正常 `task-*` 标识符不得误判（本仓大量 task-plan-*/task-length-*）
    benign = '{"id": "frontend.task-progress-and-approval", "round": "R437-task-length-stratification"}'
    if scan_secrets(benign):
        fails.append("假红控制失败: 正常 task- 标识符被误判为 key 面")

    # 假红控制2: P5 在飞执行体探测不得自匹配 —— 调用者自己的命令行里就含 `agenthost` 字面量,
    # 旧实现 `pgrep -f` 会把自己数进去 (R584 实测假 WARN) ⇒ 必须为 0 命中。
    if busy_procs(("agenthost", "llama-server")):
        fails.append("假红控制2失败: P5 自匹配 (调用者自身 cmdline 被当成在飞执行体)")

    # ── 对照轮分支（R587 候选 ⑥）: 正控 1 + 负控 5 ─────────────────────────────
    # 免检「无登记行」必须由**显式声明 ∧ 提交面零 src/ ∧ 声明面可机检**三者共同支撑;
    # 任一条不成立都要回到旧行为(判红) —— 否则这个分支就是「改判据凑绿」。
    repo2 = os.path.join(tmp, "repo2")
    d100 = os.path.join(repo2, "eval", "rover", "rf100")
    os.makedirs(d100)
    os.makedirs(os.path.join(repo2, "docs"))
    sh(["git", "init", "-q", repo2])
    git(repo2, "config", "user.email", "selftest@example.invalid")
    git(repo2, "config", "user.name", "selftest")
    sp = os.path.join(d100, "audit-scope-rf100.json")
    io.open(os.path.join(d100, "verdict-rf100.json"), "w", encoding="utf-8").write(json.dumps(
        {"round": "RF100", "arms": {"P": {"cases_per_run": [58, 58]}},
         "verdict": {"rc": 1, "judge": "FAIL(演示)"}}, ensure_ascii=False))
    rep_doc = os.path.join(d100, "report-rf100.md")

    def write_report(include_form_gate=True):
        body = "# RF100 报告\n读数: 58/58。\n诚实边界: 单窗 n=1。\n" + ("填充。" * 60)
        if include_form_gate:
            body = "# RF100 报告\n读数: 58/58 · 形式门禁 13/13。\n诚实边界: 单窗 n=1。\n" + ("填充。" * 60)
        io.open(rep_doc, "w", encoding="utf-8").write(body)

    write_report()
    io.open(os.path.join(repo2, "docs", "verification-registry.json"), "w", encoding="utf-8").write(
        json.dumps({"updated_round": "RF100", "rows": []}, ensure_ascii=False, indent=1))

    def write_scope(**over):
        sc = {"kind": CONTRAST_SCOPE_KIND,
              "reason": "本轮零产品源码改动: 只跑外部真值 × 产品默认档, 无新能力 ⇒ 本就不该有登记行",
              "readings": ["eval/rover/rf100/verdict-rf100.json", "eval/rover/rf100/report-rf100.md"],
              "allowed_faces": ["eval/rover/rf100/", "docs/"]}
        sc.update(over)
        io.open(sp, "w", encoding="utf-8").write(json.dumps(
            {"declared_at": "selftest", "declared_after_run": True, "audit_scope": sc},
            ensure_ascii=False, indent=1))

    def commit2(msg, extra=None, first=False):
        if extra:
            for p, body in extra:
                full = os.path.join(repo2, p)
                os.makedirs(os.path.dirname(full), exist_ok=True)
                io.open(full, "w", encoding="utf-8").write(body)
        git(repo2, "add", "-A")
        if first:
            git(repo2, "commit", "-q", "-m", msg)
        else:
            git(repo2, "commit", "-q", "--amend", "-m", msg)

    def hit(rep, cid, status):
        return any(i["id"] == cid and i["status"] == status for i in rep.items)

    write_scope()
    commit2("RF100: 对照轮", first=True)
    r_scope = audit(repo2, "RF100")
    if r_scope.rc() != 0 or not hit(r_scope, "R1_registry_row", "PASS") or \
       not hit(r_scope, "R8_readings_backed", "PASS"):
        fails.append("对照轮正控失败: 声明齐+零 src/ 应全绿 -> %s" % [(i["id"], i["status"]) for i in r_scope.fails()])

    # 负控 a: 声明了却动了产品源码 ⇒ 分支不适用, R1 必红
    commit2("RF100: 动了产品源码", extra=[("src/demo.cs", "// demo\n")])
    r_a = audit(repo2, "RF100")
    if not hit(r_a, "R1_registry_row", "FAIL"):
        fails.append("对照轮负控a失败: 触碰 src/ 仍被豁免登记行")
    # 还原(去掉 src/ 文件)
    os.remove(os.path.join(repo2, "src", "demo.cs"))
    os.rmdir(os.path.join(repo2, "src"))
    commit2("RF100: 对照轮")

    # 负控 b: 无声明 ⇒ 旧行为（R1 必红）
    os.rename(sp, sp + ".off")
    r_b = audit(repo2, "RF100")
    if not hit(r_b, "R1_registry_row", "FAIL"):
        fails.append("对照轮负控b失败: 无声明仍免检（旧行为被改坏）")
    os.rename(sp + ".off", sp)

    # 负控 c: 声明非法（读数件缺）⇒ 出声且不豁免
    write_scope(readings=["eval/rover/rf100/verdict-rf100.json", "eval/rover/rf100/does-not-exist.json"])
    r_c = audit(repo2, "RF100")
    if not hit(r_c, "R1_registry_row", "FAIL") or "声明无效" not in \
            " ".join(i["detail"] for i in r_c.items if i["id"] == "R1_registry_row"):
        fails.append("对照轮负控c失败: 非法声明未被拦下/未出声")

    # 负控 d: 声明合法但读数面缺「形式门禁」⇒ R8 必红（豁免不是「什么都免」）
    write_scope()
    write_report(include_form_gate=False)
    r_d = audit(repo2, "RF100")
    if not hit(r_d, "R8_readings_backed", "FAIL"):
        fails.append("对照轮负控d失败: 声明面缺形式门禁读数仍判绿")
    write_report()

    # 负控 e: 提交面越界（未声明的路径）⇒ R6 必红（面形状判据, 不是裸计数）
    commit2("RF100: 越界面", extra=[("notes/extra.md", "out-of-face\n")])
    r_e = audit(repo2, "RF100")
    if not hit(r_e, "R6_commit_hygiene", "FAIL"):
        fails.append("对照轮负控e失败: 越界面未判红")
    os.remove(os.path.join(repo2, "notes", "extra.md"))
    os.rmdir(os.path.join(repo2, "notes"))
    commit2("RF100: 对照轮")
    r_scope2 = audit(repo2, "RF100")
    if r_scope2.rc() != 0:
        fails.append("对照轮还原后应全绿 -> %s" % [(i["id"], i["status"]) for i in r_scope2.fails()])

    print(r_scope.render("对照轮正控（声明齐 + 零 src/）"))
    print(r_a.render("对照轮负控a（触碰 src/）"))
    print(r_b.render("对照轮负控b（无声明）"))
    print(r_c.render("对照轮负控c（声明非法: 读数件缺）"))
    print(r_d.render("对照轮负控d（声明面缺形式门禁）"))
    print(r_e.render("对照轮负控e（提交面越界）"))
    print(r_scope2.render("对照轮还原后"))

    print(r_bad.render("负控1 错 pin"))
    print(r_ok.render("正控 修 pin"))
    print(r_leak.render("负控2 提交内 key 面"))
    print(r_none.render("负控3 无提交轮号"))
    if fails:
        print("SELFTEST FAIL: " + " | ".join(fails))
        return 1
    print("SELFTEST PASS (负控 3/3 有牙 + 正控 1/1 + 假红控制 2/2 + 对照轮分支 正控 1/1 + 负控 5/5)")
    return 0


def main(argv):
    ap = argparse.ArgumentParser(prog="roundcheck")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("audit")
    a.add_argument("--round", required=True)
    p = sub.add_parser("preflight")
    p.add_argument("--need-key", action="append", default=[])
    p.add_argument("--min-avail-mb", type=int, default=2650)
    p.add_argument("--min-disk-gb", type=int, default=5)
    p.add_argument("--round", default="")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    repo = os.path.abspath(args.repo)
    if args.cmd == "audit":
        rep = audit(repo, args.round)
        print(rep.render("roundcheck audit %s @ %s" % (args.round, repo)))
        return rep.rc()
    if args.cmd == "preflight":
        rep = preflight(repo, args.need_key, args.min_avail_mb, args.min_disk_gb, args.round)
        print(rep.render("roundcheck preflight @ %s" % repo))
        return rep.rc()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
