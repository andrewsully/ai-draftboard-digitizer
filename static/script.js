// Global variables
let currentStep = 1;
let uploadedImage = null;
let croppedImage = null;
let colorProfiles = {};
let isColorPicking = false;
let currentPickingPosition = null;

// Advanced crop variables
let currentCropMode = 'simple';
let cornerPoints = [];
let currentCornerIndex = 0;

// Zoom and pan variables
let currentZoom = 1;
let minZoom = 0.1;
let maxZoom = 5;
let panX = 0;
let panY = 0;
let isPanning = false;
let lastPanX = 0;
let lastPanY = 0;

// Manual correction variables
let unrecognizedCells = [];
let currentCorrectionIndex = 0;
let allPlayerNames = [];

// DOM elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const cropImage = document.getElementById('cropImage');
const cropBox = document.getElementById('cropBox');
const cropOverlay = document.getElementById('cropOverlay');
const croppedPreview = document.getElementById('croppedPreview');

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing application...');
    
    // Check if all required elements exist
    const requiredElements = ['uploadArea', 'fileInput', 'cropImage', 'cropBox', 'cropOverlay', 'croppedPreview'];
    const missingElements = [];
    
    requiredElements.forEach(id => {
        const element = document.getElementById(id);
        if (!element) {
            missingElements.push(id);
        }
    });
    
    if (missingElements.length > 0) {
        console.error('Missing elements:', missingElements);
        alert('Error: Some page elements are missing. Please refresh the page.');
        return;
    }
    
    console.log('All elements found, initializing...');
    initializeUploadArea();
    initializeCropArea();
    initializeColorPicker();
    console.log('Application initialized successfully!');
});

// Upload functionality
function initializeUploadArea() {
    uploadArea.addEventListener('click', () => fileInput.click());
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });
}

function handleFileUpload(file) {
    console.log('Handling file upload:', file.name, file.type, file.size);
    
    if (!file.type.startsWith('image/')) {
        showStatus('uploadStatus', 'Please select an image file.', 'error');
        return;
    }

    showStatus('uploadStatus', 'Uploading image...', 'info');
    
    const reader = new FileReader();
    reader.onload = function(e) {
        console.log('File read successfully');
        uploadedImage = e.target.result;
        cropImage.src = uploadedImage;
        showStatus('uploadStatus', 'Image loaded successfully!', 'success');
        setTimeout(() => nextStep(), 1000);
    };
    
    reader.onerror = function() {
        console.error('FileReader error:', reader.error);
        showStatus('uploadStatus', 'Error reading file: ' + reader.error, 'error');
    };
    
    reader.readAsDataURL(file);
    
    // Upload to server
    const formData = new FormData();
    formData.append('image', file);
    
    console.log('Sending to server...');
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log('Server response status:', response.status);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Server response:', data);
        if (!data.success) {
            showStatus('uploadStatus', data.error, 'error');
        } else {
            showStatus('uploadStatus', 'Image uploaded to server successfully!', 'success');
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        showStatus('uploadStatus', 'Upload failed: ' + error.message, 'error');
    });
}

// Crop functionality
function initializeCropBox() {
    const overlayRect = cropOverlay.getBoundingClientRect();
    cropBox.style.left = '0px';
    cropBox.style.top = '0px';
    cropBox.style.width = overlayRect.width + 'px';
    cropBox.style.height = overlayRect.height + 'px';
}

function initializeCropArea() {
    let isDragging = false;
    let isResizing = false;
    let resizeHandle = null;
    let startX, startY, startLeft, startTop, startWidth, startHeight;

    // Create resize handles
    const handles = ['nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w'];
    handles.forEach(handle => {
        const handleElement = document.createElement('div');
        handleElement.className = `resize-handle resize-${handle}`;
        handleElement.dataset.handle = handle;
        cropBox.appendChild(handleElement);
    });

    // Initialize crop box when image loads
    cropImage.addEventListener('load', initializeCropBox);
    
    // Handle mouse down events
    cropBox.addEventListener('mousedown', (e) => {
        const handle = e.target.dataset.handle;
        if (handle) {
            // Resizing
            isResizing = true;
            resizeHandle = handle;
            startX = e.clientX;
            startY = e.clientY;
            startLeft = parseInt(cropBox.style.left);
            startTop = parseInt(cropBox.style.top);
            startWidth = parseInt(cropBox.style.width);
            startHeight = parseInt(cropBox.style.height);
        } else {
            // Moving
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            startLeft = parseInt(cropBox.style.left);
            startTop = parseInt(cropBox.style.top);
        }
        e.preventDefault();
    });
    
    // Handle mouse move events
    document.addEventListener('mousemove', (e) => {
        if (!isDragging && !isResizing) return;
        
        const deltaX = e.clientX - startX;
        const deltaY = e.clientY - startY;
        const overlayRect = cropOverlay.getBoundingClientRect();
        
        if (isDragging) {
            // Move the crop box
            const newLeft = Math.max(0, Math.min(startLeft + deltaX, overlayRect.width - parseInt(cropBox.style.width)));
            const newTop = Math.max(0, Math.min(startTop + deltaY, overlayRect.height - parseInt(cropBox.style.height)));
            
            cropBox.style.left = newLeft + 'px';
            cropBox.style.top = newTop + 'px';
        } else if (isResizing) {
            // Resize the crop box
            let newLeft = startLeft;
            let newTop = startTop;
            let newWidth = startWidth;
            let newHeight = startHeight;
            
            switch (resizeHandle) {
                case 'nw': // Top-left corner
                    newLeft = Math.max(0, Math.min(startLeft + deltaX, startLeft + startWidth - 50));
                    newTop = Math.max(0, Math.min(startTop + deltaY, startTop + startHeight - 50));
                    newWidth = startWidth - (newLeft - startLeft);
                    newHeight = startHeight - (newTop - startTop);
                    break;
                case 'ne': // Top-right corner
                    newTop = Math.max(0, Math.min(startTop + deltaY, startTop + startHeight - 50));
                    newWidth = Math.max(50, Math.min(startWidth + deltaX, overlayRect.width - newLeft));
                    newHeight = startHeight - (newTop - startTop);
                    break;
                case 'sw': // Bottom-left corner
                    newLeft = Math.max(0, Math.min(startLeft + deltaX, startLeft + startWidth - 50));
                    newWidth = startWidth - (newLeft - startLeft);
                    newHeight = Math.max(50, Math.min(startHeight + deltaY, overlayRect.height - newTop));
                    break;
                case 'se': // Bottom-right corner
                    newWidth = Math.max(50, Math.min(startWidth + deltaX, overlayRect.width - newLeft));
                    newHeight = Math.max(50, Math.min(startHeight + deltaY, overlayRect.height - newTop));
                    break;
                case 'n': // Top edge
                    newTop = Math.max(0, Math.min(startTop + deltaY, startTop + startHeight - 50));
                    newHeight = startHeight - (newTop - startTop);
                    break;
                case 's': // Bottom edge
                    newHeight = Math.max(50, Math.min(startHeight + deltaY, overlayRect.height - newTop));
                    break;
                case 'e': // Right edge
                    newWidth = Math.max(50, Math.min(startWidth + deltaX, overlayRect.width - newLeft));
                    break;
                case 'w': // Left edge
                    newLeft = Math.max(0, Math.min(startLeft + deltaX, startLeft + startWidth - 50));
                    newWidth = startWidth - (newLeft - startLeft);
                    break;
            }
            
            cropBox.style.left = newLeft + 'px';
            cropBox.style.top = newTop + 'px';
            cropBox.style.width = newWidth + 'px';
            cropBox.style.height = newHeight + 'px';
        }
    });
    
    // Handle mouse up events
    document.addEventListener('mouseup', () => {
        isDragging = false;
        isResizing = false;
        resizeHandle = null;
    });
    
    // Allow clicking to set crop area (only if not dragging/resizing)
    cropOverlay.addEventListener('click', (e) => {
        if (isDragging || isResizing || e.target.classList.contains('resize-handle')) return;
        
        const rect = cropOverlay.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Set crop box to a reasonable size around the click point
        const size = 200;
        const newLeft = Math.max(0, Math.min(x - size/2, rect.width - size));
        const newTop = Math.max(0, Math.min(y - size/2, rect.height - size));
        
        cropBox.style.left = newLeft + 'px';
        cropBox.style.top = newTop + 'px';
        cropBox.style.width = size + 'px';
        cropBox.style.height = size + 'px';
    });
}

