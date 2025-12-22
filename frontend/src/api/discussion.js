import axios from 'axios'

const API_BASE_URL = '/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 3000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API 请求错误:', error)
    return Promise.reject(error)
  }
)

export const discussionApi = {
  // 健康检查
  healthCheck: () => {
    return apiClient.get('/health')
  },

  // 获取所有 agents
  getAgents: () => {
    return apiClient.get('/agents')
  },

  // 获取指定 agent
  getAgent: (agentName) => {
    return apiClient.get(`/agents/${agentName}`)
  },

  // 更新 agent 配置
  updateAgent: (agentName, profile) => {
    return apiClient.put(`/agents/${agentName}`, profile)
  },

  // 开始讨论（使用更长的超时时间，因为多Agent讨论需要较长时间）
  startDiscussion: (topic, maxTurns = 10) => {
    return apiClient.post('/discussion/start', {
      topic,
      max_turns: maxTurns
    }, {
      timeout: 30000  // 5分钟（300秒）超时，因为多Agent讨论需要较长时间
    })
  },

  // 发送用户消息
  sendUserMessage: (message, topic, conversationHistory) => {
    return apiClient.post('/discussion/user-message', {
      message,
      topic,
      conversation_history: conversationHistory
    })
  },

  // 获取 agent 回复
  getAgentResponse: (agentName, topic, conversationHistory) => {
    return apiClient.post('/discussion/agent-response', {
      agent_name: agentName,
      topic,
      conversation_history: conversationHistory
    })
  },

  // 重置讨论
  resetDiscussion: () => {
    return apiClient.post('/discussion/reset')
  }
}

