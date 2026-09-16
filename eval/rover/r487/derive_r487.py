#!/usr/bin/env python3
"""R487: 由 R482 臂执行器**机派生** R487 臂执行器与 both 驱动器 (禁手抄 + 禁改历史证据)。

语言无关: 纯文本派生 + 断言, 不依赖被派生脚本的语言特性, 只按确定性替换表改写并逐条计数。
派生规则 (每条断言出现次数, 少/多一处即 rc=2 fail-closed, 不写盘):
  1) 命名空间: r482 → r487 (DIR / both 脚本路径 / 日志前缀 / key 变量名)
  2) 被测二进制默认: /tmp/pub_r479v2/agenthost → /tmp/pub_r485/agenthost (含 R485 微闸)
  3) 臂标识: 增加 TAG 维度 (arm_key = ARM+TAG), 使 A0/Arole485/R485 三臂读数**互不覆盖**;
     TAG 为空时输出名与 R482 形态逐字同 (向后兼容, 不破坏既有口径)
  4) 候选⑦: 删掉脚本内**手抄**的起手闸常数 (MEM_GATE_MB=2650 …) ⇒ 改为调用单一源器具
     eval/rover/r483/preflight_gate.py (阈值/沉降/build-server shutdown 只有一处)
  5) both 驱动器: 起手闸前置 (fail-closed) + 三臂顺序执行 (A0 → Arole485 → R485)
历史证据不动: R482/R477/R475 器具与其读数字节不改 (只读)。
三态: rc=0 派生完成并写盘 / rc=2 断言失败 (fail-closed) / rc=3 缺输入。
"""
import argparse
import difflib
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC_ARM = ROOT / "eval" / "rover" / "r482" / "run_arm_real_r482.sh"
SRC_BOTH = ROOT / "eval" / "rover" / "r482" / "run_both_r482.sh"
OUTD = ROOT / "eval" / "rover" / "r487"
PREFLIGHT_REL = "eval/rover/r483/preflight_gate.py"

