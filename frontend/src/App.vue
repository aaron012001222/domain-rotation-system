<template>
  <el-container class="main-layout">
    <el-aside width="200px">
      <div class="sidebar-logo">
        域名轮询系统
      </div>

<el-menu
            active-text-color="#ffd04b"
            background-color="#304156"
            class="el-menu-vertical-demo"
            :default-active="$route.path" text-color="#fff"
            router 
          >
            <el-menu-item index="/"> <span>仪表盘 (组管理)</span>
            </el-menu-item>
            
            <el-menu-item index="/all-domains"> <span>所有域名</span>
            </el-menu-item>
          </el-menu>
    </el-aside>

    <el-container>
      <el-header class="main-header">
        <div>域名轮询防红检测系统</div>
      </el-header>

      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
// 导入
</script>

<style>
/* 我们在这里添加一些全局样式
  注意：这里没有 'scoped' 关键字
*/
html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
}

.main-layout {
  height: 100vh; /* 占满整个视口高度 */
}

.el-aside {
  background-color: #304156;
  color: #fff;
}

.el-menu {
  border-right: none; /* 去掉菜单右侧的白边框 */
}

.sidebar-logo {
  font-size: 20px;
  font-weight: bold;
  text-align: center;
  padding: 20px 0;
  color: #fff;
}

.main-header {
  background-color: #f0f2f5;
  color: #333;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #e6e6e6;
}

.main-content {
  background-color: #f5f7fa;
  padding: 20px;
}
</style>