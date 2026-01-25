import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000', // Update if backend port changes
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add a request interceptor to attach the token
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Add a response interceptor to handle token refresh (basic implementation)
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;
            try {
                const refreshToken = localStorage.getItem('refresh_token');
                if (refreshToken) {
                    // Adjust endpoint based on your backend: /auth/token/refresh/
                    const { data } = await axios.post('http://localhost:8000/auth/token/refresh/', {
                        refresh: refreshToken
                    });
                    localStorage.setItem('access_token', data.access);
                    // Optionally update refresh token if rotated
                    if (data.refresh) {
                        localStorage.setItem('refresh_token', data.refresh);
                    }
                    api.defaults.headers.common['Authorization'] = `Bearer ${data.access}`;
                    return api(originalRequest);
                }
            } catch (refreshError) {
                console.error("RefreshToken Failed", refreshError);
                // Clear tokens and redirect to login
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);

export default api;
