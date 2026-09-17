using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace agent.modelqueue;


/// <summary>
/// R495: 本地决策台账**挂载块** (实发面 + 落盘面 + 打点面共用的同一份结构量)。
/// 挂载轴 = <see cref="LocalDecisionLedger.MountEnvName"/> (默认关; 关 ⇒ <see cref="Off"/> ⇒ 旧行为逐字节不变)。
/// </summary>
/// <param name="Text">挂载文本 (§尾追加的 system 消息; 关时 = 空串)</param>
/// <param name="N">渲染时该会话的台账条数 (关时 = 0)</param>
/// <param name="Code">渲染时该会话的核对码 (关时 = 空串)</param>
/// <param name="Session8">会话指纹 (sha256 前 8 位; 关时 = 空串)</param>
public sealed record LedgerMount(string Text, int N, string Code, string Session8)
{
    /// <summary>挂载关 / 无会话 ⇒ 一个字节都不加 (与 R490..R494 逐字节同形)。</summary>
    public static readonly LedgerMount Off = new(string.Empty, 0, string.Empty, string.Empty);

    public bool On => Text.Length > 0;
}
