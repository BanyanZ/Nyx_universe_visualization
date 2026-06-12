<script setup>
import { computed, onMounted, ref } from 'vue'
import { Activity, Box, ExternalLink, Pause, Play, Sparkles } from 'lucide-vue-next'

const data = ref(null)
const step = ref(50)
const metric = ref('mean')
const viewMode = ref('slice')
const threshold = ref(0.82)
const playing = ref(false)
const baseUrl = import.meta.env.BASE_URL
let timer = null

onMounted(async () => {
  const res = await fetch(`${baseUrl}nyx-data-summary.json`)
  data.value = await res.json()
})

const selectedKeys = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99]

const nearestKey = computed(() => {
  const t = Number(step.value)
  return selectedKeys.reduce((best, k) => Math.abs(k - t) < Math.abs(best - t) ? k : best, 0)
})

const timeline = computed(() => data.value?.timeline ?? [])
const current = computed(() => timeline.value[Number(step.value)] ?? {})
const matrix = computed(() => {
  if (!data.value) return []
  const key = String(nearestKey.value)
  return viewMode.value === 'slice'
    ? data.value.slices[key]?.values ?? []
    : data.value.projection[key]?.values ?? []
})

const hist = computed(() => {
  if (!data.value) return []
  const key = String(nearestKey.value)
  return data.value.histograms[key] ?? []
})

const metricSeries = computed(() => timeline.value.map(d => Number(d[metric.value] ?? 0)))
const metricMin = computed(() => Math.min(...metricSeries.value, 0))
const metricMax = computed(() => Math.max(...metricSeries.value, 1))
const polyline = computed(() => {
  if (!metricSeries.value.length) return ''
  return metricSeries.value.map((v, i) => {
    const x = 18 + i * (364 / Math.max(1, metricSeries.value.length - 1))
    const y = 116 - ((v - metricMin.value) / (metricMax.value - metricMin.value + 1e-9)) * 92
    return `${x.toFixed(2)},${y.toFixed(2)}`
  }).join(' ')
})

const markerX = computed(() => 18 + Number(step.value) * (364 / 99))
const markerY = computed(() => {
  const v = Number(current.value[metric.value] ?? 0)
  return 116 - ((v - metricMin.value) / (metricMax.value - metricMin.value + 1e-9)) * 92
})

const highCells = computed(() => {
  let count = 0
  for (const row of matrix.value) for (const v of row) if (v >= threshold.value) count++
  return count
})

function color(v) {
  const c = Math.max(0, Math.min(1, v))
  if (c < 0.25) return `rgba(7, 18, ${Math.round(46 + c * 160)}, 0.92)`
  if (c < 0.55) return `rgb(${Math.round(20 + c * 90)}, ${Math.round(80 + c * 140)}, ${Math.round(150 + c * 95)})`
  if (c < 0.82) return `rgb(${Math.round(72 + c * 150)}, ${Math.round(65 + c * 50)}, ${Math.round(210 + c * 30)})`
  return `rgb(255, ${Math.round(90 + c * 140)}, ${Math.round(120 + c * 110)})`
}

function togglePlay() {
  playing.value = !playing.value
  if (playing.value) {
    timer = setInterval(() => {
      step.value = Number(step.value) >= 99 ? 0 : Number(step.value) + 1
    }, 420)
  } else {
    clearInterval(timer)
  }
}
</script>