function performCrop() {
    const rect = cropBox.getBoundingClientRect();
    const overlayRect = cropOverlay.getBoundingClientRect();
    
    // Get the actual image element
    const imageElement = document.getElementById('cropImage');
    
    // Calculate scale factors between displayed and natural image size
    const scaleX = imageElement.naturalWidth / imageElement.offsetWidth;
    const scaleY = imageElement.naturalHeight / imageElement.offsetHeight;
    
    console.log('Scale factors:', { scaleX, scaleY });
    console.log('Image natural size:', { width: imageElement.naturalWidth, height: imageElement.naturalHeight });
    console.log('Image displayed size:', { width: imageElement.offsetWidth, height: imageElement.offsetHeight });
    
    // Calculate crop coordinates relative to the displayed image
    const displayX = rect.left - overlayRect.left;
    const displayY = rect.top - overlayRect.top;
    const displayWidth = rect.width;
    const displayHeight = rect.height;
    
    // Scale coordinates to match the original image size
    const x = Math.round(displayX * scaleX);
    const y = Math.round(displayY * scaleY);
    const width = Math.round(displayWidth * scaleX);
    const height = Math.round(displayHeight * scaleY);
    
    console.log('Crop coordinates:', {
        display: { x: displayX, y: displayY, width: displayWidth, height: displayHeight },
        scaled: { x, y, width, height }
    });
    
    // Get draft configuration
    const teamCount = parseInt(document.getElementById('teamCount').value);
    const roundCount = parseInt(document.getElementById('roundCount').value);
    
    fetch('/crop', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            x: x,
            y: y,
            width: width,
            height: height,
            teamCount: teamCount,
            roundCount: roundCount
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            croppedImage = data.cropped_image;
            croppedPreview.src = croppedImage;
            
            // Log image dimensions when it loads
            croppedPreview.onload = function() {
                console.log('Cropped image loaded:', {
                    naturalWidth: this.naturalWidth,
                    naturalHeight: this.naturalHeight,
                    displayWidth: this.offsetWidth,
                    displayHeight: this.offsetHeight
                });
                
                // Force image to display at natural size
                this.style.width = this.naturalWidth + 'px';
                this.style.height = this.naturalHeight + 'px';
                this.style.maxWidth = 'none';
                this.style.maxHeight = 'none';
                this.style.minWidth = 'auto';
                this.style.minHeight = 'auto';
                
                console.log('Forced image size:', {
                    width: this.style.width,
                    height: this.style.height
                });
            };
            
            showStatus('cropStatus', 'Image cropped successfully!', 'success');
            setTimeout(() => nextStep(), 1000);
        } else {
            showStatus('cropStatus', data.error, 'error');
        }
    })
    .catch(error => {
        showStatus('cropStatus', 'Cropping failed: ' + error.message, 'error');
    });
}

// Color picker functionality
function initializeColorPicker() {
    croppedPreview.addEventListener('click', handleColorPick);
}

function handleColorPick(e) {
    if (!isColorPicking) return;
    
    const rect = croppedPreview.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // Get color from image
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = croppedPreview.naturalWidth;
    canvas.height = croppedPreview.naturalHeight;
    
    ctx.drawImage(croppedPreview, 0, 0);
    const imageData = ctx.getImageData(x, y, 1, 1);
    const [r, g, b] = imageData.data;
    
    // Convert RGB to HSV
    const hsv = rgbToHsv(r, g, b);
    
    // Store color profile
    colorProfiles[currentPickingPosition] = {
        rgb: [r, g, b],
        hsv: hsv
    };
    
    // Update color preview
    const colorPreview = document.getElementById(currentPickingPosition.toLowerCase() + 'Color');
    colorPreview.style.backgroundColor = `rgb(${r}, ${g}, ${b})`;
    
    // Remove active class from current position
    document.getElementById(`colorItem${currentPickingPosition}`).classList.remove('active');
    
    // Auto-advance to next position
    const positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST'];
    const currentIndex = positions.indexOf(currentPickingPosition);
    const nextIndex = (currentIndex + 1) % positions.length;
    const nextPosition = positions[nextIndex];
    
    // Reset picking state
    isColorPicking = false;
    croppedPreview.classList.remove('color-picking');
    
    showStatus('calibrationStatus', `${currentPickingPosition} color selected!`, 'success');
    
    // Check if all colors are selected
    const allSelected = checkColorCompletion();
    
    // Auto-select next position if not all colors are selected
    if (!allSelected) {
        pickColor(nextPosition);
    }
}

function pickColor(position) {
    isColorPicking = true;
    currentPickingPosition = position;
    croppedPreview.classList.add('color-picking');
    
    // Remove active class from all color items
    document.querySelectorAll('.color-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Add active class to current position
    document.getElementById(`colorItem${position}`).classList.add('active');
    
    showStatus('calibrationStatus', `Click on a ${position} sticker in the image`, 'info');
}

function checkColorCompletion() {
    const positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST'];
    const allSelected = positions.every(pos => colorProfiles[pos]);
    
    const calibrateBtn = document.getElementById('calibrateBtn');
    calibrateBtn.disabled = !allSelected;
    
    if (allSelected) {
        showStatus('calibrationStatus', 'All colors selected! Click "Complete Calibration" to continue.', 'success');
    }
    
    return allSelected;
}

function calibrateColors() {
    fetch('/calibrate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            colors: colorProfiles
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showStatus('calibrationStatus', 'Color calibration completed!', 'success');
            setTimeout(() => nextStep(), 1000);
        } else {
            showStatus('calibrationStatus', data.error, 'error');
        }
    })
    .catch(error => {
        showStatus('calibrationStatus', 'Calibration failed: ' + error.message, 'error');
    });
}

async function autoDetectColors() {
    try {
        const btn = document.getElementById('autoDetectBtn');
        if (btn) btn.disabled = true;
        showStatus('calibrationStatus', 'Detecting colors automatically...', 'info');

        const response = await fetch('/auto_detect_colors', { method: 'POST' });
        const data = await response.json();

        if (!data.success) {
            showStatus('calibrationStatus', data.error || 'Auto-detect failed', 'error');
            if (btn) btn.disabled = false;
            return;
        }

        // Update global profiles and previews
        const detected = data.colorProfiles || {};
        const positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST'];
        positions.forEach(pos => {
            if (detected[pos]) {
                colorProfiles[pos] = {
                    rgb: detected[pos].rgb,
                    hsv: detected[pos].hsv
                };
                const [r, g, b] = detected[pos].rgb;
                const swatch = document.getElementById(pos.toLowerCase() + 'Color');
                if (swatch) swatch.style.backgroundColor = `rgb(${r}, ${g}, ${b})`;
            }
        });

        // Enable calibration button if all 6 present
        const allSelected = ['QB','RB','WR','TE','K','DST'].every(p => colorProfiles[p]);
        const calibrateBtn = document.getElementById('calibrateBtn');
        if (calibrateBtn) calibrateBtn.disabled = !allSelected;

        showStatus('calibrationStatus', allSelected ? 'Colors detected! You can refine by clicking Pick Color or proceed.' : 'Partial detection complete. Please fill missing positions.', allSelected ? 'success' : 'info');

    } catch (err) {
        showStatus('calibrationStatus', 'Auto-detect failed: ' + err.message, 'error');
    } finally {
        const btn = document.getElementById('autoDetectBtn');
        if (btn) btn.disabled = false;
    }
}

// Processing functionality
function processBoard() {
    showLoading('Processing your draft board...');
    
    // Start real progress polling
    const progressInterval = setInterval(async () => {
        try {
            const response = await fetch('/progress');
            const progress = await response.json();
            
            const loadingText = document.getElementById('loadingText');
            if (progress.total > 0) {
                loadingText.textContent = `Processing your draft board... ${Math.round(progress.percentage)}% (${progress.current}/${progress.total} cells)`;
            } else {
                loadingText.textContent = `Processing your draft board...`;
            }
        } catch (error) {
            console.log('Progress check failed:', error);
        }
    }, 200); // Check every 200ms for more responsive updates
    
    fetch('/process', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        clearInterval(progressInterval);
        hideLoading();
        if (data.success) {
            // Expose OCR comparison for manual review
            if (data.debug_ocr) {
                window.debugOcrCompare = data.debug_ocr;
                console.group('OCR Comparison (ROI vs Whole-Cell)');
                let roiWins = 0, wholeWins = 0, ties = 0;
                data.debug_ocr.forEach(entry => {
                    console.group(`Cell r${entry.row} c${entry.col}`);
                    console.log('ROI:', entry.roi);
                    console.log('WHOLE:', entry.whole);
                    console.log('CHOSEN:', entry.chosen);
                    if (entry.chosen === 'roi') roiWins++;
                    else if (entry.chosen === 'whole') wholeWins++;
                    else ties++;
                    console.groupEnd();
                });
                const total = data.debug_ocr.length || 1;
                const roiPct = ((roiWins / total) * 100).toFixed(1);
                const wholePct = ((wholeWins / total) * 100).toFixed(1);
                const tiePct = ((ties / total) * 100).toFixed(1);
                console.log(`Totals → ROI: ${roiWins} (${roiPct}%), WHOLE: ${wholeWins} (${wholePct}%), Ties: ${ties} (${tiePct}%)`);
                console.groupEnd();
            }
            displayResults(data);

            // Check for unrecognized cells that need manual correction
            if (data.unrecognized_cells && data.unrecognized_cells.length > 0) {
                // Store unrecognized cells for manual correction
                unrecognizedCells = data.unrecognized_cells;
                currentCorrectionIndex = 0;

                // Show manual correction modal instead of proceeding to next step
                showManualCorrectionModal();
            } else {
                // No unrecognized cells, proceed to next step
                nextStep();
            }
        } else {
            showStatus('processingStatus', data.error, 'error');
        }
    })
    .catch(error => {
        clearInterval(progressInterval);
        hideLoading();
        showStatus('processingStatus', 'Processing failed: ' + error.message, 'error');
    });
}

