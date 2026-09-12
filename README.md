<!-- description: 国内用 Claude Code 的完整手册：安装、ANTHROPIC_BASE_URL 端点配置、报错排查、网络问题与升级。每一步都给可直接复制的诊断命令和判断依据，不靠猜。开源 MIT。 -->

# 国内怎么用上 Claude Code：安装、端点配置与排错手册

**`claude-code-china-guide`——Claude Code 在国内环境下的安装、配置与排错手册。** 每个问题都给了可直接复制的诊断命令，
判断依据写明，不靠猜。

Claude Code 出问题的地方几乎都能归到三件事：**装不上、装上了请求失败、用得好好的升不了级**。
这三件事看着像同一个问题，其实依赖三个**互相独立**的服务：

| 环节 | 依赖的服务 | 出问题的表现 |
|---|---|---|
| 安装 | npm registry | 装不上、卡在下载 |
| 请求 | API 端点 | 401 / 403 / 404 / 全部超时 |
| 升级 | 官方发布源 | `claude update` 卡住不动 |

彼此不影响，所以经常出现「装好了但请求失败」「用得好好的但升级卡住」这类看似矛盾的情况。
**先分清是哪一层，再往下查**——这一步能省掉大量无效尝试。

> **English TL;DR** — A field manual for running Claude Code from mainland China:
> installation (npm vs native), pointing `ANTHROPIC_BASE_URL` at a custom endpoint,
> and diagnosing the errors you actually hit. Claude Code depends on three
> *independent* services — the npm registry (install), your API endpoint (requests),
> and the official release source (upgrade) — so failures in one look nothing like
> failures in another. Every section gives copy-pasteable diagnostic commands.
> See [English](#english) below.

## 还没跑起来？

从零开始装、配、跑通第一条命令，看 [**`docs/getting-started.md`**](docs/getting-started.md)——三条路怎么选、两个环境变量怎么配、跑之前怎么自查，十来分钟。

下面这份是给**已经在用、某一步出了问题**的人看的。

## 先花 10 秒定位

动手前先跑这两条：

```bash
# 1. 安装源响应情况
curl -sI -m 10 https://registry.npmjs.org/@anthropic-ai/claude-code | head -1

# 2. API 端点响应情况
curl -sI -m 10 https://api.anthropic.com/v1/messages | head -1
```

结果直接决定你该看哪份文档：

| 现象 | 卡在哪一层 | 看哪里 |
|---|---|---|
| 第 1 条超时 | 安装源 | [`docs/install.md`](docs/install.md) |
| 第 1 条正常、第 2 条超时 | 端点配置 | [`docs/configuration.md`](docs/configuration.md) |
| 两条都正常但 `claude` 报错 | 安装方式或路径 | [`docs/troubleshooting.md`](docs/troubleshooting.md) |
| `claude update` 卡住 | 发布源 | [`docs/upgrade.md`](docs/upgrade.md) |
| 还没选好接入方式 | —— | [`docs/third-party-services.md`](docs/third-party-services.md) |
| 还没装过，从头开始 | —— | [`docs/getting-started.md`](docs/getting-started.md) |

## 按报错现象直接跳转

| 你遇到的现象 | 去哪儿 |
|---|---|
| `Is a directory` | [升级 · 软链指向](docs/upgrade.md#软链必须指到二进制文件本身) |
| 请求全部超时，但 curl 直连端点是通的 | [排错 · 残留代理变量](docs/troubleshooting.md#请求全部超时但-curl-直连端点是通的) |
| **小请求正常，一发长内容就卡死** | [网络 · MTU 黑洞](docs/network-issues.md#一小请求正常一发长内容就卡死--mtu-黑洞) |
| 时通时不通，或者慢得离谱 | [网络 · IPv6 路由](docs/network-issues.md#二ipv6-线路不通但系统优先走-ipv6) |
| `401` / `403` | [排错 · 认证失败](docs/troubleshooting.md#401--403) |
| `404`，但配置看着都对 | [配置 · base_url 路径规则](docs/configuration.md#base_url-的路径规则) |
| 改了配置文件还是连旧地址 | [网络 · 配置生效优先级](docs/network-issues.md#四配置写进去了--当前-shell-生效) |
| `temperature is deprecated for this model` | [排错 · 参数弃用](docs/troubleshooting.md#temperature-is-deprecated-for-this-model) |
| `claude update` 卡住不动最后超时 | [升级 · 从镜像源取同一份二进制](docs/upgrade.md) |
| 不知道自己装的是 npm 版还是 native 版 | [安装 · 确认安装方式](docs/install.md#确认自己装的是哪种) |

## 文档

- [`docs/getting-started.md`](docs/getting-started.md)——**从零到跑通**：三条路的取舍、
  两个环境变量、跑通前的两条自查命令、常用命令，以及卡住了该去哪份文档
- [`docs/install.md`](docs/install.md)——两种安装方式的取舍（npm / native）、镜像源、
  验证安装是否成功
- [`docs/configuration.md`](docs/configuration.md)——用环境变量指定 API 端点，
  临时生效与持久化的区别，以及 `base_url` 的路径规则（`404` 的头号原因）
- [`docs/troubleshooting.md`](docs/troubleshooting.md)——实际会撞上的报错：
  认证失败、路径不对、请求全超时、WSL 的网络栈问题、参数弃用
- [`docs/network-issues.md`](docs/network-issues.md)——最难查的那一类：
  **MTU 黑洞**（小请求正常、长内容卡死）、IPv6 路由不通、代理残留、
  「配置写进去了但当前 shell 不生效」
- [`docs/upgrade.md`](docs/upgrade.md)——自动升级卡住时从镜像源取同一份二进制，
  含一个会让人卡很久的目录布局坑

## 命令速查

```bash
claude --version                         # 查版本
claude                                   # 在当前目录启动
claude --help                            # 全部参数
which claude && ls -la $(which claude)   # 确认安装方式与软链指向
env | grep -i proxy                      # 排查残留的网络环境变量
env | grep -i anthropic                  # 确认端点环境变量
ls ~/.local/share/claude/versions/       # 查看已安装的版本
```

## 把这些检查自动化

上面这些诊断都可以手工一条条跑——**这份手册的目的就是让你不依赖任何工具也能查清楚**，
所有命令在官方端点和任何第三方网关上都一样用。

如果想省事，Code2AI 有一个免费的终端助手 `c2a`，其中 `c2a doctor` 把十几项检查
串成一条命令：CLI 在不在 PATH、配置有没有真写进去、环境变量在当前 shell 生不生效、
密钥有效性与限额状态、IPv4/IPv6 可达性、MTU 黑洞、代理干扰，
最后发一个真实请求做端到端验证。每个错误都带对应的修复命令。

```bash
curl -fsSL https://console.code2ai.codes/install.sh | bash
c2a doctor
```

⚠️ 说清楚：**`c2a` 本身免费，但它「取密钥、写配置」那部分需要 Code2AI 订阅才有意义。**
纯排错的话，这份手册里的命令一个订阅都不需要。

## 关于 `ANTHROPIC_BASE_URL` 填什么

这取决于你的接入方式：用官方订阅就填官方地址；如果因为支付方式等原因走第三方网关，
就填对方给的地址。**客户端完全一样**，都是官方原生的 Claude Code CLI，
区别只在这两个环境变量——这也意味着换回来的成本是零，改两行配置的事。

**这份手册的排错内容不依赖任何特定的接入服务**，只讲怎么配、报错怎么查。

---

## English

### What this is

A field manual for running Claude Code from mainland China. Every problem comes
with copy-pasteable diagnostic commands and an explicit decision rule.

Claude Code failures almost always fall into three buckets, and they depend on
three **independent** services:

| Stage | Depends on | Typical symptom |
|---|---|---|
| Install | npm registry | Hangs during download |
| Requests | your API endpoint | 401 / 403 / 404 / everything times out |
| Upgrade | official release source | `claude update` hangs, then times out |

Because they are independent, "installed fine but requests fail" and "works fine
but won't upgrade" are both normal and unrelated. **Identify the layer first.**

### 10-second triage

```bash
curl -sI -m 10 https://registry.npmjs.org/@anthropic-ai/claude-code | head -1
curl -sI -m 10 https://api.anthropic.com/v1/messages | head -1
```

| Result | Layer | Read |
|---|---|---|
| #1 times out | install source | [`docs/install.md`](docs/install.md) |
| #1 ok, #2 times out | endpoint config | [`docs/configuration.md`](docs/configuration.md) |
| both ok, `claude` still errors | install path | [`docs/troubleshooting.md`](docs/troubleshooting.md) |
| `claude update` hangs | release source | [`docs/upgrade.md`](docs/upgrade.md) |
| nothing installed yet | — | [`docs/getting-started.md`](docs/getting-started.md) |
| small requests fine, long ones hang | **path MTU / IPv6** | [`docs/network-issues.md`](docs/network-issues.md) |

The last row is the one people rarely guess: if an intermediate hop has a smaller
MTU and the ICMP needed for path-MTU discovery is being dropped, small packets get
through and large ones vanish silently — so it looks like the server hanging, not
a network error.

### Note on `ANTHROPIC_BASE_URL`

Point it at the official API, or at whatever gateway you use. The client is
identical either way — it is the stock Claude Code CLI, and the only difference
is two environment variables, so switching back costs nothing.

**This repository does not recommend any particular access service.** It only
covers configuration and diagnostics.

---

由 [Code2AI](https://www.code2ai.codes/) 维护 · MIT License
