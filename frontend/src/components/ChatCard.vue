<template>
  <div class="flex items-start space-x-4 p-4 my-2 rounded-lg shadow-sm">
    <!-- Avatar -->
    <div 
      :class="['flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-white font-bold', avatarColor]"
    >
      {{ avatarInitial }}
    </div>

    <!-- Message Content -->
    <div class="flex-1">
      <p class="font-semibold text-gray-800">{{ agentName }}</p>
      <p class="text-gray-600 whitespace-pre-wrap">{{ message.text }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  message: {
    type: Object,
    required: true,
    // validator: (value) => {
    //   return typeof value.agent === 'string' && typeof value.text === 'string';
    // }
  }
});

// Agent to Style Mapping
const agentStyles = {
  student_analyst: {
    name: '分析者 (Analyst)',
    initial: 'A',
    color: 'bg-blue-500',
  },
  student_observer: {
    name: '观察者 (Observer)',
    initial: 'O',
    color: 'bg-green-500',
  },
  student_skeptic: {
    name: '怀疑者 (Skeptic)',
    initial: 'S',
    color: 'bg-orange-500',
  },
  teacher: {
    name: '老师 (Teacher)',
    initial: 'T',
    color: 'bg-indigo-500',
  },
  default: {
    name: '系统消息',
    initial: 'SYS',
    color: 'bg-gray-400',
  }
};

const getAgentStyle = (agentKey) => {
  return agentStyles[agentKey] || agentStyles.default;
};

// Computed Properties for dynamic styling
const agentName = computed(() => getAgentStyle(props.message.agent).name);
const avatarInitial = computed(() => getAgentStyle(props.message.agent).initial);
const avatarColor = computed(() => getAgentStyle(props.message.agent).color);

</script>

