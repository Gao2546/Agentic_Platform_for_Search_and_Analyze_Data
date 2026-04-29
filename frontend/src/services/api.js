import axios from 'axios';
const API_URL = 'http://localhost:8000/api/v1'; 

export const projectAPI = {
    getScopes: () => axios.get(`${API_URL}/projects/scopes`),
    createScope: (data) => axios.post(`${API_URL}/projects/scopes`, data),
    updateScope: (id, data) => axios.put(`${API_URL}/projects/scopes/${id}`, data), 
    deleteScope: (id) => axios.delete(`${API_URL}/projects/scopes/${id}`),

    getSchedulesByScope: (scopeId) => axios.get(`${API_URL}/projects/scopes/${scopeId}/schedules`),
    createSchedule: (scopeId, data) => axios.post(`${API_URL}/projects/scopes/${scopeId}/schedules`, data),
    updateSchedule: (id, data) => axios.put(`${API_URL}/projects/schedules/${id}`, data), 
    deleteSchedule: (id) => axios.delete(`${API_URL}/projects/schedules/${id}`),

    getTools: () => axios.get(`${API_URL}/projects/tools`),
    uploadTool: (formData) => axios.post(`${API_URL}/projects/tools/upload`, formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
    updateTool: (id, data) => axios.put(`${API_URL}/projects/tools/${id}`, data),
    deleteTool: (id) => axios.delete(`${API_URL}/projects/tools/${id}`),

    getScheduleInsights: (scheduleId) => axios.get(`${API_URL}/projects/schedules/${scheduleId}/insights`),
    getTasksBySchedule: (scheduleId) => axios.get(`${API_URL}/projects/schedules/${scheduleId}/tasks`),
    createTask: (scheduleId, data) => axios.post(`${API_URL}/projects/schedules/${scheduleId}/tasks`, data),
    updateTaskPosition: (taskId, pos) => axios.put(`${API_URL}/projects/tasks/${taskId}/position`, { ui_position: pos }),
    updateTaskDependency: (taskId, depId) => axios.put(`${API_URL}/projects/tasks/${taskId}/dependency`, { depends_on_task_id: depId }),
    updateTask: (taskId, data) => axios.put(`${API_URL}/projects/tasks/${taskId}`, data),
    deleteTask: (taskId) => axios.delete(`${API_URL}/projects/tasks/${taskId}`),
};

export const dataAPI = {
    searchInsights: (query) => axios.post(`${API_URL}/data/insights/search`, query),
};