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
        <p class="text-black whitespace-pre-wrap text-[15px] font-medium leading-relaxed">
          {{ message.text }}
        </p>

        <!-- 仅对学生 Agent 显示的文本转语音按钮，阻止冒泡到父级点击 -->
        <button
          v-if="!isTeacher"
          type="button"
          class="mt-2 inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium text-gray-600 bg-white/70 hover:bg-white shadow-sm border border-gray-200"
          @click.stop="speakMessage"
        >
          {{ isSpeaking ? '||' : '▶' }} Speak
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';

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

const isSpeaking = ref(false);

/**
 * 根据 agent 名字在可用 voice 列表中稳定选取一个音色
 */
const pickVoiceForAgent = (voices, agentName) => {
  if (!voices || voices.length === 0) return null;

  const name = agentName || 'default';
  // 简单哈希，让同一个 agent 始终映射到同一个下标
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) {
    hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  }

  // 过滤出常见的中英文 voice，更利于教学场景
  const preferred = voices.filter(v => {
    const lang = (v.lang || '').toLowerCase();
    return lang.startsWith('en') || lang.startsWith('zh');
  });

  const base = preferred.length > 0 ? preferred : voices;
  return base[hash % base.length] || null;
};

const speakMessage = () => {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
    console.warn('当前环境不支持语音合成功能');
    return;
  }

  const synth = window.speechSynthesis;

  // 如果当前这条消息正在播放，再次点击则停止播放并恢复按钮为 ▶
  if (isSpeaking.value) {
    if (synth.speaking || synth.pending) {
      synth.cancel();
    }
    isSpeaking.value = false;
    return;
  }

  const text = props.message?.text;
  if (!text) return;

  const startSpeak = () => {
    // 为避免多个消息同时播放，这里先清空队列
    if (synth.speaking || synth.pending) {
      synth.cancel();
    }

    const utter = new SpeechSynthesisUtterance(text);
    const voices = synth.getVoices();
    const voice = pickVoiceForAgent(voices, props.message.agent);
    if (voice) {
      utter.voice = voice;
    }
    // 可以适当调节语速和音量，保证教学环境可听
    utter.rate = 0.8;
    utter.pitch = 1.2;
    utter.volume = 1.0;

    utter.onend = () => {
      isSpeaking.value = false;
    };
    utter.onerror = () => {
      isSpeaking.value = false;
    };

    isSpeaking.value = true;
    synth.speak(utter);
  };

  const existing = synth.getVoices();
  if (existing && existing.length > 0) {
    startSpeak();
  } else {
    // 某些浏览器需要等待 voices 异步加载
    const handleVoicesChanged = () => {
      synth.removeEventListener('voiceschanged', handleVoicesChanged);
      startSpeak();
    };
    synth.addEventListener('voiceschanged', handleVoicesChanged);
  }
};
</script>

<style scoped>
/* 可根据需要在这里增加自定义样式 */
</style>
