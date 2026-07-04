# Open Model Research Harness

A small research harness for building and running open model evaluations behind
Open Model Lab.

## Setup

This project uses Python 3.12+ and `uv`.

```sh
uv sync
```

## Rules

Keep source code, configs, schemas, and small reproducible eval definitions in
git. Keep local datasets, model weights, run outputs, traces, and generated
reports outside git.
