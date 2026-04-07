<template>
  <div class="l3-graph-view">
    <ComponentDisabled
      :status="status"
      :error="error"
      :error-type="errorType"
      component-name="L3 图谱"
      @retry="refreshState"
    >
      <v-row>
        <v-col cols="12" lg="8">
          <v-card color="surface" variant="flat" class="graph-card">
            <v-card-title class="d-flex align-center">
              <v-icon icon="mdi-graph" color="accent" class="mr-2" />
              知识图谱可视化
              <v-spacer />
              <v-btn-group density="compact" class="mr-2">
                <v-btn
                  icon="mdi-magnify-plus"
                  variant="text"
                  size="small"
                  @click="zoomIn"
                />
                <v-btn
                  icon="mdi-magnify-minus"
                  variant="text"
                  size="small"
                  @click="zoomOut"
                />
                <v-btn
                  icon="mdi-fit-to-screen"
                  variant="text"
                  size="small"
                  @click="resetZoom"
                />
              </v-btn-group>
              <v-btn
                icon="mdi-refresh"
                variant="text"
                size="small"
                :loading="memoryStore.l3Loading"
                @click="loadGraph"
              />
            </v-card-title>
            <v-card-text class="pa-0">
              <div ref="graphContainer" class="graph-container">
                <svg ref="svgElement" class="graph-svg">
                  <defs>
                    <marker
                      id="arrowhead"
                      markerWidth="10"
                      markerHeight="7"
                      refX="9"
                      refY="3.5"
                      orient="auto"
                    >
                      <polygon points="0 0, 10 3.5, 0 7" fill="currentColor" class="arrow-marker" />
                    </marker>
                  </defs>
                  <g ref="mainGroup" class="main-group">
                    <g class="edges-layer"></g>
                    <g class="edge-labels-layer"></g>
                    <g class="nodes-layer"></g>
                  </g>
                </svg>
                <div v-if="memoryStore.l3Loading" class="loading-overlay">
                  <v-progress-circular indeterminate color="primary" size="64" />
                </div>
                <div v-else-if="memoryStore.l3Graph.nodes.length === 0" class="empty-overlay">
                  <v-icon icon="mdi-graph-outline" size="80" class="mb-3" />
                  <div class="text-h6">暂无图谱数据</div>
                </div>
                <div
                  v-if="selectedNode && popupPosition"
                  class="node-popup"
                  :style="{ left: popupPosition.x + 'px', top: popupPosition.y + 'px' }"
                >
                  <v-card color="surface" variant="elevated" class="popup-card">
                    <v-card-title class="d-flex align-center text-subtitle-1 pa-3">
                      <v-icon :icon="getNodeIcon(selectedNode.label)" :color="getTypeColor(selectedNode.label)" class="mr-2" size="small" />
                      {{ selectedNode.name || selectedNode.id }}
                      <v-spacer />
                      <v-btn
                        icon="mdi-close"
                        variant="text"
                        size="x-small"
                        density="compact"
                        @click="closePopup"
                      />
                    </v-card-title>
                    <v-card-text class="pa-3 pt-0">
                      <div class="text-caption mb-1">
                        <span class="text-medium-emphasis">类型：</span>{{ selectedNode.label }}
                      </div>
                      <div class="text-caption mb-1">
                        <span class="text-medium-emphasis">ID：</span>{{ selectedNode.id }}
                      </div>
                      <div class="text-caption mb-2">
                        <span class="text-medium-emphasis">置信度：</span>{{ (selectedNode.confidence * 100).toFixed(0) }}%
                      </div>
                      <v-btn
                        color="primary"
                        size="small"
                        block
                        :loading="memoryStore.l3Loading"
                        @click="expandFromSelected"
                      >
                        <v-icon icon="mdi-arrow-expand" class="mr-1" />
                        以此节点展开
                      </v-btn>
                    </v-card-text>
                  </v-card>
                </div>
                <div
                  v-if="selectedEdge && edgePopupPosition"
                  class="node-popup"
                  :style="{ left: edgePopupPosition.x + 'px', top: edgePopupPosition.y + 'px' }"
                >
                  <v-card color="surface" variant="elevated" class="popup-card">
                    <v-card-title class="d-flex align-center text-subtitle-1 pa-3">
                      <v-icon icon="mdi-arrow-right-bold" color="secondary" class="mr-2" size="small" />
                      {{ selectedEdge.relation }}
                      <v-spacer />
                      <v-btn
                        icon="mdi-close"
                        variant="text"
                        size="x-small"
                        density="compact"
                        @click="closeEdgePopup"
                      />
                    </v-card-title>
                    <v-card-text class="pa-3 pt-0">
                      <div class="text-caption mb-2">
                        <v-icon :icon="getNodeIcon(selectedEdge.sourceNode.label)" :color="getTypeColor(selectedEdge.sourceNode.label)" size="small" class="mr-1" />
                        <strong>{{ selectedEdge.sourceNode.name || selectedEdge.sourceNode.id }}</strong>
                      </div>
                      <div class="text-caption text-center mb-2">
                        <v-icon icon="mdi-arrow-down" size="small" />
                      </div>
                      <div class="text-caption mb-2">
                        <v-icon :icon="getNodeIcon(selectedEdge.targetNode.label)" :color="getTypeColor(selectedEdge.targetNode.label)" size="small" class="mr-1" />
                        <strong>{{ selectedEdge.targetNode.name || selectedEdge.targetNode.id }}</strong>
                      </div>
                      <v-btn
                        color="secondary"
                        size="small"
                        block
                        class="mb-2"
                        :loading="memoryStore.l3Loading"
                        @click="expandFromEdge('source')"
                      >
                        <v-icon icon="mdi-arrow-expand-left" class="mr-1" />
                        从源节点展开
                      </v-btn>
                      <v-btn
                        color="secondary"
                        size="small"
                        block
                        :loading="memoryStore.l3Loading"
                        @click="expandFromEdge('target')"
                      >
                        <v-icon icon="mdi-arrow-expand-right" class="mr-1" />
                        从目标节点展开
                      </v-btn>
                    </v-card-text>
                  </v-card>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" lg="4">
          <v-card color="surface" variant="flat" class="mb-4">
            <v-card-title>
              <v-icon icon="mdi-magnify" class="mr-2" />
              搜索图谱
            </v-card-title>
            <v-card-text>
              <v-text-field
                v-model="searchKeyword"
                placeholder="搜索节点或关系..."
                prepend-inner-icon="mdi-magnify"
                variant="outlined"
                density="compact"
                hide-details
                clearable
                @keyup.enter="handleSearch"
                @click:clear="clearSearch"
              />
              <v-btn
                color="primary"
                size="small"
                class="mt-2"
                block
                :loading="memoryStore.l3SearchLoading"
                @click="handleSearch"
              >
                搜索
              </v-btn>
            </v-card-text>
          </v-card>

          <v-card 
            v-if="memoryStore.l3SearchResults.nodes.length > 0 || memoryStore.l3SearchResults.edges.length > 0" 
            color="surface" 
            variant="flat" 
            class="mb-4"
          >
            <v-card-title class="d-flex align-center">
              <v-icon icon="mdi-magnify" class="mr-2" />
              搜索结果
              <v-spacer />
              <v-btn
                icon="mdi-close"
                variant="text"
                size="small"
                @click="clearSearch"
              />
            </v-card-title>
            <v-card-text>
              <div v-if="memoryStore.l3SearchResults.nodes.length > 0" class="mb-3">
                <div class="text-caption text-medium-emphasis mb-2">节点 ({{ memoryStore.l3SearchResults.nodes.length }})</div>
                <v-list density="compact" class="pa-0 bg-transparent">
                  <v-list-item
                    v-for="node in memoryStore.l3SearchResults.nodes"
                    :key="node.id"
                    :prepend-icon="getNodeIcon(node.label)"
                    @click="expandFromSearchNode(node.id)"
                  >
                    <v-list-item-title>{{ node.name || node.id }}</v-list-item-title>
                    <v-list-item-subtitle>{{ node.label }}</v-list-item-subtitle>
                    <template #append>
                      <v-chip size="x-small" :color="getTypeColor(node.label)" variant="tonal">
                        {{ (node.confidence * 100).toFixed(0) }}%
                      </v-chip>
                    </template>
                  </v-list-item>
                </v-list>
              </div>
              <div v-if="memoryStore.l3SearchResults.edges.length > 0">
                <div class="text-caption text-medium-emphasis mb-2">关系 ({{ memoryStore.l3SearchResults.edges.length }})</div>
                <v-list density="compact" class="pa-0 bg-transparent">
                  <v-list-item
                    v-for="(edge, idx) in memoryStore.l3SearchResults.edges"
                    :key="idx"
                    prepend-icon="mdi-arrow-right-bold"
                    @click="expandFromSearchEdge(edge)"
                  >
                    <v-list-item-title>{{ edge.relation }}</v-list-item-title>
                    <v-list-item-subtitle>
                      {{ edge.source.name }} → {{ edge.target.name }}
                    </v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </div>
            </v-card-text>
          </v-card>

          <v-card color="surface" variant="flat" class="mb-4">
            <v-card-title>
              <v-icon icon="mdi-tune" class="mr-2" />
              图谱控制
            </v-card-title>
            <v-card-text>
              <div class="mb-4">
                <div class="text-caption text-medium-emphasis mb-1">拓展深度</div>
                <v-slider
                  v-model="memoryStore.l3Depth"
                  :min="1"
                  :max="3"
                  :step="1"
                  thumb-label
                />
              </div>

              <div class="mb-4">
                <div class="text-caption text-medium-emphasis mb-1">最大节点数</div>
                <v-slider
                  v-model="memoryStore.l3MaxNodes"
                  :min="10"
                  :max="50"
                  :step="5"
                  thumb-label
                />
              </div>

              <div class="mb-4">
                <div class="text-caption text-medium-emphasis mb-1">起始节点</div>
                <v-chip
                  v-if="memoryStore.l3StartNode"
                  color="accent"
                  variant="tonal"
                  size="small"
                  closable
                  @click:close="clearStartNode"
                >
                  <v-icon :icon="getNodeIcon(memoryStore.l3StartNode.label)" start size="small" />
                  {{ memoryStore.l3StartNode.name || memoryStore.l3StartNode.id }}
                </v-chip>
                <span v-else class="text-medium-emphasis text-body-2">随机选择</span>
              </div>

              <v-btn
                color="primary"
                block
                :loading="memoryStore.l3Loading"
                @click="loadGraph"
              >
                <v-icon icon="mdi-refresh" class="mr-1" />
                重新加载
              </v-btn>
            </v-card-text>
          </v-card>

          <v-card color="surface" variant="flat" class="mb-4">
            <v-card-title>
              <v-icon icon="mdi-chart-pie" class="mr-2" />
              图谱统计
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="6" class="text-center">
                  <div class="text-h4 font-weight-bold text-primary">{{ memoryStore.l3Graph.nodes.length }}</div>
                  <div class="text-caption text-medium-emphasis">节点</div>
                </v-col>
                <v-col cols="6" class="text-center">
                  <div class="text-h4 font-weight-bold text-secondary">{{ memoryStore.l3Graph.edges.length }}</div>
                  <div class="text-caption text-medium-emphasis">关系</div>
                </v-col>
              </v-row>

              <v-divider class="my-3" />

              <div class="text-caption text-medium-emphasis mb-2">节点类型</div>
              <v-chip-group column>
                <v-chip
                  v-for="(count, type) in nodeTypeStats"
                  :key="type"
                  size="small"
                  variant="tonal"
                  :color="getTypeColor(type)"
                >
                  <v-icon :icon="getNodeIcon(type)" start size="small" />
                  {{ type }}: {{ count }}
                </v-chip>
              </v-chip-group>

              <div class="text-caption text-medium-emphasis mb-2 mt-3">关系类型</div>
              <v-chip-group column>
                <v-chip
                  v-for="(count, type) in relationTypeStats"
                  :key="type"
                  size="small"
                  variant="outlined"
                >
                  {{ type }}: {{ count }}
                </v-chip>
              </v-chip-group>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-row class="mt-4">
        <v-col cols="12">
          <v-card color="surface" variant="flat">
            <v-card-title>
              <v-icon icon="mdi-information" class="mr-2" />
              L3 知识图谱说明
            </v-card-title>
            <v-card-text>
              <v-alert type="info" variant="tonal" density="compact">
                <div class="text-body-2">
                  <strong>L3 知识图谱（Semantic Memory）</strong> 是结构化的长期记忆，存储实体关系和核心特征。
                  支持多跳推理和图谱可视化。点击节点或边可查看详情并从此展开图谱。使用搜索功能快速定位节点和关系。
                </div>
              </v-alert>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </ComponentDisabled>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useMemoryStore } from '@/stores'