function displayResults(data) {
    const summary = document.getElementById('resultsSummary');
    const tbody = document.getElementById('resultsBody');
    
    // Display summary
    const manualCorrections = data.manual_corrections || 0;
    summary.innerHTML = `
        <h3>Processing Complete!</h3>
        <p><strong>Total Cells:</strong> ${data.total_cells}</p>
        <p><strong>Successful Matches:</strong> ${data.successful_matches}</p>
        ${manualCorrections > 0 ? `<p><strong>Manual Corrections:</strong> ${manualCorrections}</p>` : ''}
        <p><strong>Success Rate:</strong> ${data.success_rate}</p>
    `;
    
    // Display results table with confidence tooltips
    tbody.innerHTML = '';
    data.results.forEach(result => {
        const row = document.createElement('tr');
        const isManualCorrection = result.confidence === 100.0;
        const teamIndex = result.col; // 0-based
        const teamLabel = (window.teamNames && window.teamNames[teamIndex]) ? window.teamNames[teamIndex] : `Team ${teamIndex + 1}`;
        row.innerHTML = `
            <td>${result.pick}</td>
            <td>${result.player} ${isManualCorrection ? '<span style="color: #2c5aa0; font-size: 12px;">(manual)</span>' : ''}<div style="font-size: 11px; color: #718096;">${teamLabel}</div></td>
            <td>${result.position}</td>
            <td>${result.team}</td>
            <td>${result.bye}</td>
            <td class="confidence-cell">
                ${result.confidence.toFixed(1)}%
                <div class="confidence-tooltip">
                    <strong>Confidence Breakdown:</strong><br>
                    Firstname: ${(result.score_breakdown?.firstname || 0).toFixed(1)} / 15<br>
                    Lastname: ${(result.score_breakdown?.lastname || 0).toFixed(1)} / 40<br>
                    Team: ${(result.score_breakdown?.team || 0).toFixed(1)} / 15<br>
                    Bye: ${(result.score_breakdown?.bye || 0).toFixed(1)} / 10<br>
                    Color Pos: ${(result.score_breakdown?.color_pos || 0).toFixed(1)} / 15<br>
                    OCR Pos: ${(result.score_breakdown?.ocr_pos || 0).toFixed(1)} / 10<br>
                    Liklihood gap to Runners Up: ${(result.score_breakdown?.draft_likelihood || 0).toFixed(1)} / 20 (Weighted) <br>
                    ${isManualCorrection ? '<em>Manual Correction</em>' : ''}
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
    
    // Generate team rosters view
    generateTeamRosters(data.results);
    
    // Store results for debug view
    window.debugResults = data.results;
    window.debugOcr = data.debug_ocr || [];
    window.cellRois = data.cell_rois || [];
    window.colorProfiles = data.colorProfiles || {};
    
    // Also store the color profiles from the current session
    if (colorProfiles && Object.keys(colorProfiles).length > 0) {
        window.colorProfiles = colorProfiles;
    }
}

// Download functionality
function downloadResults(filetype) {
    window.open(`/download/${filetype}`, '_blank');
}

// Utility functions
function nextStep() {
    const currentEl = document.getElementById(`step${currentStep}`);
    if (currentEl) currentEl.style.display = 'none';
    // Guard against advancing past the final step
    if (currentStep >= 6) {
        currentStep = 6;
    } else {
        currentStep++;
    }
    const nextEl = document.getElementById(`step${currentStep}`);
    if (nextEl) nextEl.style.display = 'block';
    
    // If moving to crop step, initialize crop box to full image size
    if (currentStep === 3) {
        setTimeout(() => {
            initializeCropImages();
        }, 100);
    }
    
    // If moving to color calibration step, select QB by default
    if (currentStep === 4) {
        setTimeout(() => {
            pickColor('QB');
        }, 100);
    }

    // If moving to draft configuration, render team names and preview
    if (currentStep === 2) {
        setTimeout(() => {
            renderTeamNames();
            const img = document.getElementById('configPreviewImage');
            if (img && uploadedImage) img.src = uploadedImage;
        }, 50);
    }
}

function initializeCropImages() {
    // Set both crop images to the uploaded image
    document.getElementById('cropImage').src = uploadedImage;
    document.getElementById('advancedCropImage').src = uploadedImage;
    
    // Initialize simple crop box
    initializeCropBox();
}

// Team Names handling
function renderTeamNames() { initTeamQuickEntry(); }

// Update team name inputs when team count changes
document.addEventListener('DOMContentLoaded', () => {
    const teamCountEl = document.getElementById('teamCount');
    if (teamCountEl) {
        teamCountEl.addEventListener('change', renderTeamNames);
        teamCountEl.addEventListener('input', renderTeamNames);
    }
    initTeamQuickEntry();
});

function initTeamQuickEntry() {
    const quick = document.getElementById('teamNameQuick');
    const teamCountInput = document.getElementById('teamCount');
    if (!quick || !teamCountInput) return;
    let idx = 1;
    // Initialize teamNames array
    const count = Math.max(1, Math.min(20, parseInt(teamCountInput.value || '10', 10)));
    if (!window.teamNames || !Array.isArray(window.teamNames)) {
        window.teamNames = Array.from({ length: count }, (_, i) => `Team ${i + 1}`);
    }
    // Keep array length in sync with count
    window.teamNames.length = count;
    for (let i = 0; i < count; i++) {
        if (!window.teamNames[i]) window.teamNames[i] = `Team ${i + 1}`;
    }
    const refreshPlaceholder = () => { quick.placeholder = `Team ${idx}`; };
    refreshPlaceholder();
    quick.value = '';

    // Clear default placeholder behavior on first input
    let cleared = false;
    quick.addEventListener('input', () => {
        if (!cleared) { cleared = true; }
    });

    quick.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const count = Math.max(1, Math.min(20, parseInt(teamCountInput.value || '10', 10)));
            // Save name to array; fallback to default label
            window.teamNames[idx - 1] = (quick.value.trim() || `Team ${idx}`);
            idx = idx >= count ? 1 : idx + 1;
            quick.value = '';
            cleared = false;
            refreshPlaceholder();
        }
    });
}

function switchCropMode(mode) {
    currentCropMode = mode;
    
    // Update button states
    document.getElementById('simpleCropBtn').classList.toggle('active', mode === 'simple');
    document.getElementById('advancedCropBtn').classList.toggle('active', mode === 'advanced');
    
    // Show/hide containers
    document.getElementById('simpleCropContainer').style.display = mode === 'simple' ? 'grid' : 'none';
    document.getElementById('advancedCropContainer').style.display = mode === 'advanced' ? 'grid' : 'none';
    
    // Initialize advanced crop if switching to it
    if (mode === 'advanced') {
        initializeAdvancedCrop();
    }
}

function initializeAdvancedCrop() {
    const overlay = document.getElementById('advancedCropOverlay');
    const image = document.getElementById('advancedCropImage');
    const container = document.getElementById('zoomContainer');
    
    // Reset state
    cornerPoints = [];
    currentCornerIndex = 0;
    currentZoom = 1;
    panX = 0;
    panY = 0;
    overlay.innerHTML = '';
    updateCornerInstruction();
    updateCornerProgress();
    // Fit image to container by default, not super-zoomed
    fitImageToContainer();
    updateImageTransform();
    updateZoomLevel();
    
    // Add click handler to overlay
    overlay.addEventListener('click', handleAdvancedCropClick);
    
    // Add zoom and pan event listeners
    initializeZoomAndPan();

    // Initialize magnifier lens
    initializeMagnifier();
}

function handleAdvancedCropClick(e) {
    if (currentCornerIndex >= 4 || isPanning) return;
    
    const overlay = e.currentTarget;
    const container = document.getElementById('zoomContainer');
    const image = document.getElementById('advancedCropImage');
    
    // Get click position relative to the overlay
    const rect = overlay.getBoundingClientRect();
    const overlayX = e.clientX - rect.left;
    const overlayY = e.clientY - rect.top;
    
    // Convert overlay coordinates to image coordinates accounting for zoom and pan
    const imageX = (overlayX - panX) / currentZoom;
    const imageY = (overlayY - panY) / currentZoom;
    
    // Store both overlay coordinates (for display) and image coordinates (for processing)
    cornerPoints.push({ 
        x: overlayX, 
        y: overlayY,
        imageX: imageX,
        imageY: imageY
    });
    
    // Create visual marker at overlay position
    const marker = document.createElement('div');
    marker.className = 'corner-point placed';
    marker.style.left = overlayX + 'px';
    marker.style.top = overlayY + 'px';
    marker.textContent = currentCornerIndex + 1;
    
    overlay.appendChild(marker);
    
    currentCornerIndex++;
    updateCornerInstruction();
    updateCornerProgress();
    
    // Enable crop button if all corners are placed
    if (currentCornerIndex >= 4) {
        document.getElementById('applyPerspectiveBtn').disabled = false;
        drawPerspectiveLines();
    }
}

function updateCornerInstruction() {
    const instructions = [
        'Click on the <strong>top-left</strong> corner of your draft board',
        'Click on the <strong>top-right</strong> corner of your draft board',
        'Click on the <strong>bottom-right</strong> corner of your draft board',
        'Click on the <strong>bottom-left</strong> corner of your draft board',
        'All corners selected! Click "Apply Perspective Correction" to continue.'
    ];
    
    document.getElementById('cornerInstruction').innerHTML = instructions[currentCornerIndex] || instructions[4];
}

function updateCornerProgress() {
    for (let i = 1; i <= 4; i++) {
        const marker = document.getElementById(`corner${i}`);
        marker.classList.toggle('completed', i <= currentCornerIndex);
    }
}

function updateMarkers() {
    const overlay = document.getElementById('advancedCropOverlay');
    if (!overlay) return;

    // Remove old markers
    overlay.querySelectorAll('.corner-point.placed').forEach(m => m.remove());

    // Recreate markers at transformed positions
    cornerPoints.forEach((pt, index) => {
        const screenX = pt.imageX * currentZoom + panX;
        const screenY = pt.imageY * currentZoom + panY;

        const marker = document.createElement('div');
        marker.className = 'corner-point placed';
        marker.style.left = screenX + 'px';
        marker.style.top = screenY + 'px';
        marker.textContent = index + 1;

        overlay.appendChild(marker);
    });
}

function drawPerspectiveLines() {
    const overlay = document.getElementById('advancedCropOverlay');
    if (!overlay) return;

    // Clear existing lines but leave markers
    overlay.querySelectorAll('.perspective-line').forEach(line => line.remove());

    if (cornerPoints.length < 2) return;

    for (let i = 0; i < cornerPoints.length; i++) {
        const start = cornerPoints[i];
        const end = cornerPoints[(i + 1) % cornerPoints.length];

        // Convert from image coords -> screen coords
        const startX = start.imageX * currentZoom + panX;
        const startY = start.imageY * currentZoom + panY;
        const endX = end.imageX * currentZoom + panX;
        const endY = end.imageY * currentZoom + panY;

        const line = document.createElement('div');
        line.className = 'perspective-line';

        const length = Math.sqrt((endX - startX) ** 2 + (endY - startY) ** 2);
        const angle = Math.atan2(endY - startY, endX - startX) * 180 / Math.PI;

        line.style.left = startX + 'px';
        line.style.top = startY + 'px';
        line.style.width = length + 'px';
        line.style.transform = `rotate(${angle}deg)`;

        overlay.appendChild(line);
    }
}


function resetCorners() {
    cornerPoints = [];
    currentCornerIndex = 0;
    
    const overlay = document.getElementById('advancedCropOverlay');
    overlay.innerHTML = '';
    
    updateCornerInstruction();
    updateCornerProgress();

    document.getElementById('applyPerspectiveBtn').disabled = true;
}

function performAdvancedCrop() {
    if (cornerPoints.length !== 4) {
        showStatus('cropStatus', 'Please select all 4 corners first', 'error');
        return;
    }
    
    const imageElement = document.getElementById('advancedCropImage');
    
    // Calculate scale factors from displayed image to natural image size
    const scaleX = imageElement.naturalWidth / imageElement.offsetWidth;
    const scaleY = imageElement.naturalHeight / imageElement.offsetHeight;
    
    // Use the image coordinates (already adjusted for zoom/pan) and scale to natural size
    const scaledCorners = cornerPoints.map(point => ({
        x: Math.round(point.imageX * scaleX),
        y: Math.round(point.imageY * scaleY)
    }));
    
    console.log('Corner points for processing:', scaledCorners);
    
    // Get draft configuration
    const teamCount = parseInt(document.getElementById('teamCount').value);
    const roundCount = parseInt(document.getElementById('roundCount').value);
    
    fetch('/advanced_crop', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            corners: scaledCorners,
            teamCount: teamCount,
            roundCount: roundCount
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            croppedImage = data.cropped_image;
            croppedPreview.src = croppedImage;
            
            // Log image dimensions when it loads
            croppedPreview.onload = function() {
                console.log('Advanced cropped image loaded:', {
                    naturalWidth: this.naturalWidth,
                    naturalHeight: this.naturalHeight
                });
                
                // Force image to display at natural size
                this.style.width = this.naturalWidth + 'px';
                this.style.height = this.naturalHeight + 'px';
                this.style.maxWidth = 'none';
                this.style.maxHeight = 'none';
                this.style.minWidth = 'auto';
                this.style.minHeight = 'auto';
            };
            
            showStatus('cropStatus', 'Perspective correction applied successfully!', 'success');
            setTimeout(() => nextStep(), 1000);
        } else {
            showStatus('cropStatus', data.error, 'error');
        }
    })
    .catch(error => {
        showStatus('cropStatus', 'Advanced cropping failed: ' + error.message, 'error');
    });
}

function showStatus(elementId, message, type) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = `status ${type}`;
    
    // Clear status after 5 seconds
    setTimeout(() => {
        element.textContent = '';
        element.className = 'status';
    }, 5000);
}

function showLoading(message) {
    document.getElementById('loadingText').textContent = message;
    document.getElementById('loadingOverlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

// Color conversion utilities
function rgbToHsv(r, g, b) {
    r /= 255;
    g /= 255;
    b /= 255;
    
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const diff = max - min;
    
    let h = 0;
    let s = max === 0 ? 0 : diff / max;
    let v = max;
    
    if (diff !== 0) {
        switch (max) {
            case r:
                h = (g - b) / diff + (g < b ? 6 : 0);
                break;
            case g:
                h = (b - r) / diff + 2;
                break;
            case b:
                h = (r - g) / diff + 4;
                break;
        }
        h /= 6;
    }
    
    return [
        Math.round(h * 180),  // H: 0-180
        Math.round(s * 255),  // S: 0-255
        Math.round(v * 255)   // V: 0-255
    ];
}

function generateTeamRosters(results) {
    const teamRosters = document.getElementById('teamRosters');
    teamRosters.innerHTML = '';
    
    // Group results by team (column)
    const teams = {};
    results.forEach(result => {
        const teamNum = result.col + 1; // Convert 0-based to 1-based
        if (!teams[teamNum]) {
            teams[teamNum] = [];
        }
        teams[teamNum].push(result);
    });
    
    // Create team roster tables
    Object.keys(teams).sort((a, b) => parseInt(a) - parseInt(b)).forEach(teamNum => {
        const teamResults = teams[teamNum];
        const teamDiv = document.createElement('div');
        teamDiv.className = 'team-roster';
        const teamIndex = parseInt(teamNum, 10) - 1;
        const teamLabel = (window.teamNames && window.teamNames[teamIndex]) ? window.teamNames[teamIndex] : `Team ${teamNum}`;
        let tableHTML = `<h3>${teamLabel}</h3><table><thead><tr><th>Pick</th><th>Player</th><th>Pos</th><th>Team</th><th>Bye</th><th>Conf</th></tr></thead><tbody>`;
        
        teamResults.forEach(result => {
            tableHTML += `
                <tr>
                    <td>${result.pick}</td>
                    <td>${result.player}</td>
                    <td>${result.position}</td>
                    <td>${result.team}</td>
                    <td>${result.bye}</td>
                    <td class="confidence-cell">
                        ${result.confidence.toFixed(1)}%
                        <div class="confidence-tooltip">
                            <strong>Confidence Breakdown:</strong><br>
                            Firstname: ${(result.score_breakdown?.firstname || 0).toFixed(1)} / 15<br>
                            Lastname: ${(result.score_breakdown?.lastname || 0).toFixed(1)} / 40<br>
                            Team: ${(result.score_breakdown?.team || 0).toFixed(1)} / 15<br>
                            Bye: ${(result.score_breakdown?.bye || 0).toFixed(1)} / 10<br>
                            Color Pos: ${(result.score_breakdown?.color_pos || 0).toFixed(1)} / 15<br>
                            OCR Pos: ${(result.score_breakdown?.ocr_pos || 0).toFixed(1)} / 10<br>
                            Draft Likelihood: ${(result.score_breakdown?.draft_likelihood || 0).toFixed(1)} / 20
                        </div>
                    </td>
                </tr>
            `;
        });
        
        tableHTML += '</tbody></table>';
        teamDiv.innerHTML = tableHTML;
        teamRosters.appendChild(teamDiv);
    });
}

function switchView(view) {
    const bigboardView = document.getElementById('bigboardView');
    const rostersView = document.getElementById('rostersView');
    const debugView = document.getElementById('debugView');
    const bigboardBtn = document.getElementById('bigboardBtn');
    const rostersBtn = document.getElementById('rostersBtn');
    const debugBtn = document.getElementById('debugBtn');
    
    // Hide all views
    bigboardView.style.display = 'none';
    rostersView.style.display = 'none';
    debugView.style.display = 'none';
    
    // Remove active class from all buttons
    bigboardBtn.classList.remove('active');
    rostersBtn.classList.remove('active');
    debugBtn.classList.remove('active');
    
    if (view === 'bigboard') {
        bigboardView.style.display = 'block';
        bigboardBtn.classList.add('active');
    } else if (view === 'rosters') {
        rostersView.style.display = 'block';
        rostersBtn.classList.add('active');
    } else if (view === 'debug') {
        debugView.style.display = 'block';
        debugBtn.classList.add('active');
        loadDebugView();
    }
}

function loadDebugView() {
    // Load the overlay image with retry until available
    const debugImage = document.getElementById('debugOverlayImage');
    const infoPanel = document.getElementById('debugInfoPanel');

    const tryLoadOverlay = (attempt = 0) => {
        // Clear previous handlers to avoid stacking
        debugImage.onload = null;
        debugImage.onerror = null;

        debugImage.onload = () => {
            renderDebugHotspots();
        };
        debugImage.onerror = () => {
            // Backoff retry up to ~10s total
            const next = Math.min(1000 + attempt * 200, 2000);
            if (attempt < 20) {
                if (infoPanel && attempt === 0) {
                    infoPanel.innerHTML = '<h3>Generating overlay...</h3><p style="color:#4a5568">Please wait a moment while the overlay is generated.</p>';
                }
                setTimeout(() => tryLoadOverlay(attempt + 1), next);
            } else {
                if (infoPanel) {
                    infoPanel.innerHTML = '<h3>Overlay unavailable</h3><p style="color:#a0aec0">Overlay generation did not complete in time. Try again or refresh.</p>';
                }
            }
        };

        // Cache-bust each attempt
        debugImage.src = '/debug/overlay?ts=' + Date.now();
    };

    tryLoadOverlay(0);

    // Generate color spectrum
    generateColorSpectrum();
}

// Render interactive hotspots over the debug overlay image
function renderDebugHotspots() {
    try {
        const overlayContainer = document.querySelector('.debug-overlay');
        const img = document.getElementById('debugOverlayImage');
        if (!overlayContainer || !img || !window.cellRois) return;

        // Wrap image to allow absolute-positioned hotspots relative to it
        let wrapper = document.querySelector('.debug-overlay-wrapper');
        if (!wrapper) {
            wrapper = document.createElement('div');
            wrapper.className = 'debug-overlay-wrapper';
            // Insert wrapper and move image inside
            overlayContainer.innerHTML = '';
            overlayContainer.appendChild(wrapper);
            wrapper.appendChild(img);
        } else {
            // Clear existing hotspots
            wrapper.querySelectorAll('.debug-hotspot, .debug-tooltip').forEach(n => n.remove());
        }

        const imgRect = img.getBoundingClientRect();
        const naturalW = img.naturalWidth;
        const naturalH = img.naturalHeight;
        if (!naturalW || !naturalH) return;

        // Compute scale factors from natural to displayed
        const scaleX = imgRect.width / naturalW;
        const scaleY = imgRect.height / naturalH;

        // Info panel target (no floating tooltip)
        const tooltip = null;
        const infoPanel = document.getElementById('debugInfoPanel');

        const rois = window.cellRois;
        const debugOcr = window.debugOcr || [];

        // Helper to get border color from position
        const getPosColor = (pos) => {
            if (!pos) return 'rgb(255,255,255)';
            const prof = (window.colorProfiles && window.colorProfiles[pos]) || null;
            if (prof && Array.isArray(prof.rgb) && prof.rgb.length === 3) {
                const [r, g, b] = prof.rgb.map(v => parseInt(v, 10));
                return `rgb(${r}, ${g}, ${b})`;
            }
            const fallback = { QB: 'rgb(255,165,0)', RB: 'rgb(165,105,79)', WR: 'rgb(0,122,255)', TE: 'rgb(255,59,48)', K: 'rgb(142,142,147)', DST: 'rgb(52,199,89)' };
            return fallback[pos] || 'rgb(255,255,255)';
        };

        // Determine number of teams (columns) for pick math
        const cols = (window.teamNames && window.teamNames.length) ? window.teamNames.length : (parseInt((document.getElementById('teamCount')||{}).value || '10', 10));

        rois.forEach((roi) => {
            const { row, col, x, y, w, h } = roi;
            const hs = document.createElement('div');
            hs.className = 'debug-hotspot';
            // Position over scaled image
            hs.style.left = `${x * scaleX}px`;
            hs.style.top = `${y * scaleY}px`;
            hs.style.width = `${w * scaleX}px`;
            hs.style.height = `${h * scaleY}px`;

            // Lookup debug entry for this cell
            const dbg = debugOcr.find(d => d.row === row && d.col === col) || {};
            const roiO = dbg.roi || {};
            const wholeO = dbg.whole || {};

            // Color border by chosen color_pos
            const chosenColorPos = (dbg.chosen === 'whole') ? (wholeO.color_pos || roiO.color_pos) : (roiO.color_pos || wholeO.color_pos);
            hs.style.borderColor = getPosColor(chosenColorPos);

            // Build tooltip HTML with pick info
            const basePick = row * cols + 1;
            const overallPick = (row % 2 === 0) ? (basePick + col) : (basePick + (cols - 1 - col));
            const roundNum = row + 1;
            const pickInRound = (row % 2 === 0) ? (col + 1) : (cols - col);

            const top3 = Array.isArray(dbg.top3) ? dbg.top3 : [];
            const top3Html = top3.length ? (
                '<div class="tt-section">Top Matches</div>' +
                '<div class="tt-mono">' +
                top3.map((t, idx) => {
                    const badge = t.used ? ' <span class="badge badge-used">used</span>' : '';
                    return `${idx+1}. ${str(t.name)} (${str(t.pos)} - ${str(t.team)})  score:${num(t.score)} rank:${t.rank}${badge}`;
                }).join('<br>') +
                '</div>'
            ) : '';

            const ttHtml = [
                `<div class="tt-title">Pick ${overallPick}</div>`,
                `<div class="tt-mono">Round ${roundNum}, Pick ${pickInRound}</div>`,
                `<div><strong>Chosen:</strong> ${dbg.chosen || 'n/a'}</div>`,
                '<div class="tt-section">ROI OCR</div>',
                `<div class="tt-mono">POS: ${str(roiO.ocr_pos)}\nFIRST: ${str(roiO.ocr_first)}\nLAST: ${str(roiO.ocr_last)}\nTEAM: ${str(roiO.ocr_team)}\nBYE: ${str(roiO.ocr_bye)}\nCOLOR_POS: ${str(roiO.color_pos)}\nSCORE: ${num(roiO.match_score)}</div>`,
                '<div class="tt-section">Whole OCR</div>',
                `<div class="tt-mono">POS: ${str(wholeO.ocr_pos)}\nFIRST: ${str(wholeO.ocr_first)}\nLAST: ${str(wholeO.ocr_last)}\nTEAM: ${str(wholeO.ocr_team)}\nBYE: ${str(wholeO.ocr_bye)}\nCOLOR_POS: ${str(wholeO.color_pos)}\nSCORE: ${num(wholeO.match_score)}</div>`,
                top3Html
            ].join('');

            hs.addEventListener('mouseenter', (e) => {
                if (infoPanel) infoPanel.innerHTML = buildInfoPanelHtml({overallPick, roundNum, pickInRound, dbg, roiO, wholeO, top3});
            });

            wrapper.appendChild(hs);
        });
    } catch (err) {
        console.warn('Failed to render debug hotspots:', err);
    }
}

function str(v) { return (v === undefined || v === null) ? '' : String(v); }
function num(v) { return (typeof v === 'number') ? v.toFixed(1) : (v || ''); }

function positionTooltip(evt, tooltip, wrapper) {
    const wrapRect = wrapper.getBoundingClientRect();
    const mouseX = evt.clientX - wrapRect.left;
    const mouseY = evt.clientY - wrapRect.top;
    const pad = 12;
    let left = mouseX + pad;
    let top = mouseY + pad;
    // Keep inside bounds
    const ttRect = tooltip.getBoundingClientRect();
    const maxLeft = wrapRect.width - ttRect.width - pad;
    const maxTop = wrapRect.height - ttRect.height - pad;
    tooltip.style.left = Math.max(pad, Math.min(maxLeft, left)) + 'px';
    tooltip.style.top = Math.max(pad, Math.min(maxTop, top)) + 'px';
}

function buildInfoPanelHtml({overallPick, roundNum, pickInRound, dbg, roiO, wholeO, top3}) {
    const safe = (v) => (v === undefined || v === null) ? '' : String(v);
    const top3Html = (Array.isArray(top3) && top3.length) ? (
        '<div class="tt-section" style="margin-top:10px">Top Matches</div>' +
        '<div class="tt-mono">' + top3.map((t, i) => {
            const badge = t.used ? ' <span class="badge badge-used">used</span>' : '';
            return `${i+1}. ${safe(t.name)} (${safe(t.pos)} - ${safe(t.team)})  score:${num(t.score)} rank:${safe(t.rank)}${badge}`;
        }).join('<br>') + '</div>'
    ) : '';
    // Selected player header (prefer reconciled final result used for overlay; fallback to OCR)
    let finalSel = null;
    try {
        const results = window.debugResults || [];
        if (Array.isArray(results) && dbg && dbg.row !== undefined && dbg.col !== undefined) {
            finalSel = results.find(r => r && r.row === dbg.row && r.col === dbg.col) || null;
        }
    } catch (_) { finalSel = null; }
    let selHeader = '';
    if (finalSel) {
        selHeader = (
            '<div style="margin-bottom:8px">' +
            '<div style="font-weight:700; font-size:1rem; color:#2d3748">' +
                safe(finalSel.player || '') +
            '</div>' +
            '<div style="color:#4a5568">' +
                safe(finalSel.team || '') + (finalSel.position ? (' • ' + safe(finalSel.position)) : '') + (finalSel.bye ? (' • BYE ' + safe(finalSel.bye)) : '') +
            '</div>' +
            '</div>'
        );
    } else {
        const chosen = dbg && dbg.chosen === 'whole' ? wholeO : roiO;
        selHeader = (
            '<div style="margin-bottom:8px">' +
            '<div style="font-weight:700; font-size:1rem; color:#2d3748">' + safe(chosen.ocr_last || '') + (chosen.ocr_first ? (', ' + safe(chosen.ocr_first)) : '') + '</div>' +
            '<div style="color:#4a5568">' + (safe(chosen.ocr_team || '')) + (chosen.ocr_pos ? (' • ' + safe(chosen.ocr_pos)) : '') + '</div>' +
            '</div>'
        );
    }

    // Row with raw and preprocessed cell images
    let row = dbg && dbg.row !== undefined ? dbg.row : null;
    let col = dbg && dbg.col !== undefined ? dbg.col : null;
    const cellImgs = (row !== null && col !== null) ? (
        '<div class="debug-cell-images">' +
            `<img src="/debug/cell_image/${row}/${col}/raw?ts=${Date.now()}" alt="Raw cell">` +
            `<img src="/debug/cell_image/${row}/${col}/pre?ts=${Date.now()}" alt="Preprocessed cell">` +
        '</div>'
    ) : '';

    const roiScore = parseFloat(num(roiO.match_score)) || 0;
    const wholeScore = parseFloat(num(wholeO.match_score)) || 0;
    const boldIf = (text, cond) => cond ? ('<strong>' + text + '</strong>') : text;
    const roiScoreCell = boldIf(safe(num(roiO.match_score)), roiScore > wholeScore || (roiScore === wholeScore && roiScore !== 0));
    const wholeScoreCell = boldIf(safe(num(wholeO.match_score)), wholeScore > roiScore || (roiScore === wholeScore && wholeScore !== 0));

    // Smaller OCR comparison table
    const tableHtml = [
        '<table style="font-size:0.7rem">',
        '<thead><tr><th>Field</th><th>ROI</th><th>Whole</th></tr></thead>',
        '<tbody>',
        '<tr><td>POS</td><td>' + safe(roiO.ocr_pos) + '</td><td>' + safe(wholeO.ocr_pos) + '</td></tr>',
        '<tr><td>FIRST</td><td>' + safe(roiO.ocr_first) + '</td><td>' + safe(wholeO.ocr_first) + '</td></tr>',
        '<tr><td>LAST</td><td>' + safe(roiO.ocr_last) + '</td><td>' + safe(wholeO.ocr_last) + '</td></tr>',
        '<tr><td>TEAM</td><td>' + safe(roiO.ocr_team) + '</td><td>' + safe(wholeO.ocr_team) + '</td></tr>',
        '<tr><td>BYE</td><td>' + safe(roiO.ocr_bye) + '</td><td>' + safe(wholeO.ocr_bye) + '</td></tr>',
        '<tr><td>COLOR_POS</td><td>' + safe(roiO.color_pos) + '</td><td>' + safe(wholeO.ocr_pos) + '</td></tr>',
        '<tr><td>SCORE</td><td>' + roiScoreCell + '</td><td>' + wholeScoreCell + '</td></tr>',
        '</tbody>',
        '</table>'
    ].join('');

    const pickHeader = '<div style="text-align:right; font-size:0.9rem; color:#4a5568; margin-top:0">' +
        'Pick ' + overallPick + '<br>Round ' + roundNum + ', Pick ' + pickInRound + '</div>';

    // Final chosen score breakdown (from reconciled result)
    let breakdownHtml = '';
    if (finalSel && finalSel.score_breakdown) {
        const bd = finalSel.score_breakdown || {};
        const fmt = (v) => (typeof v === 'number' ? v.toFixed(1) : safe(v));
        breakdownHtml = [
            '<div class="tt-section" style="margin-top:10px">Score Breakdown</div>',
            '<table style="font-size:0.7rem">',
            '<thead><tr><th>Component</th><th>Points</th></tr></thead>',
            '<tbody>',
            '<tr><td>Last name</td><td>' + fmt(bd.lastname) + '</td></tr>',
            '<tr><td>First name</td><td>' + fmt(bd.firstname) + '</td></tr>',
            '<tr><td>Team</td><td>' + fmt(bd.team) + '</td></tr>',
            '<tr><td>Bye</td><td>' + fmt(bd.bye) + '</td></tr>',
            '<tr><td>Color pos</td><td>' + fmt(bd.color_pos) + '</td></tr>',
            '<tr><td>OCR pos</td><td>' + fmt(bd.ocr_pos) + '</td></tr>',
            (bd.draft_likelihood_old !== undefined ? ('<tr><td>Draft (classic)</td><td>' + fmt(bd.draft_likelihood_old) + '</td></tr>') : ''),
            (bd.draft_likelihood_gap !== undefined ? ('<tr><td>Draft (gap‑weighted)</td><td>' + fmt(bd.draft_likelihood_gap) + '</td></tr>') : ''),
            (bd.draft_likelihood !== undefined ? ('<tr><td>Draft (total)</td><td>' + fmt(bd.draft_likelihood) + '</td></tr>') : ''),
            '</tbody>',
            '</table>'
        ].join('');
    }

    return [
        pickHeader,
        selHeader,
        cellImgs,
        '<div class="tt-section" style="margin-top:10px">OCR Comparison</div>',
        tableHtml,
        top3Html,
        breakdownHtml,
        '<div style="margin-top:10px; color:#718096; font-size:0.82rem; line-height:1.3">' +
            '<strong>Score:</strong> multi‑factor match — Last name (0–40), First (0–15), Team (0/15), Bye (0/10), Color (0/15), OCR Pos (0/10), Draft (0–20). Draft is based on classic draft‑likelihood (devalues far‑from‑pick).'+
            '<br><strong>ROI vs Whole:</strong> ROI reads targeted regions (pos/bye/name/team); Whole reads the full cell and parses tokens. Both are scored; the higher strategy is used (and its SCORE cell is bolded).'
        + '</div>'
    ].join('');
}

function generateColorSpectrum() {
    const spectrumGrid = document.getElementById('colorSpectrum');
    spectrumGrid.innerHTML = '';
    
    // Get color profiles from session or use defaults
    const profiles = window.colorProfiles || {};
    const positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST'];
    
    positions.forEach(position => {
        const profile = profiles[position];
        const spectrumItem = document.createElement('div');
        spectrumItem.className = 'spectrum-item';
        
        if (profile && profile.hsv) {
            // Convert HSV to RGB for display
            const rgb = hsvToRgb(profile.hsv[0], profile.hsv[1], profile.hsv[2]);
            const colorStyle = `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
            
            spectrumItem.innerHTML = `
                <h4>${position}</h4>
                <div class="spectrum-color" style="background-color: ${colorStyle}"></div>
                <div class="spectrum-details">
                    <strong>HSV:</strong> (${profile.hsv[0]}, ${profile.hsv[1]}, ${profile.hsv[2]})<br>
                    <strong>RGB:</strong> (${rgb[0]}, ${rgb[1]}, ${rgb[2]})<br>
                    <strong>Range:</strong> ±15 tolerance
                </div>
            `;
        } else if (profile && profile.rgb) {
            // Use RGB directly if available
            const colorStyle = `rgb(${profile.rgb[0]}, ${profile.rgb[1]}, ${profile.rgb[2]})`;
            
            spectrumItem.innerHTML = `
                <h4>${position}</h4>
                <div class="spectrum-color" style="background-color: ${colorStyle}"></div>
                <div class="spectrum-details">
                    <strong>RGB:</strong> (${profile.rgb[0]}, ${profile.rgb[1]}, ${profile.rgb[2]})<br>
                    <strong>HSV:</strong> (${profile.hsv ? profile.hsv.join(', ') : 'N/A'})<br>
                    <strong>Range:</strong> ±15 tolerance
                </div>
            `;
        } else {
            spectrumItem.innerHTML = `
                <h4>${position}</h4>
                <div class="spectrum-color" style="background-color: #e2e8f0"></div>
                <div class="spectrum-details">
                    <em>No color selected</em>
                </div>
            `;
        }
        
        spectrumGrid.appendChild(spectrumItem);
    });
}

