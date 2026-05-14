import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ReactFlow, Background, Controls, MiniMap, 
  applyNodeChanges, applyEdgeChanges, addEdge, MarkerType
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { projectAPI } from '../services/api';
import DynamicWidgetRenderer from '../components/DynamicWidgetRenderer';
import CodeEditorModal from '../components/CodeEditorModal';
import { TaskSkeleton } from '../components/Skeletons';
import { useTranslation } from 'react-i18next';

export default function ScheduleFlow() {
    const { t } = useTranslation();
    const { scopeId, scheduleId } = useParams();
    const navigate = useNavigate();
    
    const [nodes, setNodes] = useState([]);
    const [edges, setEdges] = useState([]);
    const [tools, setTools] = useState([]); 
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('pipeline'); 

    const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
    const [editingTask, setEditingTask] = useState(null);
    const [taskFormData, setTaskFormData] = useState({
        task_type: 'SEARCH', tool_id: '', engine_type: 'AIRFLOW_DAG', arguments: '{\n  \n}'
    });

    const [isToolModalOpen, setIsToolModalOpen] = useState(false);
    const [editingTool, setEditingTool] = useState(null);
    const [toolFile, setToolFile] = useState(null);
    const [toolFormData, setToolFormData] = useState({
        name: '', language: 'Python', dependencies: '', author_type: 'HUMAN',
        description: '', description_for_vector_db: '', tags: '',
        input_schema: '', output_schema: ''
    });

    const [insightsBlocks, setInsightsBlocks] = useState([]);
    const [currentSchedule, setCurrentSchedule] = useState(null);

    const [isCodeEditorOpen, setIsCodeEditorOpen] = useState(false);
    const [previewCode, setPreviewCode] = useState('');
    const [isPreviewLoading, setIsPreviewLoading] = useState(false);

    useEffect(() => { 
        loadScheduleDetails();
        loadFlowData(); 
        loadTools(); 
        loadInsightsData(); 
    }, [scheduleId]);

    // 🚀 Polling Logic สำหรับหน้า Pipeline
    useEffect(() => {
        let interval;
        // เช็คว่ามี Node จำลองที่กำลังโหลดอยู่ หรือกระดานว่างเปล่า
        const isLoadingNodes = nodes.length > 0 && nodes[0].id.startsWith('loading-');
        const isEmpty = nodes.length === 0;

        if (currentSchedule?.task_mode === 'AI_AGENT' && (isEmpty || isLoadingNodes)) {
            interval = setInterval(() => {
                loadFlowData();
            }, 3000);
        }
        return () => clearInterval(interval);
    }, [currentSchedule, nodes]);

    const loadScheduleDetails = async () => {
        try {
            const res = await projectAPI.getSchedulesByScope(scopeId);
            const schedule = res.data.data.find(s => s.id === scheduleId);
            setCurrentSchedule(schedule);
        } catch (error) { console.error(error); }
    };

    const loadTools = async () => {
        try { const res = await projectAPI.getTools(); setTools(res.data.data || []); } catch (error) { console.error(error); }
    };

    const loadInsightsData = async () => {
        try { const res = await projectAPI.getScheduleInsights(scheduleId); setInsightsBlocks(res.data.data || []); } catch (error) { console.error(error); }
    };

    const loadFlowData = async () => {
        try {
            const res = await projectAPI.getTasksBySchedule(scheduleId);
            const tasks = res.data.data || [];
            
            if (tasks.length === 0) {
                // 🚀 แก้ไขเงื่อนไขตรงนี้: เช็คว่า "มีข้อมูล Schedule แล้ว" และ "โหมดเป็น AI_AGENT"
                if (currentSchedule && currentSchedule.task_mode === 'AI_AGENT') {
                    const loadingNodes = [
                        { id: 'loading-1', position: { x: 150, y: 150 }, type: 'default', data: { label: <TaskSkeleton /> }, draggable: false },
                        { id: 'loading-2', position: { x: 450, y: 150 }, type: 'default', data: { label: <TaskSkeleton /> }, draggable: false }
                    ];``
                    const loadingEdges = [
                        { id: 'e-load', source: 'loading-1', target: 'loading-2', animated: true, style: { stroke: '#a5b4fc', strokeWidth: 2, strokeDasharray: '5,5' } }
                    ];
                    setNodes(loadingNodes);
                    setEdges(loadingEdges);
                } else {
                    setNodes([]); setEdges([]);
                }
                return;
            }
            
            const initialNodes = tasks.map((task) => ({
                id: task.id,
                position: task.ui_position || { x: 100 + Math.random() * 50, y: 100 + Math.random() * 50 },
                data: { 
                    label: (
                        <div>
                            <div className="text-xs text-gray-400">Order: {task.order}</div>
                            <div className="font-bold text-indigo-700">{task.task_type}</div>
                        </div>
                    ),
                    originalData: task 
                },
                type: 'default',
                style: { background: '#fff', border: '2px solid #6366f1', borderRadius: '8px', padding: '10px', width: 160, textAlign: 'center', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }
            }));

            const initialEdges = tasks.filter(task => task.depends_on_task_id).map(task => ({
                id: `e-${task.depends_on_task_id}-${task.id}`, source: task.depends_on_task_id, target: task.id,
                animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1' }, style: { stroke: '#6366f1', strokeWidth: 2 }
            }));

            setNodes(initialNodes); setEdges(initialEdges);
        } finally { setLoading(false); }
    };

    const onNodesChange = useCallback((changes) => setNodes((nds) => applyNodeChanges(changes, nds)), []);
    const onEdgesChange = useCallback((changes) => setEdges((eds) => applyEdgeChanges(changes, eds)), []);
    const onNodeDragStop = async (event, node) => { try { await projectAPI.updateTaskPosition(node.id, { x: node.position.x, y: node.position.y }); } catch (error) {} };
    const onConnect = async (params) => {
        setEdges((eds) => addEdge({ ...params, animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1' }, style: { stroke: '#6366f1', strokeWidth: 2 } }, eds));
        try { await projectAPI.updateTaskDependency(params.target, params.source); } catch (error) {}
    };

    const handleAddNewTask = () => {
        setEditingTask(null);
        setTaskFormData({ task_type: 'SEARCH', tool_id: '', engine_type: 'AIRFLOW_DAG', arguments: '{\n  \n}' });
        setIsTaskModalOpen(true);
    };

    const onNodeDoubleClick = async (event, node) => {
        const task = node.data.originalData;
        setEditingTask(task);
        setTaskFormData({
            task_type: task.task_type || 'SEARCH', tool_id: task.tool_id || '',
            engine_type: task.engine_type || 'AIRFLOW_DAG', arguments: task.arguments ? JSON.stringify(task.arguments, null, 2) : '{\n  \n}'
        });
        setIsTaskModalOpen(true);
    };

    const handleSaveTask = async (e) => {
        e.preventDefault();
        let parsedArgs = {};
        try { parsedArgs = JSON.parse(taskFormData.arguments); } catch (err) { alert(t('invalid_json_format')); return; }
        const payload = { ...taskFormData, arguments: parsedArgs, execution_order: editingTask ? editingTask.order : nodes.length + 1 };
        try {
            if (editingTask) await projectAPI.updateTask(editingTask.id, payload);
            else { payload.ui_position = { x: 250, y: 150 }; await projectAPI.createTask(scheduleId, payload); }
            setIsTaskModalOpen(false); loadFlowData();
        } catch (error) { alert(`${t('error')}: ${error.message}`); }
    };

    const handleDeleteTask = async () => {
        if (!editingTask) return;
        if (!window.confirm(t('confirm_delete_task'))) return;
        try { await projectAPI.deleteTask(editingTask.id); setIsTaskModalOpen(false); loadFlowData(); } catch (error) {}
    };

    const openAddToolModal = () => { setEditingTool(null); setToolFile(null); setToolFormData({ name: '', language: 'Python', author_type: 'HUMAN' }); setIsToolModalOpen(true); };
    const openToolModal = (tool_id = null) => {
            if (tool_id) {
                projectAPI.getToolsDetails(tool_id).then(toolRes => {
                    const tool = toolRes.data.data;
                    if (tool) {
                        setEditingTool(tool);
                        setToolFormData({ 
                            name: tool.name, 
                            language: tool.language, 
                            dependencies: tool.dependencies ? JSON.stringify(tool.dependencies, null, 2) : '',
                            author_type: tool.author_type,
                            description: tool.description || '',
                            description_for_vector_db: tool.description_for_vector_db || '',
                            tags: tool.tags ? tool.tags.join(', ') : '', // แปลง Array กลับเป็น String ไว้แสดงผล
                            input_schema: tool.input_schema ? JSON.stringify(tool.input_schema, null, 2) : '',
                            output_schema: tool.output_schema ? JSON.stringify(tool.output_schema, null, 2) : ''
                        });
                    } else {
                        setEditingTool(null);
                        setToolFile(null);
                        setToolFormData({ 
                            name: '', language: 'Python', dependencies: '', author_type: 'HUMAN',
                            description: '', description_for_vector_db: '', tags: '',
                            input_schema: '', output_schema: ''
                        });
                    }}).catch(err => {
                        alert(`${t('error')}: ไม่สามารถโหลดรายละเอียดเครื่องมือได้ (${err.message})`);
                    });
            setIsToolModalOpen(true);
        };
    }

    const handleToolSubmit = async (e) => {
        e.preventDefault();
        try {
            const tagsArray = toolFormData.tags ? toolFormData.tags.split(',').map(t => t.trim()).filter(t => t) : [];

            // 🚀 เตรียม FormData ชุดเดียว ใช้ได้ทั้งอัปโหลดใหม่และแก้ไข
            const fd = new FormData();
            fd.append('name', toolFormData.name);
            fd.append('language', toolFormData.language);
            fd.append('author_type', toolFormData.author_type);
            fd.append('description', toolFormData.description || '');
            fd.append('description_for_vector_db', toolFormData.description_for_vector_db || '');
            fd.append('tags', JSON.stringify(tagsArray));
            fd.append('input_schema', toolFormData.input_schema);
            fd.append('output_schema', toolFormData.output_schema);

            // ถ้ามีการแนบไฟล์ใหม่เข้ามา ก็แพ็คใส่เข้าไปด้วย
            if (toolFile) {
                fd.append('file', toolFile);
            }

            if (editingTool) {
                // กรณีเป็นการแก้ไข (Update) 
                await projectAPI.updateTool(editingTool.id, fd); // <-- API ของคุณจะส่งเป็น multipart/form-data อัตโนมัติเพราะเป็น formData
                alert(`✅ ${t('tool_edit_success')}`);
            } else {
                // กรณีเป็นการสร้างใหม่ (Upload New)
                if (!toolFile) return alert(t("please_select_file"));
                const res = await projectAPI.uploadTool(fd);
                alert(`✅ ${t('tool_upload_success')}`);

                // กรณีที่เรียกจากหน้า ScheduleFlow เพื่อเซ็ตค่า tool_id ให้ Task กลับ
                if (res && res.data && res.data.tool_id && typeof setTaskFormData !== 'undefined') {
                    setTaskFormData(prev => ({ ...prev, tool_id: res.data.tool_id }));
                }
            }
            setIsToolModalOpen(false);
            if (typeof loadTools === 'function') loadTools();
            if (typeof loadInitialData === 'function') loadInitialData(); // สำหรับหน้า ScopeList
        } catch (error) { 
            alert(`${t('error')}: ${error.message}`); 
        }
    };

    const handleDeleteTool = async (toolId) => {
        if (!window.confirm(t('confirm_delete_tool_warning'))) return;
        try { await projectAPI.deleteTool(toolId); setIsToolModalOpen(false); loadTools(); setTaskFormData(prev => ({ ...prev, tool_id: '' })); } catch (error) {}
    };

    const handlePreviewFile = async () => {
        if (!editingTool) return;
            setIsPreviewLoading(true);
            try {
                const res = await projectAPI.previewToolFile(editingTool.id);
                setPreviewCode(res.data.content);
                setIsCodeEditorOpen(true); // โหลดเสร็จค่อยสั่งเปิด Modal
            } catch (error) {
                alert(`${t('error')}: ไม่สามารถโหลดไฟล์ได้ (${error.message})`);
            } finally {
                setIsPreviewLoading(false);
            }
        };

    const handleSaveCode = async () => {
        if (!editingTool || previewCode === null) return;
        setIsSavingCode(true);
        
        try {
            const fd = new FormData();

            // 1. จำลองข้อความ String ให้กลายเป็น File Object
            const ext = toolFormData.language === 'Python' ? 'py' : toolFormData.language === 'Go' ? 'go' : 'cpp';
            const fileName = `${editingTool.name || 'script_edited'}.${ext}`;
            const fileBlob = new Blob([previewCode], { type: 'text/plain' });
            const newFile = new File([fileBlob], fileName);

            // 2. แนบไฟล์เข้าไปใน FormData (เราส่งแค่นี้ Backend จะรับรู้ว่าอัปเดตแค่ไฟล์)
            fd.append('file', newFile);

            // 3. ยิง API บันทึก
            await projectAPI.updateTool(editingTool.id, fd);
            alert(`✅ ${t('tool_edit_success')} (บันทึกสคริปต์เรียบร้อย)`);

            setPreviewCode(null); // ปิดหน้าต่าง
        } catch (error) {
            alert(`${t('error')}: ไม่สามารถบันทึกโค้ดได้ (${error.message})`);
        } finally {
            setIsSavingCode(false);
        }
    };

    if (loading) return <div className="p-8 text-center text-gray-500 font-bold mt-10">{t('loading_data')}</div>;

    return (
        <div className="flex flex-col h-[85vh] bg-gray-50 border rounded-xl shadow-lg overflow-hidden relative">
            <div className="p-4 border-b bg-white flex justify-between items-center z-10 shadow-sm">
                <div>
                    <h2 className="text-xl font-bold text-gray-800">⛓️ {t('schedule_manager')}</h2>
                    <div className="flex mt-2 space-x-1 bg-gray-100 p-1 rounded-lg w-max">
                        <button onClick={() => setActiveTab('pipeline')} className={`px-4 py-1 text-sm font-bold rounded-md transition ${activeTab === 'pipeline' ? 'bg-white text-indigo-600 shadow-sm' : 'text-gray-500 hover:bg-gray-200'}`}>🔀 {t('pipeline_builder')}</button>
                        <button onClick={() => setActiveTab('dashboard')} className={`px-4 py-1 text-sm font-bold rounded-md transition ${activeTab === 'dashboard' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-500 hover:bg-gray-200'}`}>📊 {t('results_dashboard')}</button>
                    </div>
                </div>
                <div className="space-x-3 flex items-center">
                    <button onClick={() => navigate(`/scopes/${scopeId}`)} className="px-4 py-2 text-gray-600 hover:bg-gray-200 rounded-lg font-medium transition">{t('back')}</button>
                    {activeTab === 'pipeline' && (
                        <button onClick={handleAddNewTask} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg shadow transition">+ {t('add_new_task')}</button>
                    )}
                </div>
            </div>

            <div className={`flex-1 w-full h-full relative ${activeTab === 'pipeline' ? 'block' : 'hidden'}`}>
                <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} onNodeDragStop={onNodeDragStop} onNodeDoubleClick={onNodeDoubleClick} fitView>
                    <Background color="#ccc" gap={16} />
                    <Controls />
                    <MiniMap zoomable pannable nodeColor="#6366f1" maskColor="rgba(0,0,0,0.1)" />
                </ReactFlow>
            </div>

            <div className={`flex-1 w-full h-full overflow-y-auto bg-gray-50 p-6 ${activeTab === 'dashboard' ? 'block' : 'hidden'}`}>
                <DynamicWidgetRenderer blocks={insightsBlocks} />
            </div>

            {/* Modal: Task Configuration */}
            {isTaskModalOpen && (
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9000 }}>
                    <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-lg" style={{ maxHeight: '90vh', overflowY: 'auto' }}>
                        <div className="flex justify-between items-center mb-4 border-b pb-2">
                            <h2 className="text-2xl font-bold text-gray-800">{editingTask ? t('task_config') : t('create_new_task')}</h2>
                            <button onClick={() => setIsTaskModalOpen(false)} className="text-gray-400 hover:text-red-500 text-2xl font-bold">&times;</button>
                        </div>
                        <form onSubmit={handleSaveTask} className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-gray-700 text-sm font-bold mb-1">{t('task_type')}</label>
                                    <select className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500" value={taskFormData.task_type} onChange={e => setTaskFormData({...taskFormData, task_type: e.target.value})}>
                                        <option value="SEARCH">SEARCH</option>
                                        <option value="ETL">ETL</option>
                                        <option value="TRADITIONAL_LOGIC">TRADITIONAL_LOGIC</option>
                                        <option value="AI_INFERENCE">AI_INFERENCE</option>
                                        <option value="VISUALIZE">VISUALIZE</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-gray-700 text-sm font-bold mb-1">{t('engine')}</label>
                                    <select className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500" value={taskFormData.engine_type} onChange={e => setTaskFormData({...taskFormData, engine_type: e.target.value})}>
                                        <option value="AIRFLOW_DAG">AIRFLOW_DAG</option>
                                        <option value="STREAMING_WORKER">STREAMING_WORKER</option>
                                    </select>
                                </div>
                            </div>
                            
                            <div>
                                <div className="flex justify-between items-center mb-1">
                                    <label className="block text-gray-700 text-sm font-bold">{t('tool_script')}</label>
                                    <button type="button" onClick={openAddToolModal} className="text-xs text-indigo-600 hover:text-indigo-800 font-bold hover:underline">
                                        + {t('upload_new_tool')}
                                    </button>
                                </div>
                                <div className="flex space-x-2">
                                    <select className="flex-1 border p-2 rounded focus:ring-2 focus:ring-indigo-500" value={taskFormData.tool_id} onChange={e => setTaskFormData({...taskFormData, tool_id: e.target.value})} required>
                                        <option value="" disabled>{t('select_tool_script')}</option>
                                        {tools.map(t => <option key={t.id} value={t.id}>{t.name} ({t.language})</option>)}
                                    </select>
                                    {taskFormData.tool_id && (
                                        <button type="button" onClick={() => openToolModal(taskFormData.tool_id)} className="px-3 py-2 bg-gray-100 text-blue-600 rounded hover:bg-blue-50 border border-gray-300 font-bold transition">✎</button>
                                    )}
                                </div>
                            </div>

                            <div>
                                <label className="block text-gray-700 text-sm font-bold mb-1">{t('arguments_json')}</label>
                                <textarea className="w-full border p-2 rounded font-mono text-sm bg-gray-50 focus:ring-2 focus:ring-indigo-500" rows="5" value={taskFormData.arguments} onChange={e => setTaskFormData({...taskFormData, arguments: e.target.value})} />
                            </div>
                            <div className="flex justify-between pt-4 border-t mt-4">
                                {editingTask ? <button type="button" onClick={handleDeleteTask} className="px-4 py-2 text-red-600 bg-red-50 hover:bg-red-100 font-bold rounded">🗑️ {t('delete_task')}</button> : <div />} 
                                <div className="space-x-3">
                                    <button type="button" onClick={() => setIsTaskModalOpen(false)} className="px-4 py-2 text-gray-600 bg-gray-100 hover:bg-gray-200 rounded font-medium">{t('cancel')}</button>
                                    <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded font-bold hover:bg-indigo-700">{t('save')}</button>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Modal: Tool Management */}
            {isToolModalOpen && (
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999, padding: '1rem' }}>
                    <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-2xl border-t-4 border-indigo-500 flex flex-col" style={{ maxHeight: '95vh' }}>
                        <div className="flex justify-between items-center mb-4 border-b pb-2">
                            <h2 className="text-xl font-bold text-gray-800">
                                {editingTool ? t('edit_tool') : t('upload_new_tool')}
                            </h2>
                            <button onClick={() => setIsToolModalOpen(false)} className="text-gray-400 hover:text-red-500 text-2xl font-bold">&times;</button>
                        </div>

                        {/* ทำให้ส่วนของแบบฟอร์มเลื่อน Scroll ได้ */}
                        <div className="overflow-y-auto pr-2 custom-scrollbar" style={{ flex: 1 }}>
                            <form id="toolForm" onSubmit={handleToolSubmit} className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-gray-700 text-sm font-bold mb-1">{t('tool_name')}</label>
                                        <input type="text" className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500 outline-none" 
                                            value={toolFormData.name} onChange={e => setToolFormData({...toolFormData, name: e.target.value})} required />
                                    </div>
                                    <div>
                                        <label className="block text-gray-700 text-sm font-bold mb-1">Tags (Comma separated)</label>
                                        <input type="text" placeholder="e.g. finance, python, api" className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500 outline-none" 
                                            value={toolFormData.tags} onChange={e => setToolFormData({...toolFormData, tags: e.target.value})} />
                                    </div>
                                </div>
            
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-gray-700 text-sm font-bold mb-1">{t('language')}</label>
                                        <select className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500 outline-none"
                                            value={toolFormData.language} onChange={e => setToolFormData({...toolFormData, language: e.target.value})}>
                                            <option value="Python">Python</option>
                                            <option value="Go">Go</option>
                                            <option value="C++">C++</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-gray-700 text-sm font-bold mb-1">{t('author')}</label>
                                        <select className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500 outline-none"
                                            value={toolFormData.author_type} onChange={e => setToolFormData({...toolFormData, author_type: e.target.value})}>
                                            <option value="HUMAN">HUMAN</option>
                                            <option value="AI_GENERATED">AI_GENERATED</option>
                                        </select>
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-gray-700 text-sm font-bold mb-1">Dependencies (JSON)</label>
                                    <textarea className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500 outline-none" rows="5"
                                        placeholder='e.g. {&#10;  "pandas": "pandas",&#10;  "boto3": "boto3>=1.28.0",&#10;  "requests": "requests"&#10;}'
                                        value={toolFormData.dependencies} onChange={e => setToolFormData({...toolFormData, dependencies: e.target.value})} />
                                </div>
            
                                <div>
                                    <label className="block text-gray-700 text-sm font-bold mb-1">Description (For UI)</label>
                                    <textarea className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500 outline-none" rows="2"
                                        value={toolFormData.description} onChange={e => setToolFormData({...toolFormData, description: e.target.value})} />
                                </div>
            
                                <div>
                                    <label className="block text-gray-700 text-sm font-bold mb-1">Description for Vector DB (AI Context)</label>
                                    <textarea className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500 outline-none bg-indigo-50" rows="3"
                                        placeholder="Detailed text describing the logic, inputs, and outputs. This will be embedded in the Vector DB to help the AI Agent search and use this tool accurately."
                                        value={toolFormData.description_for_vector_db} onChange={e => setToolFormData({...toolFormData, description_for_vector_db: e.target.value})} />
                                </div>
            
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-gray-700 text-sm font-bold mb-1">Input Schema (JSON)</label>
                                        <textarea 
                                            className="w-full border p-2 rounded font-mono text-xs bg-gray-50 focus:ring-2 focus:ring-indigo-500 outline-none" 
                                            rows="6"
                                            placeholder={'{\n  "type": "object",\n  "properties": {\n    "ticker": { "type": "string" }\n  }\n}'}
                                            value={toolFormData.input_schema} 
                                            onChange={e => setToolFormData({...toolFormData, input_schema: e.target.value})} 
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-gray-700 text-sm font-bold mb-1">Output Schema (JSON)</label>
                                        <textarea 
                                            className="w-full border p-2 rounded font-mono text-xs bg-gray-50 focus:ring-2 focus:ring-indigo-500 outline-none" 
                                            rows="6"
                                            placeholder={'{\n  "type": "object",\n  "properties": {\n    "price": { "type": "number" }\n  }\n}'}
                                            value={toolFormData.output_schema} 
                                            onChange={e => setToolFormData({...toolFormData, output_schema: e.target.value})} 
                                        />
                                    </div>
                                </div>

                                {/* {!editingTool && (
                                    <div className="pt-2">
                                        <label className="block text-gray-700 text-sm font-bold mb-1">{t('script_file')}</label>
                                        <input type="file" className="w-full border p-2 rounded text-sm bg-gray-50 text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100" 
                                            onChange={e => setToolFile(e.target.files[0])} required />
                                    </div>
                                )} */}

                                <div className="pt-4 border-t mt-2">
                                    <div className="flex justify-between items-center mb-1">
                                        <label className="block text-gray-700 text-sm font-bold">
                                            {t('script_file')} 
                                            {editingTool && <span className="text-gray-400 font-normal ml-2">(อัปโหลดเพื่อแทนที่)</span>}
                                        </label>

                                        {/* 🚀 ปุ่ม Preview: จะโชว์เฉพาะตอน Edit Tool เท่านั้น */}
                                        {editingTool && (
                                            <button 
                                                type="button" 
                                                onClick={handlePreviewFile}
                                                disabled={isPreviewLoading}
                                                className="text-xs flex items-center space-x-1 px-3 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md font-bold transition border"
                                            >
                                                {isPreviewLoading ? '⏳ กำลังโหลด...' : '🔍 ดูโค้ดไฟล์ปัจจุบัน'}
                                            </button>
                                        )}
                                    </div>
                                    
                                    <input 
                                        type="file" 
                                        className="w-full border p-2 rounded text-sm bg-gray-50 text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100" 
                                        onChange={e => setToolFile(e.target.files[0])} 
                                        required={!editingTool}
                                    />
                                </div>

                            </form>
                        </div>
                            
                        {/* ปุ่มกด (Fix ให้อยู่ด้านล่างสุด) */}
                        <div className="flex justify-between items-center pt-4 border-t mt-4 bg-white">
                            {editingTool ? (
                                <button type="button" onClick={() => handleDeleteTool(editingTool.id)} className="text-red-600 font-bold hover:bg-red-50 p-2 rounded transition">
                                    🗑️ {t('delete_tool')}
                                </button>
                            ) : <div />}
                            <div className={`flex space-x-3 ${!editingTool ? 'w-full justify-end' : ''}`}>
                                <button type="button" onClick={() => setIsToolModalOpen(false)} className="px-4 py-2 text-gray-600 bg-gray-100 hover:bg-gray-200 rounded font-medium">{t('cancel')}</button>
                                <button type="submit" form="toolForm" className="px-4 py-2 bg-indigo-600 text-white rounded font-bold hover:bg-indigo-700">
                                    {editingTool ? t('save_edit') : t('confirm_upload')}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Code Preview & Edit Modal */}
            {previewCode !== null && (
                <CodeEditorModal 
                isOpen={isCodeEditorOpen}
                onClose={() => setIsCodeEditorOpen(false)}
                toolId={editingTool?.id}
                toolName={editingTool?.name}
                language={toolFormData.language}
                initialCode={previewCode}
                onSaveSuccess={() => {
                    // ทำสิ่งที่ต้องการหลังจากเซฟเสร็จ เช่น สั่งรีเฟรชข้อมูล
                    setIsCodeEditorOpen(false);
                }}
            />
            )}
        </div>
    );
}