import { useComponentState } from '@/composables/useComponentState'
import ComponentDisabled from '@/components/ComponentDisabled.vue'
import type { KGNode, KGEdge } from '@/types'

const memoryStore = useMemoryStore()
const { status, error, errorType, refreshState } = useComponentState('l3_kg')

const graphContainer = ref<HTMLElement | null>(null)
const svgElement = ref<SVGSVGElement | null>(null)
const mainGroup = ref<SVGGElement | null>(null)

const selectedNode = ref<KGNode | null>(null)
const popupPosition = ref<{ x: number; y: number } | null>(null)

const selectedEdge = ref<{
  source: string
  target: string
  relation: string
  sourceNode: KGNode
  targetNode: KGNode
} | null>(null)
const edgePopupPosition = ref<{ x: number; y: number } | null>(null)

const searchKeyword = ref('')

const currentZoom = ref(1)
const currentTranslate = ref({ x: 0, y: 0 })

const nodeTypeStats = computed(() => {
  const stats: Record<string, number> = {}
  memoryStore.l3Graph.nodes.forEach(node => {
    stats[node.label] = (stats[node.label] || 0) + 1
  })
  return stats
})

const relationTypeStats = computed(() => {
  const stats: Record<string, number> = {}
  memoryStore.l3Graph.edges.forEach(edge => {
    stats[edge.relation] = (stats[edge.relation] || 0) + 1
  })
  return stats
})

