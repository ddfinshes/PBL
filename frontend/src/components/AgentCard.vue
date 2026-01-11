<template>
  <div class="agent-card" :style="{ '--base-card-color': cardColor }">
    <!-- 核心卡片背景 -->
    <div class="agent-card-bg" :style="{ backgroundColor: 'var(--base-card-color)' }"></div>

    <!-- 顶部身份信息区域 -->
    <header class="identity-header">
      <div class="identity-info-left">
        <!-- 头像选择区域 -->
        <el-popover
          placement="bottom"
          :width="160"
          trigger="click"
          popper-style="background-color: #DFE9FF; border-radius: 12px; border: 1px solid #B0C4DE; padding: 10px;"
        >
          <template #reference>
            <div 
              class="avatar-icon cursor-pointer hover:scale-105 transition-transform shadow-sm" 
              :style="{ backgroundImage: `url('/avatar/${modelValue.avatar || 'avatar1.png'}')` }"
              title="点击更换头像"
            ></div>
          </template>
          <div class="avatar-selector-grid">
            <div 
              v-for="i in 4" 
              :key="i" 
              class="avatar-option"
              :class="{ 'is-active': modelValue.avatar === `avatar${i}.png` }"
              @click="modelValue.avatar = `avatar${i}.png`"
            >
              <img :src="`/avatar/avatar${i}.png`" class="avatar-option-img" />
            </div>
          </div>
        </el-popover>
        
        <!-- 姓名交互区域 -->
        <div class="name-interactive-area">
          <div v-if="editingField !== 'name'" 
               @click.stop="editingField = 'name'" 
               class="name-display"
               :class="{'is-empty': !modelValue.name}">
            {{ modelValue.name || '请输入' }}
          </div>
          <input v-else 
                 v-model="modelValue.name" 
                 placeholder="请输入"
                 @blur="editingField = null" 
                 @keyup.enter="editingField = null"
                 v-focus
                 class="name-input" />
        </div>
      </div>

      <!-- 右侧元数据列 (年龄, 专业) -->
      <div class="metadata-column">
        <div class="meta-item-box" @click.stop="editingField = 'age'">
          <span class="meta-label">年龄:</span>
          <div v-if="editingField !== 'age'" class="meta-value" :class="{'is-empty': !modelValue.age}">
            {{ modelValue.age || '请输入' }}
          </div>
          <input v-else 
                 v-model="modelValue.age" 
                 placeholder="请输入"
                 @blur="editingField = null" 
                 @keyup.enter="editingField = null"
                 v-focus
                 class="meta-input" />
        </div>

        <div class="meta-item-box" @click.stop="editingField = 'major'">
          <span class="meta-label">专业:</span>
          <div v-if="editingField !== 'major'" class="meta-value" :class="{'is-empty': !modelValue.major}">
            {{ modelValue.major || '请输入' }}
          </div>
          <input v-else 
                 v-model="modelValue.major" 
                 placeholder="请输入"
                 @blur="editingField = null" 
                 @keyup.enter="editingField = null"
                 v-focus
                 class="meta-input" />
        </div>
      </div>

      <!-- 删除按钮 -->
      <button class="delete-agent-btn" @click.stop="$emit('delete')" title="删除此角色">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M18 6L6 18M6 6l12 12"></path>
        </svg>
      </button>
    </header>

    <!-- 主体内容容器 -->
    <div class="card-content-wrapper">
      
      <!-- 知识背景区块 -->
      <section class="panel-section knowledge-panel">
        <h3 class="panel-title">知识背景分类</h3>
        

        <div class="panel-body row-layout">
          <!-- 左侧：未分类知识点 -->
          <div class="theoretical-tags-container"
               @dragover.prevent
               @drop="onDrop($event, 'unclassified')">
             <div v-for="(item, index) in modelValue.unclassifiedKnowledge" 
                  :key="index"
                  draggable="true"
                  @dragstart="onDragStart($event, item, 'unclassified')"
                  class="theory-tag">
               {{ item }}
             </div>
             <div v-if="!modelValue.unclassifiedKnowledge?.length" class="empty-hint">暂无待分类知识点</div>
          </div>

          <!-- 右侧：三个分类框 (纵向排列) -->
          <div class="classification-zones-grid">
            <!-- Competent (Good) -->
            <div class="drop-zone good-zone"
                 :class="{'is-dragging': dragOverField === 'competent'}"
                 @dragover.prevent="dragOverField = 'competent'"
                 @dragleave="dragOverField = null"
                 @drop="onDrop($event, 'competent')">
              <div class="zone-label good-text">掌握程度：高</div>
              <div class="items-list">
                <div v-for="(item, idx) in modelValue.classifiedKnowledge.competent" :key="idx"
                     draggable="true" @dragstart="onDragStart($event, item, 'competent')"
                     class="mini-item good-bg">
                  {{ item }}
                </div>
              </div>
            </div>

            <!-- Novice (Medium) -->
            <div class="drop-zone medium-zone"
                 :class="{'is-dragging': dragOverField === 'novice'}"
                 @dragover.prevent="dragOverField = 'novice'"
                 @dragleave="dragOverField = null"
                 @drop="onDrop($event, 'novice')">
              <div class="zone-label medium-text">掌握程度：中</div>
              <div class="items-list">
                <div v-for="(item, idx) in modelValue.classifiedKnowledge.novice" :key="idx"
                     draggable="true" @dragstart="onDragStart($event, item, 'novice')"
                     class="mini-item medium-bg">
                  {{ item }}
                </div>
              </div>
            </div>

            <!-- Layman (Bad) -->
            <div class="drop-zone bad-zone"
                 :class="{'is-dragging': dragOverField === 'layman'}"
                 @dragover.prevent="dragOverField = 'layman'"
                 @dragleave="dragOverField = null"
                 @drop="onDrop($event, 'layman')">
              <div class="zone-label bad-text">掌握程度：低</div>
              <div class="items-list">
                <div v-for="(item, idx) in modelValue.classifiedKnowledge.layman" :key="idx"
                     draggable="true" @dragstart="onDragStart($event, item, 'layman')"
                     class="mini-item bad-bg">
                  {{ item }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 认知倾向区块 -->
      <section class="panel-section cognitive-panel" :class="{'is-delete-mode': isDeleteMode}">
        <h3 class="panel-title">认知倾向</h3>
        
        <!-- 暂且注释掉删除模式按钮，由排序和直选逻辑替代
        <div class="header-actions">
          <span v-if="isDeleteMode" class="delete-mode-hint animate-pulse">正在进入删除模式...再次点击取消</span>
          <button class="reset-selection-btn" 
                  @click="toggleDeleteMode" 
                  :class="{'is-active': isDeleteMode}"
                  title="切换删除模式"></button>
        </div>
        -->

        <div class="orientation-labels">
           <div v-for="(label, key) in cognitiveLabels" :key="key" class="label-text">
             {{ label }}
           </div>
        </div>

        <div class="options-grid">
          <div v-for="(allOpts, category) in cognitiveOptions" :key="category" class="option-column">
            <!-- 已选中部分（支持排序） -->
            <div v-for="(opt, idx) in modelValue.cognitive[category]" :key="'sel-' + opt" 
                 class="selectable-box is-active"
                 :style="{ backgroundColor: getOptionColor(opt) }"
                 @click="toggleCognitive(category, opt)">
              <div class="box-content-row">
                 <span class="box-text">{{ subDimensionTranslations[opt] || opt }}</span>
                 <div class="order-controls" v-if="!isDeleteMode" @click.stop>
                    <button class="order-btn" @click="moveItem(category, idx, -1)" v-if="idx > 0">▲</button>
                    <button class="order-btn" @click="moveItem(category, idx, 1)" v-if="idx < modelValue.cognitive[category].length - 1">▼</button>
                 </div>
              </div>
            </div>

            <!-- 未选中推荐部分（排到第一位/优先展示） -->
            <div v-for="opt in getSortedOptionsForCategory(category).recommended" :key="'rec-' + opt" 
                 class="selectable-box is-related"
                 :style="{ borderColor: getOptionColor(opt), color: getOptionColor(opt) }"
                 @click="toggleCognitive(category, opt)">
              {{ subDimensionTranslations[opt] || opt }}
            </div>

            <!-- 未选中其他部分 -->
            <div v-for="opt in getSortedOptionsForCategory(category).others" :key="'other-' + opt" 
                 class="selectable-box is-inactive"
                 @click="toggleCognitive(category, opt)">
              {{ subDimensionTranslations[opt] || opt }}
            </div>
          </div>
        </div>

        <!-- 组合类型展示区域 -->
        <div class="archetypes-container">
          <span class="archetype-label">关联组合：</span>
           <div v-for="(info, name) in archetypes" :key="name" 
                class="archetype-tag"
                :class="{'is-highlighted': isRelatedToHighlighted(name)}"
                :style="{ backgroundColor: isRelatedToHighlighted(name) ? info.color : '' }"
                @click="selectedArchetype = {name, ...info}">
              {{ name }}
           </div>
        </div>

        <!-- 特征解释弹窗 -->
        <div v-if="selectedArchetype" class="type-modal-overlay" @click="selectedArchetype = null">
           <div class="type-modal-content" @click.stop>
              <h4 class="modal-title">{{ selectedArchetype.name }}</h4>
              <div class="modal-composition">
                 <div class="modal-sub-label">构成要素：</div>
                 <div class="comp-tags-flex">
                   <span v-for="item in selectedArchetype.composition" :key="item" class="mini-comp-tag">
                      {{ subDimensionTranslations[item] || item }}
                   </span>
                 </div>
              </div>
              <div class="modal-description">
                 <div class="modal-sub-label">特征描述：</div>
                 <p class="modal-desc-text">{{ selectedArchetype.description }}</p>
              </div>
              <button class="close-modal-btn" @click="selectedArchetype = null">我知道了</button>
           </div>
        </div>
      </section>

      <!-- 社交与学习综合区块 -->
      <section class="panel-section combined-panel">
        <div class="combined-content-row">
          <!-- 左侧：社交属性 (2/3) -->
          <div class="social-side-column">
            <h3 class="panel-title mb-1">社交属性</h3>
            <div class="social-side-body">
              <div class="sliders-sub-column">
                <!-- 言语自信度 -->
                <div class="level-select-group">
                   <div class="level-title">言语自信度</div>
                   <div class="level-options">
                     <div v-for="lv in ['low', 'medium', 'high']" :key="lv"
                          class="level-btn"
                          :class="{'is-active': modelValue.social.confidence === lv}"
                          @click="modelValue.social.confidence = lv">
                       {{ levelTranslations[lv] }}
                     </div>
                   </div>
                </div>
                <!-- 语言正式度 -->
                <div class="level-select-group mt-1">
                   <div class="level-title">语言正式度</div>
                   <div class="level-options">
                     <div v-for="lv in ['low', 'medium', 'high']" :key="lv"
                          class="level-btn"
                          :class="{'is-active': modelValue.social.register === lv}"
                          @click="modelValue.social.register = lv">
                       {{ levelTranslations[lv] }}
                     </div>
                   </div>
                </div>
              </div>

              <div class="role-sub-column">
                <div class="role-selection-horizontal">
                   <div v-for="role in interactionRoles" :key="role.value" class="role-choice-item" @click="modelValue.social.role = role.value">
                      <div class="role-illus" :style="{backgroundImage: `url('/${role.icon}')`}"></div>
                      <div class="role-name-text">{{ role.name }}</div>
                      <div class="mini-checkbox" :class="{'is-checked': modelValue.social.role === role.value}">
                        <span v-if="modelValue.social.role === role.value" class="check-mark">✓</span>
                      </div>
                   </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 分割线 -->
          <div class="vertical-divider"></div>

          <!-- 右侧：学习可塑性 (1/3) -->
          <div class="learning-side-column">
            <h3 class="panel-title mb-1">学习可塑性</h3>
            <div class="plasticity-vertical-options">
               <div v-for="lv in ['low', 'medium', 'high']" 
                    :key="lv"
                    class="p-level-card"
                    :class="{'is-active': modelValue.plasticity === lv}"
                    @click="modelValue.plasticity = lv">
                 <div class="p-level-name">{{ plasticityTranslations[lv] }}</div>
               </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  modelValue: { type: Object, required: true },
  cognitiveOptions: { type: Object, required: true },
  interactionRoles: { type: Array, required: true },
  cardColor: { type: String, default: '#CEDCFB' }
});

