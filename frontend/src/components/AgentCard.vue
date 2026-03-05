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

        <div class="structural-knowledge-row">
          <div class="structural-title">Structural Knowledge</div>
          <div class="structural-options">
            <div
              v-for="lv in ['low', 'medium', 'high']"
              :key="lv"
              class="structural-option"
              :class="{ 'is-active': modelValue.structuralKnowledge === lv }"
              @click="modelValue.structuralKnowledge = lv"
            >
              {{ levelTranslations[lv] }}
            </div>
          </div>
        </div>
      </section>

      <section class="panel-section traits-panel">
        <div class="radar-grid">
          <div class="radar-card">
            <div class="radar-card-title">Learning Style</div>
            <svg
              ref="learningRadarRef"
              class="radar-svg"
              viewBox="-20 -20 180 180"
            >
              <polygon
                v-for="ring in [1, 2, 3]"
                :key="`ls-ring-${ring}`"
                :points="getRadarRingPoints(learningStyleAxes, ring)"
                class="radar-ring"
              />
              <line
                v-for="(axis, idx) in learningStyleAxes"
                :key="`ls-axis-${axis.key}`"
                :x1="radarCenter"
                :y1="radarCenter"
                :x2="getAxisEndpoint(learningStyleAxes.length, idx).x"
                :y2="getAxisEndpoint(learningStyleAxes.length, idx).y"
                class="radar-axis"
              />
              <polygon :points="getRadarDataPoints(modelValue.learning_styles, learningStyleAxes)" class="radar-data" />
              <circle
                v-for="(axis, idx) in learningStyleAxes"
                :key="`ls-handle-${axis.key}`"
                :cx="getRadarHandlePoints(modelValue.learning_styles, learningStyleAxes)[idx].x"
                :cy="getRadarHandlePoints(modelValue.learning_styles, learningStyleAxes)[idx].y"
                r="4.5"
                class="radar-handle"
                @mousedown.prevent="startRadarDrag('learning_styles', idx, $event)"
              />
              <text
                v-for="(axis, idx) in learningStyleAxes"
                :key="`ls-label-${axis.key}`"
                :x="getLabelPosition(learningStyleAxes.length, idx).x"
                :y="getLabelPosition(learningStyleAxes.length, idx).y"
                text-anchor="middle"
                dominant-baseline="middle"
                class="radar-label-text"
              >
                {{ axis.label }}
              </text>
            </svg>
          </div>

          <div class="radar-card">
            <div class="radar-card-title">Personality</div>
            <svg
              ref="personalityRadarRef"
              class="radar-svg"
              viewBox="-20 -20 180 180"
            >
              <polygon
                v-for="ring in [1, 2, 3]"
                :key="`bf-ring-${ring}`"
                :points="getRadarRingPoints(personalityAxes, ring)"
                class="radar-ring"
              />
              <line
                v-for="(axis, idx) in personalityAxes"
                :key="`bf-axis-${axis.key}`"
                :x1="radarCenter"
                :y1="radarCenter"
                :x2="getAxisEndpoint(personalityAxes.length, idx).x"
                :y2="getAxisEndpoint(personalityAxes.length, idx).y"
                class="radar-axis"
              />
              <polygon :points="getRadarDataPoints(modelValue.personality, personalityAxes)" class="radar-data" />
              <circle
                v-for="(axis, idx) in personalityAxes"
                :key="`bf-handle-${axis.key}`"
                :cx="getRadarHandlePoints(modelValue.personality, personalityAxes)[idx].x"
                :cy="getRadarHandlePoints(modelValue.personality, personalityAxes)[idx].y"
                r="4.5"
                class="radar-handle"
                @mousedown.prevent="startRadarDrag('personality', idx, $event)"
              />
              <text
                v-for="(axis, idx) in personalityAxes"
                :key="`bf-label-${axis.key}`"
                :x="getLabelPosition(personalityAxes.length, idx).x"
                :y="getLabelPosition(personalityAxes.length, idx).y"
                text-anchor="middle"
                dominant-baseline="middle"
                class="radar-label-text"
              >
                {{ axis.label }}
              </text>
            </svg>
          </div>
        </div>
      </section>

      <!-- Cognitive Tendency Section -->
      <section class="panel-section cognitive-panel">
        <h3 class="panel-title">Cognitive Orientation</h3>
        <div class="cognitive-choice-grid">
          <div
            v-for="item in cognitiveChoices"
            :key="item.value"
            class="cognitive-choice-item"
            :class="{ 'is-active': modelValue.cognitiveOrientation === item.value }"
            @click="modelValue.cognitiveOrientation = item.value"
          >
            <img :src="item.icon" :alt="item.label" class="cognitive-choice-icon" />
            <div class="cognitive-choice-label">{{ item.label }}</div>
          </div>
        </div>
      </section>

      <!-- Social and Learning Integration Section -->
      <section class="panel-section combined-panel">
        <div class="plasticity-grid">
          <div class="plasticity-card">
            <h3 class="panel-title">Learning Plasticity</h3>
            <div class="plasticity-options">
              <div v-for="lv in ['low', 'medium', 'high']" :key="lv"
                   class="level-btn"
                   :class="{'is-active': modelValue.plasticity === lv}"
                   @click="modelValue.plasticity = lv">
                {{ plasticityTranslations[lv] }}
              </div>
            </div>
          </div>
          <div class="plasticity-card plasticity-empty-panel">
            <h3 class="panel-title">Bias & Error</h3>
            <div class="bias-list">
              <button
                v-for="item in modelValue.biasErrorOptions"
                :key="item"
                type="button"
                class="bias-item"
                :class="{ 'is-active': modelValue.biasErrors.includes(item) }"
                @click="toggleBiasError(item)"
              >
                {{ item }}
              </button>
            </div>

            <div v-if="isAddingBiasError" class="bias-add-row">
              <input
                v-model="newBiasErrorName"
                class="bias-add-input"
                placeholder="Add bias or error..."
                v-focus
                @blur="submitAddBiasError"
                @keyup.enter="submitAddBiasError"
              />
            </div>
            <button
              v-else
              type="button"
              class="bias-add-btn"
              @click="isAddingBiasError = true"
            >
              +
            </button>
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
  interactionRoles: { type: Array, required: true },
  cardColor: { type: String, default: '#CEDCFB' }
});

