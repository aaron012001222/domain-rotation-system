<template>
  <div>
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

    <el-card class="box-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>域名组管理</span>
          <el-button type="primary" @click="dialogVisible = true">
            添加新组
          </el-button>
        </div>
      </template>
      
      <el-table :data="groups" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="组名称" width="180" />
        <el-table-column prop="transit_domains_count" label="中转域名数" align="center" />
        <el-table-column prop="landing_domains_count" label="落地域名数" align="center" />
        <el-table-column prop="created_at" label="创建时间" />
        
        <el-table-column label="操作" width="200" align="center">
          <template #default="scope">
            <el-button size="small" type="primary" @click="handleManage(scope.row)">
              管理
            </el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api' // 导入我们封装的 API
import { ElMessage, ElMessageBox } from 'element-plus' // 导入消息提示框

// --- 响应式状态定义 ---

// 1. 仪表盘统计数据
const stats = ref({ total: 0, safe: 0, unsafe: 0 })

// 2. 域名组列表
const groups = ref([])

// 3. 页面和表格的加载状态
const loading = ref(true)

// 4. “添加新组”对话框的可见性
const dialogVisible = ref(false)

// 5. 新组的名称 (与对话框中的输入框绑定)
const newGroupName = ref('')

// 6. 获取 Vue Router 实例，用于页面跳转
const router = useRouter()

// --- 核心函数 ---

// 1. 获取统计数据
async function fetchStats() {
  try {
    const response = await api.getStats()
    stats.value = response.data
  } catch (error) {
    console.error('获取统计数据失败:', error)
    ElMessage.error('获取统计数据失败')
  }
}

// 2. 获取域名组列表
async function fetchGroups() {
  try {
    loading.value = true // 开始加载，显示表格加载动画
    const response = await api.getGroups()
    groups.value = response.data
  } catch (error) {
    console.error('获取组列表失败:', error)
    ElMessage.error('获取组列表失败')
  } finally {
    loading.value = false // 加载完成
  }
}

// 3. 处理“添加新组”
async function handleAddGroup() {
  if (!newGroupName.value.trim()) {
    ElMessage.warning('组名称不能为空')
    return
  }
  try {
    // 调用 API 创建新组
    await api.createGroup(newGroupName.value)
    ElMessage.success('新组创建成功！')
    dialogVisible.value = false // 关闭对话框
    newGroupName.value = '' // 清空输入框
    fetchGroups() // 重新加载组列表
  } catch (error) {
    console.error('创建组失败:', error)
    ElMessage.error(error.response?.data?.error || '创建组失败')
  }
}

// 4. 处理“管理”按钮点击
function handleManage(group) {
  // 跳转到组详情页面
  router.push({ name: 'group-details', params: { id: group.id } })
}

// 5. 处理“删除”按钮点击
async function handleDelete(group) {
  try {
    // 显示确认对话框
    await ElMessageBox.confirm(
      `确定要删除组 "${group.name}" 吗？所有关联的域名都将被删除。`,
      '警告',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    // 用户点击了“确定”
    await api.deleteGroup(group.id)
    ElMessage.success('组删除成功！')
    fetchGroups() // 重新加载组列表
  } catch (error) {
    // 用户点击了“取消”或 API 报错
    if (error !== 'cancel') {
      console.error('删除组失败:', error)
      ElMessage.error('删除组失败')
    }
  }
}

// --- Vue 生命周期钩子 ---

// onMounted 会在组件加载完成后自动运行
onMounted(() => {
  fetchStats()
  fetchGroups()
})
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
  margin-top: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>