const emit = defineEmits(['update:modelValue', 'delete']);

const editingField = ref(null);
const dragOverField = ref(null);

// --- 认知倾向：中文翻译与 archetypes 字典 ---
const cognitiveLabels = {
  0: '注意力锚点',
  1: '推理起点',
  2: '因果结构'
};

const subDimensionTranslations = {
  'Patient Events': '患者事件',
  'Symptoms': '临床症状',
  'Social Cues': '社会线索',
  'Status': '患者状态',
  'Mechanism': '机制推演',
  'External Factors': '外部因素',
  'Risk Perception': '风险感知',
  'Familiarity Driven': '自身经验驱动',
  'Linear Causality': '线性因果',
  'Multi-Concurrent': '多重并发',
  'Cues-Driven': '心理-社会-环境',
  'Undefined': '未定义'
};

const levelTranslations = {
  'low': '低',
  'medium': '中',
  'high': '高'
};

const plasticityTranslations = {
  'low': '保守',
  'medium': '稳健',
  'high': '灵活'
};

// 手动添加区域！！！！！自定义
const archetypes = {
  "经验直觉型": {
    "composition": ["Patient Events", "Familiarity Driven", "Cues-Driven"],
    "color": "#7895CB",
    "description": "该型学生倾向于依靠直觉和患者呈现的表象进行快速判断，习惯于匹配过往经验而非深究病理机制。"
  },
  "系统生理型": {
    "composition": ["Symptoms", "Mechanism", "Linear Causality"],
    "color": "#6EA6B3",
    "description": "该型学生擅长从生理机制出发，通过逻辑严密的线性因果链条来推导病情，注重理论知识的系统应用。"
  },
  "风险感知型": {
    "composition": ["Social Cues", "Risk Perception", "Multi-Concurrent"],
    "color": "#8A87C1",
    "description": "该型学生对环境和社会线索敏感，在推理过程中会优先考虑潜在风险和多重并发因素的影响。"
  }
};

