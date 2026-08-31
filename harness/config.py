from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


MODEL_FIELDS = {
    "name",
    "backend",
    "model",
    "provider",
    "ollama_id",
    "quantization",
    "known_caveats",
}
RUN_FIELDS = {
    "dataset",
    "temperature",
    "max_tokens",
    "seed",
    "timeout_seconds",
}
MLX_MODEL_FIELDS = {
    "name",
    "backend",
    "repository",
    "revision",
    "upstream_model",
    "license",
    "quantization",
    "training_backend",
    "conversion",
    "model_artifact",
    "tokenizer",
    "known_caveats",
}


class ConfigError(ValueError):
    """Raised when a model or run configuration is invalid."""


@dataclass(frozen=True)
class ModelConfig:
    name: str
    backend: str
    model: str
    provider: str
    ollama_id: str
    quantization: str
    known_caveats: tuple[str, ...]


@dataclass(frozen=True)
class RunConfig:
    dataset: str
    temperature: int | float
    max_tokens: int
    seed: int | None
    timeout_seconds: int | float


@dataclass(frozen=True)
class ArtifactIdentity:
    path: str
    size_bytes: int
    sha256: str
    xet_hash: str


@dataclass(frozen=True)
class MlxModelConfig:
    name: str
    backend: str
    repository: str
    revision: str
    upstream_model: str
    license: str
    quantization_bits: int
    quantization_group_size: int
    training_backend: str
    conversion_tool: str
    conversion_version: str
    model_artifact: ArtifactIdentity
    tokenizer_revision: str
    chat_template_file: str
    tokenizer_artifact: ArtifactIdentity
    known_caveats: tuple[str, ...]


def _load_yaml_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"{path}: configuration file does not exist")

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise ConfigError(f"{path}: invalid YAML: {error}") from error

    if not isinstance(data, dict):
        raise ConfigError(f"{path}: configuration root must be a mapping")
    return data


def _validate_fields(
    path: Path,
    data: dict[str, Any],
    expected_fields: set[str],
) -> None:
    missing = sorted(expected_fields - data.keys())
    if missing:
        raise ConfigError(f"{path}: missing required field '{missing[0]}'")

    unknown = sorted(data.keys() - expected_fields)
    if unknown:
        raise ConfigError(f"{path}: unknown field '{unknown[0]}'")


def _non_empty_string(path: Path, data: dict[str, Any], field: str) -> str:
    value = data[field]
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{path}: field '{field}' must be a non-empty string")
    return value


def _mapping(path: Path, data: dict[str, Any], field: str) -> dict[str, Any]:
    value = data[field]
    if not isinstance(value, dict):
        raise ConfigError(f"{path}: field '{field}' must be a mapping")
    return value


def _positive_integer(path: Path, data: dict[str, Any], field: str) -> int:
    value = data[field]
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConfigError(f"{path}: field '{field}' must be a positive integer")
    return value


def _artifact_identity(
    path: Path,
    data: dict[str, Any],
    field: str,
) -> ArtifactIdentity:
    artifact = _mapping(path, data, field)
    expected_fields = {"path", "size_bytes", "sha256", "xet_hash"}
    _validate_fields(path, artifact, expected_fields)
    sha256 = _non_empty_string(path, artifact, "sha256")
    xet_hash = _non_empty_string(path, artifact, "xet_hash")
    if len(sha256) != 64 or any(character not in "0123456789abcdef" for character in sha256):
        raise ConfigError(f"{path}: field '{field}.sha256' must be lowercase SHA256")
    if len(xet_hash) != 64 or any(character not in "0123456789abcdef" for character in xet_hash):
        raise ConfigError(f"{path}: field '{field}.xet_hash' must be lowercase SHA256")
    return ArtifactIdentity(
        path=_non_empty_string(path, artifact, "path"),
        size_bytes=_positive_integer(path, artifact, "size_bytes"),
        sha256=sha256,
        xet_hash=xet_hash,
    )


def load_model_config(path: Path) -> ModelConfig:
    data = _load_yaml_object(path)
    _validate_fields(path, data, MODEL_FIELDS)

    name = _non_empty_string(path, data, "name")
    backend = _non_empty_string(path, data, "backend")
    if backend != "ollama":
        raise ConfigError(f"{path}: field 'backend' must be 'ollama'")

    known_caveats = data["known_caveats"]
    if not isinstance(known_caveats, list) or not all(
        isinstance(caveat, str) and caveat.strip() for caveat in known_caveats
    ):
        raise ConfigError(
            f"{path}: field 'known_caveats' must be a list of non-empty strings"
        )

    return ModelConfig(
        name=name,
        backend=backend,
        model=_non_empty_string(path, data, "model"),
        provider=_non_empty_string(path, data, "provider"),
        ollama_id=_non_empty_string(path, data, "ollama_id"),
        quantization=_non_empty_string(path, data, "quantization"),
        known_caveats=tuple(known_caveats),
    )


