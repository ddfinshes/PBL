<template>
  <div class="view-c">
    <!-- 空状态提示 -->
    <div v-if="!currentScene" class="empty-state">
      <div class="empty-content">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="16" y1="13" x2="8" y2="13"></line>
          <line x1="16" y1="17" x2="8" y2="17"></line>
          <polyline points="10 9 9 9 8 9"></polyline>
        </svg>
        <p>暂无场景数据，请先在左侧上传并解析教案</p>
      </div>
    </div>

    <!-- 内容区域 -->
    <div v-else class="scene-container">
      <!-- 顶部：场景标题 -->
      <div class="scene-header">
        <div class="scene-badges">
          <span class="badge-index">第 {{ currentIndex + 1 }} 幕 / 共 {{ totalScenes }} 幕</span>
          <span class="badge-title">{{ currentScene.title }}</span>
        </div>
      </div>

      <!-- 中间：滚动内容区 -->
      <div class="scene-content-scroll">
        <div class="content-wrapper">
          <!-- 左侧：文字内容 -->
          <div class="content-left">
            <!-- 1. 剧情/病情描述 (Markdown) -->
            <div class="section-card story-section">
              <div class="section-title">
                <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" fill="none">
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
                  <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
                </svg>
                情景描述 & 临床资料
              </div>
              <div class="markdown-body" v-html="renderMarkdown(currentScene.story_content)"></div>
            </div>

            <!-- 2. 教师指引/触发问题 (折叠面板) -->
            <div class="section-card teacher-section">
              <div class="section-title" @click="showTeacherGuide = !showTeacherGuide" style="cursor: pointer">
                <div style="display:flex; align-items:center; gap:6px">
                  <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" fill="none">
                    <path d="M2 21h19a2 2 0 0 0 2-2v-5a2 2 0 0 0-2-2H2"></path>
                    <path d="M5 12V3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v9"></path>
                  </svg>
                 触发问题
                </div>
                <svg :class="{ 'rotate-180': !showTeacherGuide }" class="arrow-icon" viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </div>
              
              <div v-show="showTeacherGuide" class="teacher-content-wrapper">
                <div v-if="currentScene.trigger_questions?.length" class="sub-block">
                  <div class="label">引导问题 (Trigger Questions)</div>
                  <ul class="question-list">
                    <!-- 列表项修改：增加 flex 布局 -->
                    <li v-for="(q, qIdx) in currentScene.trigger_questions" :key="qIdx" class="question-item">
                      <!-- 【编辑模式】 -->
                      <div v-if="editingQuestion?.sceneIdx === currentIndex && editingQuestion?.qIdx === qIdx" class="edit-mode">
                        <textarea 
                          v-model="editingQuestion.text"
                          class="edit-textarea"
                          placeholder="编辑问题内容..."
                        ></textarea>
                        <div class="edit-actions">
                          <button class="edit-btn save" @click="saveQuestion(qIdx)">保存</button>
                          <button class="edit-btn cancel" @click="cancelEdit">取消</button>
                        </div>
                      </div>

                      <!-- 【查看模式】 -->
                      <div v-else class="view-mode">
                        <div class="q-main">
                          <span class="q-marker">Q{{ qIdx + 1 }}</span>
                          <span class="q-text">{{ q.question }}</span>
                        </div>
                        <div class="q-actions">
                          <button 
                            class="inspect-btn" 
                            @click.stop="onInspectQuestion(q, qIdx)"
                            title="查看详细解析或关联位置"
                          >
                            <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2.5">
                              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                              <circle cx="12" cy="12" r="3"></circle>
                            </svg>
                            <span>查看</span>
                          </button>
                          <button 
                            class="edit-icon-btn"
                            @click.stop="startEdit(q.question, qIdx)"
                            title="编辑问题"
                          >
                            <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2">
                              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                            </svg>
                          </button>
                        </div>
                      </div>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <!-- 右侧：图片内容 -->
          <div v-if="currentImages.length > 0" class="content-right">
            <div class="section-card images-section">
              <div class="section-title">
                <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" fill="none">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                  <circle cx="8.5" cy="8.5" r="1.5"></circle>
                  <polyline points="21 15 16 10 5 21"></polyline>
                </svg>
                相关影像资料
              </div>
              <div class="image-stack">
                <div 
                  v-for="(img, idx) in currentImages" 
                  :key="idx" 
                  class="image-item-vertical"
                  @click="previewImage(img)"
                >
                  <img 
                    :src="img.src" 
                    @error="handleImageError(idx, currentIndex)"
                  />
                  <span class="img-caption">图 {{ idx + 1 }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部：导航按钮 -->
      <div class="scene-footer">
        <button 
          class="nav-btn prev" 
          :disabled="currentIndex === 0"
          @click="prevScene"
        >
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
          上一幕
        </button>

        <div class="progress-dots">
          <span 
            v-for="n in totalScenes" 
            :key="n" 
            class="dot"
            :class="{ active: (n-1) === currentIndex }"
            @click="currentIndex = n-1"
          ></span>
        </div>

        <button 
          class="nav-btn next" 
          :disabled="currentIndex === totalScenes - 1"
          @click="nextScene"
        >
          下一幕
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, defineEmits } from 'vue'
import MarkdownIt from 'markdown-it'

