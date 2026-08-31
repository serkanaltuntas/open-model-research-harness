import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from harness.config import MlxModelConfig, load_mlx_model_config


class CompatibilityError(RuntimeError):
    """Raised when the pinned MLX model fails an A2 compatibility check."""


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError as error:
        raise CompatibilityError(f"Required package {name!r} is not installed.") from error


def _macos_version() -> str:
    result = subprocess.run(
        ["sw_vers", "-productVersion"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def verify_local_artifacts(snapshot: Path, config: MlxModelConfig) -> None:
    for identity in (config.model_artifact, config.tokenizer_artifact):
        artifact_path = snapshot / identity.path
        if not artifact_path.is_file():
            raise CompatibilityError(f"Downloaded artifact is missing: {identity.path}")
        actual_size = artifact_path.stat().st_size
        if actual_size != identity.size_bytes:
            raise CompatibilityError(
                f"Artifact {identity.path} has size {actual_size}; "
                f"expected {identity.size_bytes}."
            )


def verify_chat_template(
    *,
    tokenizer: Any,
    snapshot: Path,
    config: MlxModelConfig,
) -> dict[str, Any]:
    template_path = snapshot / config.chat_template_file
    if not template_path.is_file():
        raise CompatibilityError(
            f"Tokenizer metadata is missing: {config.chat_template_file}"
        )
    template_data = json.loads(template_path.read_text(encoding="utf-8"))
    source_template = template_data.get("chat_template")
    loaded_template = getattr(tokenizer, "chat_template", None)
    if not isinstance(source_template, str) or not source_template:
        raise CompatibilityError("Pinned tokenizer metadata has no chat template.")
    if loaded_template != source_template:
        raise CompatibilityError(
            "Loaded chat template does not match the pinned tokenizer metadata."
        )

    user_content = "A2 compatibility check."
    rendered = tokenizer.apply_chat_template(
        [{"role": "user", "content": user_content}],
        tokenize=False,
        add_generation_prompt=True,
    )
    expected_user = f"<|im_start|>user\n{user_content}<|im_end|>\n"
    if expected_user not in rendered:
        raise CompatibilityError("Rendered chat does not preserve the Qwen user role.")
    if not rendered.endswith("<|im_start|>assistant\n"):
        raise CompatibilityError("Rendered chat has no Qwen assistant generation prompt.")

    return {
        "source": config.chat_template_file,
        "sha256": _sha256_text(source_template),
        "rendered_sha256": _sha256_text(rendered),
        "user_role_verified": True,
        "generation_prompt_verified": True,
        "custom_template_supplied": False,
        "rendered_preview": rendered,
    }


def verify_lora_entrypoint() -> dict[str, Any]:
    try:
        from mlx_lm import lora
    except ImportError as error:
        raise CompatibilityError(f"MLX-LM LoRA module is unavailable: {error}") from error

    required_api = ("build_parser", "run", "train_model")
    missing = [name for name in required_api if not callable(getattr(lora, name, None))]
    if missing:
        raise CompatibilityError(
            f"MLX-LM LoRA API is missing: {', '.join(sorted(missing))}."
        )

    entry_points = {
        entry_point.name: entry_point.value
        for entry_point in importlib.metadata.entry_points(group="console_scripts")
    }
    command_target = entry_points.get("mlx_lm.lora")
    if command_target != "mlx_lm.lora:main":
        raise CompatibilityError("Console entry point mlx_lm.lora is unavailable.")

    return {
        "module": "mlx_lm.lora",
        "console_command": "mlx_lm.lora",
        "console_target": command_target,
        "required_api": list(required_api),
        "available": True,
    }


def run_compatibility_check(
    config: MlxModelConfig,
    *,
    snapshot_download_fn: Callable[..., str] | None = None,
    load_fn: Callable[..., Any] | None = None,
    generate_fn: Callable[..., str] | None = None,
    sampler_fn: Callable[..., Any] | None = None,
    lora_check_fn: Callable[[], dict[str, Any]] = verify_lora_entrypoint,
) -> dict[str, Any]:
    if snapshot_download_fn is None:
        from huggingface_hub import snapshot_download

        snapshot_download_fn = snapshot_download
    if load_fn is None or generate_fn is None or sampler_fn is None:
        from mlx_lm import generate, load
        from mlx_lm.sample_utils import make_sampler

        load_fn = load_fn or load
        generate_fn = generate_fn or generate
        sampler_fn = sampler_fn or make_sampler

    snapshot = Path(
        snapshot_download_fn(
            repo_id=config.repository,
            revision=config.revision,
        )
    )
    if snapshot.name != config.revision:
        raise CompatibilityError(
            f"Resolved snapshot {snapshot.name!r} does not match pinned revision."
        )
    verify_local_artifacts(snapshot, config)

    model, tokenizer, model_config = load_fn(
        str(snapshot),
        lazy=False,
        return_config=True,
    )
    chat = verify_chat_template(tokenizer=tokenizer, snapshot=snapshot, config=config)
    sampler = sampler_fn(temp=0.0)
    generated = generate_fn(
        model,
        tokenizer,
        prompt=chat["rendered_preview"],
        max_tokens=8,
        sampler=sampler,
        verbose=False,
    )
    if not isinstance(generated, str) or not generated:
        raise CompatibilityError("Short deterministic inference returned no text.")

    return {
        "status": "GO",
        "environment": {
            "python": platform.python_version(),
            "mlx": _package_version("mlx"),
            "mlx_lm": _package_version("mlx-lm"),
            "macos": _macos_version(),
            "architecture": platform.machine(),
        },
        "model": {
            "repository": config.repository,
            "revision": config.revision,
            "snapshot_identity": snapshot.name,
            "upstream_model": config.upstream_model,
            "license": config.license,
            "model_type": model_config.get("model_type"),
            "quantization": {
                "bits": config.quantization_bits,
                "group_size": config.quantization_group_size,
            },
            "model_artifact_sha256": config.model_artifact.sha256,
            "model_artifact_xet_hash": config.model_artifact.xet_hash,
            "model_class": type(model).__name__,
            "loaded": True,
        },
        "tokenizer": {
            "revision": config.tokenizer_revision,
            "artifact_sha256": config.tokenizer_artifact.sha256,
            "artifact_xet_hash": config.tokenizer_artifact.xet_hash,
            "class": type(tokenizer).__name__,
            **chat,
        },
        "inference": {
            "deterministic_temperature": 0.0,
            "maximum_tokens": 8,
            "non_empty": True,
            "character_count": len(generated),
        },
        "lora": lora_check_fn(),
        "known_caveats": list(config.known_caveats),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-config", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        config = load_mlx_model_config(args.model_config)
        result = run_compatibility_check(config)
    except Exception as error:
        print(f"NO-GO: {type(error).__name__}: {error}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
