'use client';
import { createContext, useContext, useState, useEffect } from 'react';
import api from '@/lib/api';
import { useRouter } from 'next/navigation';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        checkAuth();
    }, []);

    const checkAuth = async () => {
        const token = localStorage.getItem('access_token');
        if (token) {
            const storedRole = localStorage.getItem('user_role');
            const storedEmail = localStorage.getItem('user_email');
            if (storedRole && storedEmail) {
                setUser({ role: storedRole, email: storedEmail });
            }
        }
        setLoading(false);
    };

    const login = async (email, password) => {
        try {
            const res = await api.post('/auth/login/', { email, password });

            // Check for MFA
            if (res.data.mfa_required) {
                // Alert if push failed (e.g. rate limit or config error)
                if (res.data.push_success === false) {
                    alert(`Duo Push Warning: ${res.data.message}`);
                }
                localStorage.setItem('mfa_id', res.data.mfa_id); // Save for MFA page
                return {
                    mfa_required: true,
                    mfa_id: res.data.mfa_id,
                    email: res.data.email,
                    role: res.data.role
                };
            }

            // Success
            const { access, refresh, role } = res.data;
            localStorage.setItem('access_token', access);
            localStorage.setItem('refresh_token', refresh);
            localStorage.setItem('user_role', role);
            localStorage.setItem('user_email', email);

            setUser({ email, role });
            router.push('/dashboard');
            return { success: true };
        } catch (err) {
            console.error(err);
            throw err.response?.data?.detail || 'Login failed';
        }
    };

    const googleLogin = async (code) => {
        try {
            const res = await api.post('/auth/google/', { code });
            if (res.data.mfa_required) {
                if (res.data.push_success === false) {
                    alert(`Duo Push Warning: ${res.data.message}`);
                }
                localStorage.setItem('mfa_id', res.data.mfa_id);
                localStorage.setItem('mfa_email', res.data.email); // Store for the UI
                return {
                    mfa_required: true,
                    mfa_id: res.data.mfa_id,
                    email: res.data.email,
                    role: res.data.role
                };
            }

            const access = res.data.access_token || res.data.key || res.data.access;
            const refresh = res.data.refresh_token || res.data.refresh;

            if (access) {
                localStorage.setItem('access_token', access);
                if (refresh) localStorage.setItem('refresh_token', refresh);

                // Set user details from response or storage
                const userEmail = res.data.email || 'Google User';
                const userRole = res.data.role || 'STUDENT';
                localStorage.setItem('user_role', userRole);
                localStorage.setItem('user_email', userEmail);

                setUser({ email: userEmail, role: userRole });
                router.push('/dashboard');
                return { success: true };
            }
        } catch (err) {
            console.error(err);
            throw err.response?.data?.detail || 'Google Login failed';
        }
    }

    const logout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_role');
        localStorage.removeItem('user_email');
        setUser(null);
        router.push('/login');
    };

    const completeMfaLogin = (data) => {
        const { access, refresh, role, email } = data;
        localStorage.setItem('access_token', access);
        localStorage.setItem('refresh_token', refresh);
        localStorage.setItem('user_role', role);
        localStorage.setItem('user_email', email);
        setUser({ email, role });
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, googleLogin, logout, completeMfaLogin }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
