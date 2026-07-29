import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


REQUIRED_RESULT_FIELDS = {
    "run_id",
    "task_id",
    "category",
    "model",
    "output",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "cost_estimate",
    "raw_result",
    "grader",
    "score",
    "passed",
    "reason",
    "failure_mode",
    "grader_confidence",
}
SHARED_CONFIG_FIELDS = (
    "temperature",
    "max_tokens",
    "seed",
    "timeout_seconds",
)


class ComparisonError(ValueError):
    """Raised when run artifacts cannot be compared safely."""


def _load_json(path: Path) -> Any:
    if not path.is_file():
        raise ComparisonError(f"{path}: file does not exist")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ComparisonError(f"{path}: invalid JSON: {error}") from error


def _load_results(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ComparisonError(f"{path}: file does not exist")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise ComparisonError(f"{path}: invalid UTF-8: {error}") from error

    results: list[dict[str, Any]] = []
    seen_task_ids: set[str] = set()
    for row_number, line in enumerate(lines, start=1):
        location = f"{path}: row {row_number}"
        if not line.strip():
            raise ComparisonError(f"{location}: empty JSONL row")
        try:
            result = json.loads(line)
        except json.JSONDecodeError as error:
            raise ComparisonError(f"{location}: invalid JSON: {error}") from error
        if not isinstance(result, dict):
            raise ComparisonError(f"{location}: result must be a JSON object")

        missing = sorted(REQUIRED_RESULT_FIELDS - result.keys())
        if missing:
            raise ComparisonError(
                f"{location}: missing required field '{missing[0]}'"
            )

        task_id = result["task_id"]
        if not isinstance(task_id, str) or not task_id:
            raise ComparisonError(
                f"{location}: field 'task_id' must be a non-empty string"
            )
        if task_id in seen_task_ids:
            raise ComparisonError(
                f"{location}: duplicate task_id {task_id!r}"
            )
        seen_task_ids.add(task_id)

        score = result["score"]
        if (
            isinstance(score, bool)
            or not isinstance(score, int | float)
            or not math.isfinite(score)
            or not 0.0 <= score <= 1.0
        ):
            raise ComparisonError(
                f"{location}: field 'score' must be numeric between 0.0 and 1.0"
            )
        if not isinstance(result["passed"], bool):
            raise ComparisonError(f"{location}: field 'passed' must be boolean")
        results.append(result)

    if not results:
        raise ComparisonError(f"{path}: result count must not be zero")
    return results


def _load_run(run_dir: Path) -> dict[str, Any]:
    run_path = run_dir / "run.json"
    metadata = _load_json(run_path)
    if not isinstance(metadata, dict):
        raise ComparisonError(f"{run_path}: root must be a JSON object")

    results = _load_results(run_dir / "results.jsonl")
    run_id = metadata.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ComparisonError(f"{run_path}: missing non-empty run_id")
    for row_number, result in enumerate(results, start=1):
        if result["run_id"] != run_id:
            raise ComparisonError(
                f"{run_dir / 'results.jsonl'}: row {row_number}: run_id does not "
                "match run.json"
            )

    dataset = metadata.get("dataset")
    config = metadata.get("config")
    model = metadata.get("model")
    if not isinstance(dataset, dict):
        raise ComparisonError(f"{run_path}: field 'dataset' must be an object")
    if not isinstance(config, dict):
        raise ComparisonError(f"{run_path}: field 'config' must be an object")
    if not isinstance(model, dict):
        raise ComparisonError(f"{run_path}: field 'model' must be an object")
    if dataset.get("task_count") != len(results):
        raise ComparisonError(
            f"{run_path}: dataset.task_count does not match results.jsonl count"
        )

    required_model_fields = {
        "name",
        "model",
        "ollama_id",
        "backend",
        "provider",
        "quantization",
        "known_caveats",
    }
    missing_model_fields = sorted(required_model_fields - model.keys())
    if missing_model_fields:
        raise ComparisonError(
            f"{run_path}: model missing field '{missing_model_fields[0]}'"
        )
    return {
        "run_dir": str(run_dir),
        "metadata": metadata,
        "results": results,
    }


def _shared_configuration(run: dict[str, Any]) -> dict[str, Any]:
    metadata = run["metadata"]
    dataset = metadata["dataset"]
    config = metadata["config"]
    missing_config = [field for field in SHARED_CONFIG_FIELDS if field not in config]
    if missing_config:
        raise ComparisonError(
            f"{run['run_dir']}/run.json: config missing field "
            f"'{missing_config[0]}'"
        )
    for field in ("name", "version", "path", "task_count"):
        if field not in dataset or dataset[field] in (None, ""):
            raise ComparisonError(
                f"{run['run_dir']}/run.json: dataset missing field '{field}'"
            )
    if metadata.get("month_gate") in (None, ""):
        raise ComparisonError(
            f"{run['run_dir']}/run.json: missing field 'month_gate'"
        )
    return {
        "dataset": {
            "name": dataset.get("name"),
            "version": dataset.get("version"),
            "path": dataset.get("path"),
            "task_count": dataset.get("task_count"),
        },
        "temperature": config["temperature"],
        "max_tokens": config["max_tokens"],
        "seed": config["seed"],
        "timeout_seconds": config["timeout_seconds"],
        "month_gate": metadata.get("month_gate"),
        "result_schema": sorted(REQUIRED_RESULT_FIELDS),
    }


def _verify_comparability(runs: list[dict[str, Any]]) -> dict[str, Any]:
    baseline = _shared_configuration(runs[0])
    for run in runs[1:]:
        candidate = _shared_configuration(run)
        if candidate != baseline:
            differing = [
                key for key in baseline if baseline[key] != candidate.get(key)
            ]
            raise ComparisonError(
                f"{run['run_dir']}/run.json: incompatible shared configuration "
                f"for field(s): {', '.join(differing)}"
            )

    baseline_results = {r["task_id"]: r for r in runs[0]["results"]}
    for run in runs[1:]:
        candidate_results = {r["task_id"]: r for r in run["results"]}
        if set(candidate_results) != set(baseline_results):
            raise ComparisonError(
                f"{run['run_dir']}/results.jsonl: task ID set does not match baseline"
            )
        for task_id, baseline_result in baseline_results.items():
            candidate_result = candidate_results[task_id]
            for field in ("category", "grader"):
                if candidate_result[field] != baseline_result[field]:
                    raise ComparisonError(
                        f"{run['run_dir']}/results.jsonl: task {task_id!r} field "
                        f"'{field}' does not match baseline"
                    )
            if (
                "prompt_hash" in baseline_result
                and candidate_result.get("prompt_hash")
                != baseline_result.get("prompt_hash")
            ):
                raise ComparisonError(
                    f"{run['run_dir']}/results.jsonl: task {task_id!r} prompt_hash "
                    "does not match baseline"
                )
    return baseline


def _numeric_values(
    results: list[dict[str, Any]],
    field: str,
) -> tuple[list[float], int]:
    values = [
        float(result[field])
        for result in results
        if isinstance(result.get(field), int | float)
        and not isinstance(result.get(field), bool)
        and math.isfinite(result[field])
    ]
    return values, len(results) - len(values)


def _mean(values: list[float], digits: int = 4) -> float | None:
    return round(sum(values) / len(values), digits) if values else None


def _category_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for category in sorted({result["category"] for result in results}):
        category_results = [r for r in results if r["category"] == category]
        scores = [float(r["score"]) for r in category_results]
        passed_count = sum(r["passed"] for r in category_results)
        task_count = len(category_results)
        metrics[category] = {
            "task_count": task_count,
            "passed_count": passed_count,
            "failed_count": task_count - passed_count,
            "pass_rate": round(passed_count / task_count, 4),
            "mean_score": _mean(scores),
        }
    return metrics


def _throughput_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    task_rates: list[float] = []
    total_tokens = 0.0
    total_duration_ns = 0.0
    for result in results:
        raw_result = result.get("raw_result")
        if not isinstance(raw_result, dict):
            continue
        token_count = raw_result.get("eval_count")
        duration_ns = raw_result.get("eval_duration")
        if (
            isinstance(token_count, int | float)
            and not isinstance(token_count, bool)
            and isinstance(duration_ns, int | float)
            and not isinstance(duration_ns, bool)
            and token_count >= 0
            and duration_ns > 0
        ):
            task_rates.append(token_count / (duration_ns / 1_000_000_000))
            total_tokens += token_count
            total_duration_ns += duration_ns

    weighted_rate = (
        total_tokens / (total_duration_ns / 1_000_000_000)
        if total_duration_ns
        else None
    )
    return {
        "available_task_count": len(task_rates),
        "missing_task_count": len(results) - len(task_rates),
        "mean_task_tokens_per_second": _mean(task_rates, 2),
        "aggregate_tokens_per_second": (
            round(weighted_rate, 2) if weighted_rate is not None else None
        ),
    }


def _aggregate_model(run: dict[str, Any]) -> dict[str, Any]:
    results = run["results"]
    metadata = run["metadata"]
    scores = [float(result["score"]) for result in results]
    passed_count = sum(result["passed"] for result in results)
    task_count = len(results)
    latency_values, latency_missing = _numeric_values(results, "latency_ms")
    input_values, input_missing = _numeric_values(results, "input_tokens")
    output_values, output_missing = _numeric_values(results, "output_tokens")
    cost_values, cost_missing = _numeric_values(results, "cost_estimate")

    return {
        "run_id": metadata["run_id"],
        "source_run_dir": run["run_dir"],
        "provenance": metadata["model"],
        "task_count": task_count,
        "passed_count": passed_count,
        "failed_count": task_count - passed_count,
        "pass_rate": round(passed_count / task_count, 4),
        "mean_score": _mean(scores),
        "score_sum": round(sum(scores), 4),
        "category_metrics": _category_metrics(results),
        "latency_ms": {
            "average": _mean(latency_values, 2),
            "median": (
                round(statistics.median(latency_values), 2)
                if latency_values
                else None
            ),
            "available_count": len(latency_values),
            "missing_count": latency_missing,
        },
        "tokens": {
            "total_input_tokens": int(sum(input_values)) if input_values else None,
            "total_output_tokens": int(sum(output_values)) if output_values else None,
            "average_output_tokens": _mean(output_values, 2),
            "input_available_count": len(input_values),
            "input_missing_count": input_missing,
            "output_available_count": len(output_values),
            "output_missing_count": output_missing,
        },
        "generation_throughput": _throughput_metrics(results),
        "recorded_api_cost": {
            "total": round(sum(cost_values), 6) if cost_values else None,
            "available_count": len(cost_values),
            "missing_count": cost_missing,
            "interpretation": "Recorded API cost only; local compute cost is not measured.",
        },
        "failure_mode_counts": dict(
            sorted(
                Counter(
                    result["failure_mode"]
                    for result in results
                    if not result["passed"]
                ).items()
            )
        ),
        "grader_confidence_counts": dict(
            sorted(Counter(r["grader_confidence"] for r in results).items())
        ),
        "grader_error_count": sum(
            result["failure_mode"] == "grader_error" for result in results
        ),
    }


def _normalized_output(value: str) -> str:
    return " ".join(value.casefold().split())


def _task_comparisons(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    model_names = [run["metadata"]["model"]["name"] for run in runs]
    results_by_model = {
        run["metadata"]["model"]["name"]: {
            result["task_id"]: result for result in run["results"]
        }
        for run in runs
    }
    task_order = [result["task_id"] for result in runs[0]["results"]]
    comparisons = []
    for task_id in task_order:
        model_results = {
            model_name: results_by_model[model_name][task_id]
            for model_name in model_names
        }
        passed_models = [
            model_name
            for model_name, result in model_results.items()
            if result["passed"]
        ]
        if len(passed_models) == len(model_names):
            pattern = "passed_by_all_models"
        elif not passed_models:
            pattern = "failed_by_all_models"
        elif len(passed_models) == 1:
            pattern = "passed_only_by_one_model"
        elif len(passed_models) == 2:
            pattern = "passed_by_exactly_two_models"
        else:
            pattern = "mixed"

        normalized_outputs = {
            model_name: _normalized_output(str(result["output"]))
            for model_name, result in model_results.items()
        }
        similar_output_disagreement = False
        for index, first_model in enumerate(model_names):
            for second_model in model_names[index + 1 :]:
                if (
                    model_results[first_model]["passed"]
                    != model_results[second_model]["passed"]
                    and normalized_outputs[first_model]
                    and normalized_outputs[first_model]
                    == normalized_outputs[second_model]
                ):
                    similar_output_disagreement = True

        first_result = model_results[model_names[0]]
        comparisons.append(
            {
                "task_id": task_id,
                "category": first_result["category"],
                "grader": first_result["grader"],
                "pattern": pattern,
                "passed_models": passed_models,
                "similar_output_disagreement": similar_output_disagreement,
                "models": {
                    model_name: {
                        "score": result["score"],
                        "passed": result["passed"],
                        "failure_mode": result["failure_mode"],
                        "reason": result["reason"],
                        "latency_ms": result["latency_ms"],
                        "output_tokens": result["output_tokens"],
                    }
                    for model_name, result in model_results.items()
                },
            }
        )
    return comparisons


def compare_runs(run_dirs: list[Path]) -> dict[str, Any]:
    if len(run_dirs) < 2:
        raise ComparisonError("At least two --run-dir values are required.")
    runs = [_load_run(run_dir) for run_dir in run_dirs]
    model_names = [run["metadata"]["model"]["name"] for run in runs]
    if len(model_names) != len(set(model_names)):
        raise ComparisonError("Configured model names must be unique.")

    shared_configuration = _verify_comparability(runs)
    model_metrics = {
        run["metadata"]["model"]["name"]: _aggregate_model(run) for run in runs
    }
    task_comparisons = _task_comparisons(runs)
    missing_caveats = []
    for model_name, metrics in model_metrics.items():
        missing = metrics["latency_ms"]["missing_count"]
        if missing:
            missing_caveats.append(
                f"{model_name}: latency_ms missing for {missing} task(s)."
            )
        missing = metrics["tokens"]["input_missing_count"]
        if missing:
            missing_caveats.append(
                f"{model_name}: input_tokens missing for {missing} task(s)."
            )
        missing = metrics["tokens"]["output_missing_count"]
        if missing:
            missing_caveats.append(
                f"{model_name}: output_tokens missing for {missing} task(s)."
            )
        missing = metrics["generation_throughput"]["missing_task_count"]
        if missing:
            missing_caveats.append(
                f"{model_name}: throughput metadata missing for {missing} task(s)."
            )

    return {
        "comparison_metadata": {
            "schema_version": 1,
            "deterministic": True,
            "run_count": len(runs),
            "model_order": model_names,
            "source_run_dirs": [str(path) for path in run_dirs],
        },
        "shared_configuration": shared_configuration,
        "models": model_metrics,
        "task_comparisons": task_comparisons,
        "missing_data_caveats": missing_caveats,
        "claim_boundary": (
            "These diagnostic results apply only to this 25-task July suite and "
            "do not establish general model quality."
        ),
    }


def _format_number(value: Any, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_markdown(comparison: dict[str, Any]) -> str:
    model_order = comparison["comparison_metadata"]["model_order"]
    models = comparison["models"]
    shared = comparison["shared_configuration"]
    lines = [
        "# July 2026 Model Comparison",
        "",
        "## Scope and Claim Boundary",
        "",
        comparison["claim_boundary"],
        "The model with the highest pass rate is identified only within this suite.",
        "",
        "## Shared Evaluation Setup",
        "",
        f"- Dataset: `{shared['dataset']['path']}`",
        f"- Tasks: {shared['dataset']['task_count']}",
        f"- Temperature: {shared['temperature']}",
        f"- Max tokens: {shared['max_tokens']}",
        f"- Seed: {shared['seed']}",
        f"- Timeout: {shared['timeout_seconds']} seconds",
        f"- Month gate: `{shared['month_gate']}`",
        "",
        "## Model Provenance",
        "",
        "| Model | Ollama tag | Ollama ID | Provider | Quantization |",
        "|---|---|---|---|---|",
    ]
    for model_name in model_order:
        provenance = models[model_name]["provenance"]
        lines.append(
            f"| {model_name} | `{provenance['model']}` | "
            f"`{provenance['ollama_id']}` | {provenance['provider']} | "
            f"{provenance['quantization']} |"
        )

    lines.extend(
        [
            "",
            "All model records note that the Ollama ID identifies the local artifact "
            "and that quantization was not independently verified.",
            "",
            "## Overall Results",
            "",
            "| Model | Passed | Failed | Pass rate | Mean score | Score sum |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for model_name in model_order:
        metrics = models[model_name]
        lines.append(
            f"| {model_name} | {metrics['passed_count']} | {metrics['failed_count']} | "
            f"{metrics['pass_rate']:.1%} | {metrics['mean_score']:.3f} | "
            f"{metrics['score_sum']:.1f} |"
        )

    highest_rate = max(models[name]["pass_rate"] for name in model_order)
    highest_models = [
        name for name in model_order if models[name]["pass_rate"] == highest_rate
    ]
    lines.extend(
        [
            "",
            f"Within this suite, {', '.join(highest_models)} recorded the highest pass "
            f"rate ({highest_rate:.1%}).",
            "",
            "## Category Results",
            "",
            "| Model | Category | Passed | Failed | Pass rate | Mean score |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for model_name in model_order:
        for category, metrics in models[model_name]["category_metrics"].items():
            lines.append(
                f"| {model_name} | {category} | {metrics['passed_count']} | "
                f"{metrics['failed_count']} | {metrics['pass_rate']:.1%} | "
                f"{metrics['mean_score']:.3f} |"
            )

    lines.extend(
        [
            "",
            "## Latency and Token Observations",
            "",
            "| Model | Avg latency ms | Median latency ms | Input tokens | "
            "Output tokens | Avg output tokens | Aggregate tokens/s |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for model_name in model_order:
        metrics = models[model_name]
        lines.append(
            f"| {model_name} | {_format_number(metrics['latency_ms']['average'])} | "
            f"{_format_number(metrics['latency_ms']['median'])} | "
            f"{_format_number(metrics['tokens']['total_input_tokens'])} | "
            f"{_format_number(metrics['tokens']['total_output_tokens'])} | "
            f"{_format_number(metrics['tokens']['average_output_tokens'])} | "
            f"{_format_number(metrics['generation_throughput']['aggregate_tokens_per_second'])} |"
        )
    lines.extend(
        [
            "",
            "Throughput is derived from Ollama `eval_count` and `eval_duration`. "
            "Recorded API cost is 0.0 for these local runs; local compute cost was not measured.",
            "",
            "## Failure-Mode Distribution",
            "",
            "| Model | Failure mode | Count | Grader errors |",
            "|---|---|---:|---:|",
        ]
    )
    for model_name in model_order:
        metrics = models[model_name]
        failure_counts = metrics["failure_mode_counts"] or {"none": 0}
        for failure_mode, count in failure_counts.items():
            lines.append(
                f"| {model_name} | {failure_mode} | {count} | "
                f"{metrics['grader_error_count']} |"
            )
    lines.extend(
        [
            "",
            "Grader confidence counts:",
            "",
            "| Model | High | Medium | Low |",
            "|---|---:|---:|---:|",
        ]
    )
    for model_name in model_order:
        counts = models[model_name]["grader_confidence_counts"]
        lines.append(
            f"| {model_name} | {counts.get('high', 0)} | "
            f"{counts.get('medium', 0)} | {counts.get('low', 0)} |"
        )

    disagreements = [
        task
        for task in comparison["task_comparisons"]
        if task["pattern"] != "passed_by_all_models"
    ]
    lines.extend(
        [
            "",
            "## Task-Level Disagreements",
            "",
            "| Task | Category | Pattern | Passed models |",
            "|---|---|---|---|",
        ]
    )
    for task in disagreements:
        passed_models = ", ".join(task["passed_models"]) or "none"
        lines.append(
            f"| `{task['task_id']}` | {task['category']} | {task['pattern']} | "
            f"{passed_models} |"
        )

    lines.extend(["", "## Limitations", ""])
    limitations = [
        "The suite contains only 25 draft tasks and is not a general benchmark.",
        "Graders are deterministic heuristics and may produce false negatives.",
        "Latency and throughput reflect one local runtime environment.",
        "Recorded API cost does not represent local compute or energy cost.",
        "Similar-output disagreement detection uses normalized exact equality only.",
    ]
    limitations.extend(comparison["missing_data_caveats"])
    lines.extend(f"- {limitation}" for limitation in limitations)
    lines.extend(["", "## Source Artifacts", ""])
    for run_dir in comparison["comparison_metadata"]["source_run_dirs"]:
        lines.append(f"- `{run_dir}/run.json` and `{run_dir}/results.jsonl`")
    lines.append("- `datasets/evals/july_eval_v1.jsonl`")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare compatible eval runs.")
    parser.add_argument("--run-dir", action="append", required=True, type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--markdown-output", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        comparison = compare_runs(args.run_dir)
    except ComparisonError as error:
        parser.error(str(error))

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(comparison, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.markdown_output.write_text(render_markdown(comparison), encoding="utf-8")
    print(f"Compared {len(args.run_dir)} compatible runs.")
    print(f"JSON: {args.json_output}")
    print(f"Markdown: {args.markdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
