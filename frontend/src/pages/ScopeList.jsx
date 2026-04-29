import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { projectAPI } from '../services/api';

export default function ScopeList() {
    const navigate = useNavigate();
    
    // --- States ---
    const [activeTab, setActiveTab] = useState('scopes'); // 'scopes' or 'tools'
    const [scopes, setScopes] = useState([]);
    const [tools, setTools] = useState([]);
    const [loading, setLoading] = useState(true);

    // Search States
    const [scopeSearch, setScopeSearch] = useState('');
    const [toolSearch, setToolSearch] = useState('');

    // Modal States (Common for both Scope and Tool)
    const [isScopeModalOpen, setIsScopeModalOpen] = useState(false);
    const [isToolModalOpen, setIsToolModalOpen] = useState(false);
    
    const [editingScope, setEditingScope] = useState(null);
    const [editingTool, setEditingTool] = useState(null);

    // Form States
    const [scopeFormData, setScopeFormData] = useState({ 
        name: '', description: '', goal: '', schedule_mode: 'MANUAL', status: 'ACTIVE' 
    });
    
    const [toolFile, setToolFile] = useState(null);
    const [toolFormData, setToolFormData] = useState({
        name: '', language: 'Python', author_type: 'HUMAN'
    });

    useEffect(() => { 
        loadInitialData(); 
    }, []);

    const loadInitialData = async () => {
        setLoading(true);
        try {
            const [scopeRes, toolRes] = await Promise.all([
                projectAPI.getScopes(),
                projectAPI.getTools()
            ]);
            setScopes(scopeRes.data.data || []);
            setTools(toolRes.data.data || []);
        } catch (error) {
            console.error("Failed to fetch data", error);
        } finally {
            setLoading(false);
        }
    };

    // --- Filter Logic ---
    const filteredScopes = useMemo(() => {
        return scopes.filter(s => s.name.toLowerCase().includes(scopeSearch.toLowerCase()));
    }, [scopes, scopeSearch]);

    const filteredTools = useMemo(() => {
        return tools.filter(t => t.name.toLowerCase().includes(toolSearch.toLowerCase()));
    }, [tools, toolSearch]);

    // --- Scope Handlers ---
    const openScopeModal = (scope = null) => {
        if (scope) {
            setEditingScope(scope);
            setScopeFormData({ ...scope });
        } else {
            setEditingScope(null);
            setScopeFormData({ name: '', description: '', goal: '', schedule_mode: 'MANUAL', status: 'ACTIVE' });
        }
        setIsScopeModalOpen(true);
    };

    const handleScopeSubmit = async (e) => {
        e.preventDefault();
        try {
            if (editingScope) await projectAPI.updateScope(editingScope.id, scopeFormData);
            else await projectAPI.createScope({ user_id: "00000000-0000-0000-0000-000000000000", ...scopeFormData });
            setIsScopeModalOpen(false);
            loadInitialData();
        } catch (error) { alert(error.message); }
    };

    // --- Tool Handlers ---
    const openToolModal = (tool = null) => {
        if (tool) {
            setEditingTool(tool);
            setToolFormData({ name: tool.name, language: tool.language, author_type: tool.author_type });
        } else {
            setEditingTool(null);
            setToolFile(null);
            setToolFormData({ name: '', language: 'Python', author_type: 'HUMAN' });
        }
        setIsToolModalOpen(true);
    };

    const handleToolSubmit = async (e) => {
        e.preventDefault();
        try {
            if (editingTool) {
                await projectAPI.updateTool(editingTool.id, toolFormData);
            } else {
                if (!toolFile) return alert("กรุณาเลือกไฟล์");
                const fd = new FormData();
                fd.append('name', toolFormData.name);
                fd.append('language', toolFormData.language);
                fd.append('author_type', toolFormData.author_type);
                fd.append('file', toolFile);
                await projectAPI.uploadTool(fd);
            }
            setIsToolModalOpen(false);
            loadInitialData();
        } catch (error) { alert(error.message); }
    };

    const handleDeleteTool = async (id) => {
        if (window.confirm("ต้องการลบ Tool นี้ใช่หรือไม่?")) {
            try {
                await projectAPI.deleteTool(id);
                loadInitialData();
            } catch (error) { alert("ลบไม่สำเร็จ"); }
        }
    };

    if (loading) return <div className="p-8 text-center text-gray-500 font-bold">กำลังโหลด...</div>;

    return (
        <div className="space-y-6">
            {/* Header & Tabs */}
            <div className="flex flex-col md:flex-row md:items-center justify-between border-b pb-4 gap-4">
                <div className="flex space-x-6">
                    <button 
                        onClick={() => setActiveTab('scopes')}
                        className={`text-2xl font-bold transition-colors ${activeTab === 'scopes' ? 'text-blue-600 border-b-4 border-blue-600' : 'text-gray-400 hover:text-gray-600'}`}
                    >
                        📂 My Scopes
                    </button>
                    <button 
                        onClick={() => setActiveTab('tools')}
                        className={`text-2xl font-bold transition-colors ${activeTab === 'tools' ? 'text-indigo-600 border-b-4 border-indigo-600' : 'text-gray-400 hover:text-gray-600'}`}
                    >
                        🛠 Tools Library
                    </button>
                </div>
                
                <button 
                    onClick={() => activeTab === 'scopes' ? openScopeModal() : openToolModal()}
                    className={`font-bold py-2 px-6 rounded-lg shadow transition text-white ${activeTab === 'scopes' ? 'bg-blue-600 hover:bg-blue-700' : 'bg-indigo-600 hover:bg-indigo-700'}`}
                >
                    + {activeTab === 'scopes' ? 'สร้าง Scope ใหม่' : 'อัปโหลด Tool ใหม่'}
                </button>
            </div>

            {/* --- Scopes Content --- */}
            {activeTab === 'scopes' && (
                <div className="space-y-4">
                    <input 
                        type="text" 
                        placeholder="🔍 ค้นหา Scope..." 
                        className="w-full max-w-md border p-2 rounded-lg outline-none focus:ring-2 focus:ring-blue-400"
                        value={scopeSearch}
                        onChange={e => setScopeSearch(e.target.value)}
                    />
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filteredScopes.map(scope => (
                            <div 
                                key={scope.id} 
                                onClick={() => navigate(`/scopes/${scope.id}`)}
                                className="bg-white rounded-xl shadow-sm hover:shadow-md border p-6 cursor-pointer transition flex flex-col justify-between h-48"
                            >
                                <div>
                                    <div className="flex justify-between items-start mb-2">
                                        <h2 className="text-xl font-bold text-gray-800 line-clamp-1">{scope.name}</h2>
                                        <span className={`text-xs px-2 py-1 rounded-full font-bold ${scope.status === 'ACTIVE' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{scope.status}</span>
                                    </div>
                                    <p className="text-gray-500 text-sm line-clamp-2">{scope.description || "ไม่มีคำอธิบาย"}</p>
                                </div>
                                <div className="flex justify-end mt-4 border-t pt-3">
                                    <button onClick={(e) => { e.stopPropagation(); openScopeModal(scope); }} className="text-sm text-blue-600 font-bold px-3 py-1 bg-blue-50 rounded hover:bg-blue-100">✎ แก้ไข</button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* --- Tools Content --- */}
            {activeTab === 'tools' && (
                <div className="space-y-4">
                    <input 
                        type="text" 
                        placeholder="🔍 ค้นหา Tool (เช่น Python, RSI...)" 
                        className="w-full max-w-md border p-2 rounded-lg outline-none focus:ring-2 focus:ring-indigo-400"
                        value={toolSearch}
                        onChange={e => setToolSearch(e.target.value)}
                    />
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                        <table className="w-full text-left">
                            <thead className="bg-gray-50 border-b">
                                <tr>
                                    <th className="p-4 font-bold text-gray-600">ชื่อ Tool</th>
                                    <th className="p-4 font-bold text-gray-600">ภาษา</th>
                                    <th className="p-4 font-bold text-gray-600">ประเภท</th>
                                    <th className="p-4 text-right font-bold text-gray-600">จัดการ</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredTools.map(tool => (
                                    <tr key={tool.id} className="border-b hover:bg-gray-50 transition">
                                        <td className="p-4 font-medium text-gray-800">{tool.name}</td>
                                        <td className="p-4"><span className="bg-gray-100 px-2 py-1 rounded text-xs font-bold">{tool.language}</span></td>
                                        <td className="p-4 text-sm text-gray-500">{tool.author_type}</td>
                                        <td className="p-4 text-right space-x-2">
                                            <button onClick={() => openToolModal(tool)} className="text-blue-600 hover:underline font-bold text-sm">✎ แก้ไข</button>
                                            <button onClick={() => handleDeleteTool(tool.id)} className="text-red-500 hover:underline font-bold text-sm">🗑️ ลบ</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {filteredTools.length === 0 && <div className="p-8 text-center text-gray-400">ไม่พบ Tool ที่คุณค้นหา</div>}
                    </div>
                </div>
            )}

            {/* --- Modals --- */}
            {/* Tool Modal (Upload/Edit) */}
            {isToolModalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999] p-4">
                    <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md border-t-4 border-indigo-500">
                        <h2 className="text-xl font-bold mb-4">{editingTool ? '📝 แก้ไขข้อมูล Tool' : '📤 อัปโหลด Tool ใหม่'}</h2>
                        <form onSubmit={handleToolSubmit} className="space-y-4">
                            <input type="text" placeholder="ชื่อ Tool" className="w-full border p-2 rounded outline-none focus:ring-2 focus:ring-indigo-500" value={toolFormData.name} onChange={e => setToolFormData({...toolFormData, name: e.target.value})} required />
                            <div className="grid grid-cols-2 gap-4">
                                <select className="border p-2 rounded" value={toolFormData.language} onChange={e => setToolFormData({...toolFormData, language: e.target.value})}>
                                    <option value="Python">Python</option>
                                    <option value="Go">Go</option>
                                    <option value="C++">C++</option>
                                </select>
                                <select className="border p-2 rounded" value={toolFormData.author_type} onChange={e => setToolFormData({...toolFormData, author_type: e.target.value})}>
                                    <option value="HUMAN">HUMAN</option>
                                    <option value="AI_GENERATED">AI_GENERATED</option>
                                </select>
                            </div>
                            {!editingTool && (
                                <input type="file" className="w-full border p-2 rounded text-sm bg-gray-50" onChange={e => setToolFile(e.target.files[0])} required />
                            )}
                            <div className="flex justify-end space-x-3 pt-4 border-t">
                                <button type="button" onClick={() => setIsToolModalOpen(false)} className="px-4 py-2 text-gray-500">ยกเลิก</button>
                                <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded font-bold hover:bg-indigo-700">บันทึก</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Scope Modal (โค้ดเดิมของคุณเก้า) */}
            {isScopeModalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999] p-4">
                    <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-lg">
                        <h2 className="text-xl font-bold mb-4">{editingScope ? 'แก้ไข Scope' : 'สร้าง Scope ใหม่'}</h2>
                        <form onSubmit={handleScopeSubmit} className="space-y-4">
                            <input type="text" placeholder="ชื่อ Scope" className="w-full border p-2 rounded" value={scopeFormData.name} onChange={e => setScopeFormData({...scopeFormData, name: e.target.value})} required />
                            <textarea placeholder="รายละเอียด" className="w-full border p-2 rounded" value={scopeFormData.description} onChange={e => setScopeFormData({...scopeFormData, description: e.target.value})} />
                            <div className="flex justify-end space-x-3 pt-4 border-t">
                                <button type="button" onClick={() => setIsScopeModalOpen(false)} className="px-4 py-2 text-gray-500">ยกเลิก</button>
                                <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded font-bold">บันทึก</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}