<template>
  <div class="dashboard-layout">
    <!-- 左栏：A + B -->
    <div class="left-column">
      <div class="view-wrapper" style="flex: 192px 0 0;">
        <ViewA class="view-container"/>
      </div>
      <div class="view-wrapper" style="flex: 1; min-height: 0;">
        <ViewB class="view-container"/>
      </div>
    </div>

    <!-- 中栏：C + D + E -->
    <div class="center-column">
      <div class="view-wrapper" style="flex: 365px 0 0;">
        <ViewC class="view-container"/>
      </div>
      <div class="view-wrapper" style="flex: 392px 0 0;">
        <ViewD class="view-container"/>
      </div>
      <div class="view-wrapper" style="flex: 1; min-height: 0;">
        <ViewE class="view-container"/>
      </div>
    </div>

    <!-- 右栏：F -->
    <div class="right-column">
      <ViewF class="view-container"/>
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
</script>

<style scoped>
.dashboard-layout {
  display: flex;
  width: 100%;
  height: 100vh;
  gap: 10px;
  padding: 10px;
  background: #0C0E27;
}

/* 左栏：宽度比例约 22.3% */
.left-column {
  width: 22.3%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

/* 中栏：宽度比例约 45.7% */
.center-column {
  width: 45.7%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

/* 右栏：宽度比例约 31.9% */
.right-column {
  width: 31.9%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.view-wrapper {
  background: #1B1F3A;
  border-radius: 5px;
  box-shadow: 0px 4px 4px rgba(0, 0, 0, 0.25);
  display: flex;
  overflow: hidden;
}

.view-container {
  width: 100%;
  height: 100%;
}
</style>