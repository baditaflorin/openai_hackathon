document.addEventListener('DOMContentLoaded', () => {
  const dropZone = document.getElementById('drop_zone');
  const fileInput = document.getElementById('file_input');
  const fileSelectBtn = document.getElementById('file_select_btn');

  const loadingOverlay = document.getElementById('loading');
  const progressContainer = document.getElementById('progress_container');
  const progressBar = document.getElementById('progress_bar');
  const progressLabel = document.getElementById('progress_label');

  // Define stages for client-side progress bar
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

  /**
   * Update the progress bar and status label.
   */
  const updateBar = (percent, text) => {
    progressBar.style.width = percent + '%';
    progressBar.textContent = percent + '%';
    progressLabel.textContent = text;
  };

  const handleFile = (file) => {
    loadingOverlay.classList.remove('d-none');
    loadingOverlay.classList.add('d-flex');
    progressContainer.classList.remove('d-none');
    progressLabel.classList.remove('d-none');
    // start with 0
    updateBar(0, 'Starting...');

    const formData = new FormData();
    formData.append('file', file);
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload');
    // track upload progress up to STAGE_INFO.uploading.percent
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * STAGE_INFO.uploading.percent);
        updateBar(pct, STAGE_INFO.uploading.label);
      }
    });
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        let resp;
        try {
          resp = JSON.parse(xhr.responseText);
        } catch (_e) { resp = {}; }
        const jobId = resp.id;
        // after upload, move to first server stage
        updateBar(STAGE_INFO.transcribing.percent, STAGE_INFO.transcribing.label);
        // poll backend for progress updates
        const poll = setInterval(async () => {
          try {
            const r = await fetch(`/progress/${jobId}`);
            const stat = await r.json();
            if (STAGE_INFO[stat.stage]) {
              updateBar(STAGE_INFO[stat.stage].percent, STAGE_INFO[stat.stage].label);
            }
            if (stat.progress >= 100) {
              clearInterval(poll);
              // navigate to record detail
              window.location = `/record/${jobId}`;
            }
          } catch (err) {
            console.error('Progress poll error', err);
          }
        }, 1000);
      } else {
        console.error('Upload failed', xhr.status);
        loadingOverlay.classList.remove('d-flex');
        loadingOverlay.classList.add('d-none');
        progressContainer.classList.add('d-none');
        progressLabel.classList.add('d-none');
        alert(`Upload failed with status ${xhr.status}`);
      }
    };
    xhr.onerror = () => {
      console.error('Upload error', xhr);
      loadingOverlay.classList.remove('d-flex');
      loadingOverlay.classList.add('d-none');
      progressContainer.classList.add('d-none');
      progressLabel.classList.add('d-none');
      alert('Upload error');
    };
    xhr.send(formData);
  };

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