const loadGraph = () => {
  memoryStore.fetchL3Graph()
}

const clearStartNode = () => {
  memoryStore.fetchL3Graph()
}

const closePopup = () => {
  selectedNode.value = null
  popupPosition.value = null
}

const closeEdgePopup = () => {
  selectedEdge.value = null
  edgePopupPosition.value = null
}

const expandFromSelected = () => {
  if (selectedNode.value) {
    memoryStore.expandFromNode(selectedNode.value.id)
    closePopup()
  }
}

const expandFromEdge = (type: 'source' | 'target') => {
  if (selectedEdge.value) {
    const nodeId = type === 'source' ? selectedEdge.value.source : selectedEdge.value.target
    memoryStore.expandFromNode(nodeId)
    closeEdgePopup()
  }
}

const handleSearch = () => {
  if (searchKeyword.value.trim()) {
    memoryStore.searchL3(searchKeyword.value.trim())
  }
}

const clearSearch = () => {
  searchKeyword.value = ''
  memoryStore.clearL3Search()
}

const expandFromSearchNode = (nodeId: string) => {
  memoryStore.expandFromNode(nodeId)
}

const expandFromSearchEdge = (edge: { source: { id: string }, target: { id: string } }) => {
  memoryStore.expandFromNode(edge.source.id)
}

