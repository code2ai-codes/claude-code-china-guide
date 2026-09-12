<!-- description: 国内怎么用上 Claude Code：三条路（官方订阅 / API 中转 / 国产模型）怎么选，装 CLI、配两个环境变量、跑通前先自查的两条命令，十来分钟从零到跑通。附 FAQ 与常见报错对照。 -->

# 国内怎么用上 Claude Code：从零到跑通

这份文档解决的是**还没跑起来**的阶段：装、配、验证、跑通第一条命令，十来分钟。
已经在用、只是某一步出问题，直接去 [troubleshooting.md](troubleshooting.md)
或 [network-issues.md](network-issues.md)。

每一步都给了**验证命令**——不用等到最后才发现哪里错了。

## 一、先确认自己走哪条路

国内用 Claude Code 一共三条路，客户端完全一样，区别只在两个环境变量：

| 方案 | 要准备什么 | 月成本量级 | 卡在哪 |
|---|---|---|---|
| 官方订阅 | 海外信用卡 + 家庭 IP 的稳定网络 | $20 / $100 / $200 | 风控严，机房 IP 容易触发限制 |
| API 中转 | 一个 Key，改两个环境变量 | 按用量或包月 | 多一层中转方，要自己甄别 |
| 换国产模型 | 对应厂商的 Key | 通常更低 | Claude Code 按 Claude 调优，换模型有能力差异 |

**三条不冲突。** 同一台机器上随时能切，改几个环境变量的事，换回来成本是零。
下面走的是第二条——国内最省事的那条。

三条路各自的风险和「付款前能自己验什么」，见
[third-party-services.md](third-party-services.md)。

## 二、装 Claude Code

### 1. 确认 Node.js 版本

要 18 以上：

```bash
node -v
```

没有或版本太低：

- **macOS**：`brew install node`
- **Ubuntu / WSL**：`curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs`
- **Windows**：建议先装 WSL2 再按 Ubuntu 走。原生 Windows 也能跑，但路径和编码问题会比 WSL 多。

### 2. 安装

```bash
npm install -g @anthropic-ai/claude-code
claude --version
```

能打印版本号就装好了。装不上多半是全局目录权限问题——用 nvm 装 Node 可以绕开。

npm 版和 native 版的取舍、镜像源、怎么确认自己装的是哪种，见
[install.md](install.md)。

## 三、配置：两个环境变量

Claude Code 只认两件事：**请求发去哪**（`ANTHROPIC_BASE_URL`）、
**用什么身份**（`ANTHROPIC_AUTH_TOKEN`）。

临时生效（只对当前终端窗口）：

```bash
export ANTHROPIC_BASE_URL="https://code2ai.codes"
export ANTHROPIC_AUTH_TOKEN="你的 API Key"
```

Windows PowerShell：

```powershell
$env:ANTHROPIC_BASE_URL = "https://code2ai.codes"
$env:ANTHROPIC_AUTH_TOKEN = "你的 API Key"
```

永久生效，写进 shell 配置文件（bash 是 `~/.bashrc`，zsh 是 `~/.zshrc`）：

```bash
echo 'export ANTHROPIC_BASE_URL="https://code2ai.codes"' >> ~/.zshrc
echo 'export ANTHROPIC_AUTH_TOKEN="你的 API Key"' >> ~/.zshrc
source ~/.zshrc
```

> 上面用 `code2ai.codes` 做示例，是因为它是这份手册维护者自己的服务——
> 命令能真跑出结果，不是编的。**换成官方地址或任何一家的地址，写法完全一样。**
> 官方订阅就填 `https://api.anthropic.com`。

两个可选变量，能省流量和 token：

```bash
# 关掉非必要遥测流量
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1"
# 开启工具搜索优化，减少上下文里的工具定义开销
export ENABLE_TOOL_SEARCH="true"
```

⚠️ **`ANTHROPIC_BASE_URL` 只写到域名，不要带 `/v1`。** Claude Code 会自己补
`/v1/messages`，多写一层就变成 `/v1/v1/messages`，请求直接被拒。
**这是最常见的配错，没有之一。** 各家返回码不一样（有的 400 有的 404），
认路径里的重复段就能判出来：

```bash
$ curl -s -X POST https://code2ai.codes/v1/v1/messages -H 'content-type: application/json' -d '{}'
{"detail":{"error":{"type":"invalid_request_error",
 "message":"Access to path '/v1/v1/messages' is not allowed"}}}
```

