import React, { useState, useEffect } from 'react';
import { projectAPI } from '../services/api';

export default function CodeEditorModal({ 
    isOpen, 
    onClose, 
    toolId, 
    toolName, 
    language, 
    initialCode, 
    onSaveSuccess 
}) {
    const [code, setCode] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    // อัปเดต State เมื่อเปิด Modal หรือโหลดโค้ดใหม่เข้ามา
    useEffect(() => {
        if (isOpen) setCode(initialCode || '');
    }, [isOpen, initialCode]);

    if (!isOpen) return null;

    const getExtension = (lang) => {
        if (lang === 'Python') return 'py';
        if (lang === 'Go') return 'go';
        if (lang === 'C++') return 'cpp';
        return 'txt';
    };

    const handleSaveCode = async () => {
        if (!toolId || !code) return;
        setIsSaving(true);
        
        try {
            const fd = new FormData();
            const ext = getExtension(language);
            const fileName = `${toolName || 'script_edited'}.${ext}`;
            const fileBlob = new Blob([code], { type: 'text/plain' });
            const newFile = new File([fileBlob], fileName);
            
            fd.append('file', newFile);
            
            await projectAPI.updateTool(toolId, fd);
            alert(`✅ บันทึกสคริปต์เรียบร้อย ระบบได้อัปเดตไฟล์บน Data Lake แล้ว`);
            
            if (onSaveSuccess) onSaveSuccess();
            onClose();
        } catch (error) {
            alert(`❌ ไม่สามารถบันทึกโค้ดได้: ${error.message}`);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10000, padding: '1rem' }}>
            <div className="bg-[#1e1e1e] rounded-xl shadow-2xl p-4 w-full max-w-4xl flex flex-col border border-gray-700" style={{ height: '85vh' }}>
                
                {/* Header */}
                <div className="flex justify-between items-center mb-4 border-b border-gray-700 pb-3">
                    <div className="flex items-center space-x-3">
                        <span className="flex space-x-1">
                            <div className="w-3 h-3 rounded-full bg-red-500"></div>
                            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                            <div className="w-3 h-3 rounded-full bg-green-500"></div>
                        </span>
                        <h2 className="text-gray-300 font-mono text-sm font-bold flex items-center">
                            {toolName || 'Quick_Edit_Script'}.{getExtension(language)}
                            <span className="ml-3 px-2 py-0.5 bg-indigo-900/50 text-indigo-300 text-[10px] rounded-full border border-indigo-700/50">
                                📝 โหมดแก้ไขด่วน
                            </span>
                        </h2>
                    </div>
                    <button type="button" onClick={onClose} className="text-gray-400 hover:text-white font-bold text-xl px-2">&times;</button>
                </div>
                
                {/* Editor Area */}
                <div className="flex-1 bg-[#0d0d0d] rounded border border-gray-800 flex flex-col overflow-hidden relative">
                    <textarea 
                        className="flex-1 w-full h-full p-4 bg-transparent text-green-400 font-mono text-sm resize-none outline-none custom-scrollbar"
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                        spellCheck="false"
                        autoComplete="off"
                        autoCorrect="off"
                        style={{ lineHeight: '1.5' }}
                    />
                </div>
                
                {/* Footer Controls */}
                <div className="flex justify-between items-center pt-4 mt-2">
                    <div className="text-gray-500 text-xs flex items-center">
                        💡 สามารถแก้ไขโค้ดและกดบันทึกได้ทันที ระบบจะอัปโหลดทับไฟล์เดิมใน Data Lake ให้อัตโนมัติ
                    </div>
                    <div className="flex space-x-3">
                        <button type="button" onClick={onClose} className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white font-bold rounded-lg transition">
                            ยกเลิก
                        </button>
                        <button 
                            type="button" 
                            onClick={handleSaveCode} 
                            disabled={isSaving}
                            className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white font-bold rounded-lg transition disabled:bg-green-800 disabled:text-gray-300 flex items-center gap-2"
                        >
                            {isSaving ? '⏳ กำลังอัปโหลด...' : '💾 บันทึกการแก้ไข'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}