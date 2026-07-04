# AGENTS.md

This repository is the working tree for Open Model Research Harness, the code
and artifact scaffold behind the public Open Model Lab project.

Agents should be used conservatively here. Prefer assigning agents repeatable,
well-bounded implementation, maintenance, formatting, testing, and commit tasks.
Do not use agents to make broad research claims, invent benchmark results, or
publish unverified conclusions.

## Scope For Agents

- Keep changes narrow and aligned with the existing repository structure.
- Read the relevant files before editing; do not rely on assumptions about
  project layout, dependencies, or generated artifacts.
- Preserve user work. Never revert, overwrite, or discard uncommitted changes
  unless explicitly instructed.
- Treat datasets, model outputs, eval runs, traces, generated reports, and
  credentials as local artifacts unless the repository explicitly tracks them.
- Do not add placeholder metrics, synthetic public results, or model-quality
  claims without source runs, configs, and caveats.
- Prefer small scripts, reproducible commands, and documented schemas over
  one-off manual workflows.

## Commit Policy

When Serkan asks to commit, inspect everything currently uncommitted before
creating the commit. This includes modified, deleted, renamed, staged, and
untracked files.

Required commit workflow:

1. Run `git status --short`.
2. Inspect staged and unstaged changes with `git diff --stat`, `git diff`, and
   `git diff --cached` as applicable.
3. Inspect untracked files before staging them.
4. Summarize the pending changes at an appropriate level of detail before
   committing.
5. Stage the relevant uncommitted changes. If Serkan asked to commit without a
   narrower scope, stage all current uncommitted repository changes that are not
   ignored by `.gitignore`.
6. Create a GPG-signed Conventional Commit using Serkan's identity.

All commits must:

- Follow the Conventional Commits standard.
- Be GPG-signed.
- Use this author and committer identity:
  `Serkan Altuntaş <serkan@altuntas.dev>`.
- Avoid notes about which AI model or agent produced the commit.

Use this commit command pattern:

```sh
git -c user.name="Serkan Altuntaş" \
  -c user.email="serkan@altuntas.dev" \
  commit -S --author="Serkan Altuntaş <serkan@altuntas.dev>" \
  -m "type(scope): summary"
```

If the commit needs a body, add additional `-m` arguments:

```sh
git -c user.name="Serkan Altuntaş" \
  -c user.email="serkan@altuntas.dev" \
  commit -S --author="Serkan Altuntaş <serkan@altuntas.dev>" \
  -m "type(scope): summary" \
  -m "Explain what changed and why."
```

Do not bypass GPG signing. If signing fails, stop and report the failure instead
of creating an unsigned commit.

## Conventional Commit Guidance

Use the smallest accurate type and scope.

Common types for this repository:

- `feat`: new user-facing or research-harness capability
- `fix`: bug fix or correction to existing behavior
- `docs`: documentation-only change
- `test`: tests, fixtures, or test infrastructure
- `refactor`: behavior-preserving code restructuring
- `perf`: performance improvement
- `build`: packaging, dependency, or build-system change
- `ci`: CI or automation change
- `chore`: repository maintenance

Example messages:

- `docs(repo): add agent operating instructions`
- `chore(repo): ignore local research artifacts`
- `feat(eval): add task schema loader`
- `fix(runs): preserve failure labels in summaries`
- `test(eval): cover scorer edge cases`

Use a body when the change spans multiple concerns, has important caveats, or
needs context for future research reproducibility. Keep the subject concise and
imperative. Do not add AI attribution trailers.

## Verification

Before finishing a coding task, run the most relevant available checks for the
files changed. If the repository has no test command yet, state that plainly.
For commit-only requests, do not invent extra validation; report what was
inspected and whether the commit succeeded.
