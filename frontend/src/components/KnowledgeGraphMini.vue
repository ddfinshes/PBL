<template>
  <div class="kg-mini">
    <div class="kg-mini-header">
      <div class="kg-mini-title">
        <span class="kg-mini-name" :style="{ color: accentColor }">{{ filteredTitle }}</span>
      </div>
    </div>
    <div ref="wrapRef" class="kg-mini-canvas">
      <svg ref="svgRef" class="kg-mini-svg" />
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import * as d3 from 'd3';

const props = defineProps({
  title: { type: String, default: '' },
  accentColor: { type: String, default: '#8095CA' },
  graph: { type: Object, default: () => ({ nodes: {}, edges: [] }) },
  masteredPoints: { type: Array, default: () => [] },
  agentNames: { type: Array, default: () => [] },
});

const wrapRef = ref(null);
const svgRef = ref(null);

let simulation = null;

const filteredTitle = computed(() => {
  const title = String(props.title || '').trim();
  const agentNames = Array.isArray(props.agentNames) ? props.agentNames : [];
  
  if (agentNames.length === 0) {
    return title;
  }
  
  // 检查 title 是否在 agentNames 列表中
  return agentNames.includes(title) ? title : '';
});

const normalized = computed(() => {
  const nodesObj = props.graph?.nodes && typeof props.graph.nodes === 'object' ? props.graph.nodes : {};
  const edgesArr = Array.isArray(props.graph?.edges) ? props.graph.edges : [];

  const nodes = Object.entries(nodesObj).map(([id, n]) => ({
    id,
    point: String(n?.point || id),
  }));
  const nodeById = new Map(nodes.map((n) => [n.id, n]));

  const links = edgesArr
    .map((e) => ({
      source: String(e?.source || ''),
      target: String(e?.target || ''),
      relation: String(e?.relation || ''),
    }))
    .filter((l) => nodeById.has(l.source) && nodeById.has(l.target));

  const masteredSet = new Set((props.masteredPoints || []).map((s) => String(s || '').trim()).filter(Boolean));
  const masteredNodeIds = nodes.filter((n) => masteredSet.has(n.point)).map((n) => n.id);

  return { nodes, links, masteredSet, masteredNodeIds };
});

function cleanup() {
  if (simulation) {
    simulation.stop();
    simulation = null;
  }
  const svg = d3.select(svgRef.value);
  svg.selectAll('*').remove();
}