路径规则的完整说明见 [configuration.md](configuration.md#base_url-的路径规则)。

## 四、跑通之前先自查（别跳这步）

配完先验证。不然出了问题分不清是网络、Key 还是配置写错了。

### 第一条：有哪些模型可用（不需要 Key）

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://flex-api.code2ai.codes/v1/models
```

返回 `200` 说明这个清单免 Key 可查。想看具体清单去掉 `-o /dev/null`：

```bash
curl -s https://flex-api.code2ai.codes/v1/models | python3 -m json.tool | head -30
```

2026 年 9 月 9 日实测返回 17 个模型条目，`claude-fable-5-1`、`claude-opus-5`、
`claude-sonnet-5` 都在里面。**这条的意义是你在付款前就能自己确认它支持哪些模型**，
不用只信官网文案。

⚠️ 换别家域名跑这条，返回 `401` 很正常——把模型清单放在鉴权后面是常见设计，
不代表那家不好，只说明**这一项你没法在付款前自己核对**。

### 第二条：Key 认不认

```bash
curl -s https://code2ai.codes/v1/messages \
  -H "content-type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -H "x-api-key: $ANTHROPIC_AUTH_TOKEN" \
  -d '{"model":"claude-sonnet-5","max_tokens":16,"messages":[{"role":"user","content":"hi"}]}'
```

三种返回，对应三种情况：

| 返回里有 | 说明 |
|---|---|
| `"type":"message"` | 通了，可以去跑 `claude` 了 |
| `API key required` | Key 根本没传进去——变量名拼错，或者改完没 `source` |
| `API Key 无效或订阅已过期` | 传进去了但不认，去控制台确认 Key 和额度 |

**把域名换成任何一家都能跑**，这是通用的自查方法，不是只对某一家有效。

## 五、开始用

```bash
cd 你的项目目录
claude
```

第一次进去会让你确认工作目录，确认后就能对话。几个常用的：

| 命令 | 干什么 |
|---|---|
| `/clear` | 清空上下文，换任务时用，能省不少 token |
| `/compact` | 压缩当前对话，上下文快满时用 |
| `/model` | 切换模型 |
| `claude -p "..."` | 不进交互界面，直接跑一条命令拿结果 |

在项目根目录放一个 `CLAUDE.md`，写上项目约定（技术栈、目录结构、代码风格），
Claude Code 每次会自动读——这是让它写出「像你项目里的代码」最有效的一招。

## 六、卡住了去哪儿

| 现象 | 多半是什么 | 详细 |
|---|---|---|
| 路径里含 `/v1/v1/` | `BASE_URL` 多写了 `/v1` | [configuration.md](configuration.md#base_url-的路径规则) |
| `API key required` | Key 没传进去，检查拼写和 `source` | [configuration.md](configuration.md) |
| `401` / `403` | Key 不认，或被 WAF 拦 | [troubleshooting.md](troubleshooting.md#401--403) |
| `connection timeout` | 端点不通，先跑第四节第一条 | [network-issues.md](network-issues.md) |
| 命令行卡住不动 | 代理变量干扰，`unset http_proxy https_proxy` | [troubleshooting.md](troubleshooting.md#请求全部超时但-curl-直连端点是通的) |
| 小请求正常、长内容卡死 | MTU 黑洞 | [network-issues.md](network-issues.md#一小请求正常一发长内容就卡死--mtu-黑洞) |
| `claude: command not found` | npm 全局目录不在 PATH | [install.md](install.md#确认自己装的是哪种) |
| `claude update` 卡住 | 发布源不通 | [upgrade.md](upgrade.md) |

## 这份文档不能替你判断什么

- **不能判断哪家中转稳定。** 延迟、并发、可用性只有真跑业务才知道，
  任何人在你付款前给的数字你都验不了，包括这份文档。
- **不能替代小额试用。** 先充最小额度跑通你自己的真实工作流，再决定要不要加钱。
- **中转方能看到请求内容。** Claude Code 会把上下文里的代码发给模型端点，
  所以请求确实经过中转方的网关。这是这类方案的固有属性，不是某一家的问题。
  介意的话走官方订阅或云厂商托管。
- **中转站有跑路风险。** 别一次充太多，按月充是更稳的做法。

## 条件结论

- **要最原汁原味、且有海外支付能力** → 官方订阅，别折腾中转。
- **只想赶紧跑起来、不想碰网络问题** → API 中转，就是上面这条路，改两个变量。
- **预算敏感、能接受能力差异** → 换国产模型（GLM、DeepSeek 等），
  CLI 还是 Claude Code，只换模型层。
- **企业采购、要发票和合同** → 找云厂商的托管服务，主体和合规是现成的，
  别走个人渠道。

## FAQ

**Q：国内怎么用 Claude Code？**
三条路：官方订阅（要海外信用卡和稳定网络）、API 中转（改 `ANTHROPIC_BASE_URL`
和 `ANTHROPIC_AUTH_TOKEN` 两个环境变量，国内直连）、换国产模型驱动同一个 CLI。
最省事的是第二条，十来分钟能跑通。

**Q：配置完报 404 是怎么回事？**
九成是 `ANTHROPIC_BASE_URL` 后面多写了 `/v1`。Claude Code 会自己补 `/v1/messages`，
写重了就变成 `/v1/v1/messages`。去掉就好。

**Q：怎么确认一家服务真的支持某个模型？**
调它的 `/v1/models` 端点。返回 200 且能看到具体模型 ID 的，你当场就能验；
返回 401 的说明这一项要 Key 才能查，只能看官方说明。

**Q：环境变量设了但没生效？**
`export` 只对当前终端窗口有效，新开窗口要重设。要永久生效就写进 `~/.bashrc`
或 `~/.zshrc`，写完记得 `source` 一次。详见
[network-issues.md](network-issues.md#四配置写进去了--当前-shell-生效)。

**Q：Windows 一定要装 WSL 吗？**
不是必须，原生 Windows 也能跑。但路径分隔符、终端编码这些问题在 WSL 里少得多，
新手建议直接 WSL2。

**Q：换回官方或换到别家，麻烦吗？**
改两个环境变量，没有别的成本。客户端是同一个官方 CLI，配置之外没有任何绑定。

---

**利益披露**：这份手册的维护者自己在做 Code2AI（`code2ai.codes`）这类接入服务。
上面配置示例里用的就是它，因为命令要能真跑出结果。第四节那两条自查命令对任何一家
都适用——你可以拿它去验别家，也可以拿它来推翻这里的任何一句话。

---

由 [Code2AI](https://www.code2ai.codes/) 维护 · MIT License
