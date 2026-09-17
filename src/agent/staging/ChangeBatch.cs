using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace agent.staging;


/// <summary>v0.17.1: 变更批次。Status: pending → approved(全应用)/partial(部分冲突)/rejected/expired。</summary>
public sealed class ChangeBatch
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N")[..12];
    public string Source { get; set; } = "agent";
    public string Status { get; set; } = "pending";
    public long CreatedUnixMs { get; set; }
    public long UpdatedUnixMs { get; set; }
    public int TtlDays { get; set; } = 7;
    public List<StagedItem> Items { get; set; } = new();

    public bool IsPending => Status == "pending";
}
