# Data_2 auxiliary dataset

This folder intentionally keeps Data_2 separate from the canonical runtime dataset.

## Decision

- Canonical runtime dataset remains `data/processed/seed_real_clean.json`.
- Data_2 is used only as an auxiliary dataset for:
  - synthetic Safety spike testing;
  - balanced-label model experiments;
  - taxonomy / safety-keyword reference.

Do **not** replace `data/processed/seed_real_clean.json` with files from this folder without a separate migration and evaluation pass.

## Contents

```text
synthetic/safety_spike_cases.canonical.json
train_balanced/seed_train_labeled.canonical.json
train_balanced/train_split.canonical.json
train_balanced/test_split.canonical.json
taxonomy/safety_keywords.json
taxonomy/taxonomy.json
taxonomy/routing_table.json
taxonomy/severity_rules.json
summary.json
```

## Provenance rule

Rows in this folder come from `~/Downloads/Data_2`. Data_2 includes mock/synthetic rows, especially IDs starting with `FB-MOCK-*`. Therefore this folder must be described as **auxiliary**, not as the main public-review dataset.

## Generated summary

- Balanced labeled rows: 4948
- Balanced labeled mock rows: 2706
- Balanced labeled unique texts: 3742
- Safety spike rows: 30

Regenerate with:

```bash
python3 scripts/prepare_data2_auxiliary.py
```
