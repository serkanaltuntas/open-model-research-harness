import argparse
import hashlib
import json
from datetime import datetime, timezone
from os import walk
from pathlib import Path

from harness.schemas.task import Task
from harness.runners.echo import EchoRunner


def load_tasks(path: Path) -> list[Task]:
    tasks: list[Task] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        tasks.append(Task.from_dict(json.loads(line)))
    return tasks


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    task_path = Path(args.tasks)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    runner = EchoRunner()
    tasks = load_tasks(task_path)

    run_metadata = {
        "run_id": args.run_id,
        "project": "Open Model Research Harness",
        "lab_section": "Open Model Lab",
        "month_gate": "2026-07-foundation-eval-harness",
        "model": {
            "name": runner.name,
            "provider": "local",
            "version": "debug",
            "params": "n/a",
            "quantization": "n/a",
        },
        "dataset": {
            "name": task_path.stem,
            "version": "draft",
            "path": str(task_path),
            "task_count": len(tasks),
        },
        "config": {
            "temperature": None,
            "max_tokens": None,
            "seed": None,
        },
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
    }

    results_path = output_dir / "results.jsonl"

    with results_path.open("w", encoding="utf-8") as f:
        for task in tasks:
            generated = runner.generate(task.prompt, config={})

            result = {
                "run_id": args.run_id,
                "task_id": task.id,
                "category": task.category,
                "model": generated["model"],
                "prompt_hash": sha256_text(task.prompt),
                "output_hash": sha256_text(generated["output"]),
                "prompt": task.prompt,
                "output": generated["output"],
                "score": None,
                "passed": None,
                "grader": task.grader,
                "grader_confidence": None,
                "failure_mode": None,
                "latency_ms": generated["latency_ms"],
                "input_tokens": generated["input_tokens"],
                "output_tokens": generated["output_tokens"],
                "cost_estimate": generated["cost_estimate"],
                "caveats": ["Echo runner records outputs but does not grade them."],
                "raw_result": generated["raw_result"],
            }

            f.write(json.dumps(result, ensure_ascii=False) + "\n")

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
