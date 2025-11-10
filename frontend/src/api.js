// frontend/src/api.js
import axios from 'axios'

const apiClient = axios.create({
    baseURL: '/api', 
    timeout: 10000, 
    headers: {
        'Content-Type': 'application/json',
    }
})

export default {
    getStats() {
        return apiClient.get('/stats');
    },

    getAllDomains(page, perPage, status, search) {
        return apiClient.get('/domains', {
            params: {
                page,
                per_page: perPage,
                status,
                search
            }
        });
    },

    getGroups() {
        return apiClient.get('/groups');
    },

    getGroupDetails(groupId) {
        return apiClient.get(`/groups/${groupId}`);
    },

    createGroup(name) {
        return apiClient.post('/groups', { name: name });
    },

    deleteGroup(groupId) {
        return apiClient.delete(`/groups/${groupId}`);
    },

    addLandingDomains(groupId, urls) {
        return apiClient.post(`/groups/${groupId}/landing_domains`, { urls: urls });
    },

    // --- [新] 更新：添加中转域名 ---
    addTransitDomains(groupId, { urls, path_type, custom_path }) {
        return apiClient.post(`/groups/${groupId}/transit_domains`, { 
            urls, 
            path_type, 
            custom_path 
        });
    },

    // [新] 删除中转域名
    deleteTransitDomain(domainId) {
        return apiClient.delete(`/transit_domains/${domainId}`);
    },

    deleteLandingDomains(domainIds) {
        return apiClient.delete('/domains', { data: { ids: domainIds } });
    },

    triggerCheck() {
        return apiClient.post('/tasks/run_check');
    },

    // --- [新] 调度器 API ---
    getSchedulerStatus() {
        return apiClient.get('/scheduler/status');
    },
    pauseScheduler() {
        return apiClient.post('/scheduler/pause');
    },
    resumeScheduler() {
        return apiClient.post('/scheduler/resume');
    },

    // --- [新] 跳转测试 API ---
    testRedirect(url, path) {
        return apiClient.post('/test_redirect', { url, path });
    }
}