// --- 配置与 Props ---
const API_BASE_URL = 'http://localhost:8000'

const props = defineProps({
  caseData: { type: Object, default: null },
  rawPdfData: { type: Object, default: null }
})

// 定义事件，供外部组件监听
const emit = defineEmits(['inspect-question'])

// --- 状态管理 ---
const currentIndex = ref(0)
const showTeacherGuide = ref(true)
const failedImages = ref(new Set())
// 编辑状态：{ sceneIdx, qIdx, text }
const editingQuestion = ref(null)
const isSaving = ref(false)
const md = new MarkdownIt({ html: true, breaks: true, linkify: true })

// --- 计算属性 ---
const totalScenes = computed(() => props.caseData?.scenes?.length || 0)

const currentScene = computed(() => {
  if (!props.caseData?.scenes?.length) return null
  return props.caseData.scenes[currentIndex.value]
})

const currentImages = computed(() => {
  if (!currentScene.value) return []
  let images = []
  if (currentScene.value.image_urls?.length) {
    images = currentScene.value.image_urls.map((url, idx) => ({
      src: `${API_BASE_URL}${url}`,
      index: idx
    }))
  } else if (currentScene.value.images_base64?.length) {
    images = currentScene.value.images_base64.map((base64Url, idx) => ({
      src: base64Url,
      index: idx
    }))
  }
  return images.filter((img, idx) => !failedImages.value.has(`${currentIndex.value}_${idx}`))
})

// --- 方法 ---
const renderMarkdown = (text) => text ? md.render(text) : ''

const nextScene = () => {
  if (currentIndex.value < totalScenes.value - 1) {
    currentIndex.value++
    const scrollContainer = document.querySelector('.scene-content-scroll')
    if (scrollContainer) scrollContainer.scrollTop = 0
  }
}

const prevScene = () => {
  if (currentIndex.value > 0) currentIndex.value--
}

const previewImage = (img) => {
  window.open(img.src, '_blank')
}

const handleImageError = (imgIdx, sceneIdx) => {
  failedImages.value.add(`${sceneIdx}_${imgIdx}`)
}

/**
 * 【新增方法】处理点击查看问题标识
 */
const onInspectQuestion = (questionObj, qIdx) => {
  console.log('Inspect Question:', questionObj)
  // 触发事件，发送当前幕索引、问题索引及问题对象内容
  emit('inspect-question', {
    sceneIndex: currentIndex.value,
    questionIndex: qIdx,
    data: questionObj
  })
}

/**
 * 【新增方法】开始编辑问题
 */
const startEdit = (questionText, qIdx) => {
  editingQuestion.value = {
    sceneIdx: currentIndex.value,
    qIdx,
    text: questionText
  }
}

/**
 * 【新增方法】取消编辑
 */
const cancelEdit = () => {
  editingQuestion.value = null
}

/**
 * 【新增方法】保存编辑后的问题
 */
const saveQuestion = async (qIdx) => {
  if (!editingQuestion.value || !editingQuestion.value.text.trim()) {
    alert('问题内容不能为空')
    return
  }

  isSaving.value = true
  try {
    // 1. 更新本地状态
    currentScene.value.trigger_questions[qIdx].question = editingQuestion.value.text

    // 2. 调用后端API保存到JSON文件
    const response = await fetch(`${API_BASE_URL}/api/save-case`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        caseName: props.caseData.case_title,
        sceneIndex: editingQuestion.value.sceneIdx,
        questionIndex: qIdx,
        newQuestion: editingQuestion.value.text
      })
    })

    if (!response.ok) {
      throw new Error(`保存失败: ${response.statusText}`)
    }

    console.log('✓ 问题已保存到后端')
    editingQuestion.value = null
  } catch (error) {
    console.error('保存问题失败:', error)
    alert(`保存失败: ${error.message}`)
  } finally {
    isSaving.value = false
  }
}

watch(() => props.caseData, () => {
  currentIndex.value = 0
  failedImages.value.clear()
})
</script>

<style scoped>
/* 基础布局 */
.view-c {
  background: #1a1f3a;
  color: #e5e7eb;
  width: 100%;
  height: 100%;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
}

