<template>
  <div id="app-wrapper" :style="wrapperStyle">
    <DashboardLayout />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import DashboardLayout from './DashboardLayout.vue';

const scale = ref(1);

const updateScale = () => {
  // 定义基准分辨率 (根据设计稿，通常为 1920x1080)
  const baseWidth = 1920;
  const baseHeight = 1080;
  
  const widthScale = window.innerWidth / baseWidth;
  const heightScale = window.innerHeight / baseHeight;
  
  // 选择较小的比例以确保内容完全显示且不失真
  // 如果用户觉得 50% 缩小才正常，说明其原始设计可能是在超大屏幕上或者本身组件偏大
  scale.value = Math.min(widthScale, heightScale);
};

const wrapperStyle = computed(() => {
  return {
    width: '1920px',
    height: '1080px',
    transform: `scale(${scale.value})`,
    transformOrigin: 'top left',
    position: 'absolute',
    left: '50%',
    top: '50%',
    marginLeft: `${-(1920 * scale.value) / 2}px`,
    marginTop: `${-(1080 * scale.value) / 2}px`,
    flexShrink: 0,
    background: '#1a1f3a'
  };
});

onMounted(() => {
  window.addEventListener('resize', updateScale);
  updateScale();
});

onUnmounted(() => {
  window.removeEventListener('resize', updateScale);
});
</script>

<style>
/* Global styles */
html, body {
  margin: 0;
  padding: 0;
  height: 100vh;
  width: 100vw;
  background: #1a1f3a;
  overflow: hidden;
}

#app {
  height: 100vh;
  width: 100vw;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1a1f3a;
}

#app-wrapper {
  overflow: hidden;
  box-shadow: 0 0 20px rgba(0,0,0,0.5);
}

/* 统一字体大小单位，利于自适应 */
body {
  font-size: 14px;
}
</style>