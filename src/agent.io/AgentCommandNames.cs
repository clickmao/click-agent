using System;
using System.Collections.Generic;
using System.Text;

namespace agent.io
{
    /// <summary>已知命令名 (框架内约定; 扩展命令直接传新名 — 前向兼容)。</summary>
    public static class AgentCommandNames
    {
        /// <summary>余额不足 (模型已切换): model=新模型 from=原模型 remaining=剩余额度 reason=原因</summary>
        public const string BalanceInsufficient = "balance_insufficient";

        /// <summary>思考页切换 (分片推送): seq=分片序号 session=会话</summary>
        public const string ThinkingPageSwitch = "thinking_page_switch";

        /// <summary>思考结束 (前端折叠思考区): summary_length=摘要长度 session=会话</summary>
        public const string ThinkingEnd = "thinking_end";

        /// <summary>输出追加: seq=序号 session=会话</summary>
        public const string OutputAppend = "output_append";

        /// <summary>模型切换: from=原模型 to=新模型 reason=切换原因</summary>
        public const string ModelSwitch = "model_switch";

        /// <summary>Skill 脚本进度: skill=技能id message=进度文本</summary>
        public const string SkillProgress = "skill_progress";

        /// <summary>Skill 脚本完成: skill=技能id exit=退出码 duration_ms=耗时</summary>
        public const string SkillDone = "skill_done";
    }
}
