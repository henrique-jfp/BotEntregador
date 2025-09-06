// PWA App JavaScript
document.addEventListener('DOMContentLoaded', function() {
    console.log('PWA App iniciado');

    // Register Service Worker
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function() {
            navigator.serviceWorker.register('/static/sw.js')
                .then(function(registration) {
                    console.log('ServiceWorker registrado com sucesso:', registration.scope);
                })
                .catch(function(error) {
                    console.log('ServiceWorker falhou ao registrar:', error);
                });
        });
    }

    // Install PWA prompt
    let deferredPrompt;
    const installBtn = document.getElementById('installBtn');

    window.addEventListener('beforeinstallprompt', function(e) {
        e.preventDefault();
        deferredPrompt = e;
        if (installBtn) {
            installBtn.style.display = 'block';
        }
    });

    if (installBtn) {
        installBtn.addEventListener('click', function() {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                deferredPrompt.userChoice.then(function(choiceResult) {
                    if (choiceResult.outcome === 'accepted') {
                        console.log('Usuario instalou o PWA');
                    }
                    deferredPrompt = null;
                });
            }
        });
    }

    // Drag and Drop para upload de arquivos
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('photo');

    if (uploadArea && fileInput) {
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                handleFileUpload(files[0]);
            }
        });

        uploadArea.addEventListener('click', function() {
            fileInput.click();
        });

        fileInput.addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                handleFileUpload(this.files[0]);
            }
        });
    }

    function handleFileUpload(file) {
        if (file && file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = function(e) {
                // Preview da imagem
                const preview = document.getElementById('preview');
                if (preview) {
                    preview.innerHTML = `<img src="${e.target.result}" style="max-width: 100%; height: auto; border-radius: 8px;">`;
                    preview.style.display = 'block';
                }
            };
            reader.readAsDataURL(file);
        }
    }

    // Funcionalidades dos botões de navegação
    const navButtons = document.querySelectorAll('[data-nav]');
    navButtons.forEach(button => {
        button.addEventListener('click', function() {
            const target = this.dataset.nav;
            if (target) {
                window.location.href = target;
            }
        });
    });

    // Notificações offline
    window.addEventListener('online', function() {
        showNotification('Conexão restaurada!', 'success');
    });

    window.addEventListener('offline', function() {
        showNotification('Você está offline. Algumas funcionalidades podem não funcionar.', 'warning');
    });

    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 24px;
            border-radius: 8px;
            color: white;
            font-weight: 600;
            z-index: 1000;
            animation: slideIn 0.3s ease;
        `;
        
        switch(type) {
            case 'success':
                notification.style.background = '#28a745';
                break;
            case 'warning':
                notification.style.background = '#ffc107';
                notification.style.color = '#212529';
                break;
            case 'error':
                notification.style.background = '#dc3545';
                break;
            default:
                notification.style.background = '#17a2b8';
        }
        
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    // Geolocalização para navegação
    function getCurrentLocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocalização não suportada'));
                return;
            }

            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 0
            });
        });
    }

    // Expor funções globais
    window.getCurrentLocation = getCurrentLocation;
    window.showNotification = showNotification;
});

// Função para marcar entrega como concluída
async function markDelivered(index) {
    try {
        const response = await fetch(`/deliver/${index}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            window.showNotification('Entrega marcada como concluída!', 'success');
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            window.showNotification('Erro ao marcar entrega', 'error');
        }
    } catch (error) {
        console.error('Erro:', error);
        window.showNotification('Erro de conexão', 'error');
    }
}
