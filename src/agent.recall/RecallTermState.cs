namespace agent.recall;


internal sealed class RecallTermState
{
    public byte[] Term = Array.Empty<byte>();
    public readonly ByteBuffer Blocks = new(256);
    public readonly ByteBuffer Payload = new(256);
    public int LastDocId = -1;
    public int TotalDocs;
    public int MaxTf;
    public int NumBlocks;
    public int BlockDocs;
    public int BlockMaxTf;
    public int BlockLastDocId;
}
