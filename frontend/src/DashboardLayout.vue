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
          <ViewB 
            style="height: 100%;"
            :theoretical-knowledge="caseResult?.theoretical_knowledge_points || []"
            :case-title="caseResult?.case_title || ''"
          />
        </div>
      </div>
    </div>

    <!-- 中栏 -->
    <div class="center-column">
      <div style="flex: 2.5; min-height: 0; overflow: hidden;">
        <ViewC 
          style="height: 100%;"
          :case-data="caseResult" 
          :raw-pdf-data="imagesResult" 
          @inspect-question="handleInspectQuestion"
        />
      </div>

      <!-- ViewD 和 ViewE 并排区域 -->
      <div style="flex: 3; min-height: 0; display: flex; gap: 10px;">
        <div style="flex: 1; min-width: 0;">
          <ViewD style="height: 100%;" />
        </div>
        <div style="flex: 1; min-width: 0;">
          <ViewE style="height: 100%;" />
        </div>
      </div>
    </div>

    <!-- 右栏 -->
    <div class="right-column">
      <ViewF :active-context="activeContext" />
    </div>
  </div>
</template>

<script setup>
import { ref, provide } from 'vue'
import axios from 'axios'
import ViewA from './views/ViewA.vue'
import ViewB from './views/ViewB.vue'
import ViewC from './views/ViewC.vue'
import ViewD from './views/ViewD.vue'
import ViewE from './views/ViewE.vue'
import ViewF from './views/ViewF.vue'
import { usePBLSocket } from './composables/usePBLSocket.js'

const sessionId = `pbl-session-${Date.now()}`   // 只生成一次

// 初始化 Socket
const { 
  messages, 
  currentTopic, 
  isConnected, 
  isPaused, 
  startDiscussion, 
  togglePause, 
  sendTeacherIntervention,
  activeMessageId,
  rollbackTo,
  activeQuestionInfo,
  selectedNodeLeafId,
  discussionStage,
  interventionSummaries,
  personas,
  fetchPersonas,
  getAgentConfig,
  getAgentColor,
  getAgentName,
  getAgentAvatar,
} = usePBLSocket(sessionId, () => {
    // 自动滚动的逻辑交给组件内部处理或通过事件
});

// 新增：全局选中的主题状态，用于跨视图过滤
const selectedTopic = ref(null);

const updateKnowledge = async (oldName, newName) => {
  if (!currentPdfFilename.value) return;
  try {
    await axios.post('http://127.0.0.1:8000/api/update-knowledge', {
      pdf_filename: currentPdfFilename.value,
      old_name: oldName,
      new_name: newName
    });
    // 更新本地 caseResult
    if (caseResult.value && caseResult.value.theoretical_knowledge_points) {
      caseResult.value.theoretical_knowledge_points = caseResult.value.theoretical_knowledge_points.map(p => p === oldName ? newName : p);
    }
  } catch (error) {
    console.error('Failed to update knowledge:', error);
  }
};

const addKnowledge = async (name) => {
  if (!currentPdfFilename.value) return;
  try {
    await axios.post('http://127.0.0.1:8000/api/add-knowledge', {
      pdf_filename: currentPdfFilename.value,
      knowledge_point: name
    });
    // 更新本地 caseResult
    if (caseResult.value) {
      if (!caseResult.value.theoretical_knowledge_points) {
        caseResult.value.theoretical_knowledge_points = [];
      }
      if (!caseResult.value.theoretical_knowledge_points.includes(name)) {
        caseResult.value.theoretical_knowledge_points.push(name);
      }
    }
  } catch (error) {
    console.error('Failed to add knowledge:', error);
  }
};

const deleteKnowledge = async (name) => {
  if (!currentPdfFilename.value) return;
  try {
    await axios.post('http://127.0.0.1:8000/api/delete-knowledge', {
      pdf_filename: currentPdfFilename.value,
      knowledge_point: name
    });
    // 更新本地 caseResult
    if (caseResult.value && caseResult.value.theoretical_knowledge_points) {
      caseResult.value.theoretical_knowledge_points = caseResult.value.theoretical_knowledge_points.filter(p => p !== name);
    }
  } catch (error) {
    console.error('Failed to delete knowledge:', error);
  }
};

provide('sessionId', sessionId)
provide('pblSocket', {
  messages,
  currentTopic,
  isConnected,
  isPaused,
  startDiscussion,
  togglePause,
  sendTeacherIntervention,
  activeMessageId,
  rollbackTo,
  selectedTopic, // 提供给子组件
  activeQuestionInfo,
  selectedNodeLeafId,
  discussionStage,
  interventionSummaries,
  personas,
  fetchPersonas,
  getAgentConfig,
  getAgentColor,
  getAgentName,
  getAgentAvatar,
  updateKnowledge,
  addKnowledge,
  deleteKnowledge
})

// --- 修改点 3: 定义响应式变量存储数据 ---
const caseResult = ref(null)   // 存放结构化教案数据
const imagesResult = ref(null) // 存放图片数据
const activeContext = ref(null) // 存放当前激活的场景内容（用于 ViewF 仿真）
const currentPdfFilename = ref(null) // 存放当前 PDF 文件名

// --- 修改点 4: 处理数据回调 ---
const handleDataReady = (payload) => {
  console.log('父组件收到数据:', payload)
  
  if (payload) {
    caseResult.value = payload.structure
    imagesResult.value = payload.raw_images
    currentPdfFilename.value = payload.pdf_filename
  } else {
    // 如果 ViewA 发出的是移除文件的信号
    caseResult.value = null
    imagesResult.value = null
    activeContext.value = null
    currentPdfFilename.value = null
  }
}

const handleInspectQuestion = (payload) => {
  console.log('父组件监听到问题查看:', payload)
  // payload 结构: { sceneIndex, questionIndex, data: questionObj }
  
  // 更新活跃问题信息
  activeQuestionInfo.value = { 
    sceneIndex: payload.sceneIndex, 
    questionIndex: payload.questionIndex 
  };

  if (caseResult.value && caseResult.value.scenes[payload.sceneIndex]) {
    const scene = caseResult.value.scenes[payload.sceneIndex]
    activeContext.value = {
      story: scene.story_content,
      question: payload.data.question
    }
  }
}
</script>

<style scoped>
.dashboard-layout {
  display: flex;
  width: 100%;
  height: 100%;
  gap: 10px;
  padding: 10px;
  background: #0C0E27;
}

.left-column {
  width: 32%; /* 稍微加宽一点左边栏以容纳卡片 */
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.center-column {
  width: 38%; /* 相应微调中栏 */
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.right-column {
  width: 25%;
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