function hsvToRgb(h, s, v) {
    h = h / 180; // Convert to 0-1 range
    s = s / 255;
    v = v / 255;
    
    let r, g, b;
    const i = Math.floor(h * 6);
    const f = h * 6 - i;
    const p = v * (1 - s);
    const q = v * (1 - f * s);
    const t = v * (1 - (1 - f) * s);
    
    switch (i % 6) {
        case 0: r = v; g = t; b = p; break;
        case 1: r = q; g = v; b = p; break;
        case 2: r = p; g = v; b = t; break;
        case 3: r = p; g = q; b = v; break;
        case 4: r = t; g = p; b = v; break;
        case 5: r = v; g = p; b = q; break;
    }
    
    return [
        Math.round(r * 255),
        Math.round(g * 255),
        Math.round(b * 255)
    ];
}

// Zoom and Pan Functions
function initializeZoomAndPan() {
    const container = document.getElementById('zoomContainer');
    const image = document.getElementById('advancedCropImage');
    
    // Mouse wheel zoom
    container.addEventListener('wheel', handleWheel, { passive: false });
    
    // Mouse pan
    container.addEventListener('mousedown', handlePanStart);
    document.addEventListener('mousemove', handlePanMove);
    document.addEventListener('mouseup', handlePanEnd);
    
    // Touch events for mobile
    container.addEventListener('touchstart', handleTouchStart, { passive: false });
    container.addEventListener('touchmove', handleTouchMove, { passive: false });
    container.addEventListener('touchend', handleTouchEnd);
    
    // Prevent context menu on right click
    container.addEventListener('contextmenu', (e) => e.preventDefault());
}

