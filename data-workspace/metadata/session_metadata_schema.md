# 세션 메타데이터 스키마

## 필드 설명

- `session_id`: 세션 고유 ID
- `recorded_at`: 녹음 시작 시각, ISO 8601
- `location_name`: 사람이 읽을 수 있는 장소명
- `latitude`, `longitude`: 좌표
- `device_model`: 녹음한 기기명
- `distance_estimate_m`: 울음 근원과의 대략적 거리
- `habitat_type`: 예: `urban_park`, `street_tree`, `forest_edge`
- `background_noise`: 세미콜론 구분 메모
- `weather_note`: 날씨 메모
- `species_label`: 내부 코드값
- `label_confidence`: `confirmed`, `probable`, `uncertain`
- `label_evidence`: `adult_photo`, `exuvia_photo`, `expert_verified`, `repeated_field_observation`
- `mixture_flag`: `single_species`, `possible_multiple_species`, `no_cicada_detected`
- `acoustic_quality`: `good`, `fair`, `poor`
- `notes`: 자유 메모
- `raw_audio_path`: 원본 파일 경로
- `derived_audio_path`: 파생 파일 경로
- `review_status`: `pending`, `approved`, `needs_revision`, `rejected`
- `reviewer`: 검수자 식별값

## species_label 코드

- `chammaemi`
- `malmaemi`
- `yujimaemi`
- `unknown`
