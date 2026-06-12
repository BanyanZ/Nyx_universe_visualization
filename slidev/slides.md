---
theme: default
title: Nyx 宇宙学数据可视化
info: 基于 Slidev 的 Nyx 宇宙学密度场可视化展示
class: text-left
drawings:
  persist: false
transition: slide-left
canvasWidth: 1536
aspectRatio: 1.6
---

# Nyx 宇宙学数据可视化

<div class="deck-subtitle">
我们把 100 个时间步的三维宇宙密度场，从二进制体数据变成可观察、可筛选、可解释的交互式科学可视化作品。
</div>

<div class="metric-grid">
  <div class="metric glass"><strong>100</strong><span>时间步</span></div>
  <div class="metric glass"><strong>128³</strong><span>每个时间步的三维体素网格</span></div>
  <div class="metric glass"><strong>2.1 亿</strong><span>总体素规模</span></div>
  <div class="metric glass"><strong>4 类</strong><span>体渲染、演化、统计、联动仪表板</span></div>
</div>

---
class: steps-slide
---

<div class="kicker">What We Are Doing</div>

## 我们在做什么

<div class="flow">
  <svg class="flow-path" viewBox="0 0 1180 500" preserveAspectRatio="none" aria-hidden="true">
    <defs>
      <marker id="flow-head" markerWidth="13" markerHeight="13" refX="10" refY="6.5" orient="auto">
        <path d="M 0 0 L 13 6.5 L 0 13 z" class="flow-head" />
      </marker>
    </defs>
    <path v-click="2" class="flow-segment flow-segment-1" d="M 252 104 C 408 44, 552 44, 708 104" marker-end="url(#flow-head)" />
    <path v-click="3" class="flow-segment flow-segment-2" d="M 928 142 C 1052 214, 1052 286, 928 358" marker-end="url(#flow-head)" />
    <path v-click="4" class="flow-segment flow-segment-3" d="M 708 396 C 552 456, 408 456, 252 396" marker-end="url(#flow-head)" />
  </svg>
  <div v-click="1" class="flow-step flow-step-1">
    <span class="flow-index">01</span>
    <b class="pulse-text">读入宇宙密度场</b>
    <p>每个 `.dat` 文件是一个 128×128×128 的 float32 体数据，代表一个时间步的三维密度分布。</p>
  </div>
  <div v-click="2" class="flow-step flow-step-2">
    <span class="flow-index">02</span>
    <b class="pulse-text">构建可视化管线</b>
    <p>把原始数值转换成体渲染、投影图、直方图、脊线图和统计演化曲线。</p>
  </div>
  <div v-click="3" class="flow-step flow-step-3">
    <span class="flow-index">03</span>
    <b class="pulse-text">提取结构和规律</b>
    <p>用均值、标准差、偏度、峰度、P99 等指标观察高密度节点和丝状结构的演化。</p>
  </div>
  <div v-click="4" class="flow-step flow-step-4">
    <span class="flow-index">04</span>
    <b class="pulse-text">做成可展示系统</b>
    <p>最终交付网页、视频、Slidev 演示和可交互仪表板，适合答辩现场讲解。</p>
  </div>
</div>

---

<div class="kicker">Interactive Data</div>

## 真实数据交互预览

<NyxDashboard />

---

<div class="kicker">Pipeline</div>

## 从数据到宇宙结构

<div class="two-col">
  <div class="glass" style="padding: 24px;">
    <h3>数据层</h3>
    <p>原始 Nyx 数据采用 little-endian float32，单个文件 8,388,608 bytes。我们按 Fortran order 还原为 128³ 三维体数据。</p>
    <h3>统计层</h3>
    <p>对每个时间步计算均值、标准差、偏度、峰度、分位数和高密度比例，用于解释整体演化趋势。</p>
  </div>
  <div class="glass" style="padding: 24px;">
    <h3>渲染层</h3>
    <p>使用 VTK GPU Ray Casting 做体渲染，并设计宇宙网配色：空洞变暗，墙和纤维渐亮，高密度节点呈粉红到暖白。</p>
    <h3>交互层</h3>
    <p>通过 Trame、Vuetify、Plotly 实现时间跳转、密度 Brush、空间 ROI、Ridge Plot 点击联动和沉浸式星空模式。</p>
  </div>
  <div class="glass" style="padding: 12px;">
    
  </div>
</div>

---
class: works-slide
---

<div class="kicker">Works</div>

## 我的四个展示成果

<div class="video-grid">
  <div class="video-card glass">
    <video controls loop muted :src="'Nyx_01_volume_animation.mp4'"></video>
    <div>任务 1：Nyx 密度场三维体素 / 粒子动画</div>
  </div>
  <div class="video-card glass">
    <video controls loop muted :src="'Nyx_02_structure_evolution.mp4'"></video>
    <div>任务 2：固定拓扑结构的时间演化展示</div>
  </div>
  <div class="video-card glass">
    <video controls loop muted :src="'Nyx_03_timeseries_statistics.mp4'"></video>
    <div>任务 3：时序统计与分布变化分析</div>
  </div>
  <div class="video-card glass">
    <video controls loop muted :src="'Nyx_04_linked_selection_dashboard.mp4'"></video>
    <div>任务 4：联动筛选仪表板与空间高亮</div>
  </div>
</div>

---

<div class="kicker">NxyVisulization-master</div>

## 交互系统内容

<div class="two-col">
  <div class="glass" style="padding: 22px;">
    <h3>核心功能</h3>
    <ul>
      <li>体渲染和沉浸式粒子星空两套管线</li>
      <li>Cosmic Web / Top 1% / Voids / Filaments / Show All 五种预设</li>
      <li>直方图 Brush 联动 3D 高亮</li>
      <li>2D 投影 ROI 联动空间包围盒和子集统计</li>
      <li>Ridge Plot 与 Stats Evolution 点击跳转时间步</li>
    </ul>
  </div>
  <div class="glass" style="padding: 22px;">
    <h3>技术栈</h3>
    <ul>
      <li>Python + NumPy 读取二进制密度场</li>
      <li>VTK / PyVista 做 GPU 体渲染和粒子系统</li>
      <li>Plotly 生成可交互统计图表</li>
      <li>Trame + Vuetify 构建浏览器端仪表板</li>
      <li>SciPy / Matplotlib / imageio 支持分析与批量导出</li>
    </ul>
  </div>
</div>

---

<div class="kicker">Original Frontend</div>

## 原前端网页入口

<iframe class="embed-frame glass" :src="'nyx-original-showcase.html'"></iframe>

<div class="link-row">
  <a class="pill" :href="'nyx-original-showcase.html'" target="_blank">打开原网页展示</a>
  <span class="small-note">这个页面已经搬到 Slidev 的 public 目录，视频资源也在同一站点内。</span>
</div>

---

<div class="kicker">Presentation Ending</div>

## 结论

<div class="glass" style="padding: 28px; max-width: 920px;">
  <p style="font-size: 24px; line-height: 1.65;">
  这个项目不是单纯播放宇宙动画，而是把 Nyx 模拟数据转换成一套可解释的分析系统：
  从三维密度场看到宇宙网结构，从时间序列看到统计规律，从交互筛选定位高密度节点和空间区域。
  </p>
  <p style="font-size: 20px; color: var(--nyx-muted);">
  展示时可以按顺序讲：数据规模 → 处理管线 → 交互图表 → 四个成果视频 → 原网页入口。
  </p>
</div>
