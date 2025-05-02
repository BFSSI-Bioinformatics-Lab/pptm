document.addEventListener('DOMContentLoaded', function() {
  console.log('Initializing enhanced upload functionality');
  
  // Configuration
  const config = {
    sections: ['barcode', 'nutrition', 'ingredients'],
    maxConcurrentUploads: 3
  };

  // State tracking
  const state = {
    counters: {
      barcode: 0,
      nutrition: 0, 
      ingredients: 0
    },
    activeUploads: 0,
    uploadResults: []
  };

  // File Uploader class for handling parallel uploads
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
  
    addFile(file, imageType, formPrefix, extraData = {}) {
      console.log(`Adding file to upload queue: ${formPrefix}, type: ${imageType}`);
      this.queue.push({ file, imageType, formPrefix, extraData });
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

  // Initialize uploader
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

  // Setup event listeners for Add More buttons
  document.querySelectorAll('.add-more-btn').forEach(button => {
    button.addEventListener('click', function() {
      const section = this.dataset.section;
      console.log(`Adding new upload section: ${section}`);
      addNewUploadSection(section);
    });
  });

  // Handle checkbox changes for multiple uploads
  setupMultipleUploadCheckboxes();

  // Initialize all existing file inputs
  document.querySelectorAll('input[type="file"]').forEach(input => {
    setupFileInput(input);
  });

  // Initialize form validation
  initializeFormValidation();

  // Initialize form submission handling
  setupFormSubmissionHandling();

  // FUNCTION DEFINITIONS
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
      
      // Initialize on page load
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
    
    // Setup for barcodes
    setupCheckbox(
      'id_has_multiple_barcodes',
      'barcodeUploadContainer',
      'barcode',
      'Add Barcode'
    );
    
    // Setup for nutrition facts
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
    
    // Set up remove button
    const removeBtn = uploadItem.querySelector('.remove-upload-btn');
    if (removeBtn) {
      removeBtn.addEventListener('click', function() {
        console.log(`Removing ${section} upload item ${index}`);
        uploadItem.remove();
      });
    }
    
    // Set up file input
    const fileInput = uploadItem.querySelector('input[type="file"]');
    if (fileInput) {
      setupFileInput(fileInput);
    }
    
    return uploadItem;
  }
  
  function replaceIndexPlaceholders(element, index) {
    // Replace in attributes
    if (element.attributes) {
      Array.from(element.attributes).forEach(attr => {
        if (attr.value.includes('{index}')) {
          attr.value = attr.value.replace(/{index}/g, index);
        }
      });
    }
    
    // Replace in text nodes
    if (element.nodeType === Node.TEXT_NODE && element.nodeValue.includes('{index}')) {
      element.nodeValue = element.nodeValue.replace(/{index}/g, index);
    }
    
    // Process children recursively
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
    
    // Setup drag and drop
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
      
      // Make the whole zone clickable
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
    
    // Parse input name to determine form prefix and image type
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
    
    console.log(`Preparing upload: ${formPrefix}, type: ${imageType}`);
    
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
    
    console.log(`Extra data for ${formPrefix}:`, extraData);
    
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
      
      const statusDiv = container.querySelector('.upload-status');
      const progressUI = container.querySelector('.upload-progress');
      
      if (result.success) {
        console.log(`Showing success UI for ${result.formPrefix}`);
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
        console.log(`Showing error UI for ${result.formPrefix}: ${result.error}`);
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
              console.log(`Retry clicked for ${result.formPrefix}`);
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
    console.log('Initializing form validation');
    const form = document.getElementById('combinedUploadForm');
    const submitButton = document.querySelector('button[name="submit"]');
    const productNameField = document.querySelector('input[name="product_name"]');

    if (form && submitButton && productNameField) {
      function updateSubmitButton() {
        const nameValue = productNameField.value.trim();
        const validationErrors = document.querySelector('.alert.alert-warning');
        const disabled = nameValue === '' || 
                       (validationErrors && validationErrors.children.length > 0) ||
                       state.activeUploads > 0;
        
        submitButton.disabled = disabled;
        if (disabled) {
          console.log('Submit button disabled', {
            emptyName: nameValue === '',
            hasErrors: !!(validationErrors && validationErrors.children.length > 0),
            activeUploads: state.activeUploads
          });
        }
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
    console.log('Setting up form submission handling');
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

          // Check required files
          const requiredTypes = {
            'front': 'Front of package',
            'back': 'Back of package',
            'barcode': 'Barcode',
            'nutrition': 'Nutrition facts',
            'ingredients': 'Ingredients'
          };
          
          const missingTypes = [];
          
          for (const [type, label] of Object.entries(requiredTypes)) {
            let found = false;
            
            if (type === 'front' || type === 'back') {
              found = !!document.querySelector(`.existing-image img[alt="${type} image"]`) || 
                     !!document.querySelector(`[name="image_${type}-image"]`).files.length;
            } else {
              found = !!document.querySelector(`.existing-image img[alt="${label}"]`) || 
                     !!document.querySelector(`[name="${type}-image"]`).files.length;
            }
            
            if (!found) {
              missingTypes.push(label);
            }
          }
          
          if (missingTypes.length > 0) {
            hasErrors = true;
            const li = document.createElement('li');
            li.textContent = `Missing required images: ${missingTypes.join(', ')}`;
            errorList.appendChild(li);
          }

          // Check multiple barcodes if needed
          const hasMultipleBarcodes = document.getElementById('id_has_multiple_barcodes').checked;
          if (hasMultipleBarcodes) {
            const barcodeCount = document.querySelectorAll('.existing-image img[alt="Barcode"]').length + 
                               document.querySelectorAll('.barcode-upload input[type="file"]').length;
            
            if (barcodeCount < 2) {
              hasErrors = true;
              const li = document.createElement('li');
              li.textContent = 'Multiple barcodes were indicated but not all were uploaded';
              errorList.appendChild(li);
            }
          }
          
          // Check multiple nutrition facts if needed
          const hasMultipleNutrition = document.getElementById('id_has_multiple_nutrition_facts').checked;
          if (hasMultipleNutrition) {
            const nutritionCount = document.querySelectorAll('.existing-image img[alt="Nutrition Facts"]').length + 
                                 document.querySelectorAll('.nutrition-upload input[type="file"]').length;
            
            if (nutritionCount < 2) {
              hasErrors = true;
              const li = document.createElement('li');
              li.textContent = 'Multiple nutrition facts were indicated but not all were uploaded';
              errorList.appendChild(li);
            }
          }

          if (hasErrors) {
            console.warn('Form validation failed', errorList.innerHTML);
            e.preventDefault();
            const firstCard = form.querySelector('.card-body');
            firstCard.insertBefore(errorContainer, firstCard.firstChild);
            window.scrollTo({ top: 0, behavior: 'smooth' });
            return;
          }
          
          console.log('Form validation passed, preparing for submission');
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
              console.log(`Added hidden field for AJAX upload: ${fieldName}`);
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
              console.log(`Added filename reference: ${fileNameField} = ${fileNameInput.value}`);
            }
          }
        });
      });
    }
  }

  function setupServerSideValidation() {
    console.log('Setting up server-side validation');
    const form = document.getElementById('combinedUploadForm');
    const submitButton = document.querySelector('button[name="complete_submission"]');
    
    if (!form || !submitButton) return;
    
    // Run validation before form submission
    form.addEventListener('submit', function(e) {
      if (e.submitter && e.submitter.name === 'submit_product') {
        console.log('Submit button clicked, validating form with server');
        e.preventDefault();
        
        // First check if there are active uploads
        if (state.activeUploads > 0) {
          showValidationErrors([
            'Please wait for all uploads to complete before submitting'
          ]);
          return;
        }
        
        // Get the product ID from the form action URL or a hidden field
        const productId = document.getElementById('product-id').value;
        
        // Get the CSRF token
        const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
        
        // Perform AJAX validation
        const validateUrl = document.getElementById('ajax-validate-url')?.value;
        if (!validateUrl) {
          console.error('Validation URL not found in hidden element');
          form.submit(); // Fall back to standard form submission
          return;
        }
        console.log(`Using validation URL: ${validateUrl}`);
        fetch(validateUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken
          },
          body: new URLSearchParams(new FormData(form))
        })
        .then(response => response.json())
        .then(data => {
          console.log('Validation result:', data);
          
          if (data.valid) {
            console.log('Form is valid, submitting');
            form.submit();
          } else {
            showValidationErrors(data.errors);
          }
        })
        .catch(error => {
          console.error('Validation error:', error);
          showValidationErrors(['An error occurred during validation. Please try again.']);
        });
      }
    });
    
    function showValidationErrors(errors) {
      // Remove any existing error containers
      const existingErrors = form.querySelectorAll('.alert.alert-danger');
      existingErrors.forEach(el => el.remove());
      
      // Create error container
      const errorContainer = document.createElement('div');
      errorContainer.className = 'alert alert-danger mb-4';
      const errorList = document.createElement('ul');
      errorList.className = 'mb-0';
      
      // Add each error
      errors.forEach(error => {
        const li = document.createElement('li');
        li.textContent = error;
        errorList.appendChild(li);
      });
      
      errorContainer.appendChild(errorList);
      
      // Add to form
      const firstCard = form.querySelector('.card-body');
      firstCard.insertBefore(errorContainer, firstCard.firstChild);
      
      // Scroll to top
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }  

  setupServerSideValidation();
});