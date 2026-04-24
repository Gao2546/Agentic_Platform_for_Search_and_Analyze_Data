import React, { useState, useEffect } from 'react';
import { projectAPI } from '../services/api';

export default function ScopeManager() {
    const [scopes, setScopes] = useState([]);
    const [tools, setTools] = useState([]);
    const [schedules, setSchedules] = useState([]);
    const [existingTasks, setExistingTasks] = useState([]);
    
    const [selectedScopeId, setSelectedScopeId] = useState('');
    const [selectedScheduleId, setSelectedScheduleId] = useState('');
    const [status, setStatus] = useState({ type: '', message: '' });

    // ฟอร์มข้อมูล
    const [scopeForm, setScopeForm] = useState({ name: '', description: '', goal: '', schedule_mode: 'MANUAL' });
    const [scheduleForm, setScheduleForm] = useState({ cron_expression: '' });
    const [toolForm, setToolForm] = useState({ name: '', language: 'Python', author_type: 'HUMAN', file: null });
    const [taskForm, setTaskForm] = useState({ task_type: 'SEARCH', tool_id: '', depends_on_task_id: '', execution_order: 1, arguments: '{}' });

    // โหลดข้อมูลเริ่มต้น
    const loadInitialData = async () => {
        try {
            const [scopeRes, toolRes] = await Promise.all([projectAPI.getScopes(), projectAPI.getTools()]);
            setScopes(scopeRes.data.data);
            setTools(toolRes.data.data);
        } catch (error) {
            console.error("Failed to fetch initial data", error);
        }
    };

    useEffect(() => { loadInitialData(); }, []);

    // เมื่อเลือก Scope ให้ดึง Schedules ย่อยของ Scope นั้นมา
    useEffect(() => {
        if (!selectedScopeId) return;
        projectAPI.getSchedulesByScope(selectedScopeId).then(res => setSchedules(res.data.data)).catch(console.error);
        setSelectedScheduleId(''); // รีเซ็ต Schedule
    }, [selectedScopeId]);

    // เมื่อเลือก Schedule ให้ดึง Tasks ย่อยเพื่อเอาไว้ผูก Dependencies
    useEffect(() => {
        if (!selectedScheduleId) return;
        projectAPI.getTasksBySchedule(selectedScheduleId).then(res => setExistingTasks(res.data.data)).catch(console.error);
    }, [selectedScheduleId]);

    const showStatus = (type, message) => {
        setStatus({ type, message });
        setTimeout(() => setStatus({ type: '', message: '' }), 5000);
    };

    const handleCreateScope = async (e) => {
        e.preventDefault();
        try {
            await projectAPI.createScope({ user_id: "00000000-0000-0000-0000-000000000000", ...scopeForm });
            showStatus('success', '✅ สร้าง Scope สำเร็จ!');
            setScopeForm({ name: '', description: '', goal: '', schedule_mode: 'MANUAL' });
            loadInitialData();
        } catch (error) { showStatus('error', `❌ สร้าง Scope ล้มเหลว: ${error.message}`); }
    };

    const handleCreateSchedule = async (e) => {
        e.preventDefault();
        if (!selectedScopeId) return showStatus('error', '❌ กรุณาเลือก Scope');
        try {
            await projectAPI.createSchedule(selectedScopeId, {
                task_mode: 'MANUAL', execution_type: scheduleForm.cron_expression ? 'CRON' : 'ONCE',
                cron_expression: scheduleForm.cron_expression || null, is_sequential: true
            });
            showStatus('success', '✅ สร้าง Schedule สำเร็จ!');
            setScheduleForm({ cron_expression: '' });
            projectAPI.getSchedulesByScope(selectedScopeId).then(res => setSchedules(res.data.data)); // รีเฟรชรายการ Schedule
        } catch (error) { showStatus('error', `❌ ล้มเหลว: ${error.message}`); }
    };

    const handleUploadTool = async (e) => {
        e.preventDefault();
        if (!toolForm.file) return showStatus('error', '❌ กรุณาเลือกไฟล์');
        const formData = new FormData();
        Object.keys(toolForm).forEach(key => formData.append(key, toolForm[key]));
        
        try {
            await projectAPI.uploadTool(formData);
            showStatus('success', '✅ อัปโหลด Tool สำเร็จ!');
            setToolForm({ name: '', language: 'Python', author_type: 'HUMAN', file: null });
            document.getElementById('file-upload').value = '';
            loadInitialData(); // รีเฟรชรายชื่อ Tool
        } catch (error) { showStatus('error', `❌ อัปโหลดล้มเหลว: ${error.message}`); }
    };

    const handleCreateTask = async (e) => {
        e.preventDefault();
        if (!selectedScheduleId || !taskForm.tool_id) return showStatus('error', '❌ กรุณาเลือก Schedule และ Tool');
        
        // ตรวจสอบว่า JSON ของ Arguments ถูกต้องหรือไม่
        let parsedArgs = {};
        try { parsedArgs = JSON.parse(taskForm.arguments); } 
        catch (err) { return showStatus('error', '❌ รูปแบบ Arguments JSON ไม่ถูกต้อง'); }

        try {
            await projectAPI.createTask(selectedScheduleId, {
                task_type: taskForm.task_type,
                tool_id: taskForm.tool_id,
                depends_on_task_id: taskForm.depends_on_task_id || null,
                execution_order: parseInt(taskForm.execution_order),
                arguments: parsedArgs
            });
            showStatus('success', '✅ สร้าง Task เพิ่มลงใน Pipeline สำเร็จ! (Airflow กำลังเชื่อมต่อให้)');
            setTaskForm({ ...taskForm, execution_order: parseInt(taskForm.execution_order) + 1, arguments: '{}' });
            projectAPI.getTasksBySchedule(selectedScheduleId).then(res => setExistingTasks(res.data.data)); // รีเฟรชรายการ Task
        } catch (error) { showStatus('error', `❌ ล้มเหลว: ${error.message}`); }
    };

    return (
        <div className="max-w-7xl mx-auto space-y-6">
            <h1 className="text-3xl font-bold text-gray-800 border-b pb-4">🛠 Project & Pipeline Manager</h1>

            {status.message && (
                <div className={`p-4 rounded font-medium text-white ${status.type === 'success' ? 'bg-green-500' : 'bg-red-500'}`}>
                    {status.message}
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* 1. สร้าง Scope */}
                <div className="bg-white rounded-xl shadow-md p-6">
                    <h2 className="text-xl font-bold mb-4 text-blue-600">1. สร้าง Scope ใหม่</h2>
                    <form onSubmit={handleCreateScope} className="space-y-4">
                        <input type="text" placeholder="ชื่อ Scope" className="w-full border p-2 rounded" 
                               value={scopeForm.name} onChange={e => setScopeForm({...scopeForm, name: e.target.value})} required />
                        <button type="submit" className="w-full bg-blue-600 text-white font-bold py-2 rounded">สร้าง Scope</button>
                    </form>
                </div>

                {/* 2. จัดการ Schedule */}
                <div className="bg-white rounded-xl shadow-md p-6">
                    <h2 className="text-xl font-bold mb-4 text-indigo-600">2. สร้าง Schedule ให้ Scope</h2>
                    <form onSubmit={handleCreateSchedule} className="space-y-4">
                        <select className="w-full border p-2 rounded font-bold" value={selectedScopeId} onChange={e => setSelectedScopeId(e.target.value)} required>
                            <option value="">-- เลือก Scope --</option>
                            {scopes.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                        </select>
                        <input type="text" placeholder="CRON Expression (เว้นว่าง = ONCE)" className="w-full border p-2 rounded"
                               value={scheduleForm.cron_expression} onChange={e => setScheduleForm({...scheduleForm, cron_expression: e.target.value})} />
                        <button type="submit" className="w-full bg-indigo-600 text-white font-bold py-2 rounded">สร้าง Schedule</button>
                    </form>
                </div>

                {/* 3. Upload Tool */}
                <div className="bg-white rounded-xl shadow-md p-6">
                    <h2 className="text-xl font-bold mb-4 text-green-600">3. อัปโหลด Tool Script (MinIO)</h2>
                    <form onSubmit={handleUploadTool} className="space-y-4">
                        <input type="text" placeholder="ชื่อ Tool" className="w-full border p-2 rounded" value={toolForm.name} onChange={e => setToolForm({...toolForm, name: e.target.value})} required />
                        <input type="file" id="file-upload" className="w-full border p-2 rounded" onChange={e => setToolForm({...toolForm, file: e.target.files[0]})} required />
                        <button type="submit" className="w-full bg-green-600 text-white font-bold py-2 rounded">Upload Tool</button>
                    </form>
                </div>

                {/* 4. สร้าง Task ใน Schedule (ใหม่ล่าสุด) */}
                <div className="bg-white rounded-xl shadow-md p-6 border-2 border-orange-100">
                    <h2 className="text-xl font-bold mb-4 text-orange-600">4. ประกอบร่าง Task ลงใน Schedule</h2>
                    <form onSubmit={handleCreateTask} className="space-y-4">
                        <select className="w-full border p-2 rounded" value={selectedScheduleId} onChange={e => setSelectedScheduleId(e.target.value)} required>
                            <option value="">-- เลือก Schedule --</option>
                            {schedules.map(s => <option key={s.id} value={s.id}>Schedule: {s.type} {s.cron || ''}</option>)}
                        </select>
                        
                        <div className="grid grid-cols-2 gap-4">
                            <select className="w-full border p-2 rounded" value={taskForm.task_type} onChange={e => setTaskForm({...taskForm, task_type: e.target.value})}>
                                <option value="SEARCH">SEARCH (เก็บข้อมูล)</option>
                                <option value="ETL">ETL (Spark)</option>
                                <option value="TRADITIONAL_LOGIC">TRADITIONAL LOGIC</option>
                                <option value="AI_INFERENCE">AI INFERENCE</option>
                                <option value="VISUALIZE">VISUALIZE</option>
                            </select>
                            <input type="number" placeholder="ลำดับที่ (Execution Order)" className="w-full border p-2 rounded" 
                                   value={taskForm.execution_order} onChange={e => setTaskForm({...taskForm, execution_order: e.target.value})} />
                        </div>

                        <select className="w-full border p-2 rounded" value={taskForm.tool_id} onChange={e => setTaskForm({...taskForm, tool_id: e.target.value})} required>
                            <option value="">-- เลือก Tool ที่จะรัน --</option>
                            {tools.map(t => <option key={t.id} value={t.id}>{t.name} ({t.language})</option>)}
                        </select>

                        <select className="w-full border p-2 rounded" value={taskForm.depends_on_task_id} onChange={e => setTaskForm({...taskForm, depends_on_task_id: e.target.value})}>
                            <option value="">-- ไม่ต้องรอใคร (ทำงานเป็น Task แรก) --</option>
                            {existingTasks.map(t => <option key={t.id} value={t.id}>รอ Task: {t.task_type} (ลำดับ {t.order}) ทำงานเสร็จก่อน</option>)}
                        </select>

                        <div>
                            <label className="block text-sm text-gray-600 mb-1">Arguments (JSON Format)</label>
                            <textarea className="w-full border p-2 rounded font-mono text-sm" rows="3"
                                      value={taskForm.arguments} onChange={e => setTaskForm({...taskForm, arguments: e.target.value})} />
                        </div>

                        <button type="submit" className="w-full bg-orange-500 text-white font-bold py-2 rounded hover:bg-orange-600">
                            + เพิ่ม Task เข้าสู่ Pipeline
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}