using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace agent.modelqueue;


/// <summary>本地通道不采用的原因 (拒绝原因必须显式 — 不允许静默跳过)。</summary>
public enum LocalChannelRejectReason
{
    None,
    ChannelDisabled,
    KindNotAllowed,
    ImageRequest,
    PromptTooLong,
    PortMissing,
    PortUnavailable,
    AccountingInconsistent,
}
