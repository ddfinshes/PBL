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
              title="Click to change avatar"
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
        
        <!-- Name Interaction Area -->
        <div class="name-interactive-area">
          <div v-if="editingField !== 'name'" 
               @click.stop="editingField = 'name'" 
               class="name-display"
               :class="{'is-empty': !modelValue.name}">
            {{ modelValue.name || 'Enter Name' }}
          </div>
          <input v-else 
                 v-model="modelValue.name" 
                 placeholder="Enter Name"
                 @blur="editingField = null" 
                 @keyup.enter="editingField = null"
                 v-focus
                 class="name-input" />
        </div>
      </div>

      <!-- Right Side Metadata Column (Age, Major) -->
      <div class="metadata-column">
        <div class="meta-item-box" @click.stop="editingField = 'age'">
          <span class="meta-label">Age:</span>
          <div v-if="editingField !== 'age'" class="meta-value" :class="{'is-empty': !modelValue.age}">
            {{ modelValue.age || 'Enter Age' }}
          </div>
          <input v-else 
                 v-model="modelValue.age" 
                 placeholder="Enter Age"
                 @blur="editingField = null" 
                 @keyup.enter="editingField = null"
                 v-focus
                 class="meta-input" />
        </div>

        <div class="meta-item-box" @click.stop="editingField = 'major'">
          <span class="meta-label">Major:</span>
          <div v-if="editingField !== 'major'" class="meta-value" :class="{'is-empty': !modelValue.major}">
            {{ modelValue.major || 'Enter Major' }}
          </div>
          <input v-else 
                 v-model="modelValue.major" 
                 placeholder="Enter Major"
                 @blur="editingField = null" 
                 @keyup.enter="editingField = null"
                 v-focus
                 class="meta-input" />
        </div>
      </div>

      <!-- Delete Button -->
      <button class="delete-agent-btn" @click.stop="$emit('delete')" title="Delete this agent">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M18 6L6 18M6 6l12 12"></path>
        </svg>
      </button>
    </header>

    <!-- Main Content Container -->
    <div class="card-content-wrapper">
      <!-- Quick Profile Selector -->
      <div class="quick-profile-bar">
        <button
          class="quick-pill"
          :class="{ 'is-active': activeQuickProfile === 'good' }"
          @click="applyQuickProfile('good')"
        >
          Top Student
        </button>
        <button
          class="quick-pill"
          :class="{ 'is-active': activeQuickProfile === 'medium' }"
          @click="applyQuickProfile('medium')"
        >
          Average Student
        </button>
        <button
          class="quick-pill"
          :class="{ 'is-active': activeQuickProfile === 'bad' }"
          @click="applyQuickProfile('bad')"
        >
          Struggling Student
        </button>
      </div>
      
      <!-- Knowledge Background Section -->
      <section class="panel-section knowledge-panel">
        <h3 class="panel-title">Knowledge Base</h3>
        

        <div class="panel-body row-layout">
          <!-- Left: Unclassified Knowledge Points -->
          <div class="theoretical-tags-container"
               @dragover.prevent
               @drop="onDrop($event, 'unclassified')">
             <div v-for="(item, index) in modelValue.unclassifiedKnowledge" 
                  :key="index"
                  draggable="true"
                  @dragstart="onDragStart($event, item, 'unclassified')"
                  @dblclick="startEditKnowledge('unclassified', index, item)"
                  class="theory-tag group relative">
               <template v-if="editingKnowledge.category === 'unclassified' && editingKnowledge.index === index">
                 <input v-model="editingKnowledge.value" class="tag-input" v-focus @blur="finishEditKnowledge" @keyup.enter="finishEditKnowledge" />
               </template>
               <template v-else>
                 <span class="tag-text">{{ item }}</span>
                 <span class="delete-tag-btn opacity-0 group-hover:opacity-100 transition-opacity pointer-events-auto" 
                       @click.stop="deleteKnowledgeItem(item)">×</span>
               </template>
             </div>
             
             <!-- Add Knowledge Point Entry -->
             <div v-if="!isAddingKnowledge" 
                  class="add-theory-tag" 
                  @click="isAddingKnowledge = true" 
                  title="Customize and add knowledge points">+</div>
             <div v-else class="theory-tag editing">
               <input v-model="newKnowledgeName" 
                      class="tag-input" 
                      v-focus 
                      @blur="submitAddKnowledge" 
                      @keyup.enter="submitAddKnowledge" 
                      placeholder="New knowledge point..." />
             </div>

             <div v-if="!modelValue.unclassifiedKnowledge?.length && !isAddingKnowledge" class="empty-hint">No unclassified knowledge points</div>
          </div>

          <!-- Right: Three Classification Boxes (Vertical Layout) -->
          <div class="classification-zones-grid">
            <!-- Competent (Good) -->
            <div class="drop-zone good-zone"
                 :class="{'is-dragging': dragOverField === 'competent'}"
                 @dragover.prevent="dragOverField = 'competent'"
                 @dragleave="dragOverField = null"
                 @drop="onDrop($event, 'competent')">
              <div class="zone-label good-text">Good</div>
              <div class="items-list">
                <div v-for="(item, idx) in modelValue.classifiedKnowledge.competent" :key="idx"
                     draggable="true" @dragstart="onDragStart($event, item, 'competent')"
                     @dblclick="startEditKnowledge('competent', idx, item)"
                     class="mini-item good-bg group relative">
                  <template v-if="editingKnowledge.category === 'competent' && editingKnowledge.index === idx">
                    <input v-model="editingKnowledge.value" class="tag-input" v-focus @blur="finishEditKnowledge" @keyup.enter="finishEditKnowledge" />
                  </template>
                  <template v-else>
                    <span class="tag-text">{{ item }}</span>
                    <span class="delete-tag-btn mini opacity-0 group-hover:opacity-100 transition-opacity pointer-events-auto" 
                          @click.stop="deleteKnowledgeItem(item)">×</span>
                  </template>
                </div>
              </div>
            </div>

            <!-- Novice (Medium) -->
            <div class="drop-zone medium-zone"
                 :class="{'is-dragging': dragOverField === 'novice'}"
                 @dragover.prevent="dragOverField = 'novice'"
                 @dragleave="dragOverField = null"
                 @drop="onDrop($event, 'novice')">
              <div class="zone-label medium-text">Medium</div>
              <div class="items-list">
                <div v-for="(item, idx) in modelValue.classifiedKnowledge.novice" :key="idx"
                     draggable="true" @dragstart="onDragStart($event, item, 'novice')"
                     @dblclick="startEditKnowledge('novice', idx, item)"
                     class="mini-item medium-bg group relative">
                  <template v-if="editingKnowledge.category === 'novice' && editingKnowledge.index === idx">
                    <input v-model="editingKnowledge.value" class="tag-input" v-focus @blur="finishEditKnowledge" @keyup.enter="finishEditKnowledge" />
                  </template>
                  <template v-else>
                    <span class="tag-text">{{ item }}</span>
                    <span class="delete-tag-btn mini opacity-0 group-hover:opacity-100 transition-opacity pointer-events-auto" 
                          @click.stop="deleteKnowledgeItem(item)">×</span>
                  </template>
                </div>
              </div>
            </div>

            <!-- Layman (Bad) -->
            <div class="drop-zone bad-zone"
                 :class="{'is-dragging': dragOverField === 'layman'}"
                 @dragover.prevent="dragOverField = 'layman'"
                 @dragleave="dragOverField = null"
                 @drop="onDrop($event, 'layman')">
              <div class="zone-label bad-text">Bad</div>
              <div class="items-list">
                <div v-for="(item, idx) in modelValue.classifiedKnowledge.layman" :key="idx"
                     draggable="true" @dragstart="onDragStart($event, item, 'layman')"
                     @dblclick="startEditKnowledge('layman', idx, item)"
                     class="mini-item bad-bg group relative">
                  <template v-if="editingKnowledge.category === 'layman' && editingKnowledge.index === idx">
                    <input v-model="editingKnowledge.value" class="tag-input" v-focus @blur="finishEditKnowledge" @keyup.enter="finishEditKnowledge" />
                  </template>
                  <template v-else>
                    <span class="tag-text">{{ item }}</span>
                    <span class="delete-tag-btn mini opacity-0 group-hover:opacity-100 transition-opacity pointer-events-auto" 
                          @click.stop="deleteKnowledgeItem(item)">×</span>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Cognitive Tendency Section -->
      <section class="panel-section cognitive-panel" :class="{'is-delete-mode': isDeleteMode}">
        <h3 class="panel-title">Cognitive Orientation</h3>
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
                 @click="toggleCognitive(category, opt)">
              <div class="box-content-row">
                 <span class="box-text">{{ subDimensionTranslations[opt] || opt }}</span>
                 <div class="order-controls" v-if="!isDeleteMode" @click.stop>
                    <button class="order-btn" @click="moveItem(category, idx, -1)" v-if="idx > 0">▲</button>
                    <button class="order-btn" @click="moveItem(category, idx, 1)" v-if="idx < modelValue.cognitive[category].length - 1">▼</button>
                 </div>
              </div>
            </div>

            <!-- 未选中推荐部分（已精简） -->
            <div v-for="opt in getSortedOptionsForCategory(category).recommended" :key="'rec-' + opt" 
                 class="selectable-box is-related"
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
      </section>

      <!-- Social and Learning Integration Section -->
      <section class="panel-section combined-panel">
        <!-- Top Row: Social Attributes -->
        <h3 class="panel-title mb-1">Social-Interaction Style</h3>
        <div class="social-attributes-row">
          <!-- Left Column: Two Selection Groups -->
          <div class="social-left-column">
            <div class="social-item">
              <div class="level-title">Verbal Confidence</div>
              <div class="level-options">
                <div v-for="lv in ['low', 'medium', 'high']" :key="lv"
                     class="level-btn"
                     :class="{'is-active': modelValue.social.confidence === lv}"
                     @click="modelValue.social.confidence = lv">
                  {{ levelTranslations[lv] }}
                </div>
              </div>
            </div>

            <div class="social-item">
              <div class="level-title">Language Register</div>
              <div class="level-options">
                <div v-for="lv in ['low', 'medium', 'high']" :key="lv"
                     class="level-btn"
                     :class="{'is-active': modelValue.social.register === lv}"
                     @click="modelValue.social.register = lv">
                  {{ levelTranslations[lv] }}
                </div>
              </div>
            </div>

            <div class="social-item">
              <div class="level-title">Participation</div>
              <div class="level-options">
                <div v-for="lv in ['low', 'medium', 'high']" :key="lv"
                     class="level-btn"
                     :class="{'is-active': modelValue.social.participation === lv}"
                     @click="modelValue.social.participation = lv">
                  {{ levelTranslations[lv] }}
                </div>
              </div>
            </div>
          </div>

          <!-- Right Column: Role Selection -->
          <div class="social-right-column">
            <div class="role-selection-grid">
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

        <!-- Bottom Row: Learning Plasticity -->
        <h3 class="panel-title mb-1 mt-2">Learning Plasticity</h3>
        <div class="plasticity-horizontal-options">
          <div v-for="lv in ['low', 'medium', 'high']" 
               :key="lv"
               class="p-level-card"
               :class="{'is-active': modelValue.plasticity === lv}"
               @click="modelValue.plasticity = lv">
            <div class="p-level-name">{{ plasticityTranslations[lv] }}</div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, inject } from 'vue';