// Magnifier lens
function initializeMagnifier() {
    const container = document.getElementById('zoomContainer');
    const image = document.getElementById('advancedCropImage');
    if (!container || !image) return;

    let lens = document.getElementById('magnifierLens');
    if (!lens) {
        lens = document.createElement('div');
        lens.id = 'magnifierLens';
        lens.style.position = 'absolute';
        lens.style.pointerEvents = 'none';
        lens.style.width = '160px';
        lens.style.height = '160px';
        lens.style.border = '2px solid #2c5282';
        lens.style.borderRadius = '8px';
        lens.style.boxShadow = '0 4px 12px rgba(0,0,0,0.25)';
        lens.style.backgroundRepeat = 'no-repeat';
        lens.style.display = 'none';
        // Crosshair lines
        const hLine = document.createElement('div');
        hLine.style.position = 'absolute';
        hLine.style.left = '0';
        hLine.style.top = '50%';
        hLine.style.width = '100%';
        hLine.style.height = '1px';
        hLine.style.background = 'rgba(44,82,130,0.9)';
        const vLine = document.createElement('div');
        vLine.style.position = 'absolute';
        vLine.style.top = '0';
        vLine.style.left = '50%';
        vLine.style.width = '1px';
        vLine.style.height = '100%';
        vLine.style.background = 'rgba(44,82,130,0.9)';
        lens.appendChild(hLine);
        lens.appendChild(vLine);
        container.appendChild(lens);
    }

    container.addEventListener('mouseenter', () => { lens.style.display = 'block'; });
    container.addEventListener('mouseleave', () => { lens.style.display = 'none'; });
    container.addEventListener('mousemove', (e) => updateMagnifier(e, lens));
}

