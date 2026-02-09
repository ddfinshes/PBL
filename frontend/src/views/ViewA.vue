<template>
  <div class="view-a">
    <!-- Title -->
    <div class="header">
      <h2>Upload Files</h2>
      <p class="subtitle">Upload PDF files containing case content, scenario breakdown and question annotations</p>
    </div>

    <!-- Status 1: File Processing Complete (Uploaded and Parsed) -->
    <div v-if="uploadedFile" class="uploaded-file">
      <div class="file-item">
        <div class="file-name">
          <svg class="pdf-icon" viewBox="0 0 24 24" fill="currentColor">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
          </svg>
          {{ uploadedFile.name }}
        </div>
        <div class="file-size">{{ formatFileSize(uploadedFile.size) }}</div>
      </div>
      
      <div class="success-badge">
        <svg class="success-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        Parsing Complete
      </div>

      <div class="file-actions">
        <button class="remove-btn" @click="removeFile">Remove</button>
        <button class="reupload-btn" @click="reuploadFile">Re-upload</button>
      </div>
    </div>

    <!-- Status 2: Processing (Uploading or Parsing) -->
    <div v-else-if="selectedFile" class="file-info">
      <div class="file-item">
        <div class="file-name">
          <svg class="pdf-icon" viewBox="0 0 24 24" fill="currentColor">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
          </svg>
          {{ selectedFile.name }}
        </div>
      </div>

      <!-- Stage A: Upload Progress -->
      <div v-if="isUploading" class="progress-container">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
        </div>
        <p class="progress-text">File uploading... {{ uploadProgress }}%</p>
      </div>

      <!-- Stage B: AI Parsing (New) -->
      <div v-else-if="isParsing" class="parsing-container">
        <div class="spinner"></div>
        <div class="parsing-content">
          <p class="parsing-title">AI is reading the case file...</p>
          <p class="parsing-subtitle">Splitting scenarios, extracting test results and images (approx 30-60 seconds)</p>
        </div>
      </div>
    </div>

    <!-- Status 3: Initial State (Drag Upload Area) -->
    <div 
      v-else
      class="upload-area"
      @click="openFileDialog"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
      :class="{ 'is-dragging': isDragging }"
    >
      <input
        type="file"
        ref="fileInput"
        accept=".pdf"
        @change="handleFileSelect"
        style="display: none"
      />

      <div class="upload-content">
        <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
        <p class="drag-text">Click or drag PDF file here</p>
      </div>
    </div>

    <!-- Error Message -->
    <div v-if="errorMessage" class="error-message">
      <svg class="error-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
      <div>
        <p class="error-title">Operation Failed</p>
        <p class="error-subtitle">{{ errorMessage }}</p>
      </div>
      <button class="close-error" @click="errorMessage = ''">×</button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

// Define events to emit to parent component
const emit = defineEmits(['analysis-complete'])

const fileInput = ref(null)
const selectedFile = ref(null)
const uploadedFile = ref(null)
const isDragging = ref(false)
const isUploading = ref(false)
const isParsing = ref(false)
const uploadProgress = ref(0)
const errorMessage = ref('')

const API_BASE = 'http://127.0.0.1:8000'

// Watch selectedFile change, auto start flow
watch(selectedFile, (newFile) => {
  if (newFile) {
    uploadFile()
  }
})

const openFileDialog = () => {
  fileInput.value.click()
}

const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) validateAndSelectFile(file)
}

const handleDrop = (event) => {
  isDragging.value = false
  const file = event.dataTransfer.files[0]
  if (file) validateAndSelectFile(file)
}

const validateAndSelectFile = (file) => {
  errorMessage.value = ''
  uploadedFile.value = null
  
  if (file.type !== 'application/pdf' && !file.name.endsWith('.pdf')) {
    errorMessage.value = '只支持PDF格式的文件'
    return
  }
  
  const maxSize = 100 * 1024 * 1024 // 50MB
  if (file.size > maxSize) {
    errorMessage.value = '文件大小不能超过 50MB'
    return
  }

  selectedFile.value = file
}

