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

    # R1 登记行
    rep.add("R1_registry_row", "PASS" if rows else "FAIL",
            ("%d 行 owner_round=%s" % (len(rows), round_id)) if rows else ("登记表无 owner_round=%s 的行" % round_id))

    # R2 提交唯一
    commits = commits_for(repo, round_id)
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
        files = git(repo, "show", "--name-only", "--pretty=format:", commits[0][0]).splitlines()
        files = [f for f in files if f.strip()]
        junk = [f for f in files if JUNK_RE.search(f)]
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

    # R8 读数有档
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
            ("缺: %s" % ",".join(lacks)) if lacks else "build/形式/通过率读数在档")

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
    busy = []
    for pat in ("agenthost", "llama-server"):
        rc, out, _ = sh(["pgrep", "-c", "-f", pat])
        if out.isdigit() and int(out) > 0:
            busy.append("%s×%s" % (pat, out))
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

    print(r_bad.render("负控1 错 pin"))
    print(r_ok.render("正控 修 pin"))
    print(r_leak.render("负控2 提交内 key 面"))
    print(r_none.render("负控3 无提交轮号"))
    if fails:
        print("SELFTEST FAIL: " + " | ".join(fails))
        return 1
    print("SELFTEST PASS (负控 3/3 有牙 + 正控 1/1)")
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