function render() {
  if (!wrapRef.value || !svgRef.value) return;
  cleanup();

  const { width, height } = wrapRef.value.getBoundingClientRect();
  const w = Math.max(260, Math.floor(width || 0));
  const h = Math.max(180, Math.floor(height || 0));

  const { nodes: baseNodes, links: baseLinks, masteredSet, masteredNodeIds } = normalized.value;
  const svg = d3.select(svgRef.value);
  svg.attr('viewBox', `0 0 ${w} ${h}`).attr('width', w).attr('height', h);

  const g = svg.append('g');

  // 缩放/平移：便于在小视窗里查看细节
  svg.call(
    d3
      .zoom()
      .scaleExtent([0.55, 3.2])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      })
  );

  // Light background grid hint
  g.append('rect')
    .attr('x', 0)
    .attr('y', 0)
    .attr('width', w)
    .attr('height', h)
    .attr('fill', '#ffffff');

  // ---- 构造“标签节点”，用于标签避让（所有节点都显示文字）----
  const importantIds = new Set(masteredNodeIds);
  const labelNodes = baseNodes.map((n) => {
    const text = n.point || n.id;
    // 简单估计文本宽度：字符数 * 6 + padding（中文略偏宽也可接受）
    const estW = Math.min(180, Math.max(28, String(text).length * 6 + 16));
    const estR = Math.max(14, Math.min(60, estW / 2));
    return {
      id: `label:${n.id}`,
      anchorId: n.id,
      text,
      isLabel: true,
      estR,
    };
  });
  const allNodes = [...baseNodes, ...labelNodes];

  const labelLinks = labelNodes.map((ln) => ({
    source: ln.id,
    target: ln.anchorId,
    relation: 'label_anchor',
  }));

  const allLinks = [...baseLinks, ...labelLinks];

  const link = g
    .append('g')
    .attr('stroke', '#CBD5E1')
    .attr('stroke-opacity', 0.9)
    .selectAll('line')
    .data(allLinks.filter((l) => l.relation !== 'label_anchor'))
    .join('line')
    .attr('stroke-width', (d) => (d.relation === 'co_occurrence_same_question' ? 0.8 : 1.2));

  // 标签引线（label -> anchor）
  const leader = g
    .append('g')
    .attr('stroke', '#94A3B8')
    .attr('stroke-opacity', 0.65)
    .selectAll('line')
    .data(labelLinks)
    .join('line')
    .attr('stroke-width', 0.8)
    .attr('stroke-dasharray', '2,2');

  const node = g
    .append('g')
    .selectAll('circle')
    .data(baseNodes)
    .join('circle')
    .attr('r', 5.2)
    .attr('fill', (d) => (masteredSet.has(d.point) ? props.accentColor : '#94A3B8'))
    .attr('stroke', (d) => (masteredSet.has(d.point) ? '#111827' : '#64748B'))
    .attr('stroke-width', (d) => (masteredSet.has(d.point) ? 1.4 : 0.8));

  // 所有节点都显示文字：文字跟随 labelNodes（可避让）
  const label = g
    .append('g')
    .selectAll('text')
    .data(labelNodes)
    .join('text')
    .text((d) => d.text)
    .attr('font-size', 10)
    .attr('fill', '#0F172A')
    .attr('opacity', (d) => (importantIds.has(d.anchorId) ? 0.98 : 0.85))
    .attr('pointer-events', 'none');

  // tooltip
  node.append('title').text((d) => d.point);

  // 拖拽：拖动某个节点时，力导向图会连带调整其它节点
  const drag = d3
    .drag()
    .on('start', (event, d) => {
      if (!event.active && simulation) simulation.alphaTarget(0.25).restart();
      d.fx = d.x;
      d.fy = d.y;
    })
    .on('drag', (event, d) => {
      d.fx = event.x;
      d.fy = event.y;
    })
    .on('end', (event, d) => {
      if (!event.active && simulation) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    });

  node.call(drag);

  // 文本也可拖动（拖动标签时会牵引到对应节点）
  label.call(drag);

  // Force simulation
  simulation = d3
    .forceSimulation(allNodes)
    .force(
      'link',
      d3.forceLink(allLinks)
        .id((d) => d.id)
        .distance((l) => {
          const rel = String(l.relation || '');
          if (rel === 'label_anchor') return 26;
          return rel === 'co_occurrence_same_question' ? 44 : 56;
        })
        .strength((l) => {
          const rel = String(l.relation || '');
          if (rel === 'label_anchor') return 0.9;
          return rel === 'co_occurrence_same_question' ? 0.25 : 0.6;
        })
    )
    .force(
      'charge',
      d3.forceManyBody().strength((d) => {
        if (d.isLabel) return -120;
        return importantIds.has(d.id) ? -170 : -115;
      })
    )
    .force('center', d3.forceCenter(w / 2, h / 2))
    // 更强的碰撞避免节点叠在一起
    .force(
      'collision',
      d3.forceCollide().radius((d) => {
        if (d.isLabel) return d.estR || 18;
        return importantIds.has(d.id) ? 18 : 13;
      })
    )
    // 边界约束，避免漂出画布
    .force('x', d3.forceX(w / 2).strength(0.02))
    .force('y', d3.forceY(h / 2).strength(0.02));

  simulation.on('tick', () => {
    link
      .attr('x1', (d) => d.source.x)
      .attr('y1', (d) => d.source.y)
      .attr('x2', (d) => d.target.x)
      .attr('y2', (d) => d.target.y);

    // leader lines: label -> anchor
    leader
      .attr('x1', (d) => d.source.x)
      .attr('y1', (d) => d.source.y)
      .attr('x2', (d) => d.target.x)
      .attr('y2', (d) => d.target.y);

    node.attr('cx', (d) => d.x).attr('cy', (d) => d.y);

    label
      .attr('x', (d) => d.x + 6)
      .attr('y', (d) => d.y + 3);
  });

  // Run a short warmup for stability (without blocking UI)
  simulation.alpha(0.9).restart();
  setTimeout(() => {
    if (simulation) simulation.alphaTarget(0).alpha(0.35);
  }, 300);
}

onMounted(() => {
  render();
  const ro = new ResizeObserver(() => render());
  if (wrapRef.value) ro.observe(wrapRef.value);
  onBeforeUnmount(() => ro.disconnect());
});

watch(
  () => [props.graph, props.masteredPoints],
  () => render(),
  { deep: true }
);

onBeforeUnmount(() => cleanup());
</script>

<style scoped>
.kg-mini {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  overflow: hidden;
}

.kg-mini-header {
  padding: 8px 10px;
  background: #0b1220;
}

.kg-mini-title {
  display: flex;
  align-items: baseline;
  justify-content: flex-start;
  gap: 8px;
}

.kg-mini-name {
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kg-mini-canvas {
  flex: 1;
  min-height: 0;
  background: #ffffff;
}

.kg-mini-svg {
  display: block;
}
</style>

