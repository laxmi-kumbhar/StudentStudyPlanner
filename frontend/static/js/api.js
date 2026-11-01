const API_BASE = (window.location.hostname === '127.0.0.1' && window.location.port === '5000') 
    ? '' 
    : 'http://127.0.0.1:5000';

const api = {
    async request(url, options = {}) {
        const fullEndpoint = (url.startsWith('/api') && API_BASE) ? `${API_BASE}${url}` : url;
        
        const defaultHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };

        const config = {
            credentials: 'include',
            ...options,
            headers: {
                ...defaultHeaders,
                ...(options.headers || {})
            }
        };

        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        try {
            const response = await fetch(fullEndpoint, config);
            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                const errorMessage = data.error || `HTTP error ${response.status}`;
                if (response.status === 401 && !window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
                    if (window.showToast) window.showToast("Session expired. Redirecting to login...", 'info');
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 800);
                }
                throw new Error(errorMessage);
            }

            return data;
        } catch (error) {
            console.error(`API Error [${options.method || 'GET'} ${url}]:`, error);
            if (window.showToast) {
                window.showToast(error.message, 'error');
            }
            throw error;
        }
    },

    get(url, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;
        return this.request(fullUrl, { method: 'GET' });
    },

    post(url, body) {
        return this.request(url, { method: 'POST', body });
    },

    put(url, body) {
        return this.request(url, { method: 'PUT', body });
    },

    patch(url, body) {
        return this.request(url, { method: 'PATCH', body });
    },

    delete(url) {
        return this.request(url, { method: 'DELETE' });
    }
};

window.api = api;
