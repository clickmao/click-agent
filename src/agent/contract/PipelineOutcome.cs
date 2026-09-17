namespace agent.contract;

/// <summary>R1 管道判定：rc 编码分支（0=可推进/无需执行, 2=缺信息要澄清, 3=硬闸拒答, 4=计划非法, 5=执行未达期望）。</summary>
public sealed record PipelineOutcome(int Rc, string Stage, string Reason, bool Halted);
