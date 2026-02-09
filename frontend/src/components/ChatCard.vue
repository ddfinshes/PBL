<template>
  <div :class="['flex mb-4 w-full', isTeacher ? 'flex-row-reverse' : 'flex-row items-start']">
    <!-- Avatar -->
    <div :class="['flex-shrink-0 w-10 h-10 rounded-full overflow-hidden border-2 border-white shadow-sm bg-white', isTeacher ? 'ml-3' : 'mr-3']">
      <img :src="avatarUrl" class="w-full h-full object-cover" />
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
  // Metadata passed from ViewF
  agentConfig: {
    type: Object,
    default: () => ({})
  }
});

const isTeacher = computed(() => {
  return props.message.agent === 'teacher' || props.message.agent === 'teacher_handler';
});

const agentNameDisplay = computed(() => {
  if (isTeacher.value) return 'Instructor';
  return props.agentConfig?.name || props.message.agent;
});

const avatarUrl = computed(() => {
  // case_introduction 使用default.png
  if (props.message.agent === 'case_introduction') return '/avatar/default.png';
  if (isTeacher.value) return '/avatar/teacher.png';
  // 确保头像路径正确，增加容错
  const avatarName = props.agentConfig?.avatar || 'avatar1.png';
  return `/avatar/${avatarName}`;
});

const bubbleStyle = computed(() => {
  if (isTeacher.value) {
    return { 
      backgroundColor: '#E0E7FF',
      boxShadow: '0 4px 15px rgba(224, 231, 255, 0.2)'
    }; 
  }
  // 查找颜色：检查 color, cardColor, 以及基础配置中的颜色
  const config = props.agentConfig || {};
  const bgColor = config.color || config.cardColor || '#E5E7EB'; // 默认使用稍微深一点的灰色而不是纯白
  
  return {
    backgroundColor: bgColor,
    boxShadow: `0 4px 12px ${bgColor}66` // 添加带有透明度的动态阴影，增强层次感
  };
});
</script>

<style scoped>
/* 可根据需要在这里增加自定义样式 */
</style>