<template>
  <div v-if="data" class="nyx-dash">
    <section class="dash-main glass">
      <div class="toolbar">
        <button class="icon-btn" @click="togglePlay" :title="playing ? '暂停' : '播放'">
          <Pause v-if="playing" :size="18" />
          <Play v-else :size="18" />
        </button>
        <label class="slider-wrap">
          <span>t={{ step }}</span>
          <input v-model="step" type="range" min="0" max="99" />
        </label>
        <div class="segmented">
          <button :class="{ active: viewMode === 'slice' }" @click="viewMode = 'slice'">切片</button>
          <button :class="{ active: viewMode === 'projection' }" @click="viewMode = 'projection'">投影</button>
        </div>
        <label class="slider-wrap small">
          <span>阈值 {{ threshold.toFixed(2) }}</span>
          <input v-model="threshold" type="range" min="0.45" max="0.98" step="0.01" />
        </label>
      </div>

      <div class="visual-row">
        <div class="heatmap" :title="`使用最接近的预览帧 t=${nearestKey}`">
          <template v-for="(row, y) in matrix" :key="y">
            <span
              v-for="(v, x) in row"
              :key="`${x}-${y}`"
              :style="{ background: color(v), opacity: v >= threshold ? 1 : 0.62 }"
              :class="{ hot: v >= threshold }"
            />
          </template>
        </div>

        <div class="chart-stack">
          <div class="chart-card">
            <div class="chart-title">
              <Activity :size="15" />
              <span>统计演化</span>
              <select v-model="metric">
                <option value="mean">Mean</option>
                <option value="std">Std</option>
                <option value="skew">Skew</option>
                <option value="kurtosis">Kurtosis</option>
                <option value="p99">P99</option>
              </select>
            </div>
            <svg viewBox="0 0 400 132" class="line-chart">
              <path d="M18 18 V116 H382" />
              <polyline :points="polyline" />
              <line :x1="markerX" :x2="markerX" y1="20" y2="116" />
              <circle :cx="markerX" :cy="markerY" r="4.5" />
            </svg>
          </div>

          <div class="chart-card">
            <div class="chart-title">
              <Sparkles :size="15" />
              <span>密度分布 t≈{{ nearestKey }}</span>
            </div>
            <div class="bars">
              <span v-for="(v, i) in hist" :key="i" :style="{ height: `${Math.min(100, v * 42)}%` }" />
            </div>
          </div>
        </div>
      </div>
    </section>

    <aside class="side glass">
      <div class="side-title"><Box :size="18" /> Nyx 数据摘要</div>
      <div class="stat"><span>当前均值</span><b>{{ current.mean?.toFixed(3) }}</b></div>
      <div class="stat"><span>标准差</span><b>{{ current.std?.toFixed(3) }}</b></div>
      <div class="stat"><span>P99 高密度阈值</span><b>{{ current.p99?.toFixed(3) }}</b></div>
      <div class="stat"><span>高亮格点</span><b>{{ highCells }}</b></div>
      <div class="note">
        可拖动时间步、切换切片/投影、调整阈值；这里展示的是从真实 `.dat` 数据预处理出的轻量交互摘要。
      </div>
      <a :href="`${baseUrl}nyx-original-showcase.html`" target="_blank" class="open-link">
        打开原网页 <ExternalLink :size="15" />
      </a>
    </aside>
  </div>
  <div v-else class="loading glass">正在载入 Nyx 数据摘要...</div>
</template>

<style scoped>
.nyx-dash {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 270px;
  gap: 16px;
  min-height: 500px;
}

.dash-main,
.side {
  padding: 16px;
}

.toolbar {
  display: grid;
  grid-template-columns: 40px 1fr 160px 210px;
  gap: 12px;
  align-items: center;
  margin-bottom: 14px;
}

.icon-btn,
.segmented button {
  height: 36px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.07);
  color: #fff;
  cursor: pointer;
}

.icon-btn {
  display: grid;
  place-items: center;
}

.segmented {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.segmented button.active {
  border-color: rgba(111, 247, 223, 0.65);
  background: rgba(111, 247, 223, 0.18);
}

.slider-wrap {
  display: grid;
  grid-template-columns: 58px 1fr;
  gap: 8px;
  align-items: center;
  color: rgba(247, 239, 231, 0.86);
  font-size: 13px;
}

.slider-wrap.small {
  grid-template-columns: 86px 1fr;
}

input[type="range"] {
  accent-color: #6ff7df;
}

.visual-row {
  display: grid;
  grid-template-columns: 440px minmax(0, 1fr);
  gap: 14px;
}

.heatmap {
  display: grid;
  grid-template-columns: repeat(64, 1fr);
  grid-template-rows: repeat(64, 1fr);
  width: 440px;
  aspect-ratio: 1;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 8px;
  background: #02030a;
}

.heatmap span {
  box-shadow: inset 0 0 0 0.5px rgba(255, 255, 255, 0.015);
}

.heatmap span.hot {
  box-shadow: 0 0 8px rgba(255, 209, 102, 0.78);
}

.chart-stack {
  display: grid;
  grid-template-rows: 1fr 0.84fr;
  gap: 14px;
}

.chart-card {
  min-height: 0;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.22);
}

.chart-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #f7efe7;
  font-size: 14px;
}

select {
  margin-left: auto;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 6px;
  background: rgba(7, 10, 24, 0.9);
  color: #fff;
  padding: 4px 6px;
}

.line-chart {
  width: 100%;
  height: 150px;
}

.line-chart path {
  fill: none;
  stroke: rgba(255, 255, 255, 0.18);
  stroke-width: 1.2;
}

.line-chart polyline {
  fill: none;
  stroke: #6ff7df;
  stroke-width: 2.4;
}

.line-chart line {
  stroke: #ff4f8b;
  stroke-width: 1.3;
  stroke-dasharray: 4 4;
}

.line-chart circle {
  fill: #ffd166;
  stroke: #fff;
  stroke-width: 1;
}

.bars {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 112px;
  margin-top: 12px;
}

.bars span {
  flex: 1;
  min-width: 2px;
  border-radius: 3px 3px 0 0;
  background: linear-gradient(to top, #45b7ff, #8d5cff, #ff4f8b, #ffd166);
}

.side-title {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 14px;
  color: #fff;
  font-weight: 800;
}

.stat {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
}

.stat span {
  color: rgba(247, 239, 231, 0.68);
}

.stat b {
  color: #fff;
}

.note {
  margin-top: 18px;
  color: rgba(247, 239, 231, 0.72);
  font-size: 14px;
  line-height: 1.55;
}

.open-link {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  margin-top: 18px;
  color: #6ff7df;
}

.loading {
  padding: 24px;
}
</style>
