// ================================================================
// GUARDINIA SYSTEM - JAVASCRIPT
// Sistema de Análise Inteligente de Mensagens
// ================================================================

// ========= CONFIGURAÇÃO =========
const CONFIG = {
    // IMPORTANTE: Configure seu webhook aqui
    WEBHOOK_URL: "https://hk2n2f9vu2.execute-api.us-east-1.amazonaws.com/prod/teste/teste",
    MAX_FILE_SIZE: 5 * 1024 * 1024, // 5MB
    ALLOWED_TYPES: ['image/png', 'image/jpeg', 'image/jpg', 'image/webp']
};

// ========= ELEMENTOS DOM =========
const elements = {
    // Tabs
    tabButtons: document.querySelectorAll('.tab-btn'),
    tabContents: document.querySelectorAll('.tab-content'),
    
    // Text input
    mensagem: document.getElementById('mensagem'),
    charCount: document.getElementById('charCount'),
    
    // Image upload
    imageInput: document.getElementById('imageInput'),
    uploadZone: document.getElementById('uploadZone'),
    uploadPlaceholder: document.getElementById('uploadPlaceholder'),
    imagePreview: document.getElementById('imagePreview'),
    previewImg: document.getElementById('previewImg'),
    fileName: document.getElementById('fileName'),
    fileSize: document.getElementById('fileSize'),
    btnSelectFile: document.getElementById('btnSelectFile'),
    btnRemoveImage: document.getElementById('btnRemoveImage'),
    
    // Analysis
    btnAnalyze: document.getElementById('btnAnalyze'),
    loadingState: document.getElementById('loadingState'),
    resultado: document.getElementById('resultado')
};

// ========= STATE =========
let currentTab = 'text';
let uploadedFile = null;

// ========= INITIALIZATION =========
document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    initializeTextAnalysis();
    initializeImageUpload();
    initializeAnalyzeButton();
    
    console.log('🛡️ GuardinIA System initialized successfully!');
});

// ========= TABS FUNCTIONALITY =========
function initializeTabs() {
    elements.tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tab = button.dataset.tab;
            switchTab(tab);
        });
    });
}

function switchTab(tab) {
    currentTab = tab;
    
    // Update buttons
    elements.tabButtons.forEach(btn => {
        if (btn.dataset.tab === tab) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    // Update content
    elements.tabContents.forEach(content => {
        if (content.id === `tab-${tab}`) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });
    
    // Clear results when switching tabs
    clearResults();
}

// ========= TEXT ANALYSIS =========
function initializeTextAnalysis() {
    if (!elements.mensagem) return;
    
    // Character counter
    elements.mensagem.addEventListener('input', () => {
        const length = elements.mensagem.value.length;
        elements.charCount.textContent = length;
        
        // Color change when approaching limit
        if (length > 450) {
            elements.charCount.style.color = 'var(--vermelho)';
        } else if (length > 400) {
            elements.charCount.style.color = 'var(--laranja)';
        } else {
            elements.charCount.style.color = 'var(--cinza)';
        }
    });
}

// ========= IMAGE UPLOAD =========
function initializeImageUpload() {
    // Click to select file
    elements.btnSelectFile.addEventListener('click', () => {
        elements.imageInput.click();
    });
    
    // File input change
    elements.imageInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            handleFileUpload(file);
        }
    });
    
    // Drag and drop
    elements.uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.uploadZone.classList.add('dragover');
    });
    
    elements.uploadZone.addEventListener('dragleave', () => {
        elements.uploadZone.classList.remove('dragover');
    });
    
    elements.uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        elements.uploadZone.classList.remove('dragover');
        
        const file = e.dataTransfer.files[0];
        if (file) {
            handleFileUpload(file);
        }
    });
    
    // Remove image
    elements.btnRemoveImage.addEventListener('click', () => {
        removeImage();
    });
}

function handleFileUpload(file) {
    // Validate file type
    if (!CONFIG.ALLOWED_TYPES.includes(file.type)) {
        showError('Formato inválido! Use PNG, JPG ou WEBP.');
        return;
    }
    
    // Validate file size
    if (file.size > CONFIG.MAX_FILE_SIZE) {
        showError('Arquivo muito grande! Tamanho máximo: 5MB.');
        return;
    }
    
    uploadedFile = file;
    
    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
        elements.previewImg.src = e.target.result;
        elements.fileName.textContent = file.name;
        elements.fileSize.textContent = formatFileSize(file.size);
        
        // Show preview, hide placeholder
        elements.uploadPlaceholder.style.display = 'none';
        elements.imagePreview.style.display = 'block';
    };
    reader.readAsDataURL(file);
    
    // Clear results
    clearResults();
}

