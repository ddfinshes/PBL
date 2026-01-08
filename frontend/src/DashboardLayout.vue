<template>
  <div class="dashboard-layout">
    <!-- 左栏 -->
    <div class="left-column">
      <!-- 
        1. 推荐用flex-grow来精确分配高度，占比3:3:4。
        2. 推荐写法如下：
      -->
      <div style="display: flex; flex-direction: column; height: 100%; gap: 10px;">
        <div style="flex: 3; min-height: 0;">
          <ViewA style="height: 100%;"/>
        </div>
        <div style="flex: 7; min-height: 0;">
          <ViewB style="height: 100%;"/>
        </div>
      </div>
    </div>

    <!-- 中栏 -->
    <div class="center-column">
      <ViewD class="h-1/5" />
      <ViewE class="h-4/5 min-h-0" />
    </div>

    <!-- 右栏 -->
    <div class="right-column">
      <ViewF />
    </div>
  </div>
</template>

<script setup>
import ViewA from './views/ViewA.vue'
import ViewB from './views/ViewB.vue'
import ViewD from './views/ViewD.vue'
import ViewE from './views/ViewE.vue'
import ViewF from './views/ViewF.vue'
import { provide} from 'vue';
const sessionId = `pbl-session-${Date.now()}`   // 只生成一次
provide('sessionId', sessionId)
</script>

<style scoped>
.dashboard-layout {
  display: flex;
  width: 100%;
  height: 100vh;
  gap: 10px;
  padding: 10px;
  background: #0a0e27;
}

.left-column {
  width: 25%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.center-column {
  width: 45%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.right-column {
  width: 30%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
</style>