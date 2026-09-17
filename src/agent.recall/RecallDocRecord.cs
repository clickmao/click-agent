namespace agent.recall;


public sealed class RecallDocRecord
{
    public required int DocId { get; init; }
    public required string Id { get; init; }
    public required string Path { get; init; }
    public required long TextOffset { get; init; }
    public required int TextLength { get; init; }
    public required int DocLenTokens { get; init; }
    public required long Size { get; init; }
    public required long MtimeTicks { get; init; }
    public required long Inode { get; init; }

    public byte[] Encode()
    {
        var buf = new ByteBuffer(64 + Id.Length + Path.Length);
        var idBytes = System.Text.Encoding.UTF8.GetBytes(Id);
        var pathBytes = System.Text.Encoding.UTF8.GetBytes(Path);
        buf.WriteVarInt((ulong)idBytes.Length);
        buf.Write(idBytes);
        buf.WriteVarInt((ulong)pathBytes.Length);
        buf.Write(pathBytes);
        buf.WriteVarInt((ulong)TextOffset);
        buf.WriteVarInt((ulong)TextLength);
        buf.WriteVarInt((ulong)DocLenTokens);
        buf.WriteVarInt((ulong)Math.Max(0, Size));
        buf.WriteVarInt((ulong)Math.Max(0, MtimeTicks));
        buf.WriteVarInt((ulong)Math.Max(0, Inode));
        return buf.Span.ToArray();
    }

    public static RecallDocRecord Decode(ReadOnlySpan<byte> src)
    {
        int p = 0;
        int used = VarInt.Read(src[p..], out ulong idLen);
        p += used;
        string id = System.Text.Encoding.UTF8.GetString(src.Slice(p, (int)idLen));
        p += (int)idLen;
        used = VarInt.Read(src[p..], out ulong pathLen);
        p += used;
        string path = System.Text.Encoding.UTF8.GetString(src.Slice(p, (int)pathLen));
        p += (int)pathLen;
        p += VarInt.Read(src[p..], out ulong textOffset);
        p += VarInt.Read(src[p..], out ulong textLen);
        p += VarInt.Read(src[p..], out ulong docLen);
        p += VarInt.Read(src[p..], out ulong size);
        p += VarInt.Read(src[p..], out ulong mtime);
        p += VarInt.Read(src[p..], out ulong inode);
        return new RecallDocRecord
        {
            DocId = 0,
            Id = id,
            Path = path,
            TextOffset = (long)textOffset,
            TextLength = (int)textLen,
            DocLenTokens = (int)docLen,
            Size = (long)size,
            MtimeTicks = (long)mtime,
            Inode = (long)inode,
        };
    }
}
