// ===================================
// GUARDINIA APP - JAVASCRIPT COMPLETO
// ===================================

document.addEventListener('DOMContentLoaded', function() {
    
    // ===================================
    // PARTICLES.JS CONFIGURATION
    // ===================================
    
    if (typeof particlesJS !== 'undefined') {
        particlesJS('particles-js', {
            particles: {
                number: { value: 80, density: { enable: true, value_area: 800 } },
                color: { value: '#3b82f6' },
                shape: { type: 'circle' },
                opacity: { value: 0.3, random: true, anim: { enable: true, speed: 1, opacity_min: 0.1 } },
                size: { value: 3, random: true },
                line_linked: { enable: true, distance: 150, color: '#3b82f6', opacity: 0.2, width: 1 },
                move: { enable: true, speed: 2, direction: 'none', random: false, out_mode: 'out' }
            },
            interactivity: {
                detect_on: 'canvas',
                events: {
                    onhover: { enable: true, mode: 'grab' },
                    onclick: { enable: true, mode: 'push' }
                },
                modes: {
                    grab: { distance: 140, line_linked: { opacity: 0.5 } },
                    push: { particles_nb: 4 }
                }
            }
        });
    }
    
    // ===================================
    // DOM ELEMENTS
    // ===================================
    
    const textarea = document.getElementById("mensagem");
    const charCount = document.getElementById("charCount");
    const btn = document.getElementById("btn");
    const resultado = document.getElementById("resultado");
    
    // Tabs
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // Image upload
    const uploadZone = document.getElementById('uploadZone');
    const imageInput = document.getElementById('imageInput');
    const btnSelectFile = document.getElementById('btnSelectFile');
    const uploadPlaceholder = document.getElementById('uploadPlaceholder');
    const imagePreview = document.getElementById('imagePreview');
    const previewImg = document.getElementById('previewImg');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const btnRemoveImage = document.getElementById('btnRemoveImage');
    
    // State
    let currentTab = 'text';
    let selectedImage = null;
    let selectedImageData = null;

    // ===================================
    // TAB SWITCHING
    // ===================================
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.getAttribute('data-tab');
            switchTab(tab);
        });
    });
    
    function switchTab(tab) {
        currentTab = tab;
        
        // Update buttons
        tabBtns.forEach(btn => {
            if (btn.getAttribute('data-tab') === tab) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        
        // Update content
        tabContents.forEach(content => {
            if (content.id === `tab-${tab}`) {
                content.classList.add('active');
            } else {
                content.classList.remove('active');
            }
        });
        
        // Update button text
        if (tab === 'image') {
            btn.innerHTML = '<i class="fas fa-search"></i><span>Analisar Imagem</span>';
        } else {
            btn.innerHTML = '<i class="fas fa-search"></i><span>Analisar Mensagem</span>';
        }
        
        // Clear result
        resultado.style.display = 'none';
    }

    // ===================================
    // CHARACTER COUNTER
    // ===================================
    
    textarea.addEventListener("input", () => {
        charCount.textContent = textarea.value.length;
    });

    // ===================================
    // IMAGE UPLOAD - DRAG & DROP
    // ===================================
    
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    });
    
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('drag-over');
    });
    
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleImageFile(files[0]);
        }
    });
    
    // ===================================
    // IMAGE UPLOAD - CLICK TO SELECT
    // ===================================
    
    btnSelectFile.addEventListener('click', () => {
        imageInput.click();
    });
    
    imageInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            handleImageFile(file);
        }
    });
    
    // ===================================
    // HANDLE IMAGE FILE
    // ===================================
    
    function handleImageFile(file) {
        // Validate file type
        const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            showNotification('Formato inválido! Use PNG, JPG ou WEBP', 'error');
            return;
        }
        
        // Validate file size (5MB max)
        const maxSize = 5 * 1024 * 1024; // 5MB
        if (file.size > maxSize) {
            showNotification('Arquivo muito grande! Máximo 5MB', 'error');
            return;
        }
        
        // Store file
        selectedImage = file;
        
        // Read file as data URL for preview
        const reader = new FileReader();
        reader.onload = (e) => {
            selectedImageData = e.target.result;
            showImagePreview(file, e.target.result);
        };
        reader.readAsDataURL(file);
    }
    
    // ===================================
    // SHOW IMAGE PREVIEW
    // ===================================
    
    function showImagePreview(file, dataUrl) {
        // Update preview info
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        
        // Set preview image
        previewImg.src = dataUrl;
        
        // Show preview, hide placeholder
        uploadPlaceholder.style.display = 'none';
        imagePreview.style.display = 'block';
        
        // Update upload zone style
        uploadZone.style.border = '3px solid #10b981';
        uploadZone.style.background = 'rgba(16, 185, 129, 0.05)';
    }
    
    // ===================================
    // REMOVE IMAGE
    // ===================================
    
    btnRemoveImage.addEventListener('click', () => {
        selectedImage = null;
        selectedImageData = null;
        imageInput.value = '';
        
        // Reset UI
        uploadPlaceholder.style.display = 'block';
        imagePreview.style.display = 'none';
        uploadZone.style.border = '3px dashed #e2e8f0';
        uploadZone.style.background = '#f8fafc';
        
        showNotification('Imagem removida', 'info');
    });
    
    // ===================================
    // FORMAT FILE SIZE
    // ===================================
    
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    // ===================================
    // MENSAGENS PADRÃO
    // ===================================
    
    const MENSAGENS_PADRAO = {
        verde: {
            titulo: "✅ Mensagem Segura",
            texto: "Nenhuma ação necessária. A mensagem não apresenta indícios relevantes de golpe."
        },
        amarelo: {
            titulo: "⚠️ Atenção",
            texto: "A mensagem apresenta alguns sinais suspeitos. Tenha cautela e não forneça dados pessoais."
        },
        vermelho: {
            titulo: "🚨 Possível Golpe Detectado",
            texto: "A mensagem solicita ações sensíveis. Não responda, não clique em links e não forneça informações."
        }
    };

    // ===================================
    // ANALYZE BUTTON
    // ===================================
    
    btn.addEventListener("click", analisar);
    
    // Keyboard shortcut
    textarea.addEventListener("keydown", (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            analisar();
        }
    });

    // ===================================
    // MAIN ANALYSIS FUNCTION
    // ===================================
    
    async function analisar() {
        if (currentTab === 'text') {
            await analisarTexto();
        } else {
            await analisarImagem();
        }
    }
    
    // ===================================
    // ANALYZE TEXT
    // ===================================
    
    async function analisarTexto() {
        const texto = textarea.value.trim();
        
        if (!texto) {
            showNotification("Digite uma mensagem para analisar.", "warning");
            return;
        }

        setLoadingState(true);
        showLoadingResult();

        try {
            const response = await fetch(
                "https://ly9yvqdsta.execute-api.us-east-1.amazonaws.com/prod/teste",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ mensagem: texto })
                }
            );

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            showResult(data);

        } catch (error) {
            console.error("Erro na análise:", error);
            showErrorResult();
        } finally {
            setLoadingState(false);
        }
    }
    
    // ===================================
    // ANALYZE IMAGE
    // ===================================
    
    async function analisarImagem() {
        if (!selectedImage || !selectedImageData) {
            showNotification("Selecione uma imagem para analisar.", "warning");
            return;
        }

        setLoadingState(true);
        showLoadingResult('imagem');

        try {
            // Extract base64 data (remove data:image/xxx;base64, prefix)
            const base64Data = selectedImageData.split(',')[1];
            
            const response = await fetch(
                "https://ly9yvqdsta.execute-api.us-east-1.amazonaws.com/prod/teste",
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ 
                        imagem: base64Data,
                        tipo: 'imagem'
                    })
                }
            );

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            showResult(data, true);

        } catch (error) {
            console.error("Erro na análise de imagem:", error);
            showErrorResult(true);
        } finally {
            setLoadingState(false);
        }
    }
    
    // ===================================
    // UI STATE FUNCTIONS
    // ===================================
    
    function setLoadingState(loading) {
        btn.disabled = loading;
        
        if (loading) {
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Analisando...</span>';
        } else {
            if (currentTab === 'image') {
                btn.innerHTML = '<i class="fas fa-search"></i><span>Analisar Imagem</span>';
            } else {
                btn.innerHTML = '<i class="fas fa-search"></i><span>Analisar Mensagem</span>';
            }
        }
    }
    
    function showLoadingResult(tipo = 'mensagem') {
        resultado.style.display = "block";
        resultado.className = "resultado";
        resultado.innerHTML = `
            <div style="text-align: center; padding: 2rem;">
                <i class="fas fa-spinner fa-spin" style="font-size: 3rem; color: #3b82f6; margin-bottom: 1rem;"></i>
                <h2 style="color: #334155;">Analisando ${tipo}...</h2>
                <p style="color: #64748b;">
                    ${tipo === 'imagem' ? 'Extraindo texto com OCR e verificando padrões de golpes' : 'Verificando padrões de golpes e ameaças'}
                </p>
            </div>
        `;
        resultado.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    function showResult(data, isImage = false) {
        const msg = MENSAGENS_PADRAO[data.cor] || {
            titulo: "Resultado da Análise",
            texto: data.acao_recomendada || "Análise concluída."
        };

        const cor = MENSAGENS_PADRAO[data.cor] ? data.cor : "amarelo";
        resultado.className = `resultado resultado--${cor}`;

        let detalhesHTML = '';
        
        // Show extracted text for images
        if (isImage && data.texto_analisado) {
            detalhesHTML += `
                <div style="margin-top: 1.5rem; padding: 1rem; background: rgba(0,0,0,0.05); border-radius: 0.5rem;">
                    <h4 style="font-size: 1rem; margin-bottom: 0.5rem; color: #334155;">
                        <i class="fas fa-file-alt"></i> Texto Extraído (OCR):
                    </h4>
                    <p style="font-size: 0.95rem; color: #64748b; font-style: italic;">
                        "${data.texto_analisado.substring(0, 200)}${data.texto_analisado.length > 200 ? '...' : ''}"
                    </p>
                </div>
            `;
        }
        
        if (data.motivos && data.motivos.length > 0) {
            detalhesHTML += `
                <div style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 2px solid rgba(0,0,0,0.1);">
                    <h3 style="font-size: 1.1rem; margin-bottom: 1rem; color: #334155;">
                        <i class="fas fa-list-ul"></i> Indicadores Detectados:
                    </h3>
                    <ul style="list-style: none; padding: 0;">
                        ${data.motivos.slice(0, 5).map(motivo => `
                            <li style="margin-bottom: 0.75rem; padding-left: 1.5rem; position: relative;">
                                <i class="fas fa-exclamation-circle" style="position: absolute; left: 0; top: 0.25rem; color: ${cor === 'verde' ? '#10b981' : cor === 'amarelo' ? '#f59e0b' : '#ef4444'};"></i>
                                ${motivo}
                            </li>
                        `).join('')}
                    </ul>
                </div>
            `;
        }

        if (data.confianca) {
            detalhesHTML += `
                <div style="margin-top: 1rem; text-align: center; padding: 1rem; background: rgba(0,0,0,0.05); border-radius: 0.5rem;">
                    <strong>Confiança Técnica:</strong> ${data.confianca}%
                </div>
            `;
        }

        resultado.innerHTML = `
            <h2>${msg.titulo}</h2>
            <p style="font-size: 1.1rem; margin-top: 0.5rem;">${msg.texto}</p>
            ${detalhesHTML}
        `;

        resultado.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    function showErrorResult(isImage = false) {
        resultado.className = "resultado resultado--vermelho";
        resultado.innerHTML = `
            <h2><i class="fas fa-exclamation-triangle"></i> Erro de Conexão</h2>
            <p>Não foi possível completar a análise. Verifique sua conexão e tente novamente.</p>
            ${isImage ? '<p style="font-size: 0.95rem; margin-top: 1rem; opacity: 0.9;"><strong>Dica:</strong> Certifique-se de que a imagem contém texto visível.</p>' : ''}
            <p style="font-size: 0.9rem; margin-top: 1rem; opacity: 0.8;">
                <strong>Alternativa:</strong> Teste pelo nosso 
                <a href="https://api.whatsapp.com/send?phone=5541985086826" 
                   target="_blank" 
                   style="color: #25D366; text-decoration: underline;">
                    WhatsApp Bot
                </a>
            </p>
        `;
    }

    // ===================================
    // NOTIFICATION SYSTEM
    // ===================================
    
    function showNotification(message, type = 'info') {
        const colors = {
            info: '#3b82f6',
            warning: '#f59e0b',
            error: '#ef4444',
            success: '#10b981'
        };
        
        const icons = {
            info: 'info-circle',
            warning: 'exclamation-triangle',
            error: 'times-circle',
            success: 'check-circle'
        };
        
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 2rem;
            right: 2rem;
            background: ${colors[type] || colors.info};
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 0.75rem;
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
            z-index: 10000;
            animation: slideInRight 0.3s ease;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            max-width: 400px;
        `;
        notification.innerHTML = `
            <i class="fas fa-${icons[type] || icons.info}" style="font-size: 1.3rem;"></i>
            <span>${message}</span>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // ===================================
    // ANIMATIONS
    // ===================================
    
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);

    // ===================================
    // CONSOLE MESSAGE
    // ===================================
    
    console.log('%c GuardinIA ', 
        'background: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%); color: white; font-size: 20px; font-weight: bold; padding: 10px;');
    console.log('%c Sistema de Análise com OCR Carregado ', 
        'color: #3b82f6; font-size: 14px; font-weight: bold;');

});
