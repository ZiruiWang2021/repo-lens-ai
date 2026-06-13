# 构建 RepoLens AI：一个用证据回答问题的代码库智能体

GitHub: https://github.com/ZiruiWang2021/repo-lens-ai

语言版本：[English](TECHNICAL_BLOG.md) | [简体中文](TECHNICAL_BLOG.zh-CN.md)

## Problem

大型代码库很难快速理解。一个新加入项目的工程师经常会问：

- 这个行为在哪里实现？
- 哪些文件和这个 bug 相关？
- 这个 pull request 是否引入安全风险？
- 这个 AI 回答有没有足够证据可以相信？

很多 AI coding demo 只展示聊天框，但真实工程场景里更难的是上下文：如何索引正确文件、检索正确片段、让回答带引用，以及防止仓库文本反过来控制 Agent。

## Why It Matters

对于 AI 工程岗位，一个有价值的代码库助手不能只是调用一次 LLM。它需要围绕 LLM 搭建可复现、可检查、可测试、相对安全的软件系统。

RepoLens AI 用一个紧凑的开源项目展示这些能力：

- 面向代码库的 Context Engineering
- 带文件引用的 RAG 问答
- CLI、REST、MCP 三种工具接口
- 无需付费 API Key 的离线 demo 模式
- 用测试和 CI 验证核心行为，而不是只做 happy-path 演示

## My Approach

我的核心设计原则是：仓库内容是有用上下文，但必须被当作不可信数据。

系统首先索引本地路径或公开 GitHub repository archive，将文件、符号、代码块、行号、摘要和本地确定性 embedding 写入 SQLite。当用户提问时，检索器会结合关键词匹配、向量相似度、路径提示和符号提示来排序相关代码块。Agent 只基于检索到的上下文回答，并返回明确的文件引用。

对于 pull request review，MVP 使用确定性规则识别应该被测试覆盖的风险：硬编码密钥、动态代码执行、缺少测试、疑似 prompt injection 等。输出采用结构化 schema，而不是纯自然语言，这样更容易接入自动化流程。

## Technical Implementation

RepoLens AI 使用 Python 3.12，并刻意保持技术栈简单：

- FastAPI：本地 API
- Typer：CLI
- SQLite：本地代码索引
- 静态 HTML/CSS/JavaScript：工作台 UI
- Pydantic：稳定的请求和响应 schema
- Ruff、mypy、pytest、GitHub Actions：工程质量保障

主要模块划分如下：

- `repolens/indexer.py`：文件过滤、代码切块、符号提取和仓库索引
- `repolens/retrieval.py`：基于文本、符号、路径和向量的混合排序
- `repolens/agent.py`：带引用问答、review 编排和 prompt injection 提示
- `repolens/providers.py`：demo、OpenAI-compatible、Ollama 模型适配器
- `repolens/api.py`：REST API 和静态 UI
- `repolens/mcp_server.py`：给 AI 编程助手调用的 MCP 工具

这个架构足够轻量，可以本地运行；同时每个模块都对应一个真实 AI Agent 系统里的工程边界：ingestion、storage、retrieval、model adapter、tool interface 和 evaluation。

## Results / Demo

默认 demo provider 不需要 API Key。

```bash
python -m pip install -e ".[dev]"
repolens index examples/sample_repo
repolens ask "How is the invoice total calculated?"
repolens review --diff examples/sample.diff
repolens serve
```

示例带引用回答：

```json
{
  "answer": "The most relevant context for 'How is the invoice total calculated?' is app.py:13-18#calculate_total score=0.564.",
  "citations": [
    {
      "path": "app.py",
      "start_line": 13,
      "end_line": 18,
      "symbol": "calculate_total"
    }
  ],
  "uncertain": false
}
```

示例 diff review：

```json
{
  "summary": "Found 3 actionable finding(s). Overall risk is high.",
  "risk_level": "high",
  "findings": [
    {
      "severity": "high",
      "category": "secret",
      "title": "Possible hard-coded secret",
      "path": "app.py"
    },
    {
      "severity": "high",
      "category": "security",
      "title": "Dynamic code execution introduced",
      "path": "app.py"
    }
  ]
}
```

Web 工作台支持索引、提问和 diff review，并提供中英切换：

![RepoLens AI workbench](assets/repolens-workbench.svg)

## Limitations

这是一个简历级 MVP，不是多租户 SaaS 平台。

- embedding 使用确定性本地 hash，方便复现，但不是生产级 embedding 模型。
- Python 符号提取使用标准库 `ast`，多语言解析后续应接入 tree-sitter。
- GitHub 支持目前通过公开 archive 下载实现，不是完整 GitHub App。
- PR reviewer 先覆盖高确定性的风险项，复杂语义审查可以在后续版本接入 LLM。
- UI 是本地静态工作台，不包含团队协作、权限和历史记录。

## What I Learned

这个项目最大的收获是：有用的 AI Agent 大部分是软件工程。LLM 只是其中一个组件，真正决定可用性的，是上下文构建、检索质量、引用、schema、安全边界、测试和可观测性。

我也学到，适合求职展示的 AI 项目必须同时满足两类读者：

- HR 能在一分钟内看懂项目解决什么问题。
- 技术面试官能继续追问架构、实现细节、测试覆盖和 tradeoff。

RepoLens AI 就是按这两个目标来设计的。

## GitHub Link

https://github.com/ZiruiWang2021/repo-lens-ai
