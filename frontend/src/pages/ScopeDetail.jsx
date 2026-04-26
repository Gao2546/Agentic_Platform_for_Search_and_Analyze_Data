import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { projectAPI } from "../services/api";
import DynamicWidgetRenderer from "../components/DynamicWidgetRenderer";

export default function ScopeDetail() {
  const { scopeId } = useParams();
  const navigate = useNavigate();
  const [schedules, setSchedules] = useState([]);

  // State สำหรับเก็บข้อมูล Insights ของแต่ละ Schedule
  const [scheduleInsights, setScheduleInsights] = useState({});

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [cronInputType, setCronInputType] = useState("TIME");
  const [timeValue, setTimeValue] = useState("08:00");
  const [editingSchedule, setEditingSchedule] = useState(null);

  const [formData, setFormData] = useState({
    name: "",
    task_mode: "MANUAL",
    execution_type: "CRON",
    restart_policy: "ON_FAILURE",
    is_sequential: true,
    cron_expression: "",
  });

  useEffect(() => {
    loadSchedules();
  }, [scopeId]);

  const loadSchedules = async () => {
    try {
      const res = await projectAPI.getSchedulesByScope(scopeId);
      const loadedSchedules = res.data.data || [];
      setSchedules(loadedSchedules);
      
      // พอโหลด Schedules เสร็จ ให้ไปดึงข้อมูล Insights ของแต่ละตัวมาแสดงผล
      fetchInsightsForSchedules(loadedSchedules);
    } catch (error) {
      console.error("Failed to fetch schedules", error);
    }
  };

const fetchInsightsForSchedules = async (loadedSchedules) => {
    try {
      const insightsData = {};
      
      // ใช้ Promise.all เพื่อยิง API ของทุก Schedule พร้อมกัน (ดึงข้อมูลเร็วขึ้น)
      await Promise.all(
        loadedSchedules.map(async (sch) => {
          try {
            const res = await projectAPI.getScheduleInsights(sch.id);
            // ตรวจสอบว่ามีข้อมูลส่งกลับมาไหม ถ้ามีให้เอามาใส่ใน Object
            if (res.data && res.data.data && res.data.data.length > 0) {
               insightsData[sch.id] = res.data.data;
            } else {
               insightsData[sch.id] = []; // ถ้าไม่มีก็ใส่ Array ว่างไว้ก่อน
            }
          } catch (err) {
            console.error(`Failed to fetch insight for schedule ${sch.id}`, err);
            insightsData[sch.id] = [];
          }
        })
      );
      
      // อัปเดต State ทีเดียวจบ กราฟโผล่พรึบ!
      setScheduleInsights(insightsData);
      
    } catch (error) {
      console.error("Error fetching all insights:", error);
    }
  };

  const openModal = (schedule = null) => {
    if (schedule) {
      setEditingSchedule(schedule);
      setFormData({
        name: schedule.name || "",
        task_mode: schedule.task_mode || "MANUAL",
        execution_type: schedule.type || schedule.execution_type || "CRON",
        restart_policy: schedule.restart_policy || "ON_FAILURE",
        is_sequential: schedule.is_sequential !== false,
        cron_expression: schedule.cron || schedule.cron_expression || "",
      });

      if (schedule.cron && schedule.cron.split(" ").length >= 2) {
        const parts = schedule.cron.split(" ");
        if (!isNaN(parts[0]) && !isNaN(parts[1])) {
          setTimeValue(`${parts[1].padStart(2, "0")}:${parts[0].padStart(2, "0")}`);
          setCronInputType("TIME");
        } else {
          setCronInputType("CUSTOM");
        }
      } else {
        setCronInputType("CUSTOM");
      }
    } else {
      setEditingSchedule(null);
      setFormData({
        name: "", task_mode: "MANUAL", execution_type: "CRON",
        restart_policy: "ON_FAILURE", is_sequential: true, cron_expression: "",
      });
      setTimeValue("08:00");
      setCronInputType("TIME");
    }
    setIsModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    let finalCron = formData.cron_expression;
    if (formData.execution_type === "CRON" && cronInputType === "TIME") {
      const [hour, minute] = timeValue.split(":");
      finalCron = `${parseInt(minute)} ${parseInt(hour)} * * *`;
    }
    if (formData.execution_type !== "CRON") {
      finalCron = null;
    }

    const payload = { ...formData, cron_expression: finalCron };

    try {
      if (editingSchedule) {
        await projectAPI.updateSchedule(editingSchedule.id, payload);
      } else {
        await projectAPI.createSchedule(scopeId, payload);
      }
      setIsModalOpen(false);
      loadSchedules();
    } catch (error) {
      alert(`Error: ${error.message}`);
    }
  };

  const handleDeleteSchedule = async () => {
    if (!editingSchedule) return;
    const confirmDelete = window.confirm(`คุณแน่ใจหรือไม่ที่จะลบ Schedule นี้?\n(Task ย่อยทั้งหมดในนี้จะถูกลบทิ้งด้วย)`);
    if (!confirmDelete) return;

    try {
        await projectAPI.deleteSchedule(editingSchedule.id);
        setIsModalOpen(false);
        loadSchedules();
    } catch (error) { alert(`Error: ${error.message}`); }
  };

  return (
    <div className="space-y-6 relative">
      <button
        onClick={() => navigate("/scopes")}
        className="text-blue-600 hover:underline font-medium flex items-center"
      >
        <span>&larr; กลับไปหน้า Scopes</span>
      </button>

      <div className="flex justify-between items-center border-b pb-4 mt-2">
        <h1 className="text-3xl font-bold text-gray-800">⏱ Schedules</h1>
        <button
          onClick={() => openModal()}
          className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded-lg shadow transition"
        >
          + เพิ่ม Schedule
        </button>
      </div>

      {/* Grid 2 คอลัมน์ เพื่อให้มีพื้นที่แสดงกราฟสวยๆ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-2 gap-6">
        {schedules.map((schedule) => (
          <div
            key={schedule.id}
            // ใช้ flex-col h-auto เพื่อให้การ์ดยืดขยายตามเนื้อหา Dynamic Component ได้
            className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col justify-between h-auto"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                    schedule.type === "CRON" ? "bg-green-100 text-green-700"
                      : schedule.type === "CONTINUOUS" ? "bg-orange-100 text-orange-700" : "bg-gray-100 text-gray-700"
                  }`}
                >
                  {schedule.type || schedule.execution_type}
                </span>
                <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
                  {schedule.task_mode || "MANUAL"}
                </span>
              </div>
              
              <h2 className="text-xl font-bold text-gray-800 mt-2 line-clamp-1">
                {schedule.name || "Unnamed Schedule"}
              </h2>
              <p className="text-sm font-medium text-indigo-600 mt-1">
                {schedule.type === "CRON" ? `🕒 ${schedule.cron || schedule.cron_expression}`
                  : schedule.type === "CONTINUOUS" ? "⚡ ตลอดเวลา (Streaming)" : "🎯 ทำงานครั้งเดียว"}
              </p>
              
              <ul className="text-xs text-gray-500 mt-3 space-y-1">
                <li><strong>Restart Policy:</strong> {schedule.restart_policy || "N/A"}</li>
                <li><strong>Run Mode:</strong> {schedule.is_sequential === false ? "Parallel" : "Sequential"}</li>
              </ul>
            </div>

            {/* 🚀 ส่วนที่แทรก Dynamic Widget สำหรับแสดงกราฟ/ตัวเลข */}
            {scheduleInsights[schedule.id] && scheduleInsights[schedule.id].length > 0 && (
              <div className="mt-5 pt-5 border-t border-gray-100 flex-1">
                <div className="flex justify-between items-center mb-3">
                    <h3 className="text-sm font-bold text-gray-700">📊 ผลการวิเคราะห์ล่าสุด</h3>
                    <span className="text-[10px] text-gray-400">อัปเดตเมื่อสักครู่</span>
                </div>
                
                {/* โยน JSON Blocks เข้าไปให้ Renderer จัดการวาด UI ทันที */}
                <DynamicWidgetRenderer blocks={scheduleInsights[schedule.id]} />
              </div>
            )}

            <div className="flex justify-between items-center mt-5 border-t pt-3">
              <button
                onClick={() => navigate(`/scopes/${scopeId}/schedules/${schedule.id}/flow`)}
                className="text-sm bg-indigo-50 text-indigo-700 px-3 py-1 rounded hover:bg-indigo-100 font-bold transition flex items-center"
              >
                ⚙️ จัดการ Tasks
              </button>
              <button
                onClick={() => openModal(schedule)}
                className="text-sm text-gray-500 hover:text-blue-600 font-medium"
              >
                ✎ แก้ไข
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Modal Form สำหรับสร้าง/แก้ไข Schedule */}
      {isModalOpen && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}>
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-lg" style={{ maxHeight: "90vh", overflowY: "auto" }}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold text-gray-800">{editingSchedule ? "แก้ไข Schedule" : "ตั้งเวลาทำงานใหม่"}</h2>
              <button onClick={() => setIsModalOpen(false)} className="text-gray-500 hover:text-red-500 text-xl font-bold">&times;</button>
            </div>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-gray-700 text-sm font-bold mb-1">ชื่อตารางเวลา (Schedule Name)</label>
                <input type="text" className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500 outline-none" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} placeholder="เช่น แจ้งเตือนราคา Bitcoin หลุดแนวรับ" required />
              </div>
              <div className="grid grid-cols-2 gap-4 mt-2">
                <div>
                  <label className="block text-gray-700 text-sm font-bold mb-1">Task Mode</label>
                  <select className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500 outline-none" value={formData.task_mode} onChange={(e) => setFormData({ ...formData, task_mode: e.target.value })}>
                    <option value="MANUAL">MANUAL</option>
                    <option value="AI_AGENT">AI_AGENT</option>
                  </select>
                </div>
                <div>
                  <label className="block text-gray-700 text-sm font-bold mb-1">Execution Type</label>
                  <select className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500 outline-none" value={formData.execution_type} onChange={(e) => setFormData({ ...formData, execution_type: e.target.value })}>
                    <option value="CRON">CRON (ตั้งเวลา)</option>
                    <option value="ONCE">ONCE (รันครั้งเดียว)</option>
                    <option value="CONTINUOUS">CONTINUOUS (สตรีมมิ่ง)</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-700 text-sm font-bold mb-1">Restart Policy</label>
                  <select className="w-full border p-2 rounded focus:ring-2 focus:ring-indigo-500 outline-none" value={formData.restart_policy} onChange={(e) => setFormData({ ...formData, restart_policy: e.target.value })}>
                    <option value="ALWAYS">ALWAYS</option>
                    <option value="ON_FAILURE">ON_FAILURE</option>
                    <option value="NEVER">NEVER</option>
                  </select>
                </div>
                <div className="flex items-center mt-6">
                  <input type="checkbox" id="is_sequential" className="mr-2 h-4 w-4 text-indigo-600" checked={formData.is_sequential} onChange={(e) => setFormData({ ...formData, is_sequential: e.target.checked })} />
                  <label htmlFor="is_sequential" className="text-gray-700 text-sm font-bold">Sequential Run (ทำทีละ Task)</label>
                </div>
              </div>
              {formData.execution_type === "CRON" && (
                <div className="p-4 bg-gray-50 rounded-lg border">
                  <div className="flex justify-between items-center mb-2">
                    <label className="block text-gray-700 text-sm font-bold">เวลาที่ต้องการให้รัน</label>
                    <div className="flex space-x-2 text-xs">
                      <button type="button" onClick={() => setCronInputType("TIME")} className={`px-2 py-1 rounded ${cronInputType === "TIME" ? "bg-indigo-600 text-white" : "bg-gray-200 text-gray-700"}`}>เวลาปกติ</button>
                      <button type="button" onClick={() => setCronInputType("CUSTOM")} className={`px-2 py-1 rounded ${cronInputType === "CUSTOM" ? "bg-indigo-600 text-white" : "bg-gray-200 text-gray-700"}`}>กำหนด CRON เอง</button>
                    </div>
                  </div>
                  {cronInputType === "TIME" ? (
                    <div>
                      <input type="time" className="w-full border p-2 rounded text-lg font-mono focus:ring-2 focus:ring-indigo-500 outline-none" value={timeValue} onChange={(e) => setTimeValue(e.target.value)} required />
                      <p className="text-xs text-gray-500 mt-2">ระบบจะทำงานทุกวัน ตามเวลาที่กำหนด</p>
                    </div>
                  ) : (
                    <div>
                      <input type="text" placeholder="เช่น 0 8 * * * (ทุกวัน 8 โมง)" className="w-full border p-2 rounded text-lg font-mono focus:ring-2 focus:ring-indigo-500 outline-none" value={formData.cron_expression} onChange={(e) => setFormData({ ...formData, cron_expression: e.target.value })} required />
                    </div>
                  )}
                </div>
              )}
                <div className="flex justify-between items-center pt-4 border-t mt-4">
                    {editingSchedule ? (
                        <button type="button" onClick={handleDeleteSchedule} className="px-4 py-2 text-red-600 bg-red-50 hover:bg-red-100 font-bold rounded transition">
                            🗑️ ลบ Schedule
                        </button>
                    ) : <div />}
                    <div className="space-x-3">
                        <button type="button" onClick={() => setIsModalOpen(false)} className="px-4 py-2 text-gray-600 bg-gray-100 hover:bg-gray-200 rounded font-medium">ยกเลิก</button>
                        <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded font-bold hover:bg-indigo-700">บันทึก</button>
                    </div>
                </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}