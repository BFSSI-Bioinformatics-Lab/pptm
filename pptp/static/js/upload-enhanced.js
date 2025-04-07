document.addEventListener('DOMContentLoaded', function () {
  const counters = {
    'barcode': 0,
    'nutrition': 0,
    'ingredients': 0
  };

  document.querySelectorAll('.add-more-btn').forEach(button => {
    button.addEventListener('click', function () {
      const section = this.dataset.section;
      addNewUploadSection(section);
    });
  });

  function addNewUploadSection(section) {
    counters[section]++;
    const index = counters[section];

    const template = document.getElementById(`${section}Template`).innerHTML
      .replace(/{index}/g, index);

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = template;
    const newElement = tempDiv.firstElementChild;

    document.getElementById(`${section}UploadContainer`).appendChild(newElement);

    newElement.querySelector('.remove-upload-btn').addEventListener('click', function () {
      newElement.remove();
    });

    setupFileInputPreview(newElement.querySelector('input[type="file"]'));
    setupDropZone(newElement.querySelector('.upload-zone'));
  }

  document.addEventListener('click', function (e) {
    if (e.target.classList.contains('remove-upload-btn') ||
      e.target.closest('.remove-upload-btn')) {
      const button = e.target.classList.contains('remove-upload-btn') ?
        e.target : e.target.closest('.remove-upload-btn');
      const uploadItem = button.closest('.upload-item');
      if (uploadItem) {
        uploadItem.remove();
      }
    }
  });

  if (!document.getElementById('main-drop-zone')) {
    const mainDropZone = document.createElement('div');
    mainDropZone.id = 'main-drop-zone';
    mainDropZone.className = 'drop-zone mb-4 p-5 border border-dashed rounded text-center bg-light';
    mainDropZone.innerHTML = `
        <i class="bi bi-cloud-arrow-up fs-1 mb-3"></i>
        <h3 class="h5 mb-2">Drag files here</h3>
        <p class="mb-0">Drop any image file to upload</p>
        <p class="text-muted small mt-2">You'll be prompted where to save it after dropping</p>
      `;

    const form = document.getElementById('combinedUploadForm');
    const firstSection = form.querySelector('.mb-5');
    form.insertBefore(mainDropZone, firstSection);

    setupMainDropZone(mainDropZone);
  }

  document.querySelectorAll('input[type="file"]').forEach(input => {
    setupFileInputPreview(input);
  });

  document.querySelectorAll('.upload-zone').forEach(zone => {
    setupDropZone(zone);
  });

  function setupFileInputPreview(input) {
    if (!input) return;

    const previewContainer = input.closest('.upload-zone')?.querySelector('.upload-preview');
    if (!previewContainer) return;

    input.addEventListener('change', function () {
      updatePreview(this, previewContainer);
    });
  }

  function updatePreview(fileInput, previewContainer) {
    previewContainer.innerHTML = '';
    previewContainer.classList.add('d-none');

    if (fileInput.files && fileInput.files[0]) {
      const file = fileInput.files[0];

      if (!file.type.match('image.*')) {
        return;
      }

      const reader = new FileReader();

      reader.onload = function (e) {
        previewContainer.classList.remove('d-none');

        const img = document.createElement('img');
        img.src = e.target.result;
        img.classList.add('img-fluid', 'rounded', 'mb-2');
        img.style.maxHeight = '200px';

        previewContainer.appendChild(img);
      };

      reader.readAsDataURL(file);
    }
  }

  function setupDropZone(zone) {
    if (!zone) return;

    zone.classList.add('drop-zone-container');

    const fileInput = zone.querySelector('input[type="file"]');
    if (!fileInput) return;

    if (!zone.querySelector('.drop-overlay')) {
      const overlay = document.createElement('div');
      overlay.className = 'drop-overlay';
      overlay.innerHTML = '<div class="drop-message"><i class="bi bi-cloud-arrow-down"></i><span>Drop image here</span></div>';
      zone.appendChild(overlay);
    }

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
      zone.addEventListener(eventName, preventDefaults, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
      zone.addEventListener(eventName, () => {
        zone.classList.add('active-drop-zone');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      zone.addEventListener(eventName, () => {
        zone.classList.remove('active-drop-zone');
      });
    });

    zone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;

      if (files.length > 0) {
        try {
          const dataTransfer = new DataTransfer();
          dataTransfer.items.add(files[0]);
          fileInput.files = dataTransfer.files;

          const event = new Event('change', { bubbles: true });
          fileInput.dispatchEvent(event);

          if (files.length > 1) {
            const remainingFiles = Array.from(files).slice(1);
            const newDataTransfer = new DataTransfer();
            remainingFiles.forEach(file => newDataTransfer.items.add(file));

            setTimeout(() => {
              showDestinationDialog(newDataTransfer.files);
            }, 500);
          }
        } catch (error) {
          console.error('Browser compatibility issue with DataTransfer:', error);
          // Fallback: simulate file input click to open file picker
          fileInput.click();
        }
      }
    });
  }

  function setupMainDropZone(mainDropZone) {
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
      mainDropZone.addEventListener(eventName, preventDefaults, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
      mainDropZone.addEventListener(eventName, () => {
        mainDropZone.classList.add('border-primary', 'bg-primary-subtle');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      mainDropZone.addEventListener(eventName, () => {
        mainDropZone.classList.remove('border-primary', 'bg-primary-subtle');
      });
    });

    mainDropZone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;

      if (files.length) {
        showDestinationDialog(files);
      }
    });
  }

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  function showDestinationDialog(files) {
    const existingDialog = document.getElementById('upload-destination-dialog');
    if (existingDialog) {
      existingDialog.remove();
    }

    const categories = [
      { id: 'barcode', name: 'Barcode', icon: 'upc-scan' },
      { id: 'nutrition', name: 'Nutrition Facts', icon: 'card-list' },
      { id: 'ingredients', name: 'Ingredients', icon: 'list-check' },
      { id: 'image_front', name: 'Front of Package', icon: 'box' },
      { id: 'image_back', name: 'Back of Package', icon: 'box-arrow-left' },
      { id: 'image_side', name: 'Side of Package', icon: 'box-arrow-in-right' },
      { id: 'image_other', name: 'Other Package View', icon: 'boxes' }
    ];

    const dialog = document.createElement('div');
    dialog.id = 'upload-destination-dialog';
    dialog.className = 'card position-fixed start-50 top-50 translate-middle shadow-lg';
    dialog.style.zIndex = '1050';
    dialog.style.width = '90%';
    dialog.style.maxWidth = '500px';

    let previewHtml = '';
    if (files.length === 1 && files[0].type.match('image.*')) {
      previewHtml = `
          <div class="text-center mb-3 preview-container">
            <p class="mb-1">Preview:</p>
            <img id="dialog-preview-image" class="img-fluid border rounded" style="max-height: 150px;" alt="Preview">
          </div>
        `;
    }

    let dialogContent = `
        <div class="card-header bg-primary text-white">
          <h5 class="card-title mb-0">
            <i class="bi bi-upload me-2"></i>Choose Upload Destination
          </h5>
        </div>
        <div class="card-body">
          <p>Select where to upload ${files.length > 1 ? 'these files' : 'this file'}:</p>
          ${previewHtml}
          <div class="list-group mb-3">
      `;

    categories.forEach(category => {
      dialogContent += `
          <button class="list-group-item list-group-item-action upload-destination" 
                  data-category="${category.id}">
            <div class="d-flex align-items-center">
              <i class="bi bi-${category.icon} me-3 fs-4"></i>
              <span>${category.name}</span>
            </div>
          </button>
        `;
    });

    dialogContent += `
          </div>
          <div class="d-flex justify-content-end">
            <button class="btn btn-secondary close-dialog-btn">Cancel</button>
          </div>
        </div>
      `;

    dialog.innerHTML = dialogContent;

    const overlay = document.createElement('div');
    overlay.className = 'position-fixed top-0 start-0 w-100 h-100 bg-dark bg-opacity-50';
    overlay.style.zIndex = '1040';

    document.body.appendChild(overlay);
    document.body.appendChild(dialog);

    if (files.length === 1 && files[0].type.match('image.*')) {
      const reader = new FileReader();
      reader.onload = function (e) {
        const previewImg = document.getElementById('dialog-preview-image');
        if (previewImg) {
          previewImg.src = e.target.result;
        }
      };
      reader.readAsDataURL(files[0]);
    }

    dialog.querySelectorAll('.upload-destination').forEach(button => {
      button.addEventListener('click', function () {
        const category = this.dataset.category;
        handleDestinationSelection(category, files);
        dialog.remove();
        overlay.remove();
      });
    });

    dialog.querySelector('.close-dialog-btn').addEventListener('click', function () {
      dialog.remove();
      overlay.remove();
    });
  }

  function handleDestinationSelection(category, files) {
    let fileInput;

    if (category.startsWith('image_')) {
      fileInput = document.querySelector(`input[name="${category}-image"]`);
      
      // Create the file input if it doesn't exist
      if (!fileInput && category.match(/^image_(front|back|side|other)$/)) {
        const containerSelector = `#${category.replace('_', '-')}-upload`;
        const container = document.querySelector(containerSelector);
        
        if (container) {
          // Create a hidden file input if needed
          fileInput = document.createElement('input');
          fileInput.type = 'file';
          fileInput.name = `${category}-image`;
          fileInput.style.display = 'none';
          container.appendChild(fileInput);
        }
      }
    } else {
      const inputs = document.querySelectorAll(`input[name="${category}-image"], input[name^="${category}-"][name$="-image"]`);

      for (const input of inputs) {
        if (!input.files || input.files.length === 0) {
          fileInput = input;
          break;
        }
      }

      if (!fileInput) {
        const addButton = document.querySelector(`.add-more-btn[data-section="${category}"]`);
        if (addButton) {
          addButton.click();

          const newInputs = document.querySelectorAll(`input[name^="${category}-"][name$="-image"]`);
          fileInput = newInputs[newInputs.length - 1];
        }
      }
    }

    if (fileInput) {
      try {
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(files[0]);
        fileInput.files = dataTransfer.files;

        const event = new Event('change', { bubbles: true });
        fileInput.dispatchEvent(event);

        if (files.length > 1) {
          const remainingFiles = Array.from(files).slice(1);
          const newDataTransfer = new DataTransfer();
          remainingFiles.forEach(file => newDataTransfer.items.add(file));

          setTimeout(() => {
            showDestinationDialog(newDataTransfer.files);
          }, 500);
        }
      } catch (error) {
        console.error('Browser compatibility issue with DataTransfer:', error);
        alert('Sorry, your browser doesn\'t support this feature. Please use the file picker instead.');
        fileInput.click();
      }
    } else {
      // Fallback if no input is found
      alert(`No upload field found for ${category.replace('_', ' ')}. Please check your form configuration.`);
    }
  }

  const formEl = document.getElementById('combinedUploadForm');
  const submitButton = document.querySelector('button[name="submit"]');
  const productNameField = document.querySelector('input[name="product_name"]');

  if (formEl && submitButton && productNameField) {
    function updateSubmitButton() {
      const nameValue = productNameField.value.trim();
      const validationErrors = document.querySelector('.validation_errors');

      submitButton.disabled = nameValue === '' || 
                             (validationErrors && validationErrors.children.length > 0);
    }

    updateSubmitButton();

    productNameField.addEventListener('input', updateSubmitButton);
    productNameField.addEventListener('change', updateSubmitButton);
  }

  if (formEl) {
    formEl.addEventListener('submit', function (e) {
      if (e.submitter && e.submitter.name === 'submit') {
        let hasErrors = false;
        const errorContainer = document.createElement('div');
        errorContainer.className = 'alert alert-danger mb-4';
        const errorList = document.createElement('ul');
        errorList.className = 'mb-0';
        errorContainer.appendChild(errorList);

        // Remove any existing error containers
        const existingErrors = formEl.querySelectorAll('.alert.alert-danger');
        existingErrors.forEach(el => el.remove());

        const productName = document.querySelector('input[name="product_name"]').value.trim();

        if (!productName) {
          hasErrors = true;
          const li = document.createElement('li');
          li.textContent = 'Product name is required';
          errorList.appendChild(li);
        } else if (productName.split(/\s+/).length < 2) {
          hasErrors = true;
          const li = document.createElement('li');
          li.textContent = 'Please enter the full product name (at least two words)';
          errorList.appendChild(li);
        }

        if (hasErrors) {
          e.preventDefault();
          const firstCard = formEl.querySelector('.card-body');
          firstCard.insertBefore(errorContainer, firstCard.firstChild);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }
      }
    });
  }
});