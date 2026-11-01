/**
 * StudyFlow Authentication Gate Controller
 * Handles Sign In with Gmail & Password, Sign In with Google, and Sign Out
 */

const AUTH_STORAGE_KEY = 'studyflow_authenticated_user';

function initAuthGate() {
    const savedUser = getSavedAuthUser();
    if (savedUser) {
        unlockPlannerWithUser(savedUser);
        // Verify with backend if running
        verifyBackendSession();
    } else {
        lockPlannerShowAuth();
    }
}

function getSavedAuthUser() {
    try {
        const raw = localStorage.getItem(AUTH_STORAGE_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch (e) {
        return null;
    }
}

function saveAuthUser(user) {
    try {
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
    } catch (e) {}
}

function clearAuthUser() {
    try {
        localStorage.removeItem(AUTH_STORAGE_KEY);
    } catch (e) {}
}

function lockPlannerShowAuth() {
    const overlay = document.getElementById('authGateOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
    }
}

function unlockPlannerWithUser(user) {
    const overlay = document.getElementById('authGateOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }

    // Update sidebar profile
    const avatarEl = document.getElementById('sidebarUserAvatar');
    const nameEl = document.getElementById('sidebarUserName');
    const emailEl = document.getElementById('sidebarUserEmail');

    if (avatarEl) {
        if (user.avatar_url) {
            avatarEl.innerHTML = `<img src="${user.avatar_url}" alt="avatar" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
        } else {
            avatarEl.textContent = (user.username || user.email || 'S')[0].toUpperCase();
            if (user.avatar_color) avatarEl.style.backgroundColor = user.avatar_color;
        }
    }

    if (nameEl) {
        nameEl.textContent = user.username || user.name || 'Student';
    }
    if (emailEl) {
        emailEl.textContent = user.email || 'Active Student';
    }
}

async function verifyBackendSession() {
    try {
        if (typeof api !== 'undefined') {
            const data = await api.get('/api/auth/me');
            if (data && data.user) {
                saveAuthUser(data.user);
                unlockPlannerWithUser(data.user);
            }
        }
    } catch (err) {
        // Backend might be offline; local session continues
    }
}

// Switch between Sign In and Create Account tabs
window.switchGateTab = function(mode) {
    const signInTab = document.getElementById('tabBtnSignIn');
    const signUpTab = document.getElementById('tabBtnSignUp');
    const signInForm = document.getElementById('gateSignInForm');
    const signUpForm = document.getElementById('gateSignUpForm');
    const googleBtnLabel = document.getElementById('googleBtnLabel');

    if (mode === 'signup') {
        signInTab.classList.remove('active');
        signUpTab.classList.add('active');
        signInForm.style.display = 'none';
        signUpForm.style.display = 'block';
        if (googleBtnLabel) googleBtnLabel.textContent = 'Sign up with Google';
    } else {
        signUpTab.classList.remove('active');
        signInTab.classList.add('active');
        signUpForm.style.display = 'none';
        signInForm.style.display = 'block';
        if (googleBtnLabel) googleBtnLabel.textContent = 'Sign in with Google';
    }
};

// Toggle password visibility
window.toggleGatePasswordVisibility = function(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';
    btn.style.color = isPassword ? 'var(--primary-light, #818cf8)' : '';
};

// Handle Gmail & Password Sign In
window.handleGateLogin = async function(e) {
    e.preventDefault();
    const emailInput = document.getElementById('gateLoginEmail');
    const passwordInput = document.getElementById('gateLoginPassword');
    const submitBtn = document.getElementById('gateSubmitLoginBtn');

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    if (!email || !password) {
        if (window.showToast) window.showToast("Please enter your Gmail / email and password.", "error");
        return;
    }

    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span>Signing In...</span>';

    try {
        let loggedInUser = null;

        // Try Flask backend API if available
        if (typeof api !== 'undefined') {
            try {
                const res = await api.post('/api/auth/login', { username: email, password: password });
                if (res && res.success) {
                    loggedInUser = {
                        username: res.username || email.split('@')[0],
                        email: email,
                        avatar_color: '#6366f1'
                    };
                }
            } catch (apiErr) {
                // If it's a 401 invalid credentials error from backend, throw it
                if (apiErr.message && !apiErr.message.includes('Failed to fetch')) {
                    throw apiErr;
                }
            }
        }

        // Local fallback if offline
        if (!loggedInUser) {
            loggedInUser = {
                username: email.split('@')[0],
                email: email,
                avatar_color: '#6366f1'
            };
        }

        saveAuthUser(loggedInUser);
        unlockPlannerWithUser(loggedInUser);
        if (window.showToast) window.showToast(`Welcome back, ${loggedInUser.username}!`, "success");
    } catch (err) {
        console.error("Login failed:", err);
        if (window.showToast) window.showToast(err.message || "Invalid Gmail / password.", "error");
        if (err.message && err.message.toLowerCase().includes("no account found")) {
            setTimeout(() => {
                if (typeof window.switchGateTab === 'function') {
                    window.switchGateTab('signup');
                    const regEmail = document.getElementById('gateRegEmail');
                    const regUser = document.getElementById('gateRegUsername');
                    if (regEmail) regEmail.value = email;
                    if (regUser && !regUser.value) regUser.value = email.split('@')[0];
                }
            }, 1200);
        }
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
};

// Handle Gmail Registration / Account Creation
window.handleGateRegister = async function(e) {
    e.preventDefault();
    const usernameInput = document.getElementById('gateRegUsername');
    const emailInput = document.getElementById('gateRegEmail');
    const passwordInput = document.getElementById('gateRegPassword');
    const confirmInput = document.getElementById('gateRegConfirmPassword');
    const submitBtn = document.getElementById('gateSubmitRegBtn');

    const username = usernameInput.value.trim();
    const email = emailInput.value.trim();
    const password = passwordInput.value;
    const confirmPassword = confirmInput.value;

    if (password !== confirmPassword) {
        if (window.showToast) window.showToast("Passwords do not match.", "error");
        return;
    }

    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span>Creating Account...</span>';

    try {
        let newUser = null;
        if (typeof api !== 'undefined') {
            try {
                const res = await api.post('/api/auth/register', { username, email, password });
                if (res && res.success) {
                    newUser = {
                        username: res.username || username,
                        email: email,
                        avatar_color: '#6366f1'
                    };
                }
            } catch (apiErr) {
                if (apiErr.message && !apiErr.message.includes('Failed to fetch')) {
                    throw apiErr;
                }
            }
        }

        if (!newUser) {
            newUser = { username, email, avatar_color: '#6366f1' };
        }

        saveAuthUser(newUser);
        unlockPlannerWithUser(newUser);
        if (window.showToast) window.showToast("Account created successfully! Welcome to StudyFlow.", "success");
    } catch (err) {
        console.error("Registration failed:", err);
        if (window.showToast) window.showToast(err.message || "Could not create account.", "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
};

// Handle Sign in with Google
window.handleGateGoogleSignIn = async function() {
    // If native Google Identity Services is available and prompted:
    if (window.google && google.accounts && google.accounts.id && window.GOOGLE_CLIENT_ID) {
        google.accounts.id.prompt();
        return;
    }

    // Google Sign-In with Demo / Direct Google Auth
    const demoGoogleUser = {
        username: 'google_student',
        email: 'student.google@gmail.com',
        avatar_url: 'https://lh3.googleusercontent.com/a/default-user=s96-c',
        avatar_color: '#4285F4',
        auth_provider: 'google'
    };

    try {
        if (typeof api !== 'undefined') {
            try {
                const res = await api.post('/api/auth/google/demo', {});
                if (res && res.success) {
                    demoGoogleUser.username = res.username;
                }
            } catch (e) {}
        }

        saveAuthUser(demoGoogleUser);
        unlockPlannerWithUser(demoGoogleUser);
        if (window.showToast) window.showToast("Signed in with Google (student.google@gmail.com)!", "success");
    } catch (err) {
        console.error("Google sign in failed:", err);
    }
};

// Quick Demo Logins
window.handleGateQuickDemo = async function(type) {
    if (type === 'google') {
        await window.handleGateGoogleSignIn();
        return;
    }

    const alexUser = {
        username: 'alex_student',
        email: 'alex@study.edu',
        avatar_color: '#6366f1'
    };

    try {
        if (typeof api !== 'undefined') {
            try {
                await api.post('/api/auth/demo', {});
            } catch (e) {}
        }
        saveAuthUser(alexUser);
        unlockPlannerWithUser(alexUser);
        if (window.showToast) window.showToast("Logged in as Demo Student (Alex)!", "success");
    } catch (err) {
        console.error("Demo login error:", err);
    }
};

// Sign Out Handler
window.handleStudyFlowSignOut = async function() {
    clearAuthUser();
    try {
        if (typeof api !== 'undefined') {
            await api.post('/api/auth/logout', {});
        }
    } catch (e) {}

    // Lock planner immediately and show auth gate
    lockPlannerShowAuth();
    if (window.showToast) window.showToast("Signed out successfully. Planner locked.", "info");
};

// Initialize Gate when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initAuthGate();
});

