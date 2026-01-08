<template>
  <div class="dashboard-layout">
    <!-- 左栏 -->
    <div class="left-column">
      <div style="display: flex; flex-direction: column; height: 100%; gap: 10px;">
        <!-- 
          ViewA 区域 (上传与解析)
          修改点 1: 监听 @analysis-complete 事件，接收 ViewA 传出来的解析结果 
        -->
        <div style="flex: 2; min-height: 0;">
          <ViewA 
            style="height: 100%;" 
            @analysis-complete="handleDataReady"
          />
        </div>
        
        <!-- ViewB 区域 (角色配置) -->
        <div style="flex: 8; min-height: 0;">
          <ViewB style="height: 100%;"/>
        </div>
      </div>
    </div>

    <!-- 中栏 -->
    <div class="center-column">
      <div style="flex: 3; min-height: 0; overflow: hidden;">
        <ViewC 
          style="height: 100%;"
          :case-data="caseResult" 
          :raw-pdf-data="imagesResult" 
        />
      </div>

      <!-- ViewD 区域 -->
      <div style="flex: 3; min-height: 0;">
        <ViewD style="height: 100%;" />
      </div>

      <!-- ViewE 区域 (聊天/主交互区) -->
      <div style="flex: 4; min-height: 0;">
        <ViewE style="height: 100%;" />
      </div>
    </div>

    <!-- 右栏 -->
    <div class="right-column">
      <ViewF />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ViewA from './views/ViewA.vue'
import ViewB from './views/ViewB.vue'
import ViewC from './views/ViewC.vue'
import ViewD from './views/ViewD.vue'
import ViewE from './views/ViewE.vue'
import ViewF from './views/ViewF.vue'
import { provide} from 'vue';
const sessionId = `pbl-session-${Date.now()}`   // 只生成一次
provide('sessionId', sessionId)

// --- 修改点 3: 定义响应式变量存储数据 ---
const caseResult = ref(null)   // 存放结构化教案数据
const imagesResult = ref(null) // 存放图片数据

// --- 修改点 4: 处理数据回调 ---
const handleDataReady = (payload) => {
  console.log('父组件收到数据:', payload)
  
  if (payload) {
    caseResult.value = payload.structure
    imagesResult.value = payload.raw_images
  } else {
    // 如果 ViewA 发出的是移除文件的信号
    caseResult.value = null
    imagesResult.value = null
  }
}
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

/* 
  额外建议：
  如果你的项目中没有配置 Tailwind CSS，
  之前代码里的 class="h-1/5" 是不起作用的。
  所以我上面用了 flex: 2; flex: 6; 这样的写法来替代，
  确保布局高度分配正确。
*/
</style>