def load_mlx_model_config(path: Path) -> MlxModelConfig:
    data = _load_yaml_object(path)
    _validate_fields(path, data, MLX_MODEL_FIELDS)

    backend = _non_empty_string(path, data, "backend")
    if backend != "mlx":
        raise ConfigError(f"{path}: field 'backend' must be 'mlx'")
    training_backend = _non_empty_string(path, data, "training_backend")
    if training_backend != "mlx-lm":
        raise ConfigError(f"{path}: field 'training_backend' must be 'mlx-lm'")

    revision = _non_empty_string(path, data, "revision")
    if len(revision) != 40 or any(
        character not in "0123456789abcdef" for character in revision
    ):
        raise ConfigError(f"{path}: field 'revision' must be a 40-character commit hash")

    quantization = _mapping(path, data, "quantization")
    _validate_fields(path, quantization, {"bits", "group_size"})
    conversion = _mapping(path, data, "conversion")
    _validate_fields(path, conversion, {"tool", "version"})
    tokenizer = _mapping(path, data, "tokenizer")
    _validate_fields(
        path,
        tokenizer,
        {"revision", "chat_template_file", "artifact"},
    )
    tokenizer_revision = _non_empty_string(path, tokenizer, "revision")
    if tokenizer_revision != revision:
        raise ConfigError(
            f"{path}: tokenizer revision must match the model revision"
        )

    known_caveats = data["known_caveats"]
    if not isinstance(known_caveats, list) or not all(
        isinstance(caveat, str) and caveat.strip() for caveat in known_caveats
    ):
        raise ConfigError(
            f"{path}: field 'known_caveats' must be a list of non-empty strings"
        )

    return MlxModelConfig(
        name=_non_empty_string(path, data, "name"),
        backend=backend,
        repository=_non_empty_string(path, data, "repository"),
        revision=revision,
        upstream_model=_non_empty_string(path, data, "upstream_model"),
        license=_non_empty_string(path, data, "license"),
        quantization_bits=_positive_integer(path, quantization, "bits"),
        quantization_group_size=_positive_integer(path, quantization, "group_size"),
        training_backend=training_backend,
        conversion_tool=_non_empty_string(path, conversion, "tool"),
        conversion_version=_non_empty_string(path, conversion, "version"),
        model_artifact=_artifact_identity(path, data, "model_artifact"),
        tokenizer_revision=tokenizer_revision,
        chat_template_file=_non_empty_string(path, tokenizer, "chat_template_file"),
        tokenizer_artifact=_artifact_identity(path, tokenizer, "artifact"),
        known_caveats=tuple(known_caveats),
    )


def load_run_config(path: Path) -> RunConfig:
    data = _load_yaml_object(path)
    _validate_fields(path, data, RUN_FIELDS)

    dataset = _non_empty_string(path, data, "dataset")

    temperature = data["temperature"]
    if isinstance(temperature, bool) or not isinstance(temperature, int | float):
        raise ConfigError(f"{path}: field 'temperature' must be numeric")
    if temperature < 0:
        raise ConfigError(f"{path}: field 'temperature' must be non-negative")

    max_tokens = data["max_tokens"]
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int):
        raise ConfigError(f"{path}: field 'max_tokens' must be an integer")
    if max_tokens <= 0:
        raise ConfigError(f"{path}: field 'max_tokens' must be positive")

    seed = data["seed"]
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise ConfigError(f"{path}: field 'seed' must be an integer or null")

    timeout_seconds = data["timeout_seconds"]
    if isinstance(timeout_seconds, bool) or not isinstance(
        timeout_seconds, int | float
    ):
        raise ConfigError(f"{path}: field 'timeout_seconds' must be numeric")
    if timeout_seconds <= 0:
        raise ConfigError(f"{path}: field 'timeout_seconds' must be positive")

    return RunConfig(
        dataset=dataset,
        temperature=temperature,
        max_tokens=max_tokens,
        seed=seed,
        timeout_seconds=timeout_seconds,
    )