const emit = defineEmits(['update:modelValue', 'delete']);

const knowledgeActions = inject('knowledgeActions', {});

const editingField = ref(null);
const dragOverField = ref(null);

const radarCenter = 70;
const radarRadius = 48;

const learningStyleAxes = [
  { key: 'surface', label: 'Surface' },
  { key: 'deep', label: 'Deep' },
  { key: 'strategic', label: 'Strategic' }
];

const personalityAxes = [
  { key: 'openness', label: 'Openness' },
  { key: 'conscientiousness', label: 'Conscientiousness' },
  { key: 'extraversion', label: 'Extraversion' },
  { key: 'agreeableness', label: 'Agreeableness' },
  { key: 'neuroticism', label: 'Neuroticism' }
];

const learningRadarRef = ref(null);
const personalityRadarRef = ref(null);
const draggingRadar = ref({ type: null, axisIndex: -1 });

if (!props.modelValue.structuralKnowledge) {
  props.modelValue.structuralKnowledge = 'medium';
}

if (!props.modelValue.cognitiveOrientation) {
  props.modelValue.cognitiveOrientation = 'line_based';
}

if (!props.modelValue.learning_styles || typeof props.modelValue.learning_styles !== 'object') {
  props.modelValue.learning_styles = { surface: 2, deep: 2, strategic: 2 };
}

if (!props.modelValue.personality || typeof props.modelValue.personality !== 'object') {
  props.modelValue.personality = {
    openness: 2,
    conscientiousness: 2,
    extraversion: 2,
    agreeableness: 2,
    neuroticism: 2
  };
}

const defaultBiasErrorOptions = [
  'Anchoring Bias',
  'Availability Bias',
  'Confirmation Bias',
  'Premature Closure'
];

if (!Array.isArray(props.modelValue.biasErrors)) {
  props.modelValue.biasErrors = Array.isArray(props.modelValue.bias_errors)
    ? [...props.modelValue.bias_errors]
    : [];
}

const sourceBiasErrorOptions = Array.isArray(props.modelValue.biasErrorOptions)
  ? props.modelValue.biasErrorOptions
  : (Array.isArray(props.modelValue.bias_error_options) ? props.modelValue.bias_error_options : []);

