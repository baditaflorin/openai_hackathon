document.addEventListener('DOMContentLoaded', () => {
  const dropZone = document.getElementById('drop_zone');
  const fileInput = document.getElementById('file_input');
  const fileSelectBtn = document.getElementById('file_select_btn');

  const recordsContainer = document.getElementById('records_container');

  const recordControls = document.getElementById('record_controls');
  const recordScreenBtn = document.getElementById('record_screen_btn');
  const recordWebcamBtn = document.getElementById('record_webcam_btn');
  const recordBothBtn = document.getElementById('record_both_btn');
  let mediaRecorder;
  let mediaChunks = [];
  const STAGE_INFO = {
    uploading:   { label: 'Uploading file...',       percent: 10 },
    transcribing:{ label: 'Transcribing audio...',    percent: 20 },
    descriptions:{ label: 'Generating descriptions...',percent: 30 },
    entities:    { label: 'Extracting entities...',    percent: 40 },
    titles:      { label: 'Suggesting titles...',     percent: 50 },
    script:      { label: 'Generating script...',     percent: 60 },
    editing:     { label: 'Editing audio...',         percent: 75 },
    distribution:{ label: 'Distributing audio...',     percent: 90 },
    complete:    { label: 'Finalizing...',            percent:100 },
  };

  function createJobCard(initialId, fileName) {
    const col = document.createElement('div');
    col.className = 'col';
    col.id = `rec_${initialId}`;
    const card = document.createElement('div');
    card.className = 'card h-100';
    const body = document.createElement('div');
    body.className = 'card-body d-flex flex-column';
    const title = document.createElement('h5');
    title.className = 'card-title';
    title.textContent = fileName;
    const time = document.createElement('p');
    time.className = 'card-text text-muted mb-1';
    time.textContent = new Date().toLocaleString();
    const badge = document.createElement('span');
    badge.className = 'badge bg-info mb-2';
    badge.textContent = `${STAGE_INFO.uploading.label} (0%)`;
    const progDiv = document.createElement('div');
    progDiv.className = 'progress mb-2';
    const progBar = document.createElement('div');
    progBar.className = 'progress-bar';
    progBar.setAttribute('role', 'progressbar');
    progBar.style.width = '0%';
    progBar.textContent = '0%';
    progDiv.appendChild(progBar);
    body.append(title, time, badge, progDiv);
    card.appendChild(body);
    col.appendChild(card);
    recordsContainer.prepend(col);
    return { badge, progBar, cardBody: body, col };
  }

  const handleFile = (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const placeholderId = Date.now().toString();
    const { badge, progBar, cardBody, col } = createJobCard(placeholderId, file.name);
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload');
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * STAGE_INFO.uploading.percent);
        badge.textContent = `${STAGE_INFO.uploading.label} (${pct}%)`;
        progBar.style.width = pct + '%';
        progBar.textContent = pct + '%';
      }
    });
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const resp = JSON.parse(xhr.responseText || '{}');
        const jobId = resp.id;
        col.id = `rec_${jobId}`;
        badge.textContent = STAGE_INFO.transcribing.label + ` (0%)`;
        progBar.style.width = STAGE_INFO.transcribing.percent + '%';
        progBar.textContent = STAGE_INFO.transcribing.percent + '%';
        const poll = setInterval(async () => {
          try {
            const r = await fetch(`/progress/${jobId}`);
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            const stat = await r.json();
            if (stat.stage === 'error') {
              clearInterval(poll);
              badge.className = 'badge bg-danger mb-2';
              badge.textContent = `Error: ${stat.message || 'processing failed'}`;
              return;
            }
            const info = STAGE_INFO[stat.stage];
            if (info) {
              badge.textContent = `${info.label} (${stat.progress}%)`;
              progBar.style.width = stat.progress + '%';
              progBar.textContent = stat.progress + '%';
            }
            if (stat.progress >= 100) {
              clearInterval(poll);
              badge.className = 'badge bg-success mb-2';
              badge.textContent = 'Completed';
              const link = document.createElement('a');
              link.href = `/record/${jobId}`;
              link.className = 'btn btn-primary btn-sm me-2';
              link.textContent = 'Details';
              cardBody.appendChild(link);
            }
          } catch (err) {
            clearInterval(poll);
            badge.className = 'badge bg-danger mb-2';
            badge.textContent = `Error: ${err.message}`;
          }
        }, 1000);
      } else {
        badge.className = 'badge bg-danger mb-2';
        badge.textContent = `Upload failed (${xhr.status})`;
      }
    };
    xhr.onerror = () => {
      badge.className = 'badge bg-danger mb-2';
      badge.textContent = 'Upload error';
    };
    xhr.send(formData);
  };

  const startRecording = async (captureScreen, captureWebcam) => {
    const streams = [];
    if (captureScreen) {
      const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: captureWebcam });
      streams.push(screenStream);
      if (!captureWebcam) {
        const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        streams.push(micStream);
      }
    }
    if (captureWebcam) {
      const camStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      streams.push(camStream);
    }
    const tracks = streams.flatMap(s => s.getTracks());
    const stream = new MediaStream(tracks);
    mediaChunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = e => mediaChunks.push(e.data);
    mediaRecorder.onstop = () => {
      const blob = new Blob(mediaChunks, { type: mediaChunks[0]?.type });
      const file = new File([blob], 'recording.webm', { type: blob.type });
      handleFile(file);
      recordScreenBtn.disabled = false;
      recordWebcamBtn.disabled = false;
      recordBothBtn.disabled = false;
      stopBtn.remove();
    };
    const stopBtn = document.createElement('button');
    stopBtn.textContent = 'Stop Recording';
    stopBtn.className = 'btn btn-danger ms-2';
    stopBtn.onclick = () => mediaRecorder.stop();
    recordControls.appendChild(stopBtn);
    recordScreenBtn.disabled = true;
    recordWebcamBtn.disabled = true;
    recordBothBtn.disabled = true;
    mediaRecorder.start();
  };

  recordScreenBtn.addEventListener('click', () => startRecording(true, false));
  recordWebcamBtn.addEventListener('click', () => startRecording(false, true));
  recordBothBtn.addEventListener('click', () => startRecording(true, true));

  fileSelectBtn.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      handleFile(fileInput.files[0]);
    }
  });

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('hover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('hover');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('hover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  });
});