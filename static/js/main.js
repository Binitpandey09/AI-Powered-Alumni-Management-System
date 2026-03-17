// AlumniConnect - Main JavaScript

// Global configuration
const CONFIG = {
    API_BASE_URL: '/api',
    TOKEN_KEY: 'access_token',
    REFRESH_TOKEN_KEY: 'refresh_token',
};

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    console.log('AlumniConnect initialized');
    
    // Check authentication status
    checkAuthStatus();
    
    // Initialize mobile menu toggle
    initMobileMenu();
    
    // Initialize notification dropdown
    initNotifications();
});

// Check if user is authenticated
function checkAuthStatus() {
    const token = localStorage.getItem(CONFIG.TOKEN_KEY);
    if (token) {
        // User is logged in
        updateUIForAuthenticatedUser();
    } else {
        // User is not logged in
        updateUIForGuestUser();
    }
}

// Update UI for authenticated user
function updateUIForAuthenticatedUser() {
    const loginButtons = document.querySelectorAll('.login-btn');
    const logoutButtons = document.querySelectorAll('.logout-btn');
    const userMenus = document.querySelectorAll('.user-menu');
    
    loginButtons.forEach(btn => btn.style.display = 'none');
    logoutButtons.forEach(btn => btn.style.display = 'block');
    userMenus.forEach(menu => menu.style.display = 'block');
}

// Update UI for guest user
function updateUIForGuestUser() {
    const loginButtons = document.querySelectorAll('.login-btn');
    const logoutButtons = document.querySelectorAll('.logout-btn');
    const userMenus = document.querySelectorAll('.user-menu');
    
    loginButtons.forEach(btn => btn.style.display = 'block');
    logoutButtons.forEach(btn => btn.style.display = 'none');
    userMenus.forEach(menu => menu.style.display = 'none');
}

// Initialize mobile menu toggle
function initMobileMenu() {
    const mobileMenuButton = document.querySelector('.mobile-menu-button');
    const mobileMenu = document.querySelector('.mobile-menu');
    
    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
    }
}

// Initialize notifications
function initNotifications() {
    const notificationButton = document.querySelector('.notification-button');
    const notificationDropdown = document.querySelector('.notification-dropdown');
    
    if (notificationButton && notificationDropdown) {
        notificationButton.addEventListener('click', function(e) {
            e.stopPropagation();
            notificationDropdown.classList.toggle('hidden');
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function() {
            notificationDropdown.classList.add('hidden');
        });
    }
}

// Logout function
function logout() {
    localStorage.removeItem(CONFIG.TOKEN_KEY);
    localStorage.removeItem(CONFIG.REFRESH_TOKEN_KEY);
    window.location.href = '/';
}

// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${
        type === 'success' ? 'bg-green-500' :
        type === 'error' ? 'bg-red-500' :
        type === 'warning' ? 'bg-yellow-500' :
        'bg-blue-500'
    }`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Fade in
    setTimeout(() => toast.classList.add('fade-in'), 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Show loading spinner
function showLoading() {
    const loader = document.createElement('div');
    loader.id = 'global-loader';
    loader.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    loader.innerHTML = '<div class="spinner"></div>';
    document.body.appendChild(loader);
}

// Hide loading spinner
function hideLoading() {
    const loader = document.getElementById('global-loader');
    if (loader) {
        loader.remove();
    }
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// Format time
function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
    }).format(amount);
}

// Debounce function
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

// Export functions for use in other scripts
window.AlumniConnect = {
    showToast,
    showLoading,
    hideLoading,
    formatDate,
    formatTime,
    formatCurrency,
    debounce,
    logout
};