const getOptionColor = (opt) => {
  // 查找该 opt 属于哪个 Archetype
  for (let name in archetypes) {
    if (archetypes[name].composition.includes(opt)) {
      return archetypes[name].color;
    }
  }
  return "#8095CA"; // 统一蓝色
};

const selectedArchetype = ref(null);
const isDeleteMode = ref(false);

const toggleDeleteMode = () => {
  isDeleteMode.value = !isDeleteMode.value;
};

const resetCognitive = () => {
  props.modelValue.cognitive[0] = [];
  props.modelValue.cognitive[1] = [];
  props.modelValue.cognitive[2] = [];
};

const toggleCognitive = (category, opt) => {
  if (!Array.isArray(props.modelValue.cognitive[category])) {
    props.modelValue.cognitive[category] = [props.modelValue.cognitive[category]];
  }
  
  const index = props.modelValue.cognitive[category].indexOf(opt);
  
  if (isDeleteMode.value) {
    if (index !== -1) {
      props.modelValue.cognitive[category].splice(index, 1);
    }
  } else {
    if (index === -1) {
      // 选中逻辑：如果点击的维度属于某个 Archetype，则该 Archetype 的所有成员进入“选中候选/高亮”或直接选中
      // 根据用户要求：直接进入选中模式
      props.modelValue.cognitive[category].push(opt);
      
      // 联动：查找包含此 opt 的所有组合，并把它们的成员也设为选中（如果还没选中的话）
      for (let name in archetypes) {
        if (archetypes[name].composition.includes(opt)) {
          archetypes[name].composition.forEach(comp => {
            // 需要找到这个 comp 属于哪个 category
            for (let catKey in props.cognitiveOptions) {
              if (props.cognitiveOptions[catKey].includes(comp)) {
                if (!props.modelValue.cognitive[catKey].includes(comp)) {
                  props.modelValue.cognitive[catKey].push(comp);
                }
              }
            }
          });
        }
      }
    } else {
      props.modelValue.cognitive[category].splice(index, 1);
    }
  }
};

