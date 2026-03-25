# Maemi Translater

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](#getting-started)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Android-green.svg)](#project-scope)
[![Language](https://img.shields.io/badge/Docs-English%20%2F%20Korean-orange.svg)](./README.ko.md)

[Read this README in Korean](./README.ko.md)

Maemi Translater is a cicada sound classification project that combines field recording workflows, dataset curation, machine learning experiments, and an Android-first product concept in one workspace.

The repository is currently organized as a practical build-and-research base rather than a polished app release. Its main focus is to make the full pipeline reproducible: collect audio, validate metadata, train baseline models, and prepare UX and dashboard assets for the product layer.

## Overview

- Build a Korean cicada audio dataset with consistent labeling rules
- Train and compare baseline, weighted, CNN, and transfer-learning models
- Prepare Android-first UX specifications and inference contracts
- Generate dashboard assets for model review and qualitative inspection
- Keep documentation, scripts, manifests, and artifacts in one place

## Project Scope

Current MVP assumptions:

- Target classes include major Korean cicada species such as `chammaemi`, `malmaemi`, and `yujimaemi`
- Primary product direction is `Android-first`
- Typical input audio length is around `5 seconds`
- Analysis is designed around a short sliding window, centered on `3-second` review behavior
- The workspace supports both data/ML operations on PC and inference-oriented product planning for mobile

## Repository Structure

```text
.
|-- dashboard/          Interactive review dashboard assets and cached predictions
|-- data-workspace/     Manifests, metadata templates, review queues, and raw/derived audio folders
|-- design-workspace/   Android UX drafts, prompts, wireframes, and inference specs
|-- docs/               Planning notes, runbooks, policies, and stage-gate documents
|-- ml-workspace/       Experiments, reports, notebooks, trained artifacts, and analysis outputs
|-- requirements/       Environment requirement files
`-- scripts/            Data, training, validation, normalization, and dashboard utility scripts
```

## What Is Included

### Data Pipeline

- Public seed manifests and metadata templates
- YouTube and iNaturalist collection manifests
- Low-quality review queues and filtering reports
- Session metadata validation helpers

### ML Workspace

- Feature extraction scripts
- Baseline and weighted classical ML training flows
- CNN and transfer-learning experiment scripts
- Saved model artifacts and experiment outputs

### Product and UX

- Android MVP wireframes and copy prompts
- Inference contract examples
- Dashboard assets with sample clips and spectrogram images

## Getting Started

### 1. Check your environment

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-local-environment.ps1
```

### 2. Set up the ML environment

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-ml-env.ps1
```

### 3. Download and normalize public seed audio

```powershell
py -3.12 .\scripts\download_public_seed_audio.py
powershell -ExecutionPolicy Bypass -File .\scripts\normalize-public-seed-audio.ps1
```

### 4. Validate session metadata

```powershell
.\.venv\Scripts\python.exe .\scripts\validate_session_metadata.py
```

### 5. Extract features and train a baseline model

```powershell
.\.venv\Scripts\python.exe .\scripts\extract_manifest_features.py <manifest.csv>
.\.venv\Scripts\python.exe .\scripts\train_baseline_from_features.py <features.npz> <metadata.csv>
```

## Dashboard

The repository includes a lightweight dashboard for inspecting predictions and sample assets.

- Main entry: `dashboard/index.html`
- Payload build script: `.\.venv\Scripts\python.exe .\scripts\build_dashboard_payload.py`

## Key Documents

- `docs/00-environment-baseline.md`
- `docs/01-data-collection-spec.md`
- `docs/02-labeling-policy.md`
- `docs/03-ml-experiment-plan.md`
- `docs/04-app-ux-brief.md`
- `docs/05-stage-gates.md`
- `docs/06-next-actions.md`
- `docs/10-android-screen-spec.md`
- `docs/11-baseline-runbook.md`
- `docs/12-worldwide-audio-harvest.md`

## Working Principles

- Do not overwrite original source audio
- Do not force unsupported files into training labels
- Prefer split rules that respect session, location, and device boundaries
- Keep abstention and uncertainty handling as a first-class UX behavior
- Favor operational clarity and repeatability over premature polish

## Status

This repository is an active research-and-build workspace. It already contains a large amount of supporting material, scripts, and artifacts, but it should be read as an evolving foundation for a cicada recognition product rather than a finished application.

## License

No license has been added yet. Add one before distributing or accepting outside contributions.
