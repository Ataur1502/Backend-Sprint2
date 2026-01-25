'use client';
import { useState, Suspense, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import api from '@/lib/api';
import { motion } from 'framer-motion';
import { ShieldCheck, Loader2 } from 'lucide-react';

function MFAContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const email = searchParams.get('email');
    const [code, setCode] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [debugStatus, setDebugStatus] = useState('Initializing...');
    const [mfaIdDebug, setMfaIdDebug] = useState('');

    // Auto-trigger Duo Push if that was the preference could be done here
    // But for now we stick to manual entry or "Check Status" for Duo

    // Poll for Duo Push status
    useEffect(() => {
        const mfa_id = localStorage.getItem('mfa_id');
        if (!mfa_id) return;

        const interval = setInterval(async () => {
            if (loading) return; // Don't overlap requests

            try {
                // Send empty OTP to trigger status check in backend
                const res = await api.post('/auth/mfa-verify/', {
                    mfa_id: mfa_id,
                    otp: ''
                });

                // If success (200 OK), we are verified
                localStorage.setItem('access_token', res.data.access);
                localStorage.setItem('refresh_token', res.data.refresh);
                localStorage.setItem('user_role', res.data.role);
                localStorage.removeItem('mfa_id');

                router.push('/dashboard');
                clearInterval(interval);
            } catch (err) {
                // Ignore "pending" errors, stop on "denied" or other hard errors if needed
                // But for now, just keep polling unless it's a 400 with specific deny?
                // Backend returns 400 for 'pending' too.
                // We'll just continue polling silently.
            }
        }, 3000);

        return () => clearInterval(interval);
    }, [router, loading]);

    const handleVerify = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        const mfa_id = localStorage.getItem('mfa_id');
        if (!mfa_id) {
            setError("MFA Session ID missing. Please login again.");
            setLoading(false);
            return;
        }

        try {
            const res = await api.post('/auth/mfa-verify/', {
                mfa_id: mfa_id,
                otp: code
            });

            // Success
            localStorage.setItem('access_token', res.data.access);
            localStorage.setItem('refresh_token', res.data.refresh);
            localStorage.setItem('user_role', res.data.role);
            localStorage.removeItem('mfa_id');

            router.push('/dashboard');
        } catch (err) {
            setError(err.response?.data?.detail || "Verification failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="page-center bg-blue-50">
            <div style={{ position: 'absolute', inset: 0, background: 'var(--muted)', zIndex: -1 }}></div>
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="glass-card p-8 w-full max-w-md text-center"
            >
                <div className="mb-6 flex justify-center">
                    <div className="bg-[var(--primary-light)] p-3 rounded-full text-[var(--primary)]">
                        <ShieldCheck size={32} />
                    </div>
                </div>

                <h1 className="text-xl font-bold mb-2">Two-Factor Authentication</h1>
                <p className="text-gray-500 text-sm mb-6">
                    Enter the 6-digit passcode from your <b>Duo Mobile App</b> (or email OTP if applicable).
                </p>

                {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

                <form onSubmit={handleVerify} className="space-y-4">
                    <input
                        type="text"
                        className="input-field text-center text-2xl tracking-widest"
                        placeholder="123456"
                        maxLength={6}
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                    />

                    <button className="btn btn-primary w-full" disabled={loading}>
                        {loading ? <Loader2 className="animate-spin" /> : 'Verify Identity'}
                    </button>

                    <p className="text-xs text-gray-400 mt-4 animate-pulse">
                        Waiting for approval...
                    </p>

                    <div className="mt-6 p-2 bg-gray-100 rounded text-[10px] text-gray-500 font-mono text-left overflow-hidden">
                        <p>MFA ID: {mfaIdDebug}</p>
                        <p>Status: {debugStatus}</p>
                    </div>
                </form>
            </motion.div>
        </div>
    );
}

export default function MFAPage() {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <MFAContent />
        </Suspense>
    );
}
