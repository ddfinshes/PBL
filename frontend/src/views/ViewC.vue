<template>
  <div class="view-c">
    <!-- Top: Scene Title (Always Visible) -->
    <div class="scene-header">
      <h2 class="view-title">Original Case</h2>
      <div v-if="currentScene" class="scene-badges">
        <span class="badge-index">Scene {{ currentIndex + 1 }} / {{ totalScenes }}</span>
      </div>
    </div>

    <!-- Empty State Hint -->
    <div v-if="!currentScene" class="empty-state">
      <div class="empty-content">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="16" y1="13" x2="8" y2="13"></line>
          <line x1="16" y1="17" x2="8" y2="17"></line>
          <polyline points="10 9 9 9 8 9"></polyline>
        </svg>
        <p>Please upload the original case file on the left</p>
      </div>
    </div>

    <!-- Content Area -->
    <div v-else class="scene-container-content">

      <!-- Middle: Scrollable Content Area -->
      <div class="scene-content-scroll">
        <!-- Top Half: Story + Images -->
        <div class="top-half">
          <div class="content-left">
            <div class="section-card story-section">
              <div class="markdown-body" v-html="renderMarkdown(currentScene.story_content)"></div>
            </div>
          </div>

          <div v-if="currentImages.length > 0" class="content-right">
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
              </div>
            </div>
          </div>
        </div>

        <!-- Bottom Half: Trigger Questions -->
        <div class="bottom-half">
          <div class="section-card teacher-section">
            <div class="section-title">
              Trigger Questions
            </div>
            
            <div class="teacher-content-wrapper">
              <div class="sub-block">
                <ul v-if="currentScene.trigger_questions?.length" class="question-list">
                  <li 
                    v-for="(q, qIdx) in currentScene.trigger_questions" 
                    :key="qIdx" 
                    class="question-item"
                    :class="{ 'active-item': activeQuestionInfo.sceneIndex === currentIndex && activeQuestionInfo.questionIndex === qIdx }"
                  >
                    <div v-if="editingQuestion?.sceneIdx === currentIndex && editingQuestion?.qIdx === qIdx" class="edit-mode">
                      <textarea 
                        v-model="editingQuestion.text"
                        class="edit-textarea"
                        placeholder="Edit question content..."
                      ></textarea>
                      <div class="edit-actions">
                        <button class="edit-btn save" @click="saveQuestion(qIdx)">Save</button>
                        <button class="edit-btn cancel" @click="cancelEdit">Cancel</button>
                      </div>
                    </div>

                    <div v-else class="view-mode">
                      <div class="q-main">
                        <span class="q-marker">Q{{ qIdx + 1 }}</span>
                        <span class="q-text">{{ q.question }}</span>
                      </div>
                      <div class="q-actions">
                        <button 
                          class="inspect-btn" 
                          :class="{ 'active-inspect': activeQuestionInfo.sceneIndex === currentIndex && activeQuestionInfo.questionIndex === qIdx }"
                          @click.stop="onInspectQuestion(q, qIdx)"
                          title="View detailed analysis or related location"
                        >
                          <svg viewBox="0 0 24 24" width="18" height="14" stroke="currentColor" fill="none" stroke-width="2.5">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                          </svg>
                        </button>
                        <button 
                          class="edit-icon-btn"
                          @click.stop="startEdit(q.question, qIdx)"
                          title="Edit question"
                        >
                          <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" fill="none" stroke-width="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                          </svg>
                        </button>
                        <button 
                          class="delete-item-btn"
                          @click.stop="deleteQuestion(qIdx)"
                          title="Delete question"
                        >
                          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" stroke-width="2.5">
                            <path d="M18 6L6 18M6 6l12 12"></path>
                          </svg>
                        </button>
                      </div>
                    </div>
                  </li>
                </ul>
                
                <div class="add-question-btn-wrapper" @click="addQuestion">
                  <div class="plus-icon">+</div>
                  <div class="add-text">Add Question</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Bottom: Navigation Buttons -->
      <div class="scene-footer">
        <button 
          class="nav-btn prev" 
          :disabled="currentIndex === 0"
          @click="prevScene"
        >
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
          Previous
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
          Next
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, defineEmits, inject } from 'vue'
import MarkdownIt from 'markdown-it'

// --- 配置与 Props ---
const API_BASE_URL = 'http://127.0.0.1:8000'