// 第一步：上传文件
const uploadFile = async () => {
  if (!selectedFile.value) return

  isUploading.value = true
  isParsing.value = false
  uploadProgress.value = 0
  errorMessage.value = ''

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    const xhr = new XMLHttpRequest()

    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) {
        uploadProgress.value = Math.round((event.loaded / event.total) * 100)
      }
    })

    xhr.addEventListener('load', () => {
      isUploading.value = false
      if (xhr.status === 200) {
        // 上传成功，拿到文件名，开始解析
        const response = JSON.parse(xhr.responseText)
        console.log('文件上传成功，准备解析:', response.file_name)
        startParsing(response.file_name)
      } else {
        const response = JSON.parse(xhr.responseText)
        errorMessage.value = response.detail || '上传失败'
        selectedFile.value = null // 重置状态允许重试
      }
    })

    xhr.addEventListener('error', () => {
      isUploading.value = false
      errorMessage.value = '网络连接失败，请检查后端服务'
      selectedFile.value = null
    })

    xhr.open('POST', `${API_BASE}/upload-pdf`)
    xhr.send(formData)
  } catch (err) {
    isUploading.value = false
    errorMessage.value = err.message
    selectedFile.value = null
  }
}

// 第二步：请求后端解析 (这是之前缺失的逻辑)
const startParsing = async (filename) => {
  isParsing.value = true
  
  try {
    // 同时请求：1.结构化数据(慢) 2.原始图片(快)
    // 这里的 fetch 不会像 axios 那样自动抛错，需要手动 check
    const [structureRes, imagesRes] = await Promise.all([
      fetch(`${API_BASE}/api/parse-case/${filename}`, { method: 'POST' }),
      fetch(`${API_BASE}/api/pdf-images/${filename}`, { method: 'GET' })
    ])

    if (!structureRes.ok) {
       const errJson = await structureRes.json().catch(() => ({}))
       throw new Error(errJson.detail || `结构解析失败 (${structureRes.status})`)
    }
    if (!imagesRes.ok) {
       throw new Error(`图片提取失败 (${imagesRes.status})`)
    }

    const structureData = await structureRes.json()
    const imagesData = await imagesRes.json()

    console.log('解析完成:', structureData)

    // 全部成功，更新状态
    uploadedFile.value = selectedFile.value
    
    // 提取基础名称（去掉时间戳）用于后续查询
    const caseName = filename.replace(/_\d{8}_\d{6}\.pdf$/, '')
    
    // 向父组件发送数据
    emit('analysis-complete', {
      structure: structureData,
      raw_images: imagesData,
      case_name: caseName,  // 新增：案例名称（不含时间戳）
      pdf_filename: filename
    })

  } catch (err) {
    console.error(err)
    errorMessage.value = `解析过程出错: ${err.message}`
    uploadedFile.value = null // 解析失败不视为完整成功
  } finally {
    isParsing.value = false
    // 只有在失败时才清空 selectedFile 以便重试，成功时保留以显示“已解析完成”
    if (errorMessage.value) {
      selectedFile.value = null
    }
  }
}

const removeFile = () => {
  uploadedFile.value = null
  selectedFile.value = null
  isParsing.value = false
  isUploading.value = false
  // 这里可以触发一个事件通知父组件清空 ViewC
  emit('analysis-complete', { 
    structure: null, 
    raw_images: null,
    case_name: null,
    pdf_filename: null
  })
}

const reuploadFile = () => {
  removeFile()
  openFileDialog()
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}
</script>

<style scoped>
.view-a {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #ECECEC;
  border-radius: 12px;
  overflow: hidden;
  color: #e5e7eb;
}

.header {
  flex-shrink: 0;
  background: #000000;
  padding: 8px 12px;
  margin: 0;
}

.header h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  text-align: left;
}

.subtitle {
  margin: 5px 0 0 0;
  font-size: 12px;
  color: #000000;
  display: none;
}

