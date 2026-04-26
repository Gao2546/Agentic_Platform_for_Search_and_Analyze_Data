import axios from 'axios';

// ปรับแก้ URL ให้ตรงกับพอร์ต Backend ของคุณ
const API_URL = 'http://localhost:8000/api/v1'; 

export const projectAPI = {
    // === Scope APIs ===
    getScopes: () => axios.get(`${API_URL}/projects/scopes`),
    createScope: (data) => axios.post(`${API_URL}/projects/scopes`, data),
    updateScope: (id, data) => axios.put(`${API_URL}/projects/scopes/${id}`, data), 
    deleteScope: (id) => axios.delete(`${API_URL}/projects/scopes/${id}`),

    // === Schedule APIs ===
    getSchedulesByScope: (scopeId) => axios.get(`${API_URL}/projects/scopes/${scopeId}/schedules`),
    createSchedule: (scopeId, data) => axios.post(`${API_URL}/projects/scopes/${scopeId}/schedules`, data),
    updateSchedule: (id, data) => axios.put(`${API_URL}/projects/schedules/${id}`, data), 
    deleteSchedule: (id) => axios.delete(`${API_URL}/projects/schedules/${id}`),

    // === Tools & Tasks APIs ===
    getTools: () => axios.get(`${API_URL}/projects/tools`),
    uploadTool: (formData) => axios.post(`${API_URL}/projects/tools/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),getScheduleInsights: (scheduleId) => axios.get(`${API_URL}/projects/schedules/${scheduleId}/insights`),
    getTasksBySchedule: (scheduleId) => axios.get(`${API_URL}/projects/schedules/${scheduleId}/tasks`),
    createTask: (scheduleId, data) => axios.post(`${API_URL}/projects/schedules/${scheduleId}/tasks`, data),
    updateTaskPosition: (taskId, position) => axios.put(`${API_URL}/projects/tasks/${taskId}/position`, { ui_position: position }),
    updateTaskDependency: (taskId, dependsOnId) => axios.put(`${API_URL}/projects/tasks/${taskId}/dependency`, { depends_on_task_id: dependsOnId }),
    updateTask: (taskId, data) => axios.put(`${API_URL}/projects/tasks/${taskId}`, data),
    deleteTask: (taskId) => axios.delete(`${API_URL}/projects/tasks/${taskId}`),
    
};

export const dataAPI = {
    searchInsights: (query) => axios.post(`${API_URL}/data/insights/search`, query),
};