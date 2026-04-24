import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
    baseURL: API_BASE_URL,
});

export const projectAPI = {
    createScope: (data) => apiClient.post('/projects/scopes', data),
    getScopes: () => apiClient.get('/projects/scopes'),
    createSchedule: (scopeId, data) => apiClient.post(`/projects/scopes/${scopeId}/schedules`, data),
    triggerSchedule: (scheduleId, payload) => apiClient.post(`/schedules/trigger/${scheduleId}`, payload),
    uploadTool: (formData) => apiClient.post('/projects/tools/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    getTools: () => apiClient.get('/projects/tools'),
    getSchedulesByScope: (scopeId) => apiClient.get(`/projects/scopes/${scopeId}/schedules`),
    getTasksBySchedule: (scheduleId) => apiClient.get(`/projects/schedules/${scheduleId}/tasks`),
    createTask: (scheduleId, data) => apiClient.post(`/projects/schedules/${scheduleId}/tasks`, data),
};

export const dataAPI = {
    searchInsights: (query) => apiClient.post('/data/insights/search', query),
};