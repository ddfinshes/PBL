<template>
  <div class="section-c-container">
    <!-- Agent导航栏 -->
    <div class="agent-navbar">
      <div class="agent-nav-label">选择被评估对象：</div>
      <div class="agent-nav-buttons">
        <button 
          v-for="(agent, agentName) in agents"
          :key="agentName"
          :class="['agent-nav-btn', { 'active': currentAgent === agentName }]"
          @click="selectAgent(agentName)"
          :title="`切换到 ${agent.name}`"
        >
          {{ agent.name }}
        </button>
      </div>
    </div>

    <div class="header-section">
      <div class="title-instruction-row">
        <div class="title-progress-container">
          <h3>评估维度</h3>
        </div>
      
      </div>
      
      <!-- 反馈按钮 -->
      <button 
        class="feedback-btn" 
        @click="openFeedbackModal"
        title="添加反馈意见"
      >
        <span class="feedback-arrow">➤</span>
        <span class="feedback-text">反馈案例（可选）</span>
      </button>
    </div>
    
    <!-- 反馈弹窗 -->
    <div v-if="showFeedbackModal" class="feedback-modal-overlay" @click="closeFeedbackModal">
      <div class="feedback-modal" @click.stop>
        <div class="feedback-modal-header">
          <h4>反馈</h4>
          <button class="close-btn" @click="closeFeedbackModal">×</button>
        </div>
        <div class="feedback-modal-content">
          <textarea
            v-model="feedbackText"
            placeholder="请输入您的反馈意见..."
            class="feedback-textarea"
            rows="6"
          ></textarea>
        </div>
        <div class="feedback-modal-footer">
          <button class="save-btn" @click="saveFeedback">保存</button>
          <button class="cancel-btn" @click="closeFeedbackModal">取消</button>
        </div>
      </div>
    </div>
    
    <div class="evaluation-content">
      
      <div class="dimensions-list">
        <div
          v-for="(dimension, index) in evaluationDimensions"
          :key="index"
          class="dimension-item"
        >
          <div class="dimension-header">
            <span class="dimension-text">{{ dimension.dimension }}</span>
          </div>
          
          <div class="scoring-section">
            <!-- 分数标签行 -->
            <div class="score-labels">
              <span
                v-for="score in 6"
                :key="score - 1"
                class="score-label"
              >
              </span>
            </div>
            
            <!-- Anchors描述行 -->
            <div class="anchors-descriptions">
              <span
                v-for="score in 6"
                :key="score - 1"
                class="anchor-description"
              >
                {{ getAnchorDescription(dimension, score - 1) }}
              </span>
            </div>
            
                         <!-- 评分点行 -->
             <div class="score-dots">
               <span
                 v-for="score in 6"
                 :key="score - 1"
                 :class="[
                   'score-dot',
                   { 
                     'active': getDimensionScore(`${dimension.category}-${dimension.dimension}`) === score - 1,
                     'filled': getDimensionScore(`${dimension.category}-${dimension.dimension}`) >= score - 1
                   }
                 ]"
                 @click="(event) => {
                   console.log('点击评分点:', { score: score - 1, dimension: dimension.dimension });
                   setDimensionScore(`${dimension.category}-${dimension.dimension}`, score - 1);
                 }"
                 :title="`${score - 1}分`"
               >
                 {{ score - 1 === 0 ? 'N' : score - 1 }}
               </span>
             </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch, onMounted } from 'vue'

