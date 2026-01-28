'use client';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { motion } from 'framer-motion';
import { LogOut, LayoutDashboard, BookOpen, GraduationCap, Building2, Plus, Trash2, Edit2, Loader2, Save, X, ShieldCheck, Calendar, Clock, PartyPopper, Users, FileText } from 'lucide-react';

const SlotManager = ({ formData, setFormData }) => {
    const slots = formData.slots || [];
    const addSlot = () => {
        const lastOrder = slots.length > 0 ? Math.max(...slots.map(s => s.slot_order)) : 0;
        const newSlot = { day: 'MONDAY', start_time: '09:00', end_time: '10:00', slot_order: lastOrder + 1, slot_type: 'Theory' };
        setFormData({ ...formData, slots: [...slots, newSlot] });
    };
    const removeSlot = (index) => {
        const newSlots = [...slots];
        newSlots.splice(index, 1);
        setFormData({ ...formData, slots: newSlots });
    };
    const updateSlot = (index, field, value) => {
        const newSlots = [...slots];
        newSlots[index] = { ...newSlots[index], [field]: value };
        setFormData({ ...formData, slots: newSlots });
    };
    return (
        <div className="mt-6 border-t border-blue-100 pt-4 text-left">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider">Time Slots Configuration</h3>
                <button type="button" onClick={addSlot} className="btn btn-outline text-[10px] py-1 px-3">
                    <Plus size={14} /> Add Slot
                </button>
            </div>
            <div className="space-y-3">
                {slots.map((slot, idx) => (
                    <div key={idx} className="bg-white p-3 rounded-lg border border-blue-100 grid grid-cols-2 md:grid-cols-6 gap-2 items-end relative">
                        <div>
                            <label className="text-[9px] font-bold text-gray-400 block mb-1 uppercase">Day</label>
                            <select className="input-field py-1 text-xs" value={slot.day} onChange={e => updateSlot(idx, 'day', e.target.value)}>
                                {['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'].map(d => <option key={d} value={d}>{d}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="text-[9px] font-bold text-gray-400 block mb-1 uppercase">Start</label>
                            <input type="time" className="input-field py-1 text-xs" value={slot.start_time} onChange={e => updateSlot(idx, 'start_time', e.target.value)} />
                        </div>
                        <div>
                            <label className="text-[9px] font-bold text-gray-400 block mb-1 uppercase">End</label>
                            <input type="time" className="input-field py-1 text-xs" value={slot.end_time} onChange={e => updateSlot(idx, 'end_time', e.target.value)} />
                        </div>
                        <div>
                            <label className="text-[9px] font-bold text-gray-400 block mb-1 uppercase">Order</label>
                            <input type="number" className="input-field py-1 text-xs" value={slot.slot_order} onChange={e => updateSlot(idx, 'slot_order', parseInt(e.target.value))} />
                        </div>
                        <div>
                            <label className="text-[9px] font-bold text-gray-400 block mb-1 uppercase">Type</label>
                            <input type="text" className="input-field py-1 text-xs" value={slot.slot_type} onChange={e => updateSlot(idx, 'slot_type', e.target.value)} placeholder="Theory/Lab" />
                        </div>
                        <div className="flex justify-end">
                            <button type="button" onClick={() => removeSlot(idx)} className="text-red-400 hover:text-red-600 p-1 rounded-md hover:bg-red-50"><Trash2 size={16} /></button>
                        </div>
                    </div>
                ))}
                {slots.length === 0 && <div className="text-center py-4 bg-white/50 border border-dashed border-gray-200 rounded-lg text-xs text-gray-400 italic">No slots added yet.</div>}
            </div>
        </div>
    );
};

const HolidayManager = () => {
    const [calendars, setCalendars] = useState([]);
    const [selectedCalendarId, setSelectedCalendarId] = useState('');
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(false);
    const [viewDate, setViewDate] = useState(new Date());
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [selectedDate, setSelectedDate] = useState(null);
    const [reason, setReason] = useState('');

    useEffect(() => {
        api.get('/academic/calendars/').then(res => setCalendars(res.data.results || res.data)).catch(console.error);
    }, []);

    const fetchEvents = async (id) => {
        if (!id) return;
        setLoading(true);
        try {
            const res = await api.get(`/academic/events/?calendar_id=${id}`);
            setEvents(res.data.results || res.data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchEvents(selectedCalendarId);
    }, [selectedCalendarId]);

    const handleDateClick = (dayStr) => {
        if (!selectedCalendarId) {
            alert("Please select a calendar first.");
            return;
        }
        setSelectedDate(dayStr);
        // Check if event already exists
        const existing = events.find(e => e.start_date === dayStr);
        setReason(existing ? existing.description : '');
        setIsModalOpen(true);
    };

    const handleSaveHoliday = async () => {
        try {
            await api.post('/academic/events/', {
                calendar: selectedCalendarId,
                type: 'HOLIDAY',
                name: reason || 'Holiday',
                description: reason,
                start_date: selectedDate,
                end_date: selectedDate
            });
            setIsModalOpen(false);
            fetchEvents(selectedCalendarId);
        } catch (err) {
            console.error(err);
            alert("Failed to save holiday");
        }
    };

    const renderCalendarGrid = () => {
        const year = viewDate.getFullYear();
        const month = viewDate.getMonth();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const firstDay = new Date(year, month, 1).getDay();

        const days = [];
        for (let i = 0; i < firstDay; i++) days.push(null);
        for (let i = 1; i <= daysInMonth; i++) days.push(i);

        return (
            <div className="grid grid-cols-7 gap-1 mt-4">
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(d => (
                    <div key={d} className="text-center text-xs font-bold text-gray-400 py-2">{d}</div>
                ))}
                {days.map((day, idx) => {
                    if (!day) return <div key={idx} />;
                    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                    const event = events.find(e => e.start_date === dateStr);
                    const isHoliday = event && event.type === 'HOLIDAY';

                    return (
                        <div
                            key={idx}
                            onClick={() => handleDateClick(dateStr)}
                            className={`h-16 border rounded cursor-pointer p-1 text-xs hover:bg-blue-50 transition-colors relative
                                ${isHoliday ? 'bg-red-50 border-red-200' : 'bg-white border-gray-100'}
                            `}
                        >
                            <span className="font-bold text-gray-700">{day}</span>
                            {event && (
                                <div className={`text-[9px] mt-1 p-1 rounded leading-tight ${isHoliday ? 'text-red-600 bg-red-100' : 'text-blue-600 bg-blue-100'}`}>
                                    {event.name}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        );
    };

    return (
        <div className="p-6">
            <div className="flex gap-4 mb-4 items-end">
                <div className="flex-1">
                    <label className="label text-xs uppercase font-bold text-gray-400">Select Academic Calendar</label>
                    <select
                        className="input-field"
                        value={selectedCalendarId}
                        onChange={(e) => setSelectedCalendarId(e.target.value)}
                    >
                        <option value="">-- Choose Calendar --</option>
                        {calendars.map(c => <option key={c.calendar_id} value={c.calendar_id}>{c.name} ({c.batch})</option>)}
                    </select>
                </div>
                <div className="flex gap-2">
                    <button onClick={() => setViewDate(new Date(viewDate.setMonth(viewDate.getMonth() - 1)))} className="btn btn-outline px-3">Prev</button>
                    <div className="px-4 py-2 font-bold text-gray-700 min-w-[150px] text-center">
                        {viewDate.toLocaleString('default', { month: 'long', year: 'numeric' })}
                    </div>
                    <button onClick={() => setViewDate(new Date(viewDate.setMonth(viewDate.getMonth() + 1)))} className="btn btn-outline px-3">Next</button>
                </div>
            </div>

            {loading ? <div className="text-center py-10">Loading events...</div> : renderCalendarGrid()}

            {isModalOpen && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-xl p-6 w-full max-w-sm shadow-2xl">
                        <h3 className="text-lg font-bold mb-4">Mark Holiday: {selectedDate}</h3>
                        <label className="block text-xs font-bold text-gray-400 mb-1">Reason / Description</label>
                        <textarea
                            className="input-field h-24 resize-none"
                            value={reason}
                            onChange={e => setReason(e.target.value)}
                            placeholder="e.g. Gandhi Jayanti"
                        />
                        <div className="flex justify-end gap-2 mt-4">
                            <button onClick={() => setIsModalOpen(false)} className="btn btn-outline text-gray-500">Cancel</button>
                            <button onClick={handleSaveHoliday} className="btn btn-primary">Mark as Holiday</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

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

const BulkUploadButton = ({ endpoint, onUploadSuccess }) => {
    const [uploading, setUploading] = useState(false);

    const handleFileChange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setUploading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await api.post(endpoint, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            alert(`Successfully created ${res.data.created} records.`);
            if (onUploadSuccess) onUploadSuccess();
        } catch (err) {
            console.error(err);
            alert("Upload failed. Please check the file format.");
        } finally {
            setUploading(false);
            e.target.value = ''; // Reset input
        }
    };

    return (
        <label className={`btn btn-outline text-xs flex items-center gap-2 cursor-pointer ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}>
            {uploading ? <Loader2 className="animate-spin" size={14} /> : <FileText size={14} />}
            {uploading ? 'Uploading...' : 'Bulk Upload'}
            <input type="file" className="hidden" onChange={handleFileChange} disabled={uploading} accept=".xlsx,.xls,.csv" />
        </label>
    );
};

// Generic Data Manager Component with Schema Support
const DataManager = ({ title, endpoint, icon: Icon, fields = [], idField = 'id', displayField = 'name', renderExtra = null, renderHeaderExtra = null }) => {
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
            if ((field.type === 'select' || field.type === 'multi-select') && field.resource) {
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
            let message = 'Failed to save.';
            if (err.response?.data) {
                const data = err.response.data;
                if (data.detail) {
                    message = data.detail;
                } else if (data.non_field_errors) {
                    message = data.non_field_errors[0];
                } else {
                    // Collect field errors
                    const fieldErrors = Object.entries(data)
                        .map(([key, msg]) => `${key}: ${Array.isArray(msg) ? msg[0] : msg}`)
                        .join('\n');
                    if (fieldErrors) message = `Validation Error:\n${fieldErrors}`;
                }
            }
            alert(message);
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
                <div className="flex gap-2 items-center">
                    {renderHeaderExtra && renderHeaderExtra({ fetchData })}
                    {!isEditing && (
                        <button onClick={startCreate} className="btn btn-primary text-xs">
                            <Plus size={16} /> Add New
                        </button>
                    )}
                </div>
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
                                            {field.options ? (
                                                field.options.map(opt => (
                                                    <option key={opt.id} value={opt.id}>{opt.name}</option>
                                                ))
                                            ) : (
                                                foreignData[field.name]?.map(opt => (
                                                    <option key={opt[field.idKey || 'id']} value={opt[field.idKey || 'id']}>
                                                        {opt[field.displayKey || 'name']}
                                                    </option>
                                                ))
                                            )}
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
                                    ) : field.type === 'multi-select' ? (
                                        <div className="space-y-2 mt-2">
                                            <div className="grid grid-cols-1 gap-2 max-h-40 overflow-y-auto p-2 border border-blue-100 rounded-lg bg-white">
                                                {(field.options || foreignData[field.name])?.map(opt => {
                                                    const val = opt[field.idKey || 'id'] || opt.value;
                                                    const label = opt[field.displayKey || 'name'] || opt.label;
                                                    const isChecked = (formData[field.name] || []).some(m =>
                                                        (m.school_id + ':' + (m.department_id || 'none')) === val ||
                                                        (field.mappingMode && m[field.mappingIdKey || 'id'] === val)
                                                    );

                                                    return (
                                                        <label key={val} className="flex items-center gap-2 p-1 hover:bg-blue-50 rounded cursor-pointer text-xs">
                                                            <input
                                                                type="checkbox"
                                                                className="w-4 h-4 accent-[var(--primary)]"
                                                                checked={isChecked}
                                                                onChange={(e) => {
                                                                    let current = [...(formData[field.name] || [])];
                                                                    if (e.target.checked) {
                                                                        if (field.mappingMode) {
                                                                            const [s_id, d_id] = val.split(':');
                                                                            current.push({ school_id: s_id, department_id: d_id === 'none' ? null : d_id });
                                                                        } else {
                                                                            current.push(val);
                                                                        }
                                                                    } else {
                                                                        if (field.mappingMode) {
                                                                            current = current.filter(m => (m.school_id + ':' + (m.department_id || 'none')) !== val);
                                                                        } else {
                                                                            current = current.filter(v => v !== val);
                                                                        }
                                                                    }
                                                                    setFormData({ ...formData, [field.name]: current });
                                                                }}
                                                            />
                                                            <span className="text-gray-700">{label}</span>
                                                        </label>
                                                    );
                                                })}
                                            </div>
                                            <p className="text-[10px] text-gray-400 italic">Select one or more assignments.</p>
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
                        {renderExtra && renderExtra({ formData, setFormData, currentItem })}
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
                    <TabButton
                        active={activeTab === 'timetable-template'}
                        onClick={() => setActiveTab('timetable-template')}
                        icon={Clock}
                        label="Time Table Templates"
                    />
                    <TabButton
                        active={activeTab === 'sections'}
                        onClick={() => setActiveTab('sections')}
                        icon={LayoutDashboard}
                        label="Sections"
                    />
                    <TabButton
                        active={activeTab === 'holidays'}
                        onClick={() => setActiveTab('holidays')}
                        icon={PartyPopper}
                        label="Holidays"
                    />
                    <TabButton
                        active={activeTab === 'faculty'}
                        onClick={() => setActiveTab('faculty')}
                        icon={Users}
                        label="Faculty Management"
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
                    {activeTab === 'timetable-template' && (
                        <DataManager
                            title="Time Table Templates"
                            endpoint="/academic/timetable-templates/"
                            icon={Clock}
                            idField="template_id"
                            displayField="name"
                            fields={[
                                { name: 'name', label: 'Template Name', required: true },
                                {
                                    name: 'school', label: 'School Mapping', type: 'select', resource: '/create/schools/',
                                    idKey: 'school_id', displayKey: 'school_name', required: true
                                },
                                {
                                    name: 'degree', label: 'Degree Mapping', type: 'select', resource: '/create/degrees/',
                                    idKey: 'degree_id', displayKey: 'degree_name', required: true
                                },
                                {
                                    name: 'department', label: 'Department Mapping', type: 'select', resource: '/create/departments/',
                                    idKey: 'dept_id', displayKey: 'dept_name', required: true
                                },
                                {
                                    name: 'semester', label: 'Semester Mapping', type: 'select', resource: '/create/semesters/',
                                    idKey: 'sem_id', displayKey: 'sem_name', required: true
                                },
                                { name: 'is_active', label: 'Active?', type: 'checkbox', required: false, defaultValue: true },
                            ]}
                            renderExtra={({ formData, setFormData }) => <SlotManager formData={formData} setFormData={setFormData} />}
                        />
                    )}
                    {activeTab === 'sections' && (
                        <DataManager
                            title="Section Management"
                            endpoint="/academic/sections/"
                            icon={LayoutDashboard}
                            idField="section_id"
                            displayField="name"
                            fields={[
                                { name: 'name', label: 'Section Name', required: true, type: 'text' },
                                { name: 'capacity', label: 'Capacity', required: true, type: 'number', defaultValue: 60 },
                                {
                                    name: 'school', label: 'School Mapping', type: 'select', resource: '/create/schools/',
                                    idKey: 'school_id', displayKey: 'school_name', required: true
                                },
                                {
                                    name: 'degree', label: 'Degree Mapping', type: 'select', resource: '/create/degrees/',
                                    idKey: 'degree_id', displayKey: 'degree_name', required: true
                                },
                                {
                                    name: 'department', label: 'Department Mapping', type: 'select', resource: '/create/departments/',
                                    idKey: 'dept_id', displayKey: 'dept_name', required: true
                                },
                                {
                                    name: 'regulation', label: 'Regulation Mapping', type: 'select', resource: '/create/regulations/',
                                    idKey: 'regulation_id', displayKey: 'regulation_code', required: true
                                },
                                { name: 'batch', label: 'Batch / Academic Year', required: true },
                                {
                                    name: 'semester', label: 'Semester Mapping', type: 'select', resource: '/create/semesters/',
                                    idKey: 'sem_id', displayKey: 'sem_name', required: true
                                },
                                { name: 'is_active', label: 'Active?', type: 'checkbox', required: false, defaultValue: true },
                            ]}
                        />
                    )}
                    {activeTab === 'holidays' && (
                        <div className="bg-white rounded-xl shadow-sm border border-[var(--border)] overflow-hidden min-h-[600px]">
                            <div className="p-6 border-b border-[var(--border)] flex gap-3 items-center bg-gray-50">
                                <div className="bg-blue-100 p-2 rounded-lg text-[var(--primary)]">
                                    <PartyPopper size={24} />
                                </div>
                                <h2 className="text-lg font-bold text-gray-800">Holiday Management</h2>
                            </div>
                            <HolidayManager />
                        </div>
                    )}
                    {activeTab === 'faculty' && (
                        <DataManager
                            title="Faculty Management"
                            endpoint="/users/faculty/"
                            icon={Users}
                            idField="faculty_id"
                            displayField="full_name"
                            renderHeaderExtra={({ fetchData }) => (
                                <BulkUploadButton
                                    endpoint="/users/faculty/upload-bulk/"
                                    onUploadSuccess={fetchData}
                                />
                            )}
                            fields={[
                                { name: 'full_name', label: 'Full Name', required: true },
                                { name: 'employee_id', label: 'Employee ID', required: true },
                                { name: 'email', label: 'Email Address', required: true, type: 'email' },
                                { name: 'mobile_no', label: 'Mobile Number', required: false },
                                { name: 'dob', label: 'Date of Birth', required: false, type: 'date' },
                                {
                                    name: 'gender', label: 'Gender', required: true, type: 'select',
                                    options: [
                                        { id: 'MALE', name: 'Male' },
                                        { id: 'FEMALE', name: 'Female' },
                                        { id: 'OTHER', name: 'Other' }
                                    ]
                                },
                                {
                                    name: 'mappings', label: 'School/Department Assignments', type: 'multi-select',
                                    resource: '/users/faculty/mapping-options/',
                                    mappingMode: true,
                                    required: true
                                },
                                { name: 'is_active', label: 'Active Status', type: 'checkbox', defaultValue: true }
                            ]}
                        />
                    )}
                </motion.div>
            </main>
        </div>
    );
}
