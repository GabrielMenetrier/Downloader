// Estado da aplicação
let urlCount = 1;

// Elementos DOM
const urlInputsContainer = document.getElementById('urlInputs');
const addUrlBtn = document.getElementById('addUrlBtn');
const processBtn = document.getElementById('processBtn');
const clearBtn = document.getElementById('clearBtn');
const loadingSection = document.getElementById('loadingSection');
const resultsSection = document.getElementById('resultsSection');
const resultsContainer = document.getElementById('results');
const themeToggle = document.getElementById('themeToggle');

// Tema
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
}

themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
});

// Adicionar novo input de URL
addUrlBtn.addEventListener('click', () => {
    const inputGroup = document.createElement('div');
    inputGroup.className = 'input-group';
    inputGroup.innerHTML = `
        <input type="url" class="url-input" placeholder="Cole o link do vídeo aqui (YouTube, Instagram, TikTok, Pinterest)">
        <button class="btn-remove" aria-label="Remover">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M6 18L18 6M6 6l12 12"/>
            </svg>
        </button>
    `;
    
    const removeBtn = inputGroup.querySelector('.btn-remove');
    removeBtn.addEventListener('click', () => {
        if (urlInputsContainer.children.length > 1) {
            inputGroup.remove();
            urlCount--;
        } else {
            showNotification('Você precisa ter pelo menos um campo de URL', 'warning');
        }
    });
    
    urlInputsContainer.appendChild(inputGroup);
    urlCount++;
    
    // Scroll suave para o novo input
    inputGroup.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
});

// Adicionar evento de remoção ao input inicial
document.querySelector('.btn-remove').addEventListener('click', function() {
    if (urlInputsContainer.children.length > 1) {
        this.closest('.input-group').remove();
        urlCount--;
    } else {
        showNotification('Você precisa ter pelo menos um campo de URL', 'warning');
    }
});

// Processar vídeos
processBtn.addEventListener('click', async () => {
    const inputs = document.querySelectorAll('.url-input');
    const urls = Array.from(inputs)
        .map(input => input.value.trim())
        .filter(url => url !== '');
    
    if (urls.length === 0) {
        showNotification('Por favor, adicione pelo menos um URL válido', 'error');
        return;
    }
    
    // Validar URLs
    const invalidUrls = urls.filter(url => !isValidUrl(url));
    if (invalidUrls.length > 0) {
        showNotification('Alguns URLs não são válidos. Verifique e tente novamente.', 'error');
        return;
    }
    
    // Mostrar loading
    loadingSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    resultsContainer.innerHTML = '';
    processBtn.disabled = true;
    
    try {
        const response = await fetch('/process_videos', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ urls })
        });
        
        if (!response.ok) {
            throw new Error('Erro ao processar vídeos');
        }
        
        const data = await response.json();
        displayResults(data.results);
        
    } catch (error) {
        showNotification('Erro ao processar vídeos: ' + error.message, 'error');
    } finally {
        loadingSection.classList.add('hidden');
        processBtn.disabled = false;
    }
});

// Limpar tudo
clearBtn.addEventListener('click', () => {
    if (confirm('Tem certeza que deseja limpar todos os campos e resultados?')) {
        // Limpar inputs
        const inputs = document.querySelectorAll('.url-input');
        inputs.forEach(input => input.value = '');
        
        // Remover inputs extras
        while (urlInputsContainer.children.length > 1) {
            urlInputsContainer.lastChild.remove();
        }
        
        // Limpar resultados
        resultsSection.classList.add('hidden');
        resultsContainer.innerHTML = '';
        
        showNotification('Campos limpos com sucesso', 'success');
    }
});

// Validar URL
function isValidUrl(string) {
    try {
        const url = new URL(string);
        const validDomains = ['youtube.com', 'youtu.be', 'instagram.com', 'tiktok.com', 'pinterest.com'];
        return validDomains.some(domain => url.hostname.includes(domain));
    } catch (_) {
        return false;
    }
}

// Exibir resultados
function displayResults(results) {
    resultsContainer.innerHTML = '';
    
    results.forEach((result, index) => {
        const card = createResultCard(result, index);
        resultsContainer.appendChild(card);
    });
    
    resultsSection.classList.remove('hidden');
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Criar card de resultado
function createResultCard(result, index) {
    const card = document.createElement('div');
    card.className = 'result-card';
    
    if (!result.success) {
        card.classList.add('error');
        card.innerHTML = `
            <div class="error-message">
                <strong>Erro ao processar vídeo ${index + 1}</strong>
                <p>${result.error}</p>
                <p><small>URL: ${result.url}</small></p>
            </div>
        `;
        return card;
    }
    
    const duration = formatDuration(result.duration);
    const language = getLanguageName(result.transcription.language);
    
    card.innerHTML = `
        <div class="result-header">
            ${result.thumbnail ? `<img src="${result.thumbnail}" alt="Thumbnail" class="thumbnail">` : ''}
            <div class="result-info">
                <h3 class="result-title">${escapeHtml(result.title)}</h3>
                <p class="result-meta">Duração: ${duration}</p>
                <button class="download-btn" onclick="downloadVideo('${result.video_id}')">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                    </svg>
                    Baixar Vídeo
                </button>
            </div>
        </div>
        
        <div class="transcription-section">
            <div class="transcription-header">
                <h3>Transcrição</h3>
                <span class="language-badge">${language}</span>
            </div>
            <div class="transcription-text">
                ${escapeHtml(result.transcription.text)}
            </div>
        </div>
    `;
    
    return card;
}

// Download de vídeo
function downloadVideo(filename) {
    window.location.href = `/download/${filename}`;
    showNotification('Download iniciado!', 'success');
}

// Formatar duração
function formatDuration(seconds) {
    if (!seconds) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

// Nome do idioma
function getLanguageName(code) {
    const languages = {
        'en': 'Inglês',
        'pt': 'Português',
        'es': 'Espanhol',
        'fr': 'Francês',
        'de': 'Alemão',
        'it': 'Italiano',
        'error': 'Erro'
    };
    return languages[code] || code.toUpperCase();
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Notificações
function showNotification(message, type = 'info') {
    // Criar elemento de notificação
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: var(--bg-secondary);
        border: 2px solid var(--border-color);
        border-radius: 8px;
        box-shadow: var(--shadow-lg);
        z-index: 1000;
        animation: slideIn 0.3s ease;
        max-width: 400px;
    `;
    
    if (type === 'error') {
        notification.style.borderColor = 'var(--error-color)';
        notification.style.color = 'var(--error-color)';
    } else if (type === 'success') {
        notification.style.borderColor = 'var(--success-color)';
        notification.style.color = 'var(--success-color)';
    } else if (type === 'warning') {
        notification.style.borderColor = 'var(--warning-color)';
        notification.style.color = 'var(--warning-color)';
    }
    
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Remover após 4 segundos
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

// Adicionar animações CSS
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Inicializar tema ao carregar
initTheme();

// Permitir Enter para adicionar novo campo
document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target.classList.contains('url-input')) {
        e.preventDefault();
        addUrlBtn.click();
    }
});