# ---- 替换表: (旧, 新, 期望次数) ----
ARM_RULES = [
    # 0) 前言块整块替换 (含 2650/r482 的历史注释) ⇒ 派生后机检必须零阈值字面量
    ("# R482 臂执行器 —— 由 R477 版**机派生** (只改: DIR r477→r482 / key 变量名 R477_→R482_ / 默认二进制\n"
     "#   /tmp/pub_r476/agenthost → /tmp/pub_r479v2/agenthost(含 R478 空正文定因+不浪费重试, R479 协议面))。\n"
     "#   其余逐字同 R477 版 (rol 夹具 / 网格 p12 / 中继 v2 / 预算闸 / quiesce / 归档 / MemAvailable 起手闸 2650MB)。\n"
     "#   本文件**不是**对 R477 证据的改写, R477 器具字节不动。\n"
     "#!/usr/bin/env bash\n"
     "# R477 臂执行器 —— 由 R474 版机派生。差异逐条:\n"
     "#   1) DIR r474 → r477 (读数命名空间隔离, 不覆盖 R474 证据)\n"
     "#   2) 中继 relay_real.py(v1) → eval/rover/r475/relay_real_r475.py(v2: +finish_reason/empty_body/\n"
     "#      reasoning_tokens/sampling/逐调用恒等式); v1 文件与 sha 保持不动 (证据↔器具绑定)\n"
     "#   3) 二进制默认 /tmp/r470_publish/agenthost → /tmp/pub_r476/agenthost (含 R475 复述回放守卫 + R476 分档打点)\n"
     "#   4) key 变量 R474_UPSTREAM_KEY → R482_UPSTREAM_KEY (仅转发为 v2 读取的 R475_UPSTREAM_KEY)\n"
     "#   5) + MemAvailable 起手闸 (fail-closed, 2650MB, 与 R475/R476 同常数) 并落盘读数\n"
     "# 其余(配置改写 / role 夹具 / 网格 / 预算闸 / quiesce / 归档)与 R474 逐字同。\n"
     "#   Arole = 门关 + relation_judge=on   ← 生产等价分母\n"
     "#   R     = 门开 + rj=on + repeat_skip=on ← 主判据面 (r1 在管道内)\n"
     "# 与 R467 的差异: 远端由桩改成「本地中继 relay_real.py → 真 DeepSeek 端点」;\n"
     "#   宿主侧 key 仍为 dummy (key 只在中继进程的 env 里, 不落任何文件/日志)。\n"
     "# 用法: bash run_arm_real.sh <Arole|R> [relay_port] [api_port]\n",
     "# R487 臂执行器 —— 由 R482 版**机派生** (eval/rover/r487/derive_r487.py: 替换表逐条计数断言, 差异见 derive_r487.diff)。\n"
     "#   相对 R482 的差异逐条:\n"
     "#   1) DIR r482 → r487 (读数命名空间隔离)\n"
     "#   2) 默认二进制 → /tmp/pub_r485/agenthost (含 R485 微问询预发送闸)\n"
     "#   3) 新增 TAG 维度 ⇒ arm_key = ARM+TAG (A0 / Arole485 / R485 三臂读数互不覆盖; TAG 空时与 R482 形态逐字同)\n"
     "#   4) 候选⑦: 删除脚本内手抄的起手闸常数 ⇒ 改调单一源 eval/rover/r483/preflight_gate.py (本文件零阈值字面量)\n"
     "#   5) A0 臂 = 与 Arole 同臂参 (门关 + rj 开 + repeat_skip off), 只换二进制 ⇒ 隔离微闸单独效应\n"
     "#!/usr/bin/env bash\n"
     "#   A0    = 门关 + rj 开 + repeat_skip off + pub_r479v2 二进制 ← 生产等价分母锚\n"
     "#   Arole = 门关 + relation_judge=on  + pub_r485 二进制      ← 同二进制门关 (隔离微闸)\n"
     "#   R     = 门开 + rj=on + repeat_skip=on + pub_r485 二进制 ← 主判据面 (r1 在管道内)\n"
     "# 远端: 本地中继 relay_real_r475.py(v2) → 真供应商端点; 宿主侧 key 仍为 dummy\n"
     "#   (key 只在中继进程的 env 里, 不落任何文件/日志)。\n"
     "# 用法: bash run_arm_real_r487.sh <A0|Arole|R> [tag] [relay_port] [api_port]\n", 1),
    # 1) 命名空间
    ("DIR=$ROOT/eval/rover/r482", "DIR=$ROOT/eval/rover/r487", 1),
    ("R482_UPSTREAM_KEY", "R487_UPSTREAM_KEY", 3),
    ("# R482 臂 (端点 = 本地中继 v2 → 真供应商; 其余与生产 config/base/models.yaml 逐字同)",
     "# R487 臂 (端点 = 本地中继 v2 → 真供应商; 其余与生产 config/base/models.yaml 逐字同)", 1),
    # 2) 被测二进制默认 + 3) TAG 维度
    ("HOST=${AGENTFRAMEWORK_HOST_BIN:-/tmp/pub_r479v2/agenthost}",
     "HOST=${AGENTFRAMEWORK_HOST_BIN:-/tmp/pub_r485/agenthost}", 1),
    ("ARM=${1:?用法: run_arm_real.sh <Arole|R>}",
     "ARM=${1:?用法: run_arm_real_r487.sh <A0|Arole|R> [tag] [relay_port] [api_port]}\nTAG=${2:-}", 1),
    ("RELAY_PORT=${2:-48110}", "RELAY_PORT=${3:-48710}", 1),
    ("API_PORT=${3:-48112}", "API_PORT=${4:-48712}", 1),
    ("CFG=$DIR/config-$ARM", "CFG=$DIR/config-$ARM$TAG", 1),
    ("CALLS=$DIR/calls-$ARM.jsonl", "CALLS=$DIR/calls-$ARM$TAG.jsonl", 1),
    ("USAGE=$DIR/usage-$ARM.jsonl", "USAGE=$DIR/usage-$ARM$TAG.jsonl", 1),
    ("TURNS=$DIR/turns-$ARM.jsonl", "TURNS=$DIR/turns-$ARM$TAG.jsonl", 1),
    ("HOSTLOG=$DIR/host-$ARM.log", "HOSTLOG=$DIR/host-$ARM$TAG.log", 1),
    ("RELAYLOG=$DIR/relay-$ARM.log", "RELAYLOG=$DIR/relay-$ARM$TAG.log", 1),
    ("SERVLOG=$DIR/server-$ARM.txt", "SERVLOG=$DIR/server-$ARM$TAG.txt", 1),
    ('  Arole) CWD_NAME=run-Arole ;;\n  R)     CWD_NAME=run-R ;;',
     '  A0|Arole) CWD_NAME=run-$ARM$TAG ;;\n  R)        CWD_NAME=run-$ARM$TAG ;;', 1),
    ("RUNDIR=$DIR/$CWD_NAME\nARCH=$DIR/rundata-$ARM", "RUNDIR=$DIR/$CWD_NAME\nARCH=$DIR/rundata-$ARM$TAG", 1),
    # 臂参数: A0 与 Arole 同参 (门关 + rj 开 + repeat_skip off)
    ('  Arole) MP=$M3B; GATE=false; RJ=true;  ROLE="$ROLE_GROWTH"; RS=off ;;',
     '  A0|Arole) MP=$M3B; GATE=false; RJ=true;  ROLE="$ROLE_GROWTH"; RS=off ;;', 1),
    # flags 落盘带 tag (同一臂名可跨二进制, 防覆盖)
    ('"$DIR" "$ARM" "$CFG/base/models.yaml" "$HOST" "$ROLE_GROWTH" "$GRID" "$RS" "$BIN_SHA" "$TASK" "$CWD_NAME"',
     '"$DIR" "$ARM" "$CFG/base/models.yaml" "$HOST" "$ROLE_GROWTH" "$GRID" "$RS" "$BIN_SHA" "$TASK" "$CWD_NAME" "$TAG"', 1),
    ('d, arm, cfg, host, role, grid, rs, bsha, task, cwdname = sys.argv[1:11]',
     'd, arm, cfg, host, role, grid, rs, bsha, task, cwdname, tag = sys.argv[1:12]', 1),
    ('open(os.path.join(d, "flags-%s.json" % arm), "w", encoding="utf-8")',
     'open(os.path.join(d, "flags-%s%s.json" % (arm, tag)), "w", encoding="utf-8")', 1),
    ('"rundir_cwd": "eval/rover/%s/%s" % (os.path.basename(d), cwdname),',
     '"rundir_cwd": "eval/rover/%s/%s" % (os.path.basename(d), cwdname), "arm_key": arm + tag,', 1),
    # 4) 起手闸单一源 (候选⑦): 删手抄常数
    ('MEM_GATE_MB=2650\n'
     'MEM_AVAIL_MB=$(awk \'/MemAvailable/{printf "%d", $2/1024}\' /proc/meminfo)\n'
     'echo "[memgate] MemAvailable=${MEM_AVAIL_MB}MB gate=${MEM_GATE_MB}MB"\n'
     '[ "$MEM_AVAIL_MB" -ge "$MEM_GATE_MB" ] || { echo "[致命] MemAvailable ${MEM_AVAIL_MB}MB < ${MEM_GATE_MB}MB 起手闸"; exit 10; }',
     '# R487 候选⑦: 起手闸/沉降**单一源** (禁手抄) —— 阈值/build-server shutdown/沉降轮询全在\n'
     '#   eval/rover/r483/preflight_gate.py 内; 本文件不含任何阈值字面量 (机检 grep 计数 0)。\n'
     'python3 "$ROOT/%s" --out "$DIR/preflight-$ARM$TAG.json" --round R487 \\\n'
     '  || { echo "[致命] 起手闸未通过 (rc=$?)"; exit 10; }' % PREFLIGHT_REL, 1),
]

