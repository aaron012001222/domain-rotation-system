<template>
  <div v-loading="loading">
    <div class="page-header">
      <el-page-header @back="goBack">
        <template #content>
          <span class="text-large font-600 mr-3">
            管理域名组: {{ group?.name }}
          </span>
        </template>
      </el-page-header>
      
      <el-button type="success" @click="triggerManualCheck">
        手动触发检测
      </el-button>
    </div>

    <el-card class="box-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>中转域名 (Transit Domains)</span>
          <el-button type="primary" @click="openAddDialog('transit')">
            批量添加中转域名
          </el-button>
        </div>
      </template>
      <el-table :data="transitDomains" v-loading="loadingTables" max-height="250px">
        <el-table-column prop="url" label="中转域名 URL" />
        <el-table-column prop="created_at" label="添加时间" />
        <el-table-column label="操作" width="100" align="center">
          <template #default="scope">
            <el-button 
              size="small" 
              type="danger" 
              @click="handleDeleteTransit(scope.row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>

      </el-table>
    </el-card>

    <el-card class="box-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>落地域名 (Landing Domains)</span>
          <div>
            <el-button type="danger" @click="handleDeleteSelected">
              批量删除选中
            </el-button>
            <el-button type="primary" @click="openAddDialog('landing')">
              批量添加落地域名
            </el-button>
          </div>
        </div>
      </template>
      
      <el-table 
        :data="landingDomains" 
        v-loading="loadingTables" 
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="url" label="落地域名 URL" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="scope">
            <el-tag 
              :type="scope.row.status === 'safe' ? 'success' : (scope.row.status === 'unsafe' ? 'danger' : 'info')"
              disable-transitions
            >
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_checked_at" label="最后检测时间" width="200" />
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialog.visible"
      :title="dialogTitle"
      width="50%"
    >
      <el-alert 
        title="请输入域名，每行一个。" 
        type="info" 
        :closable="false" 
        show-icon 
        style="margin-bottom: 15px;"
      />
      <el-input
        v-model="dialog.urls"
        :rows="10"
        type="textarea"
        placeholder="http://example.com&#10;http://another-example.net"
      />
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialog.visible = false">取消</el-button>
          <el-button type="primary" @click="handleAddDomains">
            确定添加
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

// --- 状态定义 ---
const route = useRoute() // 获取当前路由信息（为了拿到 ID）
const router = useRouter() // 获取路由实例（为了“返回”按钮）

const groupId = ref(route.params.id) // 从 URL 中获取组 ID
const group = ref(null) // 存储组的基本信息 { id, name, ... }
const transitDomains = ref([]) // 中转域名列表
const landingDomains = ref([]) // 落地域名列表

const loading = ref(true) // 页面加载状态
const loadingTables = ref(false) // 表格刷新加载状态

// “添加域名”对话框的状态
const dialog = ref({
  visible: false,
  type: 'transit', // 'transit' 或 'landing'
  urls: '', // 绑定到 textarea
})

// 落地域名表格中被选中的行
const selectedDomains = ref([])

// --- 计算属性 ---
// 对话框的标题
const dialogTitle = computed(() => {
  return dialog.value.type === 'transit' ? '批量添加中转域名' : '批量添加落地域名'
})

// --- 函数定义 ---

// 1. 获取所有页面数据
async function fetchGroupDetails() {
  try {
    loading.value = true
    const response = await api.getGroupDetails(groupId.value)
    group.value = response.data.group
    transitDomains.value = response.data.transit_domains
    landingDomains.value = response.data.landing_domains
  } catch (error) {
    console.error('获取组详情失败:', error)
    ElMessage.error('获取组详情失败')
  } finally {
    loading.value = false
  }
}

// 2. 打开“添加域名”对话框
function openAddDialog(type) {
  dialog.value.type = type
  dialog.value.urls = '' // 清空上次输入
  dialog.value.visible = true
}

// 3. 提交“添加域名”
async function handleAddDomains() {
  if (!dialog.value.urls.trim()) {
    ElMessage.warning('域名列表不能为空')
    return
  }
  
  try {
    loadingTables.value = true // 显示表格加载
    if (dialog.value.type === 'transit') {
      await api.addTransitDomains(groupId.value, dialog.value.urls)
      ElMessage.success('中转域名添加成功！')
    } else {
      await api.addLandingDomains(groupId.value, dialog.value.urls)
      ElMessage.success('落地域名添加成功！')
    }
    dialog.value.visible = false // 关闭弹窗
    await fetchGroupDetails() // 重新加载数据
  } catch (error) {
    console.error('添加域名失败:', error)
    ElMessage.error('添加域名失败')
  } finally {
    loadingTables.value = false
  }
}

// 4. 当落地域名表格的选择发生变化时
function handleSelectionChange(selection) {
  // selection 是一个包含了所有被选中行对象的数组
  selectedDomains.value = selection
}

// 5. 批量删除选中的落地域名
async function handleDeleteSelected() {
  if (selectedDomains.value.length === 0) {
    ElMessage.warning('请至少选择一个要删除的域名')
    return
  }

  // 从选中对象中提取 ID 列表
  const domainIds = selectedDomains.value.map(domain => domain.id)
  
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${domainIds.length} 个落地域名吗？`,
      '警告',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    // 用户确认
    await api.deleteLandingDomains(domainIds)
    ElMessage.success('批量删除成功！')
    await fetchGroupDetails() // 重新加载数据
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 6. 手动触发健康检测
async function triggerManualCheck() {
  try {
    ElMessage.info('已发送检测指令，请稍后...')
    await api.triggerCheck()
    ElMessage.success('检测任务已在后台启动！')
    // 我们可以 5 秒后自动刷新一次数据
    setTimeout(fetchGroupDetails, 5000)
  } catch (error) {
    console.error('触发检测失败:', error)
    ElMessage.error('触发检测失败')
  }
}

// 7. 返回仪表盘
function goBack() {
  router.push({ name: 'dashboard' })
}

// [新] 8. 删除单个中转域名
async function handleDeleteTransit(domain) {
  try {
    await ElMessageBox.confirm(
      `确定要删除中转域名 "${domain.url}" 吗？`,
      '警告',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    // 用户确认
    loadingTables.value = true
    await api.deleteTransitDomain(domain.id)
    ElMessage.success('中转域名删除成功！')
    await fetchGroupDetails() // 重新加载数据
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除中转域名失败:', error)
      ElMessage.error('删除失败')
    }
  } finally {
    loadingTables.value = false
  }
}

// --- 生命周期钩子 ---
onMounted(() => {
  fetchGroupDetails()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
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