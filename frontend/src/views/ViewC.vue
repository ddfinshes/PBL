<template>
  <div class="p-4 bg-gray-900 h-screen overflow-y-auto">
    <div class="placeholder-view">Agent Modify</div>
    <!-- <h1 class="text-3xl font-bold mb-6 text-white text-center">Agent Modify</h1> -->
    <div class="max-w-3xl mx-auto">
      <div class="flex flex-col gap-6">
        <el-card v-for="(persona, agentId) in agentPersonas" :key="agentId" class="agent-card">
          <template #header>
            <div class="card-header">
              <span>{{ agentNames[agentId] }}</span>
            </div>
          </template>
          <el-form :model="persona" label-position="left">
            <el-form-item value="推理路径">
              <el-radio-group v-model="persona.reasoning_path">
                <el-radio value="线性简化">线性简化</el-radio>
                <el-radio value="多线并行">多线并行</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item value="知识整合">
              <el-radio-group v-model="persona.knowledge_integration">
                <el-radio value="碎片化">碎片化</el-radio>
                <el-radio value="系统化">系统化</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item value="核心偏误">
              <el-checkbox-group v-model="persona.core_biases">
                <el-checkbox value="锚定偏差">锚定偏差</el-checkbox>
                <el-checkbox value="代表性启发">代表性启发</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item value="关键点敏度">
              <el-slider v-model="persona.sensitivity" :min="0" :max="10" :step="1"></el-slider>
            </el-form-item>
            <el-form-item value="知识熟练程度">
              <el-slider v-model="persona.proficiency" :min="0" :max="10" :step="1"></el-slider>
            </el-form-item>
          </el-form>
        </el-card>
      </div>
    </div>
    <div class="mt-8 text-center">
      <el-button type="primary" size="large" @click="syncPersona">保存配置</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';
import { ElMessage } from 'element-plus';

const agentNames = {
  student_analyst: '分析者 (Analyst)',
  student_observer: '观察者 (Observer)',
  student_skeptic: '怀疑者 (Skeptic)',
};

const agentPersonas = ref({
  student_analyst: {
    reasoning_path: '线性简化',
    knowledge_integration: '系统化',
    core_biases: ['锚定偏差'],
    sensitivity: 7,
    proficiency: 8,
  },
  student_observer: {
    reasoning_path: '多线并行',
    knowledge_integration: '碎片化',
    core_biases: [],
    sensitivity: 8,
    proficiency: 6,
  },
  student_skeptic: {
    reasoning_path: '线性简化',
    knowledge_integration: '系统化',
    core_biases: ['代表性启发'],
    sensitivity: 5,
    proficiency: 7,
  },
});

const syncPersona = async () => {
  try {
    const response = await axios.post('http://127.0.0.1:8000/update_personas', agentPersonas.value);
    if (response.status === 200) {
      ElMessage.success('配置保存成功！');
    } else {
      ElMessage.error('配置保存失败。');
    }
  } catch (error) {
    console.error('Error saving personas:', error);
    ElMessage.error('配置保存失败，请检查后端服务是否可用。');
  }
};
</script>

<style scoped>
.placeholder-view { 
  background: #1a1f3a; 
  color: white; 
  display: flex; 
  align-items: center; justify-content: 
  center; width: 100%; 
  height: 4%; 
  border-radius: 8px; }

.agent-card {
  background-color: #2d3748; /* 深灰蓝色背景 */
  border: 1px solid #4a5568;
}

.card-header {
  font-weight: bold;
  color: #ffffff;
  font-size: 1rem;
}

/* 使用 :deep() 来穿透组件样式 */
:deep(.el-form-item__label) {
  color: #e2e8f0; /* 浅灰色标签 */
  font-weight: 400;
}

:deep(.el-radio__label),
:deep(.el-checkbox__label) {
  color: #cbd5e0; /* 更浅的灰色用于选项文本 */
}

:deep(.el-radio__input.is-checked .el-radio__inner),
:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #4299e1; /* Element Plus 蓝色主题色 */
  border-color: #4299e1;
}

:deep(.el-slider__bar) {
  background-color: #4299e1;
}

:deep(.el-card__header) {
  border-bottom: 1px solid #4a5568;
}
</style>