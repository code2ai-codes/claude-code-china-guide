# 升级：自动升级卡住时怎么办

> `claude update` 走官方发布源，网络条件不佳时会长时间无响应最后超时。
> 这份文档给出从 npm 镜像源取**同一份二进制**手工替换的完整步骤，
> 以及一个会让人卡很久的目录布局坑。
>
> 只适用于 native 安装（`~/.local/share/claude/versions/`）。
> 不确定自己装的哪种见 [`install.md`](install.md#确认自己装的是哪种)。

## 现象

```bash
claude update
# 或
claude install
```

长时间无响应，最后超时。

## 解法：从 npm 镜像源取同一份二进制

关键点是——**npm 上的 `@anthropic-ai/claude-code-linux-x64` 包里就是同一个二进制文件**，
而 npmmirror 是国内常用镜像源，响应稳定。所以可以手工替换：

```bash
# 1. 查最新版本号
curl -s https://registry.npmmirror.com/@anthropic-ai/claude-code/latest \
  | grep -o '"version":"[^"]*"' | head -1

# 2. 换成上面查到的版本号，别照抄
V=2.1.238
cd "$(mktemp -d)"
curl -sSL -o p.tgz \
  "https://registry.npmmirror.com/@anthropic-ai/claude-code-linux-x64/-/claude-code-linux-x64-$V.tgz"
tar xzf p.tgz      # 二进制在 package/claude
```

**选包提示**：glibc 系统（Ubuntu、Debian、CentOS）用 `linux-x64`，
别选 `-musl`——那是 Alpine 用的。

## 安装到版本目录并切换软链

```bash
D=~/.local/share/claude/versions/$V
install -Dm755 package/claude "$D/claude"

# 先确认新版本能跑
"$D/claude" --version

# 确认输出正确后，再执行这一步
ln -sfn "$D/claude" ~/.local/bin/claude
```

**顺序很重要**：先验证新二进制能跑，再切软链。反过来做，新版本有问题时
你连一个可用的 `claude` 都没有了。

## 软链必须指到二进制文件本身

⚠️ 这一步错了，`claude` 会直接报 `Is a directory`。

**两种目录布局并存**，装之前必须先确认手上这个版本是哪种：

| 版本 | `versions/<版本>` 是什么 | 软链要指向 |
|---|---|---|
| 早期 | ELF 二进制文件本身 | `versions/<版本>` |
| 较新（实测 2.1.219 起） | **目录**，二进制在里面 | `versions/<版本>/claude` |

一条命令判断：

```bash
V=2.1.238
ls -la ~/.local/share/claude/versions/$V
# 输出是文件 → 早期布局；是目录且里面有 claude → 新布局
```

如果按早期布局的习惯把软链指向**目录**，会得到这个报错：

```text
/home/用户名/.local/bin/claude: Is a directory
```

**排查第一步永远是看软链指向哪儿**：

```bash
ls -la ~/.local/bin/claude
```

正确状态长这样（指向文件，不是目录）：

```text
lrwxrwxrwx ... /home/你的用户名/.local/bin/claude
              -> /home/你的用户名/.local/share/claude/versions/2.1.233/claude
```

回滚到老版本时同理——早期版本指到 `versions/<版本>`，新版本指到
`versions/<版本>/claude`，**两者不能混**。

## 升级失败不会失去可用版本

老版本仍留在 `versions/` 下，随时切回去：

```bash
ls ~/.local/share/claude/versions/     # 看有哪些版本
ln -sfn ~/.local/share/claude/versions/<老版本>/claude ~/.local/bin/claude
```

所以升级失败时**别急着重装**，先切回去恢复可用状态，再慢慢查。

另外，**改软链不影响已经在运行的会话**，需要重启 Claude Code 才生效。

---

由 [Code2AI](https://www.code2ai.codes/) 维护 · MIT License