export default {
  name: "SectionC",
  props: {
    username: {
      type: String,
      default: ''
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
  emits: ['scoring-status-changed', 'agent-selected'],
  setup(props, { emit }) {
    // 评估维度数组
    const evaluationDimensions = ref([])
    
    // 添加响应式变量来触发重新渲染
    const scoreUpdateTrigger = ref(0)

    // Agent相关变量
    const agents = ref({})
    const currentAgent = ref(props.currentAgentName)

    // 反馈相关变量
    const showFeedbackModal = ref(false)
    const feedbackText = ref('')

    // 监听 props.currentAgentName 变化，保持同步
    watch(() => props.currentAgentName, (newVal) => {
      if (newVal && newVal !== currentAgent.value) {
        currentAgent.value = newVal;
        scoreUpdateTrigger.value++;
      }
    });

    // 加载case中的所有agents
    const loadAgents = async () => {
      if (!props.currentCaseId) {
        console.log('loadAgents: 缺少caseId')
        return
      }
      
      try {
        const response = await fetch(`/api/evaluation/case-agents?case_id=${props.currentCaseId}`)
        if (response.ok) {
          const data = await response.json()
          if (data.status === 'success' && data.agents) {
            agents.value = data.agents
            console.log('成功加载agents:', data.agents)
            
            // 优先使用 props 传下来的 agent，其次是第一个
            const agentNames = Object.keys(agents.value)
            if (agentNames.length > 0) {
              if (!props.currentAgentName || !agents.value[props.currentAgentName]) {
                currentAgent.value = agentNames[0]
                emit('agent-selected', currentAgent.value)
              } else {
                currentAgent.value = props.currentAgentName
              }
              console.log('SectionC: 当前选中 agent:', currentAgent.value)
            } else {
              currentAgent.value = ''
            }
          }
        } else {
          console.error('加载agents失败:', response.statusText)
        }
      } catch (error) {
        console.error('加载agents出错:', error)
      }
    }

    // 选择agent
    const selectAgent = (agentName) => {
      currentAgent.value = agentName
      scoreUpdateTrigger.value++
      console.log('SectionC: 切换到agent:', agentName)
      emit('agent-selected', agentName)
    }

    // 获取anchors描述
    const getAnchorDescription = (dimension, score) => {
      if (dimension.anchors && dimension.anchors[score.toString()]) {
        return dimension.anchors[score.toString()]
      }
      return ''
    }

    // 获取维度评分
    const getDimensionScore = (dimensionKey) => {
      // 添加对scoreUpdateTrigger的依赖，确保响应式更新
      scoreUpdateTrigger.value
      
      if (!props.username || !props.currentCaseId || !currentAgent.value) {
        console.log('getDimensionScore: 缺少必要参数', {
          username: props.username,
          currentCaseId: props.currentCaseId,
          currentAgent: currentAgent.value
        })
        return 0
      }
      
      const caseKey = `case${props.currentCaseId}`
      const agentName = currentAgent.value

      // 选中的 evaluator（scene/file）优先使用
      const sceneKey = props.selectedEvaluator?.file || props.selectedEvaluator?.id || null

      // 优先从localStorage缓存读取
      const storageKey = `evaluation_scores_${props.username}`
      const scores = JSON.parse(localStorage.getItem(storageKey) || '{}')

      const caseScores = scores[caseKey] || {}
      let dimensions = {}

      if (sceneKey) {
        const sceneScores = caseScores[sceneKey] || {}
        const agentScores = sceneScores[agentName] || {}
        dimensions = agentScores.dimensions || {}
      } else {
        // 向后兼容，旧结构直接在 case -> agent
        const agentScores = caseScores[agentName] || {}
        dimensions = agentScores.dimensions || {}
      }

      const score = dimensions[dimensionKey] || 0
      return score
    }

    // 设置维度评分
    const setDimensionScore = async (dimensionKey, score) => {
      console.log('setDimensionScore 被调用:', { dimensionKey, score, agentName: currentAgent.value })
      
      if (!props.username || !props.currentCaseId || !currentAgent.value) {
        console.log('setDimensionScore: 缺少必要参数')
        return
      }
      
      const caseKey = `case${props.currentCaseId}`
      const agentName = currentAgent.value
      const sceneKey = props.selectedEvaluator?.file || props.selectedEvaluator?.id || null
      
      try {
        // 实时保存到后端
        // 识别 evaluator id（优先）和 scene（优先使用文件名带 .json）
        const evaluatorId = props.selectedEvaluator?.id || props.selectedEvaluator?.file || null
        const sceneKey = props.selectedEvaluator?.file || props.selectedEvaluator?.id || null

        const bodyPayload = {
          username: props.username,
          case_id: caseKey,
          scene: sceneKey,
          agent_name: agentName,
          dimension_key: dimensionKey,
          score: score
        }
        if (evaluatorId) bodyPayload['evaluator_id'] = evaluatorId

        const response = await fetch('/api/evaluation/save-dimension-score', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(bodyPayload)
        })
        
        if (response.ok) {
          console.log(`评分已保存到后端: ${caseKey} - ${agentName} - ${dimensionKey} = ${score}`)
        } else {
          console.error('保存评分到后端失败:', response.statusText)
        }
      } catch (error) {
        console.error('保存评分到后端出错:', error)
      }
      
      // 同时保存到localStorage作为缓存（支持 case -> scene -> agent -> dimensions）
      const storageKey = `evaluation_scores_${props.username}`
      const scores = JSON.parse(localStorage.getItem(storageKey) || '{}')

      if (!scores[caseKey]) scores[caseKey] = {}

      if (sceneKey) {
        if (!scores[caseKey][sceneKey]) scores[caseKey][sceneKey] = {}
        if (!scores[caseKey][sceneKey][agentName]) scores[caseKey][sceneKey][agentName] = { dimensions: {} }
        scores[caseKey][sceneKey][agentName].dimensions[dimensionKey] = score
      } else {
        if (!scores[caseKey][agentName]) scores[caseKey][agentName] = { dimensions: {} }
        scores[caseKey][agentName].dimensions[dimensionKey] = score
      }

      localStorage.setItem(storageKey, JSON.stringify(scores))
      
      console.log('localStorage已更新:', scores)
      
      // 触发响应式更新
      scoreUpdateTrigger.value++
      
      // 检查当前案例是否所有agent的所有维度都已评分，并通知父组件
      const allScored = await checkAllDimensionsScored()
      // 使用emit通知父组件评分状态变化
      if (typeof emit === 'function') {
        emit('scoring-status-changed', {
          allDimensionsScored: allScored,
          currentCase: props.currentCaseId
        })
        // 通知需要重新检查评分状态
        emit('score-updated')
      }
    }

    // 从JSON文件加载预定义维度
    const loadPredefinedDimensions = async () => {
      try {
        console.log('开始加载预定义维度...')
        const response = await fetch('/api/evaluation/dimensions')
        if (response.ok) {
          const dimensions = await response.json()
          evaluationDimensions.value = dimensions
          console.log('成功加载维度数据:', dimensions)
          console.log('维度数量:', dimensions.length)
        } else {
          console.error('加载预定义维度失败:', response.status, response.statusText)
        }
      } catch (error) {
        console.error('加载预定义维度出错:', error)
      }
    }

    // 保存维度数据到localStorage
    const saveDimensionsToLocalStorage = () => {
      const username = props.username || localStorage.getItem('evaluation_username') || 'default'
      localStorage.setItem(`evaluation_dimensions_${username}`, JSON.stringify(evaluationDimensions.value))
    }

    // 从后端加载用户评分数据
    const loadUserScoresFromBackend = async () => {
      if (!props.username) {
        console.log('loadUserScoresFromBackend: 用户名不存在')
        return
      }
      
      console.log('开始从后端加载用户评分数据，用户名:', props.username)
      
      try {
        // 请求时带上 case_id 与可选 scene 参数以获取更精确的数据
        const caseKey = `case${props.currentCaseId}`
        const sceneKey = props.selectedEvaluator?.file || props.selectedEvaluator?.id || null
        let url = `/api/evaluation/get-user-scores?username=${props.username}&case_id=${caseKey}`
        if (sceneKey) url += `&scene=${sceneKey}`
        const response = await fetch(url)
        console.log('后端响应状态:', response.status, response.statusText)
        
        if (response.ok) {
          const data = await response.json()
          console.log('后端返回的原始数据:', data)
          
            if (data.status === 'success' && data.scores) {
            // 将后端数据同步到localStorage（保留其他 case 的数据）
            const storageKey = `evaluation_scores_${props.username}`
            const existing = JSON.parse(localStorage.getItem(storageKey) || '{}')
            // data.scores 可能是整个 case 层级或单个 scene 层级
            if (!existing[caseKey]) existing[caseKey] = {}
            // 如果返回的是 scene 层级（当 scene 查询时），直接写入 case[scene] = data.scores
            if (sceneKey) {
              existing[caseKey][sceneKey] = data.scores
            } else {
              // 返回整个 case 层级，直接覆盖
              existing[caseKey] = data.scores
            }
            localStorage.setItem(storageKey, JSON.stringify(existing))
            console.log('从后端加载用户评分数据成功，已合并到localStorage:', existing[caseKey])

            // 强制触发重新渲染
            scoreUpdateTrigger.value++
          } else {
            console.log('后端返回的数据格式不正确或为空:', data)
          }
        } else {
          console.error('从后端加载用户评分数据失败:', response.statusText)
        }
      } catch (error) {
        console.error('从后端加载用户评分数据出错:', error)
      }
    }

    // 从localStorage加载维度数据
    const loadDimensionsFromLocalStorage = async () => {
      const username = props.username || localStorage.getItem('evaluation_username') || 'default'
      console.log('加载维度数据，用户名:', username)
      const saved = localStorage.getItem(`evaluation_dimensions_${username}`)
      if (saved) {
        const savedDimensions = JSON.parse(saved)
        evaluationDimensions.value = savedDimensions
        console.log('从localStorage加载维度数据:', savedDimensions)
        console.log('维度数量:', savedDimensions.length)
      } else {
        console.log('localStorage中没有保存的维度数据，加载预定义维度')
        // 如果没有保存的数据，加载预定义维度
        await loadPredefinedDimensions()
      }
    }

    // 清空所有数据的方法（供App.vue调用）
    const clearAll = () => {
      evaluationDimensions.value.splice(0)
      
      // 清除localStorage中的数据
      const username = props.username || localStorage.getItem('evaluation_username') || 'default'
      localStorage.removeItem(`evaluation_dimensions_${username}`)
    }

    // 检查当前案例的所有agent是否所有维度都已评分
    const checkAllDimensionsScored = async () => {
      if (!props.username || !props.currentCaseId) return false
      
      try {
        const storageKey = `evaluation_scores_${props.username}`
        const scores = JSON.parse(localStorage.getItem(storageKey) || '{}')
        
        const caseKey = `case${props.currentCaseId}`
        const caseScores = scores[caseKey] || {}
        const sceneKey = props.selectedEvaluator?.id || props.selectedEvaluator?.file || null

        // 检查每个agent的所有维度是否都有评分且不为0（支持 case->scene->agent 结构）
        for (const agentName of Object.keys(agents.value)) {
          let agentScores = {}
          if (sceneKey) {
            const sceneScores = caseScores[sceneKey] || {}
            agentScores = sceneScores[agentName] || {}
          } else {
            agentScores = caseScores[agentName] || {}
          }

          // 检查该agent的所有维度
          for (const dimension of evaluationDimensions.value) {
            const dimensionKey = `${dimension.category}-${dimension.dimension}`
            const score = agentScores.dimensions?.[dimensionKey] || 0
            if (score === 0) {
              return false
            }
          }
        }
        
        return true
      } catch (error) {
        console.error('检查评分状态失败:', error)
        return false
      }
    }

    // 加载反馈意见
    const loadFeedback = () => {
      if (!props.username || !props.currentCaseId || !currentAgent.value) return

      const storageKey = `evaluation_feedback_${props.username}`
      const feedbacks = JSON.parse(localStorage.getItem(storageKey) || '{}')

      const caseKey = `case${props.currentCaseId}`
      const agentName = currentAgent.value
      const sceneKey = props.selectedEvaluator?.id || props.selectedEvaluator?.file || null

      let feedback = ''
      if (sceneKey) {
        feedback = feedbacks[caseKey]?.[sceneKey]?.[agentName] || ''
      } else {
        feedback = feedbacks[caseKey]?.[agentName] || ''
      }
      feedbackText.value = feedback
    }

    // 打开反馈弹窗
    const openFeedbackModal = () => {
      loadFeedback() // 加载当前反馈
      showFeedbackModal.value = true
    }

    // 实时保存反馈到localStorage
    const saveFeedbackToLocalStorage = () => {
      if (!props.username || !props.currentCaseId || !currentAgent.value) return
      
      const caseKey = `case${props.currentCaseId}`
      const agentName = currentAgent.value
      
      const storageKey = `evaluation_feedback_${props.username}`
      const feedbacks = JSON.parse(localStorage.getItem(storageKey) || '{}')

      // 初始化数据结构
      if (!feedbacks[caseKey]) feedbacks[caseKey] = {}
      const sceneKey = props.selectedEvaluator?.id || props.selectedEvaluator?.file || null

      if (sceneKey) {
        if (!feedbacks[caseKey][sceneKey]) feedbacks[caseKey][sceneKey] = {}
        feedbacks[caseKey][sceneKey][agentName] = feedbackText.value
      } else {
        feedbacks[caseKey][agentName] = feedbackText.value
      }

      // 保存到localStorage
      localStorage.setItem(storageKey, JSON.stringify(feedbacks))
      
      console.log('反馈已实时保存到localStorage:', {
        case: caseKey,
        agent: agentName,
        feedback: feedbackText.value
      })
    }

    // 保存反馈意见
    const saveFeedback = async () => {
      if (!props.username || !props.currentCaseId || !currentAgent.value) return
      
      const caseKey = `case${props.currentCaseId}`
      const agentName = currentAgent.value
      
      // 先保存到localStorage
      saveFeedbackToLocalStorage()
      
      try {
        // 发送反馈到后端
        const response = await fetch('/api/evaluation/feedback', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            username: props.username,
            case_id: props.currentCaseId,
            agent_name: agentName,
            feedback: feedbackText.value
          })
        })
        
        if (response.ok) {
          console.log('反馈已保存到后端:', {
            case: caseKey,
            agent: agentName,
            feedback: feedbackText.value
          })
        } else {
          console.error('保存反馈失败:', response.statusText)
        }
      } catch (error) {
        console.error('保存反馈出错:', error)
      }
      
      showFeedbackModal.value = false
    }

    // 关闭反馈弹窗
    const closeFeedbackModal = () => {
      showFeedbackModal.value = false
      // 不重置feedbackText，保持用户输入的内容
    }

    // 监听相关props变化
    watch([() => props.username, () => props.currentCaseId], async () => {
      console.log('SectionC props变化:', {
        username: props.username,
        currentCaseId: props.currentCaseId
      })
      
      // 当用户、案例改变时，重新加载agents
      if (props.username && props.currentCaseId) {
        await loadAgents() // 等待agents加载完成，这样currentAgent就被设置了
        // 首先从后端加载用户评分数据
        await loadUserScoresFromBackend()
        // 然后加载维度数据
        await loadDimensionsFromLocalStorage()
        loadFeedback() // 加载对应的反馈（此时currentAgent已设置）
        
        // 延迟触发重新渲染，确保数据已加载
        setTimeout(() => {
          scoreUpdateTrigger.value++
        }, 100)
      }
    }, { immediate: true })

    // 当选中的 evaluator (scene/file) 改变时，重新加载该 scene 的评分和反馈
    watch(() => props.selectedEvaluator, async (newVal) => {
      console.log('SectionC: selectedEvaluator 变化:', newVal)
      // 重新从后端加载 scene 级别评分
      await loadUserScoresFromBackend()
      // 重新加载反馈
      loadFeedback()
      // 触发视图更新
      scoreUpdateTrigger.value++
    })

    // 监听反馈文本变化，实时保存到localStorage
    let feedbackSaveTimeout = null
    watch(feedbackText, () => {
      if (props.username && props.currentCaseId && props.selectedEvaluator) {
        // 使用防抖，避免频繁保存
        if (feedbackSaveTimeout) {
          clearTimeout(feedbackSaveTimeout)
        }
        feedbackSaveTimeout = setTimeout(() => {
          saveFeedbackToLocalStorage()
        }, 500) // 500ms防抖
      }
    })

    // 组件挂载时加载维度数据和agents
    onMounted(async () => {
      console.log('SectionC 组件挂载，用户名:', props.username, '当前caseId:', props.currentCaseId)
      if (props.username && props.currentCaseId) {
        // 加载agents - 等待完成，这样currentAgent就被设置了
        await loadAgents()
        // 首先从后端加载用户评分数据
        await loadUserScoresFromBackend()
        // 然后加载维度数据
        await loadDimensionsFromLocalStorage()
        loadFeedback() // 加载反馈（此时currentAgent已设置）
        
        // 延迟触发重新渲染，确保数据已加载
        setTimeout(() => {
          scoreUpdateTrigger.value++
        }, 100)
      }
    })

    // 获取评分进度
    const getScoringProgress = () => {
      // 添加对scoreUpdateTrigger的依赖，确保响应式更新
      scoreUpdateTrigger.value
      
      if (!props.username || !props.currentCaseId || !currentAgent.value) {
        return '0/0'
      }
      
      const caseKey = `case${props.currentCaseId}`
      const agentName = currentAgent.value

      // 从localStorage获取评分数据
      const storageKey = `evaluation_scores_${props.username}`
      const scores = JSON.parse(localStorage.getItem(storageKey) || '{}')

      const caseScores = scores[caseKey] || {}
      const sceneKey = props.selectedEvaluator?.id || props.selectedEvaluator?.file || null
      let dimensions = {}

      if (sceneKey) {
        const sceneScores = caseScores[sceneKey] || {}
        const agentScores = sceneScores[agentName] || {}
        dimensions = agentScores.dimensions || {}
      } else {
        const agentScores = caseScores[agentName] || {}
        dimensions = agentScores.dimensions || {}
      }
      
      // 计算已评分的维度数量（包含所有维度）
      let scoredCount = 0
      let totalCount = 0
      
      evaluationDimensions.value.forEach(dimension => {
        totalCount++
        const dimensionKey = `${dimension.category}-${dimension.dimension}`
        const score = dimensions[dimensionKey] || 0
        if (score > 0) {
          scoredCount++
        }
      })
      
      return `${scoredCount}/${totalCount}`
    }

    return {
      evaluationDimensions,
      scoreUpdateTrigger,
      agents,
      currentAgent,
      selectAgent,
      loadAgents,
      getAnchorDescription,
      getDimensionScore,
      setDimensionScore,
      clearAll,
      saveDimensionsToLocalStorage,
      loadDimensionsFromLocalStorage,
      loadUserScoresFromBackend,
      checkAllDimensionsScored,
      showFeedbackModal,
      feedbackText,
      saveFeedback,
      saveFeedbackToLocalStorage,
      closeFeedbackModal,
      loadFeedback,
      openFeedbackModal,
      getScoringProgress
    }
  }
};
</script>

