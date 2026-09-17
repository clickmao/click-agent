namespace agent.skills;


/// <summary>Skill 类型: normative=口径型 (模板+禁语) / executive=执行型 (entry 委托)</summary>
public enum SkillType
{
    Normative,
    Executive,
    /// <summary>知识提示型 (v0.15.2 R326-f): 命中 → SKILL.md body 作生成参考注入, 回复仍走 LLM 主链 (不直出/不吞提问)</summary>
    KnowledgeHint,
}
