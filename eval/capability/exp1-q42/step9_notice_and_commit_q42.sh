#!/usr/bin/env bash
# EXP1-Q42 step 9 (M5 + 真提交): 漂移通知件现场读数 + 本地提交 + 回读
set -u
cd /home/agentuser/AgentFramework
D=eval/capability/exp1-q42

echo "--- M5 通知件在真实提交面上的现场读数 (green check 日志) ---"
python3 eval/capability/exp1-q41/commit_face_notice_q41.py --log "$D/bind_check_q42b.txt" \
  > "$D/notice_live_q42.txt" 2>&1; echo "notice_rc=$?"
echo "notice_lines=$(wc -l < "$D/notice_live_q42.txt")"
cat "$D/notice_live_q42.txt" | head -5 | cut -c1-160

echo "--- 本地提交 (推送暂停令在效; 只 commit) ---"
git commit -q -m "EXP1-Q42: 尾 LF 闸转正的期望时效收口 + exp1q41.* 三条能力登记 + 登记表形态反解

- 转正副作用收口: selftest_q40_taillf 的 E5 原期望「默认档放行坏清单」在 EXP1-Q41 转正后过期
  (首跑实测 9/10, E5 FAIL) ⇒ 改为「默认档拦下」+ 新增 E5b「显式关闸放行」; 11/11 绿。
  前态/现态负控 5/5 (nc_prestate_q42.py, 前态钉 ecd363d)。
- 登记 exp1q41.* 三条 (L2, 各带成对控制): 闸转正+期望刷新 / 回放分类误报0+扩面否决 / 漂移通知件成对控制。
- 根因修复: bind_evidence.py 序列化器硬编码 indent=1, 而登记表自 R500 起现盘为 indent=2 ⇒
  --apply 恒 SER_ASSERT=FAIL rc=3 (登记通路死亡) ⇒ 改为**从现盘反解形态** (反解失败仍 fail-closed);
  定向重审 5 行 + decl_sweep RE_AUDITED=1; bind_evidence --check rc=0。
- 证据件纪律: classified 归档含 HEAD 字段 (head_ct) 重跑字节必变 ⇒ 不作冻结 pin;
  改取输入不变归档 + 确定性校验器 (verify_replay_archive_q42.py, V6 同输入两遍字节相同)。
- 形式门禁 dotnet test (VerificationForm|SkillGeneralization|DevPlanDocRef): Failed 0 / Passed 14, rc=0。" \
  > "$D/commit_q42.txt" 2>&1; echo "commit_rc=$?"
tail -6 "$D/commit_q42.txt" | cut -c1-200

echo "--- 现场读数: 提交面尾 LF 闸 (默认开) ---"
tail -3 /tmp/tail_lf_precommit.log 2>/dev/null | cut -c1-160

echo "--- 回读 HEAD ---"
git log --oneline -1
git show --stat --oneline HEAD | tail -8 | cut -c1-140
echo "HEAD_REG_SHA=$(git show HEAD:docs/verification-registry.json | sha256sum | cut -c1-16)"
echo "DISK_REG_SHA=$(sha256sum docs/verification-registry.json | cut -c1-16)"
