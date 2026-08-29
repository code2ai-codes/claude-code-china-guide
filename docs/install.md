# 安装：两种方式，选错了后面很痛苦

> Claude Code 有两种安装形态，区别不只是命令不同——**后续的升级方式完全不一样**。
> 这份文档讲怎么选、怎么装、怎么确认自己装的是哪种。
>
> 升级问题见 [`upgrade.md`](upgrade.md)，端点配置见 [`configuration.md`](configuration.md)。

## npm 安装

```bash
npm install -g @anthropic-ai/claude-code
```

官方源响应慢时换国内镜像：

```bash
npm install -g @anthropic-ai/claude-code --registry=https://registry.npmmirror.com
```

## native 安装（推荐）

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

装完后的结构：

```text
~/.local/bin/claude                     # 软链
~/.local/share/claude/versions/<版本>    # 实际二进制
```

### 为什么推荐 native

**一是不依赖 Node 环境。** npm 版需要本机有可用的 Node，版本过低或全局目录权限不对都会
出问题，而这类问题的报错信息往往指向别处，很难一眼看出根因。

**二是多版本共存。** native 版每个版本单独占一个目录，切换只是改一个软链，
升级失败可以立刻切回去——这一点在自动升级不稳定时很重要。

**三是启动更快**，省掉了 Node 的启动开销。

代价是它的自动升级依赖官方发布源，响应不稳定时会卡住。
[`upgrade.md`](upgrade.md) 给了用 npm 镜像源手工升级的方法，补上这个短板。

## 确认自己装的是哪种

```bash
which claude
ls -la $(which claude)
```

| 输出指向 | 安装方式 |
|---|---|
| `~/.local/share/claude/versions/...` | native |
| `node_modules/...` | npm |

⚠️ **两种并存时 PATH 顺序决定实际调用哪个**，很容易混淆——建议只留一个。
要从 npm 版换到 native 版：

```bash
npm uninstall -g @anthropic-ai/claude-code
curl -fsSL https://claude.ai/install.sh | bash
which claude          # 确认软链指向对了
```

## 验证安装

```bash
claude --version
```

能输出版本号（例如 `2.1.238`）就说明二进制本身没问题，
**后面的问题都在网络或配置层面**，不用再怀疑安装。

如果 `claude --version` 正常但一启动就报错，按这个顺序查：

1. `env | grep -i anthropic` —— 环境变量对不对（见 [`configuration.md`](configuration.md)）
2. 用 curl 直接打端点 —— 把客户端因素排除掉
3. `env | grep -i proxy` —— 有没有残留的代理变量（见 [`troubleshooting.md`](troubleshooting.md)）

这三步能覆盖绝大多数情况。

---

由 [Code2AI](https://www.code2ai.codes/) 维护 · MIT License
