'use client';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { motion } from 'framer-motion';
import { LogOut, LayoutDashboard, BookOpen, GraduationCap, Building2, Plus, Trash2, Edit2, Loader2, Save, X, ShieldCheck, Calendar } from 'lucide-react';

// Reusable Tab Component
const TabButton = ({ active, onClick, icon: Icon, label }) => (
    <button
        onClick={onClick}
        className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${active
            ? 'bg-[var(--primary)] text-white shadow-md'
            : 'text-gray-500 hover:bg-white hover:text-[var(--primary)]'
            }`}
    >
        <Icon size={18} />
        <span className="font-medium">{label}</span>
    </button>
);

// Generic Data Manager Component with Schema Support
const DataManager = ({ title, endpoint, icon: Icon, fields = [], idField = 'id', displayField = 'name' }) => {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isEditing, setIsEditing] = useState(false);
    const [currentItem, setCurrentItem] = useState(null);
    const [formData, setFormData] = useState({});
    const [foreignData, setForeignData] = useState({}); // To store school list for dropdowns

    useEffect(() => {
        fetchData();
        fetchForeignResources();
    }, [endpoint]);

    const fetchData = async () => {
        setLoading(true);
        try {
            const res = await api.get(endpoint);
            // Handle different response formats (standard array vs wrapped)
            setData(Array.isArray(res.data) ? res.data : (res.data.results || []));
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const fetchForeignResources = async () => {
        // If any field is a FK (e.g. school_id), fetch the list
        for (const field of fields) {
            if (field.type === 'select' && field.resource) {
                try {
                    const res = await api.get(field.resource);
                    const resourceData = Array.isArray(res.data) ? res.data : (res.data.results || []);
                    setForeignData(prev => ({ ...prev, [field.name]: resourceData }));
                } catch (err) {
                    console.error(`Failed to fetch ${field.resource}`, err);
                }
            }
        }
    };

    const handleDelete = async (id) => {
        if (!confirm('Are you sure?')) return;
        try {
            await api.delete(`${endpoint}${id}/`);
            fetchData();
        } catch (err) {
            alert('Failed to delete');
        }
    };

    const handleSave = async (e) => {
        e.preventDefault();
        try {
            const hasFile = fields.some(f => f.type === 'file');
            let payload;
            let config = {};

            if (hasFile) {
                const fd = new FormData();
                Object.keys(formData).forEach(key => {
                    if (formData[key] !== undefined && formData[key] !== null) {
                        fd.append(key, formData[key]);
                    }
                });
                payload = fd;
                // Important: Override default JSON header for multipart
                config = { headers: { 'Content-Type': 'multipart/form-data' } };
            } else {
                payload = formData;
            }

            if (currentItem) {
                await api.put(`${endpoint}${currentItem[idField]}/`, payload, config);
            } else {
                await api.post(endpoint, payload, config);
            }
            setIsEditing(false);
            setCurrentItem(null);
            setFormData({});
            fetchData();
        } catch (err) {
            console.error(err);
            const detail = err.response?.data?.detail ||
                err.response?.data?.non_field_errors?.[0] ||
                (err.response?.data?.excel_file ? `Excel Error: ${err.response.data.excel_file[0]}` : null) ||
                'Failed to save. Check all fields.';
            alert(detail);
        }
    };

    const startEdit = (item) => {
        setCurrentItem(item);
        const initialForm = {};
        fields.forEach(f => {
            initialForm[f.name] = item[f.name] || '';
        });
        setFormData(initialForm);
        setIsEditing(true);
    };

    const startCreate = () => {
        setCurrentItem(null);
        const initialForm = {};
        fields.forEach(f => {
            initialForm[f.name] = f.defaultValue || '';
        });
        setFormData(initialForm);
        setIsEditing(true);
    };

    return (
        <div className="bg-white rounded-xl shadow-sm border border-[var(--border)] overflow-hidden">
            <div className="p-6 border-b border-[var(--border)] flex justify-between items-center bg-gray-50">
                <div className="flex items-center gap-3">
                    <div className="bg-blue-100 p-2 rounded-lg text-[var(--primary)]">
                        <Icon size={24} />
                    </div>
                    <h2 className="text-lg font-bold text-gray-800">{title}</h2>
                </div>
                {!isEditing && (
                    <button onClick={startCreate} className="btn btn-primary text-xs">
                        <Plus size={16} /> Add New
                    </button>
                )}
            </div>

            {isEditing && (
                <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    className="p-6 bg-blue-50 border-b border-blue-100"
                >
                    <form onSubmit={handleSave} className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {fields.map(field => (
                                <div key={field.name} className="flex-1">
                                    <label className="label text-[10px] uppercase text-gray-400 font-bold">{field.label}</label>
                                    {field.type === 'select' ? (
                                        <select
                                            className="input-field"
                                            value={formData[field.name]}
                                            onChange={e => setFormData({ ...formData, [field.name]: e.target.value })}
                                            required={field.required}
                                        >
                                            <option value="">Select {field.label}</option>
                                            {foreignData[field.name]?.map(opt => (
                                                <option key={opt[field.idKey || 'id']} value={opt[field.idKey || 'id']}>
                                                    {opt[field.displayKey || 'name']}
                                                </option>
                                            ))}
                                        </select>
                                    ) : field.type === 'file' ? (
                                        <div className="flex flex-col gap-1">
                                            <input
                                                type="file"
                                                className="mt-2 text-xs text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                                                onChange={e => setFormData({ ...formData, [field.name]: e.target.files[0] })}
                                                required={field.required}
                                            />
                                            {field.templateUri && (
                                                <a href={field.templateUri} download className="text-[10px] text-blue-600 hover:underline mt-1">
                                                    Download template
                                                </a>
                                            )}
                                        </div>
                                    ) : field.type === 'checkbox' ? (
                                        <div className="flex items-center gap-2 mt-2">
                                            <input
                                                type="checkbox"
                                                className="w-5 h-5 accent-[var(--primary)]"
                                                checked={formData[field.name] || false}
                                                onChange={e => setFormData({ ...formData, [field.name]: e.target.checked })}
                                            />
                                            <span className="text-sm text-gray-600">{field.label}</span>
                                        </div>
                                    ) : (
                                        <input
                                            type={field.type || 'text'}
                                            className="input-field"
                                            value={formData[field.name]}
                                            onChange={e => setFormData({ ...formData, [field.name]: e.target.value })}
                                            placeholder={field.label}
                                            required={field.required}
                                        />
                                    )}
                                </div>
                            ))}
                        </div>
                        <div className="flex gap-2 justify-end pt-2">
                            <button type="button" onClick={() => setIsEditing(false)} className="btn btn-outline py-2 px-4 text-gray-500">
                                <X size={16} /> Cancel
                            </button>
                            <button type="submit" className="btn btn-primary py-2 px-6">
                                <Save size={16} /> {currentItem ? 'Update' : 'Create'}
                            </button>
                        </div>
                    </form>
                </motion.div>
            )}

            <div className="divide-y divide-gray-100">
                {loading ? (
                    <div key="loading" className="p-8 text-center text-gray-400">Loading...</div>
                ) : data.length === 0 ? (
                    <div key="empty" className="p-8 text-center text-gray-400 italic">No records found.</div>
                ) : (
                    data.map((item) => (
                        <div key={item[idField]} className="p-4 flex items-center justify-between hover:bg-gray-50 transition-colors group">
                            <div className="flex flex-col">
                                <span className="font-bold text-gray-700">{item[displayField]}</span>
                                <span className="text-[10px] text-gray-400 font-mono">{item[idField]}</span>
                            </div>
                            <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button onClick={() => startEdit(item)} className="p-2 text-blue-500 hover:bg-blue-50 rounded">
                                    <Edit2 size={16} />
                                </button>
                                <button onClick={() => handleDelete(item[idField])} className="p-2 text-red-500 hover:bg-red-50 rounded">
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default function Dashboard() {
    const { user, logout, loading } = useAuth();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState('schools');

    useEffect(() => {
        if (!loading && !user) {
            router.push('/login');
        }
    }, [user, loading, router]);

    if (loading || !user) {
        return <div className="min-h-screen flex items-center justify-center text-[var(--primary)]"><Loader2 className="animate-spin" size={40} /></div>;
    }

    return (
        <div className="min-h-screen bg-[var(--muted)] flex">
            {/* Sidebar */}
            <aside className="w-64 bg-white border-r border-[var(--border)] flex flex-col fixed h-full z-10 hidden md:flex">
                <div className="p-6 border-b border-[var(--border)]">
                    <div className="flex items-center gap-2 text-[var(--primary)] font-bold text-xl">
                        <LayoutDashboard />
                        <span>AdminPanel</span>
                    </div>
                </div>

                <div className="p-4 flex-1 space-y-2">
                    <p className="px-4 text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Management</p>
                    <TabButton
                        active={activeTab === 'schools'}
                        onClick={() => setActiveTab('schools')}
                        icon={Building2}
                        label="Schools"
                    />
                    <TabButton
                        active={activeTab === 'degrees'}
                        onClick={() => setActiveTab('degrees')}
                        icon={GraduationCap}
                        label="Degrees"
                    />
                    <TabButton
                        active={activeTab === 'departments'}
                        onClick={() => setActiveTab('departments')}
                        icon={BookOpen}
                        label="Departments"
                    />
                    <TabButton
                        active={activeTab === 'semesters'}
                        onClick={() => setActiveTab('semesters')}
                        icon={LayoutDashboard}
                        label="Semesters"
                    />
                    <TabButton
                        active={activeTab === 'regulations'}
                        onClick={() => setActiveTab('regulations')}
                        icon={ShieldCheck}
                        label="Regulations"
                    />
                    <TabButton
                        active={activeTab === 'calendar'}
                        onClick={() => setActiveTab('calendar')}
                        icon={Calendar}
                        label="Academic Setup"
                    />
                </div>

                <div className="p-4 border-t border-[var(--border)]">
                    <div className="flex items-center gap-3 px-4 mb-4">
                        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-[var(--primary)] font-bold text-lg">
                            {user.email[0].toUpperCase()}
                        </div>
                        <div className="overflow-hidden">
                            <p className="text-sm font-bold truncate">{user.email}</p>
                            <p className="text-xs text-gray-500 truncate capitalize">{user.role.replace('_', ' ')}</p>
                        </div>
                    </div>
                    <button onClick={logout} className="w-full btn btn-outline text-red-500 border-red-200 hover:bg-red-50 hover:border-red-300">
                        <LogOut size={16} /> Sign Out
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 md:ml-64 p-8">
                <header className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-800 mb-2 capitalize">{activeTab}</h1>
                    <p className="text-gray-500">Manage your institution's {activeTab} structure here.</p>
                </header>

                <motion.div
                    key={activeTab}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                >
                    {activeTab === 'schools' && (
                        <DataManager
                            title="Schools"
                            endpoint="/create/schools/"
                            icon={Building2}
                            idField="school_id"
                            displayField="school_name"
                            fields={[
                                { name: 'school_name', label: 'School Name', required: true },
                                { name: 'school_code', label: 'School Code', required: true },
                                { name: 'school_short_name', label: 'Short Name', required: true },
                            ]}
                        />
                    )}
                    {activeTab === 'degrees' && (
                        <DataManager
                            title="Degrees"
                            endpoint="/create/degrees/"
                            icon={GraduationCap}
                            idField="degree_id"
                            displayField="degree_name"
                            fields={[
                                { name: 'degree_name', label: 'Degree Name', required: true },
                                { name: 'degree_code', label: 'Degree Code', required: true },
                                { name: 'degree_duration', label: 'Duration (Years)', type: 'number', required: true },
                                { name: 'number_of_semesters', label: 'Total Semesters', type: 'number', required: true },
                                {
                                    name: 'school_id',
                                    label: 'Assign to School',
                                    type: 'select',
                                    resource: '/create/schools/',
                                    idKey: 'school_id',
                                    displayKey: 'school_name',
                                    required: true
                                },
                            ]}
                        />
                    )}
                    {activeTab === 'departments' && (
                        <DataManager
                            title="Departments"
                            endpoint="/create/departments/"
                            icon={BookOpen}
                            idField="dept_id"
                            displayField="dept_name"
                            fields={[
                                { name: 'dept_name', label: 'Department Name', required: true },
                                { name: 'dept_code', label: 'Department Code', required: true },
                                {
                                    name: 'degree',
                                    label: 'Assign to Degree',
                                    type: 'select',
                                    resource: '/create/degrees/',
                                    idKey: 'degree_id',
                                    displayKey: 'degree_name',
                                    required: true
                                },
                            ]}
                        />
                    )}
                    {activeTab === 'semesters' && (
                        <DataManager
                            title="Semesters"
                            endpoint="/create/semesters/"
                            icon={LayoutDashboard}
                            idField="sem_id"
                            displayField="sem_name"
                            fields={[
                                { name: 'sem_name', label: 'Semester Name', required: true },
                                { name: 'sem_short_name', label: 'Short Name (I-I, etc)', required: true },
                                { name: 'sem_number', label: 'Semester Number', type: 'number', required: true },
                                { name: 'year', label: 'Academic Year', type: 'number', required: true },
                                { name: 'annual_exam', label: 'Annual Exam?', type: 'checkbox', required: false },
                                {
                                    name: 'degree',
                                    label: 'Degree',
                                    type: 'select',
                                    resource: '/create/degrees/',
                                    idKey: 'degree_id',
                                    displayKey: 'degree_name',
                                    required: true
                                },
                                {
                                    name: 'department',
                                    label: 'Department',
                                    type: 'select',
                                    resource: '/create/departments/',
                                    idKey: 'dept_id',
                                    displayKey: 'dept_name',
                                    required: true
                                },
                            ]}
                        />
                    )}
                    {activeTab === 'regulations' && (
                        <DataManager
                            title="Regulation Batch Management"
                            endpoint="/create/regulations/"
                            icon={ShieldCheck}
                            idField="regulation_id"
                            displayField="regulation_code"
                            fields={[
                                { name: 'regulation_code', label: 'Regulation ID (e.g. MR25)', required: true },
                                { name: 'batch', label: 'Batch (e.g. 2025-2026)', required: true },
                                {
                                    name: 'degree',
                                    label: 'Degree Mapping',
                                    type: 'select',
                                    resource: '/create/degrees/',
                                    idKey: 'degree_id',
                                    displayKey: 'degree_name',
                                    required: true
                                },
                                { name: 'is_active', label: 'Active?', type: 'checkbox', required: false, defaultValue: true },
                            ]}
                        />
                    )}
                    {activeTab === 'calendar' && (
                        <DataManager
                            title="Calendar Creation"
                            endpoint="/academic/calendars/"
                            icon={Calendar}
                            idField="calendar_id"
                            displayField="name"
                            fields={[
                                { name: 'name', label: 'Academic Calendar Name (e.g. AY 2025-26)', required: true },
                                {
                                    name: 'school',
                                    label: 'School Mapping',
                                    type: 'select',
                                    resource: '/create/schools/',
                                    idKey: 'school_id',
                                    displayKey: 'school_name',
                                    required: true
                                },
                                {
                                    name: 'degree',
                                    label: 'Degree Mapping',
                                    type: 'select',
                                    resource: '/create/degrees/',
                                    idKey: 'degree_id',
                                    displayKey: 'degree_name',
                                    required: true
                                },
                                {
                                    name: 'department',
                                    label: 'Department Mapping',
                                    type: 'select',
                                    resource: '/create/departments/',
                                    idKey: 'dept_id',
                                    displayKey: 'dept_name',
                                    required: true
                                },
                                {
                                    name: 'regulation',
                                    label: 'Regulation Mapping',
                                    type: 'select',
                                    resource: '/create/regulations/',
                                    idKey: 'regulation_id',
                                    displayKey: 'regulation_code',
                                    required: true
                                },
                                { name: 'batch', label: 'Batch / Academic Year', required: true },
                                {
                                    name: 'semester',
                                    label: 'Semester Mapping',
                                    type: 'select',
                                    resource: '/create/semesters/',
                                    idKey: 'sem_id',
                                    displayKey: 'sem_name',
                                    required: true
                                },
                                {
                                    name: 'excel_file',
                                    label: 'Academic Spell Excel',
                                    type: 'file',
                                    required: true,
                                    templateUri: 'http://localhost:8000/academic/template/'
                                },
                                { name: 'is_active', label: 'Active?', type: 'checkbox', required: false, defaultValue: true },
                            ]}
                        />
                    )}
                </motion.div>
            </main>
        </div>
    );
}