props.modelValue.biasErrorOptions = Array.from(
  new Set([
    ...defaultBiasErrorOptions,
    ...sourceBiasErrorOptions,
    ...props.modelValue.biasErrors
  ])
);

const normalizeRadarValues = () => {
  learningStyleAxes.forEach(axis => {
    const current = Number(props.modelValue.learning_styles[axis.key]);
    props.modelValue.learning_styles[axis.key] = Number.isFinite(current)
      ? Math.max(1, Math.min(3, Math.round(current)))
      : 2;
  });

  personalityAxes.forEach(axis => {
    const current = Number(props.modelValue.personality[axis.key]);
    props.modelValue.personality[axis.key] = Number.isFinite(current)
      ? Math.max(1, Math.min(3, Math.round(current)))
      : 2;
  });
};

normalizeRadarValues();

const getAxisAngle = (total, index) => -Math.PI / 2 + (index * 2 * Math.PI) / total;

const getAxisEndpoint = (total, index) => {
  const angle = getAxisAngle(total, index);
  return {
    x: radarCenter + radarRadius * Math.cos(angle),
    y: radarCenter + radarRadius * Math.sin(angle)
  };
};

const getRadarRingPoints = (axes, ringLevel) => {
  const ringRadius = (ringLevel / 3) * radarRadius;
  return axes
    .map((_, index) => {
      const angle = getAxisAngle(axes.length, index);
      const x = radarCenter + ringRadius * Math.cos(angle);
      const y = radarCenter + ringRadius * Math.sin(angle);
      return `${x},${y}`;
    })
    .join(' ');
};

const getRadarHandlePoints = (valuesObj, axes) => {
  return axes.map((axis, index) => {
    const value = Math.max(1, Math.min(3, Number(valuesObj?.[axis.key]) || 1));
    const radius = (value / 3) * radarRadius;
    const angle = getAxisAngle(axes.length, index);
    return {
      x: radarCenter + radius * Math.cos(angle),
      y: radarCenter + radius * Math.sin(angle)
    };
  });
};

const getRadarDataPoints = (valuesObj, axes) => {
  return getRadarHandlePoints(valuesObj, axes)
    .map(point => `${point.x},${point.y}`)
    .join(' ');
};

const clampRadarScore = (value) => Math.max(1, Math.min(3, Math.round(value)));
//调整learning style后大五人格的影响
const learningStylePersonalityEffects = {
  deep: {
    openness: 1,
    conscientiousness: 1,
    agreeableness: 1
  },
  strategic: {
    conscientiousness: 1,
    extraversion: 1
  },
  surface: {
    neuroticism: 1,
    openness: -1,
    conscientiousness: -1
  }
};

const applyLinkedPersonalityFromLearningStyles = (changedAxisKey, delta) => {
  const effects = learningStylePersonalityEffects[changedAxisKey];
  if (!effects || !delta) return;

  Object.entries(effects).forEach(([traitKey, direction]) => {
    const current = Number(props.modelValue.personality?.[traitKey]) || 2;
    const next = clampRadarScore(current + direction * delta);
    props.modelValue.personality[traitKey] = next;
  });
};

const getLabelPosition = (total, index) => {
  const angle = getAxisAngle(total, index);
  const labelDistance = total === 5 ? radarRadius + 30 : radarRadius + 18;
  const personalityOffsets = [
    { x: 0, y: -6 },
    { x: 14, y: -3 },
    { x: 16, y: 9 },
    { x: -16, y: 9 },
    { x: -14, y: -3 }
  ];

  const offset = total === 5 ? personalityOffsets[index] || { x: 0, y: 0 } : { x: 0, y: 0 };

  return {
    x: radarCenter + labelDistance * Math.cos(angle) + offset.x,
    y: radarCenter + labelDistance * Math.sin(angle) + offset.y
  };
};

const getLabelAnchor = (total, index) => {
  if (total !== 5) return 'middle';
  if (index === 1 || index === 2) return 'start';
  if (index === 3 || index === 4) return 'end';
  return 'middle';
};

const getLabelBaseline = (total, index) => {
  if (total !== 5) return 'middle';
  if (index === 0) return 'hanging';
  return 'middle';
};