const getNodeIcon = (label: string): string => {
  const icons: Record<string, string> = {
    Person: 'mdi-account',
    Event: 'mdi-calendar',
    Location: 'mdi-map-marker',
    Organization: 'mdi-office-building',
    Concept: 'mdi-lightbulb',
    Topic: 'mdi-tag',
    Entity: 'mdi-circle'
  }
  return icons[label] || 'mdi-tag'
}

const getTypeColor = (label: string): string => {
  const colors: Record<string, string> = {
    Person: 'primary',
    Event: 'secondary',
    Location: 'success',
    Organization: 'warning',
    Concept: 'info',
    Topic: 'accent',
    Entity: 'default'
  }
  return colors[label] || 'default'
}

const zoomIn = () => {
  currentZoom.value = Math.min(currentZoom.value * 1.2, 3)
  updateTransform()
}

const zoomOut = () => {
  currentZoom.value = Math.max(currentZoom.value / 1.2, 0.3)
  updateTransform()
}

const resetZoom = () => {
  currentZoom.value = 1
  currentTranslate.value = { x: 0, y: 0 }
  updateTransform()
}

const updateTransform = () => {
  if (mainGroup.value) {
    mainGroup.value.setAttribute(
      'transform',
      `translate(${currentTranslate.value.x}, ${currentTranslate.value.y}) scale(${currentZoom.value})`
    )
  }
}