const props = defineProps({
  modelValue: { type: Object, required: true },
  cognitiveOptions: { type: Object, required: true },
  interactionRoles: { type: Array, required: true },
  cardColor: { type: String, default: '#CEDCFB' }
});

const emit = defineEmits(['update:modelValue', 'delete']);

const knowledgeActions = inject('knowledgeActions', {});

const editingField = ref(null);
const dragOverField = ref(null);

// 知识点编辑状态
const editingKnowledge = ref({ category: null, index: null, value: '' });

const startEditKnowledge = (category, index, value) => {
  editingKnowledge.value = { category, index, value };
};

const finishEditKnowledge = () => {
  if (editingKnowledge.value.category) {
    const { category, index, value } = editingKnowledge.value;
    let oldName = '';
    if (category === 'unclassified') {
      oldName = props.modelValue.unclassifiedKnowledge[index];
    } else {
      oldName = props.modelValue.classifiedKnowledge[category][index];
    }
    if (value && value !== oldName) {
      if (knowledgeActions.renameKnowledge) {
        knowledgeActions.renameKnowledge(oldName, value);
      }
    }
  }
  editingKnowledge.value = { category: null, index: null, value: '' };
};

// 新增知识点状态
const isAddingKnowledge = ref(false);
const newKnowledgeName = ref('');