<style scoped>
.section-c-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  overflow: hidden;
  min-height: 0;
  padding: 16px;
  background-color: #f0f9eb; /* 柔和的绿色背景 */
}

/* Agent导航栏样式 */
.agent-navbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.agent-nav-label {
  color: white;
  font-weight: 600;
  font-size: clamp(12px, 1.2vw, 14px);
  white-space: nowrap;
}

.agent-nav-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  flex: 1;
}

.agent-nav-btn {
  padding: 6px 12px;
  background-color: rgba(255, 255, 255, 0.2);
  color: white;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-radius: 6px;
  font-size: clamp(11px, 1.1vw, 13px);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.agent-nav-btn:hover {
  background-color: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.6);
  transform: translateY(-1px);
}

.agent-nav-btn.active {
  background-color: white;
  color: #667eea;
  border-color: white;
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.header-section {
  display: flex;
  flex-direction: column;
  margin-bottom: 2px;
  gap: 8px;
}

.title-instruction-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
}

.title-progress-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-indicator {
  background: linear-gradient(135deg, #4caf50, #66bb6a);
  color: white;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: clamp(10px, 0.96vw, 12px);
  font-weight: bold;
  box-shadow: 0 2px 4px rgba(76, 175, 80, 0.3);
  min-width: 40px;
  text-align: center;
}

.progress-text {
  font-weight: 600;
}

.header-section h3 {
  margin-top: 0;
  margin-bottom: 0;
  color: #333;
  border-bottom: 2px solid #007bff;
  padding-bottom: 8px;
  font-size: clamp(10px, 0.96vw, 12px); /* 缩小20%: 12px -> 10px, 1.2vw -> 0.96vw, 16px -> 13px */
}

.evaluation-content {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.dimensions-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
}

.dimension-item {
  background: white;
  border-radius: 6px;
  padding: 12px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  border-left: 3px solid #007bff;
}

.dimension-header {
  margin-bottom: 8px;
}

.dimension-text {
  font-size: clamp(11px, 1.12vw, 14px); /* 缩小20%: 14px -> 11px, 1.4vw -> 1.12vw, 18px -> 14px */
  font-weight: 600;
  color: #333;
  line-height: 1.4;
}

.scoring-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.score-labels {
  display: flex;
  justify-content: space-between;
  padding: 0 10px;
}

.score-label {
  font-size: clamp(10px, 0.96vw, 12px); /* 缩小20%: 12px -> 10px, 1.2vw -> 0.96vw, 15px -> 12px */
  color: #666;
  font-weight: 500;
  flex: 1;
  text-align: center;
}

.anchors-descriptions {
  display: flex;
  justify-content: space-between;
  padding: 0 8px;
  min-height: 28px;
}

.anchor-description {
  font-size: clamp(9px, 0.88vw, 11px); /* 缩小20%: 11px -> 9px, 1.1vw -> 0.88vw, 14px -> 11px */
  color: #888;
  flex: 1;
  text-align: center;
  line-height: 1.2;
  padding: 0 2px;
}

.score-dots {
  display: flex;
  justify-content: space-between;
  gap: 6px;
  padding: 0 8px;
}

.score-dot {
  width: clamp(26px, 2.56vw, 32px); /* 缩小20%: 32px -> 26px, 3.2vw -> 2.56vw, 40px -> 32px */
  height: clamp(26px, 2.56vw, 32px); /* 缩小20%: 32px -> 26px, 3.2vw -> 2.56vw, 40px -> 32px */
  border-radius: 50%;
  border: 2px solid #ddd;
  background-color: white;
  color: #666;
  font-size: clamp(10px, 0.96vw, 12px); /* 缩小20%: 12px -> 10px, 1.2vw -> 0.96vw, 15px -> 12px */
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
  flex: 1;
  max-width: clamp(26px, 2.56vw, 32px); /* 缩小20%: 32px -> 26px, 3.2vw -> 2.56vw, 40px -> 32px */
  position: relative;
  z-index: 10;
}

.score-dot:hover {
  border-color: #007bff;
  transform: scale(1.1);
}

.score-dot.active {
  background-color: #007bff;
  color: white;
  border-color: #007bff;
}

.score-dot.filled:not(.active) {
  background-color: #e3f2fd;
  border-color: #2196f3;
  color: #1976d2;
}

/* 新增的提示框样式 */
.instruction-box {
  display: flex;
  align-items: center;
  background-color: #e8f5e9; /* 浅绿色背景 */
  border: 1px solid #a5d6a7; /* 浅绿色边框 */
  border-radius: 6px;
  padding: 8px 12px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  flex-shrink: 0;
}

.instruction-icon {
  font-size: clamp(14px, 1.44vw, 18px); /* 缩小20%: 18px -> 14px, 1.8vw -> 1.44vw, 22px -> 18px */
  margin-right: 8px;
  color: #4caf50; /* 绿色图标 */
}

.instruction-text {
  font-size: clamp(8px, 0.84vw, 11px);
  color: #333;
  font-weight: 900;
  white-space: nowrap;
}

/* 反馈按钮样式 */
.feedback-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
  color: white;
  border: 2px solid #e55a2b;
  border-radius: 6px;
  padding: 6px 16px;
  font-size: clamp(9px, 0.9vw, 11px);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 6px rgba(255, 107, 53, 0.3);
  position: relative;
  overflow: hidden;
  width: 100%;
}

