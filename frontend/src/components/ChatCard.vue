<template>
  <div :class="['flex mb-4 w-full', isTeacher ? 'flex-row-reverse' : 'flex-row items-start']">
    <!-- Avatar -->
    <div v-if="isTeacher" 
      class="flex-shrink-0 w-10 h-10 rounded-full overflow-hidden border-2 border-white shadow-sm bg-white ml-3"
    >
      <img :src="avatarUrl" class="w-full h-full object-cover" />
    </div>
    <div v-else
      :class="['flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-white font-bold', avatarColor, 'mr-3']"
    >
      {{ avatarInitial }}
    </div>

    <!-- Content -->
    <div :class="['flex flex-col max-w-[80%]', isTeacher ? 'items-end' : 'items-start']">
      <p class="text-xs text-gray-400 mb-1 px-1">{{ agentNameDisplay }}</p>
      <div 
        class="px-4 py-2.5 rounded-2xl shadow-md border border-white/30 transition-all duration-300"
        :style="bubbleStyle"
      >
        <p class="text-black whitespace-pre-wrap text-[15px] font-medium leading-relaxed">{{ message.text }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  message: {
    type: Object,
    required: true
  },
  agentConfig: {
    type: Object,
    default: () => ({})
  }
});

// =====================
// Teacher 判定
// =====================
const isTeacher = computed(() => {
  return props.message.agent === 'teacher' || props.message.agent === 'teacher_handler';
});

// =====================
// Agent 显示名称
// =====================
const agentNameDisplay = computed(() => {
  if (isTeacher.value) return '指导老师';
  const style = agentStyle.value;
  return style.name || props.agentConfig?.name || props.message.agent;
});

// =====================
// Agent 样式映射（整合 B 版本逻辑）
// =====================
const agentStyles = {
  student_analyst: { name: '分析者 (Analyst)', initial: 'A', color: 'bg-blue-500' },
  student_observer: { name: '观察者 (Observer)', initial: 'O', color: 'bg-green-500' },
  student_skeptic: { name: '怀疑者 (Skeptic)', initial: 'S', color: 'bg-orange-500' },
  teacher: { name: '老师 (Teacher)', initial: 'T', color: 'bg-indigo-500' },
  default: { name: '系统消息', initial: 'SYS', color: 'bg-gray-400' }
};

const getAgentStyle = (agentKey) => {
  return agentStyles[agentKey] || agentStyles.default;
};

const agentStyle = computed(() => {
  if (isTeacher.value) return agentStyles.teacher;
  return getAgentStyle(props.message.agent);
});

// =====================
// 头像显示
// =====================
const avatarUrl = computed(() => {
  if (isTeacher.value) return '/avatar/teacher.png';
  return ''; // 学生用缩写显示，不用图片
});

const avatarInitial = computed(() => {
  if (!isTeacher.value) return agentStyle.value.initial;
  return '';
});

const avatarColor = computed(() => {
  if (!isTeacher.value) return agentStyle.value.color;
  return '';
});

// =====================
// 气泡样式
// =====================
const bubbleStyle = computed(() => {
  if (isTeacher.value) {
    return { 
      backgroundColor: '#E0E7FF',
      boxShadow: '0 4px 15px rgba(224, 231, 255, 0.2)'
    }; 
  }

  // 学生消息气泡颜色
  const config = props.agentConfig || {};
  const bgColor = config.color || config.cardColor || '#E5E7EB';

  return {
    backgroundColor: bgColor,
    boxShadow: `0 4px 12px ${bgColor}66`
  };
});
</script>

<style scoped>
/* 可根据需要在这里增加自定义样式 */
</style>