const renderGraph = () => {
  if (!svgElement.value || !mainGroup.value) return

  const nodes = memoryStore.l3Graph.nodes
  const edges = memoryStore.l3Graph.edges

  if (nodes.length === 0) return

  const container = graphContainer.value
  if (!container) return

  const width = container.clientWidth
  const height = 500

  svgElement.value.setAttribute('width', String(width))
  svgElement.value.setAttribute('height', String(height))

  const nodeMap = new Map<string, KGNode>()
  nodes.forEach(n => nodeMap.set(n.id, n))

  const nodePositions = new Map<string, { x: number; y: number }>()
  const centerX = width / 2
  const centerY = height / 2
  const radius = Math.min(width, height) / 3

  nodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / nodes.length
    nodePositions.set(node.id, {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle)
    })
  })

  const edgesLayer = mainGroup.value.querySelector('.edges-layer') as SVGGElement
  const edgeLabelsLayer = mainGroup.value.querySelector('.edge-labels-layer') as SVGGElement
  const nodesLayer = mainGroup.value.querySelector('.nodes-layer') as SVGGElement

  edgesLayer.innerHTML = ''
  edgeLabelsLayer.innerHTML = ''
  nodesLayer.innerHTML = ''

  edges.forEach(edge => {
    const source = nodePositions.get(edge.source)
    const target = nodePositions.get(edge.target)

    if (!source || !target) return

    const midX = (source.x + target.x) / 2
    const midY = (source.y + target.y) / 2

    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line')
    line.setAttribute('x1', String(source.x))
    line.setAttribute('y1', String(source.y))
    line.setAttribute('x2', String(target.x))
    line.setAttribute('y2', String(target.y))
    line.setAttribute('stroke', 'currentColor')
    line.setAttribute('stroke-width', '1.5')
    line.setAttribute('stroke-opacity', '0.5')
    line.setAttribute('marker-end', 'url(#arrowhead)')
    line.classList.add('graph-edge')
    line.style.cursor = 'pointer'

    const sourceNode = nodeMap.get(edge.source)
    const targetNode = nodeMap.get(edge.target)

    line.addEventListener('click', (event: MouseEvent) => {
      if (sourceNode && targetNode) {
        selectedEdge.value = {
          source: edge.source,
          target: edge.target,
          relation: edge.relation,
          sourceNode,
          targetNode
        }
        const containerRect = graphContainer.value?.getBoundingClientRect()
        if (containerRect) {
          edgePopupPosition.value = {
            x: event.clientX - containerRect.left + 10,
            y: event.clientY - containerRect.top + 10
          }
        }
      }
      event.stopPropagation()
    })

    line.addEventListener('mouseenter', () => {
      line.setAttribute('stroke-opacity', '1')
      line.setAttribute('stroke-width', '2.5')
    })

    line.addEventListener('mouseleave', () => {
      line.setAttribute('stroke-opacity', '0.5')
      line.setAttribute('stroke-width', '1.5')
    })

    edgesLayer.appendChild(line)

    const labelText = document.createElementNS('http://www.w3.org/2000/svg', 'text')
    
    labelText.setAttribute('x', String(midX))
    labelText.setAttribute('y', String(midY))
    labelText.setAttribute('text-anchor', 'middle')
    labelText.setAttribute('dominant-baseline', 'middle')
    labelText.setAttribute('fill', 'currentColor')
    labelText.setAttribute('font-size', '10')
    labelText.setAttribute('font-weight', '500')
    labelText.textContent = edge.relation
    labelText.style.pointerEvents = 'none'

    edgesLayer.appendChild(labelText)
  })

  nodes.forEach(node => {
    const pos = nodePositions.get(node.id)
    if (!pos) return

    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g')
    g.classList.add('graph-node')
    g.style.cursor = 'pointer'

    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle')
    circle.setAttribute('cx', String(pos.x))
    circle.setAttribute('cy', String(pos.y))
    circle.setAttribute('r', '20')
    circle.setAttribute('fill', `rgb(var(--v-theme-${getTypeColor(node.label)}))`)
    circle.setAttribute('stroke', 'currentColor')
    circle.setAttribute('stroke-width', '2')

    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text')
    text.setAttribute('x', String(pos.x))
    text.setAttribute('y', String(pos.y + 35))
    text.setAttribute('text-anchor', 'middle')
    text.setAttribute('fill', 'currentColor')
    text.setAttribute('font-size', '12')
    text.textContent = node.name || node.id

    g.appendChild(circle)
    g.appendChild(text)

    g.addEventListener('click', (event: MouseEvent) => {
      selectedNode.value = node
      closeEdgePopup()
      const containerRect = graphContainer.value?.getBoundingClientRect()
      if (containerRect) {
        popupPosition.value = {
          x: event.clientX - containerRect.left + 10,
          y: event.clientY - containerRect.top + 10
        }
      }
    })

    g.addEventListener('mouseenter', () => {
      circle.setAttribute('r', '25')
    })

    g.addEventListener('mouseleave', () => {
      circle.setAttribute('r', '20')
    })

    nodesLayer.appendChild(g)
  })
}