/* Upload Area */
.upload-area {
  flex: 1;
  border: 2px dashed #4b5563;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  min-height: 100px;
  background: rgba(75, 85, 99, 0.05);
  margin: 12px;
}

.upload-area:hover {
  border-color: #8095CA;
  background: rgba(128, 149, 202, 0.05);
}

.upload-area.is-dragging {
  border-color: #8095CA;
  background: rgba(128, 149, 202, 0.1);
  transform: scale(1.02);
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
  text-align: center;
}

.upload-icon {
  width: 40px;
  height: 40px;
  color: #8095CA;
  margin-bottom: 8px;
}

.drag-text {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: #4b5563;
}

.or-text {
  margin: 5px 0;
  font-size: 12px;
  color: #9ca3af;
}

/* File Info & Parsing States */
.file-info, .uploaded-file {
  flex-shrink: 0;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid #6366f1;
  border-radius: 8px;
  padding: 10px;
  margin: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.uploaded-file {
  background: rgba(34, 197, 94, 0.15);
  border-color: #198842;
}

.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.file-name {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: #1f2937;
  font-weight: 500;
}

.pdf-icon {
  width: 20px;
  height: 20px;
  color: #fc8d59;
  flex-shrink: 0;
}

.file-size {
  font-size: 12px;
  color: #9ca3af;
  flex-shrink: 0;
}

/* Progress Bar */
.progress-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.progress-bar {
  width: 100%;
  height: 4px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #8095CA;
  transition: width 0.3s ease;
  border-radius: 2px;
}

.progress-text {
  margin: 0;
  font-size: 12px;
  color: #9ca3af;
  text-align: right;
}

/* Parsing State */
.parsing-container {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(99, 102, 241, 0.1);
  padding: 10px;
  border-radius: 6px;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(128, 149, 202, 0.3);
  border-radius: 50%;
  border-top-color: #8095CA;
  animation: spin 1s linear infinite;
  flex-shrink: 0;
}

.parsing-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.parsing-title {
  font-size: 13px;
  font-weight: 500;
  color: #1f2937;
  margin: 0;
}

.parsing-subtitle {
  font-size: 11px;
  color: #9ca3af;
  margin: 0;
}

/* Success Badge */
.success-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #7fbf4c;
  font-weight: 500;
}

.success-icon {
  width: 16px;
  height: 16px;
}

/* Actions */
.file-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}

.remove-btn,
.reupload-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.remove-btn {
  background: rgba(252, 141, 89, 0.1);
  color: #fc8d59;
}
.remove-btn:hover {
  background: rgba(252, 141, 89, 0.2);
}

.reupload-btn {
  background: rgba(128, 149, 202, 0.1);
  color: #8095CA;
}
.reupload-btn:hover {
  background: rgba(128, 149, 202, 0.2);
}

/* Error Message */
.error-message {
  flex-shrink: 0;
  background: rgba(252, 141, 89, 0.1);
  border: 1px solid #fc8d59;
  border-radius: 8px;
  padding: 10px;
  margin: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  animation: slideIn 0.3s ease;
  position: relative;
}

.error-icon {
  width: 24px;
  height: 24px;
  color: #fc8d59;
  flex-shrink: 0;
}

.error-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #fc8d59;
}

.error-subtitle {
  margin: 3px 0 0 0;
  font-size: 12px;
  color: #fc8d59;
}

.close-error {
  position: absolute;
  top: 8px;
  right: 8px;
  background: none;
  border: none;
  color: #fca5a5;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Scrollbar */
.view-a::-webkit-scrollbar {
  width: 6px;
}
.view-a::-webkit-scrollbar-track {
  background: transparent;
}
.view-a::-webkit-scrollbar-thumb {
  background: rgba(75, 85, 99, 0.5);
  border-radius: 3px;
}
.view-a::-webkit-scrollbar-thumb:hover {
  background: rgba(75, 85, 99, 0.8);
}
</style>