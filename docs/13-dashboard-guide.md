# Dashboard Guide

## Purpose
- This dashboard is the working console for the current project.
- It is meant to answer four questions quickly:
  - What audio files do we already have?
  - Which samples can we listen to right now?
  - What does the current baseline model predict?
  - How is the Android app planned to behave?

## What it shows
- Collection overview by species
- Korea vs worldwide file counts
- Total normalized duration
- Duplicate-hash summary
- Current baseline metrics
- Top confusion pairs
- Android screen plan
- Playable representative samples
- Searchable normalized-audio library
- Local file upload prediction
- Library-row instant prediction
- Quick-open links for inventory, report, and model artifact

## How to refresh data
1. Rebuild dashboard payload
   - `.\\.venv\\Scripts\\python.exe .\\scripts\\build_dashboard_payload.py`
2. Open local dashboard server
   - `powershell -ExecutionPolicy Bypass -File .\\scripts\\start-dashboard.ps1`
3. Open in browser
   - `http://127.0.0.1:8765/dashboard/index.html`

## Notes
- Representative sample predictions are precomputed only for the curated sample browser.
- The full library browser supports playback and instant re-prediction for selected rows.
- If a row has no spectrogram image, it means that sample is not in the representative sample set yet.
- Upload prediction uses the current baseline model at `ml-workspace/artifacts/inat_full_feature_model.joblib`.
