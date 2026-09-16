#!/usr/bin/env python3
"""R491 器具机派生器 (承 R488 教训: 臂/驱动器一律由上一轮机派生, 禁手抄)。

用途: 由 R490 目录**机械派生**出 R491 的三类产物 —— 臂脚本 / 链脚本 / 辅助器具 (含 teardown 断言)。

R491 新增的派生纪律 (本轮机踩中后补):
  · **辅助器具必须同批携带**: 上一轮机只搬了 run_arm/run_rest 两个文件, teardown_assert.py 漏搬 ⇒
    真机跑到收尾才炸 (「[致命] teardown 断言红 / Arole 失败 rc=11」), quiesce 那 6 分钟白等。
    ⇒ 现在 aux 集由「上一轮目录里全部 .py/.sh 减去本轮另行派生者」**枚举**得到, 不靠人记。
  · **链脚本的臂序列由 PLAN 表生成** (单一来源), 不用整行替换; 端口/arg 全部来自 PLAN。
  · **引用存在性 fail-closed**: 派生出的脚本里出现的每个 `<name>.py|.sh` 必须在磁盘上存在。

用法:
  python3 eval/rover/r491/derive_r491.py                # 全量 (Arole T1 T2 T3)
  python3 eval/rover/r491/derive_r491.py --arms T1 T2 T3
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R490 = os.path.join(HERE, "..", "r490")

# ── 臂计划 (单一来源: 端口 491xx 与 R490 同构, tag 见 run_rest) ──────────────────
PLAN = [
    ("Arole", "b", 49110, 49112),
    ("T", "1", 49114, 49116),
    ("T", "2", 49118, 49120),
    ("T", "3", 49122, 49124),
]
# R490 里作为「行模板」的那条臂调用 (R 臂), 派生物由它替换 argv/端口
TEMPLATE_MARK = "run_arm_real_r490.sh R 1 49014 49016"

RENAMES = [("r490", "r491"), ("R490", "R491"), ("r49", "r49")]  # r49 恒等, 占位防误伤
AUX_EXCLUDE = ("analyze_r490.py", "derive_r491.py")            # 另行派生

# 端口字面量必须**显式**改写: 5 位端口号 `49010` 里没有 `r490` 子串 ⇒ 纯命名空间替换漏改
# (R491 首次派生实测踩中: 臂脚本校验报「缺锚点 49110」, 而文件里还写着 49010)。
# 只改 490xx 这 8 个已知端口, 不做泛化的 490→491 (防误伤无关数字)。
PORT_MAP = {"49010": "49110", "49012": "49112", "49014": "49114", "49016": "49116",
            "49018": "49118", "49020": "49120", "49022": "49122", "49024": "49124"}
PORT_RE = re.compile(r"\b(490(?:10|12|14|16|18|20|22|24))\b")


def rewrite(text: str) -> str:
    out = text.replace("r490", "r491").replace("R490", "R491")
    return PORT_RE.sub(lambda m: PORT_MAP[m.group(1)], out)


def ports_rewritten(src: str) -> int:
    return len(PORT_RE.findall(src))


def read(p: str) -> str:
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p: str, text: str) -> None:
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def check_clean(path: str, text: str) -> None:
    """派生物不得残留旧命名空间 (fail-closed)。"""
    bad = [ln for ln in text.splitlines() if re.search(r"\br490\b|R490", ln)]
    if bad:
        raise SystemExit("[derive] FATAL 残留旧命名空间 %s: %s" % (path, bad[:3]))


# ── ① 臂脚本 ─────────────────────────────────────────────────────────────────
def derive_arm() -> str:
    src = os.path.join(R490, "run_arm_real_r490.sh")
    dst = os.path.join(HERE, "run_arm_real_r491.sh")
    text = rewrite(read(src))
    for must in ("/tmp/pub_r491/agenthost", "R491_UPSTREAM_KEY", "49110", "49112"):
        if must not in text:
            raise SystemExit("[derive] FATAL 臂脚本缺锚点: " + must)
    if ports_rewritten(read(src)) < 2:
        raise SystemExit("[derive] FATAL 臂脚本端口改写数为 0 ⇒ 端口映射失效")
    check_clean(dst, text)
    write(dst, text)
    os.chmod(dst, 0o755)
    return dst


# ── ② 链脚本 (臂序列由 PLAN 生成) ─────────────────────────────────────────────
def derive_rest(arms: list[str]) -> str:
    src = os.path.join(R490, "run_rest_r490.sh")
    dst = os.path.join(HERE, "run_rest_r491.sh")
    lines = read(src).splitlines()
    idx = [i for i, l in enumerate(lines) if TEMPLATE_MARK in l]
    if len(idx) != 1:
        raise SystemExit("[derive] FATAL 链脚本里臂模板行不唯一: %d" % len(idx))
    i = idx[0]
    any_arm = [k for k, l in enumerate(lines) if "run_arm_real_r490.sh" in l]
    head = lines[: min(any_arm)]                       # shebang/注释/key/起手闸/二进制变量 (首个臂行之前)
    if len(any_arm) < 2:
        raise SystemExit("[derive] FATAL 链脚本臂行数 < 2 ⇒ 形状可疑")
    tmpl = lines[i]                                    # 臂调用模板 (取 R 臂)
    ok_tmpl = lines[i + 1]                             # 紧随其后的 "[rest-r491] R1 ok ..." 行
    if "run_arm_real_r490.sh R 1 49014 49016" not in tmpl or "ok" not in ok_tmpl or "R1" not in ok_tmpl:
        raise SystemExit("[derive] FATAL 链脚本模板形状变了: %r / %r" % (tmpl[:60], ok_tmpl[:60]))
    final = [l for l in lines[i:] if "ALLDONE" in l]
    if len(final) != 1:
        raise SystemExit("[derive] FATAL 链脚本 ALLDONE 行不唯一: %d" % len(final))
    if not head:
        raise SystemExit("[derive] FATAL 链脚本头为空")
    body = list(head)
    for arm, tag, a1, a2 in PLAN:
        if arms and (arm + tag) not in arms:
            continue
        body.append(tmpl.replace("run_arm_real_r490.sh R 1 49014 49016",
                                 "run_arm_real_r491.sh %s %s %d %d" % (arm, tag, a1, a2))
                          .replace("R1 失败", arm + tag + " 失败"))
        body.append(ok_tmpl.replace("R1", arm + tag))
    body.append(final[0])
    text = rewrite("\n".join(body)) + "\n"
    if arms and any("run_arm_real_r491.sh" in l for l in head):
        raise SystemExit("[derive] FATAL 头部残留臂行 ⇒ 会重复执行")
    for arm, tag, a1, a2 in PLAN:
        if arms and (arm + tag) not in arms:
            continue
        if "run_arm_real_r491.sh %s %s %d %d" % (arm, tag, a1, a2) not in text:
            raise SystemExit("[derive] FATAL 链脚本缺臂: %s%s" % (arm, tag))
    for arm, tag, _, _ in PLAN:                        # 未入列的臂不得出现 (含其 echo 行)
        if arms and (arm + tag) not in arms:
            if "%s%s ok" % (arm, tag) in text:
                raise SystemExit("[derive] FATAL 链脚本残留未入列臂的 echo: %s%s" % (arm, tag))
            if "run_arm_real_r491.sh %s %s " % (arm, tag) in text:
                raise SystemExit("[derive] FATAL 链脚本残留未入列臂: %s%s" % (arm, tag))
    check_clean(dst, text)
    write(dst, text)
    os.chmod(dst, 0o755)
    return dst


# ── ③ 辅助器具同批携带 ───────────────────────────────────────────────────────
def carry_aux() -> list[str]:
    out = []
    for name in sorted(os.listdir(R490)):
        if not name.endswith((".py", ".sh")):
            continue
        if name.startswith(("run_arm_real_", "run_rest_")) or name in AUX_EXCLUDE:
            continue
        src = os.path.join(R490, name)
        dst_name = name.replace("r490", "r491").replace("R490", "R491")
        dst = os.path.join(HERE, dst_name)
        text = read(src)
        if "r490" in text or "R490" in text:
            text = rewrite(text)
            check_clean(dst, text)
        write(dst, text)
        if dst_name.endswith(".sh"):
            os.chmod(dst, 0o755)
        out.append(dst_name)
    return out


# ── ④ 形式门禁: 语法 + 引用存在性 ────────────────────────────────────────────
def gate(paths: list[str]) -> None:
    for p in paths:
        if p.endswith(".py"):
            subprocess.run([sys.executable, "-m", "py_compile", p], check=True)
        else:
            r = subprocess.run(["bash", "-n", p], capture_output=True, text=True)
            if r.returncode != 0:
                raise SystemExit("[derive] FATAL bash -n %s: %s" % (p, r.stderr))
    missing = []
    repo = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
    rover = os.path.abspath(os.path.join(HERE, ".."))
    import glob as _glob
    for p in paths:
        for tok in set(re.findall(r"[\w./${}-]+\.(?:py|sh)\b", read(p))):
            parts = tok.split("/")
            ok = False
            for k in range(len(parts)):                      # 逐层剥掉 shell 变量前缀 ($ROOT/…, ${DIR}/…)
                sub = "/".join(parts[k:])
                if not sub.endswith((".py", ".sh")):
                    continue
                cands = [os.path.join(HERE, sub), os.path.join(R490, sub), os.path.join(repo, sub)]
                if any(os.path.exists(c) for c in cands):
                    ok = True
                    break
            if not ok:                                       # 兜底: 在 eval/rover 下按 basename 找 (器具散落在各轮机目录)
                base = parts[-1]
                if _glob.glob(os.path.join(rover, "**", base), recursive=True):
                    ok = True
            if not ok:
                missing.append((os.path.basename(p), tok))
    if missing:
        raise SystemExit("[derive] FATAL 引用的器具不存在: %s" % missing[:6])
    print("[derive] 形式门禁 PASS (语法 + 引用存在性): %s" % ", ".join(os.path.basename(x) for x in paths))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="*", default=None, help="只生成这些臂 (如 T1 T2 T3); 缺省全量")
    ns = ap.parse_args()
    arm = derive_arm()
    rest = derive_rest(ns.arms or [])
    aux = carry_aux()
    gate([arm, rest] + [os.path.join(HERE, a) for a in aux])
    print("[derive] 产出:")
    print("  臂   :", os.path.relpath(arm))
    print("  链   :", os.path.relpath(rest), "臂序:", ns.arms or [a + t for a, t, _, _ in PLAN])
    print("  辅助 :", ", ".join(aux))
    return 0


if __name__ == "__main__":
    sys.exit(main())
