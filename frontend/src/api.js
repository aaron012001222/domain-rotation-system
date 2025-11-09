import axios from 'axios'

// 创建一个 Axios 实例
const apiClient = axios.create({
    baseURL: '/api', // 关键：指向我们的 Flask 后端
    timeout: 10000, // 10 秒超时
    headers: {
        'Content-Type': 'application/json',
    }
})

// 导出我们将来要用的所有 API 函数
export default {
    
    // 获取统计数据
    getStats() {
        return apiClient.get('/stats')
    },

    // [新] 获取所有域名
    getAllDomains(page, perPage, status, search) {
        return apiClient.get('/domains', {
            params: {
                page,
                per_page: perPage,
                status,
                search
            }
        })
    },

    // 获取所有组
    getGroups() {
        return apiClient.get('/groups')
    },

    // 获取特定组的详情
    getGroupDetails(groupId) {
        return apiClient.get(`/groups/${groupId}`)
    },

    // 创建新组
    createGroup(name) {
        return apiClient.post('/groups', { name: name })
    },

    // 删除组
    deleteGroup(groupId) {
        return apiClient.delete(`/groups/${groupId}`)
    },

    // 批量添加落地域名
    addLandingDomains(groupId, urls) {
        return apiClient.post(`/groups/${groupId}/landing_domains`, { urls: urls })
    },

    // 批量添加中转域名
    addTransitDomains(groupId, urls) {
        return apiClient.post(`/groups/${groupId}/transit_domains`, { urls: urls })
    },

    // 批量删除落地域名
    deleteLandingDomains(domainIds) {
        return apiClient.delete('/domains', { data: { ids: domainIds } })
    },

    // [新] 删除单个中转域名
    deleteTransitDomain(domainId) {
        return apiClient.delete(`/transit_domains/${domainId}`)
    },

    // 手动触发检测
    triggerCheck() {
        return apiClient.post('/tasks/run_check')
    },

    // [新] 暂停/恢复/获取 调度器状态
    pauseScheduler() {
        return apiClient.post('/scheduler/pause')
    },
    resumeScheduler() {
        return apiClient.post('/scheduler/resume')
    },
    getSchedulerStatus() {
        return apiClient.get('/scheduler/status')
    },

    // [新] 测试跳转
    testRedirect(url) {
        return apiClient.post('/api/test_redirect', { url: url })
    }
}