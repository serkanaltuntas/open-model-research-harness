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

## License

Software, scripts, tests, configuration files, and schemas are licensed under
the [Apache License 2.0](LICENSE).

Original datasets and documentation are licensed under the
[Creative Commons Attribution 4.0 International License](LICENSE-DATA).

Model outputs, model weights, and third-party materials are not relicensed by
this project and remain subject to their respective source terms. See
[NOTICE](NOTICE) for the repository-wide scope summary.
