
      const data = window.DASHBOARD_DATA;
      const relRoot = "../";
      const $ = (id) => document.getElementById(id);
      let currentSamples = data.samples.slice();
      let currentLibraryRows = data.collection.library_rows.slice();
      let currentCacheItems = [];
      let activeLibrarySoundId = null;
      const libraryPredictionCache = new Map();
      const speciesNameMap = Object.fromEntries(
        data.collection.species_stats.map((item) => [item.species_code, item.common_name_ko || item.species_code])
      );

      function formatNumber(value) {
        return Number(value).toLocaleString("ko-KR");
      }

      function formatSeconds(value) {
        return `${Number(value).toLocaleString("ko-KR", { maximumFractionDigits: 2 })} sec`;
      }

      function escapeHtml(value) {
        return String(value ?? "")
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;")
          .replaceAll('"', "&quot;");
      }

      function speciesLabel(item) {
        const common = item.common_name_ko || item.species_code;
        return `${common} (${item.species_code})`;
      }

      function renderHeader() {
        $("title").textContent = data.project.title;
        $("subtitle").textContent = data.project.subtitle;
        $("hero-pills").innerHTML = [
          `<span class="pill">총 ${formatNumber(data.collection.inventory_rows)}개 정규화 파일</span>`,
          `<span class="pill">한국 ${formatNumber(data.collection.korea_rows)}개</span>`,
          `<span class="pill warn">중복 해시 그룹 ${formatNumber(data.collection.duplicate_groups)}</span>`,
          `<span class="pill">총 길이 ${formatSeconds(data.collection.total_duration_sec)}</span>`,
        ].join("");

        const metricGrid = $("metric-grid");
        metricGrid.innerHTML = "";
        [
          ["정규화 파일", formatNumber(data.collection.inventory_rows)],
          ["총 길이", formatSeconds(data.collection.total_duration_sec)],
          ["정확도", data.training.accuracy],
          ["Macro F1", data.training.macro_f1],
        ].forEach(([label, value]) => {
          const card = document.createElement("div");
          card.className = "card metric";
          card.innerHTML = `<div class="metric-value">${value}</div><div class="label">${label}</div>`;
          metricGrid.appendChild(card);
        });
      }

      function renderSpeciesTable() {
        $("species-table").innerHTML = `
          <thead>
            <tr>
              <th>종</th>
              <th>파일 수</th>
              <th>총 길이</th>
              <th>한국</th>
              <th>해외</th>
              <th>F1</th>
            </tr>
          </thead>
          <tbody>
            ${data.collection.species_stats.map((item) => `
              <tr>
                <td>
                  <strong>${escapeHtml(item.common_name_ko || item.species_code)}</strong>
                  <div class="small">${escapeHtml(item.scientific_name || item.species_code)}</div>
                </td>
                <td>${formatNumber(item.file_count)}</td>
                <td>${formatSeconds(item.duration_sec)}</td>
                <td>${formatNumber(item.korea_count)}</td>
                <td>${formatNumber(item.world_only_count)}</td>
                <td>${item.f1_score}</td>
              </tr>
            `).join("")}
          </tbody>
        `;
      }

      function renderTraining() {
        $("training-metrics").innerHTML = `
          <div class="detail-panel"><div class="small">특징 버전</div><div><code>${escapeHtml(data.training.feature_version)}</code></div></div>
          <div class="detail-panel"><div class="small">윈도우 / 홉</div><div>${data.training.window_sec}s / ${data.training.hop_sec}s</div></div>
          <div class="detail-panel"><div class="small">라이선스 수</div><div>${Object.keys(data.collection.licenses).length}종</div></div>
        `;
        $("model-status").innerHTML = data.training.model_status.notes
          .map((item) => `<div class="status-item">${escapeHtml(item)}</div>`)
          .join("");
        $("confusion-list").innerHTML = data.training.top_confusions
          .map((item) => `<li>${escapeHtml(item.true)} -> ${escapeHtml(item.pred)} (${formatNumber(item.count)})</li>`)
          .join("");
        $("confusion-image").src = relRoot + data.assets.confusion_matrix;
        $("f1-image").src = relRoot + data.assets.per_class_f1;
      }

      function renderAndroid() {
        $("screen-pills").innerHTML = data.android.screens
          .map((screen) => `<span class="pill">${escapeHtml(screen.id)}</span>`)
          .join("");
        $("screen-table").innerHTML = `
          <thead>
            <tr><th>화면</th><th>목적</th><th>주요 액션</th></tr>
          </thead>
          <tbody>
            ${data.android.screens.map((screen) => `
              <tr>
                <td>${escapeHtml(screen.id)}</td>
                <td>${escapeHtml(screen.purpose)}</td>
                <td>${escapeHtml(screen.primary_action || "-")}</td>
              </tr>
            `).join("")}
          </tbody>
        `;
        $("android-spec-link").href = relRoot + data.android.spec_path;
      }

      function renderOpsStatus() {
        $("ops-status").innerHTML = `
          <div class="status-item">예측 캐시: <strong>${formatNumber(data.prediction_cache.cache_size || 0)}개</strong> 파일 사전 계산 완료</div>
          <div class="status-item">캐시 정책: 한국 샘플 전체 + 종별 해외 추가 ${escapeHtml(String(data.prediction_cache.selection_policy.extra_world_rows_per_species || 0))}개</div>
          <div class="status-item">건강도 리포트: ${data.dataset_health.path ? `<code>${escapeHtml(data.dataset_health.path)}</code>` : "미생성"}</div>
        `;
        $("duration-bucket-list").innerHTML = Object.entries(data.dataset_health.duration_buckets || {})
          .map(([bucket, count]) => `<li>${escapeHtml(bucket)} / ${formatNumber(count)}</li>`)
          .join("");
        $("quality-list").innerHTML = Object.entries(data.dataset_health.quality || {})
          .map(([quality, count]) => `<li>${escapeHtml(quality)} / ${formatNumber(count)}</li>`)
          .join("");
      }

      function renderOpsQueue() {
        $("ops-queue-grid").innerHTML = (data.ops_queue.queues || []).map((queue) => `
          <div class="detail-panel">
            <div class="pill">우선순위 ${escapeHtml(queue.priority)}</div>
            <h3 style="margin-top:10px;">${escapeHtml(queue.title)}</h3>
            <ul>${(queue.tasks || []).map((task) => `<li>${escapeHtml(task)}</li>`).join("")}</ul>
          </div>
        `).join("");
        $("ops-log-path").innerHTML = data.ops_queue.latest_log_path
          ? `<code>${escapeHtml(data.ops_queue.latest_log_path)}</code>`
          : "아직 장기 실행 로그가 없습니다.";
      }

      async function loadLatestLog() {
        const preview = $("ops-log-preview");
        preview.textContent = "로그를 불러오는 중입니다...";
        try {
          const response = await fetch("/api/latest-log");
          const payload = await response.json();
          if (!response.ok || payload.error) {
            throw new Error(payload.error || "log fetch failed");
          }
          preview.textContent = (payload.tail || []).join("\n");
        } catch (error) {
          preview.textContent = `로그 로드 실패: ${error.message}`;
        }
      }

      function setupCacheFilters() {
        const items = (window.DASHBOARD_DATA.prediction_cache_items || []);
        currentCacheItems = items.slice();
        $("cache-species-filter").innerHTML = `
          <option value="all">종 전체</option>
          ${[...new Set(items.map((item) => item.species_code))].sort().map((species) => `<option value="${species}">${escapeHtml(speciesNameMap[species] || species)} (${species})</option>`).join("")}
        `;
        $("cache-species-filter").addEventListener("change", applyCacheFilters);
        $("cache-region-filter").addEventListener("change", applyCacheFilters);
      }

      function applyCacheFilters() {
        const items = (window.DASHBOARD_DATA.prediction_cache_items || []);
        const species = $("cache-species-filter").value;
        const region = $("cache-region-filter").value;
        currentCacheItems = items.filter((item) => {
          if (species !== "all" && item.species_code !== species) return false;
          if (region !== "all" && String(item.is_korea) !== region) return false;
          return true;
        });
        renderCacheGrid();
      }

      function renderCacheGrid() {
        const grid = $("cache-grid");
        if (!currentCacheItems.length) {
          grid.innerHTML = `<div class="empty">조건에 맞는 캐시 예측이 없습니다.</div>`;
          return;
        }
        grid.innerHTML = currentCacheItems.map((item) => `
          <div class="sample-card">
            <div>${String(item.is_korea) === "true" ? '<span class="pill">한국</span>' : '<span class="pill warn">해외</span>'}<span class="pill">${escapeHtml(item.species_code)}</span></div>
            <h3>${escapeHtml(item.common_name_ko || item.species_code)}</h3>
            <div class="small">sound ${escapeHtml(item.sound_id)} / obs ${escapeHtml(item.observation_id)}</div>
            <div class="small">${escapeHtml(item.license_code)} / ${formatSeconds(item.duration_sec)}</div>
            <audio controls preload="none" src="../dashboard/assets/preview_clips/${escapeHtml(item.species_code)}_sound${escapeHtml(item.sound_id)}_preview.mp3"></audio>
            <div class="detail-panel" style="margin-top:12px;">
              <div class="small">Cached top 3</div>
              <ul>${(item.aggregate_ranking || []).slice(0, 3).map((row) => `<li>${escapeHtml(row.label)} / prob ${row.mean_probability.toFixed(4)} / votes ${row.vote_count}</li>`).join("")}</ul>
            </div>
          </div>
        `).join("");
      }

      function renderKoreaSection() {
        $("korea-summary-list").innerHTML = `
          <li>한국 샘플 수: <strong>${formatNumber(data.korea_subset.row_count || 0)}</strong></li>
          <li>한국 샘플 리포트: ${data.korea_subset.path ? `<code>${escapeHtml(data.korea_subset.path)}</code>` : "미생성"}</li>
          <li>종별 분포: ${Object.entries(data.korea_subset.species_counts || {}).map(([k, v]) => `${escapeHtml(k)} ${formatNumber(v)}`).join(" / ")}</li>
        `;
        $("korea-prediction-list").innerHTML = `
          <li>캐시 한국 샘플 수: <strong>${formatNumber(data.korea_prediction.korea_items || 0)}</strong></li>
          <li>캐시 top1 정확도: <strong>${escapeHtml(data.korea_prediction.top1_accuracy_over_cached_korea_items || 0)}</strong></li>
          <li>리포트 경로: ${data.korea_prediction.path ? `<code>${escapeHtml(data.korea_prediction.path)}</code>` : "미생성"}</li>
        `;
        $("korea-confusion-list").innerHTML = (data.korea_prediction.top_confusions || [])
          .slice(0, 10)
          .map((row) => `<li>${escapeHtml(row.true)} -> ${escapeHtml(row.pred)} (${formatNumber(row.count)})</li>`)
          .join("");
      }

      function renderTrainingProof() {
        const summary = data.training.proof.dataset_summary;
        const cv = data.training.proof.cross_validation;
        $("proof-summary-list").innerHTML = `
          <li>특성 행 수: <strong>${formatNumber(summary.num_feature_rows)}</strong></li>
          <li>그룹 수: <strong>${formatNumber(summary.num_groups)}</strong></li>
          <li>클래스 수: <strong>${formatNumber(summary.classes.length)}</strong></li>
          <li>특성 버전: <code>${escapeHtml(summary.feature_version)}</code></li>
          <li>윈도우 / 홉: ${summary.window_sec}s / ${summary.hop_sec}s</li>
        `;
        $("proof-cv-list").innerHTML = `
          <li>교차검증 전략: <code>${escapeHtml(cv.strategy)}</code></li>
          <li>폴드 수: <strong>${formatNumber(cv.num_folds)}</strong></li>
          <li>모델 파일과 리포트 파일은 별도 아티팩트로 저장되어 있습니다.</li>
          <li>대시보드 즉석 예측은 이 저장된 모델 파일을 다시 읽어서 실행합니다.</li>
        `;
        const artifacts = data.training.proof.artifacts;
        $("proof-artifact-table").innerHTML = `
          <thead>
            <tr>
              <th>아티팩트</th>
              <th>경로</th>
              <th>크기(bytes)</th>
              <th>sha256</th>
            </tr>
          </thead>
          <tbody>
            ${Object.entries(artifacts).map(([name, info]) => `
              <tr>
                <td><strong>${escapeHtml(name)}</strong></td>
                <td><code>${escapeHtml(info.path)}</code></td>
                <td>${formatNumber(info.size_bytes)}</td>
                <td><code>${escapeHtml(info.sha256.slice(0, 16))}...</code></td>
              </tr>
            `).join("")}
          </tbody>
        `;
      }

      function renderPaths() {
        $("path-list").innerHTML = Object.entries(data.paths)
          .map(([key, value]) => `<li><strong>${escapeHtml(key)}</strong><br><code>${escapeHtml(value)}</code></li>`)
          .join("");
        $("inventory-link").href = relRoot + data.paths.inventory;
        $("report-link").href = relRoot + data.paths.report;
        $("model-link").href = relRoot + data.paths.model;
      }

      function buildSampleCard(sample) {
        const top3 = sample.top3
          .map((item) => `${item.label} ${item.mean_probability.toFixed(3)}`)
          .join(" / ");
        const regionPill = String(sample.is_korea) === "true"
          ? '<span class="pill">한국</span>'
          : '<span class="pill warn">해외</span>';
        const imageSrc = sample.spectrogram_path ? `../${sample.spectrogram_path}` : "";
        const audioSrc = sample.preview_audio_path ? `../${sample.preview_audio_path}` : (relRoot + sample.audio_path);
        return `
          <div class="sample-card">
            <div>${regionPill}<span class="pill">${escapeHtml(sample.species_code)}</span></div>
            <h3>${escapeHtml(sample.common_name_ko || sample.species_code)}</h3>
            <div class="small">sound ${escapeHtml(sample.sound_id)} / obs ${escapeHtml(sample.observation_id)}</div>
            <div class="small">${escapeHtml(sample.license_code)} / ${formatSeconds(sample.duration_sec)}</div>
            ${sample.spectrogram_path ? `<img src="${imageSrc}" alt="spectrogram" />` : ""}
            <audio controls preload="none" src="${audioSrc}"></audio>
            <div class="small" style="margin-top:8px;">top1 ${escapeHtml(sample.top_prediction.label)} (${sample.top_prediction.mean_probability.toFixed(4)})</div>
            <div class="small">top3 ${escapeHtml(top3)}</div>
            <div class="actions">
              <button type="button" onclick="window.selectSampleBySoundId('${escapeHtml(sample.sound_id)}')">상세 보기</button>
              <a class="link-button secondary" target="_blank" rel="noreferrer" href="${relRoot + sample.audio_path}">정규화 wav</a>
              <a class="link-button secondary" target="_blank" rel="noreferrer" href="${relRoot + sample.raw_audio_path}">원본</a>
            </div>
          </div>
        `;
      }

      function renderSelectedSample(sample) {
        const image = sample.spectrogram_path
          ? `<img class="selected-image" src="../${sample.spectrogram_path}" alt="selected spectrogram" />`
          : "";
        const audioSrc = sample.preview_audio_path ? `../${sample.preview_audio_path}` : (relRoot + sample.audio_path);
        $("selected-sample").innerHTML = `
          <div>${String(sample.is_korea) === "true" ? '<span class="pill">한국 샘플</span>' : '<span class="pill warn">해외 샘플</span>'}</div>
          <h3 style="margin-top:10px;">${escapeHtml(sample.common_name_ko || sample.species_code)}</h3>
          <p style="margin-top:8px;">${escapeHtml(sample.place_guess || "장소 정보 없음")}</p>
          ${image}
          <audio controls preload="metadata" src="${audioSrc}"></audio>
          <div class="grid two" style="margin-top:12px;">
            <div class="detail-panel">
              <div class="small">Top prediction</div>
              <div><strong>${escapeHtml(sample.top_prediction.label)}</strong> (${sample.top_prediction.mean_probability.toFixed(4)})</div>
              <div class="small" style="margin-top:8px;">Top 3</div>
              <ul>
                ${sample.top3.map((item) => `<li>${escapeHtml(item.label)} / prob ${item.mean_probability.toFixed(4)} / votes ${item.vote_count}</li>`).join("")}
              </ul>
            </div>
            <div class="detail-panel">
              <div class="small">Metadata</div>
              <ul>
                <li>sound id: <code>${escapeHtml(sample.sound_id)}</code></li>
                <li>observation id: <code>${escapeHtml(sample.observation_id)}</code></li>
                <li>license: <code>${escapeHtml(sample.license_code)}</code></li>
                <li>duration: ${formatSeconds(sample.duration_sec)}</li>
                <li>region: ${String(sample.is_korea) === "true" ? "Korea" : "World"}</li>
              </ul>
              <div class="actions">
                <a class="link-button secondary" target="_blank" rel="noreferrer" href="${relRoot + sample.audio_path}">정규화 wav</a>
                <a class="link-button secondary" target="_blank" rel="noreferrer" href="${relRoot + sample.raw_audio_path}">원본</a>
              </div>
            </div>
          </div>
        `;
      }

      function setupSampleFilters() {
        $("species-filter").innerHTML = `
          <option value="all">종 전체</option>
          ${[...new Set(data.samples.map((sample) => sample.species_code))].sort().map((species) => `<option value="${species}">${escapeHtml(speciesNameMap[species] || species)} (${species})</option>`).join("")}
        `;
        $("species-filter").addEventListener("change", applySampleFilters);
        $("region-filter").addEventListener("change", applySampleFilters);
        $("search-input").addEventListener("input", applySampleFilters);
      }

      function applySampleFilters() {
        const species = $("species-filter").value;
        const region = $("region-filter").value;
        const query = $("search-input").value.trim().toLowerCase();
        currentSamples = data.samples.filter((sample) => {
          if (species !== "all" && sample.species_code !== species) return false;
          if (region !== "all" && String(sample.is_korea) !== region) return false;
          if (!query) return true;
          const haystack = [
            sample.species_code,
            sample.common_name_ko,
            sample.sound_id,
            sample.observation_id,
            sample.place_guess,
            sample.license_code,
          ].join(" ").toLowerCase();
          return haystack.includes(query);
        });
        renderSampleGrid();
      }

      function renderSampleGrid() {
        const grid = $("sample-grid");
        if (currentSamples.length === 0) {
          grid.innerHTML = `<div class="empty">조건에 맞는 대표 샘플이 없습니다.</div>`;
          $("selected-sample").innerHTML = `<div class="empty">왼쪽에서 샘플을 먼저 선택해 주세요.</div>`;
          return;
        }
        grid.innerHTML = currentSamples.map(buildSampleCard).join("");
        renderSelectedSample(currentSamples[0]);
      }

      function setupLibraryFilters() {
        $("library-species-filter").innerHTML = `
          <option value="all">종 전체</option>
          ${[...new Set(data.collection.library_rows.map((row) => row.species_code))].sort().map((species) => `<option value="${species}">${escapeHtml(speciesNameMap[species] || species)} (${species})</option>`).join("")}
        `;
        $("library-license-filter").innerHTML = `
          <option value="all">라이선스 전체</option>
          ${Object.keys(data.collection.licenses).sort().map((licenseCode) => `<option value="${licenseCode}">${licenseCode}</option>`).join("")}
        `;
        $("library-quality-filter").innerHTML = `
          <option value="all">품질 전체</option>
          ${[...new Set(data.collection.library_rows.map((row) => row.quality_grade || "unknown"))].sort().map((quality) => `<option value="${quality}">${escapeHtml(quality)}</option>`).join("")}
        `;
        $("library-species-filter").addEventListener("change", applyLibraryFilters);
        $("library-region-filter").addEventListener("change", applyLibraryFilters);
        $("library-license-filter").addEventListener("change", applyLibraryFilters);
        $("library-quality-filter").addEventListener("change", applyLibraryFilters);
        $("library-search-input").addEventListener("input", applyLibraryFilters);
      }

      function applyLibraryFilters() {
        const species = $("library-species-filter").value;
        const region = $("library-region-filter").value;
        const licenseCode = $("library-license-filter").value;
        const quality = $("library-quality-filter").value;
        const query = $("library-search-input").value.trim().toLowerCase();

        currentLibraryRows = data.collection.library_rows.filter((row) => {
          if (species !== "all" && row.species_code !== species) return false;
          if (region !== "all" && String(row.is_korea) !== region) return false;
          if (licenseCode !== "all" && row.license_code !== licenseCode) return false;
          if (quality !== "all" && String(row.quality_grade || "unknown") !== quality) return false;
          if (!query) return true;
          const haystack = [
            row.species_code,
            row.common_name_ko,
            row.scientific_name,
            row.sound_id,
            row.observation_id,
            row.place_guess,
            row.license_code,
          ].join(" ").toLowerCase();
          return haystack.includes(query);
        });
        $("library-summary").textContent = `현재 ${formatNumber(currentLibraryRows.length)}개 파일 표시 중, 상단 테이블은 최대 250개까지만 렌더링합니다.`;
        renderLibraryTable();
      }

      function renderLibraryTable() {
        const visibleRows = currentLibraryRows.slice(0, 250);
        $("library-table").innerHTML = `
          <thead>
            <tr>
              <th>종</th>
              <th>sound id</th>
              <th>길이</th>
              <th>지역</th>
              <th>라이선스</th>
              <th>장소</th>
            </tr>
          </thead>
          <tbody>
            ${visibleRows.map((row) => `
              <tr data-sound-id="${escapeHtml(row.sound_id)}" class="${String(row.sound_id) === String(activeLibrarySoundId) ? "active" : ""}" onclick="window.selectLibraryRowBySoundId('${escapeHtml(row.sound_id)}')">
                <td><strong>${escapeHtml(row.common_name_ko || row.species_code)}</strong><div class="small">${escapeHtml(row.species_code)}</div></td>
                <td><code>${escapeHtml(row.sound_id)}</code></td>
                <td>${formatSeconds(row.duration_sec)}</td>
                <td>${String(row.is_korea) === "true" ? "한국" : "해외"}</td>
                <td>${escapeHtml(row.license_code)}</td>
                <td>${escapeHtml(row.place_guess || "-")}</td>
              </tr>
            `).join("")}
          </tbody>
        `;

        if (currentLibraryRows.length === 0) {
          $("library-detail").innerHTML = `<div class="empty">조건에 맞는 라이브러리 파일이 없습니다.</div>`;
          return;
        }
        const selected = currentLibraryRows.find((row) => String(row.sound_id) === String(activeLibrarySoundId)) || currentLibraryRows[0];
        activeLibrarySoundId = selected.sound_id;
        renderLibraryDetail(selected);
      }

      function renderLibraryDetail(row) {
        const sampleMatch = data.samples.find((sample) => String(sample.sound_id) === String(row.sound_id));
        const cachedPrediction = libraryPredictionCache.get(String(row.sound_id));
        const top3 = sampleMatch
          ? `<div class="detail-panel" style="margin-top:12px;">
              <div class="small">대표 샘플 예측 결과</div>
              <ul>${sampleMatch.top3.map((item) => `<li>${escapeHtml(item.label)} / prob ${item.mean_probability.toFixed(4)} / votes ${item.vote_count}</li>`).join("")}</ul>
            </div>`
          : `<div class="detail-panel" style="margin-top:12px;"><div class="small">예측 결과</div><div>이 항목은 아직 대표 샘플 세트에 포함되지 않았습니다.</div></div>`;

        const image = row.spectrogram_path
          ? `<img class="selected-image" src="../${row.spectrogram_path}" alt="library spectrogram" />`
          : `<div class="detail-panel" style="margin-top:12px;">스펙트로그램 자산은 대표 샘플만 생성되어 있습니다.</div>`;

        const audioSrc = row.preview_audio_path ? `../${row.preview_audio_path}` : (relRoot + row.audio_path);
        $("library-detail").innerHTML = `
          <div>${String(row.is_korea) === "true" ? '<span class="pill">한국</span>' : '<span class="pill warn">해외</span>'}<span class="pill">${escapeHtml(row.species_code)}</span></div>
          <h3 style="margin-top:10px;">${escapeHtml(speciesLabel(row))}</h3>
          <p>${escapeHtml(row.place_guess || "장소 정보 없음")}</p>
          ${image}
          <audio controls preload="metadata" src="${audioSrc}"></audio>
          <div class="actions">
            <a class="link-button secondary" target="_blank" rel="noreferrer" href="${relRoot + row.audio_path}">정규화 wav</a>
            <a class="link-button secondary" target="_blank" rel="noreferrer" href="${relRoot + row.raw_audio_path}">원본 파일</a>
            <button type="button" onclick="window.predictLibraryBySoundId('${escapeHtml(row.sound_id)}')">이 파일 다시 예측</button>
          </div>
          <div class="detail-panel" style="margin-top:12px;">
            <div class="small">Metadata</div>
            <ul>
              <li>scientific name: <code>${escapeHtml(row.scientific_name || "-")}</code></li>
              <li>sound id: <code>${escapeHtml(row.sound_id)}</code></li>
              <li>observation id: <code>${escapeHtml(row.observation_id)}</code></li>
              <li>license: <code>${escapeHtml(row.license_code)}</code></li>
              <li>duration: ${formatSeconds(row.duration_sec)}</li>
            </ul>
          </div>
          <div class="detail-panel" id="library-predict-panel" style="margin-top:12px;">
            ${cachedPrediction ? renderPredictionPanelHtml(cachedPrediction, "라이브러리 즉석 예측") : '<div class="small">라이브러리 즉석 예측</div><div>아직 실행 전입니다. 버튼을 눌러 현재 baseline으로 다시 예측할 수 있습니다.</div>'}
          </div>
          ${top3}
        `;
      }

      function renderPredictionPanelHtml(payload, title) {
        const ranking = payload.aggregate_ranking || [];
        const windowRows = payload.window_predictions || [];
        return `
          <div class="small">${escapeHtml(title)}</div>
          <div style="margin-top:8px;"><strong>${escapeHtml((ranking[0] && ranking[0].label) || "-")}</strong>${ranking[0] ? ` (${ranking[0].mean_probability.toFixed(4)})` : ""}</div>
          <div class="small" style="margin-top:8px;">길이 / 윈도우 수</div>
          <div>${formatSeconds(payload.duration_sec)} / ${formatNumber(payload.num_windows || 0)}개</div>
          <div class="detail-panel" style="margin-top:12px;">
            <div class="small">Aggregate ranking</div>
            <ul>${ranking.slice(0, 5).map((item) => `<li>${escapeHtml(item.label)} / prob ${item.mean_probability.toFixed(4)} / votes ${item.vote_count}</li>`).join("")}</ul>
          </div>
          <div class="detail-panel" style="margin-top:12px;">
            <div class="small">Window predictions</div>
            <ul>${windowRows.slice(0, 10).map((item) => `<li>${item.start_sec}-${item.end_sec}s / ${escapeHtml(item.top_label)} / ${item.top_probability.toFixed(4)}</li>`).join("")}</ul>
          </div>
        `;
      }

      async function runUploadPrediction() {
        const fileInput = $("upload-audio-input");
        const status = $("upload-predict-status");
        const resultBox = $("upload-predict-result");
        const file = fileInput.files && fileInput.files[0];

        if (!file) {
          status.textContent = "예측할 오디오 파일을 먼저 선택해 주세요.";
          resultBox.innerHTML = `<div class="empty">선택된 파일이 없습니다.</div>`;
          return;
        }

        status.textContent = `업로드 및 예측 중: ${file.name}`;
        resultBox.innerHTML = `<div class="empty">예측을 실행하고 있습니다...</div>`;

        const formData = new FormData();
        formData.append("audio", file);

        try {
          const response = await fetch("/api/predict", {
            method: "POST",
            body: formData,
          });
          const payload = await response.json();
          if (!response.ok || payload.error) {
            throw new Error(payload.error || "prediction failed");
          }

          status.textContent = `예측 완료: ${payload.uploaded_name}`;
          const ranking = payload.aggregate_ranking || [];
          resultBox.innerHTML = `
            <div class="small">업로드 파일</div>
            <div><strong>${escapeHtml(payload.uploaded_name)}</strong></div>
            <div style="margin-top:12px;">${renderPredictionPanelHtml(payload, "업로드 파일 예측")}</div>
          `;
        } catch (error) {
          status.textContent = `예측 실패: ${error.message}`;
          resultBox.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
        }
      }

      async function runLibraryPrediction(row) {
        const panel = $("library-predict-panel");
        panel.innerHTML = `<div class="small">라이브러리 즉석 예측</div><div>예측을 실행하고 있습니다...</div>`;
        try {
          const response = await fetch("/api/predict-path", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ audio_path: row.audio_path }),
          });
          const payload = await response.json();
          if (!response.ok || payload.error) {
            throw new Error(payload.error || "prediction failed");
          }
          libraryPredictionCache.set(String(row.sound_id), payload);
          panel.innerHTML = renderPredictionPanelHtml(payload, "라이브러리 즉석 예측");
        } catch (error) {
          panel.innerHTML = `<div class="small">라이브러리 즉석 예측</div><div class="empty">${escapeHtml(error.message)}</div>`;
        }
      }

      window.selectSampleBySoundId = function selectSampleBySoundId(soundId) {
        const sample = currentSamples.find((item) => String(item.sound_id) === String(soundId));
        if (sample) {
          renderSelectedSample(sample);
        }
      };

      window.selectLibraryRowBySoundId = function selectLibraryRowBySoundId(soundId) {
        const row = currentLibraryRows.find((item) => String(item.sound_id) === String(soundId));
        if (row) {
          activeLibrarySoundId = row.sound_id;
          renderLibraryDetail(row);
          renderLibraryTable();
        }
      };

      window.predictLibraryBySoundId = function predictLibraryBySoundId(soundId) {
        const row = currentLibraryRows.find((item) => String(item.sound_id) === String(soundId));
        if (row) {
          runLibraryPrediction(row);
        }
      };

      renderHeader();
      renderSpeciesTable();
      renderTraining();
      renderTrainingProof();
      renderOpsStatus();
      renderOpsQueue();
      loadLatestLog();
      renderAndroid();
      renderPaths();
      setupSampleFilters();
      applySampleFilters();
      setupLibraryFilters();
      applyLibraryFilters();
      setupCacheFilters();
      applyCacheFilters();
      renderKoreaSection();
      $("upload-predict-button").addEventListener("click", runUploadPrediction);
    