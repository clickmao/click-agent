using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace agent.modelqueue;


public sealed record LocalChannelDecision(bool Allowed, LocalChannelRejectReason Reason)
{
    public static readonly LocalChannelDecision Allow = new(true, LocalChannelRejectReason.None);

    public string ReasonText => Reason switch
    {
        LocalChannelRejectReason.None => "ok",
        LocalChannelRejectReason.ChannelDisabled => "channel_disabled",
        LocalChannelRejectReason.KindNotAllowed => "kind_not_allowed",
        LocalChannelRejectReason.ImageRequest => "image_request",
        LocalChannelRejectReason.PromptTooLong => "prompt_too_long",
        LocalChannelRejectReason.PortMissing => "port_missing",
        LocalChannelRejectReason.PortUnavailable => "port_unavailable",
        LocalChannelRejectReason.AccountingInconsistent => "accounting_inconsistent",
        _ => "unknown",
    };
}