const moveItem = (category, index, direction) => {
  const list = props.modelValue.cognitive[category];
  if (direction === -1 && index > 0) {
    [list[index], list[index - 1]] = [list[index - 1], list[index]];
  } else if (direction === 1 && index < list.length - 1) {
    [list[index], list[index + 1]] = [list[index + 1], list[index]];
  }
};

const getSortedOptionsForCategory = (category) => {
  const options = props.cognitiveOptions[category] || [];
  const selected = props.modelValue.cognitive[category] || [];
  
  // 1. 已经选中的（按选中的顺序/用户排序后的顺序）
  // 2. 被推荐的（属于已选中项相关组合的成员）
  // 3. 其他
  
  const recommended = [];
  selected.forEach(s => {
    for (let name in archetypes) {
      if (archetypes[name].composition.includes(s)) {
        archetypes[name].composition.forEach(c => {
          if (options.includes(c) && !selected.includes(c) && !recommended.includes(c)) {
            recommended.push(c);
          }
        });
      }
    }
  });

  const remaining = options.filter(o => !selected.includes(o) && !recommended.includes(o));
  
  return {
    selected: selected,
    recommended: recommended,
    others: remaining
  };
};

const isOptionRelated = (opt) => {
  for (let name in archetypes) {
    if (isRelatedToHighlighted(name)) {
      if (archetypes[name].composition.includes(opt)) return true;
    }
  }
  return false;
};

