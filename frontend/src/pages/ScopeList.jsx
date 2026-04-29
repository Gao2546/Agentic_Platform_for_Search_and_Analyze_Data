import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { projectAPI } from '../services/api';
import { useTranslation } from 'react-i18next';

export default function ScopeList() {
    const { t } = useTranslation();
    const navigate = useNavigate();
    
    // --- States ---
    const [activeTab, setActiveTab] = useState('scopes'); // 'scopes' หรือ 'tools'
    const [scopes, setScopes] = useState([]);
    const [tools, setTools] = useState([]);
    const [loading, setLoading] = useState(true);

    // Search States
    const [scopeSearch, setScopeSearch] = useState('');
    const [toolSearch, setToolSearch] = useState('');

    // Modal States
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
    const openScopeModal = (e, scope = null) => {
        if (e) e.stopPropagation();
        if (scope) {
            setEditingScope(scope);
            setScopeFormData({ 
                name: scope.name || '', description: scope.description || '', goal: scope.goal || '', 
                schedule_mode: scope.schedule_mode || 'MANUAL', status: scope.status || 'ACTIVE' 
            });
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
        } catch (error) { alert(`${t('error')}: ${error.message}`); }
    };

    const handleDeleteScope = async () => {
        if (!editingScope) return;
        if (!window.confirm(t('confirm_delete_scope'))) return;
        try {
            await projectAPI.deleteScope(editingScope.id);
            setIsScopeModalOpen(false);
            loadInitialData();
        } catch (error) { alert(`${t('error')}: ${error.message}`); }
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
                if (!toolFile) return alert(t("please_select_file"));
                const fd = new FormData();
                fd.append('name', toolFormData.name);
                fd.append('language', toolFormData.language);
                fd.append('author_type', toolFormData.author_type);
                fd.append('file', toolFile);
                await projectAPI.uploadTool(fd);
            }
            setIsToolModalOpen(false);
            loadInitialData();
        } catch (error) { alert(`${t('error')}: ${error.message}`); }
    };

    const handleDeleteTool = async (id) => {
        if (window.confirm(t('confirm_delete_tool'))) {
            try {
                await projectAPI.deleteTool(id);
                loadInitialData();
            } catch (error) { alert(`${t('error')}: ${t('delete_failed')}`); }
        }
    };

    if (loading) return <div className="p-8 text-center text-gray-500 font-bold">{t('loading')}</div>;

    return (
        <div className="space-y-6">
            {/* Header & Tabs */}
            <div className="flex flex-col md:flex-row md:items-center justify-between border-b pb-4 gap-4">
                <div className="flex space-x-6">
                    <button 
                        onClick={() => setActiveTab('scopes')}
                        className={`text-2xl font-bold transition-colors ${activeTab === 'scopes' ? 'text-blue-600 border-b-4 border-blue-600' : 'text-gray-400 hover:text-gray-600'}`}
                    >
                        📂 {t('scopes')}
                    </button>
                    <button 
                        onClick={() => setActiveTab('tools')}
                        className={`text-2xl font-bold transition-colors ${activeTab === 'tools' ? 'text-indigo-600 border-b-4 border-indigo-600' : 'text-gray-400 hover:text-gray-600'}`}
                    >
                        🛠 {t('tools_library')}
                    </button>
                </div>
                
                <button 
                    onClick={(e) => activeTab === 'scopes' ? openScopeModal(e) : openToolModal()}
                    className={`font-bold py-2 px-6 rounded-lg shadow transition text-white ${activeTab === 'scopes' ? 'bg-blue-600 hover:bg-blue-700' : 'bg-indigo-600 hover:bg-indigo-700'}`}
                >
                    + {activeTab === 'scopes' ? t('create_scope') : t('upload_tool')}
                </button>
            </div>

            {/* --- Scopes Content --- */}
            {activeTab === 'scopes' && (
                <div className="space-y-4">
                    <input 
                        type="text" 
                        placeholder={t('search_scope')} 
                        className="w-full max-w-md border p-2 rounded-lg outline-none focus:ring-2 focus:ring-blue-400"
                        value={scopeSearch}
                        onChange={e => setScopeSearch(e.target.value)}
                    />
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filteredScopes.map(scope => (
                            <div 
                                key={scope.id} 
                                onClick={() => navigate(`/scopes/${scope.id}`)}
                                className="bg-white rounded-xl shadow-sm hover:shadow-md border border-gray-200 p-6 cursor-pointer transition flex flex-col justify-between h-48"
                            >
                                <div>
                                    <div className="flex justify-between items-start mb-2">
                                        <h2 className="text-xl font-bold text-gray-800 line-clamp-1">{scope.name}</h2>
                                        <span className={`text-xs px-2 py-1 rounded-full font-bold ${scope.status === 'ACTIVE' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                            {t(scope.status || 'ACTIVE')}
                                        </span>
                                    </div>
                                    <p className="text-gray-500 text-sm line-clamp-2">{scope.description || t("no_description")}</p>
                                    <div className="mt-2 text-xs font-semibold text-blue-600 bg-blue-50 w-max px-2 py-1 rounded">
                                        Mode: {t(scope.schedule_mode || 'MANUAL')}
                                    </div>
                                </div>
                                <div className="flex justify-end mt-4 border-t pt-3">
                                    <button onClick={(e) => openScopeModal(e, scope)} className="text-sm text-blue-600 font-bold px-3 py-1 bg-blue-50 rounded hover:bg-blue-100 transition">
                                        ✎ {t('edit')}
                                    </button>
                                </div>
                            </div>
                        ))}
                        {filteredScopes.length === 0 && <div className="col-span-full p-8 text-center text-gray-400">{t('no_scope_found')}</div>}
                    </div>
                </div>
            )}

            {/* --- Tools Content --- */}
            {activeTab === 'tools' && (
                <div className="space-y-4">
                    <input 
                        type="text" 
                        placeholder={t('search_tool')} 
                        className="w-full max-w-md border p-2 rounded-lg outline-none focus:ring-2 focus:ring-indigo-400"
                        value={toolSearch}
                        onChange={e => setToolSearch(e.target.value)}
                    />
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                        <table className="w-full text-left">
                            <thead className="bg-gray-50 border-b">
                                <tr>
                                    <th className="p-4 font-bold text-gray-600">{t('name')}</th>
                                    <th className="p-4 font-bold text-gray-600">{t('language')}</th>
                                    <th className="p-4 font-bold text-gray-600">{t('author')}</th>
                                    <th className="p-4 text-right font-bold text-gray-600">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredTools.map(tool => (
                                    <tr key={tool.id} className="border-b hover:bg-gray-50 transition">
                                        <td className="p-4 font-medium text-gray-800">{tool.name}</td>
                                        <td className="p-4"><span className="bg-gray-100 px-2 py-1 rounded text-xs font-bold">{tool.language}</span></td>
                                        <td className="p-4 text-sm text-gray-500">{t(tool.author_type)}</td>
                                        <td className="p-4 text-right space-x-2">
                                            <button onClick={() => openToolModal(tool)} className="text-blue-600 hover:underline font-bold text-sm">✎ {t('edit')}</button>
                                            <button onClick={() => handleDeleteTool(tool.id)} className="text-red-500 hover:underline font-bold text-sm">🗑️ {t('delete')}</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {filteredTools.length === 0 && <div className="p-8 text-center text-gray-400">{t('no_tool_found')}</div>}
                    </div>
                </div>
            )}

            {/* --- Modals --- */}
            {/* Tool Modal */}
            {isToolModalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999] p-4">
                    <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md border-t-4 border-indigo-500">
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-xl font-bold text-gray-800">{editingTool ? t('edit') + ' Tool' : t('upload_tool')}</h2>
                            <button onClick={() => setIsToolModalOpen(false)} className="text-gray-400 hover:text-red-500 text-2xl font-bold">&times;</button>
                        </div>
                        <form onSubmit={handleToolSubmit} className="space-y-4">
                            <div>
                                <label className="block text-gray-700 text-sm font-bold mb-1">{t('name')}</label>
                                <input type="text" className="w-full border p-2 rounded outline-none focus:ring-2 focus:ring-indigo-500" value={toolFormData.name} onChange={e => setToolFormData({...toolFormData, name: e.target.value})} required />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-gray-700 text-sm font-bold mb-1">{t('language')}</label>
                                    <select className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500 outline-none" value={toolFormData.language} onChange={e => setToolFormData({...toolFormData, language: e.target.value})}>
                                        <option value="Python">Python</option>
                                        <option value="Go">Go</option>
                                        <option value="C++">C++</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-gray-700 text-sm font-bold mb-1">{t('author')}</label>
                                    <select className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500 outline-none" value={toolFormData.author_type} onChange={e => setToolFormData({...toolFormData, author_type: e.target.value})}>
                                        <option value="HUMAN">HUMAN</option>
                                        <option value="AI_GENERATED">AI_GENERATED</option>
                                    </select>
                                </div>
                            </div>
                            {!editingTool && (
                                <div>
                                    <label className="block text-gray-700 text-sm font-bold mb-1">{t('file')}</label>
                                    <input type="file" className="w-full border p-2 rounded text-sm bg-gray-50 text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100" onChange={e => setToolFile(e.target.files[0])} required />
                                </div>
                            )}
                            <div className="flex justify-between items-center pt-4 border-t mt-4">
                                {editingTool ? (
                                    <button type="button" onClick={() => handleDeleteTool(editingTool.id)} className="text-red-600 font-bold hover:bg-red-50 px-3 py-2 rounded transition">
                                        🗑️ {t('delete')} Tool
                                    </button>
                                ) : <div />}
                                <div className="space-x-3">
                                    <button type="button" onClick={() => setIsToolModalOpen(false)} className="px-4 py-2 text-gray-600 bg-gray-100 hover:bg-gray-200 rounded font-medium">{t('cancel')}</button>
                                    <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded font-bold hover:bg-indigo-700">{t('save')}</button>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Scope Modal */}
            {isScopeModalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999] p-4">
                    <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-lg">
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-2xl font-bold text-gray-800">{editingScope ? t('edit') + ' Scope' : t('create_scope')}</h2>
                            <button onClick={() => setIsScopeModalOpen(false)} className="text-gray-500 hover:text-red-500 text-2xl font-bold">&times;</button>
                        </div>
                        <form onSubmit={handleScopeSubmit} className="space-y-4">
                           <div>
                                <label className="block text-gray-700 text-sm font-bold mb-1">{t('name')} Scope</label>
                                <input type="text" className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none" value={scopeFormData.name} onChange={e => setScopeFormData({...scopeFormData, name: e.target.value})} required />
                            </div>
                            <div>
                                <label className="block text-gray-700 text-sm font-bold mb-1">{t('description')}</label>
                                <textarea className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none" value={scopeFormData.description} onChange={e => setScopeFormData({...scopeFormData, description: e.target.value})} rows="2" />
                            </div>
                            <div>
                                <label className="block text-gray-700 text-sm font-bold mb-1">{t('goal')}</label>
                                <textarea className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none" value={scopeFormData.goal} onChange={e => setScopeFormData({...scopeFormData, goal: e.target.value})} rows="2" />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-gray-700 text-sm font-bold mb-1">Schedule Mode</label>
                                    <select className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none" value={scopeFormData.schedule_mode} onChange={e => setScopeFormData({...scopeFormData, schedule_mode: e.target.value})}>
                                        <option value="MANUAL">MANUAL</option>
                                        <option value="AI_AGENT">AI AGENT</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-gray-700 text-sm font-bold mb-1">{t('status')}</label>
                                    <select className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none" value={scopeFormData.status} onChange={e => setScopeFormData({...scopeFormData, status: e.target.value})}>
                                        <option value="ACTIVE">ACTIVE</option>
                                        <option value="PAUSED">PAUSED</option>
                                    </select>
                                </div>
                            </div>
                            
                            <div className="flex justify-between items-center pt-4 border-t mt-4">
                                {editingScope ? (
                                    <button type="button" onClick={handleDeleteScope} className="px-4 py-2 text-red-600 bg-red-50 hover:bg-red-100 font-bold rounded transition">
                                        🗑️ {t('delete')} Scope
                                    </button>
                                ) : <div />}
                                
                                <div className="space-x-3">
                                    <button type="button" onClick={() => setIsScopeModalOpen(false)} className="px-4 py-2 text-gray-600 bg-gray-100 hover:bg-gray-200 rounded font-medium">{t('cancel')}</button>
                                    <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded font-bold hover:bg-blue-700">{t('save')}</button>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}