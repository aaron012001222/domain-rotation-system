<template>
  <el-row :gutter="20">
    
    <!-- 左侧栏 -->
    <el-col :span="7">
      <!-- 统计卡片 -->
      <el-card shadow="hover" class="stat-card total-card">
        <div class="stat-title">目标域名总数</div>
        <div class="stat-value">{{ stats.total }}</div>
      </el-card>
      <el-card shadow="hover" class="stat-card safe-card">
        <div class="stat-title">安全域名</div>
        <div class="stat-value">{{ stats.safe }}</div>
      </el-card>
      <el-card shadow="hover" class="stat-card unsafe-card">
        <div class="stat-title">不安全域名</div>
        <div class="stat-value">{{ stats.unsafe }}</div>
      </el-card>

      <!-- 快速操作 -->
      <el-card class="box-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>⚡ 快速操作</span>
          </div>
        </template>
        <el-button type="primary" plain class="quick-action-btn" @click="triggerManualCheck">
          检测所有域名
        </el-button>
        <el-button type="success" plain class="quick-action-btn" @click="dialogVisible = true">
          添加目标域名组
        </el-button>
        <el-button type="info" plain class="quick-action-btn" @click="goToAllDomains">
          查看所有域名
        </el-button>
      </el-card>

      <!-- 自动检测设置 -->
      <el-card class="box-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>⚙️ 自动检测设置</span>
            <el-tag v-if="schedulerStatus === 'running'" type="success">运行中</el-tag>
            <el-tag v-else type="info">已暂停</el-tag>
          </div>
        </template>
        <div class="setting-item">
          <span>检测间隔 (分钟):</span>
          <el-input-number v-model="schedulerInterval" :min="1" :max="60" size="small" disabled />
        </div>
        <el-button 
          type="success" 
          plain 
          class="quick-action-btn" 
          @click="handleResume" 
          :disabled="schedulerStatus === 'running'"
        >
          启动自动检测
        </el-button>
        <el-button 
          type="danger" 
          plain 
          class="quick-action-btn" 
          @click="handlePause" 
          :disabled="schedulerStatus === 'paused'"
        >
          停止自动检测
        </el-button>
      </el-card>
    </el-col>

    <!-- 右侧主内容区 -->
    <el-col :span="17">
      <!-- 目标域名管理 (组列表) -->
      <el-card class="box-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>🗂️ 目标域名组管理</span>
            <el-input
              v-model="groupSearch"
              placeholder="搜索组名称..."
              class="search-input"
              clearable
            />
          </div>
        </template>
        
        <el-table :data="filteredGroups" v-loading="loading" style="width: 100%">
          <el-table-column prop="name" label="组名称" width="180" />
          <el-table-column prop="transit_domains_count" label="中转域名数" align="center" />
          <el-table-column prop="landing_domains_count" label="落地域名数" align="center" />
          <el-table-column prop="created_at" label="创建时间" />
          
          <el-table-column label="操作" width="200" align="center">
            <template #default="scope">
              <el-button size="small" type="primary" @click="handleManage(scope.row)">
                管理
              </el-button>
              <el-button size="small" type="danger" @click="handleDeleteGroup(scope.row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 跳转测试 -->
      <el-card class="box-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>🔬 跳转测试</span>
          </div>
        </template>
        <el-input
          v-model="testDomain"
          placeholder="输入一个完整的中转域名 (例如: go1.example.com)"
        >
          <template #append>
            <el-button type="primary" @click="handleRunTest" :loading="testLoading">
              执行测试
            </el-button>
          </template>
        </el-input>
        <div v-if="testResult" class="test-result" :class="testResult.status">
          <strong>测试结果:</strong> {{ testResult.message }}
          <div v-if="testResult.final_url">
            <strong>跳转到:</strong> {{ testResult.final_url }}
          </div>
        </div>
      </el-card>
    </el-col>

  </el-row>

  <!-- 添加新组的对话框 (Modal) -->
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
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api' // 导入我们封装的 API
import { ElMessage, ElMessageBox } from 'element-plus'

// --- 状态定义 ---
const router = useRouter()
const stats = ref({ total: 0, safe: 0, unsafe: 0 })
const groups = ref([])
const loading = ref(true)
const dialogVisible = ref(false)
const newGroupName = ref('')
const groupSearch = ref('')

// 新状态：自动检测
const schedulerStatus = ref('paused')
const schedulerInterval = ref(5)

// 新状态：跳转测试
const testDomain = ref('')
const testLoading = ref(false)
const testResult = ref(null) // { status: 'success'/'error', message: '...' }