const isRelatedToHighlighted = (typeName) => {
  const type = archetypes[typeName];
  if (!type) return false;
  
  // 检查当前选中的任何一个子维度是否在组合中
  for (let cat in props.modelValue.cognitive) {
    const selectedList = Array.isArray(props.modelValue.cognitive[cat]) 
      ? props.modelValue.cognitive[cat] 
      : [props.modelValue.cognitive[cat]];
      
    if (selectedList.some(item => type.composition.includes(item))) return true;
  }
  return false;
};

// --- 拖拽逻辑实现 ---
const onDragStart = (e, item, source) => {
  e.dataTransfer.dropEffect = 'move';
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', item);
  e.dataTransfer.setData('sourceCategory', source);
};

const onDrop = (e, targetCategory) => {
  dragOverField.value = null;
  const item = e.dataTransfer.getData('text/plain');
  const sourceCategory = e.dataTransfer.getData('sourceCategory');
  
  if (!item || sourceCategory === targetCategory) return;

  if (sourceCategory === 'unclassified') {
    props.modelValue.unclassifiedKnowledge = props.modelValue.unclassifiedKnowledge.filter(i => i !== item);
  } else {
    props.modelValue.classifiedKnowledge[sourceCategory] = props.modelValue.classifiedKnowledge[sourceCategory].filter(i => i !== item);
  }

  if (targetCategory === 'unclassified') {
    if (!props.modelValue.unclassifiedKnowledge) props.modelValue.unclassifiedKnowledge = [];
    props.modelValue.unclassifiedKnowledge.push(item);
  } else {
    if (!props.modelValue.classifiedKnowledge[targetCategory]) props.modelValue.classifiedKnowledge[targetCategory] = [];
    props.modelValue.classifiedKnowledge[targetCategory].push(item);
  }
};

const vFocus = {
  mounted: (el) => {
    el.focus();
    if (el.tagName === 'INPUT') el.select();
  }
};

const resetEditing = () => {
  editingField.value = null;
};

defineExpose({ resetEditing });
</script>

<style scoped>
/* =========================================
   1. 基础布局 & 卡片容器 (Layout & Base)
   ========================================= */
.agent-card {
  position: relative;
  width: 100%;
  max-width: 100%;
  height: auto;
  min-height: 900px;
  flex-shrink: 0;
  transition: all 0.3s ease;
  user-select: none;
  margin-bottom: 20px;
}

.agent-card-bg {
  position: absolute;
  inset: 0;
  background-color: #CEDCFB;
  box-shadow: 0 4px 4px rgba(0, 0, 0, 0.25);
  border-radius: 20px;
  z-index: 0;
}

.card-content-wrapper {
  position: relative;
  z-index: 10;
  padding: 1rem 1rem 1.5rem; /* 减小上方 padding (1.5rem -> 1rem) */
  height: calc(100% - 70px); /* 同步头部高度的修改 (80px -> 70px) */
  display: flex;
  flex-direction: column;
  gap: 1rem; /* 压缩内部模块间的间距 (1.5rem -> 1rem) */
}

/* =========================================
   2. 身份信息部分 (Identity Header)
   ========================================= */
.identity-header {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 2rem 0; /* 减小上方间距，使其更贴近顶端 */
  height: 70px; /* 压缩头部高度 */
}

.delete-agent-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  color: #6C6565;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  z-index: 30;
}

.delete-agent-btn:hover {
  background: #ff4d4f;
  color: white;
  transform: rotate(90deg);
  box-shadow: 0 2px 8px rgba(255, 77, 79, 0.3);
}

