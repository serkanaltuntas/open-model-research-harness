import argparse
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from os import walk
from pathlib import Path
from typing import Any

from harness.config import ModelConfig, RunConfig, load_model_config, load_run_config
from harness.graders import GraderResult, get_grader
from harness.runners.base import ModelRunner
from harness.schemas.task import Task
from harness.runners.echo import EchoRunner
from harness.runners.ollama import OllamaRunner


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedEvaluationConfig:
    backend: str
    model_name: str
    model_tag: str
    provider: str
    ollama_id: str | None
    quantization: str
    known_caveats: tuple[str, ...]
    dataset: str
    temperature: int | float | None
    max_tokens: int | None
    seed: int | None
    timeout_seconds: int | float | None

    def generation_config(self) -> dict[str, Any]:
        return {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "seed": self.seed,
            "timeout_seconds": self.timeout_seconds,
        }


def load_tasks(path: Path) -> list[Task]:
    tasks: list[Task] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        tasks.append(Task.from_dict(json.loads(line)))
    return tasks


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def grade_task(task: Task, output: str) -> GraderResult:
    try:
        grader = get_grader(task.grader)
        return grader.grade(task.to_dict(), output)
    except Exception as error:
        LOGGER.exception("Grader failed for task %s", task.id)
        error_detail = str(error).strip().splitlines()[0] if str(error).strip() else ""
        reason = f"Grader failed with {type(error).__name__}."
        if error_detail:
            reason = f"{reason[:-1]}: {error_detail[:160]}"

        return {
            "score": 0.0,
            "passed": False,
            "reason": reason,
            "failure_mode": "grader_error",
            "grader_confidence": "low",
        }


def write_results(
    *,
    tasks: list[Task],
    runner: ModelRunner,
    results_path: Path,
    run_id: str,
    runner_name: str,
    generation_config: dict[str, Any] | None = None,
) -> None:
    resolved_generation_config = generation_config or {}
    with results_path.open("w", encoding="utf-8") as f:
        for task in tasks:
            generated = runner.generate(task.prompt, config=resolved_generation_config)
            grading = grade_task(task, generated["output"])

            result: dict[str, Any] = {
                "run_id": run_id,
                "task_id": task.id,
                "category": task.category,
                "model": generated["model"],
                "prompt_hash": sha256_text(task.prompt),
                "output_hash": sha256_text(generated["output"]),
                "prompt": task.prompt,
                "output": generated["output"],
                "grader": task.grader,
                **grading,
                "latency_ms": generated["latency_ms"],
                "input_tokens": generated["input_tokens"],
                "output_tokens": generated["output_tokens"],
                "cost_estimate": generated["cost_estimate"],
                "caveats": (
                    ["Echo runner output is diagnostic, not a model evaluation."]
                    if runner_name == "echo"
                    else []
                ),
                "raw_result": generated["raw_result"],
            }

            f.write(json.dumps(result, ensure_ascii=False) + "\n")


