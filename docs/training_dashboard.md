# Cicada Audio Dashboard

Updated: 2026-03-19

## Data Status

| Dataset | File Count | Notes |
|---|---:|---|
| iNat full | 1543 | Full raw collection |
| iNat approved | 1099 | Low-quality/review candidates excluded |
| YouTube full | 1111 | All downloaded items |
| YouTube downloaded after reject | 813 | In-place rejected rows removed from training pool |
| YouTube strict | 721 | Stronger title/species filtering |
| YouTube top subset | 200 | Balanced high-confidence subset used for best retrain |

## Low-Quality Review Lists

| Source | Flagged | Rejected | Review |
|---|---:|---:|---:|
| YouTube | 390 | 298 | 92 |
| iNat | 444 | 73 | 371 |
| Total | 834 | 371 | 463 |

Files:

- [youtube_low_quality_review.csv](/C:/Users/kmnoh/maemi_translater/data-workspace/metadata/youtube_low_quality_review.csv)
- [inat_low_quality_review.csv](/C:/Users/kmnoh/maemi_translater/data-workspace/metadata/inat_low_quality_review.csv)
- [all_low_quality_review.csv](/C:/Users/kmnoh/maemi_translater/data-workspace/metadata/all_low_quality_review.csv)
- [low_quality_review_summary.json](/C:/Users/kmnoh/maemi_translater/data-workspace/metadata/low_quality_review_summary.json)

## Training Sets

| Experiment | Source Files | Windows | Test Accuracy | Macro F1 | Report |
|---|---:|---:|---:|---:|---|
| iNat + noisy YouTube combined | 2653 | 102789 | 0.2968 | 0.2768 | [combined report](/C:/Users/kmnoh/maemi_translater/ml-workspace/reports/cnn_experiment_combined_report.json) |
| Combined filtered GPU | 2305 | 57789 | 0.4613 | 0.4514 | [filtered GPU report](/C:/Users/kmnoh/maemi_translater/ml-workspace/reports/cnn_experiment_combined_filtered_gpu_report.json) |
| iNat approved + YouTube top200 GPU | 1299 | 19134 | 0.7630 | 0.7329 | [top200 GPU report](/C:/Users/kmnoh/maemi_translater/ml-workspace/reports/cnn_experiment_top200_gpu_report.json) |

## Current Best Practical Set

- iNat approved: [inat_approved_manifest.csv](/C:/Users/kmnoh/maemi_translater/data-workspace/metadata/inat_approved_manifest.csv)
- YouTube high-confidence subset: [youtube_manifest_top200.csv](/C:/Users/kmnoh/maemi_translater/data-workspace/metadata/youtube_manifest_top200.csv)
- Combined training manifest: [combined_training_manifest_top200.csv](/C:/Users/kmnoh/maemi_translater/data-workspace/metadata/combined_training_manifest_top200.csv)
- CNN split manifest: [cnn_manifest_with_split.csv](/C:/Users/kmnoh/maemi_translater/ml-workspace/experiments/cnn_dataset_top200/cnn_manifest_with_split.csv)
- Best current model: [cnn_experiment_top200_gpu_model.pt](/C:/Users/kmnoh/maemi_translater/ml-workspace/artifacts/cnn_experiment_top200_gpu_model.pt)

## Recommendation

- Keep the current `iNat approved + YouTube top200` model as the working baseline.
- Next sweep should test `top150` and `top250`.
- Add new YouTube clips in small high-confidence batches instead of bulk expansion.
