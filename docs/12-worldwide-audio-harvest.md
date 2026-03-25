# 전세계 동일 종 음원 수집 규칙

## 목표

- 한국 서식 동일 종의 전세계 공개 음원을 가능한 한 넓게 확보한다.
- 단, 라이선스가 비어 있는 음원은 자동 다운로드 대상에서 제외한다.

## 현재 수집 원칙

- source: iNaturalist
- species scope: 동일 종 기준
- geographic scope: worldwide
- dedupe 1차: `sound_id`
- dedupe 2차: raw file `sha256`

## 이유

- 같은 종이면 해외 음원도 특징 학습에 도움을 줄 수 있다.
- 다만 지역 개체차와 녹음 환경 차이가 있으므로 최종 평가는 한국 현장 데이터로 다시 해야 한다.

## 자동화 흐름

1. `build_inat_full_manifest.py`로 전세계 라이선스 음원 매니페스트 생성
2. `download_manifest_audio.py`로 원본 다운로드
3. `normalize_manifest_audio.ps1`로 공통 포맷 변환
4. `dedupe_manifest_by_hash.py`로 파일 해시 중복 검사

## 주의

- `sound_id`가 달라도 같은 파일이 중복 업로드됐을 수 있다.
- 따라서 수집 후 해시 중복 검사는 별도 단계로 유지한다.
