<template>
  <el-container class="layout-container">
    <el-aside :width="sidebarWidth" class="sidebar">
      <div class="logo">
        <h3 v-if="!appStore.sidebarCollapsed">生产计划优化</h3>
        <h3 v-else>优化</h3>
      </div>
      <el-menu
        :default-active="$route.path"
        :collapse="appStore.sidebarCollapsed"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <template #title>工作台</template>
        </el-menu-item>

        <el-menu-item index="/master-data">
          <el-icon><Setting /></el-icon>
          <template #title>基础数据</template>
        </el-menu-item>

        <el-menu-item index="/inventory">
          <el-icon><Box /></el-icon>
          <template #title>库存需求</template>
        </el-menu-item>

        <el-menu-item index="/solve">
          <el-icon><Cpu /></el-icon>
          <template #title>排产求解</template>
        </el-menu-item>

        <el-menu-item index="/solution">
          <el-icon><Document /></el-icon>
          <template #title>方案管理</template>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-icon" @click="appStore.toggleSidebar">
            <Fold v-if="!appStore.sidebarCollapsed" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="$route.meta.title">{{ $route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-tag v-if="solveRunning" type="warning" effect="dark">
            <el-icon class="is-loading"><Loading /></el-icon>
            排产运行中
          </el-tag>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useAppStore } from '@/store/app'
import { isRunning } from '@/api/solve'

const appStore = useAppStore()

const sidebarWidth = computed(() => appStore.sidebarCollapsed ? '64px' : '240px')
const solveRunning = ref(false)

let pollingTimer = null

const checkSolveStatus = async () => {
  try {
    const res = await isRunning()
    solveRunning.value = res.running
  } catch (err) {
    console.error('Failed to check solve status:', err)
  }
}

onMounted(() => {
  checkSolveStatus()
  pollingTimer = setInterval(checkSolveStatus, 5000)
})

onUnmounted(() => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
  }
})
</script>

<style scoped lang="scss">
.layout-container {
  height: 100vh;
}

.sidebar {
  background-color: #304156;
  transition: width 0.3s;
  overflow-x: hidden;
  
  .logo {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    border-bottom: 1px solid #3d4a5a;
    
    h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
      white-space: nowrap;
    }
  }
  
  .el-menu {
    border-right: none;
  }
}

.header {
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  
  .header-left {
    display: flex;
    align-items: center;
    gap: 15px;
    
    .collapse-icon {
      font-size: 20px;
      cursor: pointer;
      transition: color 0.3s;
      
      &:hover {
        color: #409EFF;
      }
    }
  }
  
  .header-right {
    display: flex;
    align-items: center;
    gap: 15px;
  }
}

.main-content {
  background: #f0f2f5;
  overflow-y: auto;
}
</style>
