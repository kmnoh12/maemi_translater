# 기준선 실험 런북

## 목적

- 공개 동일 종 음원을 이용해 기준선 파이프라인을 재현 가능하게 유지한다.
- 특성추출 단계와 학습 단계를 분리해 모델 비교 실험에 재사용한다.

## 1. 후보 음원 매니페스트 갱신

```powershell
.\.venv\Scripts\python.exe .\scripts\build_inat_candidate_manifest.py --per-region 20
```

## 2. 음원 다운로드

```powershell
.\.venv\Scripts\python.exe .\scripts\download_manifest_audio.py .\data-workspace\metadata\inat_candidate_manifest.csv
```

## 3. 오디오 정규화

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\normalize_manifest_audio.ps1 -ManifestPath .\data-workspace\metadata\inat_candidate_manifest.csv
```

## 4. 자동 특성추출

```powershell
.\.venv\Scripts\python.exe .\scripts\extract_manifest_features.py .\data-workspace\metadata\inat_candidate_manifest.csv --features-out .\ml-workspace\artifacts\features\inat_candidate_features.npz --metadata-out .\ml-workspace\artifacts\features\inat_candidate_features_metadata.csv
```

## 5. 특성 기반 기준선 학습

```powershell
.\.venv\Scripts\python.exe .\scripts\train_baseline_from_features.py .\ml-workspace\artifacts\features\inat_candidate_features.npz .\ml-workspace\artifacts\features\inat_candidate_features_metadata.csv --report-out .\ml-workspace\reports\inat_candidate_feature_report.json --model-out .\ml-workspace\artifacts\inat_candidate_feature_model.joblib
```

## 6. 시각 자산 생성

```powershell
.\.venv\Scripts\python.exe .\scripts\render_baseline_report_assets.py .\ml-workspace\reports\inat_candidate_feature_report.json --out-dir .\ml-workspace\reports\assets
```

## 7. 단일 파일 예측 확인

```powershell
.\.venv\Scripts\python.exe .\scripts\predict_audio_with_baseline.py .\data-workspace\derived_audio\inat_candidates\chammaemi\inat_obs107268421_sound360681_16k_mono.wav --model .\ml-workspace\artifacts\inat_candidate_feature_model.joblib --out .\ml-workspace\reports\sample_prediction_chammaemi.json
```

## 출력물

- 특성 파일: `ml-workspace/artifacts/features/inat_candidate_features.npz`
- 특성 메타데이터: `ml-workspace/artifacts/features/inat_candidate_features_metadata.csv`
- 기준선 리포트: `ml-workspace/reports/inat_candidate_feature_report.json`
- 기준선 모델: `ml-workspace/artifacts/inat_candidate_feature_model.joblib`
- 시각 자산: `ml-workspace/reports/assets/`
- 예측 샘플: `ml-workspace/reports/sample_prediction_chammaemi.json`

## 현재 해석

- 이 파이프라인은 “전세계 동일 종 음원으로도 6종 기준선 분류가 실제로 돈다”는 확인용이다.
- 한국 현장 데이터가 들어오면 같은 런북을 그대로 재사용해 비교 검증한다.
