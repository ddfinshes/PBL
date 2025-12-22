<template>
  <div class="view-container view-b">
    <div class="view-header">
      <h3 class="view-title">{{ title }}</h3>
      <div class="status-indicator" :class="{ active: isLoaded }"></div>
    </div>
    <div class="view-content">
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <span>加载中...</span>
      </div>
      <div v-else class="data-placeholder">
        <div class="chart-placeholder">
          <div class="chart-bar" v-for="i in 5" :key="i" :style="{ height: `${20 + i * 10}%` }"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const title = ref('View B - 数据分析')
const loading = ref(true)
const isLoaded = ref(false)

onMounted(() => {
  setTimeout(() => {
    loading.value = false
    isLoaded.value = true
  }, 1200)
})
</script>

<style scoped>
.view-container {
  background: linear-gradient(135deg, #1a1f3a 0%, #16213e 100%);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 15px;
  display: flex;
  flex-direction: column;
  height: 100%;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

.view-b {
  flex: 1;
  min-height: 0;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.view-title {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #666;
  transition: background 0.3s;
}

.status-indicator.active {
  background: #4ade80;
  box-shadow: 0 0 8px rgba(74, 222, 128, 0.5);
}

.view-content {
  flex: 1;
  overflow-y: auto;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 10px;
  color: #999;
}

.spinner {
  width: 30px;
  height: 30px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: #4ade80;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.chart-placeholder {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 100%;
  gap: 8px;
}

.chart-bar {
  flex: 1;
  background: linear-gradient(to top, #4ade80, #22c55e);
  border-radius: 4px 4px 0 0;
  min-height: 20px;
  transition: all 0.3s;
}

.chart-bar:hover {
  opacity: 0.8;
}
</style>

