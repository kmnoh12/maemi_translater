# 데이터 수집 스펙

## 1차 타깃 종

- 참매미
- 말매미
- 유지매미

## 수집 단위

- 파일이 아니라 `세션` 단위로 관리한다.
- 한 세션은 가능한 한 하나의 현장 방문과 하나의 촬영/녹음 맥락을 의미한다.

## 세션마다 반드시 남길 항목

- `session_id`
- `recorded_at`
- `location_name`
- `latitude`, `longitude`
- `device_model`
- `distance_estimate_m`
- `habitat_type`
- `background_noise`
- `weather_note`
- `species_label`
- `label_confidence`
- `label_evidence`
- `mixture_flag`
- `acoustic_quality`
- `notes`

## 종 확인 근거

아래 중 최소 1개 이상을 남긴다.

- 성충 사진
- 탈피각 사진
- 전문가 확인
- 같은 개체의 현장 반복 관찰

## 수집 목표

- 종당 최소 `100~150 세션`
- 장소 최소 `5개`
- 스마트폰 기종 최소 `3개`
- 시간대 최소 `2개`

## 파일 저장 원칙

- 원본은 `data-workspace/raw_audio/`
- 학습용 변환본은 `data-workspace/derived_audio/`
- 메타데이터는 `data-workspace/metadata/`
- 검수 메모는 `data-workspace/review/`

## 절대 하지 말 것

- 라벨 근거 없는 인터넷 음원을 정답셋처럼 섞기
- 원본 파일 덮어쓰기
- 파일명만 보고 종 라벨 확정하기
- 세션 정보를 따로 기록하지 않고 파일만 쌓아두기