const submitAddKnowledge = () => {
  if (newKnowledgeName.value) {
    if (knowledgeActions.addKnowledge) {
      knowledgeActions.addKnowledge(newKnowledgeName.value);
    }
  }
  isAddingKnowledge.value = false;
  newKnowledgeName.value = '';
};

const deleteKnowledgeItem = (item) => {
  if (knowledgeActions.deleteKnowledge) {
    knowledgeActions.deleteKnowledge(item);
  }
};

// 拖拽相关 - 用于存储拖拽的数据
let draggedData = null;

const onDragStart = (event, item, sourceCategory) => {
  draggedData = { item, sourceCategory };
  event.dataTransfer.effectAllowed = 'move';
  event.dataTransfer.setData('text/plain', item);
};

const onDrop = (event, targetCategory) => {
  event.preventDefault();
  if (!draggedData) return;
  
  const { item, sourceCategory } = draggedData;
  
  // 如果目标和源相同，不做任何操作
  if (sourceCategory === targetCategory) {
    draggedData = null;
    dragOverField.value = null;
    return;
  }
  
  // 确保classifiedKnowledge结构存在
  if (!props.modelValue.classifiedKnowledge) {
    props.modelValue.classifiedKnowledge = {
      competent: [],
      novice: [],
      layman: []
    };
  }
  
  // 从源类别移除
  if (sourceCategory === 'unclassified') {
    const index = props.modelValue.unclassifiedKnowledge.indexOf(item);
    if (index > -1) {
      props.modelValue.unclassifiedKnowledge.splice(index, 1);
    }
  } else {
    const index = props.modelValue.classifiedKnowledge[sourceCategory].indexOf(item);
    if (index > -1) {
      props.modelValue.classifiedKnowledge[sourceCategory].splice(index, 1);
    }
  }
  
  // 添加到目标类别
  if (targetCategory === 'unclassified') {
    if (!props.modelValue.unclassifiedKnowledge.includes(item)) {
      props.modelValue.unclassifiedKnowledge.push(item);
    }
  } else {
    if (!props.modelValue.classifiedKnowledge[targetCategory].includes(item)) {
      props.modelValue.classifiedKnowledge[targetCategory].push(item);
    }
  }
  
  draggedData = null;
  dragOverField.value = null;
};

