# Long-Run Ops

## Recommended long tasks
- Rebuild full dashboard payload after any dataset refresh
- Recompute dashboard prediction cache
- Rebuild preview clips
- Re-extract features after new species or no-cicada data arrives
- Re-train baseline after major dataset growth

## Daily operator flow
1. Update dataset or manifests
2. Rebuild inventory
3. Recompute prediction cache
4. Rebuild preview clips
5. Rebuild dashboard payload
6. Start dashboard app

## Commands
- Inventory
  - `.\\.venv\\Scripts\\python.exe .\\scripts\\build_manifest_inventory.py .\\data-workspace\\metadata\\inat_full_manifest.csv .\\ml-workspace\\reports\\inat_full_inventory.csv`
- Prediction cache
  - `.\\.venv\\Scripts\\python.exe .\\scripts\\precompute_dashboard_predictions.py`
- Preview clips
  - `powershell -ExecutionPolicy Bypass -File .\\scripts\\build_preview_clips.ps1`
- Dashboard payload
  - `.\\.venv\\Scripts\\python.exe .\\scripts\\build_dashboard_payload.py`
- Dashboard app
  - `powershell -ExecutionPolicy Bypass -File .\\scripts\\start-dashboard.ps1`