def resolve_evaluation_config(
    *,
    model_config: ModelConfig | None,
    run_config: RunConfig | None,
    runner_override: str | None = None,
    model_override: str | None = None,
    dataset_override: str | None = None,
    temperature_override: float | None = None,
    max_tokens_override: int | None = None,
    seed_override: int | None = None,
    timeout_seconds_override: float | None = None,
) -> ResolvedEvaluationConfig:
    backend = (
        runner_override
        if runner_override is not None
        else model_config.backend if model_config else None
    )
    if not isinstance(backend, str) or not backend.strip():
        raise ValueError("Runner is required via --runner or --model-config.")
    if backend not in {"echo", "ollama"}:
        raise ValueError(f"Runner {backend!r} is not supported.")

    model_tag = (
        model_override
        if model_override is not None
        else model_config.model if model_config else None
    )
    if not isinstance(model_tag, str) or not model_tag.strip():
        raise ValueError("Model is required via --model or --model-config.")

    dataset = (
        dataset_override
        if dataset_override is not None
        else run_config.dataset if run_config else None
    )
    if not isinstance(dataset, str) or not dataset.strip():
        raise ValueError("Dataset is required via --tasks or --run-config.")

    temperature = (
        temperature_override
        if temperature_override is not None
        else run_config.temperature if run_config else None
    )
    max_tokens = (
        max_tokens_override
        if max_tokens_override is not None
        else run_config.max_tokens if run_config else None
    )
    seed = (
        seed_override
        if seed_override is not None
        else run_config.seed if run_config else None
    )
    timeout_seconds = (
        timeout_seconds_override
        if timeout_seconds_override is not None
        else run_config.timeout_seconds if run_config else None
    )

    if temperature is not None and temperature < 0:
        raise ValueError("Temperature must be non-negative.")
    if max_tokens is not None and max_tokens <= 0:
        raise ValueError("Max tokens must be positive.")
    if timeout_seconds is not None and timeout_seconds <= 0:
        raise ValueError("Timeout seconds must be positive.")

    return ResolvedEvaluationConfig(
        backend=backend,
        model_name=model_config.name if model_config else model_tag,
        model_tag=model_tag,
        provider=model_config.provider if model_config else "local",
        ollama_id=model_config.ollama_id if model_config else None,
        quantization=model_config.quantization if model_config else "unknown",
        known_caveats=model_config.known_caveats if model_config else (),
        dataset=dataset,
        temperature=temperature,
        max_tokens=max_tokens,
        seed=seed,
        timeout_seconds=timeout_seconds,
    )


def build_run_metadata(
    *,
    resolved: ResolvedEvaluationConfig,
    run_id: str,
    task_count: int,
    started_at: str,
) -> dict[str, Any]:
    task_path = Path(resolved.dataset)
    return {
        "run_id": run_id,
        "project": "Open Model Research Harness",
        "lab_section": "Open Model Lab",
        "month_gate": "2026-07-foundation-eval-harness",
        "model": {
            "name": resolved.model_name,
            "model": resolved.model_tag,
            "ollama_id": resolved.ollama_id,
            "backend": resolved.backend,
            "provider": resolved.provider,
            "quantization": resolved.quantization,
            "known_caveats": list(resolved.known_caveats),
        },
        "dataset": {
            "name": task_path.stem,
            "version": "v1",
            "path": resolved.dataset,
            "task_count": task_count,
        },
        "config": resolved.generation_config(),
        "started_at": started_at,
        "finished_at": None,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-config", type=Path)
    parser.add_argument("--run-config", type=Path)
    parser.add_argument("--runner")
    parser.add_argument("--model")
    parser.add_argument("--tasks")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--timeout-seconds", type=float)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)

    model_config = load_model_config(args.model_config) if args.model_config else None
    run_config = load_run_config(args.run_config) if args.run_config else None
    resolved = resolve_evaluation_config(
        model_config=model_config,
        run_config=run_config,
        runner_override=args.runner,
        model_override=args.model,
        dataset_override=args.tasks,
        temperature_override=args.temperature,
        max_tokens_override=args.max_tokens,
        seed_override=args.seed,
        timeout_seconds_override=args.timeout_seconds,
    )

    task_path = Path(resolved.dataset)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    runners = {"echo": EchoRunner, "ollama": OllamaRunner}
    runner = runners[resolved.backend](model=resolved.model_tag)
    tasks = load_tasks(task_path)

    run_metadata = build_run_metadata(
        resolved=resolved,
        run_id=args.run_id,
        task_count=len(tasks),
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    results_path = output_dir / "results.jsonl"

    write_results(
        tasks=tasks,
        runner=runner,
        results_path=results_path,
        run_id=args.run_id,
        runner_name=resolved.backend,
        generation_config=resolved.generation_config(),
    )

    run_metadata["finished_at"] = datetime.now(timezone.utc).isoformat()

    (output_dir / "run.json").write_text(
        json.dumps(run_metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nFiles Created:")
    for (dirpath, dirnames, filenames) in walk(output_dir):
        for filename in filenames:
            print(f"{dirpath}/{filename}")


if __name__ == "__main__":
    main()
