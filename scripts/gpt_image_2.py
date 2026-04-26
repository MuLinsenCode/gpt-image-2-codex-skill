#!/usr/bin/env python3

import argparse
import base64
import json
import mimetypes
import re
import urllib.error
import urllib.request
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path

from openai import APIStatusError
from openai import OpenAI

DEFAULT_BASE_URL = "https://sensoft.top/v1"
DEFAULT_MODEL = "gpt-image-2"
DEFAULT_GENERATE_SIZE = "1024x1024"
DEFAULT_EDIT_SIZE = "auto"
DEFAULT_QUALITY = "medium"
DEFAULT_OUTPUT_FORMAT = "png"
DEFAULT_TIMEOUT = 420.0


def load_dotenv(dotenv_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not dotenv_path.is_file():
        return values

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value

    return values


def resolve_config(script_dir: Path) -> dict[str, str]:
    env = load_dotenv(script_dir.parent / ".env")
    return {
        "base_url": env.get("IMAGE_API_BASE_URL", DEFAULT_BASE_URL),
        "api_key": env.get("IMAGE_API_KEY", ""),
        "model": env.get("IMAGE_MODEL", DEFAULT_MODEL),
        "timeout": env.get("IMAGE_API_TIMEOUT", str(DEFAULT_TIMEOUT)),
    }


def build_client(base_url: str, api_key: str, timeout: float) -> OpenAI:
    if not api_key.strip():
        raise SystemExit(
            "Missing IMAGE_API_KEY. Create skill/.env from skill/.env.example first."
        )

    return OpenAI(api_key=api_key.strip(), base_url=base_url.strip(), timeout=timeout)


def extension_from_content_type(content_type: str) -> str:
    extension = mimetypes.guess_extension(content_type.split(";", 1)[0].strip()) or ".png"
    return ".jpg" if extension == ".jpe" else extension


def print_error_context(err: APIStatusError, base_url: str, model: str) -> None:
    response = err.response
    request = err.request

    print("Request failed.")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print(f"HTTP status: {response.status_code}")
    print(f"Request URL: {request.url}")
    print(f"Method: {request.method}")

    request_id = response.headers.get("x-request-id")
    if request_id:
        print(f"OpenAI request id: {request_id}")

    server = response.headers.get("server")
    if server:
        print(f"Server header: {server}")

    cf_ray = response.headers.get("cf-ray")
    if cf_ray:
        print(f"cf-ray: {cf_ray}")

    content_type = response.headers.get("content-type", "")
    print(f"Content-Type: {content_type}")
    print("Response body:")

    response_text = response.text
    if "application/json" in content_type:
        try:
            print(json.dumps(json.loads(response_text), indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print(response_text)
    else:
        print(response_text[:4000])


def fetch_url(url: str, timeout: float) -> tuple[bytes, str]:
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        content_type = response.headers.get("Content-Type", "image/png")
        return body, content_type


def default_output_dir(script_dir: Path) -> Path:
    del script_dir
    return Path.cwd()


def slugify_prompt(prompt: str, max_length: int = 10) -> str:
    text = prompt.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text).strip("-_")
    if not text:
        return "image"
    return text[:max_length].rstrip("-_") or "image"


def resolve_target_path(
    output: str | None,
    output_dir: Path,
    index: int,
    total: int,
    default_suffix: str,
    base_name: str,
) -> Path:
    if output:
        path = Path(output)
        if total == 1:
            return path if path.suffix else path.with_suffix(default_suffix)

        stem = path.stem if path.suffix else path.name
        suffix = path.suffix or default_suffix
        return path.with_name(f"{stem}-{index + 1}{suffix}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if total == 1:
        return output_dir / f"{base_name}_{timestamp}{default_suffix}"
    return output_dir / f"{base_name}_{timestamp}_{index + 1}{default_suffix}"


def save_result_images(
    result,
    output: str | None,
    output_dir: Path,
    timeout: float,
    base_name: str,
) -> list[Path]:
    items = result.data or []
    if not items:
        raise SystemExit("The provider returned no image data.")

    saved_paths: list[Path] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for index, item in enumerate(items):
        target = resolve_target_path(
            output, output_dir, index, len(items), ".png", base_name
        )

        if getattr(item, "b64_json", None):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(base64.b64decode(item.b64_json))
            saved_paths.append(target.resolve())
            continue

        if getattr(item, "url", None):
            body, content_type = fetch_url(item.url, timeout)
            final_target = target if target.suffix else target.with_suffix(
                extension_from_content_type(content_type)
            )
            final_target.parent.mkdir(parents=True, exist_ok=True)
            final_target.write_bytes(body)
            saved_paths.append(final_target.resolve())
            continue

        raise SystemExit(f"Unsupported image item: {item}")

    return saved_paths


def run_generate(args: argparse.Namespace, script_dir: Path, config: dict[str, str]) -> list[Path]:
    timeout = float(args.timeout or config["timeout"])
    model = args.model or config["model"]
    base_url = args.base_url or config["base_url"]
    client = build_client(base_url, args.api_key or config["api_key"], timeout)

    request = {
        "model": model,
        "prompt": args.prompt,
        "size": args.size,
        "quality": args.quality,
        "output_format": args.output_format,
        "background": args.background,
        "n": args.n,
    }

    try:
        result = client.images.generate(**request)
    except APIStatusError as err:
        print_error_context(err, base_url, model)
        raise

    return save_result_images(
        result,
        args.output,
        Path(args.output_dir),
        timeout,
        slugify_prompt(args.prompt),
    )


def run_edit(args: argparse.Namespace, script_dir: Path, config: dict[str, str]) -> list[Path]:
    timeout = float(args.timeout or config["timeout"])
    model = args.model or config["model"]
    base_url = args.base_url or config["base_url"]
    client = build_client(base_url, args.api_key or config["api_key"], timeout)

    with ExitStack() as stack:
        images = [stack.enter_context(open(path, "rb")) for path in args.image]
        mask = stack.enter_context(open(args.mask, "rb")) if args.mask else None

        request = {
            "model": model,
            "image": images if len(images) > 1 else images[0],
            "prompt": args.prompt,
            "size": args.size,
            "quality": args.quality,
            "output_format": args.output_format,
            "background": args.background,
            "n": args.n,
        }
        if mask:
            request["mask"] = mask
        if args.input_fidelity:
            request["input_fidelity"] = args.input_fidelity

        try:
            result = client.images.edit(**request)
        except APIStatusError as err:
            print_error_context(err, base_url, model)
            raise

    return save_result_images(
        result,
        args.output,
        Path(args.output_dir),
        timeout,
        slugify_prompt(args.prompt),
    )


def build_parser(script_dir: Path, config: dict[str, str]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or edit images with gpt-image-2 using a skill-local .env config."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate a new image.")
    add_shared_arguments(generate, script_dir, config)
    generate.add_argument("--prompt", required=True, help="Prompt used to generate the image.")
    generate.add_argument("--size", default=DEFAULT_GENERATE_SIZE)
    generate.add_argument("--quality", default=DEFAULT_QUALITY)
    generate.add_argument(
        "--output-format",
        default=DEFAULT_OUTPUT_FORMAT,
        choices=("png", "jpeg", "webp"),
    )
    generate.add_argument(
        "--background",
        default="auto",
        choices=("auto", "opaque", "transparent"),
    )
    generate.add_argument("--n", type=int, default=1)

    edit = subparsers.add_parser("edit", help="Edit an existing image.")
    add_shared_arguments(edit, script_dir, config)
    edit.add_argument(
        "--image",
        action="append",
        required=True,
        help="Input image path. Repeat to provide multiple images.",
    )
    edit.add_argument("--prompt", required=True, help="Editing instructions for the model.")
    edit.add_argument("--mask", help="Optional mask image path.")
    edit.add_argument("--size", default=DEFAULT_EDIT_SIZE)
    edit.add_argument("--quality", default=DEFAULT_QUALITY)
    edit.add_argument(
        "--output-format",
        default=DEFAULT_OUTPUT_FORMAT,
        choices=("png", "jpeg", "webp"),
    )
    edit.add_argument(
        "--background",
        default="auto",
        choices=("auto", "opaque", "transparent"),
    )
    edit.add_argument(
        "--input-fidelity",
        choices=("low", "high"),
        help="Optional fidelity hint for image editing.",
    )
    edit.add_argument("--n", type=int, default=1)

    return parser


def add_shared_arguments(
    parser: argparse.ArgumentParser, script_dir: Path, config: dict[str, str]
) -> None:
    parser.add_argument(
        "--base-url",
        default=config["base_url"],
        help=f"Override the image API base URL. Defaults to {config['base_url']}.",
    )
    parser.add_argument(
        "--api-key",
        default=config["api_key"],
        help="Override IMAGE_API_KEY from .env.",
    )
    parser.add_argument(
        "--model",
        default=config["model"],
        help=f"Override the model name. Defaults to {config['model']}.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(config["timeout"]),
        help=f"Request timeout in seconds. Defaults to {config['timeout']}.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(default_output_dir(script_dir)),
        help="Directory used for default generated output paths. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--output",
        help="Explicit output path. For multi-image runs, numbered suffixes are added.",
    )
    parser.add_argument(
        "--paths-only",
        action="store_true",
        help="Print only saved file paths, one per line.",
    )


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    config = resolve_config(script_dir)
    parser = build_parser(script_dir, config)
    args = parser.parse_args()

    if args.command == "generate":
        saved_paths = run_generate(args, script_dir, config)
    else:
        saved_paths = run_edit(args, script_dir, config)

    if args.paths_only:
        for path in saved_paths:
            print(path)
        return

    for path in saved_paths:
        print(f"Saved image to {path}")


if __name__ == "__main__":
    main()