function updateMagnifier(e, lens) {
    const container = document.getElementById('zoomContainer');
    const image = document.getElementById('advancedCropImage');
    if (!container || !image) return;

    const rect = container.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Position lens near cursor with slight offset
    const lensW = lens.offsetWidth;
    const lensH = lens.offsetHeight;
    let lensX = mouseX + 12;
    let lensY = mouseY + 12;
    // Keep lens inside container
    lensX = Math.min(Math.max(0, lensX), rect.width - lensW);
    lensY = Math.min(Math.max(0, lensY), rect.height - lensH);
    lens.style.left = lensX + 'px';
    lens.style.top = lensY + 'px';

    // Compute background image and zoomed area based on current pan/zoom
    const bgImage = image.src;
    lens.style.backgroundImage = `url(${bgImage})`;

    const imgDisplayW = image.offsetWidth * currentZoom;
    const imgDisplayH = image.offsetHeight * currentZoom;
    const imgLeft = panX;
    const imgTop = panY;

    // Map cursor position to image coordinates
    const imgX = (mouseX - imgLeft) / currentZoom;
    const imgY = (mouseY - imgTop) / currentZoom;

    // Magnification factor for the lens view
    const lensZoom = Math.min(3, Math.max(1.5, 2 * currentZoom));

    // Background size needs to reflect zoomed image size times lens zoom
    const bgW = image.offsetWidth * lensZoom;
    const bgH = image.offsetHeight * lensZoom;
    lens.style.backgroundSize = `${bgW}px ${bgH}px`;

    // Background position to center around (imgX, imgY)
    const bgPosX = -(imgX * lensZoom - lensW / 2);
    const bgPosY = -(imgY * lensZoom - lensH / 2);
    lens.style.backgroundPosition = `${bgPosX}px ${bgPosY}px`;
}