// --- Cognitive Tendency: Chinese Translation & archetypes Dictionary ---
const cognitiveLabels = {
  0: 'Attentional Anchor',
  1: 'Reasoning Entry',
  2: 'Reasoning Style'
};

const subDimensionTranslations = {
  'symptoms': 'Symptoms',
  'present_illness': 'Present Illness',
  'past_medical_history': 'Past Medical History',
  'physicochemical_parameters': 'Physicochemical Parameters',
  'familiarity_driven': 'Familiarity Driven',
  'symptom_significance': 'Symptom Significance',
  'risk_perception': 'Risk Perception',
  'irrelevant_factors': 'Irrelevant Factors',
  'linear_causality': 'Linear Causality',
  'multi_concurrent': 'Multi Concurrent',
  'undefined': 'Undefined'
};

const levelTranslations = {
  'low': 'Low',
  'medium': 'Medium',
  'high': 'High'
};

const plasticityTranslations = {
  'low': 'Rigid',
  'medium': 'Steady',
  'high': 'Adaptive'
};

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
      props.modelValue.cognitive[category].push(opt);
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
  
  const remaining = options.filter(o => !selected.includes(o));
  
  return {
    selected: selected,
    recommended: [],
    others: remaining
  };
};

const vFocus = {
  mounted: (el) => {
    el.focus();
    if (el.tagName === 'INPUT') el.select();
  }
};

const resetEditing = () => {
  editingField.value = null;
  editingKnowledge.value = { category: null, index: null, value: '' };
  isAddingKnowledge.value = false;
};

const getAllKnowledgePoints = () => {
  const unclassified = props.modelValue.unclassifiedKnowledge || [];
  const classified = props.modelValue.classifiedKnowledge || {
    competent: [],
    novice: [],
    layman: []
  };
  return [
    ...unclassified,
    ...(classified.competent || []),
    ...(classified.novice || []),
    ...(classified.layman || [])
  ];
};

