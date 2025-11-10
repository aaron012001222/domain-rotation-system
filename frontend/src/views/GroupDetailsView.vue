<!-- frontend/src/views/GroupDetailsView.vue -->
<template>
  <div v-loading="loading">
    <!-- 1. 顶部操作栏 -->
    <div class="page-header">
      <el-page-header @back="goBack">
        <template #content>
          <span class="text-large font-600 mr-3">
            管理域名组: {{ group?.name }}
          </span>
        </template>
      </el-page-header>
      
      <el-button type="success" @click="triggerManualCheck">
        <el-icon><Refresh /></el-icon>
        手动触发检测
      </el-button>
    </div>

    <!-- 2. 中转域名管理卡片 -->
    <el-card class="box-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>中转域名 (Transit Domains)</span>
          <el-button type="primary" @click="openAddDialog('transit')">
            <el-icon><Plus /></el-icon>
            批量添加中转域名
          </el-button>
        </div>
      </template>
      <el-table :data="transitDomains" v-loading="loadingTables" max-height="300px">
        
        <!-- [新] 完整的 URL 列 -->
        <el-table-column prop="full_url" label="中转链接 (访客链接)" show-overflow-tooltip>
          <template #default="scope">
            <el-link :href="scope.row.full_url" type="primary" target="_blank">{{ scope.row.full_url }}</el-link>
          </template>
        </el-table-column>
        
        <!-- [新] 状态列 -->
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
        
        <!-- [新] 删除操作 -->
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

    <!-- 3. 落地域名管理卡片 -->
    <el-card class="box-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>落地域名 (Landing Domains)</span>
          <div>
            <el-button type="danger" @click="handleDeleteSelected">
              <el-icon><Delete /></el-icon>
              批量删除选中
            </el-button>
            <el-button type="primary" @click="openAddDialog('landing')">
              <el-icon><Plus /></el-icon>
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

    <!-- 4. “添加域名”对话框 (已升级) -->
    <el-dialog
      v-model="dialog.visible"
      :title="dialogTitle"
      width="50%"
    >
      <el-alert 
        title="请输入域名，每行一个 (例如: go1.example.com)。" 
        type="info" 
        :closable="false" 
        show-icon 
        style="margin-bottom: 15px;"
      />
      
      <!-- [新] 路径选项 -->
      <el-form-item label="路径类型" v-if="dialog.type === 'transit'">
        <el-radio-group v-model="dialog.path_type">
          <el-radio label="default">默认 (/go)</el-radio>
          <el-radio label="custom">自定义</el-radio>
          <el-radio label="random">随机 (5-8位)</el-radio>
        </el-radio-group>
      </el-form-item>
      
      <!-- [新] 自定义路径输入框 -->
      <el-form-item label="自定义路径" v-if="dialog.type === 'transit' && dialog.path_type === 'custom'">
        <el-input 
          v-model="dialog.custom_path" 
          placeholder="例如: /my-path"
        >
          <template #prepend>/</template>
        </el-input>
      </el-form-item>
      
      <el-input
        v-model="dialog.urls"
        :rows="10"
        type="textarea"
        :placeholder="dialog.type === 'transit' ? 'go1.example.com\ngo2.example.com' : 'http://landing-page.com/1\nhttp://landing-page.com/2'"
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
// [新] 导入图标
import { Plus, Delete, Refresh } from '@element-plus/icons-vue'

// --- 状态定义 ---
const route = useRoute()
const router = useRouter()

const groupId = ref(route.params.id)
const group = ref(null)
const transitDomains = ref([])
const landingDomains = ref([])

const loading = ref(true)
const loadingTables = ref(false)

const dialog = ref({
  visible: false,
  type: 'transit',
  urls: '',
  path_type: 'default', // [新] 默认路径类型
  custom_path: '' // [新] 自定义路径
})

const selectedDomains = ref([])

// --- 计算属性 ---
const dialogTitle = computed(() => {
  return dialog.type === 'transit' ? '批量添加中转域名' : '批量添加落地域名'
})

// --- 函数定义 ---
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

function openAddDialog(type) {
  dialog.value.type = type
  dialog.value.urls = ''
  dialog.value.path_type = 'default' // [新] 重置
  dialog.value.custom_path = '' // [新] 重置
  dialog.value.visible = true
}

// [新] 升级：提交“添加域名”
async function handleAddDomains() {
  if (!dialog.value.urls.trim()) {
    ElMessage.warning('域名列表不能为空')
    return
  }
  
  if (dialog.value.type === 'transit' && dialog.value.path_type === 'custom' && !dialog.value.custom_path.trim()) {
    ElMessage.warning('自定义路径不能为空')
    return
  }

  try {
    loadingTables.value = true
    let response;
    
    if (dialog.value.type === 'transit') {
      response = await api.addTransitDomains(groupId.value, {
        urls: dialog.value.urls,
        path_type: dialog.value.path_type,
        custom_path: dialog.value.custom_path
      })
    } else {
      response = await api.addLandingDomains(groupId.value, dialog.value.urls)
    }
    
    ElMessage.success(response.data.message || '添加成功！')
    dialog.value.visible = false
    await fetchGroupDetails()
  } catch (error) {
    console.error('添加域名失败:', error)
    ElMessage.error(error.response?.data?.message || '添加域名失败')
  } finally {
    loadingTables.value = false
  }
}

function handleSelectionChange(selection) {
  selectedDomains.value = selection
}

async function handleDeleteSelected() {
  if (selectedDomains.value.length === 0) {
    ElMessage.warning('请至少选择一个要删除的落地域名')
    return
  }
  const domainIds = selectedDomains.value.map(domain => domain.id)
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${domainIds.length} 个落地域名吗？`,
      '警告', { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
    )
    await api.deleteLandingDomains(domainIds)
    ElMessage.success('批量删除成功！')
    await fetchGroupDetails()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// [新] 删除单个中转域名
async function handleDeleteTransit(domain) {
  try {
    await ElMessageBox.confirm(
      `确定要删除中转链接 "${domain.full_url}" 吗？`,
      '警告', { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
    )
    await api.deleteTransitDomain(domain.id)
    ElMessage.success('删除成功！')
    await fetchGroupDetails()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

async function triggerManualCheck() {
  try {
    ElMessage.info('已发送检测指令，请稍后...')
    await api.triggerCheck()
    ElMessage.success('检测任务已在后台启动！')
    setTimeout(() => {
      fetchGroupDetails()
    }, 5000) // 5秒后自动刷新
  } catch (error) {
    console.error('触发检测失败:', error)
    ElMessage.error('触发检测失败')
  }
}

function goBack() {
  router.push({ name: 'dashboard' })
}

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
.el-icon {
  margin-right: 5px;
}
/* [新] 为表单项添加一些间距 */
.el-form-item {
  margin-bottom: 10px;
}
</style>