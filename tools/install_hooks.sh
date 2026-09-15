#!/usr/bin/env bash
# 安装 L4 写者仲裁 + 推送闸门钩子 (R444)。幂等。
#   core.hooksPath -> tools/hooks, 使钩子随仓库版本化 (不再散落在 .git/hooks)。
set -eu
cd "$(dirname "$0")/.."
chmod +x tools/hooks/pre-commit tools/hooks/pre-push tools/round_claim.sh
git config core.hooksPath tools/hooks
echo "core.hooksPath=$(git config core.hooksPath)"
ls -l tools/hooks/
echo "自检: bash tools/hooks/pre-commit; echo rc=\$?  (应 rc=0; registry 违规时 rc=1)"
