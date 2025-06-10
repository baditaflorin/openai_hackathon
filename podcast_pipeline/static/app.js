document.addEventListener('DOMContentLoaded', () => {
  const dropZone = document.getElementById('drop_zone');
  const fileInput = document.getElementById('file_input');
  const fileSelectBtn = document.getElementById('file_select_btn');

  const loadingOverlay = document.getElementById('loading');

  const handleFile = async (file) => {
    loadingOverlay.classList.add('show');
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch('/upload', {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        throw new Error(`Upload failed with status ${response.status}`);
      }
      const html = await response.text();
      document.open();
      document.write(html);
      document.close();
    } catch (err) {
      console.error(err);
      loadingOverlay.classList.remove('show');
      alert(`Upload error: ${err}`);
    }
  };

  fileSelectBtn.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', async () => {
    if (fileInput.files.length > 0) {
      await handleFile(fileInput.files[0]);
    }
  });

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('hover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('hover');
  });

  dropZone.addEventListener('drop', async (e) => {
    e.preventDefault();
    dropZone.classList.remove('hover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      await handleFile(files[0]);
    }
  });
});