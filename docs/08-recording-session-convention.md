# 녹음 세션 명명 규칙

## session_id 형식

- 기본 형식: `{species_code}_{yyyymmdd}_{location_code}_{sequence}`
- 예시: `chammaemi_20260803_seoulforest_001`

## species_code

- `chammaemi`
- `malmaemi`
- `yujimaemi`
- `unknown`

## location_code 규칙

- 영문 소문자 사용
- 공백 대신 `_`
- 너무 길면 핵심 지명만 남김

## sequence 규칙

- 같은 날짜와 같은 장소에서 같은 종을 여러 세션으로 녹음하면 `001`, `002`, `003` 순으로 증가

## 권장 파일 배치

- `data-workspace/raw_audio/field_sessions/{species_code}/{session_id}/`
- 한 세션 폴더 안에 들어갈 것
  - 원본 오디오
  - 현장 사진
  - 검수 메모 초안

## 목적

- 파일명만 보고도 종, 날짜, 장소의 최소 맥락을 알 수 있게 한다.
- 메타데이터 CSV의 `session_id`와 파일 구조를 쉽게 맞춘다.