const activeQuickProfile = ref(null);

const applyQuickProfile = (level) => {
  activeQuickProfile.value = level;
  const allKnowledge = getAllKnowledgePoints();
  props.modelValue.unclassifiedKnowledge = [];
  props.modelValue.classifiedKnowledge = {
    competent: [],
    novice: [],
    layman: []
  };

  if (level === 'good') {
    props.modelValue.classifiedKnowledge.competent = [...allKnowledge];
    props.modelValue.cognitive[0] = [
      'symptoms',
      'present_illness',
      'physicochemical_parameters',
      'past_medical_history'
    ];
    props.modelValue.cognitive[1] = [
      'risk_perception',
      'familiarity_driven',
      'symptom_significance'
    ];
    props.modelValue.cognitive[2] = ['multi_concurrent'];
  } else if (level === 'medium') {
    props.modelValue.classifiedKnowledge.novice = [...allKnowledge];
    props.modelValue.cognitive[0] = [
      'symptoms',
      'present_illness',
      'past_medical_history'
    ];
    props.modelValue.cognitive[1] = [
      'familiarity_driven',
      'symptom_significance'
    ];
    props.modelValue.cognitive[2] = ['linear_causality'];
  } else {
    props.modelValue.classifiedKnowledge.layman = [...allKnowledge];
    props.modelValue.cognitive[0] = [
      'symptoms',
      'present_illness'
    ];
    props.modelValue.cognitive[1] = ['irrelevant_factors'];
    props.modelValue.cognitive[2] = ['undefined'];
  }
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
  min-height: 850px;
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
  padding: 0.6rem 0.6rem 0.8rem; /* 进一步压缩左右 padding */
  height: calc(100% - 60px); /* 同步头部高度的修改 */
  display: flex;
  flex-direction: column;
  gap: 0.7rem; /* 压缩内部模块间的间距 */
}

.quick-profile-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px;
  border-radius: 20px;
  border: 2px dashed color-mix(in srgb, var(--base-card-color) 70%, #ffffff 30%);
  background: color-mix(in srgb, var(--base-card-color) 18%, #ffffff 82%);
}

.quick-pill {
  flex: 1;
  border: none;
  background: rgba(255, 255, 255, 0.8);
  color: #7A7A7A;
  font-weight: 600;
  font-size: 12px;
  padding: 6px 8px;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.04);
}

.quick-pill.is-active,
.quick-pill:hover {
  background: var(--base-card-color);
  color: #ffffff;
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
  top: 8px;
  right: 8px;
  width: 22px;
  height: 22px;
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
  gap: 1rem; /* gap-4 */
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
  width: 40px;
  height: 40px;
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
  font-size: 16px;
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
  font-size: 16px;
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
  gap: 0.5rem; /* gap-2 */
}

.meta-item-box {
  width: 130px; /* 缩小宽度 */
  height: 24px;
  background-color: rgba(255, 255, 255, 0.35);
  border-radius: 12px;
  display: flex;
  align-items: center;
  padding: 0 0.75rem;
  cursor: text;
}

.meta-label {
  font-size: 11px;
  font-weight: bold;
  color: #6C6565;
  margin-right: 0.5rem;
}

.meta-value {
  font-size: 11px;
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
  padding: 0.15rem 0rem 0.2rem; /* 进一步压缩内边距 */
  display: flex;
  flex-direction: column;
}
.panel-section > * + * {
  margin-top: 2px; /* 极小间距，消除标题与内容间的空隙 */
}

.panel-title {
  margin: 0;
  padding: 0;
  font-size: 14px;
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
  gap: 0.8rem; /* 进一步减小间距 */
}

/* =========================================
   4. 知识背景部分 (Knowledge Background)
   ========================================= */
.knowledge-panel {
  height: 300px;
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
  height: 250px;
  background-color: rgba(255, 255, 255, 0.4);
  border-radius: 12px;
  padding: 0.6rem;
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 0.6rem;
  overflow-y: auto;
  border: 1px dashed rgba(0, 0, 0, 0.1);
}

