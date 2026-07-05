import time
from typing import Any

from harness.runners.base import ModelRunner


class EchoRunner(ModelRunner):
    name = "echo-runner"

    def generate(self, prompt: str, config: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        output = f"[ECHO]\n{prompt}"
        latency_ms = int((time.perf_counter() - started) * 1000)

        return {
            "model": self.name,
            "output": output,
            "latency_ms": latency_ms,
            "input_tokens": None,
            "output_tokens": None,
            "cost_estimate": 0.0,
            "raw_result": {},
        }