/* 空状态 */
.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
}
.empty-content {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.empty-icon {
  width: 48px;
  height: 48px;
  opacity: 0.5;
}

/* 场景容器 */
.scene-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* 头部 */
.scene-header {
  padding: 16px 20px;
  background: rgba(0, 0, 0, 0.2);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  flex-shrink: 0;
}
.scene-badges {
  display: flex;
  align-items: center;
  gap: 12px;
}
.badge-index {
  background: #6366f1;
  color: white;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}
.badge-title {
  font-size: 16px;
  font-weight: 600;
  color: white;
}

/* 滚动内容区 */
.scene-content-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.content-wrapper {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.content-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 0;
}

.content-right {
  width: 300px;
  flex-shrink: 0;
}

/* 通用卡片 */
.section-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 16px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #9ca3af;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.1);
}

/* Markdown 内容样式 */
:deep(.markdown-body) {
  font-size: 14px;
  line-height: 1.6;
  color: #d1d5db;
}
:deep(.markdown-body p) { margin-bottom: 10px; }
:deep(.markdown-body table) {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0;
  background: rgba(0, 0, 0, 0.2);
}
:deep(.markdown-body th), :deep(.markdown-body td) {
  padding: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

/* 教师指引与问题列表 */
.teacher-section {
  border-left: 3px solid #10b981;
  background: rgba(16, 185, 129, 0.05);
}

.label {
  font-size: 12px;
  color: #34d399;
  font-weight: 600;
  margin-bottom: 8px;
}

.question-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

/* 每一项改为 Flex 布局以容纳按钮 */
.question-item {
  background: rgba(0, 0, 0, 0.2);
  padding: 10px 12px;
  border-radius: 6px;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.question-item:hover {
  border-color: rgba(16, 185, 129, 0.3);
  background: rgba(16, 185, 129, 0.08);
}

.q-main {
  display: flex;
  gap: 8px;
  font-size: 13px;
  line-height: 1.5;
}

.q-marker {
  color: #10b981;
  font-weight: bold;
  flex-shrink: 0;
}

.q-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

/* 查看模式和编辑模式的包装器 */
.view-mode {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
}

.edit-mode {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

.edit-textarea {
  width: 100%;
  min-height: 80px;
  padding: 10px;
  border: 1px solid rgba(16, 185, 129, 0.5);
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.3);
  color: #d1d5db;
  font-size: 13px;
  line-height: 1.5;
  font-family: inherit;
  resize: vertical;
}

.edit-textarea:focus {
  outline: none;
  border-color: #10b981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.3);
}

.edit-actions {
  display: flex;
  gap: 8px;
}

.edit-btn {
  padding: 6px 12px;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  color: #d1d5db;
}

.edit-btn.save {
  background: #10b981;
  color: white;
  border-color: #10b981;
}

.edit-btn.save:hover {
  background: #059669;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
}

.edit-btn.cancel {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
  color: #fca5a5;
}

.edit-btn.cancel:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.5);
}

/* 编辑图标按钮 */
.edit-icon-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.3);
  color: #818cf8;
  cursor: pointer;
  transition: all 0.2s;
}

.edit-icon-btn:hover {
  background: #6366f1;
  color: white;
  border-color: #6366f1;
}

/* 查看标识按钮 */
.inspect-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 5px;
  border-radius: 4px;
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #34d399;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: -1px;
}

.inspect-btn:hover {
  background: #10b981;
  color: #fff;
  border-color: #10b981;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
}

/* 图片堆栈 */
.images-section {
  border-left: 3px solid #8b5cf6;
  background: rgba(139, 92, 246, 0.05);
}
.image-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.image-item-vertical {
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  overflow: hidden;
  cursor: zoom-in;
  background: #000;
}
.image-item-vertical img {
  width: 100%;
  display: block;
  max-height: 200px;
  object-fit: contain;
}
.img-caption {
  display: block;
  padding: 4px;
  text-align: center;
  font-size: 11px;
  background: rgba(0,0,0,0.5);
}

/* 底部导航 */
.scene-footer {
  padding: 5px 10px;
  background: rgba(0, 0, 0, 0.3);
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: white;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 10px;
}
.nav-btn:hover:not(:disabled) {
  background: #6366f1;
  border-color: #6366f1;
}
.nav-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.progress-dots {
  display: flex;
  gap: 8px;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  cursor: pointer;
}
.dot.active {
  background: #6366f1;
  transform: scale(1.2);
}

.arrow-icon { transition: transform 0.3s; }
.rotate-180 { transform: rotate(180deg); }

/* 滚动条美化 */
.scene-content-scroll::-webkit-scrollbar { width: 5px; }
.scene-content-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
}
</style>