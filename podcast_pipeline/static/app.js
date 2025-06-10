document.addEventListener('DOMContentLoaded', () => {
  const dropZone = document.getElementById('drop_zone');
  const fileInput = document.getElementById('file_input');
  const fileSelectBtn = document.getElementById('file_select_btn');

  const loadingOverlay = document.getElementById('loading');
  const progressContainer = document.getElementById('progress_container');
  const progressBar = document.getElementById('progress_bar');

  const handleFile = (file) => {
    loadingOverlay.classList.remove('d-none');
    loadingOverlay.classList.add('d-flex');
    progressContainer.classList.remove('d-none');
    progressBar.style.width = '0%';
    progressBar.textContent = '0%';
    const formData = new FormData();
    formData.append('file', file);
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload');
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        progressBar.style.width = percent + '%';
        progressBar.textContent = percent + '%';
      }
    });
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        document.open();
        document.write(xhr.responseText);
        document.close();
      } else {
        console.error('Upload failed', xhr.status);
        loadingOverlay.classList.remove('d-flex');
        loadingOverlay.classList.add('d-none');
        progressContainer.classList.add('d-none');
        alert(`Upload failed with status ${xhr.status}`);
      }
    };
    xhr.onerror = () => {
      console.error('Upload error', xhr);
      loadingOverlay.classList.remove('d-flex');
      loadingOverlay.classList.add('d-none');
      progressContainer.classList.add('d-none');
      alert('Upload error');
    };
    xhr.responseType = 'text';
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