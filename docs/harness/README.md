# Harness Documentation

This directory holds the project harness — the process layer governing how
humans and agents collaborate.

## Main Files

- `HARNESS.md`: how humans and agents collaborate.
- `FEATURE_INTAKE.md`: how prompts become tiny, normal, or high-risk work.
- `CONTEXT_RULES.md`: phase-by-lane context selection rules.
- `TOOL_REGISTRY.md`: equipped tools and capabilities.
- `TRACE_SPEC.md`: trace fields, quality tiers, friction recording.
- `TEST_MATRIX.md`: legacy proof map; current status via `scripts/bin/harness-cli query matrix`.
- `HARNESS_BACKLOG.md`: improvement backlog; current records via `scripts/bin/harness-cli backlog`.
- `GLOSSARY.md`: shared terms.
- `HARNESS_COMPONENTS.md`: map of files to harness component responsibilities.
- `HARNESS_MATURITY.md`: H0–H5 maturity definitions and current level.
- `HARNESS_AUDIT.md`: drift detection and entropy scoring.
- `IMPROVEMENT_PROTOCOL.md`: review loop for backlog proposals.

## Folders

- `stories/`: feature packets and backlog.
- `decisions/`: durable decisions and tradeoffs.
- `templates/`: reusable spec-intake, story, plan, decision, and validation formats.
- `superpowers/`: project-specific superpowers specs.

## Project docs

See `docs/project/` for architecture, setup, deployment, and product documentation.
