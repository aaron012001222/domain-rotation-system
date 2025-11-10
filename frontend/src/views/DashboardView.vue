<!-- frontend/src/views/DashboardView.vue -->
<template>
  <div>
    <!-- 1. 顶部错误提示 -->
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      @close="error = null"
      show-icon
      style="margin-bottom: 20px;"
    />
    
    <!-- 2. 统计卡片 -->
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-title">目标域名总数</div>
            <div class="stat-value">{{ stats.total }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="card-safe">
          <div class="stat-card">
            <div class="stat-title">安全域名</div>
            <div class="stat-value">{{ stats.safe }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="card-unsafe">
          <div class="stat-card">
            <div class="stat-title">不安全域名</div>
            <div class="stat-value">{{ stats.unsafe }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 3. 主内容区 (左右布局) -->
    <el-row :gutter="20" style="margin-top: 20px;">
      
      <!-- 3a. 左侧操作栏 -->
      <el-col :span="8">
        <!-- 快速操作 -->
        <el-card class="box-card" shadow="never">
          <template #header>
            <span>⚡ 快速操作</span>
          </template>
          <div class="quick-actions">
            <el-button type="primary" plain @click="triggerManualCheck('all')">检测所有域名</el-button>
            <el-button type="success" plain @click="openAddGroupDialog">添加目标域名组</el-button>
            <el-button type="info" plain @click="goToAllDomains">查看所有域名</el-button>
          </div>
        </el-card>
        
        <!-- 自动检测设置 -->
        <el-card class="box-card" shadow="never" style="margin-top: 20px;">
          <template #header>
            <div class="card-header">
              <span>⚙️ 自动检测设置</span>
              <el-tag :type="schedulerStatus === 'running' ? 'success' : 'info'">
                {{ schedulerStatus === 'running' ? '运行中' : '已暂停' }}
              </el-tag>
            </div>
          </template>
          <div class="scheduler-settings">
            <el-input-number v-model="checkInterval" :min="1" :max="60" disabled />
            <span>检测间隔 (分钟)</span>
          </div>
          <el-button 
            type="success" 
            plain 
            @click="resumeScheduler" 
            :disabled="schedulerStatus === 'running'"
            style="width: 100%; margin-top: 10px;"
          >
            启动自动检测
          </el-button>
          <el-button 
            type="danger" 
            plain 
            @click="pauseScheduler" 
            :disabled="schedulerStatus !== 'running'"
            style="width: 100%; margin: 10px 0 0 0;"
          >
            停止自动检测
          </el-button>
        </el-card>
      </el-col>
      
      <!-- 3b. 右侧内容区 -->
      <el-col :span="16">
        <!-- 目标域名组管理 -->
        <el-card class="box-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>🎯 目标域名组管理</span>
              <el-input
                v-model="searchGroup"
                placeholder="搜索组名称..."
                class="search-input"
              />
            </div>
          </template>
          
          <el-table :data="filteredGroups" v-loading="loading.groups" style="width: 100%">
            <el-table-column prop="name" label="组名称" />
            <el-table-column prop="transit_domains_count" label="中转域名数" align="center" />
            <el-table-column prop="landing_domains_count" label="落地域名数" align="center" />
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="scope">
                {{ formatTime(scope.row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" align="center">
              <template #default="scope">
                <el-button size="small" type="primary" @click="handleManage(scope.row)">
                  管理
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
        
        <!-- 跳转测试 -->
        <el-card class="box-card" shadow="never" style="margin-top: 20px;">
          <template #header>
            <span>🔄 跳转测试</span>
          </template>
          <el-input
            v-model="testUrl"
            placeholder="输入一个完整的中转链接 (例如: http://go1.example.com/go)"
            @keyup.enter="handleTestRedirect"
          >
            <template #append>
              <el-button @click="handleTestRedirect" :loading="loading.test">执行测试</el-button>
            </template>
          </el-input>
        </el-card>
      </el-col>

    </el-row>

    <!-- “添加新组”对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="添加新组"
      width="30%"
    >
      <el-input
        v-model="newGroupName"
        placeholder="请输入新组的名称"
        @keyup.enter="handleAddGroup"
      />
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleAddGroup">
            确定
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

// 错误提示
const error = ref(null)

// 统计
const stats = ref({ total: 0, safe: 0, unsafe: 0 })

// 表格
const groups = ref([])
const searchGroup = ref('')
const filteredGroups = computed(() => {
  if (!searchGroup.value) {
    return groups.value
  }
  return groups.value.filter(g => 
    g.name.toLowerCase().includes(searchGroup.value.toLowerCase())
  )
})

// 加载状态
const loading = ref({
  stats: true,
  groups: true,
  scheduler: true,
  test: false
})

// 调度器
const schedulerStatus = ref('unknown') // 'running' or 'paused'
const checkInterval = ref(5)

// 跳转测试
const testUrl = ref('')

// “添加新组”对话框
const dialogVisible = ref(false)
const newGroupName = ref('')

// --- API 调用 ---
async function fetchData() {
  error.value = null // 重置错误
  const promises = [
    api.getStats(),
    api.getGroups(),
    api.getSchedulerStatus()
  ]
  
  try {
    const [statsRes, groupsRes, schedulerRes] = await Promise.all(promises)
    
    stats.value = statsRes.data
    groups.value = groupsRes.data
    schedulerStatus.value = schedulerRes.data.status
    
  } catch (err) {
    console.error("获取仪表盘数据失败:", err)
    error.value = "获取仪表盘数据失败，请检查后端服务是否正在运行。"
  } finally {
    loading.value.stats = false
    loading.value.groups = false
    loading.value.scheduler = false
  }
}

// --- 调度器操作 ---
async function pauseScheduler() {
  try {
    await api.pauseScheduler()
    schedulerStatus.value = 'paused'
    ElMessage.success('自动检测已暂停')
  } catch (err) {
    ElMessage.error('操作失败')
  }
}
async function resumeScheduler() {
  try {
    await api.resumeScheduler()
    schedulerStatus.value = 'running'
    ElMessage.success('自动检测已启动')
  } catch (err) {
    ElMessage.error('操作失败')
  }
}

// --- 快速操作 ---
async function triggerManualCheck(target) {
  try {
    ElMessage.info('已发送检测指令，请稍后...')
    await api.triggerCheck() // 我们的后端 checker.py 会同时检测所有
    ElMessage.success('检测任务已在后台启动！')
    // 5秒后自动刷新数据
    setTimeout(fetchData, 5000) 
  } catch (err) {
    ElMessage.error('触发检测失败')
  }
}
function openAddGroupDialog() {
  newGroupName.value = ''
  dialogVisible.value = true
}
function goToAllDomains() {
  router.push({ name: 'all-domains' })
}

// --- 组管理 ---
async function handleAddGroup() {
  if (!newGroupName.value.trim()) {
    ElMessage.warning('组名称不能为空')
    return
  }
  try {
    await api.createGroup(newGroupName.value)
    ElMessage.success('新组创建成功！')
    dialogVisible.value = false
    await api.getGroups().then(res => { groups.value = res.data }) // 只刷新组列表
  } catch (err) {
    ElMessage.error(err.response?.data?.error || '创建组失败')
  }
}
function handleManage(group) {
  router.push({ name: 'group-details', params: { id: group.id } })
}

// --- 跳转测试 ---
async function handleTestRedirect() {
  if (!testUrl.value.trim()) {
    ElMessage.warning('请输入要测试的中转链接')
    return
  }
  
  // 从完整 URL 中解析出域名和路径
  let urlObj
  try {
    // 自动为没有 http/https 的 URL 添加 http://
    let fullUrl = testUrl.value
    if (!fullUrl.startsWith('http://') && !fullUrl.startsWith('https://')) {
        fullUrl = 'http://' + fullUrl
    }
    urlObj = new URL(fullUrl)
  } catch (err) {
    ElMessage.error('输入的 URL 格式不正确')
    return
  }
  
  const domain = urlObj.hostname
  const path = urlObj.pathname
  
  loading.value.test = true
  try {
    const res = await api.testRedirect(domain, path)
    if (res.data.status === 'success') {
      ElMessageBox.alert(
        `<strong>中转成功!</strong><br/>
         组: ${res.data.group_name}<br/>
         跳转到: ${res.data.landing_url}`,
        '测试成功',
        { dangerouslyUseHTMLString: true, type: 'success' }
      )
    }
  } catch (err) {
    ElMessageBox.alert(
      err.response?.data?.message || '测试失败',
      '测试失败',
      { type: 'error' }
    )
  } finally {
    loading.value.test = false
  }
}

// --- 辅助函数 ---
function formatTime(isoString) {
  if (!isoString) return 'N/A'
  return new Date(isoString).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// --- 生命周期 ---
onMounted(fetchData)
</script>

<style scoped>
.stat-card {
  text-align: center;
}
.stat-title {
  font-size: 16px;
  color: #606266;
  margin-bottom: 10px;
}
.stat-value {
  font-size: 30px;
  font-weight: bold;
}
.card-safe .stat-value {
  color: #67C23A; /* 绿色 */
}
.card-unsafe .stat-value {
  color: #F56C6C; /* 红色 */
}
.box-card {
  margin-top: 0;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.search-input {
  width: 250px;
}
.quick-actions .el-button {
  width: 100%;
  margin: 5px 0 5px 0; /* 修复按钮间距 */
}
.scheduler-settings {
  display: flex;
  align-items: center;
  gap: 10px;
}
.scheduler-settings .el-input-number {
  width: 100px;
}
</style>