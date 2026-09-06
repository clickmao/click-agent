#!/bin/bash

# AgentFramework GitHub上传脚本
# 使用提供的token上传编译后的二进制文件到GitHub

set -e

echo "🚀 开始上传 AgentFramework 到 GitHub..."

# 配置
# token 从环境变量读取 (绝不硬编码): export GITHUB_TOKEN=ghp_xxx 后运行本脚本
GITHUB_TOKEN="${GITHUB_TOKEN:?set GITHUB_TOKEN first}"
REPO_OWNER="${REPO_OWNER:-clickmao}"
REPO_NAME="AgentFramework"
RELEASE_TAG="v0.10.0"
RELEASE_TITLE="AgentFramework v0.10.0 - AOT编译版本"
RELEASE_DESCRIPTION="AgentFramework v0.10.0版本，支持MiniYaml和LALR.CC两种YAML解析器，NativeAOT零反射编译。"

# 检查编译结果
if [ ! -f "src/agent/bin/Release/net10.0/publish/agent" ]; then
    echo "❌ 未找到编译后的可执行文件，请先运行编译脚本"
    exit 1
fi

# 创建发布目录
mkdir -p release
cd release

# 复制可执行文件
cp ../src/agent/bin/Release/net10.0/publish/agent agent
chmod +x agent

# 创建README
cat > README.md << EOF
# AgentFramework v0.10.0

基于微软 MAF (Microsoft Agent Framework) 与 WebReaper 的功能全面的 C# 智能体框架。

## 🚀 特性

- 🎯 **统一输出接口** - 所有反馈输出走统一底层接口
- 📊 **Token使用统计** - 实时统计、成本计算、余额管理
- 🔒 **敏感意图审批** - 智能检测、分级审批、计划暂停
- 🧩 **Skill标准化** - 符合Anthropic Agent-Skills Open Standard
- 🔧 **反射禁用** - 零反射NativeAOT安全编译
- 🔄 **双YAML解析器** - 支持MiniYaml和LALR.CC

## 📋 系统要求

- .NET 8.0 运行时（如果使用自包含发布，则不需要）
- Linux/macOS/Windows

## 🚀 快速开始

### 1. 下载二进制文件
\`\`\`bash
curl -L -o agent https://github.com/${REPO_OWNER}/${REPO_NAME}/releases/download/${RELEASE_TAG}/agent
chmod +x agent
\`\`\`

### 2. 运行程序
\`\`\`bash
./agent --help
\`\`\`

## 🔧 配置

### YAML解析器选择
创建配置文件 \`yaml-parser-config.json\`：
\`\`\`json
{
  "parserType": "MiniYaml"  // 或 "LALR.CC"
}
\`\`\`

## 📊 性能特性

- **NativeAOT编译** - 单文件发布，无需运行时
- **零反射架构** - 完全类型安全，编译时错误检查
- **高性能** - 编译时代码生成，运行时零开销
- **跨平台** - 支持Linux、macOS、Windows

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

**编译时间**: $(date)
**版本**: v0.10.0
**解析器**: ${PARSER_TYPE:-MiniYaml}
EOF

echo "📦 GitHub上传准备完成!"
echo "📁 发布文件位置: $(pwd)"
echo "📄 README文件: $(pwd)/README.md"
echo "🔗 GitHub仓库: https://github.com/${REPO_OWNER}/${REPO_NAME}"
echo "🏷️  版本标签: ${RELEASE_TAG}"
echo ""
echo "⚠️  注意: 请确保已替换 ${REPO_OWNER} 为你的GitHub用户名"
echo "💡 使用GitHub CLI创建发布:"
echo "   gh release create ${RELEASE_TAG} agent README.md"
echo "📤 手动上传: 请将文件上传到GitHub Releases页面"
