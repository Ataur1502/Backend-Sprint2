'use client';

import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { LogOut, ShieldAlert, Clock, User, Building2, GraduationCap } from 'lucide-react';
import { motion } from 'framer-motion';

export default function WelcomePage() {
    const { user, logout, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!loading && !user) {
            router.push('/login');
        }
    }, [user, loading, router]);

    if (loading || !user) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    const getRoleContent = () => {
        switch (user.role) {
            case 'STUDENT':
                return {
                    title: 'Student Portal',
                    icon: <GraduationCap size={48} className="text-blue-500" />,
                    message: 'Welcome to the Student Portal. Your personal dashboard, grades, and course materials are currently being prepared for the upcoming semester.'
                };
            case 'FACULTY':
                return {
                    title: 'Faculty Portal',
                    icon: <User size={48} className="text-green-500" />,
                    message: 'Welcome, Faculty Member. The management tools for your courses, attendance, and student tracking are currently under development.'
                };
            case 'ACADEMIC_COORDINATOR':
                return {
                    title: 'Coordinator Portal',
                    icon: <Clock size={48} className="text-orange-500" />,
                    message: 'Welcome, Academic Coordinator. The coordination dashboard and reporting tools are being configured for your access.'
                };
            default:
                return {
                    title: 'Welcome',
                    icon: <ShieldAlert size={48} className="text-red-500" />,
                    message: 'Welcome to the system. You currently do not have administrative access to the main dashboard. Please contact the IT department if you believe this is an error.'
                };
        }
    };

    const content = getRoleContent();

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="max-w-md w-full bg-white rounded-2xl shadow-xl overflow-hidden"
            >
                <div className="p-8 text-center">
                    <div className="mx-auto w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mb-6">
                        {content.icon}
                    </div>

                    <h1 className="text-2xl font-bold text-gray-800 mb-2">{content.title}</h1>
                    <div className="flex items-center justify-center gap-2 mb-6">
                        <span className="px-3 py-1 bg-blue-100 text-blue-700 text-xs font-bold rounded-full uppercase tracking-wider">
                            {user.role}
                        </span>
                    </div>

                    <p className="text-gray-600 mb-8 leading-relaxed">
                        {content.message}
                    </p>

                    <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 mb-8">
                        <div className="flex items-start gap-3 text-left">
                            <Clock className="text-blue-500 flex-shrink-0 mt-0.5" size={18} />
                            <div>
                                <h3 className="text-sm font-bold text-blue-800 uppercase tracking-tight">Status: Under Development</h3>
                                <p className="text-xs text-blue-600 mt-1">We are working hard to bring you the best experience. Please check back later.</p>
                            </div>
                        </div>
                    </div>

                    <button
                        onClick={logout}
                        className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-gray-800 hover:bg-black text-white rounded-xl font-bold transition-all duration-200"
                    >
                        <LogOut size={18} />
                        Logout and Return
                    </button>
                </div>

                <div className="bg-gray-50 p-4 border-t border-gray-100 text-center">
                    <p className="text-[10px] text-gray-400 font-medium uppercase tracking-widest">
                        © 2026 University Management System
                    </p>
                </div>
            </motion.div>
        </div>
    );
}
