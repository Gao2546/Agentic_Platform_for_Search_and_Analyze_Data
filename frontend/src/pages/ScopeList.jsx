import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { projectAPI } from '../services/api';

export default function ScopeList() {
    const navigate = useNavigate();
    const [scopes, setScopes] = useState([]);
    
    // Modal State
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingScope, setEditingScope] = useState(null);
    
    // อ้างอิงตาม DB Columns: name, description, goal, schedule_mode, status
    const [formData, setFormData] = useState({ 
        name: '', 
        description: '', 
        goal: '', 
        schedule_mode: 'MANUAL',
        status: 'ACTIVE'
    });

    useEffect(() => { loadScopes(); }, []);

    const loadScopes = async () => {
        try {
            const res = await projectAPI.getScopes();
            setScopes(res.data.data || []);
        } catch (error) { console.error("Failed to fetch scopes", error); }
    };

    const openModal = (e, scope = null) => {
        if (e) e.stopPropagation(); 
        
        if (scope) {
            setEditingScope(scope);
            setFormData({ 
                name: scope.name || '', 
                description: scope.description || '', 
                goal: scope.goal || '', 
                schedule_mode: scope.schedule_mode || 'MANUAL',
                status: scope.status || 'ACTIVE'
            });
        } else {
            setEditingScope(null);
            setFormData({ name: '', description: '', goal: '', schedule_mode: 'MANUAL', status: 'ACTIVE' });
        }
        setIsModalOpen(true);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            if (editingScope) {
                await projectAPI.updateScope(editingScope.id, formData);
            } else {
                await projectAPI.createScope({ user_id: "00000000-0000-0000-0000-000000000000", ...formData });
            }
            setIsModalOpen(false);
            loadScopes();
        } catch (error) { alert(`Error: ${error.message}`); }
    };

    const handleDeleteScope = async () => {
        if (!editingScope) return;
        const confirmDelete = window.confirm(`คุณแน่ใจหรือไม่ที่จะลบ Scope "${editingScope.name}"?\n(ข้อมูล Schedule และ Task ทั้งหมดในนี้จะถูกลบทิ้งถาวร)`);
        if (!confirmDelete) return;

        try {
            await projectAPI.deleteScope(editingScope.id);
            setIsModalOpen(false);
            loadScopes();
        } catch (error) { alert(`Error: ${error.message}`); }
    };

    return (
        <div className="space-y-6 relative">
            <div className="flex justify-between items-center border-b pb-4">
                <h1 className="text-3xl font-bold text-gray-800">📂 My Scopes</h1>
                <button 
                    onClick={(e) => openModal(e)} 
                    className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg shadow transition"
                >
                    + สร้าง Scope ใหม่
                </button>
            </div>

            {/* Scope Cards List */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {scopes.map(scope => (
                    <div 
                        key={scope.id} 
                        onClick={() => navigate(`/scopes/${scope.id}`)}
                        className="bg-white rounded-xl shadow-sm hover:shadow-md border border-gray-200 p-6 cursor-pointer transition flex flex-col justify-between h-48"
                    >
                        {/* เนื้อหา Card (เหมือนเดิม) */}
                         <div>
                            <div className="flex justify-between items-start mb-2">
                                <h2 className="text-xl font-bold text-gray-800 line-clamp-1">{scope.name}</h2>
                                <span className={`text-xs px-2 py-1 rounded-full font-bold ${scope.status === 'ACTIVE' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                    {scope.status || 'ACTIVE'}
                                </span>
                            </div>
                            <p className="text-gray-500 text-sm line-clamp-2">{scope.description || "ไม่มีคำอธิบาย"}</p>
                            <div className="mt-2 text-xs font-semibold text-blue-600 bg-blue-50 w-max px-2 py-1 rounded">
                                Mode: {scope.schedule_mode || 'MANUAL'}
                            </div>
                        </div>
                        <div className="flex justify-end mt-4 border-t pt-3">
                            <button 
                                onClick={(e) => openModal(e, scope)} 
                                className="text-sm text-gray-600 hover:text-blue-600 font-medium px-3 py-1 bg-gray-100 hover:bg-blue-50 rounded transition"
                            >
                                ✎ แก้ไข
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            {/* Modal Form */}
            {isModalOpen && (
                <div style={{
                    position: 'fixed',
                    top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 9999
                }}>
                    <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-lg" style={{ maxHeight: '90vh', overflowY: 'auto' }}>
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-2xl font-bold text-gray-800">{editingScope ? 'แก้ไข Scope' : 'สร้าง Scope ใหม่'}</h2>
                            <button onClick={() => setIsModalOpen(false)} className="text-gray-500 hover:text-red-500 text-xl font-bold">&times;</button>
                        </div>
                        
                        <form onSubmit={handleSubmit} className="space-y-4">
                           {/* ฟอร์ม input (เหมือนเดิม) */}
                           <div>
                                <label className="block text-gray-700 text-sm font-bold mb-1">ชื่อ Scope</label>
                                <input type="text" className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none" 
                                    value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} required />
                            </div>
                            <div>
                                <label className="block text-gray-700 text-sm font-bold mb-1">รายละเอียด (Description)</label>
                                <textarea className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none" 
                                    value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} rows="2" />
                            </div>
                            <div>
                                <label className="block text-gray-700 text-sm font-bold mb-1">เป้าหมาย (Goal)</label>
                                <textarea className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none" 
                                    value={formData.goal} onChange={e => setFormData({...formData, goal: e.target.value})} rows="2" placeholder="เช่น ดึงข่าวย้อนหลัง 1 ปีมาวิเคราะห์" />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-gray-700 text-sm font-bold mb-1">Schedule Mode</label>
                                    <select className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                                        value={formData.schedule_mode} onChange={e => setFormData({...formData, schedule_mode: e.target.value})}>
                                        <option value="MANUAL">MANUAL (จัดการเอง)</option>
                                        <option value="AI_AGENT">AI AGENT (AI จัดการให้)</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-gray-700 text-sm font-bold mb-1">สถานะ (Status)</label>
                                    <select className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                                        value={formData.status} onChange={e => setFormData({...formData, status: e.target.value})}>
                                        <option value="ACTIVE">ACTIVE</option>
                                        <option value="PAUSED">PAUSED</option>
                                    </select>
                                </div>
                            </div>
                            
                            <div className="flex justify-between items-center pt-4 border-t mt-4">
                                {editingScope ? (
                                    <button type="button" onClick={handleDeleteScope} className="px-4 py-2 text-red-600 bg-red-50 hover:bg-red-100 font-bold rounded transition">
                                        🗑️ ลบ Scope
                                    </button>
                                ) : <div />} {/* เว้นว่างไว้จัดเลย์เอาต์ตอนสร้างใหม่ */}
                                
                                <div className="space-x-3">
                                    <button type="button" onClick={() => setIsModalOpen(false)} className="px-4 py-2 text-gray-600 bg-gray-100 hover:bg-gray-200 rounded font-medium">ยกเลิก</button>
                                    <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded font-bold hover:bg-blue-700">บันทึก</button>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}