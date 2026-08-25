# SADE

Self Adaptive Decision Engine

## Current Version

- Version: 0.1.0
- Current capabilities:
	- Adaptive Pipeline (SADE V0.1)
	- Pricing Pipeline (SADE V0.1)

## Input Service

- SDX V1.1 gRPC

## Current Validated Unit Run

- SADE Unit Run 001
- Entity: AAPL
- Vectors: 100

## Scientific Provenance

SADE V0.1 adaptive behavior originates from the validated frozen adaptive
execution lineage historically validated in Test 006B.

## Current Exclusions

- Volume path: NOT IMPLEMENTED IN V0.1
- External decision synthesis: NOT IMPLEMENTED IN V0.1
- Paper execution: NOT IMPLEMENTED IN V0.1
- Semantic input layer: NOT IMPLEMENTED IN V0.1
- New system feedback loop: NOT IMPLEMENTED IN V0.1

## Setup

```powershell
pip install -e .
pip install -e .[dev]
```

## Package Tests

```powershell
pytest -q
```

## Unit Run CLI

```powershell
python -m sade run --entity AAPL --max-vectors 100
```

## Unit Run 001 Command

```powershell
python -m sade.unit_run.run_001 --endpoint localhost:50051 --output-dir output/unit_runs/001
```

## Pricing Unit Run 001 Command

```powershell
python -m sade.unit_run.run_pricing_001 --endpoint localhost:50051 --output-dir output/unit_runs/pricing_001
```