BOTH_RULES = [
    ("# R482 双臂顺序执行 (Arole → R)", "# R487 三臂顺序执行 (A0 → Arole485 → R485)", 1),
    ("R482_UPSTREAM_KEY", "R487_UPSTREAM_KEY", 3),
    # 先换具体执行行 (其内嵌 [both-r482] 一并改写), 再扫尾剩余前缀标签
    ("bash eval/rover/r482/run_arm_real_r482.sh Arole 48210 48212 || { echo \"[both-r482] Arole 失败 rc=$?\"; exit 1; }",
     '# R487 候选⑦: 起手闸前置 (fail-closed; 单一源器具, 本脚本不自带 mem 判定)。\n'
     'python3 %s --out eval/rover/r487/preflight-both.json --round R487 \\\n'
     '  || { echo "[both-r487] 起手闸未通过 (rc=$?) ⇒ 拒跑"; exit 10; }\n'
     'echo "[both-r487] gate PASS $(date +%%H:%%M:%%S)"\n'
     'AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r479v2/agenthost bash eval/rover/r487/run_arm_real_r487.sh A0 "" 48710 48712 '
     '|| { echo "[both-r487] A0 失败 rc=$?"; exit 1; }' % PREFLIGHT_REL, 1),
    ("bash eval/rover/r482/run_arm_real_r482.sh R 48214 48213 || { echo \"[both-r482] R 失败 rc=$?\"; exit 2; }",
     'AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r485/agenthost bash eval/rover/r487/run_arm_real_r487.sh Arole 485 48714 48713 '
     '|| { echo "[both-r487] Arole485 失败 rc=$?"; exit 2; }\n'
     'echo "[both-r487] Arole485 ok $(date +%H:%M:%S)"\n'
     'AGENTFRAMEWORK_HOST_BIN=/tmp/pub_r485/agenthost bash eval/rover/r487/run_arm_real_r487.sh R 485 48716 48715 '
     '|| { echo "[both-r487] R485 失败 rc=$?"; exit 3; }', 1),
    ("[both-r482]", "[both-r487]", 4),          # start / Arole ok / R ok / ALLDONE
    ('echo "[both-r487] Arole ok $(date +%H:%M:%S)"', 'echo "[both-r487] A0 ok $(date +%H:%M:%S)"', 1),
]


