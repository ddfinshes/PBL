<template>
  <div class="content">
    <div class="section-container">
      <!-- 上半部分：用户信息 -->
      <div class="upper-section">
        <div class="user-info-section">
          <div class="user-header">
            <h4>用户信息</h4>
            <div class="user-details">
              <span><strong>欢迎: </strong> {{ username }}</span>
              <span class="divider">|</span>
              <span><strong>当前病例: </strong> {{ currentCaseName }}</span>
            </div>
            <div class="user-actions">
              <button class="logout-action-btn" @click="handleLogout">退出登录</button>
            </div>
          </div>
          <button 
            class="back-to-analysis-btn"
            :class="{ disabled: !isPort5000Open }"
            @click="handleBackToAnalysis"
            :disabled="!isPort5000Open"
            :title="isPort5000Open ? '切换到分析模式' : '分析服务未运行。请使用python run_all.py启动后端'"
          >
            返回分析
          </button>
        </div>
      </div>
      
      <!-- 下半部分：对话内容 -->
      <div class="lower-section">
        <h3>询问记录</h3>
        <div class="chat-messages" ref="messageContainer">
          <div
            v-for="(message, index) in messages"
            :key="index"
            :class="['message', getMessageRoleClass(message)]"
          >
            <div class="avatar">
              <img 
                :src="getMessageAvatarSrc(message)"
                :alt="getMessageDisplayName(message)"
                @error="handleAvatarError($event)"
                class="avatar-img"
              />
            </div>
            <div class="message-container">
              <div v-if="shouldShowMessageName(message)" class="message-name">
                {{ getMessageDisplayName(message) }}
              </div>
              <div class="message-content" :style="getMessageContentStyle(message)">
                <div class="message-text">
                  {{ message.content }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch, nextTick } from 'vue';
import axios from "axios";

// 配置axios baseURL
const baseURL = process.env.NODE_ENV === 'development' 
  ? '' // 在开发环境中使用相对路径，通过Vue代理
  : window.location.origin;

// 创建axios实例
const api = axios.create({
  baseURL: baseURL,
  timeout: 10000
});

