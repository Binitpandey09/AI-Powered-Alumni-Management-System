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

    // Avatar dropdown
    initAvatarDropdown();
    // Only load avatar if token exists AND avatar button is present on this page
    if (document.getElementById('navbar-avatar-btn') &&
        (localStorage.getItem('access_token') || document.cookie.includes('access_token'))) {
        loadNavbarAvatar();
    }
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

// ── Avatar dropdown open/close ──
function initAvatarDropdown() {
    const btn = document.getElementById('navbar-avatar-btn');
    const dropdown = document.getElementById('navbar-avatar-dropdown');
    const closeBtn = document.getElementById('avatar-dropdown-close');
    if (!btn || !dropdown) return;

    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('hidden');
    });

    document.addEventListener('click', (e) => {
        if (!dropdown.contains(e.target) && e.target !== btn) {
            dropdown.classList.add('hidden');
        }
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', () => dropdown.classList.add('hidden'));
    }
}

// ── Load user data and populate dropdown ──
async function loadNavbarAvatar() {
    try {
        const meResult = await apiGet('/api/accounts/me/');
        if (!meResult.ok) return;
        const user = meResult.data;

        // Initials
        const initials = ((user.first_name?.[0] || '') + (user.last_name?.[0] || '')).toUpperCase()
            || user.email[0].toUpperCase();
        const navInitials = document.getElementById('navbar-avatar-initials');
        const dropInitials = document.getElementById('dropdown-avatar-initials');
        if (navInitials) navInitials.textContent = initials;
        if (dropInitials) dropInitials.textContent = initials;

        // Avatar background color by role
        const roleColors = { alumni: '#534AB7', student: '#2563EB', faculty: '#0F6E56', admin: '#1E293B' };
        const color = roleColors[user.role] || '#2563EB';
        const navBtn = document.getElementById('navbar-avatar-btn');
        const dropCircle = document.getElementById('dropdown-avatar-circle');
        if (navBtn) navBtn.style.background = color;
        if (dropCircle) dropCircle.style.background = color;

        // Name
        const nameEl = document.getElementById('dropdown-user-name');
        if (nameEl) nameEl.textContent = (user.first_name + ' ' + user.last_name).trim() || user.email;

        // Profile link based on role
        const profileLinks = { student: '/profile/student/', alumni: '/profile/alumni/', faculty: '/profile/faculty/' };
        const linkEl = document.getElementById('dropdown-profile-link');
        if (linkEl) linkEl.href = profileLinks[user.role] || '#';

        // Completeness ring (r=28, circumference=175.929)
        const compResult = await apiGet('/api/accounts/profile/completeness/');
        if (compResult.ok) {
            const pct = compResult.data.percentage || 0;
            const circ = 175.929;
            const offset = circ - (circ * pct / 100);
            const ring = document.getElementById('dropdown-ring');
            if (ring) {
                ring.style.strokeDashoffset = offset;
                ring.style.stroke = pct >= 80 ? '#22C55E' : pct >= 50 ? '#F97316' : '#EF4444';
            }
        }

        // For students: get degree info
        if (user.role === 'student') {
            const fullResult = await apiGet('/api/accounts/profile/student/full/');
            if (fullResult.ok && fullResult.data.educations?.length > 0) {
                const gradEdu = fullResult.data.educations.find(e => e.education_type === 'graduation');
                if (gradEdu) {
                    const degreeText = [gradEdu.degree, gradEdu.specialization].filter(Boolean).join(' ');
                    const shortDegree = degreeText.length > 35 ? degreeText.substring(0, 35) + '...' : degreeText;
                    const degEl = document.getElementById('dropdown-user-degree');
                    if (degEl) degEl.textContent = shortDegree;
                }
            }
        }
    } catch (e) {
        console.log('Avatar load error:', e);
    }
}

// ── Logout ──
async function handleLogout() {
    const refresh = localStorage.getItem('refresh_token');
    try {
        if (refresh) await apiPost('/api/accounts/logout/', { refresh });
    } catch (e) {}
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    window.location.href = '/auth/login/';
}