const props = defineProps({
  caseData: { type: Object, default: null },
  rawPdfData: { type: Object, default: null }
})

// 定义事件，供外部组件监听
const emit = defineEmits(['inspect-question'])

const { activeQuestionInfo } = inject('pblSocket')

// --- 状态管理 ---
const currentIndex = ref(0)
// const activeQuestionInfo = ref({ sceneIdx: -1, qIdx: -1 })
const showTeacherGuide = ref(true)
const failedImages = ref(new Set())
const existingImages = ref(new Set())  // 存储实际存在的图片列表
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
      index: idx,
      filename: url.split('/').pop()  // 提取文件名
    }))
  } else if (currentScene.value.images_base64?.length) {
    images = currentScene.value.images_base64.map((base64Url, idx) => ({
      src: base64Url,
      index: idx,
      filename: null
    }))
  }
  // 过滤：只保留没有加载失败的图片
  // 如果已有实际图片列表，则进一步过滤不存在的图片
  return images.filter((img, idx) => {
    // 先检查是否加载失败
    if (failedImages.value.has(`${currentIndex.value}_${idx}`)) {
      return false
    }
    // 如果有实际图片列表且是URL图片，检查是否存在
    if (existingImages.value.size > 0 && img.filename) {
      return existingImages.value.has(img.filename)
    }
    // base64图片或existingImages还未加载时，显示
    return true
  })
})

// --- 方法 ---
const renderMarkdown = (text) => text ? md.render(text) : ''

/**
 * 获取案例文件夹中实际存在的图片列表
 */