.feedback-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s;
}

.feedback-btn:hover::before {
  left: 100%;
}

.feedback-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 3px 10px rgba(255, 107, 53, 0.4);
  border-color: #ff8c42;
}

.feedback-arrow {
  font-size: clamp(12px, 1.2vw, 14px);
  font-weight: bold;
  animation: bounce 1.5s infinite;
  flex-shrink: 0;
}

.feedback-text {
  white-space: nowrap;
}

/* 动画效果 */
@keyframes bounce {
  0%, 20%, 50%, 80%, 100% {
    transform: translateX(0);
  }
  40% {
    transform: translateX(3px);
  }
  60% {
    transform: translateX(1px);
  }
}

/* 反馈弹窗样式 */
.feedback-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.feedback-modal {
  background-color: white;
  border-radius: 10px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
  width: 90%;
  max-width: 500px;
  max-height: 80%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.feedback-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #eee;
  background-color: #f8f9fa;
}

.feedback-modal-header h4 {
  margin: 0;
  font-size: clamp(14px, 1.44vw, 18px);
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: clamp(20px, 2vw, 24px);
  color: #888;
  cursor: pointer;
  transition: color 0.2s ease;
}

.close-btn:hover {
  color: #333;
}

.feedback-modal-content {
  padding: 20px;
  overflow-y: auto;
  flex-grow: 1;
}