.theory-tag {
  background-color: #717171;
  border: 1px solid #A5A8AC;
  padding: 0.4rem 0.8rem;
  border-radius: 9999px;
  font-size: 12px;
  color: #fff;
  cursor: move;
  transition: background-color 0.2s;
  white-space: nowrap;
  display: flex;
  align-items: center;
  justify-content: center;
}

.theory-tag.editing {
  padding: 0;
  overflow: hidden;
}

.tag-input {
  background: transparent;
  border: none;
  color: inherit;
  font-size: inherit;
  width: 100%;
  padding: 0;
  text-align: center;
  outline: none;
}

.delete-tag-btn {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 16px;
  line-height: 1;
  color: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
}

.delete-tag-btn.mini {
  font-size: 12px;
  right: 4px;
}

.delete-tag-btn:hover {
  color: #fff;
  background-color: rgba(0, 0, 0, 0.2);
}

.add-theory-tag {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #D9D9D9;
  color: #ffffff;
  border: 1px dashed #A5A8AC;
  border-radius: 50%;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s;
}

.add-theory-tag:hover {
  background-color: rgba(255, 255, 255, 0.4);
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
  gap: 0.6rem;
}

.drop-zone {
  height: 75px;
  border: none;                  /* 去掉边框 */
  border-radius: 14px;           /* 更像 card，而不是框 */
  padding: 0.6rem;
  display: flex;
  flex-direction: column;
  transition: background-color 0.15s ease, transform 0.15s ease;
  overflow: hidden;
}


.zone-label {
  font-size: 10px;
  font-weight: bold;
  margin-bottom: 0.3rem;
}

.items-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  width: 100%;
  overflow-y: auto;
  align-content: flex-start;
  padding: 0.15rem;
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
  font-size: 10px;
  padding: 0.2rem 0.6rem;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  justify-content: center;
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
  height: 320px;
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
  column-gap: 0.8rem;
  margin-top: 5px; /* 紧凑排列 */
  padding: 0 0.3rem;
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
  gap: 0.8rem;
  margin-top: 5px; /* 紧凑排列 */
  height: 180px;
  padding: 0 0.8rem;
}

.option-column {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.selectable-box {
  background-color: rgba(255, 255, 255, 0.45);
  border-radius: 8px;
  min-height: 28px;
  font-size: 11px;
  padding: 0.6rem;
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
  background-color: #7F96CB;
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
  border: 1.5px dashed #B0C4DE;
  background-color: rgba(176, 196, 222, 0.1);
  color: #7F8C8D;
}

/* =========================================
   6. 社交与学习综合部分 (Combined Social & Learning)
   ========================================= */
.combined-panel {
  height: auto;
  padding: 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.social-attributes-row {
  display: flex;
  flex-direction: row;
  gap: 0.8rem;
  width: 100%;
}

.social-left-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.social-right-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.role-selection-grid {
  display: flex;
  flex-direction: row;
  justify-content: space-around;
  align-items: center;
  padding: 0.4rem;
  gap: 0.3rem;
  background-color: rgba(255, 255, 255, 0.4);
  border-radius: 12px;
}

.plasticity-horizontal-options {
  display: flex;
  flex-direction: row;
  gap: 0.6rem;
  width: 100%;
  justify-content: space-around;
}

.combined-content-row {
  display: flex;
  height: 100%;
  gap: 1rem;
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
  gap: 0.4rem;
}

.level-select-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.level-title {
  font-size: 11px;
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
  padding: 2px 10px;
  font-size: 10px;
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
  padding: 0.3rem;
  gap: 3px;
  background-color: rgba(255, 255, 255, 0.4);
  border-radius: 12px;
}

.role-choice-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  width: 50px;
  height: auto;
  justify-content: center;
  transition: all 0.2s;
}

.role-illus {
  width: 1.4rem;
  height: 1.4rem;
  background-size: contain;
  background-repeat: no-repeat;
  margin-bottom: 0.2rem;
  transition: transform 0.2s;
}

.role-choice-item:hover .role-illus {
  transform: scale(1.1);
}

.role-name-text {
  font-size: 10px;
  color: #6C6565;
  margin-bottom: 0.2rem;
  font-weight: bold;
  text-align: center;
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
  gap: 0.6rem;
}

.p-level-card {
  width: auto;
  flex: 1;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(255, 255, 255, 0.45);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  font-size: 11px;
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
