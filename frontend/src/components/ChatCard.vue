<template>
  <div :class="['flex mb-4 w-full', isTeacher ? 'flex-row-reverse' : 'flex-row items-start']">
    <!-- Avatar -->
    <div 
      class="flex-shrink-0 w-[45px] h-[45px] rounded-full overflow-hidden border-2 border-white shadow-sm flex items-center justify-center transition-all duration-300 bg-white"
      :class="[isTeacher ? 'ml-3' : 'mr-3']"
      :style="avatarBgStyle"
    >
      <img v-if="avatarUrl" :src="avatarUrl" class="w-full h-full object-cover" />
      <span v-else-if="!isTeacher" class="text-white font-bold text-sm">{{ avatarInitial }}</span>
    </div>

    <!-- Content -->
    <div :class="['flex flex-col max-w-[80%]', isTeacher ? 'items-end' : 'items-start']">
      <p class="text-xs text-gray-400 mb-1 px-1">{{ agentNameDisplay }}</p>
      <div 
        class="px-4 py-2.5 rounded-[20px] shadow-sm border border-white/20"
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
  
  // 1. 优先使用传入的配置名 (来自 personas / AgentCard)
  if (props.agentConfig?.name) return props.agentConfig.name;
  
  // 2. 处理特殊系统节点
  if (props.message.agent === 'case_introduction') return '病例资料';
  
  // 3. 处理已知默认角色
  const style = agentStyles[props.message.agent];
  if (style) return style.name;
  
  // 4. 最后回退到消息中的 agent ID
  return props.message.agent || '未知角色';
});

// =====================
// Agent 样式映射（整合 B 版本逻辑）
// =====================
const agentStyles = {
  student_analyst: { name: '分析者 (Analyst)', initial: 'A', color: 'bg-blue-500' },
  student_observer: { name: '观察者 (Observer)', initial: 'O', color: 'bg-green-500' },
  student_skeptic: { name: '怀疑者 (Skeptic)', initial: 'S', color: 'bg-orange-500' },
  teacher: { name: '老师 (Teacher)', initial: 'T', color: 'bg-indigo-500' },
  default: { name: '系统', initial: 'S', color: 'bg-gray-400' }
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
  if (isTeacher.value) return '/teacher.png';
  if (props.agentConfig?.avatar) {
    const avatar = props.agentConfig.avatar;
    if (avatar.startsWith('http') || avatar.startsWith('/')) return avatar;
    return `/avatar/${avatar}`;
  }
  return '';
});

const avatarInitial = computed(() => {
  if (isTeacher.value) return '';
  // 如果没有头像图片，尝试由 agentConfig 或 style 确定显示的首字母
  const name = props.agentConfig?.name || (agentStyle.value.name !== '系统消息' ? agentStyle.value.name : '') || props.message.agent;
  if (name) return name.charAt(0).toUpperCase();
  return 'S'; 
});

const avatarColor = computed(() => {
  if (!isTeacher.value) return agentStyle.value.color;
  return '';
});

const avatarBgStyle = computed(() => {
  if (isTeacher.value) return { backgroundColor: 'white' };
  if (avatarUrl.value) return {};
  
  // 优先从配置取颜色，否则用 tailwind class (由 avatarColor 提供)
  const configColor = props.agentConfig?.color || props.agentConfig?.cardColor;
  if (configColor) return { backgroundColor: configColor };
  
  return {};
});

// =====================
// 气泡样式
// =====================
const bubbleStyle = computed(() => {
  if (isTeacher.value) {
    return { 
      backgroundColor: '#fff',
      // boxShadow: '0 4px 15px rgba(224, 231, 255, 0.2)'
    }; 
  }

  // 学生消息气泡颜色
  const config = props.agentConfig || {};
  const bgColor = config.color || config.cardColor || '#E5E7EB';

  return {
    backgroundColor: bgColor,
    // boxShadow: `0 4px 12px ${bgColor}66`
  };
});
</script>

<style scoped>
/* 可根据需要在这里增加自定义样式 */
</style>
