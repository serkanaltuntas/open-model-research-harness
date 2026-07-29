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
