---
name: gpt-image-2
description: Use when the user wants Codex to create, generate, draw, make, render, remix, or edit an image with `gpt-image-2`, including natural requests such as “帮我画一张图”, “生成配图”, “做一张海报草图”, “改这张图片”, “换背景”, “扩图”, or “按这张图继续修改”. Prefer this skill when a real image file should be produced through the `https://sensoft.top` OpenAI-compatible endpoint instead of only returning sample code.
---

# GPT Image 2

Use this skill when the user wants image generation or image editing with `gpt-image-2`.

Prefer running the bundled Python script so Codex produces a real image file instead of only replying with example code.

## Runtime setup

- Skill directory: resolve paths relative to this `SKILL.md`.
- Configure `.env` in the skill directory before the first run. Copy `.env.example` to `.env`.
- Default base URL is `https://sensoft.top`.
- Default model is `gpt-image-2`.
- Install dependencies with `uv sync` inside the skill directory.

## Expected inputs

For generation:

- `prompt` - required
- `size` - optional, default `1024x1024`
- `quality` - optional, default `medium`
- `output_format` - optional, default `png`

For editing:

- `image` - required input image path
- `prompt` - required
- `mask` - optional mask image path
- `size` - optional, default `auto`
- `quality` - optional, default `medium`
- `output_format` - optional, default `png`

If the user asks to edit an image but does not give an input image path, stop and ask for that path instead of guessing.

## Preferred tooling

- Generate:
  `uv run --project "<skill-dir>" python "<skill-dir>/scripts/gpt_image_2.py" generate --prompt "<prompt>" --paths-only`
- Edit:
  `uv run --project "<skill-dir>" python "<skill-dir>/scripts/gpt_image_2.py" edit --image "<input.png>" --prompt "<prompt>" --paths-only`

Default output goes into the current working directory, using a readable filename derived from the prompt plus a timestamp. If the user wants a specific location or filename, pass `--output-dir` or `--output`.

## Workflow

1. Read the user request and decide whether this is a `generate` or `edit` run.
2. Confirm `.env` exists if the script has not been configured yet.
3. Run the bundled script with `--paths-only` so the saved file path is easy to capture.
4. If the request generated multiple images, return the saved paths and display the most relevant one.
5. If the request fails, surface the exact error briefly and mention whether it looks like provider compatibility, auth, or Cloudflare blocking.

## Safety rules

- Never store the user's API key in `SKILL.md`, chat, or checked-in source files.
- Keep `https://sensoft.top` as the default endpoint unless the user explicitly asks to override it.
- Treat `edit` as destructive to input intent: preserve the original input file and write output to a new path.
- If the provider returns a block page or Cloudflare response, report the headers and body summary instead of pretending the model failed normally.