export default {
  name: "SectionD",
  props: {
    username: {
      type: String,
      required: true
    },
    currentCaseId: {
      type: Number,
      default: 1
    },
    selectedEvaluator: {
      type: Object,
      default: null
    },
    currentAgentName: {
      type: String,
      default: ''
    }
  },
  emits: ['back-to-analysis'],
  setup(props, { emit }) {
    const patientInfo = ref('');
    const mainSuit = ref('');
    const loading = ref(false);
    const error = ref('');
    const messages = ref([]);
    const messageContainer = ref(null);
    const currentCaseName = ref(`case${props.currentCaseId}`);
    const agentsData = ref(null); // 存储case.json中的agents数据

    const normalizeRole = (role) => {
      return String(role || '').trim();
    };

    const getAgentByRole = (role) => {
      const normalizedRole = normalizeRole(role);
      if (!normalizedRole || !agentsData.value) {
        return null;
      }

      // 1. 直接通过 key 匹配
      if (agentsData.value[normalizedRole]) {
        return agentsData.value[normalizedRole];
      }

      // 2. 遍历所有 agent，尝试匹配 name
      const allAgents = Object.values(agentsData.value);
      return allAgents.find(agent => agent?.name === normalizedRole) || null;
    };

    const isCaseIntroductionMessage = (message) => {
      return normalizeRole(message?.role) === 'case_introduction';
    };

    const isAgentMessage = (message) => {
      return !!getAgentByRole(message?.role);
    };

    const getMessageDisplayName = (message) => {
      const agent = getAgentByRole(message?.role);
      if (agent?.name) {
        return agent.name;
      }

      if (isCaseIntroductionMessage(message)) {
        return '病例介绍';
      }

      return normalizeRole(message?.role) || '系统';
    };

    const getMessageAvatarSrc = (message) => {
      if (isCaseIntroductionMessage(message)) {
        return '/avatar/default.png';
      }

      const agent = getAgentByRole(message?.role);
      if (agent?.avatar) {
        return `/avatar/${agent.avatar}`;
      }

      // Fallback: role命名是“中学生1/2/3/4”时，映射到 avatar1/2/3/4
      const normalizedRole = normalizeRole(message?.role);
      const roleNumberMatch = normalizedRole.match(/(\d+)$/);
      if (roleNumberMatch) {
        return `/avatar/avatar${roleNumberMatch[1]}.png`;
      }

      return '/avatar/default.png';
    };

    const handleAvatarError = (event) => {
      const img = event?.target;
      if (!img) {
        return;
      }

      if (!img.dataset.fallbackApplied) {
        img.dataset.fallbackApplied = 'true';
        img.src = '/avatar/default.png';
      }
    };

    const shouldShowMessageName = (message) => {
      return isAgentMessage(message);
    };

    const getMessageContentStyle = (message) => {
      if (isCaseIntroductionMessage(message)) {
        return {
          backgroundColor: '#f0f0f0',
          color: '#333'
        };
      }

      const agent = getAgentByRole(message?.role);
      if (!agent) {
        return {
          backgroundColor: '#fff',
          color: '#333',
          border: '1px solid #ddd'
        };
      }

      return {
        backgroundColor: agent?.cardColor || agent?.color || '#fff',
        color: '#333'
      };
    };

    const getMessageRoleClass = (message) => {
      const isCurrent = isAgentMessage(message) && getMessageDisplayName(message) === props.currentAgentName;
      
      if (isCaseIntroductionMessage(message)) {
        return 'case_introduction';
      }

      if (isAgentMessage(message)) {
        return isCurrent ? 'agent highlighted-agent' : 'agent';
      }

      return 'system';
    };
    
    const resolveActualCaseId = async () => {
      if (!props.username) {
        return props.currentCaseId;
      }

      try {
        const caseResponse = await api.get(`/api/evaluation/current-case?username=${props.username}`);
        const caseData = caseResponse.data;

        if (caseData?.status === 'success' && caseData.case_filename?.startsWith('case')) {
          const parsedCaseId = parseInt(caseData.case_filename.replace('case', ''), 10);
          if (!Number.isNaN(parsedCaseId)) {
            return parsedCaseId;
          }
        }
      } catch (err) {
        console.warn('解析实际case_id失败，使用当前case_id:', err);
      }

      return props.currentCaseId;
    };

    // 加载agents数据
    const loadAgentsData = async (caseIdOverride = null) => {
      try {
        const caseId = caseIdOverride || await resolveActualCaseId();
        console.log(`[loadAgentsData] 正在為 Case ${caseId} 加載 Agents...`);
        
        // 1. 嘗試通過 api 實例 (使用 /api/evaluation 前綴)
        try {
          const response = await api.get(`/api/evaluation/case-agents?case_id=${caseId}`);
          if (response.data && response.data.status === 'success') {
            agentsData.value = response.data.agents;
            console.log('[loadAgentsData] 通過 API 加載成功');
            return;
          }
        } catch (e) {
          console.warn("[loadAgentsData] API 請求 404，嘗試備選路徑...");
        }

        // 2. 備選方案：如果後端端口是 5001 且 proxy 配置有誤，直接請求
        const directUrl = `http://localhost:5001/api/evaluation/case-agents?case_id=${caseId}`;
        const directResponse = await axios.get(directUrl);
        if (directResponse.data && directResponse.data.status === 'success') {
          agentsData.value = directResponse.data.agents;
          console.log('[loadAgentsData] 通過 5001 直接請求成功');
        }
      } catch (error) {
        console.error('[loadAgentsData] 加載失敗:', error.message);
      }
    };
    
    const fetchCaseInfo = async () => {
      loading.value = true;
      error.value = '';
      
      try {
        // 获取患者基本信息
        const caseResponse = await api.get(`/api/evaluation/current-case?username=${props.username}`);
        const caseData = caseResponse.data;
        
        if (caseData.status === 'success') {
          patientInfo.value = caseData.formatted_data;
          // 获取当前案例名称
          if (caseData.case_filename) {
            currentCaseName.value = caseData.case_filename;
          }
        } else {
          error.value = caseData.message || '获取病例信息失败';
        }
        
        // 获取主诉
        const suitResponse = await api.get(`/api/evaluation/get-main-suit?username=${props.username}`);
        const suitData = suitResponse.data;
        
        if (suitData.status === 'success') {
          mainSuit.value = suitData.main_suit;
        } else {
          error.value = suitData.message || '获取主诉失败';
        }
        
      } catch (err) {
        error.value = '网络请求失败: ' + err.message;
      } finally {
        loading.value = false;
      }
    };
    
    onMounted(async () => {
      if (props.username) {
        await fetchCaseInfo();
        // 加载agents数据
        await loadAgentsData();
      }
      // Check port 5000 when component mounts
      await checkPort5000();
      // Periodically check port status (every 5 seconds)
      setInterval(checkPort5000, 5000);
    });
    
    // 监听username变化，重新加载数据
    watch(() => props.username, () => {
      if (props.username) {
        fetchCaseInfo();
      }
    });

    // 监听currentCaseId变化，重新加载数据和agents数据
    watch(() => props.currentCaseId, () => {
      if (props.currentCaseId) {
        fetchCaseInfo();
        loadAgentsData(props.currentCaseId);
      }
    });

    // 加载评估者对话内容
    const loadEvaluatorConversation = async (evaluator) => {
      if (!evaluator) {
        messages.value = [];
        return;
      }

      try {
        // 获取当前案例信息，以确定正确的案例ID
        const caseResponse = await api.get(`/api/evaluation/current-case?username=${props.username}`);
        const caseData = caseResponse.data;
        
        if (caseData.status !== 'success') {
          throw new Error('获取当前案例信息失败');
        }
        
        // 从case_filename中提取案例ID
        let actualCaseId = props.currentCaseId;
        if (caseData.case_filename && caseData.case_filename.startsWith('case')) {
          actualCaseId = parseInt(caseData.case_filename.replace('case', ''));
        }

        // 使用实际case_id重新加载agents，避免role映射错位
        await loadAgentsData(actualCaseId);
        
        const evaluatorId = evaluator.evaluator?.id || evaluator.id || evaluator;
        console.log('准备加载对话，evaluatorId:', evaluatorId, 'actualCaseId:', actualCaseId);
        
        const response = await api.get(`/api/evaluation/case/${actualCaseId}/evaluator/${evaluatorId}`);
        if (response.data && response.data.status === 'success') {
          const data = response.data;
          if (data.conversation) {
            messages.value = data.conversation;
            console.log(`加载评估者 ${evaluatorId} 的对话内容:`, data.conversation);
            console.log('当前agentsData:', agentsData.value);
            // 滚动到底部
            nextTick(() => {
              scrollToBottom();
            });
          }
        } else {
          console.error('获取对话失败');
        }
      } catch (error) {
        console.error(`加载对话失败:`, error);
        messages.value = [];
      }
    };

    // 滚动到底部
    const scrollToBottom = () => {
      if (messageContainer.value) {
        messageContainer.value.scrollTop = messageContainer.value.scrollHeight;
      }
    };

    // 监听选中的评估者变化
    watch(() => props.selectedEvaluator, async (newEvaluator) => {
      if (newEvaluator) {
        // 确保agentsData已加载
        if (!agentsData.value) {
          console.log('agentsData未加载，先加载agents数据');
          await loadAgentsData();
        }
        loadEvaluatorConversation(newEvaluator);
      } else {
        messages.value = [];
      }
    }, { immediate: true });
    
    const formatPatientInfo = (info) => {
      if (!info) return '';
      // 将换行符转换为HTML换行标签
      return info.replace(/\n/g, '<br>');
    };

    const handleBackToAnalysis = () => {
      // Emit event to switch back to analysis mode
      emit('back-to-analysis');
    };

    const handleLogout = () => {
      localStorage.removeItem('evaluation_username');
      localStorage.removeItem('evaluation_user_info');
      window.location.reload(); // 刷新页面回到登录页
    };
    
    // Check if port 5000 (Analysis service) is open
    const isPort5000Open = ref(false);
    
    const checkPort5000 = async () => {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 3000); // 3 second timeout
        
        const response = await fetch('http://localhost:5000/health', {
          signal: controller.signal,
          mode: 'no-cors'  // Allow CORS requests
        });
        
        clearTimeout(timeout);
        // In no-cors mode, response.ok might not work correctly, so check if response is not null
        isPort5000Open.value = response !== null;
      } catch (error) {
        console.log('Port 5000 check failed:', error);
        isPort5000Open.value = false;
      }
    };
    
    return {
      patientInfo,
      mainSuit,
      loading,
      error,
      messages,
      messageContainer,
      currentCaseName,
      agentsData,
      formatPatientInfo,
      fetchCaseInfo,
      handleBackToAnalysis,
      handleLogout,
      isPort5000Open,
      checkPort5000,
      getMessageRoleClass,
      isCaseIntroductionMessage,
      isAgentMessage,
      shouldShowMessageName,
      getMessageDisplayName,
      getMessageAvatarSrc,
      handleAvatarError,
      getMessageContentStyle
    };
  },
};
</script>

