# 配置：用环境变量指定 API 端点

> Claude Code 通过两个官方环境变量指定请求地址与身份，这是产品内置的配置能力。
> 这份文档讲临时生效与持久化的区别、怎么单独验证端点，
> 以及 `base_url` 的路径规则——**那是 404 的头号原因**。
>
> 报错诊断见 [`troubleshooting.md`](troubleshooting.md)。

```bash
export ANTHROPIC_BASE_URL=https://你的网关地址
export ANTHROPIC_AUTH_TOKEN=你的密钥
```

## 临时生效（当前终端）

```bash
export ANTHROPIC_BASE_URL=https://your-gateway.example.com
export ANTHROPIC_AUTH_TOKEN=sk-xxxxxxxx
claude
```

关掉窗口就没了，适合临时测试不同的端点地址。

### ⚠️ 优先级有个坑

**命令行里 `export` 的值会覆盖 shell 配置文件里的值。**

所以如果你改了 `.bashrc` 但不生效，先检查当前终端是不是早就 export 过一个旧值——
这时候 `source ~/.bashrc` 也救不回来，得**开个新终端**，或者手动重新 export 一次。

这个坑的表现是「我明明改了配置文件，怎么还是连到旧地址」，很容易怀疑到别处去。

## 持久化（推荐）

```bash
# bash
echo 'export ANTHROPIC_BASE_URL=https://your-gateway.example.com' >> ~/.bashrc
echo 'export ANTHROPIC_AUTH_TOKEN=sk-xxxxxxxx' >> ~/.bashrc
source ~/.bashrc

# zsh
echo 'export ANTHROPIC_BASE_URL=https://your-gateway.example.com' >> ~/.zshrc
echo 'export ANTHROPIC_AUTH_TOKEN=sk-xxxxxxxx' >> ~/.zshrc
source ~/.zshrc
```

## 验证端点是否真的通了

**别直接开 `claude` 试**，先用 curl 单独验证——报错信息清楚得多，
而且能立刻区分「端点问题」和「客户端问题」：

```bash
curl -sS https://your-gateway.example.com/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: sk-xxxxxxxx" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-sonnet-5","max_tokens":32,
       "messages":[{"role":"user","content":"只回复两个字：通了"}]}'
```

返回 JSON 且 `content` 里有文本，这条链路就是通的。

| curl 结果 | `claude` 结果 | 结论 |
|---|---|---|
| 通 | 不通 | **客户端配置问题**——查环境变量、查代理变量 |
| 不通 | 不通 | **端点或密钥问题**——按返回的错误结构继续查 |

这一步能把排查范围直接砍掉一半。

## `base_url` 的路径规则

**这是最容易出错的一处。** 多数客户端会自己补 `/v1/messages`，所以：

```bash
# ❌ 写重了，实际请求变成 /v1/messages/v1/messages，返回 404
export ANTHROPIC_BASE_URL="https://example.com/v1/messages"

# ✅ 写到域名（或 /v1）为止
export ANTHROPIC_BASE_URL="https://example.com"
```

这个 404 特别有迷惑性，**因为密钥和网络都是好的，看起来哪儿都对**。

判别方法是看**客户端最后拼出来的完整 URL**，而不是看你配了什么。
同类变体还有末尾多一个 `/`、把 `/v1` 单独带上，表现都一样。

## 环境变量速查

```bash
env | grep -i anthropic     # 确认端点变量
env | grep -i proxy         # 排查残留的代理变量（见 troubleshooting.md）
```

| 变量 | 作用 |
|---|---|
| `ANTHROPIC_BASE_URL` | 请求发往哪里。写到域名为止 |
| `ANTHROPIC_AUTH_TOKEN` | 身份凭证 |

⚠️ 密钥不要写进会被提交的文件。放 shell 配置文件或 `.env`（并确保 `.env` 已被 gitignore）。

---

由 [Code2AI](https://www.code2ai.codes/) 维护 · MIT License
