<template>
  <div class="login-container">
    <div class="login-card">
      <!-- Logo区域 -->
      <div class="logo-section">
        <div class="logo-container">
          <img src="@/assets/logo_red.svg" alt="Logo" class="red-logo" />
          <img src="@/assets/实验室logo.png" alt="实验室Logo" class="lab-logo" />
        </div>
      </div>
      
      <div class="login-header">
        <h3>我们是上海科技大学ViSeerLAB组，目前在探究多智能体模拟PBL教学。现诚邀您参与我们的评估实验！</h3>
      </div>
      
      <div class="login-form">
        <div class="input-group">
          <label for="username">姓名：</label>
          <input 
            id="username"
            v-model="username" 
            type="text" 
            placeholder="请输入您的姓名"
            @keyup.enter="startEvaluation"
            :class="{ 'error': showError && !username.trim() }"
          />
          <span v-if="showError && !username.trim()" class="error-message">请输入姓名</span>
        </div>
        
        <button 
          class="start-btn" 
          @click="startEvaluation"
          :disabled="!isFormValid"
        >
          开始作答
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LoginPage',
  data() {
    return {
      username: '',
      showError: false
    }
  },
  computed: {
    isFormValid() {
      return this.username.trim() !== '';
    }
  },
  methods: {
    startEvaluation() {
      if (!this.isFormValid) {
        this.showError = true;
        return;
      }
      
      this.showError = false;
      
      // ✅ 固定返回所有组
      const userInfo = {
        username: this.username.trim(),
        caseGroup: 'all'
      };
      
      // 存储用户信息
      localStorage.setItem('evaluation_username', userInfo.username);
      localStorage.setItem('evaluation_user_info', JSON.stringify(userInfo));
      
      // 触发事件
      this.$emit('start-evaluation', userInfo);
    }
  }
}
</script>

<style lang="less" scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 50%, #fdcb6e 100%);
  padding: 20px;
}

.login-card {
  background: white;
  border-radius: 15px;
  box-shadow: 0 18px 37px rgba(0, 0, 0, 0.15);
  padding: 74px;
  width: 100%;
  max-width: 590px;
  text-align: center;
}

.logo-section {
  margin-bottom: 24px;
}

.logo-container {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
  flex-wrap: wrap;
}

.lab-logo {
  height: 74px;
  width: auto;
  object-fit: contain;
}

.red-logo {
  height: 59px;
  width: auto;
  object-fit: contain;
}

.login-header {
  margin-bottom: 37px;
  
  h3 {
    color: #333;
    font-size: 21px;
    font-weight: 600;
    margin-bottom: 12px;
    line-height: 1.4;
  }
}

.login-form {
  .input-group {
    margin-bottom: 22px;
    text-align: left;
    
    label {
      display: block;
      margin-bottom: 9px;
      color: #333;
      font-weight: 500;
      font-size: 13px;
    }
    
    input {
      width: 100%;
      padding: 15px;
      border: 1px solid #e1e5e9;
      border-radius: 8px;
      font-size: 13px;
      transition: all 0.3s ease;
      box-sizing: border-box;
      
      &:focus {
        outline: none;
        border-color: #667eea;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
      }
      
      &.error {
        border-color: #ff4757;
      }
    }
    
    .error-message {
      color: #ff4757;
      font-size: 12px;
      margin-top: 8px;
      display: block;
    }
  }
  
  .start-btn {
    width: 100%;
    padding: 15px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    margin-top: 15px;
    
    &:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 6px 19px rgba(102, 126, 234, 0.3);
    }
    
    &:disabled {
      background: #ccc;
      cursor: not-allowed;
      transform: none;
      box-shadow: none;
    }
  }
}
</style>