<style scoped>
.content {
  padding: clamp(8px, 1vw, 16px);
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.section-container {
  display: flex;
  flex-direction: column;
  gap: clamp(6px, 1vw, 12px);
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.upper-section {
  display: flex;
  gap: clamp(8px, 1.2vw, 16px);
  flex-shrink: 0;
  max-height: 30%;
}

.patient-info-section {
  flex: 1;
  border: clamp(1px, 0.2vw, 2px) solid #e0e0e0;
  border-radius: clamp(4px, 0.8vw, 12px);
  padding: clamp(6px, 1vw, 12px);
  background-color: #fafafa;
  display: flex;
  flex-direction: column;
}

.user-info-section {
  flex: 1;
  border: clamp(1px, 0.2vw, 2px) solid #e0e0e0;
  border-radius: clamp(4px, 0.8vw, 12px);
  padding: clamp(6px, 1vw, 12px);
  background-color: #fafafa;
  display: flex;
  flex-direction: column;
}

.user-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: clamp(8px, 1.2vw, 16px);
  margin-bottom: clamp(4px, 0.8vw, 10px);
}

.user-actions {
  display: flex;
  gap: 8px;
}

.logout-action-btn {
  padding: 2px 8px;
  background-color: #f44336;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: clamp(7px, 0.72vw, 10px);
  transition: background 0.3s;
}

.logout-action-btn:hover {
  background-color: #d32f2f;
}

.user-info-section h4 {
  margin: 0;
  font-size: clamp(8px, 0.8vw, 11px);
  font-weight: 600;
  white-space: nowrap;
}

.user-details {
  display: flex;
  align-items: center;
  gap: clamp(4px, 0.8vw, 10px);
  color: #333;
  font-size: clamp(7px, 0.72vw, 10px);
  line-height: 1.4;
}

.divider {
  color: #ccc;
  font-weight: normal;
}

.back-to-analysis-btn {
  width: 100%;
  padding: clamp(2px, 0.5vw, 5px);
  border: none;
  border-radius: clamp(2px, 0.4vw, 5px);
  background: #2196F3;
  color: white;
  cursor: pointer;
  font-size: clamp(7px, 0.72vw, 10px);
  font-weight: 500;
  transition: all 0.3s ease;
  margin-top: clamp(4px, 0.8vw, 10px);
}

.back-to-analysis-btn:hover:not(:disabled) {
  background: #1976D2;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.3);
}

.back-to-analysis-btn:active:not(:disabled) {
  transform: translateY(0);
}

.back-to-analysis-btn:disabled {
  background: #ccc;
  color: #666;
  cursor: not-allowed;
  opacity: 0.6;
}

.lower-section {
  border: clamp(1px, 0.2vw, 2px) solid #e0e0e0;
  border-radius: clamp(4px, 0.8vw, 12px);
  padding: clamp(8px, 1.2vw, 16px);
  background-color: #fafafa;
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.upper-section h3, .lower-section h3 {
  margin-top: 0;
  margin-bottom: clamp(8px, 1.2vw, 16px);
  color: #333;
  border-bottom: clamp(1px, 0.2vw, 3px) solid #007bff;
  padding-bottom: clamp(3px, 0.6vw, 8px);
  font-size: clamp(10px, 0.96vw, 13px);
}

.case-info {
  display: flex;
  flex-direction: column;
  gap: clamp(10px, 1.5vw, 20px);
  flex: 1;
  min-height: 0;
}

.patient-info, .main-suit {
  background-color: white;
  padding: clamp(8px, 1.2vw, 16px);
  border-radius: clamp(3px, 0.6vw, 8px);
  border: clamp(1px, 0.15vw, 2px) solid #ddd;
  flex-shrink: 0;
}

.patient-info h4, .main-suit h4 {
  margin-top: 0;
  margin-bottom: clamp(4px, 0.8vw, 10px);
  color: #007bff;
  font-size: clamp(8px, 0.8vw, 11px);
  font-weight: 600;
}

.info-content, .suit-content {
  color: #333;
  line-height: 1.4;
  white-space: pre-line;
  font-size: clamp(7px, 0.72vw, 10px);
}

.loading {
  color: #666;
  font-style: italic;
}

.error {
  color: #dc3545;
  font-weight: 500;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: clamp(10px, 1.5vw, 20px);
  min-height: 0;
  scrollbar-width: thin;
  scrollbar-color: #c1c1c1 #f1f1f1;
}

.chat-messages::-webkit-scrollbar {
  width: clamp(4px, 0.5vw, 8px);
}

.chat-messages::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: clamp(2px, 0.3vw, 4px);
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: clamp(2px, 0.3vw, 4px);
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.message {
  display: flex;
  margin-bottom: clamp(8px, 1.5vw, 16px);
  align-items: flex-start;
}

.message-container {
  display: flex;
  flex-direction: column;
  max-width: 75%;
}

.message-name {
  font-size: clamp(8px, 0.8vw, 11px);
  font-weight: 600;
  margin-bottom: 4px;
  color: #555;
  padding-left: 4px;
}

.avatar {
  margin: 0 clamp(6px, 1vw, 12px);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-img {
  width: clamp(28px, 3.5vw, 44px);
  height: clamp(28px, 3.5vw, 44px);
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid #ddd;
}

.avatar-emoji {
  font-size: clamp(11px, 1.6vw, 19px);
}

.avatar-name {
  font-size: clamp(7px, 0.72vw, 10px);
  color: #333;
  white-space: nowrap;
  font-weight: 600;
}

.message-content {
  background: #fff;
  padding: clamp(6px, 1vw, 12px);
  border-radius: clamp(4px, 0.8vw, 12px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  font-size: clamp(8px, 0.88vw, 11px);
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.message.user .message-content {
  background: #fff;
  color: #333;
  border: 1px solid #ddd;
}

.message.case_introduction .message-content {
  background: #f0f0f0;
  color: #333;
}

.message-text {
  user-select: text;
  cursor: text;
  line-height: 1.6;
}

.message-name {
  font-size: clamp(7px, 0.7vw, 9px);
  font-weight: 600;
  margin-bottom: clamp(3px, 0.5vw, 6px);
  opacity: 0.8;
  transition: all 0.3s ease;
}

/* 选中的对话高亮样式 */
.highlighted-agent .message-content {
  transform: scale(1.02);
  transform-origin: left center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border: 2px solid #007bff !important;
  z-index: 5;
}

.highlighted-agent .message-text {
  font-size: clamp(10px, 1.1vw, 14px); /* 放大字体 */
  font-weight: 500;
  color: #000;
}

.highlighted-agent .message-name {
  font-size: clamp(9px, 1vw, 12px);
  color: #007bff;
  opacity: 1;
}

.highlighted-agent .avatar-img {
  border: 3px solid #007bff;
  transform: scale(1.1);
}

@media (max-width: 1200px) {
  .message-content {
    max-width: 80%;
    font-size: clamp(9px, 0.96vw, 13px);
  }
  
  .message:not(.user) .message-content {
    background: #fff;
    color: #333;
  }
  
  .avatar {
    font-size: clamp(13px, 1.76vw, 22px);
  }
}

@media (max-width: 768px) {
  .content {
    padding: clamp(6px, 0.8vw, 12px);
  }
  
  .section-container {
    gap: clamp(4px, 0.8vw, 8px);
  }
  
  .upper-section, .lower-section {
    padding: clamp(6px, 1vw, 12px);
  }
  
  .upper-section {
    flex-direction: column;
    gap: clamp(6px, 1vw, 12px);
  }
  
  .patient-info-section, .user-info-section {
    flex: none;
  }
  
  .message-content {
    max-width: 85%;
    font-size: clamp(8px, 0.88vw, 11px);
  }
  
  .message:not(.user) .message-content {
    background: #fff;
    color: #333;
  }
  
  .avatar {
    font-size: clamp(11px, 1.6vw, 19px);
    margin: 0 clamp(6px, 1vw, 12px);
  }
  
  .message {
    margin-bottom: clamp(8px, 1.5vw, 16px);
  }
}

@media (max-height: 600px) {
  .section-container {
    gap: clamp(3px, 0.6vw, 6px);
  }
  
  .upper-section, .lower-section {
    padding: clamp(4px, 0.8vw, 8px);
  }
  
  .message {
    margin-bottom: clamp(6px, 1.2vw, 12px);
  }
  
  .avatar {
    font-size: clamp(10px, 1.44vw, 16px);
  }
  
  .message-content {
    font-size: clamp(7px, 0.8vw, 10px);
  }
  
  .message:not(.user) .message-content {
    background: #fff;
    color: #333;
  }
}
</style>
