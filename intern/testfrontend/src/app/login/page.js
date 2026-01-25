'use client';
import { useState, useEffect, Suspense } from 'react';
import { useAuth } from '@/context/AuthContext';
import { motion } from 'framer-motion';
import { Mail, Lock, LogIn, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';

function LoginContent() {
    const { login, googleLogin } = useAuth();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const searchParams = useSearchParams();
    const code = searchParams.get('code');

    const GOOGLE_CLIENT_ID = "576300956330-hqt2a43s05986cu5363rbtei57sqp8rl.apps.googleusercontent.com";
    // Dynamically determine redirect URI based on current window if possible, but for strictness use localhost:3001
    const GOOGLE_REDIRECT_URI = "http://localhost:3000/login";

    useEffect(() => {
        if (code) {
            handleGoogleCode(code);
        }
    }, [code]);

    const handleGoogleCode = async (authCode) => {
        setLoading(true);
        try {
            const result = await googleLogin(authCode);
            if (result && result.mfa_required) {
                window.location.href = '/mfa-verify';
            }
            // Success redirect handled in context
        } catch (err) {
            setError(typeof err === 'string' ? err : 'Google Login failed');
            setLoading(false);
        }
    };

    const handleGoogleClick = () => {
        // Clear any old tokens/state to prevent interceptor conflicts
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('mfa_id');
        localStorage.removeItem('login_status');

        const scope = "https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile";
        const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?redirect_uri=${encodeURIComponent(GOOGLE_REDIRECT_URI)}&prompt=consent&response_type=code&client_id=${GOOGLE_CLIENT_ID}&scope=${encodeURIComponent(scope)}&access_type=online`;

        window.location.href = authUrl;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        // Match Sprint 2 pattern: Don't call API here, let mfa-verify handle it
        localStorage.setItem('pending_email', email);
        localStorage.setItem('pending_password', password);
        localStorage.setItem('login_status', 'pending');

        // Wait a tiny bit for localStorage if needed, then redirect
        window.location.href = '/mfa-verify';
    };

    return (
        <div className="page-center bg-blue-50">
            <div style={{ position: 'absolute', inset: 0, background: 'var(--muted)', zIndex: -1 }}></div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-card p-8 w-full max-w-md"
            >
                <div className="text-center mb-8">
                    <h1 className="text-2xl font-bold text-[var(--primary)] mb-2">Welcome Back</h1>
                    <p className="text-gray-500 text-sm">Sign in to access your dashboard</p>
                </div>

                {error && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        className="bg-red-50 text-red-600 text-sm p-3 rounded-md mb-4 border border-red-100"
                    >
                        {error}
                    </motion.div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="label">Email Address</label>
                        <div className="relative">
                            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                            <input
                                type="text"
                                className="input-field pl-10"
                                placeholder="you@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required={!code}
                            />
                        </div>
                    </div>

                    <div>
                        <label className="label">Password</label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                            <input
                                type="password"
                                className="input-field pl-10"
                                placeholder="••••••••"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required={!code}
                            />
                        </div>
                    </div>

                    <div className="flex justify-end">
                        <Link href="/forgot-password" className="text-xs text-[var(--primary)] hover:underline">
                            Forgot password?
                        </Link>
                    </div>

                    <button
                        type="submit"
                        className="btn btn-primary w-full"
                        disabled={loading}
                    >
                        {loading ? <Loader2 className="animate-spin" size={20} /> : <><LogIn size={18} /> Sign In</>}
                    </button>
                </form>

                <div className="relative my-6">
                    <div className="absolute inset-0 flex items-center">
                        <div className="w-full border-t border-[var(--border)]"></div>
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-[var(--background)] px-2 text-gray-400 uppercase">Or continue with</span>
                    </div>
                </div>

                <button
                    type="button"
                    className="btn btn-outline w-full"
                    onClick={handleGoogleClick}
                    disabled={loading}
                >
                    <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                        <path
                            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                            fill="#4285F4"
                        />
                        <path
                            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                            fill="#34A853"
                        />
                        <path
                            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                            fill="#FBBC05"
                        />
                        <path
                            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                            fill="#EA4335"
                        />
                    </svg>
                    Sign in with Google
                </button>

            </motion.div>
        </div>
    );
}

export default function LoginPage() {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <LoginContent />
        </Suspense>
    );
}
