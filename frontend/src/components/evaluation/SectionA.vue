<template>
  <div class="content">
    <!-- 保存成功提示弹窗 -->
    <transition name="notification">
      <div v-if="showSaveNotification" class="save-notification">
        <div class="notification-content">
          <span class="notification-icon">✓</span>
          <span class="notification-text">顺序已保存</span>
        </div>
      </div>
    </transition>



    <!-- 按钮和提示框容器 -->
    <div class="header-controls">
      <div class="case-navigation">
        <button 
          class="nav-btn prev-btn"
          @click="handlePrevCase"
          :disabled="currentCaseIndex <= 0"
          title="上一个病例"
        >
          ◀ 上一个
        </button>
        <span class="case-label">{{ caseDisplayLabel }}</span>
        <button 
          class="nav-btn next-btn"
          @click="handleNextCase"
          :disabled="currentCaseIndex >= caseNames.length - 1"
          title="下一个病例"
        >
          下一个 ▶
        </button>
      </div>
    </div>

    <!-- 医生列表 -->
    <div v-if="loading" class="loading">
      加载中...
    </div>
    <div v-else class="evaluators-container">
      <div 
        v-for="(evaluator, index) in evaluators" 
        :key="evaluator.id" 
        class="evaluator-card"
        :class="{ 'selected': selectedEvaluator && selectedEvaluator.id === evaluator.id }"
        @click="selectEvaluator(evaluator)"
      >
        <div class="evaluator-avatar">
          <img 
            :src="require('@/assets/user.png')" 
            alt="医生头像" 
            class="avatar-image"
          />
        </div>
        <div class="evaluator-info">
          <div class="evaluator-name">{{ evaluator.name }}</div>
          <div class="evaluator-number">#{{ index + 1 }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";

// 配置axios baseURL
axios.defaults.baseURL = process.env.NODE_ENV === 'development' 
  ? '' // 在开发环境中使用相对路径，通过Vue代理
  : window.location.origin;

