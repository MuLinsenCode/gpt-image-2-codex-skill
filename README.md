# GPT Image 2 Codex Skill

这个 skill 让 Codex 可以通过一个 OpenAI 兼容接口，直接调用 `gpt-image-2` 来生成图片或编辑图片。

它支持：

- 生成新图片
- 编辑已有图片
- 通过本地 `.env` 文件配置 API Key
- 默认把图片保存到当前工作目录

## 安装前准备

安装前请先确认：

- 你正在使用支持 `~/.codex/skills` 目录的 Codex 环境
- 你的机器上已经安装了 `uv`
- 你有一个可用的接口地址和 API Key，并且这个 Key 可以调用 `gpt-image-2`

## 安装步骤

1. 把这个仓库克隆到本地 Codex 的 skill 目录中，并命名为 `gpt-image-2`。

示例：

```bash
mkdir -p ~/.codex/skills
git clone <your-repo-url> ~/.codex/skills/gpt-image-2
```

2. 安装这个 skill 依赖的 Python 包：

```bash
uv sync --project ~/.codex/skills/gpt-image-2
```

3. 创建本地配置文件：

```bash
cp ~/.codex/skills/gpt-image-2/.env.example ~/.codex/skills/gpt-image-2/.env
```

4. 编辑 `~/.codex/skills/gpt-image-2/.env`，填入你自己的 API Key：

```env
IMAGE_API_BASE_URL=https://your-openai-compatible-endpoint
IMAGE_API_KEY=your_api_key_here
IMAGE_MODEL=gpt-image-2
IMAGE_API_TIMEOUT=420
```

5. 如果 Codex 没有自动刷新 skill 列表，建议新开一个对话再试。

## 验证安装

先执行下面的命令，确认脚本能正常运行：

```bash
uv run --project ~/.codex/skills/gpt-image-2 \
  python ~/.codex/skills/gpt-image-2/scripts/gpt_image_2.py --help
```

### 测试生成图片

```bash
uv run --project ~/.codex/skills/gpt-image-2 \
  python ~/.codex/skills/gpt-image-2/scripts/gpt_image_2.py \
  generate --prompt "一只戴橙色围巾的猫，儿童绘本风格" --paths-only
```

### 测试编辑图片

```bash
uv run --project ~/.codex/skills/gpt-image-2 \
  python ~/.codex/skills/gpt-image-2/scripts/gpt_image_2.py \
  edit --image /path/to/input.png --prompt "把背景改成雪山黄昏" --paths-only
```

生成图片和编辑图片在默认情况下都会传 `size=auto`；只有当你明确传了 `--size` 时，才会优先使用你指定的尺寸。

## Codex 会在什么场景下触发这个 Skill

安装完成后，Codex 在遇到下面这类请求时，应该更容易命中这个 skill：

- “帮我画一张图”
- “生成一张海报草图”
- “帮我做一张配图”
- “改这张图片”
- “换掉这张图的背景”
- “基于这张图继续修改”

## 输出文件行为

- 默认情况下，图片会保存到当前工作目录
- 默认文件名会根据 prompt 生成一个较短的可读名称，并附带时间戳
- 你可以用 `--output-dir` 指定输出目录
- 你也可以用 `--output` 直接指定输出文件名

## 常见问题

### 1. 提示 `Missing IMAGE_API_KEY`

说明你的 `.env` 文件里没有填 `IMAGE_API_KEY`，或者填的是空值。

### 2. 提示 `Your request was blocked`

如果响应头里包含 `server: cloudflare` 或 `cf-ray`，通常说明请求被你配置的接口地址前面的 Cloudflare 或其他边缘防护拦截了。  
这种情况下一般需要去对应域名的 Cloudflare 后台放行图片接口路径。

### 3. Skill 没有在 Codex 里生效

请检查：

- 安装目录是不是 `~/.codex/skills/gpt-image-2`
- 这个目录下是否存在 `SKILL.md`
- 安装完成后是否重新开了一个新的 Codex 对话

## 目录说明

这个仓库里的关键文件如下：

- `SKILL.md`：Codex 的触发说明和使用规则
- `agents/openai.yaml`：Codex UI 展示信息
- `scripts/gpt_image_2.py`：真正执行生成图和编辑图的 Python 脚本
- `.env.example`：配置模板
- `pyproject.toml`：通过 `uv` 管理的 Python 依赖

## 欢迎一起共建

如果你在使用过程中发现了问题，或者你有更好的触发词设计、参数处理方式、输出命名策略、图片编辑能力补充，欢迎一起完善这个 skill。

无论是提 Issue、发 PR，还是补充文档和使用案例，都非常欢迎。希望这个 skill 能在大家的持续迭代下变得更稳定、更好用。
