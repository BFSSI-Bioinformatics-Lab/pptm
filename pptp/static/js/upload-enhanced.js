document.addEventListener('DOMContentLoaded', function() {
  // Configuration
  const config = {
    sections: ['barcode', 'nutrition', 'ingredients'],
    maxConcurrentUploads: 3
  };

  // State tracking
  const state = {
    counters: {
      'barcode': 0,
      'nutrition': 0, 
      'ingredients': 0
    },
    activeUploads: 0,
    uploadResults: []
  };

  // File Uploader class for handling parallel uploads
  class FileUploader {
    constructor(options) {
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
  
    addFile(file, imageType, formPrefix, extraData = {}) {
      this.queue.push({
        file,
        imageType,
        formPrefix,
        extraData
      });
      
      this.processQueue();
      return this;
    }
    
    processQueue() {
      if (this.queue.length === 0 && this.activeUploads === 0) {
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
      
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      
      formData.append('file', item.file);
      formData.append('image_type', item.imageType);
      
      Object.keys(item.extraData).forEach(key => {
        formData.append(key, item.extraData[key]);
      });
      
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
            this.results.push({
              file: item.file,
              formPrefix: item.formPrefix,
              success: false,
              imageType: item.imageType,
              error: response.error || `Server error: ${xhr.status}`
            });
            
            this.onError(item, response.error || `Server error: ${xhr.status}`);
          }
        } catch (e) {
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
      
      // Get CSRF token
      const csrfToken = this.csrfToken || document.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
      if (csrfToken) {
        xhr.setRequestHeader('X-CSRFToken', csrfToken);
      }
      
      xhr.send(formData);
    }
  }

  // Initialize uploader
  const uploader = new FileUploader({
    productId: typeof productId !== 'undefined' ? productId : null,
    csrfToken: typeof csrfToken !== 'undefined' ? csrfToken : null,
    maxConcurrent: config.maxConcurrentUploads,
    onProgress: (item, percentage) => {
      updateProgressUI(item.formPrefix, percentage);
    },
    onComplete: (results) => {
      showCompletionStatus(results);
    },
    onError: (item, error) => {
      showErrorMessage(item.formPrefix, error);
    }
  });

  // Setup event listeners for Add More buttons
  document.querySelectorAll('.add-more-btn').forEach(button => {
    button.addEventListener('click', function() {
      const section = this.dataset.section;
      addNewUploadSection(section);
    });
  });

  // Initialize all existing file inputs
  document.querySelectorAll('input[type="file"]').forEach(input => {
    setupFileInput(input);
  });

  // Initialize form validation
  initializeFormValidation();

  // Initialize form submission handling
  setupFormSubmissionHandling();

  // FUNCTION DEFINITIONS

  function addNewUploadSection(section) {
    state.counters[section]++;
    const index = state.counters[section];

    const template = document.getElementById(`${section}Template`).innerHTML
      .replace(/{index}/g, index);

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = template;
    const newElement = tempDiv.firstElementChild;

    document.getElementById(`${section}UploadContainer`).appendChild(newElement);

    newElement.querySelector('.remove-upload-btn')?.addEventListener('click', function() {
      newElement.remove();
    });

    setupFileInput(newElement.querySelector('input[type="file"]'));
  }

  function setupFileInput(input) {
    if (!input) return;
    
    const cardBody = input.closest('.card-body');
    if (!cardBody) {
      return;
    }
    
    const previewContainer = cardBody.querySelector('.upload-preview');
    
    if (!previewContainer) {
      return;
    }
    
    input.addEventListener('change', function() {
      
      if (this.files && this.files[0]) {
        const file = this.files[0];
        
        updatePreview(file, previewContainer);
        
        prepareFileForUpload(file, this);
      }
    });
  }
    
  function updatePreview(file, previewContainer) {
    previewContainer.innerHTML = '';
    previewContainer.classList.remove('show');
    
    if (!file.type.match('image.*')) {
      return;
    }

    const reader = new FileReader();

    reader.onload = function(e) {
      previewContainer.classList.add('show');

      const img = document.createElement('img');
      img.src = e.target.result;
      img.classList.add('img-fluid', 'rounded', 'mb-2');
      img.style.maxHeight = '200px';

      previewContainer.appendChild(img);
    };

    reader.readAsDataURL(file);
  }

  function prepareFileForUpload(file, fileInput) {
    if (!file) return;
    
    // Store original filename
    fileInput.dataset.originalFileName = file.name;
    
    // Extract form prefix and image type from input name
    const inputName = fileInput.name;
    let formPrefix = '';
    let imageType = '';
    
    if (inputName.startsWith('image_')) {
      // Product image types (image_front-image, etc.)
      const parts = inputName.split('-')[0];
      formPrefix = parts;
      imageType = parts.replace('image_', '');
    } else {
      // Other image types (barcode-image, nutrition-image, etc.)
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
      console.error("Could not determine image type from input name:", inputName);
      return;
    }
    
    // Collect additional form data
    const extraData = {};
    
    // For barcodes, get the barcode number if available
    if (imageType === 'barcode') {
      const barcodeNumInput = document.querySelector(`[name="${formPrefix}-barcode_number"]`);
      if (barcodeNumInput) {
        extraData.barcode_number = barcodeNumInput.value || '';
      }
    }
    
    // Get notes if available
    const notesInput = document.querySelector(`[name="${formPrefix}-notes"]`);
    if (notesInput) {
      extraData.notes = notesInput.value || '';
    }
    
    // Create progress UI
    createProgressUI(fileInput, formPrefix);
    
    // Add to uploader queue
    uploader.addFile(file, imageType, formPrefix, extraData);
  }

  function createProgressUI(fileInput, formPrefix) {
    const container = fileInput.closest('.card-body');
    if (!container) return;
    
    // Check if progress UI already exists
    let progressContainer = container.querySelector('.upload-progress');
    if (!progressContainer) {
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
      
      const statusDiv = container.querySelector('.upload-status');
      const progressUI = container.querySelector('.upload-progress');
      
      if (result.success) {
        if (statusDiv) {
          statusDiv.textContent = 'Upload complete!';
          statusDiv.classList.add('text-success');
        }
        
        if (progressUI) {
          const successDiv = document.createElement('div');
          successDiv.className = 'mt-2 d-flex justify-content-between align-items-center';
          successDiv.innerHTML = `
            <span class="text-success"><i class="bi bi-check-circle"></i> Upload successful</span>
            <button type="button" class="btn btn-sm btn-outline-primary refresh-btn">
              <i class="bi bi-arrow-clockwise"></i> Refresh Page
            </button>
          `;
          progressUI.appendChild(successDiv);
          
          const refreshBtn = successDiv.querySelector('.refresh-btn');
          if (refreshBtn) {
            refreshBtn.addEventListener('click', function() {
              window.location.reload();
            });
          }
        }
      } else {
        if (statusDiv) {
          statusDiv.textContent = `Error: ${result.error}`;
          statusDiv.classList.add('text-danger');
        }
        
        if (progressUI) {
          const errorDiv = document.createElement('div');
          errorDiv.className = 'mt-2';
          errorDiv.innerHTML = `
            <button type="button" class="btn btn-sm btn-outline-danger retry-btn">
              <i class="bi bi-arrow-repeat"></i> Retry
            </button>
          `;
          progressUI.appendChild(errorDiv);
          
          const retryBtn = errorDiv.querySelector('.retry-btn');
          if (retryBtn) {
            retryBtn.addEventListener('click', function() {
              fileInput.value = '';
              if (progressUI) {
                progressUI.remove();
              }
            });
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
    const formEl = document.getElementById('combinedUploadForm');
    const submitButton = document.querySelector('button[name="submit"]');
    const productNameField = document.querySelector('input[name="product_name"]');

    if (formEl && submitButton && productNameField) {
      function updateSubmitButton() {
        const nameValue = productNameField.value.trim();
        const validationErrors = document.querySelector('.validation_errors');

        submitButton.disabled = nameValue === '' || 
                               (validationErrors && validationErrors.children.length > 0) ||
                               state.activeUploads > 0;
      }

      // Initial update
      updateSubmitButton();

      // Add event listeners
      productNameField.addEventListener('input', updateSubmitButton);
      productNameField.addEventListener('change', updateSubmitButton);
      
      // Check active uploads periodically
      setInterval(updateSubmitButton, 1000);
    }
  }

  function setupFormSubmissionHandling() {
    const form = document.getElementById('combinedUploadForm');
    
    if (form) {
      form.addEventListener('submit', function(e) {
        // Handle validation
        if (e.submitter && e.submitter.name === 'submit') {
          let hasErrors = false;
          const errorContainer = document.createElement('div');
          errorContainer.className = 'alert alert-danger mb-4';
          const errorList = document.createElement('ul');
          errorList.className = 'mb-0';
          errorContainer.appendChild(errorList);

          // Remove any existing error containers
          const existingErrors = form.querySelectorAll('.alert.alert-danger');
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

          // Check for active uploads
          if (state.activeUploads > 0) {
            hasErrors = true;
            const li = document.createElement('li');
            li.textContent = 'Please wait for all uploads to complete before submitting';
            errorList.appendChild(li);
          }

          if (hasErrors) {
            e.preventDefault();
            const firstCard = form.querySelector('.card-body');
            firstCard.insertBefore(errorContainer, firstCard.firstChild);
            window.scrollTo({ top: 0, behavior: 'smooth' });
            return;
          }
        }
        
        // Process file inputs that were uploaded via AJAX
        const fileInputs = form.querySelectorAll('input[type="file"]');
        fileInputs.forEach(input => {
          const container = input.closest('.card-body');
          if (!container) return;
          
          const progressUI = container.querySelector('.upload-progress');
          
          if (progressUI) {
            // Add hidden input to indicate this file was uploaded via AJAX
            const fieldName = input.name.replace('-image', '-already_uploaded');
            let hiddenInput = form.querySelector(`input[name="${fieldName}"]`);
            
            if (!hiddenInput) {
              hiddenInput = document.createElement('input');
              hiddenInput.type = 'hidden';
              hiddenInput.name = fieldName;
              hiddenInput.value = 'true';
              form.appendChild(hiddenInput);
            }
            
            // Clear the file input to prevent double-upload
            input.value = '';
            
            // Add the original filename for reference
            const fileNameField = input.name.replace('-image', '-ajax_filename');
            let fileNameInput = form.querySelector(`input[name="${fileNameField}"]`);
            
            if (!fileNameInput) {
              fileNameInput = document.createElement('input');
              fileNameInput.type = 'hidden';
              fileNameInput.name = fileNameField;
              fileNameInput.value = input.dataset.originalFileName || 'File uploaded via AJAX';
              form.appendChild(fileNameInput);
            }
          }
        });
      });
    }
  }
});