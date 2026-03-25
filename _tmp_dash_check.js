
    const data = window.DASHBOARD_DATA;
    const $ = (id) => document.getElementById(id);
    const relRoot = "../";
    let currentSamples = data.samples.slice();
    let currentRows = data.collection.library_rows.slice();
    let activeSoundId = null;

    function esc(v){return String(v ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");}
    function n(v){return Number(v || 0).toLocaleString("ko-KR");}
    function secs(v){return `${Number(v || 0).toLocaleString("ko-KR",{maximumFractionDigits:2})} sec`;}
    function sampleAudio(s){return s.preview_audio_path ? `../${s.preview_audio_path}` : `${relRoot}${s.audio_path}`;}
    function rowAudio(r){return r.preview_audio_path ? `../${r.preview_audio_path}` : `${relRoot}${r.audio_path}`;}

    function renderTop() {
      $("title").textContent = data.project.title;
      $("subtitle").textContent = data.project.subtitle;
      $("top-metrics").innerHTML = [
        ["정규화 파일", n(data.collection.inventory_rows)],
        ["정확도", data.training.accuracy],
        ["Macro F1", data.training.macro_f1],
        ["예측 캐시", n(data.prediction_cache.cache_size)]
      ].map(([k,v]) => `<div class="detail"><div class="small">${esc(k)}</div><div style="font-size:28px;font-weight:800">${esc(v)}</div></div>`).join("");
    }

    function renderProof() {
      const p = data.training.proof;
      $("proof-list").innerHTML = `
        <li>특성 행 수: <strong>${n(p.dataset_summary.num_feature_rows)}</strong></li>
        <li>교차검증: <code>${esc(p.cross_validation.strategy)}</code></li>
        <li>폴드 수: <strong>${n(p.cross_validation.num_folds)}</strong></li>
        <li>모델 파일: <code>${esc(p.artifacts.model.path)}</code></li>
        <li>모델 해시: <code>${esc(p.artifacts.model.sha256.slice(0,16))}...</code></li>
        <li>리포트 파일: <code>${esc(p.artifacts.report.path)}</code></li>
      `;
    }

    async function renderLog() {
      $("log-path").textContent = data.ops_queue.latest_log_path || "로그 없음";
      try {
        const r = await fetch("/api/latest-log");
        const j = await r.json();
        $("log-preview").textContent = (j.tail || []).join("\n");
      } catch {
        $("log-preview").textContent = "로그를 읽지 못했습니다.";
      }
    }

    function buildSampleCard(s) {
      const top3 = (s.top3 || []).map((x) => `${x.label} ${x.mean_probability.toFixed(3)}`).join(" / ");
      const img = s.spectrogram_path ? `<img src="../${s.spectrogram_path}" alt="spectrogram" />` : "";
      return `
        <div class="sample">
          <div>${String(s.is_korea)==="true" ? '<span class="pill">한국</span>' : '<span class="pill warn">해외</span>'}<span class="pill">${esc(s.species_code)}</span></div>
          <h3>${esc(s.common_name_ko || s.species_code)}</h3>
          <div class="small">sound ${esc(s.sound_id)} / obs ${esc(s.observation_id)}</div>
          <div class="small">${esc(s.license_code)} / ${secs(s.duration_sec)}</div>
          <details>
            <summary>음원 재생</summary>
            <div>
              ${img}
              <audio controls preload="none" src="${sampleAudio(s)}"></audio>
            </div>
          </details>
          <details>
            <summary>예측 요약</summary>
            <div>
              <div class="small">top1 ${esc(s.top_prediction.label)} (${s.top_prediction.mean_probability.toFixed(4)})</div>
              <div class="small">top3 ${esc(top3)}</div>
            </div>
          </details>
          <div class="actions" style="margin-top:10px">
            <button type="button" onclick="window.selectSample('${esc(s.sound_id)}')">상세 보기</button>
          </div>
        </div>
      `;
    }

    function renderSelectedSample(s) {
      const img = s.spectrogram_path ? `<img src="../${s.spectrogram_path}" alt="selected spectrogram" />` : "";
      $("selected-sample").innerHTML = `
        <div>${String(s.is_korea)==="true" ? '<span class="pill">한국 샘플</span>' : '<span class="pill warn">해외 샘플</span>'}</div>
        <h3 style="margin-top:10px">${esc(s.common_name_ko || s.species_code)}</h3>
        <div class="small">${esc(s.place_guess || "장소 정보 없음")}</div>
        <details open>
          <summary>음원 재생</summary>
          <div>
            ${img}
            <audio controls preload="metadata" src="${sampleAudio(s)}"></audio>
          </div>
        </details>
        <details open>
          <summary>예측 상세</summary>
          <div>
            <ul>${(s.top3 || []).map((x) => `<li>${esc(x.label)} / prob ${x.mean_probability.toFixed(4)} / votes ${x.vote_count}</li>`).join("")}</ul>
          </div>
        </details>
      `;
    }

    function applySampleFilters() {
      const species = $("species-filter").value;
      const region = $("region-filter").value;
      const q = $("search-input").value.trim().toLowerCase();
      currentSamples = data.samples.filter((s) => {
        if (species !== "all" && s.species_code !== species) return false;
        if (region !== "all" && String(s.is_korea) !== region) return false;
        if (!q) return true;
        return [s.species_code, s.common_name_ko, s.sound_id, s.place_guess].join(" ").toLowerCase().includes(q);
      });
      $("sample-grid").innerHTML = currentSamples.length ? currentSamples.map(buildSampleCard).join("") : `<div class="empty">조건에 맞는 샘플이 없습니다.</div>`;
      $("selected-sample").innerHTML = currentSamples.length ? "" : `<div class="empty">샘플 없음</div>`;
      if (currentSamples.length) renderSelectedSample(currentSamples[0]);
    }

    function applyLibraryFilters() {
      const species = $("library-species-filter").value;
      const q = $("library-search-input").value.trim().toLowerCase();
      currentRows = data.collection.library_rows.filter((r) => {
        if (species !== "all" && r.species_code !== species) return false;
        if (!q) return true;
        return [r.species_code, r.common_name_ko, r.sound_id, r.place_guess].join(" ").toLowerCase().includes(q);
      });
      $("library-summary").textContent = `현재 ${n(currentRows.length)}개 파일 표시 중, 테이블은 최대 250개까지 보여줍니다.`;
      renderLibraryTable();
    }

    function renderLibraryTable() {
      const visible = currentRows.slice(0,250);
      $("library-table").innerHTML = `
        <thead><tr><th>종</th><th>sound id</th><th>길이</th><th>지역</th><th>장소</th></tr></thead>
        <tbody>
          ${visible.map((r) => `
            <tr class="${String(r.sound_id)===String(activeSoundId) ? "active" : ""}" onclick="window.selectRow('${esc(r.sound_id)}')">
              <td><strong>${esc(r.common_name_ko || r.species_code)}</strong><div class="small">${esc(r.species_code)}</div></td>
              <td><code>${esc(r.sound_id)}</code></td>
              <td>${secs(r.duration_sec)}</td>
              <td>${String(r.is_korea)==="true" ? "한국" : "해외"}</td>
              <td>${esc(r.place_guess || "-")}</td>
            </tr>`).join("")}
        </tbody>`;
      if (!currentRows.length) {
        $("library-detail").innerHTML = `<div class="empty">조건에 맞는 파일이 없습니다.</div>`;
        return;
      }
      const selected = currentRows.find((r) => String(r.sound_id) === String(activeSoundId)) || currentRows[0];
      activeSoundId = selected.sound_id;
      renderLibraryDetail(selected);
    }

    function renderPredictionBlock(p) {
      return `
        <details open>
          <summary>즉석 예측</summary>
          <div>
            <ul>${(p.aggregate_ranking || []).slice(0,5).map((x) => `<li>${esc(x.label)} / prob ${x.mean_probability.toFixed(4)} / votes ${x.vote_count}</li>`).join("")}</ul>
          </div>
        </details>
      `;
    }

    function renderLibraryDetail(r) {
      const cached = libraryPredictionCache.get(String(r.sound_id));
      const sample = data.samples.find((s) => String(s.sound_id) === String(r.sound_id));
      const img = r.spectrogram_path ? `<img src="../${r.spectrogram_path}" alt="library spectrogram" />` : "";
      $("library-detail").innerHTML = `
        <div>${String(r.is_korea)==="true" ? '<span class="pill">한국</span>' : '<span class="pill warn">해외</span>'}<span class="pill">${esc(r.species_code)}</span></div>
        <h3 style="margin-top:10px">${esc(speciesLabel(r))}</h3>
        <div class="small">${esc(r.place_guess || "장소 정보 없음")}</div>
        <details open>
          <summary>음원 재생</summary>
          <div>
            ${img}
            <audio controls preload="metadata" src="${rowAudio(r)}"></audio>
          </div>
        </details>
        <div class="actions" style="margin-top:10px">
          <button type="button" onclick="window.predictRow('${esc(r.sound_id)}')">이 파일 다시 예측</button>
          <a class="link" target="_blank" rel="noreferrer" href="${relRoot + r.audio_path}">정규화 wav</a>
          <a class="link" target="_blank" rel="noreferrer" href="${relRoot + r.raw_audio_path}">원본 파일</a>
        </div>
        <details>
          <summary>메타데이터</summary>
          <div>
            <ul>
              <li>scientific name: <code>${esc(r.scientific_name || "-")}</code></li>
              <li>sound id: <code>${esc(r.sound_id)}</code></li>
              <li>observation id: <code>${esc(r.observation_id)}</code></li>
              <li>license: <code>${esc(r.license_code)}</code></li>
            </ul>
          </div>
        </details>
        ${cached ? renderPredictionBlock(cached) : `<div class="detail" style="margin-top:12px">아직 즉석 예측 전입니다.</div>`}
        ${sample ? `<details><summary>대표 샘플 top3</summary><div><ul>${sample.top3.map((x) => `<li>${esc(x.label)} / prob ${x.mean_probability.toFixed(4)} / votes ${x.vote_count}</li>`).join("")}</ul></div></details>` : ""}
      `;
    }

    async function runPredictRow(r) {
      try {
        const res = await fetch("/api/predict-path", {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({audio_path: r.audio_path})
        });
        const payload = await res.json();
        if (!res.ok || payload.error) throw new Error(payload.error || "prediction failed");
        libraryPredictionCache.set(String(r.sound_id), payload);
        renderLibraryDetail(r);
      } catch (e) {
        $("library-detail").insertAdjacentHTML("beforeend", `<div class="detail" style="margin-top:12px">예측 실패: ${esc(e.message)}</div>`);
      }
    }

    async function runUploadPrediction() {
      const file = $("upload-audio-input").files && $("upload-audio-input").files[0];
      if (!file) {
        $("upload-predict-status").textContent = "파일을 먼저 선택해 주세요.";
        return;
      }
      $("upload-predict-status").textContent = `예측 중: ${file.name}`;
      const fd = new FormData();
      fd.append("audio", file);
      try {
        const res = await fetch("/api/predict", {method:"POST", body:fd});
        const payload = await res.json();
        if (!res.ok || payload.error) throw new Error(payload.error || "prediction failed");
        $("upload-predict-status").textContent = `예측 완료: ${payload.uploaded_name}`;
        $("upload-predict-result").innerHTML = renderPredictionBlock(payload);
      } catch (e) {
        $("upload-predict-status").textContent = `예측 실패: ${e.message}`;
      }
    }

    window.selectSample = function(soundId) {
      const sample = currentSamples.find((s) => String(s.sound_id) === String(soundId));
      if (sample) renderSelectedSample(sample);
    };

    window.selectRow = function(soundId) {
      const row = currentRows.find((r) => String(r.sound_id) === String(soundId));
      if (!row) return;
      activeSoundId = row.sound_id;
      renderLibraryDetail(row);
      renderLibraryTable();
    };

    window.predictRow = function(soundId) {
      const row = currentRows.find((r) => String(r.sound_id) === String(soundId));
      if (row) runPredictRow(row);
    };

    $("species-filter").innerHTML = `<option value="all">종 전체</option>` +
      [...new Set(data.samples.map((s) => s.species_code))].sort().map((v) => `<option value="${v}">${esc(speciesNameMap[v] || v)} (${v})</option>`).join("");
    $("library-species-filter").innerHTML = `<option value="all">종 전체</option>` +
      [...new Set(data.collection.library_rows.map((r) => r.species_code))].sort().map((v) => `<option value="${v}">${esc(speciesNameMap[v] || v)} (${v})</option>`).join("");
    $("species-filter").addEventListener("change", applySampleFilters);
    $("region-filter").addEventListener("change", applySampleFilters);
    $("search-input").addEventListener("input", applySampleFilters);
    $("library-species-filter").addEventListener("change", applyLibraryFilters);
    $("library-search-input").addEventListener("input", applyLibraryFilters);
    $("upload-predict-button").addEventListener("click", runUploadPrediction);

    renderTop();
    renderSpeciesTable();
    renderTraining();
    renderTrainingProof();
    renderOpsStatus();
    renderProof();
    applySampleFilters();
    applyLibraryFilters();
    renderLog();
  