export default {
  name: "SectionA",
  props: {
    username: {
      type: String,
      required: true
    },
    currentCaseId: {
      type: Number,
      default: 1
    },
    navigationDirection: {
      type: String,
      default: null
    }
  },
  emits: ['evaluator-selected', 'available-evaluators-changed'],
  data() {
    return {
      evaluators: [],
      selectedEvaluator: null,
      loading: false,
      showSaveNotification: false,
      // case 切换相关
      caseNames: [],
      currentCaseIndex: 0
    }
  },
  computed: {
    caseDisplayLabel() {
    const mapping = [
      '差差差中', // case1
      '中中中中', // case2
      '好中好中', // case3
      '好中差差'  // case4
    ];
    return mapping[this.currentCaseIndex] || '';
  }
  },
  methods: {
    async loadEvaluators() {
      this.loading = true;
      
      try {
        // 首先获取当前案例信息，以确定正确的案例ID
        const caseResponse = await fetch(`/api/evaluation/current-case?username=${this.username}`);
        const caseData = await caseResponse.json();
        
        if (caseData.status !== 'success') {
          throw new Error('获取当前案例信息失败');
        }
        
        // 从case_filename中提取案例ID
        let actualCaseId = this.currentCaseId;
        if (caseData.case_filename && caseData.case_filename.startsWith('case')) {
          actualCaseId = parseInt(caseData.case_filename.replace('case', ''));
        }
        
        // 获取可用的cases列表（从后端或本地定义）
        await this.loadAvailableCases();
        
        // 更新currentCaseIndex
        this.currentCaseIndex = this.caseNames.findIndex(name => {
          const caseNum = parseInt(name.replace('case', ''));
          return caseNum === actualCaseId;
        });
        if (this.currentCaseIndex === -1) {
          this.currentCaseIndex = 0;
        }
        
        const apiUrl = `/api/evaluation/case/${actualCaseId}/evaluators`;
        console.log('请求API:', apiUrl, '实际caseId:', actualCaseId, '传入caseId:', this.currentCaseId);
        
        const response = await fetch(apiUrl);
        console.log('API响应状态:', response.status, response.statusText);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('API响应数据:', data);
        
        if (data.status === 'success') {
          this.evaluators = data.evaluators;
          
          // 为每个评估者添加初始顺序（player x）
          this.evaluators.forEach((evaluator, index) => {
            evaluator.initialOrder = index + 1;
          });
          
          // 强制选中第一个评估者，确保跨case切换时能正确触发子组件加载
          if (this.evaluators.length > 0) {
            this.selectEvaluator(this.evaluators[0]);
          }
          console.log(`成功加载用户 ${this.username} 的医生:`, this.evaluators);
        } else {
          console.error('加载医生失败:', data.error);
        }
      } catch (error) {
        console.error('加载医生请求失败:', error);
      } finally {
        this.loading = false;
      }
    },

    // 获取可用的cases列表
    async loadAvailableCases() {
      try {
        const response = await fetch(`/api/evaluation/available-cases?username=${this.username}`);
        if (response.ok) {
          const data = await response.json();
          if (data.status === 'success' && data.cases) {
            this.caseNames = data.cases.map(c => `case${c}`);
          }
        }
      } catch (error) {
        console.error('获取可用cases失败:', error);
        // 如果后端不支持，使用默认cases
        this.caseNames = ['case8', 'case9'];
      }
    },

    // 处理上一个case
    handlePrevCase() {
      if (this.currentCaseIndex > 0) {
        this.currentCaseIndex--;
        this.switchToCase();
      }
    },

    // 处理下一个case
    handleNextCase() {
      if (this.currentCaseIndex < this.caseNames.length - 1) {
        this.currentCaseIndex++;
        this.switchToCase();
      }
    },

    // 切换到指定case
    async switchToCase() {
      const caseName = this.caseNames[this.currentCaseIndex];
      
      try {
        await fetch('/api/evaluation/navigate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            username: this.username,
            direction: 'jump', // 这里简单起见可以用 new_index 或者其他逻辑，
            // 但后端 navigate 原本只支持 next/previous
            // 我们直接让后端更新到指定的 index 比较稳妥
            new_index: this.currentCaseIndex 
          })
        });
      } catch (e) {
        console.error('切换Case失败:', e);
      }

      // 通知父组件case已改变
      this.$emit('case-changed', {
        case_name: caseName,
        current_index: this.currentCaseIndex
      });
    },

    selectEvaluator(evaluator) {
      this.selectedEvaluator = evaluator;
      // 向父组件发送选中的评估者信息
      this.$emit('evaluator-selected', {
        caseId: this.currentCaseId,
        evaluator: evaluator
      });
    },

    // 检查case的排序状态（简化版本）
    async checkCaseSortingStatus() {
      console.log('检查case排序状态，currentCaseId:', this.currentCaseId);
      // 在简化版本中，这个方法主要用于兼容性，不再处理复杂的排序逻辑
      // 直接加载评估者列表即可
    }
  },
  watch: {
    currentCaseId(newCaseId) {
      console.log('currentCaseId 变化:', newCaseId);
      this.loadEvaluators();
    },
    username(newUsername) {
      console.log('username 变化:', newUsername);
      if (newUsername) {
        this.loadEvaluators();
      }
    }
  },
  mounted() {
    console.log('SectionA 挂载');
    this.loadEvaluators();
  }
};
</script>

<style lang="less" scoped>
.content {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: #ffffff;
  padding: clamp(8px, 1.5vw, 16px);
  box-sizing: border-box;
  position: relative;
}