const updateRadarScoreByPointer = (clientX, clientY) => {
  const { type, axisIndex } = draggingRadar.value;
  if (!type || axisIndex < 0) return;

  const svgEl = type === 'learning_styles' ? learningRadarRef.value : personalityRadarRef.value;
  if (!svgEl) return;

  const rect = svgEl.getBoundingClientRect();
  const x = ((clientX - rect.left) / rect.width) * 140;
  const y = ((clientY - rect.top) / rect.height) * 140;

  const axes = type === 'learning_styles' ? learningStyleAxes : personalityAxes;
  const angle = getAxisAngle(axes.length, axisIndex);
  const unitX = Math.cos(angle);
  const unitY = Math.sin(angle);

  const dx = x - radarCenter;
  const dy = y - radarCenter;
  const projection = Math.max(0, Math.min(radarRadius, dx * unitX + dy * unitY));
  const score = Math.max(1, Math.min(3, Math.round((projection / radarRadius) * 3)));

  const targetAxis = axes[axisIndex];
  if (targetAxis) {
    const currentScore = Number(props.modelValue[type]?.[targetAxis.key]);
    if (currentScore === score) return;
    props.modelValue[type][targetAxis.key] = score;
    if (type === 'learning_styles') {
      const delta = score - currentScore;
      applyLinkedPersonalityFromLearningStyles(targetAxis.key, delta);
    }
  }
};

const onRadarMouseMove = (event) => {
  updateRadarScoreByPointer(event.clientX, event.clientY);
};

const stopRadarDrag = () => {
  draggingRadar.value = { type: null, axisIndex: -1 };
  window.removeEventListener('mousemove', onRadarMouseMove);
  window.removeEventListener('mouseup', stopRadarDrag);
};

const startRadarDrag = (type, axisIndex, event) => {
  draggingRadar.value = { type, axisIndex };
  updateRadarScoreByPointer(event.clientX, event.clientY);
  window.addEventListener('mousemove', onRadarMouseMove);
  window.addEventListener('mouseup', stopRadarDrag);
};

const isAddingBiasError = ref(false);
const newBiasErrorName = ref('');

const toggleBiasError = (item) => {
  if (!Array.isArray(props.modelValue.biasErrors)) {
    props.modelValue.biasErrors = [];
  }
  const index = props.modelValue.biasErrors.indexOf(item);
  if (index >= 0) {
    props.modelValue.biasErrors.splice(index, 1);
  } else {
    props.modelValue.biasErrors.push(item);
  }
};

const submitAddBiasError = () => {
  const value = (newBiasErrorName.value || '').trim();
  if (value) {
    if (!Array.isArray(props.modelValue.biasErrorOptions)) {
      props.modelValue.biasErrorOptions = [];
    }
    if (!props.modelValue.biasErrorOptions.includes(value)) {
      props.modelValue.biasErrorOptions.push(value);
    }
    if (!Array.isArray(props.modelValue.biasErrors)) {
      props.modelValue.biasErrors = [];
    }
    if (!props.modelValue.biasErrors.includes(value)) {
      props.modelValue.biasErrors.push(value);
    }
  }
  isAddingBiasError.value = false;
  newBiasErrorName.value = '';
};

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

const cognitiveChoices = [
  {
    value: 'point_based',
    label: 'Point-based Reasoning',
    icon: '/点.png'
  },
  {
    value: 'line_based',
    label: 'Linear Chaining',
    icon: '/线.png'
  },
  {
    value: 'plane_based',
    label: 'Multi Concurrent',
    icon: '/面.png'
  }
];

const levelTranslations = {
  'low': 'Low',
  'medium': 'Medium',
  'high': 'High'
};

const plasticityTranslations = {
  'low': 'low',
  'medium': 'medium',
  'high': 'high'
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
  isAddingBiasError.value = false;
  newBiasErrorName.value = '';
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

.structural-knowledge-row {
  margin: 0.2rem 0.6rem 0.5rem;
  padding: 0.4rem 0.5rem;
  background-color: rgba(255, 255, 255, 0.4);
  border-radius: 12px;
}

.structural-title {
  font-size: 11px;
  font-weight: bold;
  color: #6C6565;
  margin-bottom: 0.3rem;
}

.structural-options {
  display: flex;
  background-color: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 20px;
  padding: 2px;
}

.structural-option {
  flex: 1;
  text-align: center;
  padding: 2px 10px;
  font-size: 10px;
  border-radius: 18px;
  cursor: pointer;
  transition: all 0.2s;
  color: #7F8C8D;
}

.structural-option.is-active {
  background-color: #8095CA;
  color: white;
  font-weight: bold;
}
.traits-panel {
  padding: 0.2rem 0.3rem 0rem;
}

.radar-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.55rem;
}

