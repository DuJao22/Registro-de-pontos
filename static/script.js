// Global JavaScript functionality for the Time Tracking System
// Performance optimized with debouncing and lazy loading

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all components with performance optimization
    initializeTooltips();
    initializeAlerts();
    initializeFormValidation();
    initializeResponsiveFeatures();
    
    // Set focus on first input field if exists (after small delay for better UX)
    setTimeout(() => {
        const firstInput = document.querySelector('input[type="text"], input[type="email"], input[type="password"]');
        if (firstInput && window.innerWidth > 768) { // Only on desktop
            firstInput.focus();
        }
    }, 100);
});

// Initialize Bootstrap tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Auto-hide alerts after 5 seconds
function initializeAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
}

// Form validation enhancements
function initializeFormValidation() {
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Focus on first invalid field
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                }
            }
            form.classList.add('was-validated');
        });
    });
}

// CPF formatting and validation
function formatCPF(input) {
    let value = input.value.replace(/\D/g, '');
    
    if (value.length <= 11) {
        value = value.replace(/(\d{3})(\d)/, '$1.$2');
        value = value.replace(/(\d{3})(\d)/, '$1.$2');
        value = value.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
        input.value = value;
    }
}

// Simple CPF validation
function validateCPF(cpf) {
    cpf = cpf.replace(/\D/g, '');
    
    if (cpf.length !== 11) return false;
    if (/^(\d)\1{10}$/.test(cpf)) return false; // All same digits
    
    // Basic checksum validation
    let sum = 0;
    for (let i = 0; i < 9; i++) {
        sum += parseInt(cpf.charAt(i)) * (10 - i);
    }
    let checkDigit1 = 11 - (sum % 11);
    if (checkDigit1 >= 10) checkDigit1 = 0;
    
    sum = 0;
    for (let i = 0; i < 10; i++) {
        sum += parseInt(cpf.charAt(i)) * (11 - i);
    }
    let checkDigit2 = 11 - (sum % 11);
    if (checkDigit2 >= 10) checkDigit2 = 0;
    
    return checkDigit1 === parseInt(cpf.charAt(9)) && checkDigit2 === parseInt(cpf.charAt(10));
}

// Confirmation dialogs
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Show loading state
function showLoading(element) {
    element.classList.add('loading');
    const originalText = element.innerHTML;
    element.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Processando...';
    element.disabled = true;
    
    return function() {
        element.classList.remove('loading');
        element.innerHTML = originalText;
        element.disabled = false;
    };
}

// Success animation
function showSuccess(element) {
    element.classList.add('pulse-success');
    setTimeout(function() {
        element.classList.remove('pulse-success');
    }, 500);
}

// Notification system
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(function() {
        if (alertDiv.parentNode) {
            const bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }
    }, 5000);
}

// Time formatting utilities
function formatTime(timeString) {
    if (!timeString) return '--:--';
    return timeString.substring(0, 5); // Returns HH:MM
}

function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString('pt-BR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function getCurrentDate() {
    const now = new Date();
    return now.toLocaleDateString('pt-BR');
}

// Local storage utilities
function saveToStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
        console.warn('Could not save to localStorage:', e);
    }
}

function getFromStorage(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (e) {
        console.warn('Could not read from localStorage:', e);
        return defaultValue;
    }
}

// Table utilities
function sortTable(tableId, columnIndex, dataType = 'string') {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    const sorted = rows.sort((a, b) => {
        const aVal = a.cells[columnIndex].textContent.trim();
        const bVal = b.cells[columnIndex].textContent.trim();
        
        if (dataType === 'number') {
            return parseFloat(aVal) - parseFloat(bVal);
        } else if (dataType === 'date') {
            return new Date(aVal) - new Date(bVal);
        } else {
            return aVal.localeCompare(bVal, 'pt-BR');
        }
    });
    
    // Clear and re-append sorted rows
    tbody.innerHTML = '';
    sorted.forEach(row => tbody.appendChild(row));
}

