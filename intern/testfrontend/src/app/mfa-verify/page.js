'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';
import { ShieldCheck, Loader2, LogOut, Smartphone, Hash, CheckCircle, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function MFAVerifyPage() {
    const [mfaId, setMfaId] = useState(null);
    const [email, setEmail] = useState(null);
    const [passcode, setPasscode] = useState('');
    const [isVerifying, setIsVerifying] = useState(false);
    const [error, setError] = useState('');
    const [statusMessage, setStatusMessage] = useState('Checking security status...');
    const [isPushSupported, setIsPushSupported] = useState(true);
    const [isSuccess, setIsSuccess] = useState(false);
    const router = useRouter();
    const pollInterval = useRef(null);
    const loginInitiated = useRef(false);

    useEffect(() => {
        const handleLogin = async () => {
            const pendingEmail = localStorage.getItem('pending_email');
            const pendingPassword = localStorage.getItem('pending_password');
            const loginStatus = localStorage.getItem('login_status');

            if (loginStatus === 'pending' && pendingEmail && pendingPassword) {
                if (loginInitiated.current) return;
                loginInitiated.current = true;
                setStatusMessage('Starting verification...');

                try {
                    const response = await api.post('/auth/login/', { email: pendingEmail, password: pendingPassword });
                    localStorage.removeItem('pending_email');
                    localStorage.removeItem('pending_password');
                    localStorage.removeItem('login_status');

                    const { mfa_required, access, refresh, role, mfa_id, push_success, message } = response.data;

                    if (mfa_required) {
                        setMfaId(mfa_id);
                        // Store the session ID locally for fallback use
                        localStorage.setItem('mfa_id', mfa_id);
                        setEmail(response.data.email);
                        setIsPushSupported(push_success);
                        setStatusMessage(message || 'Check your Duo app...');

                        if (push_success) {
                            checkMfaStatus(mfa_id);
                            pollInterval.current = setInterval(() => { checkMfaStatus(mfa_id); }, 3000);
                        }
                    } else {
                        localStorage.setItem('access_token', access);
                        localStorage.setItem('refresh_token', refresh);
                        localStorage.setItem('user_role', role);
                        router.push('/dashboard');
                    }
                } catch (err) {
                    console.error(err);
                    setError('Sign-in failed. Please try again.');
                }
            } else {
                // Resume an existing MFA session if available
                const storedMfaId = localStorage.getItem('mfa_id');
                const storedEmail = localStorage.getItem('mfa_email');
                if (storedMfaId) {
                    setMfaId(storedMfaId);
                    setEmail(storedEmail);
                    setStatusMessage('Check your Duo app...');

                    checkMfaStatus(storedMfaId);
                    if (!pollInterval.current) {
                        pollInterval.current = setInterval(() => { checkMfaStatus(storedMfaId); }, 3000);
                    }
                } else {
                    router.push('/login');
                }
            }
        };

        handleLogin();

        return () => {
            if (pollInterval.current) clearInterval(pollInterval.current);
        };
    }, [router]);

    const checkMfaStatus = async (id) => {
        if (isSuccess) return;
        try {
            const response = await api.post('/auth/mfa-verify/', { mfa_id: id });
            if (response.data.mfa_verified) completeLogin(response.data);
        } catch (err) {
            // Ignore polling errors
        }
    };

    const handlePasscodeVerify = async (e) => {
        e.preventDefault();
        if (!passcode || passcode.length < 6) return;
        setIsVerifying(true);
        setError('');

        // Explicitly use the mfaId from state
        const currentId = mfaId || localStorage.getItem('mfa_id');
        if (!currentId) {
            setError("Session expired. Please sign in again.");
            setIsVerifying(false);
            return;
        }

        try {
            const response = await api.post('/auth/mfa-verify/', { mfa_id: currentId, otp: passcode });
            if (response.data.mfa_verified) completeLogin(response.data);
        } catch (err) {
            console.log(err);
            const msg = err.response?.data?.detail || err.response?.data?.non_field_errors?.[0] || 'Incorrect passcode.';
            setError(msg);
        } finally { setIsVerifying(false); }
    };

    const { completeMfaLogin } = useAuth();

    const completeLogin = (data) => {
        setIsSuccess(true);
        completeMfaLogin(data);
        localStorage.removeItem('mfa_id');
        setTimeout(() => router.push('/dashboard'), 1500);
    };

    const handleLogout = () => { localStorage.clear(); window.location.href = '/login'; };

    return (
        <div className="min-h-screen bg-blue-50 flex items-center justify-center p-4">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="glass-card p-0 w-full max-w-md overflow-hidden bg-white shadow-xl rounded-2xl border border-blue-100"
            >
                <div className="bg-blue-50 p-8 text-center border-b border-blue-100">
                    <motion.div
                        initial={{ scale: 0.8 }}
                        animate={{ scale: 1 }}
                        className="inline-flex p-4 rounded-2xl bg-white shadow-sm text-blue-600 mb-4"
                    >
                        <ShieldCheck size={32} />
                    </motion.div>
                    <h1 className="text-xl font-bold text-slate-800">Two-Step Login</h1>
                    <p className="text-slate-500 text-sm mt-1">Verifying <strong>{email || 'your account'}</strong></p>
                </div>

                <div className="p-8">
                    <AnimatePresence mode="wait">
                        {isSuccess ? (
                            <motion.div
                                key="success"
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="text-center py-8"
                            >
                                <CheckCircle size={64} className="text-green-500 mx-auto mb-4" />
                                <h2 className="text-xl font-bold text-slate-800">Verified</h2>
                                <p className="text-slate-500">Redirecting to dashboard...</p>
                            </motion.div>
                        ) : (
                            <motion.div
                                key="content"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                            >
                                {isPushSupported ? (
                                    <div className="bg-blue-50 border border-blue-100 rounded-xl p-6 text-center mb-6">
                                        <div className="animate-pulse text-blue-600 mb-3 flex justify-center">
                                            <Smartphone size={32} />
                                        </div>
                                        <h3 className="font-semibold text-slate-800 mb-1">Approval Requested</h3>
                                        <p className="text-xs text-slate-500">{statusMessage}</p>
                                    </div>
                                ) : (
                                    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center gap-3 text-amber-800 text-sm mb-6">
                                        <AlertCircle size={20} className="shrink-0" />
                                        <span>{statusMessage || 'Push unavailable'}</span>
                                    </div>
                                )}

                                <div className="relative my-6 text-center">
                                    <span className="bg-white px-2 text-xs font-bold text-slate-400 uppercase tracking-wider relative z-10">Or Passcode</span>
                                    <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-100"></div></div>
                                </div>

                                <form onSubmit={handlePasscodeVerify} className="space-y-4">
                                    <div>
                                        <label className="block text-xs font-bold text-slate-600 uppercase mb-2">Verification Code</label>
                                        <div className="relative">
                                            <Hash size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                                            <input
                                                type="text"
                                                placeholder="000 000"
                                                value={passcode}
                                                onChange={(e) => setPasscode(e.target.value.replace(/\D/g, '').substring(0, 6))}
                                                className="input-field pl-12 text-center text-lg tracking-widest font-semibold"
                                            />
                                        </div>
                                    </div>

                                    {error && (
                                        <motion.div
                                            initial={{ opacity: 0, height: 0 }}
                                            animate={{ opacity: 1, height: 'auto' }}
                                            className="text-red-500 text-xs font-bold text-center bg-red-50 p-2 rounded"
                                        >
                                            {error}
                                        </motion.div>
                                    )}

                                    <button type="submit" className="btn btn-primary w-full h-12" disabled={isVerifying || passcode.length < 6}>
                                        {isVerifying ? <Loader2 className="animate-spin" size={20} /> : 'Verify Code'}
                                    </button>
                                </form>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                <div className="bg-slate-50 p-4 border-t border-slate-100 text-center">
                    <button onClick={handleLogout} className="text-slate-500 text-sm hover:text-red-500 flex items-center justify-center gap-2 w-full">
                        <LogOut size={16} />
                        <span>Cancel and Sign Out</span>
                    </button>
                </div>
            </motion.div>
        </div>
    );
}
