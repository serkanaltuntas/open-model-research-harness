"""Explicit download/local verification of tokenizer files, never model weights."""

import hashlib
import json
from pathlib import Path
from typing import Any

from harness.config import MlxModelConfig
from harness.training.data import TrainingDataError, sha256


def load_tokenizer(
    config: MlxModelConfig,
    identity_path: Path,
    *,
    snapshot: Path | None = None,
    download: bool = False,
    cache_dir: Path | None = None,
) -> tuple[Any, dict[str, Any]]:
    from transformers import AutoTokenizer

    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    if (
        identity.get("schema_version"),
        identity.get("repository"),
        identity.get("revision"),
    ) != (
        "a3-tokenizer-v1",
        config.repository,
        config.tokenizer_revision,
    ):
        raise TrainingDataError("tokenizer identity does not match pinned model config")
    if config.revision != config.tokenizer_revision:
        raise TrainingDataError("model and tokenizer revisions must match")
    files = identity.get("files")
    required = {
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "added_tokens.json",
        "config.json",
    }
    if not isinstance(files, dict) or set(files) != required:
        raise TrainingDataError(
            "identity must list the five tokenizer/config files only"
        )
    if files[config.tokenizer_artifact.path] != config.tokenizer_artifact.sha256:
        raise TrainingDataError("tokenizer artifact hash differs from A2 config")
    if download:
        if snapshot is not None:
            raise TrainingDataError(
                "choose local snapshot or explicit download, not both"
            )
        from huggingface_hub import snapshot_download

        snapshot = Path(
            snapshot_download(
                repo_id=config.repository,
                revision=config.tokenizer_revision,
                allow_patterns=sorted(files),
                cache_dir=cache_dir,
            )
        )
    if snapshot is None:
        raise TrainingDataError("provide --tokenizer-snapshot or --download-tokenizer")
    if snapshot.name != config.tokenizer_revision:
        raise TrainingDataError(
            "snapshot directory must be named by the pinned revision"
        )
    hashes = {}
    for name, expected in files.items():
        path = snapshot / name
        if not path.is_file() or sha256(path) != expected:
            raise TrainingDataError(f"pinned tokenizer file hash mismatch: {name}")
        hashes[name] = expected
    # Prevent alternate templates/configuration from overriding verified files.
    unexpected = {path.name for path in snapshot.iterdir()} - set(files)
    if unexpected:
        raise TrainingDataError(
            f"tokenizer-only snapshot has unexpected files: {sorted(unexpected)}"
        )
    source = json.loads(
        (snapshot / config.chat_template_file).read_text(encoding="utf-8")
    )
    template_hash = hashlib.sha256(source["chat_template"].encode()).hexdigest()
    if template_hash != identity["chat_template_sha256"]:
        raise TrainingDataError("pinned chat template hash mismatch")
    tokenizer = AutoTokenizer.from_pretrained(
        str(snapshot), local_files_only=True, trust_remote_code=False
    )
    if tokenizer.chat_template != source["chat_template"]:
        raise TrainingDataError("loaded tokenizer template differs from pinned source")
    if (tokenizer.eos_token, tokenizer.eos_token_id, tokenizer.pad_token_id) != (
        "<|im_end|>",
        151645,
        151643,
    ):
        raise TrainingDataError("unexpected Qwen3 EOS/padding identity")
    return tokenizer, {
        "repository": config.repository,
        "revision": config.tokenizer_revision,
        "files": hashes,
        "chat_template_sha256": template_hash,
        "enable_thinking": True,
        "snapshot": str(snapshot.resolve()),
        "model_weights_loaded": False,
    }