watch(() => memoryStore.l3Graph, () => {
  nextTick(() => {
    renderGraph()
  })
}, { deep: true })

const handleRefresh = () => {
  loadGraph()
}

onMounted(() => {
  loadGraph()
  window.addEventListener('iris:refresh', handleRefresh)
  window.addEventListener('resize', renderGraph)
})

onUnmounted(() => {
  window.removeEventListener('iris:refresh', handleRefresh)
  window.removeEventListener('resize', renderGraph)
})
</script>

<style scoped>
.graph-card {
  min-height: 600px;
}

.graph-container {
  position: relative;
  width: 100%;
  height: 500px;
  background: rgb(var(--v-theme-surface-variant));
  border-radius: 8px;
  overflow: hidden;
}

.graph-svg {
  width: 100%;
  height: 100%;
}

.main-group {
  transition: transform 0.2s ease;
}

.graph-node circle {
  transition: r 0.2s ease;
}

.graph-edge {
  transition: stroke-opacity 0.2s ease, stroke-width 0.2s ease;
}

.arrow-marker {
  fill: rgb(var(--v-theme-on-surface));
  opacity: 0.5;
}

.loading-overlay,
.empty-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgb(var(--v-theme-surface));
  opacity: 0.9;
}

.node-popup {
  position: absolute;
  z-index: 100;
  pointer-events: auto;
  min-width: 200px;
  max-width: 280px;
}

.popup-card {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}
</style>
