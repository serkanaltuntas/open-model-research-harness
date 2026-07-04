# Claim Boundaries

This document defines what Open Model Research Harness reports may and may not claim.

## July 2026 Boundary

The July 2026 report should validate the first evaluation harness flow.

If backed by completed runs, it may claim:

- Three open models were evaluated on the same small task suite.
- Scores, latency, cost estimates, grader metadata, and failure-mode labels were recorded.
- The harness can produce inspectable comparison reports from recorded run metadata.
- The July task suite can serve as a baseline for later SFT and DPO experiments.

It must not claim:

- One model is generally better than another.
- The task suite is a comprehensive benchmark.
- The graders are authoritative.
- LLM-as-judge outputs are equivalent to human evaluation.
- The reported scores generalize beyond the small July task suite.
- The system is production-grade.

## General Rules

- Do not publish placeholder metrics.
- Do not invent benchmark results.
- Do not report synthetic results as real runs.
- Do not hide grader uncertainty.
- Do not compare models without the same dataset and comparable config.
- Do not turn task-level observations into broad model-quality claims.

## Standard Report Disclaimer

This report is an early research-engineering artifact. It is designed to validate
evaluation infrastructure and produce a reproducible baseline. The results should
be treated as diagnostic, not as a general benchmark of model quality.
