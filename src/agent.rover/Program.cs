using System.Text;
using agent.rover.cli;

try { Console.OutputEncoding = Encoding.UTF8; } catch { /* 重定向/无终端时可能不支持, 不影响主流程 */ }
return RoverCli.Run(args, Console.Out, Console.Error);