function removeImage() {
    uploadedFile = null;
    elements.imageInput.value = '';
    elements.previewImg.src = '';
    
    // Hide preview, show placeholder
    elements.imagePreview.style.display = 'none';
    elements.uploadPlaceholder.style.display = 'block';
    
    // Clear results
    clearResults();
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// ========= ANALYZE BUTTON =========
function initializeAnalyzeButton() {
    elements.btnAnalyze.addEventListener('click', async () => {
        await performAnalysis();
    });
}

async function performAnalysis() {
    // Validate input
    if (currentTab === 'text') {
        const message = elements.mensagem.value.trim();
        if (!message) {
            showError('Por favor, digite uma mensagem para análise.');
            return;
        }
    } else if (currentTab === 'image') {
        if (!uploadedFile) {
            showError('Por favor, selecione uma imagem para análise.');
            return;
        }
    }
    
    // Show loading
    showLoading();
    
    try {
        // Prepare data
        const formData = new FormData();
        
        if (currentTab === 'text') {
            formData.append('type', 'text');
            formData.append('message', elements.mensagem.value.trim());
        } else {
            formData.append('type', 'image');
            formData.append('image', uploadedFile);
        }
        
        // Call API
        const response = await fetch(CONFIG.WEBHOOK_URL, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Erro na análise. Tente novamente.');
        }
        
        const result = await response.json();
        
        // Show results
        hideLoading();
        displayResults(result);
        
    } catch (error) {
        console.error('Analysis error:', error);
        hideLoading();
        showError('Erro ao analisar mensagem. Por favor, tente novamente.');
    }
}

// ========= LOADING STATES =========
function showLoading() {
    elements.btnAnalyze.disabled = true;
    elements.loadingState.style.display = 'block';
    elements.resultado.innerHTML = '';
    
    // Scroll to loading
    elements.loadingState.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function hideLoading() {
    elements.btnAnalyze.disabled = false;
    elements.loadingState.style.display = 'none';
}

// ========= RESULTS DISPLAY =========
function displayResults(result) {
    // Determine result type
    const resultType = determineResultType(result);
    
    // Create result HTML
    const html = `
        <div class="result-card ${resultType}">
            <div class="result-header">
                <i class="fas ${getResultIcon(resultType)} result-icon"></i>
                <div>
                    <div class="result-title">${getResultTitle(resultType)}</div>
                </div>
            </div>
            <div class="result-content">
                ${formatResultContent(result)}
            </div>
        </div>
    `;
    
    elements.resultado.innerHTML = html;
    
    // Scroll to results
    elements.resultado.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function determineResultType(result) {
    // Customize this based on your API response
    if (result.is_scam || result.confidence > 0.7) {
        return 'danger';
    } else if (result.confidence > 0.4) {
        return 'warning';
    } else {
        return 'success';
    }
}

function getResultIcon(type) {
    const icons = {
        danger: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        success: 'fa-check-circle'
    };
    return icons[type] || 'fa-info-circle';
}

function getResultTitle(type) {
    const titles = {
        danger: '⚠️ GOLPE CONFIRMADO',
        warning: '⚡ ATENÇÃO: Mensagem Suspeita',
        success: '✅ Mensagem Segura'
    };
    return titles[type] || 'Resultado da Análise';
}

function formatResultContent(result) {
    // Customize this based on your API response structure
    let html = '';
    
    if (result.analysis) {
        html += `<p>${result.analysis}</p>`;
    }
    
    if (result.confidence) {
        html += `<p><strong>Confiança técnica:</strong> ${(result.confidence * 100).toFixed(0)}%</p>`;
    }
    
    if (result.scam_types && result.scam_types.length > 0) {
        html += `
            <h3>🎯 Tipos de Golpe Detectados:</h3>
            <ul>
                ${result.scam_types.map(type => `<li>${type}</li>`).join('')}
            </ul>
        `;
    }
    
    if (result.reasons && result.reasons.length > 0) {
        html += `
            <h3>📋 Motivos:</h3>
            <ul>
                ${result.reasons.map(reason => `<li>${reason}</li>`).join('')}
            </ul>
        `;
    }
    
    if (result.recommendations) {
        html += `
            <h3>💡 Recomendações:</h3>
            <p>${result.recommendations}</p>
        `;
    }
    
    return html;
}

function clearResults() {
    elements.resultado.innerHTML = '';
}

// ========= ERROR HANDLING =========
function showError(message) {
    const html = `
        <div class="result-card danger">
            <div class="result-header">
                <i class="fas fa-times-circle result-icon"></i>
                <div>
                    <div class="result-title">Erro</div>
                </div>
            </div>
            <div class="result-content">
                <p>${message}</p>
            </div>
        </div>
    `;
    
    elements.resultado.innerHTML = html;
    elements.resultado.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// ========= DEMO MODE (for testing without backend) =========
// Uncomment this to test the UI without a real backend
/*
async function performAnalysis() {
    showLoading();
    
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Mock result
    const mockResult = {
        is_scam: true,
        confidence: 0.95,
        analysis: 'Esta mensagem apresenta características típicas de golpe de phishing. O texto usa urgência artificial e solicita ação imediata.',
        scam_types: ['Phishing', 'Urgência Artificial', 'Falso Bloqueio de PIX'],
        reasons: [
            'Uso de URGÊNCIA artificial ("URGENTE")',
            'Ameaça de bloqueio de serviço',
            'Solicitação de ação imediata',
            'Link suspeito',
            'Técnicas de engenharia social'
        ],
        recommendations: 'NÃO clique em links. Entre em contato com seu banco pelos canais oficiais. Bloqueie e denuncie o remetente.'
    };
    
    hideLoading();
    displayResults(mockResult);
}
*/

// ========= UTILITY FUNCTIONS =========
function scrollToElement(element, offset = 100) {
    const elementPosition = element.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - offset;

    window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
    });
}

// ========= KEYBOARD SHORTCUTS =========
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Enter to analyze
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        performAnalysis();
    }
    
    // Escape to clear results
    if (e.key === 'Escape') {
        clearResults();
    }
});

// ========= ANALYTICS (Optional) =========
function trackEvent(category, action, label) {
    // Add your analytics tracking here
    // Example: gtag('event', action, { event_category: category, event_label: label });
    console.log('Event:', category, action, label);
}

// Track tab switches
elements.tabButtons.forEach(button => {
    button.addEventListener('click', () => {
        trackEvent('Interface', 'tab_switch', button.dataset.tab);
    });
});

// Track analysis
elements.btnAnalyze.addEventListener('click', () => {
    trackEvent('Analysis', 'analyze_click', currentTab);
});

console.log('✅ GuardinIA System ready!');