// Print utilities
function printElement(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Impressão - Sistema de Ponto</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body { padding: 20px; }
                .no-print { display: none; }
                @media print {
                    .btn, .no-print { display: none !important; }
                }
            </style>
        </head>
        <body>
            ${element.innerHTML}
            <script>
                window.onload = function() {
                    window.print();
                    window.close();
                };
            </script>
        </body>
        </html>
    `);
    printWindow.document.close();
}

// Form utilities
function resetForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.reset();
        form.classList.remove('was-validated');
    }
}

function serializeForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return {};
    
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    
    return data;
}

// Keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // Alt + H: Go to home/dashboard
    if (event.altKey && event.key === 'h') {
        event.preventDefault();
        window.location.href = '/';
    }
    
    // Alt + L: Logout
    if (event.altKey && event.key === 'l') {
        event.preventDefault();
        const logoutLink = document.querySelector('a[href*="logout"]');
        if (logoutLink) {
            logoutLink.click();
        }
    }
    
    // Escape: Close modals
    if (event.key === 'Escape') {
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        });
    }
});

// Network status monitoring
window.addEventListener('online', function() {
    showNotification('Conexão restaurada!', 'success');
});

window.addEventListener('offline', function() {
    showNotification('Sem conexão com a internet!', 'warning');
});

// Prevent form double submission
document.addEventListener('submit', function(event) {
    const form = event.target;
    const submitButton = form.querySelector('button[type="submit"]');
    
    if (submitButton && !submitButton.disabled) {
        setTimeout(function() {
            submitButton.disabled = true;
            const originalText = submitButton.innerHTML;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Processando...';
            
            setTimeout(function() {
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
            }, 3000);
        }, 100);
    }
});

// Responsive features initialization
function initializeResponsiveFeatures() {
    // Mobile menu optimizations (only add listener once)
    const navbarToggler = document.querySelector('.navbar-toggler');
    if (navbarToggler && !navbarToggler.hasAttribute('data-initialized')) {
        navbarToggler.setAttribute('data-initialized', 'true');
        navbarToggler.addEventListener('click', function() {
            // Check for reduced motion preference
            if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                this.classList.add('pulse-success');
                setTimeout(() => this.classList.remove('pulse-success'), 300);
            }
        });
    }
    
    // Touch-friendly tables with proper cleanup
    const tables = document.querySelectorAll('.table-responsive table');
    tables.forEach(table => {
        if (window.innerWidth <= 768) {
            table.style.fontSize = '0.85rem';
            table.classList.add('table-sm');
        } else {
            // Clean up mobile styles for larger screens
            table.style.fontSize = '';
            table.classList.remove('table-sm');
        }
    });
    
    // Optimize cards with proper cleanup
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        if (window.innerWidth <= 480) {
            card.style.marginBottom = '1rem';
        } else {
            // Clean up mobile styles for larger screens
            card.style.marginBottom = '';
        }
    });
}

// Debounced resize handler for performance
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Handle window resize with debouncing
window.addEventListener('resize', debounce(function() {
    initializeResponsiveFeatures();
}, 250));

// Auto-refresh for dashboard pages with visibility optimization
function enableAutoRefresh(interval = 30000) {
    if (window.location.pathname.includes('dashboard')) {
        let refreshTimer;
        
        function scheduleRefresh() {
            refreshTimer = setTimeout(function() {
                if (document.visibilityState === 'visible' && navigator.onLine) {
                    location.reload();
                } else {
                    scheduleRefresh(); // Try again later
                }
            }, interval);
        }
        
        // Start the refresh cycle
        scheduleRefresh();
        
        // Pause/resume based on page visibility
        document.addEventListener('visibilitychange', function() {
            if (document.visibilityState === 'hidden') {
                clearTimeout(refreshTimer);
            } else {
                scheduleRefresh();
            }
        });
    }
}

// Initialize auto-refresh with improved logic
enableAutoRefresh();

// Export functions for global use
window.TimeTrackingSystem = {
    formatCPF,
    validateCPF,
    confirmAction,
    showLoading,
    showSuccess,
    showNotification,
    formatTime,
    getCurrentTime,
    getCurrentDate,
    saveToStorage,
    getFromStorage,
    sortTable,
    printElement,
    resetForm,
    serializeForm,
    enableAutoRefresh
};