.radar-card {
  background-color: rgba(255, 255, 255, 0.42);
  border-radius: 12px;
  padding: 0.2rem 0.3rem 0rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.radar-card-title {
  font-size: 14px;
  font-weight: bold;
  color: #000000;
  line-height: 1.1;
}

.radar-svg {
  width: 300px;
  height: 160px;
}

.radar-ring {
  fill: none;
  stroke: rgba(108, 101, 101, 0.35);
  stroke-width: 0.8;
}

.radar-axis {
  stroke: rgba(108, 101, 101, 0.38);
  stroke-width: 0.8;
}

.radar-data {
  fill: rgba(128, 149, 202, 0.28);
  stroke: #8095CA;
  stroke-width: 1.4;
}

.radar-handle {
  fill: #8095CA;
  stroke: #ffffff;
  stroke-width: 1.1;
  cursor: grab;
}

.radar-handle:active {
  cursor: grabbing;
}

.radar-labels {
  width: 100%;
  display: grid;
  gap: 2px;
}

.radar-labels.three-col {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.radar-labels.five-col {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.radar-label-text {
  font-size: 12px;
  font-weight: 600;
  fill: #4A4A4A;
  pointer-events: none;
}
/* =========================================
   5. 认知倾向部分 (Cognitive Orientation)
   ========================================= */
.cognitive-panel {
  height: 120px;
  position: relative;
  margin-bottom: 0.2rem;
  margin-top: 0;
}


.cognitive-choice-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.8rem;
  padding: 0.5rem 0.8rem 0.35rem;
}

.cognitive-choice-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  min-height: 82px;
  border-radius: 12px;
  background-color: rgba(255, 255, 255, 0.45);
  border: 1px solid rgba(0, 0, 0, 0.08);
  cursor: pointer;
  transition: all 0.2s;
  padding: 0.45rem;
}

.cognitive-choice-item:hover {
  background-color: #C5C9D4;
}

.cognitive-choice-item.is-active {
  background-color: #8095CA;
  color: #fff;
  border-color: #8095CA;
}

.cognitive-choice-icon {
  width: 28px;
  height: 28px;
  object-fit: contain;
}

.cognitive-choice-label {
  font-size: 11px;
  text-align: center;
  font-weight: 600;
  line-height: 1.2;
  color: #000000;
}

.cognitive-choice-item.is-active .cognitive-choice-label {
  color: #ffffff;
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

.plasticity-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.55rem;
}

.plasticity-card {
  background-color: rgba(255, 255, 255, 0.42);
  border-radius: 12px;
  padding: 0.45rem 0.45rem;
  min-height: 72px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}

.plasticity-options {
  margin: 0.45rem auto 0.1rem;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  background: transparent;
  border: none;
  padding: 0;
}

.plasticity-options .level-btn {
  display: block;
  width: 100%;
  box-sizing: border-box;
  text-align: center;
  background: rgba(255, 255, 255, 0.55);
  border-radius: 12px;
  min-height: 34px;
  font-size: 13px;
  font-weight: 600;
}

.plasticity-options .level-btn:hover {
  background: rgba(197, 201, 212, 0.8);
}

.plasticity-empty-panel {
  min-height: 58px;
}

.bias-list {
  margin-top: 0.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.bias-item {
  border: none;
  background: rgba(255, 255, 255, 0.55);
  color: #7A7A7A;
  border-radius: 12px;
  min-height: 28px;
  padding: 0.2rem 0.6rem;
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.bias-item:hover {
  background: rgba(197, 201, 212, 0.8);
}

.bias-item.is-active {
  background: #8095CA;
  color: #ffffff;
}

.bias-add-row {
  margin-top: 0.35rem;
}

.bias-add-input {
  width: 100%;
  border: 1px dashed rgba(122, 122, 122, 0.45);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.65);
  color: #6C6565;
  font-size: 12px;
  padding: 0.2rem 0.55rem;
  outline: none;
  text-align: center;
}

.bias-add-btn {
  margin: 0.35rem auto 0;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 1px dashed #A5A8AC;
  background: #D9D9D9;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
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