// --- 计算属性 ---
const filteredGroups = computed(() => {
  if (!groupSearch.value) {
    return groups.value
  }
  return groups.value.filter(group => 
    group.name.toLowerCase().includes(groupSearch.value.toLowerCase())
  )
})

// --- 核心函数 ---

async function fetchData() {
  loading.value = true
  try {
    // [新] 一次性获取所有数据
    const [statsRes, groupsRes, schedulerRes] = await Promise.all([
      api.getStats(),
      api.getGroups(),
      api.getSchedulerStatus()
    ])
    
    stats.value = statsRes.data
    groups.value = groupsRes.data
    schedulerStatus.value = schedulerRes.data.status
    schedulerInterval.value = schedulerRes.data.interval_minutes

  } catch (error) {
    console.error('获取仪表盘数据失败:', error)
    ElMessage.error('获取仪表盘数据失败')
  } finally {
    loading.value = false
  }
}

async function handleAddGroup() {
  if (!newGroupName.value.trim()) {
    ElMessage.warning('组名称不能为空')
    return
  }
  try {
    await api.createGroup(newGroupName.value)
    ElMessage.success('新组创建成功！')
    dialogVisible.value = false
    newGroupName.value = ''
    // 只刷新组列表
    const groupsRes = await api.getGroups()
    groups.value = groupsRes.data
  } catch (error)
 {
    console.error('创建组失败:', error)
    ElMessage.error(error.response?.data?.error || '创建组失败')
  }
}

function handleManage(group) {
  router.push({ name: 'group-details', params: { id: group.id } })
}

async function handleDeleteGroup(group) {
  try {
    await ElMessageBox.confirm(
      `确定要删除组 "${group.name}" 吗？所有关联的域名都将被删除。`,
      '警告',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await api.deleteGroup(group.id)
    ElMessage.success('组删除成功！')
    // 重新加载所有数据
    fetchData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除组失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// --- 新函数 (匹配新UI) ---

function goToAllDomains() {
  router.push({ name: 'all-domains' })
}

async function triggerManualCheck() {
  try {
    ElMessage.info('已发送检测指令，请稍后...')
    await api.triggerCheck()
    ElMessage.success('检测任务已在后台启动！')
  } catch (error) {
    console.error('触发检测失败:', error)
    ElMessage.error('触发检测失败')
  }
}

async function handlePause() {
  try {
    await api.pauseScheduler()
    ElMessage.success('自动检测已暂停')
    schedulerStatus.value = 'paused'
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

async function handleResume() {
  try {
    await api.resumeScheduler()
    ElMessage.success('自动检测已启动')
    schedulerStatus.value = 'running'
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

async function handleRunTest() {
  if (!testDomain.value.trim()) {
    ElMessage.warning('请输入要测试的中转域名')
    return
  }
  testLoading.value = true
  testResult.value = null
  try {
    // [新] 调用测试 API
    const response = await api.testRedirect(testDomain.value)
    testResult.value = response.data
    
    if (response.data.status === 'success') {
      ElMessage.success('测试成功: 跳转到 ' + response.data.final_url)
    } else {
      ElMessage.error(response.data.message || '测试失败')
    }
  } catch (error) {
    console.error('测试失败:', error)
    testResult.value = { status: 'error', message: '前端请求失败' }
    ElMessage.error('测试请求失败')
  } finally {
    testLoading.value = false
  }
}

// --- Vue 生命周期钩子 ---
onMounted(fetchData)
</script>

<style scoped>
/* 统计卡片 */
.stat-card {
  margin-bottom: 20px;
  text-align: center;
}
.stat-card .stat-title {
  font-size: 16px;
  color: #606266;
  margin-bottom: 10px;
}
.stat-card .stat-value {
  font-size: 30px;
  font-weight: bold;
}
.total-card .stat-value {
  color: #409EFF; /* 蓝色 */
}
.safe-card .stat-value {
  color: #67C23A; /* 绿色 */
}
.unsafe-card .stat-value {
  color: #F56C6C; /* 红色 */
}

.box-card {
  margin-bottom: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.search-input {
  width: 250px;
}
.quick-action-btn {
  width: 100%;
  margin: 5px 0 !important; /* 修复 el-button 奇怪的 margin */
}
.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}
.test-result {
  margin-top: 15px;
  padding: 10px;
  border-radius: 4px;
  font-size: 14px;
}
.test-result.success {
  background-color: #f0f9eb;
  color: #67c23a;
  border: 1px solid #e1f3d8;
}
.test-result.error {
  background-color: #fef0f0;
  color: #f56c6c;
  border: 1px solid #fde2e2;
}
</style>