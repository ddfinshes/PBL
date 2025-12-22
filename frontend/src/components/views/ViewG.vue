<template>
  <div class="view-container view-g">
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
        <div class="activity-list">
          <div class="activity-item" v-for="i in 5" :key="i">
            <div class="activity-icon">●</div>
            <div class="activity-content">
              <div class="activity-title">活动 {{ i }}</div>
              <div class="activity-time">刚刚</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const title = ref('View G - 活动日志')
const loading = ref(true)
const isLoaded = ref(false)

onMounted(() => {
  setTimeout(() => {
    loading.value = false
    isLoaded.value = true
  }, 1100)
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

.view-g {
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

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 4px;
}

.activity-icon {
  color: #4ade80;
  font-size: 8px;
  margin-top: 6px;
}

.activity-content {
  flex: 1;
}

.activity-title {
  font-size: 13px;
  color: #e0e0e0;
  margin-bottom: 4px;
}

.activity-time {
  font-size: 11px;
  color: #666;
}
</style>

