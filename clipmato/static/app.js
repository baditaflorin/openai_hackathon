document.addEventListener("DOMContentLoaded", () => {
  const STAGE_INFO = {
    uploading: { label: "Uploading", percent: 10 },
    transcribing: { label: "Transcribing", percent: 20 },
    descriptions: { label: "Writing descriptions", percent: 30 },
    entities: { label: "Extracting entities", percent: 40 },
    titles: { label: "Generating titles", percent: 50 },
    script: { label: "Building script", percent: 60 },
    remove_silence: { label: "Removing silence", percent: 65 },
    editing: { label: "Editing audio", percent: 75 },
    distribution: { label: "Preparing distribution", percent: 90 },
    complete: { label: "Complete", percent: 100 },
    pending: { label: "Queued", percent: 0 },
  };

  const recordPollers = new Map();
  const liveRegion = document.getElementById("app-live-region");
  const recordsContainer = document.getElementById("records_container");
  const emptyState = document.getElementById("dashboard_empty_state");

  function announce(message) {
    if (!liveRegion || !message) {
      return;
    }
    liveRegion.textContent = "";
    window.setTimeout(() => {
      liveRegion.textContent = message;
    }, 30);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function setEmptyStateVisibility() {
    if (!emptyState || !recordsContainer) {
      return;
    }
    emptyState.hidden = recordsContainer.children.length > 0;
  }

  function updateQueueSummary() {
    const banner = document.getElementById("upload_queue_summary");
    if (!banner || !recordsContainer) {
      return;
    }
    const active = Array.from(recordsContainer.querySelectorAll("[data-progress-track='true']")).length;
    banner.textContent = `${active} active processing job${active === 1 ? "" : "s"} across the library.`;
  }

  function badgeClass(kind) {
    switch (kind) {
      case "success":
        return "status-pill is-success";
      case "danger":
        return "status-pill is-danger";
      case "muted":
        return "status-pill is-muted";
      default:
        return "status-pill is-brand";
    }
  }

  function actionMarkup(recordId, canOpen, allowRemove) {
    const buttons = [];
    if (canOpen) {
      buttons.push(
        `<a href="/record/${escapeHtml(recordId)}" class="btn btn-primary btn-sm">Open Episode</a>`,
      );
    }
    if (allowRemove) {
      buttons.push(
        `<form method="post" action="/record/${escapeHtml(recordId)}/delete" class="inline-form" data-busy-form="true" data-confirm-message="Remove this record and its media file?">` +
          '<button type="submit" class="btn btn-outline-secondary btn-sm" data-busy-label="Removing...">Remove</button>' +
        "</form>",
      );
    }
    return buttons.join("");
  }

  function createJobCard(id, fileName) {
    if (!recordsContainer) {
      return null;
    }
    const card = document.createElement("article");
    card.className = "episode-card is-processing job-skeleton";
    card.dataset.recordId = id;
    card.dataset.fileName = fileName;
    card.dataset.progressValue = "0";
    card.dataset.progressStage = "uploading";
    card.dataset.progressTrack = "true";
    card.innerHTML = `
      <div class="episode-card__header">
        <div>
          <p class="episode-card__eyebrow">Episode</p>
          <h3 class="episode-card__title" data-card-title>${escapeHtml(fileName)}</h3>
        </div>
      </div>
      <p class="episode-card__meta" data-card-time>${escapeHtml(new Date().toLocaleString())}</p>
      <div class="episode-card__status">
        <span class="${badgeClass("brand")}" data-card-badge>Uploading (0%)</span>
        <div class="progress shell-progress" data-card-progress-wrap>
          <div class="progress-bar" role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" data-card-progress>0%</div>
        </div>
        <p class="episode-card__detail" data-card-detail>Preparing upload...</p>
      </div>
      <div class="episode-card__actions" data-card-actions></div>
    `;
    recordsContainer.prepend(card);
    bindBusyForms(card);
    setEmptyStateVisibility();
    updateQueueSummary();
    return card;
  }

  function updateCard(card, state) {
    if (!card) {
      return;
    }
    const badge = card.querySelector("[data-card-badge]");
    const progressWrap = card.querySelector("[data-card-progress-wrap]");
    const progressBar = card.querySelector("[data-card-progress]");
    const detail = card.querySelector("[data-card-detail]");
    const title = card.querySelector("[data-card-title]");
    const time = card.querySelector("[data-card-time]");
    const actions = card.querySelector("[data-card-actions]");

    if (title && state.displayTitle) {
      title.textContent = state.displayTitle;
    }
    if (time && state.uploadTime) {
      time.textContent = state.uploadTime;
    }
    if (detail) {
      detail.textContent = state.detail || "";
    }

    const progress = Math.max(0, Math.min(100, Number(state.progress ?? 0)));
    card.dataset.progressValue = String(progress);
    card.dataset.progressStage = state.stage || "pending";
    card.dataset.progressTrack = state.track ? "true" : "false";
    card.classList.toggle("is-processing", !!state.track && !state.isError);
    card.classList.toggle("is-failed", !!state.isError);
    if (!state.track) {
      card.classList.remove("job-skeleton");
    }

    if (badge) {
      badge.className = badgeClass(state.badgeKind);
      badge.textContent = state.badgeText;
    }

    if (progressWrap && progressBar) {
      progressWrap.hidden = state.hideProgress;
      progressBar.style.width = `${progress}%`;
      progressBar.textContent = `${progress}%`;
      progressBar.setAttribute("aria-valuenow", String(progress));
    }

    if (actions && state.recordId) {
      actions.innerHTML = actionMarkup(state.recordId, state.canOpen, state.allowRemove);
      bindBusyForms(actions);
    }

    updateQueueSummary();
  }

  async function fetchRecordSummary(recordId) {
    const response = await fetch(`/record/${recordId}/summary`);
    if (!response.ok) {
      throw new Error(`Unable to load record ${recordId}`);
    }
    return response.json();
  }

  async function pollRecord(recordId, card) {
    if (recordPollers.has(recordId)) {
      return;
    }

    const intervalId = window.setInterval(async () => {
      try {
        const response = await fetch(`/progress/${recordId}`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const status = await response.json();
        if (status.stage === "error") {
          window.clearInterval(intervalId);
          recordPollers.delete(recordId);
          updateCard(card, {
            recordId,
            displayTitle: card.dataset.fileName,
            badgeText: "Processing failed",
            badgeKind: "danger",
            detail: status.message || "The pipeline stopped before completion.",
            progress: status.progress ?? 0,
            stage: "error",
            hideProgress: true,
            track: false,
            canOpen: false,
            allowRemove: true,
            isError: true,
          });
          announce(`Processing failed for ${card.dataset.fileName}.`);
          return;
        }

        const info = STAGE_INFO[status.stage] || STAGE_INFO.pending;
        updateCard(card, {
          recordId,
          displayTitle: card.dataset.fileName,
          badgeText: `${info.label} (${status.progress}%)`,
          badgeKind: "brand",
          detail: status.message || "",
          progress: status.progress,
          stage: status.stage,
          hideProgress: false,
          track: status.progress < 100,
          canOpen: false,
          isError: false,
        });

        if (status.progress >= 100) {
          window.clearInterval(intervalId);
          recordPollers.delete(recordId);
          const summary = await fetchRecordSummary(recordId);
          updateCard(card, {
            recordId,
            displayTitle: summary.display_title || summary.filename,
            uploadTime: summary.upload_time,
            badgeText: summary.error ? "Processing failed" : "Ready",
            badgeKind: summary.error ? "danger" : "success",
            detail: summary.error || (summary.schedule_time ? `Scheduled for ${summary.schedule_time}` : "Ready for title selection, scheduling, and publishing."),
            progress: 100,
            stage: "complete",
            hideProgress: true,
            track: false,
            canOpen: !summary.error,
            allowRemove: true,
            isError: Boolean(summary.error),
          });
          announce(`Processing finished for ${summary.display_title || summary.filename}.`);
        }
      } catch (error) {
        window.clearInterval(intervalId);
        recordPollers.delete(recordId);
        updateCard(card, {
          recordId,
          displayTitle: card.dataset.fileName,
          badgeText: "Status unavailable",
          badgeKind: "danger",
          detail: error.message || "Progress polling stopped unexpectedly.",
          progress: Number(card.dataset.progressValue || 0),
          stage: "error",
          hideProgress: true,
          track: false,
          canOpen: false,
          allowRemove: false,
          isError: true,
        });
        announce(`Status polling stopped for ${card.dataset.fileName}.`);
      }
    }, 1200);

    recordPollers.set(recordId, intervalId);
  }

  function initExistingRecordPollers() {
    if (!recordsContainer) {
      return;
    }
    Array.from(recordsContainer.querySelectorAll("[data-progress-track='true']")).forEach((card) => {
      const recordId = card.dataset.recordId;
      if (recordId) {
        pollRecord(recordId, card);
      }
    });
    setEmptyStateVisibility();
    updateQueueSummary();
  }

  function initBusyForms(root = document) {
    bindBusyForms(root);
  }

  function bindBusyForms(root) {
    const forms = root.querySelectorAll ? root.querySelectorAll("[data-busy-form='true']") : [];
    forms.forEach((form) => {
      if (form.dataset.busyBound === "true") {
        return;
      }
      form.dataset.busyBound = "true";
      form.addEventListener("submit", (event) => {
        const message = form.dataset.confirmMessage;
        if (message && !window.confirm(message)) {
          event.preventDefault();
          return;
        }
        form.dataset.busy = "true";
        Array.from(form.querySelectorAll("button[type='submit']")).forEach((button) => {
          if (!button.dataset.originalLabel) {
            button.dataset.originalLabel = button.textContent;
          }
          button.disabled = true;
          if (button.dataset.busyLabel) {
            button.textContent = button.dataset.busyLabel;
          }
        });
      });
    });
  }

  function handleUpload(file) {
    const removeSilence = document.getElementById("remove_silence_checkbox")?.checked;
    const card = createJobCard(`pending-${Date.now()}`, file.name);
    if (!card) {
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("remove_silence", Boolean(removeSilence));

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/upload");
    xhr.upload.addEventListener("progress", (event) => {
      if (!event.lengthComputable) {
        return;
      }
      const progress = Math.round((event.loaded / event.total) * STAGE_INFO.uploading.percent);
      updateCard(card, {
        recordId: card.dataset.recordId,
        displayTitle: file.name,
        badgeText: `Uploading (${progress}%)`,
        badgeKind: "brand",
        detail: removeSilence ? "Silence trimming will run after editing." : "Uploading the source file.",
        progress,
        stage: "uploading",
        hideProgress: false,
        track: true,
        canOpen: false,
        isError: false,
      });
    });
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const response = JSON.parse(xhr.responseText || "{}");
        const recordId = response.id;
        card.dataset.recordId = recordId;
        card.dataset.fileName = file.name;
        announce(`Upload accepted for ${file.name}.`);
        updateCard(card, {
          recordId,
          displayTitle: file.name,
          badgeText: `${STAGE_INFO.transcribing.label} (${STAGE_INFO.transcribing.percent}%)`,
          badgeKind: "brand",
          detail: "Upload finished. Backend processing started.",
          progress: STAGE_INFO.transcribing.percent,
          stage: "transcribing",
          hideProgress: false,
          track: true,
          canOpen: false,
          allowRemove: false,
          isError: false,
        });
        pollRecord(recordId, card);
      } else {
        let detail = "The upload could not be started.";
        try {
          const parsed = JSON.parse(xhr.responseText || "{}");
          detail = parsed.detail || detail;
        } catch {
          // Keep default detail.
        }
        updateCard(card, {
          recordId: card.dataset.recordId,
          displayTitle: file.name,
          badgeText: `Upload failed (${xhr.status})`,
          badgeKind: "danger",
          detail,
          progress: 0,
          stage: "error",
          hideProgress: true,
          track: false,
          canOpen: false,
          allowRemove: false,
          isError: true,
        });
        announce(`Upload failed for ${file.name}.`);
      }
    };
    xhr.onerror = () => {
      updateCard(card, {
        recordId: card.dataset.recordId,
        displayTitle: file.name,
        badgeText: "Upload error",
        badgeKind: "danger",
        detail: "The browser could not reach the server.",
        progress: 0,
        stage: "error",
        hideProgress: true,
        track: false,
          canOpen: false,
          allowRemove: false,
          isError: true,
        });
      announce(`Upload error for ${file.name}.`);
    };
    xhr.send(formData);
  }

  function initUploadWorkspace() {
    const dropZone = document.getElementById("drop_zone");
    const fileInput = document.getElementById("file_input");
    const fileSelectBtn = document.getElementById("file_select_btn");
    if (!dropZone || !fileInput || !fileSelectBtn) {
      return;
    }

    const openFilePicker = () => fileInput.click();
    fileSelectBtn.addEventListener("click", openFilePicker);
    dropZone.addEventListener("click", openFilePicker);
    dropZone.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openFilePicker();
      }
    });
    fileInput.addEventListener("change", () => {
      if (fileInput.files && fileInput.files.length > 0) {
        handleUpload(fileInput.files[0]);
      }
    });
    dropZone.addEventListener("dragover", (event) => {
      event.preventDefault();
      dropZone.classList.add("hover");
    });
    dropZone.addEventListener("dragleave", () => {
      dropZone.classList.remove("hover");
    });
    dropZone.addEventListener("drop", (event) => {
      event.preventDefault();
      dropZone.classList.remove("hover");
      if (event.dataTransfer?.files?.length) {
        handleUpload(event.dataTransfer.files[0]);
      }
    });
  }

  function initCadenceToggle() {
    const cadenceSelect = document.getElementById("cadence");
    const nDaysGroup = document.getElementById("n-days-group");
    const nDaysInput = document.getElementById("n-days");
    if (!cadenceSelect || !nDaysGroup || !nDaysInput) {
      return;
    }

    const toggle = () => {
      const needsInterval = cadenceSelect.value === "every_n";
      nDaysGroup.classList.toggle("is-hidden", !needsInterval);
      nDaysInput.disabled = !needsInterval;
      nDaysInput.required = needsInterval;
      if (!needsInterval) {
        nDaysInput.value = "";
      }
    };

    cadenceSelect.addEventListener("change", toggle);
    toggle();
  }

  function initSettingsVisibility() {
    const transcriptionSelect = document.querySelector("[data-settings-selector='transcription']");
    const contentSelect = document.querySelector("[data-settings-selector='content']");
    if (!transcriptionSelect && !contentSelect) {
      return;
    }

    const setGroupVisibility = (groupName, shouldShow) => {
      document.querySelectorAll(`[data-settings-group='${groupName}']`).forEach((group) => {
        group.classList.toggle("is-hidden", !shouldShow);
      });
    };

    const refresh = () => {
      const transcriptionBackend = transcriptionSelect?.value || "auto";
      const contentBackend = contentSelect?.value || "auto";
      setGroupVisibility("local-whisper", transcriptionBackend === "auto" || transcriptionBackend === "local-whisper");
      setGroupVisibility("openai-content", contentBackend === "auto" || contentBackend === "openai");
      setGroupVisibility("ollama", contentBackend === "ollama");
    };

    transcriptionSelect?.addEventListener("change", refresh);
    contentSelect?.addEventListener("change", refresh);
    refresh();
  }

  function initRecordingControls() {
    const recordControls = document.getElementById("record_controls");
    const screenButton = document.getElementById("record_screen_btn");
    const webcamButton = document.getElementById("record_webcam_btn");
    const bothButton = document.getElementById("record_both_btn");
    if (!recordControls || !screenButton || !webcamButton || !bothButton) {
      return;
    }

    let mediaRecorder = null;
    let mediaChunks = [];
    let stopButton = null;

    async function startRecording(captureScreen, captureWebcam) {
      try {
        const streams = [];
        if (captureScreen) {
          const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: captureWebcam });
          streams.push(screenStream);
          if (!captureWebcam) {
            streams.push(await navigator.mediaDevices.getUserMedia({ audio: true }));
          }
        }
        if (captureWebcam) {
          streams.push(await navigator.mediaDevices.getUserMedia({ video: true, audio: true }));
        }

        const combined = new MediaStream(streams.flatMap((stream) => stream.getTracks()));
        mediaChunks = [];
        mediaRecorder = new MediaRecorder(combined);
        mediaRecorder.ondataavailable = (event) => mediaChunks.push(event.data);
        mediaRecorder.onstop = () => {
          const blob = new Blob(mediaChunks, { type: mediaChunks[0]?.type || "video/webm" });
          const file = new File([blob], "recording.webm", { type: blob.type });
          handleUpload(file);
          [screenButton, webcamButton, bothButton].forEach((button) => {
            button.disabled = false;
          });
          if (stopButton) {
            stopButton.remove();
            stopButton = null;
          }
          announce("Recording stopped and queued for processing.");
        };

        stopButton = document.createElement("button");
        stopButton.type = "button";
        stopButton.className = "btn btn-outline-secondary";
        stopButton.textContent = "Stop recording";
        stopButton.addEventListener("click", () => mediaRecorder?.stop());
        recordControls.appendChild(stopButton);

        [screenButton, webcamButton, bothButton].forEach((button) => {
          button.disabled = true;
        });
        mediaRecorder.start();
        announce("Recording started.");
      } catch (error) {
        announce(error.message || "The browser could not start recording.");
      }
    }

    screenButton.addEventListener("click", () => startRecording(true, false));
    webcamButton.addEventListener("click", () => startRecording(false, true));
    bothButton.addEventListener("click", () => startRecording(true, true));
  }

  initBusyForms();
  initUploadWorkspace();
  initCadenceToggle();
  initSettingsVisibility();
  initRecordingControls();
  initExistingRecordPollers();
});
