using System.IO.Compression;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Security.Cryptography;
using System.Text;

namespace agent.roles;


/// <summary>AOT source-gen (payload 是扁平 string→string 字典)。</summary>
[JsonSerializable(typeof(Dictionary<string, string>))]
internal sealed partial class PayloadJsonContext : JsonSerializerContext;