// 保存通知
.save-notification {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1000;
  animation: slideIn 0.3s ease-out;

  .notification-content {
    display: flex;
    align-items: center;
    gap: 8px;
    background-color: #4caf50;
    color: white;
    padding: 12px 16px;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    font-size: clamp(12px, 1vw, 16px);
  }

  .notification-icon {
    font-weight: bold;
    font-size: clamp(14px, 1.2vw, 18px);
  }
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

// 标题和按钮区域
.header-controls {
  margin-bottom: clamp(8px, 1.5vw, 16px);
}

.case-navigation {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: clamp(8px, 1.5vw, 12px);
  flex-wrap: wrap;
  
  .nav-btn {
    padding: clamp(6px, 0.8vw, 10px) clamp(10px, 1.5vw, 14px);
    font-size: clamp(12px, 0.9vw, 14px);
    border: 1px solid #ddd;
    background-color: #f5f5f5;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap;
    
    &:hover:not(:disabled) {
      background-color: #e0e0e0;
      border-color: #999;
    }
    
    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      background-color: #f0f0f0;
    }
  }

  .case-label {
    flex: 1;
    text-align: center;
    font-weight: bold;
    font-size: clamp(13px, 0.95vw, 15px);
    color: #333;
    min-width: 100px;
  }
}

// 提示框样式
.instruction-box {
  display: flex;
  align-items: flex-start;
  gap: clamp(8px, 1.5vw, 12px);
  padding: clamp(8px, 1vw, 12px);
  background-color: #f0f4f8;
  border-left: 3px solid #2196f3;
  border-radius: 4px;
  margin-bottom: clamp(8px, 1.5vw, 16px);
  
  .instruction-icon {
    font-size: clamp(16px, 1.5vw, 20px);
    flex-shrink: 0;
    line-height: 1.4;
  }
  
  .instruction-content {
    flex: 1;
  }
  
  .instruction-text {
    font-size: clamp(12px, 0.9vw, 14px);
    color: #555;
    line-height: 1.5;
  }
}

// 加载状态
.loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: clamp(13px, 0.95vw, 16px);
  color: #999;
}

// 医生列表容器
.evaluators-container {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: clamp(8px, 1.5vw, 12px);
  padding-right: 4px;
  
  // 自定义滚动条样式
  &::-webkit-scrollbar {
    width: 6px;
  }
  
  &::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 3px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 3px;
    
    &:hover {
      background: #a1a1a1;
    }
  }
}

// 医生卡片
.evaluator-card {
  display: flex;
  align-items: center;
  gap: clamp(8px, 1.5vw, 12px);
  padding: clamp(8px, 1vw, 12px);
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  background-color: #fafafa;
  flex-shrink: 0;
  
  &:hover {
    border-color: #2196f3;
    background-color: #f0f8ff;
    box-shadow: 0 2px 8px rgba(33, 150, 243, 0.15);
  }
  
  &.selected {
    border-color: #2196f3;
    background-color: #e3f2fd;
    box-shadow: 0 2px 8px rgba(33, 150, 243, 0.25);
    
    .evaluator-name {
      color: #1976d2;
      font-weight: 600;
    }
  }
}

.evaluator-avatar {
  flex-shrink: 0;
  width: clamp(32px, 5vw, 48px);
  height: clamp(32px, 5vw, 48px);
  border-radius: 50%;
  overflow: hidden;
  background-color: #e8eef7;
  display: flex;
  align-items: center;
  justify-content: center;
  
  .avatar-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.evaluator-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.evaluator-name {
  font-size: clamp(13px, 0.95vw, 15px);
  font-weight: 500;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.2s ease;
}

.evaluator-number {
  font-size: clamp(11px, 0.8vw, 13px);
  color: #999;
  font-weight: 400;
}

// 响应式设计
@media (max-width: 1024px) {
  .content {
    padding: clamp(6px, 1vw, 12px);
  }
  
  .evaluator-card {
    padding: clamp(6px, 0.8vw, 10px);
  }
}

@media (max-width: 768px) {
  .case-navigation {
    flex-direction: column;
    
    .nav-btn {
      width: 100%;
    }
  }
}

// 平滑过渡
.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s ease;
}

.notification-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.notification-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
</style>
       