.feedback-textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 8px;
  font-size: clamp(12px, 1.2vw, 14px);
  line-height: 1.5;
  resize: vertical;
  min-height: 100px;
}

.feedback-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 15px 20px;
  border-top: 1px solid #eee;
  background-color: #f8f9fa;
}

.save-btn, .cancel-btn {
  padding: 8px 15px;
  border: none;
  border-radius: 8px;
  font-size: clamp(12px, 1.2vw, 14px);
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.save-btn {
  background-color: #4caf50;
  color: white;
}

.save-btn:hover {
  background-color: #388e3c;
}

.cancel-btn {
  background-color: #f44336;
  color: white;
}

.cancel-btn:hover {
  background-color: #d32f2f;
}

@media (max-width: 768px) {
  .section-c-container {
    padding: 12px;
  }
  
  .header-section {
    flex-direction: column;
    align-items: flex-start;
    margin-bottom: 0px;
  }

  .title-instruction-row {
    flex-direction: column;
    gap: 8px;
  }

  .title-progress-container {
    flex-direction: column;
    gap: 4px;
    align-items: flex-start;
  }
  
  .progress-indicator {
    font-size: clamp(8px, 0.8vw, 10px);
    padding: 2px 6px;
    min-width: 32px;
  }

  .header-section h3 {
    margin-bottom: 8px;
  }

  .feedback-btn {
    margin-top: 0;
    padding: 5px 12px;
    font-size: 10px;
    flex-direction: column;
    gap: 3px;
    width: 100%;
  }

  .feedback-arrow {
    font-size: 14px;
  }

  .feedback-text {
    white-space: normal;
    text-align: center;
  }

  .instruction-box {
    margin-top: 0;
    padding: 6px 10px;
    width: 100%;
    justify-content: center;
  }

  .instruction-icon {
    font-size: 16px;
    margin-right: 6px;
  }

  .instruction-text {
    font-size: clamp(7px, 0.7vw, 10px);
    font-weight: 900;
  }

  .dimensions-list {
    padding: 10px;
    gap: 10px;
  }
  
  .dimension-item {
    padding: 10px;
  }
  
  .dimension-text {
    font-size: 13px;
  }
  
  .score-labels {
    padding: 0 4px;
  }
  
  .score-label {
    font-size: 11px;
  }
  
  .anchors-descriptions {
    padding: 0 4px;
    min-height: 24px;
  }
  
  .anchor-description {
    font-size: 10px;
    padding: 0 1px;
  }
  
  .score-dots {
    padding: 0 4px;
    gap: 4px;
  }
  
  .score-dot {
    width: 28px;
    height: 28px;
    font-size: 11px;
  }

  .feedback-modal {
    width: 95%;
    max-height: 90%;
  }

  .feedback-modal-header {
    padding: 10px 15px;
  }

  .feedback-modal-header h4 {
    font-size: 16px;
  }

  .close-btn {
    font-size: 24px;
  }

  .feedback-modal-content {
    padding: 15px;
  }



  .feedback-textarea {
    font-size: 11px;
    min-height: 80px;
  }

  .feedback-modal-footer {
    padding: 10px 15px;
  }

  .save-btn, .cancel-btn {
    padding: 6px 12px;
    font-size: 11px;
  }
}
</style>

