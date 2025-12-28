<template>
  <div class="dashboard-layout">
    <!-- 左栏 -->
    <div class="left-column">
      <ViewA />
      <ViewB />
      <ViewC />
    </div>

    <!-- 中栏 -->
    <div class="center-column">
      <ViewD class="h-1/2" />
      <ViewE class="h-1/2 min-h-0" />
    </div>

    <!-- 右栏 -->
    <div class="right-column">
      <ViewF />
      <ViewG />
      <ViewH />
    </div>
  </div>
</template>

<script setup>
import ViewA from './views/ViewA.vue'
import ViewB from './views/ViewB.vue'
import ViewC from './views/ViewC.vue'
import ViewD from './views/ViewD.vue'
import ViewE from './views/ViewE.vue'
import ViewF from './views/ViewF.vue'
import ViewG from './views/ViewG.vue'
import ViewH from './views/ViewH.vue'
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
  width: 30%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.center-column {
  width: 40%;
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