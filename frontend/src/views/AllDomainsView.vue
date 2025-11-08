<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <span>所有落地域名 ({{ total }})</span>
        <el-input
          v-model="search"
          placeholder="搜索域名..."
          class="search-input"
          @keyup.enter="fetchData"
          clearable
          @clear="fetchData"
        />
      </div>
    </template>

    <el-table :data="domains" v-loading="loading" style="width: 100%">
      <el-table-column prop="url" label="域名 URL" show-overflow-tooltip />
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
      <el-table-column prop="group.name" label="所属组" width="150" />
      <el-table-column prop="last_checked_at" label="最后检测时间" width="200" />
    </el-table>

    <el-pagination
      background
      layout="prev, pager, next, total"
      :total="total"
      :page-size="pageSize"
      v-model:current-page="currentPage"
      @current-change="fetchData"
      class="pagination-bar"
    />
  </el-card>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import api from '../api'
import { ElMessage } from 'element-plus'

const domains = ref([])
const loading = ref(true)
const total = ref(0)
const pageSize = ref(10) // 匹配后端的 per_page 默认值
const currentPage = ref(1)
const search = ref('')

async function fetchData() {
  loading.value = true
  try {
    const response = await api.getAllDomains(
      currentPage.value,
      pageSize.value,
      null, // status filter (null for all)
      search.value
    )
    domains.value = response.data.domains
    total.value = response.data.total
  } catch (error) {
    console.error('获取所有域名失败:', error)
    ElMessage.error('获取所有域名失败')
  } finally {
    loading.value = false
  }
}

// 首次加载
onMounted(fetchData)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.search-input {
  width: 250px;
}
.pagination-bar {
  margin-top: 20px;
}
</style>