def apply_rules(text, rules, label, asserts):
    out = text
    for i, (old, new, want) in enumerate(rules):
        got = out.count(old)
        asserts.append({"file": label, "rule": i, "old_head": old.splitlines()[0][:70],
                        "want": want, "got": got})
        if got != want:
            return None
        out = out.replace(old, new)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="允许覆盖已存在的 r487 脚本")
    a = ap.parse_args()
    for p in (SRC_ARM, SRC_BOTH):
        if not p.is_file():
            print("MISS:", p)
            return 3
    outs = {"run_arm_real_r487.sh": OUTD / "run_arm_real_r487.sh",
            "run_both_r487.sh": OUTD / "run_both_r487.sh"}
    if not a.force and any(p.exists() for p in outs.values()):
        print("[REFUSE] r487 脚本已存在 (幂等闸); 用 --force 覆盖")
        return 2

    srcs = {"run_arm_real_r487.sh": SRC_ARM.read_text(encoding="utf-8"),
            "run_both_r487.sh": SRC_BOTH.read_text(encoding="utf-8")}
    asserts = []
    derived = {"run_arm_real_r487.sh": apply_rules(srcs["run_arm_real_r487.sh"], ARM_RULES,
                                                   "run_arm_real_r487.sh", asserts),
               "run_both_r487.sh": apply_rules(srcs["run_both_r487.sh"], BOTH_RULES,
                                               "run_both_r487.sh", asserts)}
    if any(v is None for v in derived.values()):
        print(json.dumps({"verdict": "FAIL_ASSERT", "asserts": asserts}, ensure_ascii=False, indent=1))
        return 2

    # 派生后自检 (机检, 非人读):
    #   a) 阈值字面量 `2650` 必须为 0 (候选⑦: 常数只在单一源器具里)
    #   b) 单一源器具必须被**调用** (>=1 次引用)
    #   c) 旧命名空间**可执行形态**残留必须为 0 —— 仅统计会改变行为的字面量
    #      (路径/变量/标签/旧脚本名); 前言散文里「由 R482 版机派生」这类历史叙述不计。
    RESIDUE = ("rover/r482", "R482_UPSTREAM_KEY", "[both-r482]", "r482/",
               "run_arm_real_r482.sh", "run_both_r482.sh")
    post = {}
    for name, txt in derived.items():
        post[name] = {
            "literal_2650_count": txt.count("2650"),
            "preflight_gate_refs": txt.count(PREFLIGHT_REL),
            "old_namespace_residue": {k: txt.count(k) for k in RESIDUE if txt.count(k)},
            "lines": len(txt.splitlines()),
            "sha256": hashlib.sha256(txt.encode("utf-8")).hexdigest(),
        }
    ok_post = all(p["literal_2650_count"] == 0
                  and p["preflight_gate_refs"] >= 1
                  and not p["old_namespace_residue"] for p in post.values())
    if not ok_post:
        print(json.dumps({"verdict": "FAIL_POSTCHECK", "post": post}, ensure_ascii=False, indent=1))
        return 2

    OUTD.mkdir(parents=True, exist_ok=True)
    diff_txt = []
    for name, txt in derived.items():
        outs[name].write_text(txt, encoding="utf-8")
        outs[name].chmod(0o755)
        diff_txt += list(difflib.unified_diff(srcs[name].splitlines(keepends=True),
                                              txt.splitlines(keepends=True),
                                              fromfile="a/eval/rover/r482/%s" % name,
                                              tofile="b/eval/rover/r487/%s" % name))
    (OUTD / "derive_r487.diff").write_text("".join(diff_txt), encoding="utf-8")
    rec = {"round": "R487", "derived_from": {"run_arm_real_r487.sh": str(SRC_ARM.relative_to(ROOT)),
                                             "run_both_r487.sh": str(SRC_BOTH.relative_to(ROOT))},
           "rules_total": len(ARM_RULES) + len(BOTH_RULES), "asserts": asserts, "postcheck": post,
           "verdict": "PASS"}
    (OUTD / "derive_r487.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n",
                                           encoding="utf-8")
    print(json.dumps({"verdict": "PASS", "postcheck": post,
                      "rules": rec["rules_total"],
                      "asserts_all_want_equal_got": all(x["want"] == x["got"] for x in asserts)},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
