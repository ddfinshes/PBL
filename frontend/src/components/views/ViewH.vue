<template>
  <div class="view-container view-h">
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
        <div class="tag-list">
          <span class="tag" v-for="i in 6" :key="i">标签 {{ i }}</span>
        </div>
        <div class="info-text">
          <p>系统运行正常</p>
          <p>所有服务已就绪</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const title = ref('View H - 系统状态')
const loading = ref(true)
const isLoaded = ref(false)

onMounted(() => {
  setTimeout(() => {
    loading.value = false
    isLoaded.value = true
  }, 700)
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

.view-h {
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

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 15px;
}

.tag {
  padding: 4px 10px;
  background: rgba(74, 222, 128, 0.2);
  border: 1px solid rgba(74, 222, 128, 0.3);
  border-radius: 12px;
  font-size: 11px;
  color: #4ade80;
}

.info-text {
  color: #999;
  font-size: 12px;
  line-height: 1.8;
}

.info-text p {
  margin-bottom: 5px;
}
</style>