function handleWheel(e) {
    e.preventDefault();
    
    const container = document.getElementById('zoomContainer');
    const rect = container.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.max(minZoom, Math.min(maxZoom, currentZoom * zoomFactor));
    
    if (newZoom !== currentZoom) {
        // Zoom towards mouse position
        const zoomRatio = newZoom / currentZoom;
        panX = mouseX - (mouseX - panX) * zoomRatio;
        panY = mouseY - (mouseY - panY) * zoomRatio;
        
        currentZoom = newZoom;
        updateImageTransform();
        updateZoomLevel();
        constrainPan();
    }
}

function handlePanStart(e) {
    if (e.button === 0 && currentZoom > 1) { // Left mouse button only when zoomed
        isPanning = true;
        lastPanX = e.clientX;
        lastPanY = e.clientY;
        document.getElementById('zoomContainer').classList.add('panning');
        e.preventDefault();
    }
}

function handlePanMove(e) {
    if (isPanning) {
        const deltaX = e.clientX - lastPanX;
        const deltaY = e.clientY - lastPanY;
        
        panX += deltaX;
        panY += deltaY;
        
        lastPanX = e.clientX;
        lastPanY = e.clientY;
        
        updateImageTransform();
        constrainPan();
        e.preventDefault();
    }
}

function handlePanEnd(e) {
    if (isPanning) {
        isPanning = false;
        document.getElementById('zoomContainer').classList.remove('panning');
    }
}

// Touch event handlers for mobile support
function handleTouchStart(e) {
    if (e.touches.length === 1 && currentZoom > 1) {
        isPanning = true;
        lastPanX = e.touches[0].clientX;
        lastPanY = e.touches[0].clientY;
        document.getElementById('zoomContainer').classList.add('panning');
    }
}

function handleTouchMove(e) {
    e.preventDefault();
    
    if (e.touches.length === 1 && isPanning) {
        const deltaX = e.touches[0].clientX - lastPanX;
        const deltaY = e.touches[0].clientY - lastPanY;
        
        panX += deltaX;
        panY += deltaY;
        
        lastPanX = e.touches[0].clientX;
        lastPanY = e.touches[0].clientY;
        
        updateImageTransform();
        constrainPan();
    } else if (e.touches.length === 2) {
        // Pinch to zoom (basic implementation)
        const touch1 = e.touches[0];
        const touch2 = e.touches[1];
        const distance = Math.sqrt(
            Math.pow(touch2.clientX - touch1.clientX, 2) + 
            Math.pow(touch2.clientY - touch1.clientY, 2)
        );
        
        if (this.lastTouchDistance) {
            const zoomFactor = distance / this.lastTouchDistance;
            const newZoom = Math.max(minZoom, Math.min(maxZoom, currentZoom * zoomFactor));
            
            if (newZoom !== currentZoom) {
                currentZoom = newZoom;
                updateImageTransform();
                updateZoomLevel();
                constrainPan();
            }
        }
        
        this.lastTouchDistance = distance;
    }
}

function handleTouchEnd(e) {
    if (isPanning) {
        isPanning = false;
        document.getElementById('zoomContainer').classList.remove('panning');
    }
    this.lastTouchDistance = null;
}

function zoomIn() {
    const newZoom = Math.min(maxZoom, currentZoom * 1.25);
    if (newZoom !== currentZoom) {
        // Zoom towards center
        const container = document.getElementById('zoomContainer');
        const centerX = container.offsetWidth / 2;
        const centerY = container.offsetHeight / 2;
        
        const zoomRatio = newZoom / currentZoom;
        panX = centerX - (centerX - panX) * zoomRatio;
        panY = centerY - (centerY - panY) * zoomRatio;
        
        currentZoom = newZoom;
        updateImageTransform();
        updateZoomLevel();
        constrainPan();
    }
}

function zoomOut() {
    const newZoom = Math.max(minZoom, currentZoom * 0.8);
    if (newZoom !== currentZoom) {
        // Zoom towards center
        const container = document.getElementById('zoomContainer');
        const centerX = container.offsetWidth / 2;
        const centerY = container.offsetHeight / 2;
        
        const zoomRatio = newZoom / currentZoom;
        panX = centerX - (centerX - panX) * zoomRatio;
        panY = centerY - (centerY - panY) * zoomRatio;
        
        currentZoom = newZoom;
        updateImageTransform();
        updateZoomLevel();
        constrainPan();
    }
}

function resetZoom() {
    currentZoom = 1;
    panX = 0;
    panY = 0;
    updateImageTransform();
    updateZoomLevel();
}

function updateImageTransform() {
    const image = document.getElementById('advancedCropImage');
    if (image) {
        image.style.transform = `translate(${panX}px, ${panY}px) scale(${currentZoom})`;
    }
    updateMarkers();
    drawPerspectiveLines();
}


function updateZoomLevel() {
    const zoomLevelElement = document.getElementById('zoomLevel');
    if (zoomLevelElement) {
        zoomLevelElement.textContent = Math.round(currentZoom * 100) + '%';
    }
}

function constrainPan() {
    const container = document.getElementById('zoomContainer');
    const image = document.getElementById('advancedCropImage');
    
    if (!container || !image) return;
    
    const containerWidth = container.offsetWidth;
    const containerHeight = container.offsetHeight;
    const imageWidth = image.offsetWidth * currentZoom;
    const imageHeight = image.offsetHeight * currentZoom;
    
    // Only constrain if image is larger than container
    if (imageWidth > containerWidth) {
        const maxPanX = 0;
        const minPanX = containerWidth - imageWidth;
        panX = Math.max(minPanX, Math.min(maxPanX, panX));
    } else {
        panX = (containerWidth - imageWidth) / 2;
    }
    
    if (imageHeight > containerHeight) {
        const maxPanY = 0;
        const minPanY = containerHeight - imageHeight;
        panY = Math.max(minPanY, Math.min(maxPanY, panY));
    } else {
        panY = (containerHeight - imageHeight) / 2;
    }
    
    updateImageTransform();
}

// Fit the image to the container on initialize so it doesn't start super zoomed
function fitImageToContainer() {
    const container = document.getElementById('zoomContainer');
    const image = document.getElementById('advancedCropImage');
    if (!container || !image) return;

    const containerWidth = container.offsetWidth;
    const containerHeight = container.offsetHeight;
    if (containerWidth === 0 || containerHeight === 0) return;

    const naturalWidth = image.naturalWidth || image.offsetWidth;
    const naturalHeight = image.naturalHeight || image.offsetHeight;
    if (!naturalWidth || !naturalHeight) return;

    // Compute scale to fit within container
    const scaleX = containerWidth / naturalWidth;
    const scaleY = containerHeight / naturalHeight;
    currentZoom = Math.min(scaleX, scaleY);

    // Center the image
    const imageWidth = naturalWidth * currentZoom;
    const imageHeight = naturalHeight * currentZoom;
    panX = (containerWidth - imageWidth) / 2;
    panY = (containerHeight - imageHeight) / 2;
}

// Manual Correction Functions
async function showManualCorrectionModal() {
    // Load player names for suggestions
    if (allPlayerNames.length === 0) {
        try {
            const response = await fetch('/player_names');
            const data = await response.json();
            if (data.success) {
                allPlayerNames = data.player_names;
            }
        } catch (error) {
            console.error('Failed to load player names:', error);
        }
    }

    // Initialize event listeners
    initializeCorrectionEventListeners();

    // Show modal and load first cell
    document.getElementById('manualCorrectionModal').style.display = 'block';
    loadCurrentCorrectionCell();
}

async function closeManualCorrectionModal() {
    document.getElementById('manualCorrectionModal').style.display = 'none';

    // Refresh results one final time to show all manual corrections
    await refreshDisplayedResults();
}