.identity-info-left {
  display: flex;
  align-items: center;
  gap: 1.5rem; /* gap-6 */
}

.avatar-selector-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  padding: 5px;
}

.avatar-option {
  cursor: pointer;
  border: 2px solid transparent;
  border-radius: 8px;
  padding: 2px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-option:hover {
  background-color: rgba(99, 85, 191, 0.1);
  transform: scale(1.05);
}

.avatar-option.is-active {
  border-color: #8095CA;
  background-color: rgba(128, 149, 202, 0.2);
}

.avatar-option-img {
  width: 60px;
  height: 60px;
  object-fit: contain;
}

.avatar-icon {
  width: 45px;
  height: 45px;
  background-size: contain;
  background-repeat: no-repeat;
  border-radius: 50%; /* 圆形头像 */
  background-color: white;
}

.name-interactive-area {
  min-width: 160px;
}

.name-display {
  font-weight: bold;
  font-size: 18px;
  color: #6C6565;
  cursor: text;
  padding: 0 0.5rem;
  border-radius: 0.25rem;
  transition: background-color 0.2s;
}

.name-display:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.name-display.is-empty {
  font-style: italic;
  opacity: 0.5;
  font-weight: normal;
}

.name-input {
  font-weight: bold;
  font-size: 18px;
  color: #6C6565;
  background-color: rgba(255, 255, 255, 0.5);
  border: none;
  outline: none;
  border-radius: 0.25rem;
  padding: 0 0.5rem;
  width: 100%;
}

.metadata-column {
  display: flex;
  flex-direction: column;
  gap: 0.75rem; /* gap-3 */
}

.meta-item-box {
  width: 140px; /* 缩小宽度 */
  height: 28px;
  background-color: rgba(255, 255, 255, 0.35);
  border-radius: 14px;
  display: flex;
  align-items: center;
  padding: 0 0.75rem;
  cursor: text;
}

.meta-label {
  font-size: 13px;
  font-weight: bold;
  color: #6C6565;
  margin-right: 0.5rem;
}

.meta-value {
  font-size: 13px;
  color: #6C6565;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta-value.is-empty {
  font-style: italic;
  opacity: 0.5;
}

.meta-input {
  width: 100%;
  background: transparent;
  border: none;
  font-size: 13px;
  outline: none;
  color: #6C6565; /* 确保输入文字可见 */
}

/* =========================================
   3. 通用面板组件 (Panel Section)
   ========================================= */
.panel-section {
  background-color: rgba(255, 255, 255, 0.45);
  box-shadow: 0 4px 4px rgba(0, 0, 0, 0.15);
  border-radius: 20px;
  padding: 0.2rem 0rem 0.3rem; /* 更加紧凑的内边距 */
  display: flex;
  flex-direction: column;
}
.panel-section > * + * {
  margin-top: 2px; /* 极小间距，消除标题与内容间的空隙 */
}

.panel-title {
  margin: 0;
  padding: 0;
  font-size: 16px;
  font-weight: bold;
  text-align: center;
  line-height: 1.2;
  color: #000;
  margin-bottom: 0px;
}


.panel-body.row-layout {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem; /* 减小间距以适应窄屏 */
}

/* =========================================
   4. 知识背景部分 (Knowledge Background)
   ========================================= */
.knowledge-panel {
  height: 350px;
}

.competence-legend {
  display: flex;
  gap: 1.5rem;
  margin-left: 0.5rem;
  margin-bottom: 1rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.legend-dot {
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 2px;
}

.legend-dot.good   { background-color: #7fbf4c; }
.legend-dot.medium { background-color: #FFB74D; }
.legend-dot.bad    { background-color: #fc8d59; }

.legend-text {
  font-size: 12px;
}

.theoretical-tags-container {
  flex: 1.2;
  height: 280px;
  background-color: rgba(255, 255, 255, 0.4);
  border-radius: 12px;
  padding: 0.75rem;
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 0.75rem;
  overflow-y: auto;
  border: 1px dashed rgba(0, 0, 0, 0.1);
}

.theory-tag {
  background-color: #717171;
  border: 1px solid #A5A8AC;
  padding: 0.5rem 1rem;
  border-radius: 9999px;
  font-size: 13px;
  color: #fff;
  cursor: move;
  transition: background-color 0.2s;
  white-space: nowrap;
}

.theory-tag:hover {
  background-color: #ccc;
}

.empty-hint {
  font-size: 12px;
  color: #9CA3AF;
  margin: auto;
}

.classification-zones-grid {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.drop-zone {
  height: 85px;
  border: none;                  /* 去掉边框 */
  border-radius: 14px;           /* 更像 card，而不是框 */
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  transition: background-color 0.15s ease, transform 0.15s ease;
  overflow: hidden;
}


.zone-label {
  font-size: 11px;
  font-weight: bold;
  margin-bottom: 0.5rem;
}

.items-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  width: 100%;
  overflow-y: auto;
  align-content: flex-start;
  padding: 0.25rem;
}

/* 分类框色彩变体 */
/* 分类框色彩变体 - 重构配色 */

/* 分类框色彩变体（最终版） */

.good-zone {
  background-color: #7fbf4c;
}

.medium-zone {
  background-color: #ffffbf;
}

.bad-zone {
  background-color: #fc8d59;
}


.good-zone.is-dragging {
  background-color: #6da241; /* slightly darker */
}

.medium-zone.is-dragging {
  background-color: #f2f2a6;
}

.bad-zone.is-dragging {
  background-color: #e57e4f;
}


.good-text {
  color: #000000;   /* 浅绿偏白 */
}

.medium-text {
  color: #7a7a3a;   /* 暗金黄，避免白色不清晰 */
}

.bad-text {
  color: #ffffff;   /* 浅橘白 */
}



.mini-item {
  font-size: 11px;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  white-space: nowrap;
  max-width: 100%;
  background-color: rgba(255, 255, 255, 0.35);
  color: rgba(0, 0, 0, 0.75);
}


.good-bg   { background-color: #c4f19f; color: #000000;}
.medium-bg { background-color: #f2f2a6; color: #000000;}
.bad-bg    { background-color: #ffbfa1; color: #000; }

/* =========================================
   5. 认知倾向部分 (Cognitive Orientation)
   ========================================= */
.cognitive-panel {
  height: 360px;
  position: relative;
  margin-bottom: 0.2rem;
  margin-top: 0;
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .5; }
}

.orientation-labels {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  column-gap: 1rem;
  margin-top: 5px; /* 紧凑排列 */
  padding: 0 0.5rem;
}

.label-text {
  text-align: center;
  font-size: 12px;
  font-weight: bold;
  color: #4A4A4A;
}

.options-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-top: 5px; /* 紧凑排列 */
  height: 200px;
  padding: 0 1rem;
}

.option-column {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.selectable-box {
  background-color: rgba(255, 255, 255, 0.45);
  border-radius: 8px;
  min-height: 32px;
  font-size: 12px;
  padding: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.selectable-box:hover {
  background-color: #C5C9D4;
}

.selectable-box.is-active {
  background-color: #8095CA;
  color: white;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
  font-weight: bold;
}

.box-content-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.box-text {
  flex: 1;
}

.order-controls {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-left: 4px;
}

.order-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  font-size: 8px;
  padding: 1px 3px;
  border-radius: 2px;
  cursor: pointer;
}

.order-btn:hover {
  background: rgba(255, 255, 255, 0.4);
}

.selectable-box.is-inactive {
  color: #8C8C8C;
}

.selectable-box.is-related {
  border: 1.5px dashed #FFB74D;
  background-color: rgba(255, 183, 77, 0.1);
  color: #E67E22;
}

/* 组合类型样式 */
.archetypes-container {
  margin-top: 2rem;
  padding: 0 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.archetype-label {
  font-size: 13px;
  font-weight: bold;
  color: #6C6565;
}

.archetype-tag {
  font-size: 12px;
  padding: 0.25rem 0.75rem;
  background-color: #ECEFF4;
  border: 1px solid #D1D9E6;
  border-radius: 4px;
  color: #7F8C8D;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.archetype-tag.is-highlighted {
  border-color: #F39C12;
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  font-weight: bold;
}

/* 弹窗样式 */
.type-modal-overlay {
  position: absolute;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  border-radius: 20px;
}

.type-modal-content {
  background-color: white;
  width: 80%;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.2);
  display: flex;
  flex-direction: column;
}

.modal-title {
  text-align: center;
  font-weight: bold;
  font-size: 18px;
  margin-bottom: 1rem;
  color: #2C3E50;
}

.modal-sub-label {
  font-size: 11px;
  color: #95A5A6;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.comp-tags-flex {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.mini-comp-tag {
  font-size: 11px;
  background-color: #F0F3F7;
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  color: #34495E;
}

.modal-desc-text {
  font-size: 13px;
  line-height: 1.6;
  color: #34495E;
  margin-bottom: 1.5rem;
}

.close-modal-btn {
  background-color: #8095CA;
  color: white;
  border: none;
  padding: 0.6rem;
  border-radius: 6px;
  font-weight: bold;
  cursor: pointer;
  transition: background-color 0.2s;
}

.close-modal-btn:hover {
  background-color: #6D8DBE;
}

/* =========================================
   6. 社交与学习综合部分 (Combined Social & Learning)
   ========================================= */
.combined-panel {
  height: 250px;
  padding: 1.25rem;
}

.combined-content-row {
  display: flex;
  height: 100%;
  gap: 1.5rem;
}

.social-side-column {
  flex: 2; /* 2/3 width */
  display: flex;
  flex-direction: column;
}

.social-side-body {
  flex: 1;
  display: flex;
  gap: 2rem;
  align-items: center;
}

.sliders-sub-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.5rem;
}

.level-select-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.level-title {
  font-size: 13px;
  font-weight: bold;
  color: #6C6565;
}

.level-options {
  display: flex;
  background-color: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 20px;
  padding: 2px;
  width: fit-content;
}

.level-btn {
  padding: 3px 12px;
  font-size: 11px;
  border-radius: 18px;
  cursor: pointer;
  transition: all 0.2s;
  color: #7F8C8D;
}

.level-btn.is-active {
  background-color: #8095CA;
  color: white;
  font-weight: bold;
}

.role-sub-column {
  flex: 1.2;
}

.role-selection-horizontal {
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 0.5rem;
  background-color: rgba(255, 255, 255, 0.4);
  border-radius: 12px;
}

.role-choice-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  width: 50px;
  height: 90px;
  justify-content: center;
  transition: all 0.2s;
}

.role-illus {
  width: 2rem;
  height: 2rem;
  background-size: contain;
  background-repeat: no-repeat;
  margin-bottom: 0.4rem;
  transition: transform 0.2s;
}

.role-choice-item:hover .role-illus {
  transform: scale(1.1);
}

.role-name-text {
  font-size: 11px;
  color: #6C6565;
  margin-bottom: 0.3rem;
  font-weight: bold;
}

.mini-checkbox {
  width: 14px;
  height: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.mini-checkbox.is-checked {
  background-color: #8095CA;
  border-color: transparent;
}

.check-mark {
  color: white;
  font-size: 10px;
}

/* 分割线 */
.vertical-divider {
  width: 1px;
  background: linear-gradient(to bottom, transparent, #B0C4DE, transparent);
  margin: 0.5rem 0;
}

.learning-side-column {
  flex: 1; /* 1/3 width */
  display: flex;
  flex-direction: column;
}

.plasticity-vertical-options {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.75rem;
}

.p-level-card {
  width: 100%;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(255, 255, 255, 0.45);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  font-size: 12px;
  color: #7F8C8D;
  cursor: pointer;
  transition: all 0.2s;
}

.p-level-card.is-active {
  background-color: #8095CA;
  border-color: #8095CA;
  color: white;
  font-weight: bold;
  box-shadow: 0 2px 4px rgba(128, 149, 202, 0.3);
}

.p-level-card:hover:not(.is-active) {
  background-color: #F8F9FB;
}

/* =========================================
   8. 滚动条美化 (Scrollbars)
   ========================================= */
.theoretical-tags-container::-webkit-scrollbar,
.items-list::-webkit-scrollbar {
  width: 4px;
}
.theoretical-tags-container::-webkit-scrollbar-track,
.items-list::-webkit-scrollbar-track {
  background: transparent;
}
.theoretical-tags-container::-webkit-scrollbar-thumb,
.items-list::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 10px;
}

/* =========================================
   9. Range Input Thumb Reset
   ========================================= */
input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 10px;
  height: 10px;
  background: #000;
  border-radius: 50%;
  cursor: pointer;
}
input[type="range"]::-moz-range-thumb {
  width: 10px;
  height: 10px;
  background: #000;
  border-radius: 50%;
  cursor: pointer;
  border: none;
}
</style>
