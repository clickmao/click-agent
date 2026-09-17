#!/usr/bin/env bash
# R527 候选⑤ — 安装「新增文件结构不变式」前置闸 (幂等, 链式插入, 绝不替换既有钩子)。
# 口径: 目标钩子 = `git config core.hooksPath` 下的 pre-commit (本仓 = tools/hooks/pre-commit,
#       该文件已被版本化, 内含 L4 写者仲裁 / L3 审计面 / EXP1-Q39/Q40/Q41 多级闸)。
#       本闸作为**追加段**插到 `exit 0` 之前, 默认开, 关闸 = AGENTFRAMEWORK_NEW_FILE_GATE=0。
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
HP="$(git config core.hooksPath || true)"
if [ -d "$HP" ] || [ -n "$HP" ]; then HOOK_DIR="$ROOT/$HP"; else HOOK_DIR="$ROOT/.git/hooks"; fi
HOOK="$HOOK_DIR/pre-commit"
echo "目标钩子: $HOOK"
[ -f "$HOOK" ] || { echo "FAIL: 目标钩子不存在 ⇒ 先跑 bash tools/install_hooks.sh" >&2; exit 1; }
if grep -q "R527 new-file-gate" "$HOOK"; then echo "already installed (marker 命中)"; exit 0; fi
python3 - "$HOOK" <<'PY'
import io, sys
p = sys.argv[1]
t = io.open(p, encoding="utf-8").read()
lines = t.rstrip("\n").splitlines()
assert lines[-1].strip() == "exit 0", f"尾行不是 exit 0: {lines[-1]!r}"
stage = ['', '# >>> R527 new-file-gate >>>  (新增 .cs 文件结构不变式前置闸; 只在**新增**文件上判, 存量违规不阻塞)',
         '#   关闸 (诊断/夹具): AGENTFRAMEWORK_NEW_FILE_GATE=0',
         '_NFG_ROOT="$(git rev-parse --show-toplevel)"',
         'if [ "${AGENTFRAMEWORK_NEW_FILE_GATE:-1}" != "0" ] && [ -f "$_NFG_ROOT/tools/refactor/new_file_gate.py" ]; then',
         '  if ! python3 "$_NFG_ROOT/tools/refactor/new_file_gate.py" >/tmp/new_file_gate_precommit.log 2>&1; then',
         '    echo "BLOCKED(R527 新增文件结构闸): 新增 .cs 违反单类型单文件/文件名=类型名/ns 与目录一致/括号或 region 配对。" >&2',
         '    echo "  处置: 修该文件结构后重提交; 关闸 (诊断): AGENTFRAMEWORK_NEW_FILE_GATE=0" >&2',
         '    tail -8 /tmp/new_file_gate_precommit.log >&2',
         '    exit 1',
         '  fi',
         'fi']
io.open(p, "w", encoding="utf-8").write("\n".join(lines[:-1] + stage + ["", "exit 0"]) + "\n")
print("inserted")
PY
grep -c "R527 new-file-gate" "$HOOK"