const fetchExistingImages = async () => {
  if (!props.caseData?.case_title) return
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/case-images/${props.caseData.case_title}`)
    const data = await response.json()
    if (data.images) {
      existingImages.value = new Set(data.images)
      console.log('✓ 已加载存在的图片列表:', data.images)
    }
  } catch (error) {
    console.error('获取图片列表失败:', error)
  }
}

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
  // 获取失败的图片信息
  if (currentImages.value[imgIdx]) {
    const failedImg = currentImages.value[imgIdx]
    // 标记为加载失败
    failedImages.value.add(`${sceneIdx}_${imgIdx}`)
    // 从existing列表中移除，防止再次尝试加载
    if (failedImg.filename) {
      existingImages.value.delete(failedImg.filename)
      console.log(`✗ 图片加载失败，已从列表中移除: ${failedImg.filename}`)
    }
  }
}

/**
 * 添加新引导问题
 */
async function addQuestion() {
  if (!props.caseData || !props.caseData.case_title) {
    alert('无法获取案例信息，请重试');
    return;
  }

  const defaultText = "";
  
  try {
    const caseName = props.caseData.case_title;
    const sceneIdx = currentIndex.value;

    const response = await fetch(`${API_BASE_URL}/api/add-question`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        caseName: caseName,
        sceneIndex: sceneIdx,
        questionText: defaultText
      })
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || result.message || '添加失败');
    }

    // 更新本地状态
    if (!currentScene.value.trigger_questions) {
      currentScene.value.trigger_questions = [];
    }
    
    // 为了响应式，重新分配数组
    currentScene.value.trigger_questions = [...currentScene.value.trigger_questions, { question: defaultText }];
    
    // 自动进入新问题的编辑模式
    const newIdx = currentScene.value.trigger_questions.length - 1;
    startEdit(defaultText, newIdx);
    
    console.log('✓ 问题已添加到后端并更新 UI');
  } catch (error) {
    console.error('Add question error:', error);
    alert(`添加失败: ${error.message}`);
  }
}

/**
 * 删除问题
 */
async function deleteQuestion(qIdx) {
  if (!props.caseData || !props.caseData.case_title) {
    alert('无法获取案例信息，请重试');
    return;
  }
  
  try {
    const caseName = props.caseData.case_title;
    const sceneIdx = currentIndex.value;
    
    console.log(`Deleting question: Case=${caseName}, Scene=${sceneIdx}, Index=${qIdx}`);

    const response = await fetch(`${API_BASE_URL}/api/delete-question`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        caseName: caseName,
        sceneIndex: sceneIdx,
        questionIndex: qIdx
      })
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || result.message || '删除失败');
    }

    // 更新本地状态
    if (currentScene.value && currentScene.value.trigger_questions) {
      currentScene.value.trigger_questions.splice(qIdx, 1);
    }
    
    // 如果删除的是当前选中的问题
    if (activeQuestionInfo.value.sceneIndex === sceneIdx && activeQuestionInfo.value.questionIndex === qIdx) {
      if (currentScene.value.trigger_questions.length > 0) {
        onInspectQuestion(currentScene.value.trigger_questions[0], 0);
      } else {
        activeQuestionInfo.value = { sceneIndex: -1, questionIndex: -1 };
      }
    } else if (activeQuestionInfo.value.sceneIndex === sceneIdx && activeQuestionInfo.value.questionIndex > qIdx) {
      activeQuestionInfo.value.questionIndex--;
    }

    alert('问题已成功删除');
  } catch (error) {
    console.error('Delete error:', error);
    alert(`删除失败: ${error.message}`);
  }
}

/**
 * 处理点击查看问题标识
 */
const onInspectQuestion = async (questionObj, qIdx) => {
  const activeStory = currentScene.value.story_content;
  const activeQuestion = questionObj.question;

  // 更新当前激活的问题索引，用于 UI 高亮 (同步到全局 socket 状态)
  activeQuestionInfo.value = { sceneIndex: currentIndex.value, questionIndex: qIdx };

  console.log('--- Agent Context Updated ---');
  console.log('Scene:', currentScene.value.title);
  console.log('Story Segment:', activeStory.substring(0, 100) + '...');
  console.log('Trigger Question:', activeQuestion);
  console.log('------------------------------');

  // 1. 调用后端更新当前的 PBL 状态，以便 Agent 使用
  try {
    const response = await fetch(`${API_BASE_URL}/api/set-active-scene`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        story: activeStory,
        trigger_questions: [activeQuestion], // 重点：传入当前点击的这一个问题
        scene_index: currentIndex.value,
        question_index: qIdx
      })
    })
    if (response.ok) {
      console.log('✓ Backend PBL (Story & Question) successfully synced with clicked item.');
    }
  } catch (error) {
    console.error('Failed to update backend PBL background:', error)
  }

  // 2. 触发事件，用于 UI 同步或通知
  emit('inspect-question', {
    sceneIndex: currentIndex.value,
    questionIndex: qIdx,
    data: questionObj
  })
}

/**
 * 开始编辑问题
 */
const startEdit = (questionText, qIdx) => {
  editingQuestion.value = {
    sceneIdx: currentIndex.value,
    qIdx,
    text: questionText
  }
}

/**
 * 取消编辑
 */
const cancelEdit = () => {
  editingQuestion.value = null
}

/**
 * 保存编辑后的问题
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

watch(() => props.caseData, (newData) => {
  console.log('Case Data Changed, resetting scene to 0.');
  currentIndex.value = 0;
  failedImages.value.clear();
  
  // 获取案例的实际图片列表
  fetchExistingImages();
  
  // 如果新数据存在，手动触发第一幕第一个问题的激活
  if (newData?.scenes?.[0]?.trigger_questions?.[0]) {
    setTimeout(() => {
      onInspectQuestion(newData.scenes[0].trigger_questions[0], 0);
    }, 500);
  }
})

/**
 * 监听幕次切换，自动高亮并同步当前幕的第一个问题
 */
watch(currentIndex, (newIdx) => {
  console.log('Current Index Changed to:', newIdx);
  if (props.caseData?.scenes?.[newIdx]?.trigger_questions?.[0]) {
    const firstQuestion = props.caseData.scenes[newIdx].trigger_questions[0];
    setTimeout(() => {
      onInspectQuestion(firstQuestion, 0);
    }, 300);
  }
})
</script>

<style scoped>
/* 基础布局 */
.view-c {
  background: #ECECEC;
  color: #333333;
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
  flex: 1;
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
.scene-container-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

/* 头部 */
.scene-header {
  padding: 8px 12px;
  background: #000000;
  flex-shrink: 0;
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.view-title {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
  text-align: left;
}
.view-tag {
  width: 32px;
  height: 32px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 16px;
  color: #8fa1ff;
}
.scene-badges {
  display: flex;
  align-items: center;
  gap: 12px;
}
.badge-index {
  background: rgba(255, 255, 255, 0.9);
  color: #000000;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;
}

/* 滚动内容区 */
.scene-content-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 0 14px;
}

.content-wrapper {
  display: flex;
  gap: 24px;
  align-items: flex-start;
  padding-top: 10px;
}

.content-left {
  flex: 1.2;
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-width: 0;
}

.content-right {
  flex: 0.8;
  flex-shrink: 0;
}

/* 通用卡片 */
.section-card {
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 10px;
}

/* Markdown 内容样式 */
:deep(.markdown-body) {
  font-size: 15px;
  line-height: 1.6;
  color: #1f2937;
}

/* 教师指引与问题列表 */
.teacher-section {
  border: none;
  background: transparent;
  padding: 0;
}

.question-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.question-item {
  background: #f3f4f6;
  padding: 8px 12px;
  border-radius: 8px;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border: 1px solid #d1d5db;
  transition: all 0.2s;
}

.question-item.active-item {
  background: #dbeafe;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

.view-mode {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  width: 100%;
  min-height: 32px;
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
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #ffffff;
  color: #1f2937;
  font-size: 13px;
  line-height: 1.5;
  font-family: inherit;
  resize: vertical;
}

.edit-textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.edit-actions {
  display: flex;
  gap: 8px;
}

.edit-btn {
  padding: 6px 12px;
  border-radius: 4px;
  /* border: 1px solid rgba(255, 255, 255, 0.2); */
  font-size: 12px;
  cursor: pointer;
  /* transition: all 0.2s; */
  color: #ffffff;
  background-color: #7F96CB;
}

.edit-btn.save {
  background: #3b3f61;
  color: white;
  border-color: #4a5d8a;
}

.edit-btn.save:hover {
  background: #4a5d8a;
}

.edit-btn.cancel {
  background: rgba(252, 141, 89, 0.1);
  border-color: rgba(252, 141, 89, 0.3);
  color: #fc8d59;
}

.edit-btn.cancel:hover {
  background: rgba(252, 141, 89, 0.2);
  border-color: rgba(252, 141, 89, 0.5);
}

.q-main {
  display: flex;
  gap: 12px;
  font-size: 15px;
  color: #1f2937;
  flex: 1;
  min-width: 0;
}

.q-text {
  word-break: break-word;
}

.q-marker {
  color: #3b82f6;
  font-weight: 700;
  flex-shrink: 0;
}

.q-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.inspect-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: #4d7c0f;
  border: none;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.inspect-btn.active-inspect {
  background: #65a30d;
  box-shadow: 0 0 12px rgba(101, 163, 13, 0.4);
}

.edit-icon-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: #e0e7ff;
  border: 1px solid #818cf8;
  color: #4f46e5;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.edit-icon-btn:hover {
  background: #c7d2fe;
  border-color: #6366f1;
}

.delete-item-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #ef4444;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.delete-item-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.5);
}

/* Add Question Button (ViewB style) */
.add-question-btn-wrapper {
  margin-top: 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  gap: 12px;
  padding: 10px 24px;
  border-radius: 9999px;
  border: 2px dashed #8095CA;
  background-color: rgba(128, 149, 202, 0.1);
  transition: all 0.3s ease;
}

.add-question-btn-wrapper:hover {
  background-color: rgba(128, 149, 202, 0.2);
  transform: translateY(-2px);
}

.add-question-btn-wrapper .plus-icon {
  font-size: 28px;
  color: #8095CA;
  font-weight: 300;
  line-height: 1;
}

.add-question-btn-wrapper .add-text {
  font-size: 15px;
  color: #4b5563;
  font-weight: 700;
}

/* 图片堆栈 */
.image-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.image-item-vertical {
  border-radius: 8px;
  overflow: hidden;
  cursor: zoom-in;
  background: #ffffff;
  border: 1px solid #d1d5db;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
.image-item-vertical img {
  width: 100%;
  display: block;
}

/* 底部导航 */
.scene-footer {
  padding: 10px 14px;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #374151;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 12px;
  font-weight: 500;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}
.nav-btn:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #9ca3af;
}
.nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  background: #f3f4f6;
}

.progress-dots {
  display: flex;
  gap: 12px;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d1d5db;
  cursor: pointer;
  transition: all 0.2s;
}
.dot:hover {
  background: #9ca3af;
}
.dot.active {
  background: #3b82f6;
  transform: scale(1.2);
}

.arrow-icon { transition: transform 0.3s; }
.rotate-180 { transform: rotate(180deg); }

/* 滚动条美化 */
.scene-content-scroll::-webkit-scrollbar { width: 5px; }
.scene-content-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.scene-content-scroll::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 10px;
}
.scene-content-scroll::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}
</style>