function loadCurrentCorrectionCell() {
    if (currentCorrectionIndex >= unrecognizedCells.length) {
        // All corrections completed
        closeManualCorrectionModal();
        nextStep();
        return;
    }

    const cell = unrecognizedCells[currentCorrectionIndex];

    // Update progress
    document.getElementById('correctionProgress').textContent =
        `Cell ${currentCorrectionIndex + 1} of ${unrecognizedCells.length}`;

    // Load cell image
    document.getElementById('correctionCellImage').src = cell.cell_image;

    // Update info
    document.getElementById('ocrText').textContent = cell.ocr_text || 'No OCR text';
    document.getElementById('detectedPosition').textContent = cell.detected_position || 'Unknown';
    document.getElementById('confidenceScore').textContent = `${cell.confidence.toFixed(1)}%`;

    // Pre-fill input with suggested player if available
    const playerInput = document.getElementById('playerNameInput');
    const saveBtn = document.getElementById('saveCorrectionBtn');

    if (cell.suggested_player && cell.suggested_player.name) {
        const isDb = !!cell.suggested_player.is_db;
        const suggestions = document.getElementById('playerSuggestions');
        suggestions.innerHTML = '';

        if (isDb) {
            // Prefill only when suggestion is a valid DB-backed player
            playerInput.value = cell.suggested_player.name;
            saveBtn.disabled = false;
            playerInput.dataset.prefilled = 'true';
        } else {
            playerInput.value = '';
            saveBtn.disabled = true;
            delete playerInput.dataset.prefilled;
        }

        const item = document.createElement('div');
        item.className = 'suggestion-item';
        item.innerHTML = `
            <strong>${cell.suggested_player.name}</strong><br>
            <small>${cell.suggested_player.position} • ${cell.suggested_player.team} • ${cell.suggested_player.confidence.toFixed(1)}% confidence</small>
        `;
        item.onclick = () => selectPlayerName(cell.suggested_player.name);
        suggestions.appendChild(item);
        suggestions.style.display = 'block';
    } else {
        // No suggestion available
        playerInput.value = '';
        saveBtn.disabled = true;
        document.getElementById('playerSuggestions').style.display = 'none';
        delete playerInput.dataset.prefilled;
    }
}

function prefilledInputInterceptor(e) {
    const input = e.currentTarget;
    if (input && input.dataset && input.dataset.prefilled === 'true') {
        // On first keystroke, clear prefilled value and remove flag
        input.value = '';
        delete input.dataset.prefilled;
    }
}

function handlePlayerNameInput() {
    const input = document.getElementById('playerNameInput');
    const suggestions = document.getElementById('playerSuggestions');
    const query = input.value.toLowerCase().trim();

    if (query.length === 0) {
        suggestions.style.display = 'none';
        document.getElementById('saveCorrectionBtn').disabled = true;
        return;
    }

    // Filter player names
    const filteredNames = allPlayerNames.filter(name =>
        name.toLowerCase().includes(query)
    ).slice(0, 10); // Limit to 10 suggestions

    if (filteredNames.length === 0) {
        suggestions.style.display = 'none';
        document.getElementById('saveCorrectionBtn').disabled = true;
        return;
    }

    // Show suggestions
    suggestions.innerHTML = '';
    filteredNames.forEach((name, index) => {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        item.textContent = name;
        item.onclick = () => selectPlayerName(name);
        if (index === 0) item.classList.add('selected');
        suggestions.appendChild(item);
    });

    suggestions.style.display = 'block';
    updateSelectedSuggestion();
}

function updateSelectedSuggestion() {
    const items = document.querySelectorAll('.suggestion-item');
    items.forEach(item => item.classList.remove('selected'));
    if (items.length > 0) {
        items[0].classList.add('selected');
    }
}

function selectPlayerName(name) {
    document.getElementById('playerNameInput').value = name;
    document.getElementById('playerSuggestions').style.display = 'none';
    document.getElementById('saveCorrectionBtn').disabled = false;
    // Auto-save and advance to next correction/results on selection
    // Fire-and-forget; internal saveCorrection handles advancing logic
    saveCorrection();
}

function handleSuggestionNavigation(event) {
    const suggestions = document.getElementById('playerSuggestions');
    if (suggestions.style.display === 'none') return;

    const items = document.querySelectorAll('.suggestion-item');
    let selectedIndex = Array.from(items).findIndex(item => item.classList.contains('selected'));

    if (event.key === 'ArrowDown') {
        event.preventDefault();
        selectedIndex = (selectedIndex + 1) % items.length;
    } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        selectedIndex = selectedIndex <= 0 ? items.length - 1 : selectedIndex - 1;
    } else if (event.key === 'Enter') {
        event.preventDefault();
        if (selectedIndex >= 0) {
            items[selectedIndex].click();
        }
        return;
    } else {
        return; // Don't handle other keys
    }

    // Update selection
    items.forEach(item => item.classList.remove('selected'));
    items[selectedIndex].classList.add('selected');

    // Scroll into view
    items[selectedIndex].scrollIntoView({ block: 'nearest' });
}

async function saveCorrection() {
    const playerName = document.getElementById('playerNameInput').value.trim();
    if (!playerName) return;

    const cell = unrecognizedCells[currentCorrectionIndex];

    try {
        const response = await fetch('/update_manual_correction', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                cell_index: cell.index,
                player_name: playerName
            })
        });

        const data = await response.json();
        if (data.success) {
            // Remove this cell from unrecognized list
            unrecognizedCells.splice(currentCorrectionIndex, 1);

            // Refresh the displayed results to show the manual correction
            await refreshDisplayedResults();

            // Overlay auto-refresh removed; refresh manually via Debug View toggle if desired

            // Don't increment currentCorrectionIndex since we removed an item
            loadCurrentCorrectionCell();
        } else {
            showStatus('processingStatus', 'Failed to save correction: ' + data.error, 'error');
        }
    } catch (error) {
        showStatus('processingStatus', 'Failed to save correction: ' + error.message, 'error');
    }
}

function skipCurrentCell() {
    currentCorrectionIndex++;
    loadCurrentCorrectionCell();
}

// Refresh displayed results after manual corrections
async function refreshDisplayedResults() {
    try {
        // Fetch current results from backend
        const response = await fetch('/get_current_results');
        const data = await response.json();

        if (data.success) {
            // Update the displayed results
            const summary = document.getElementById('resultsSummary');
            const tbody = document.getElementById('resultsBody');

            // Update summary
            summary.innerHTML = `
                <h3>Processing Complete!</h3>
                <p><strong>Total Cells:</strong> ${data.total_cells}</p>
                <p><strong>Successful Matches:</strong> ${data.successful_matches}</p>
                <p><strong>Manual Corrections:</strong> ${data.manual_corrections || 0}</p>
                <p><strong>Success Rate:</strong> ${data.success_rate}</p>
            `;

            // Update results table
            tbody.innerHTML = '';
            data.results.forEach(result => {
                const row = document.createElement('tr');
                const isManualCorrection = result.confidence === 100.0;
                row.innerHTML = `
                    <td>${result.pick}</td>
                    <td>${result.player} ${isManualCorrection ? '<span style="color: #2c5aa0; font-size: 12px;">(manual)</span>' : ''}</td>
                    <td>${result.position}</td>
                    <td>${result.team}</td>
                    <td>${result.bye}</td>
                    <td class="confidence-cell">
                        ${result.confidence.toFixed(1)}%
                        <div class="confidence-tooltip">
                            <strong>Confidence Breakdown:</strong><br>
                            Firstname: ${(result.score_breakdown?.firstname || 0).toFixed(1)} / 15<br>
                            Lastname: ${(result.score_breakdown?.lastname || 0).toFixed(1)} / 40<br>
                            Team: ${(result.score_breakdown?.team || 0).toFixed(1)} / 15<br>
                            Bye: ${(result.score_breakdown?.bye || 0).toFixed(1)} / 10<br>
                            Color Pos: ${(result.score_breakdown?.color_pos || 0).toFixed(1)} / 15<br>
                            OCR Pos: ${(result.score_breakdown?.ocr_pos || 0).toFixed(1)} / 10<br>
                            Draft Likelihood: ${(result.score_breakdown?.draft_likelihood || 0).toFixed(1)} / 20<br>
                            ${isManualCorrection ? '<em>Manual Correction</em>' : ''}
                        </div>
                    </td>
                `;
                tbody.appendChild(row);
            });

            // Update team rosters if the function exists
            if (typeof generateTeamRosters === 'function') {
                generateTeamRosters(data.results);
            }

            // Store updated results for debug view
            window.debugResults = data.results;

            console.log('Results refreshed with manual corrections');
        } else {
            console.error('Failed to refresh results:', data.error);
        }
    } catch (error) {
        console.error('Error refreshing results:', error);
    }
}

// Initialize input event listeners for manual correction
function initializeCorrectionEventListeners() {
    const playerNameInput = document.getElementById('playerNameInput');
    if (playerNameInput) {
        playerNameInput.addEventListener('keydown', prefilledInputInterceptor, true);
        playerNameInput.addEventListener('input', handlePlayerNameInput);
        playerNameInput.addEventListener('keydown', handleSuggestionNavigation);
    }

    // Close suggestions when clicking outside
    document.addEventListener('click', function(e) {
        const suggestions = document.getElementById('playerSuggestions');
        const input = document.getElementById('playerNameInput');
        if (input && suggestions && !input.contains(e.target) && !suggestions.contains(e.target)) {
            suggestions.style.display = 'none';
        }
    });
}
