document.addEventListener('DOMContentLoaded', function() {
  console.log('Initializing enhanced upload functionality');
  
  const config = {
    sections: ['barcode', 'nutrition', 'ingredients'],
    maxConcurrentUploads: 3
  };

  const state = {
    counters: {
      barcode: 0,
      nutrition: 0, 
      ingredients: 0
    },
    activeUploads: 0,
    uploadResults: []
  };

  const deleteImageUrl = document.getElementById('delete-image-url')?.value;
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

  class FileUploader {
    constructor(options) {
      console.log('Initializing FileUploader', options);
      this.baseUrl = options.baseUrl || '';
      this.productId = options.productId;
      this.csrfToken = options.csrfToken;
      this.maxConcurrent = options.maxConcurrent || 3;
      this.onProgress = options.onProgress || (() => {});
      this.onComplete = options.onComplete || (() => {});
      this.onError = options.onError || (() => {});
      
      this.queue = [];
      this.activeUploads = 0;
      this.results = [];
    }
  
    addFile(file, imageType, formPrefix, fileInput) {
      console.log(`Adding file to upload queue: ${formPrefix}, type: ${imageType}`);
      this.queue.push({ file, imageType, formPrefix, fileInput });
      this.processQueue();
      return this;
    }
    
    processQueue() {
      if (this.queue.length === 0 && this.activeUploads === 0) {
        console.log('Upload queue completed, triggering onComplete');
        this.onComplete(this.results);
        return;
      }
      
      while (this.queue.length > 0 && this.activeUploads < this.maxConcurrent) {
        const item = this.queue.shift();
        this.uploadFile(item);
      }
    }
    
    uploadFile(item) {
      this.activeUploads++;
      state.activeUploads++;
      console.log(`Starting upload: ${item.formPrefix}, active uploads: ${state.activeUploads}`);
      
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      
      formData.append('file', item.file);
      formData.append('image_type', item.imageType);
      formData.append('notes', '');
      
      console.log(`=== Uploading file ${item.formPrefix} ===`);
      
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percentComplete = Math.round((event.loaded / event.total) * 100);
          this.onProgress(item, percentComplete);
        }
      };
      
      xhr.onload = () => {
        this.activeUploads--;
        state.activeUploads--;
        
        try {
          const response = JSON.parse(xhr.responseText);
          console.log(`Upload completed: ${item.formPrefix}, status: ${xhr.status}`, response);
          
          if (xhr.status >= 200 && xhr.status < 300 && response.success) {
            this.results.push({
              file: item.file,
              formPrefix: item.formPrefix,
              success: true,
              imageType: item.imageType,
              imageId: response.image_id,
              imageUrl: response.image_url
            });
          } else {
            const errorMsg = response.error || `Server error: ${xhr.status}`;
            console.error(`Upload failed: ${item.formPrefix}`, errorMsg);
            this.results.push({
              file: item.file,
              formPrefix: item.formPrefix,
              success: false,
              imageType: item.imageType,
              error: errorMsg
            });
            
            this.onError(item, errorMsg);
          }
        } catch (e) {
          console.error(`Error parsing server response: ${item.formPrefix}`, e);
          this.results.push({
            file: item.file,
            formPrefix: item.formPrefix,
            success: false,
            imageType: item.imageType,
            error: 'Invalid server response'
          });
          
          this.onError(item, 'Invalid server response');
        }
        
        this.processQueue();
      };
      
      xhr.onerror = () => {
        this.activeUploads--;
        state.activeUploads--;
        console.error(`Network error during upload: ${item.formPrefix}`);
        
        this.results.push({
          file: item.file,
          formPrefix: item.formPrefix,
          success: false,
          imageType: item.imageType,
          error: 'Network error'
        });
        
        this.onError(item, 'Network error');
        this.processQueue();
      };
      
      const uploadUrl = document.getElementById('ajax-upload-url')?.value || '/upload';
      xhr.open('POST', uploadUrl);
      
      const csrfToken = this.csrfToken || document.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
      if (csrfToken) {
        xhr.setRequestHeader('X-CSRFToken', csrfToken);
      }
      
      xhr.send(formData);
    }
  }

  const uploader = new FileUploader({
    productId: typeof productId !== 'undefined' ? productId : null,
    csrfToken: typeof csrfToken !== 'undefined' ? csrfToken : null,
    maxConcurrent: config.maxConcurrentUploads,
    onProgress: (item, percentage) => {
      updateProgressUI(item.formPrefix, percentage);
    },
    onComplete: (results) => {
      console.log('All uploads completed', results);
      showCompletionStatus(results);
    },
    onError: (item, error) => {
      console.error(`Upload error: ${item.formPrefix}`, error);
      showErrorMessage(item.formPrefix, error);
    }
  });

  setupDeleteButtons();

  document.querySelectorAll('.add-more-btn').forEach(button => {
    button.addEventListener('click', function() {
      const section = this.dataset.section;
      console.log(`Adding new upload section: ${section}`);
      addNewUploadSection(section);
    });
  });

  setupMultipleUploadCheckboxes();

  document.querySelectorAll('input[type="file"]').forEach(input => {
    setupFileInput(input);
  });

  initializeFormValidation();

  setupFormSubmission();

  function setupDeleteButtons() {
    document.querySelectorAll('.delete-image-btn').forEach(btn => {
      btn.addEventListener('click', handleDeleteImage);
    });
  }

  function handleDeleteImage(e) {
    e.preventDefault();
    e.stopPropagation();
    
    const button = e.target.closest('.delete-image-btn');
    const imageId = button.dataset.imageId;
    const imageType = button.dataset.imageType;
    const imageContainer = button.closest('.existing-image');
    
    if (!confirm('Are you sure you want to delete this image?')) {
      return;
    }

    if (!deleteImageUrl || !csrfToken) {
      showToast('Delete functionality not available', 'error');
      return;
    }

    button.disabled = true;
    button.innerHTML = '<i class="bi bi-hourglass-split"></i>';

    const formData = new FormData();
    formData.append('image_id', imageId);
    formData.append('image_type', imageType);
    formData.append('csrfmiddlewaretoken', csrfToken);

    fetch(deleteImageUrl, {
      method: 'POST',
      body: formData,
      headers: {
        'X-CSRFToken': csrfToken
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        imageContainer.classList.add('removing');
        setTimeout(() => {
          imageContainer.remove();
          showToast('Image deleted successfully', 'success');
        }, 200);
      } else {
        showToast('Error deleting image: ' + (data.error || 'Unknown error'), 'error');
        button.disabled = false;
        button.innerHTML = '<i class="bi bi-x"></i>';
      }
    })
    .catch(error => {
      console.error('Error:', error);
      showToast('Error deleting image', 'error');
      button.disabled = false;
      button.innerHTML = '<i class="bi bi-x"></i>';
    });
  }

  function showToast(message, type) {
    const toastContainer = getOrCreateToastContainer();
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'error' ? 'danger' : 'success'} alert-dismissible fade show`;
    toast.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
      if (toast.parentNode) {
        toast.remove();
      }
    }, 5000);
  }

  function getOrCreateToastContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'position-fixed top-0 end-0 p-3';
      container.style.zIndex = '1050';
      document.body.appendChild(container);
    }
    return container;
  }

  function setupMultipleUploadCheckboxes() {
    console.log('Setting up multiple upload checkboxes');
    
    function setupCheckbox(checkboxId, containerId, sectionType, buttonLabel) {
      const checkbox = document.getElementById(checkboxId);
      if (!checkbox) return;
      
      checkbox.addEventListener('change', function() {
        console.log(`Checkbox change: ${checkboxId} = ${this.checked}`);
        const container = document.getElementById(containerId);
        if (!container) return;
        
        if (this.checked) {
          container.style.display = 'block';
          
          let headerEl = container.querySelector('.additional-uploads-header');
          if (!headerEl) {
            const addButtonTemplate = document.getElementById('addButtonTemplate');
            if (addButtonTemplate) {
              headerEl = document.importNode(addButtonTemplate.content, true);
              const addButton = headerEl.querySelector('.add-more-btn');
              if (addButton) {
                addButton.setAttribute('data-section', sectionType);
                addButton.querySelector('.btn-label').textContent = buttonLabel;
              }
              container.prepend(headerEl);
            }
          }
          
          if (container.querySelectorAll(`.${sectionType}-upload`).length === 0) {
            addNewUploadSection(sectionType);
          }
        } else {
          container.style.display = 'none';
        }
      });
      
      setTimeout(() => {
        if (checkbox.checked) {
          const event = new Event('change');
          checkbox.dispatchEvent(event);
        } else {
          const container = document.getElementById(containerId);
          if (container) {
            container.style.display = 'none';
          }
        }
      }, 0);
    }
    
    setupCheckbox(
      'id_has_multiple_barcodes',
      'barcodeUploadContainer',
      'barcode',
      'Add Barcode'
    );
    
    setupCheckbox(
      'id_has_multiple_nutrition_facts',
      'nutritionUploadContainer',
      'nutrition',
      'Add Nutrition Facts'
    );
  }
  
  function addNewUploadSection(section) {
    state.counters[section]++;
    const index = state.counters[section];
    console.log(`Creating new ${section} upload section with index ${index}`);
  
    const templateElement = document.getElementById(`${section}Template`);
    if (!templateElement) {
      console.error(`Template #${section}Template not found`);
      return null;
    }
    
    const newElement = document.importNode(templateElement.content, true);
    replaceIndexPlaceholders(newElement, index);
    
    const container = document.getElementById(`${section}UploadContainer`);
    if (!container) {
      console.error(`Container #${section}UploadContainer not found`);
      return null;
    }
    
    container.appendChild(newElement);
    const uploadItem = container.lastElementChild;
    
    const removeBtn = uploadItem.querySelector('.remove-upload-btn');
    if (removeBtn) {
      removeBtn.addEventListener('click', function() {
        console.log(`Removing ${section} upload item ${index}`);
        uploadItem.remove();
      });
    }
    
    const fileInput = uploadItem.querySelector('input[type="file"]');
    if (fileInput) {
      setupFileInput(fileInput);
    }
    
    setupDeleteButtons();
    
    return uploadItem;
  }
  
  function replaceIndexPlaceholders(element, index) {
    if (element.attributes) {
      Array.from(element.attributes).forEach(attr => {
        if (attr.value.includes('{index}')) {
          attr.value = attr.value.replace(/{index}/g, index);
        }
      });
    }
    
    if (element.nodeType === Node.TEXT_NODE && element.nodeValue.includes('{index}')) {
      element.nodeValue = element.nodeValue.replace(/{index}/g, index);
    }
    
    if (element.childNodes) {
      Array.from(element.childNodes).forEach(child => {
        replaceIndexPlaceholders(child, index);
      });
    }
  }

  function setupFileInput(input) {
    if (!input) return;
    
    const cardBody = input.closest('.card-body');
    if (!cardBody) return;
    
    const previewContainer = cardBody.querySelector('.upload-preview');
    if (!previewContainer) return;

    console.log(`Setting up file input: ${input.name}`);
    
    input.addEventListener('change', function() {
      if (this.files && this.files[0]) {
        const file = this.files[0];
        console.log(`File selected: ${file.name}, type: ${file.type}, size: ${file.size} bytes`);
        updatePreview(file, previewContainer);
        prepareFileForUpload(file, this);
      }
    });
    
    const uploadZone = cardBody.querySelector('.upload-zone');
    if (uploadZone) {
      ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, e => {
          e.preventDefault();
          e.stopPropagation();
        }, false);
      });
      
      ['dragenter', 'dragover'].forEach(eventName => {
        uploadZone.addEventListener(eventName, () => {
          uploadZone.classList.add('highlight');
        }, false);
      });
      
      ['dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, () => {
          uploadZone.classList.remove('highlight');
        }, false);
      });
      
      uploadZone.addEventListener('drop', function(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
          console.log(`File dropped: ${files[0].name}`);
          input.files = files;
          const file = files[0];
          updatePreview(file, previewContainer);
          prepareFileForUpload(file, input);
        }
      }, false);
      
      uploadZone.addEventListener('click', () => {
        input.click();
      });
    }
  }
    
  function updatePreview(file, previewContainer) {
    previewContainer.innerHTML = '';
    previewContainer.classList.remove('show');
    
    if (!file.type.match('image.*')) {
      console.warn(`File is not an image: ${file.type}`);
      const errorMsg = document.createElement('div');
      errorMsg.className = 'alert alert-warning mt-2';
      errorMsg.textContent = 'Please select an image file';
      previewContainer.appendChild(errorMsg);
      previewContainer.classList.add('show');
      return;
    }

    console.log(`Generating preview for: ${file.name}`);
    const reader = new FileReader();

    reader.onload = function(e) {
      previewContainer.classList.add('show');
      const previewDiv = document.createElement('div');
      previewDiv.className = 'preview-container mb-2';
      previewDiv.innerHTML = `
        <img src="${e.target.result}" class="img-fluid" style="max-height: 200px;">
        <button type="button" class="btn btn-sm btn-outline-danger mt-2 remove-preview">
          <i class="bi bi-x"></i> Remove
        </button>
      `;
      previewContainer.appendChild(previewDiv);
      
      previewDiv.querySelector('.remove-preview').addEventListener('click', function() {
        previewContainer.innerHTML = '';
        previewContainer.classList.remove('show');
        const zone = previewContainer.previousElementSibling;
        if (zone) {
          zone.style.display = 'block';
          const fileInput = zone.querySelector('input[type="file"]');
          if (fileInput) {
            fileInput.value = '';
          }
        }
      });
    };

    reader.readAsDataURL(file);
  }

  function prepareFileForUpload(file, fileInput) {
    if (!file) return;
    
    fileInput.dataset.originalFileName = file.name;
    
    const inputName = fileInput.name;
    let formPrefix = '';
    let imageType = '';
    
    if (inputName.startsWith('image_')) {
      const parts = inputName.split('-')[0];
      formPrefix = parts;
      imageType = parts.replace('image_', '');
    } else {
      const parts = inputName.split('-');
      if (parts.length === 2) {
        formPrefix = parts[0];
        imageType = parts[0];
      } else if (parts.length === 3) {
        formPrefix = `${parts[0]}-${parts[1]}`;
        imageType = parts[0];
      }
    }
    
    if (!formPrefix || !imageType) {
      console.error(`Could not determine image type from input name: ${inputName}`);
      return;
    }
    
    console.log(`Auto-uploading file immediately: ${formPrefix}, type: ${imageType}`);
    
    createProgressUI(fileInput, formPrefix);
    uploader.addFile(file, imageType, formPrefix, fileInput);
  }

  function createProgressUI(fileInput, formPrefix) {
    const container = fileInput.closest('.card-body');
    if (!container) return;
    
    let progressContainer = container.querySelector('.upload-progress');
    if (!progressContainer) {
      console.log(`Creating progress UI for ${formPrefix}`);
      progressContainer = document.createElement('div');
      progressContainer.className = 'upload-progress mt-3';
      progressContainer.innerHTML = `
        <div class="progress" style="height: 20px;">
          <div class="progress-bar" role="progressbar" style="width: 0%;" 
               aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div>
        </div>
        <div class="upload-status small mt-1">Preparing upload...</div>
      `;
      container.appendChild(progressContainer);
    }
  }

  function updateProgressUI(formPrefix, percentage) {
    const inputSelector = `[name="${formPrefix}-image"]`;
    const fileInput = document.querySelector(inputSelector);
    if (!fileInput) return;
    
    const container = fileInput.closest('.card-body');
    if (!container) return;
    
    const progressBar = container.querySelector('.progress-bar');
    const statusDiv = container.querySelector('.upload-status');
    
    if (progressBar) {
      progressBar.style.width = `${percentage}%`;
      progressBar.setAttribute('aria-valuenow', percentage);
      progressBar.textContent = `${percentage}%`;
    }
    
    if (statusDiv) {
      statusDiv.textContent = `Uploading: ${percentage}%`;
    }
  }
  
  function showCompletionStatus(results) {
    results.forEach(result => {
        const inputSelector = `[name="${result.formPrefix}-image"]`;
        const fileInput = document.querySelector(inputSelector);
        if (!fileInput) return;
        
        const container = fileInput.closest('.card-body');
        if (!container) return;
        
        const hiddenField = document.createElement('input');
        hiddenField.type = 'hidden';
        hiddenField.name = `${result.formPrefix}-already_uploaded`;
        hiddenField.value = 'true';
        container.appendChild(hiddenField);
        
        if (result.success) {
          const imageIdField = document.createElement('input');
          imageIdField.type = 'hidden';
          imageIdField.name = `${result.formPrefix}-image_id`;
          imageIdField.value = result.imageId;
          container.appendChild(imageIdField);
        }
        
        const statusDiv = container.querySelector('.upload-status');
        const progressUI = container.querySelector('.upload-progress');
        
        if (result.success) {
            console.log(`Upload successful for ${result.formPrefix}, ID: ${result.imageId}`);
            if (statusDiv) {
                statusDiv.innerHTML = '<span class="text-success"><i class="bi bi-check-circle"></i> Uploaded! Notes will be saved when you submit the form.</span>';
            }
            
            if (progressUI) {
                const progressBar = progressUI.querySelector('.progress-bar');
                if (progressBar) {
                    progressBar.classList.remove('progress-bar');
                    progressBar.classList.add('bg-success');
                }
            }
        } else {
            console.log(`Upload failed for ${result.formPrefix}: ${result.error}`);
            if (statusDiv) {
                statusDiv.textContent = `Error: ${result.error}`;
                statusDiv.classList.add('text-danger');
            }
            
            if (progressUI) {
                let existingError = progressUI.querySelector('.upload-error-message');
                if (!existingError) {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'upload-error-message mt-2';
                    errorDiv.innerHTML = `
                        <button type="button" class="btn btn-sm btn-outline-danger retry-btn">
                            <i class="bi bi-arrow-repeat"></i> Retry
                        </button>
                    `;
                    progressUI.appendChild(errorDiv);
                    
                    const retryBtn = errorDiv.querySelector('.retry-btn');
                    if (retryBtn) {
                        retryBtn.addEventListener('click', function() {
                            console.log(`Retry clicked for ${result.formPrefix}`);
                            fileInput.value = '';
                            if (progressUI) {
                                progressUI.remove();
                            }
                        });
                    }
                }
            }
        }
    });
  }
  
  function showErrorMessage(formPrefix, error) {
    const inputSelector = `[name="${formPrefix}-image"]`;
    const fileInput = document.querySelector(inputSelector);
    if (!fileInput) return;
    
    const container = fileInput.closest('.card-body');
    if (!container) return;
    
    const statusDiv = container.querySelector('.upload-status');
    
    if (statusDiv) {
      statusDiv.textContent = `Error: ${error}`;
      statusDiv.classList.add('text-danger');
    }
  }

  function initializeFormValidation() {
    console.log('Initializing form validation');
    const form = document.getElementById('combinedUploadForm');
    const submitButton = document.querySelector('button[name="submit_product"]');
    const productNameField = document.querySelector('input[name="product_name"]');

    if (form && submitButton && productNameField) {
      function updateSubmitButton() {
        const nameValue = productNameField.value.trim();
        const validationErrors = document.querySelector('.alert.alert-warning, .validation-errors');
        const disabled = nameValue === '' || 
                       (validationErrors && validationErrors.querySelector('ul')?.children.length > 0) ||
                       state.activeUploads > 0;
        
        submitButton.disabled = disabled;
        if (disabled) {
          console.log('Submit button disabled', {
            emptyName: nameValue === '',
            hasErrors: !!(validationErrors && validationErrors.querySelector('ul')?.children.length > 0),
            activeUploads: state.activeUploads
          });
        }
      }

      updateSubmitButton();
      productNameField.addEventListener('input', updateSubmitButton);
      productNameField.addEventListener('change', updateSubmitButton);
      setInterval(updateSubmitButton, 1000);
    }
  }

  function setupFormSubmission() {
    console.log('Setting up form submission handling');
    const form = document.getElementById('combinedUploadForm');
  
    if (form) {
      form.addEventListener('submit', function(e) {
        console.log('Form submit event triggered', {
          submitter: e.submitter,
          submitterName: e.submitter?.name
        });
  
        if (e.submitter && e.submitter.name === 'submit_product') {
          e.preventDefault();
          console.log('Intercepting submit_product submission');
          
          if (state.activeUploads > 0) {
            console.log('Blocking submission - active uploads:', state.activeUploads);
            showValidationErrors(['Please wait for all uploads to complete before submitting']);
            return;
          }
          
          const productNameInput = document.querySelector('input[name="product_name"]');
          const productName = productNameInput ? productNameInput.value.trim() : '';
          if (!productName) {
            console.log('Blocking submission - missing product name');
            showValidationErrors(['Product name is required']);
            return;
          }
          
          const validateUrl = document.getElementById('ajax-validate-url')?.value;
          if (!validateUrl) {
            console.error('Validation URL not found, falling back to standard submission');
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'submit_product';
            hiddenInput.value = '1';
            form.appendChild(hiddenInput);
            form.submit();
            return;
          }
          
          const csrfTokenInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
          const csrfTokenValue = csrfTokenInput ? csrfTokenInput.value : '';
          
          if (!csrfTokenValue) {
            console.error('CSRF token not found');
            showValidationErrors(['Security token missing. Please refresh the page.']);
            return;
          }
  
          console.log('Starting server validation');
          
          const submitButton = e.submitter;
          const originalText = submitButton.innerHTML;
          submitButton.disabled = true;
          submitButton.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Validating...';
          
          fetch(validateUrl, {
            method: 'POST',
            headers: {
              'X-CSRFToken': csrfTokenValue,
              'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams(new FormData(form))
          })
          .then(response => {
            console.log('Validation response status:', response.status);
            if (!response.ok) {
              throw new Error(`Server error: ${response.status}`);
            }
            return response.json();
          })
          .then(data => {
            console.log('Validation response:', data);
            if (data.valid) {
              console.log('Validation passed, submitting form');
              const hiddenInput = document.createElement('input');
              hiddenInput.type = 'hidden';
              hiddenInput.name = 'submit_product';
              hiddenInput.value = '1';
              form.appendChild(hiddenInput);
              
              form.removeEventListener('submit', arguments.callee);
              form.submit();
            } else {
              console.log('Validation failed:', data.errors);
              showValidationErrors(data.errors || ['Validation failed']);
              submitButton.disabled = false;
              submitButton.innerHTML = originalText;
            }
          })
          .catch(error => {
            console.error('Validation error:', error);
            showValidationErrors(['An error occurred during validation. Please try again.']);
            submitButton.disabled = false;
            submitButton.innerHTML = originalText;
          });
        } else {
          console.log('Allowing normal form submission for:', e.submitter?.name);
        }
      });
    }
  
    function showValidationErrors(errors) {
      console.log('Showing validation errors:', errors);
      
      const existingErrors = form.querySelectorAll('.validation-errors');
      existingErrors.forEach(el => el.remove());
      
      const errorContainer = document.createElement('div');
      errorContainer.className = 'alert alert-danger mb-4 validation-errors';
      
      if (errors.length === 1) {
        errorContainer.textContent = errors[0];
      } else {
        const errorList = document.createElement('ul');
        errorList.className = 'mb-0';
        
        errors.forEach(error => {
          const li = document.createElement('li');
          li.textContent = error;
          errorList.appendChild(li);
        });
        
        errorContainer.appendChild(errorList);
      }
      
      const firstCard = form.querySelector('.card-body');
      if (firstCard) {
        firstCard.insertBefore(errorContainer, firstCard.firstChild);
        errorContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }
});