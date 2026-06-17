# Nyx Cosmic Density Visualization

Nyx 宇宙学模拟密度场数据的交互式可视化系统。基于 Python + Trame 构建，浏览器直接访问沉浸式 3D 仪表板，支持体渲染、粒子星空、多视图联动与时序统计分析。

## 功能概览

| 赛题任务 | 功能 | 实现方式 |
|---------|------|---------|
| 任务一 · 体数据渲染 | 多级传递函数 + 沉浸式粒子星空 | GPU Ray Casting (纯自发光模式) / 多层粒子系统 (Star、Mist、Nebula、Glow、Veil、Field) |
| 任务二 · 演化规律归纳 | 宇宙大尺度结构演化分析 | 基于统计指标的自动化分析，支持 click-to-jump 跳转时间步 |
| 任务三 · 时序统计分析 | 密度分布直方图、脊线图、统计量演化曲线 | Plotly 交互图表，支持框选联动和点击跳转 |
| 任务四 · 交互仪表板 | 双向联动仪表板 | Trame Web 应用: 直方图框选 <-> 3D 体渲染 + 投影图框选 <-> 空间 ROI |

## 界面设计

- **Glassmorphism 风格** — 磨砂半透明浮动面板 (`backdrop-filter: blur(18px)`)，覆盖于全屏 3D 场景之上
- **自定义暗色主题** — 统一色板：`#1a1a2e` → `#16213e` → `#0f3460` → `#533483` → `#e94560` → `#fcd5ce`
- **沉浸模式 (Immersive)** — 关闭体渲染，切换至多层粒子星空管线，模拟 Star Walk 式宇宙体验

## 数据集准备

项目需要 Nyx 模拟输出的密度场时序数据：

```
FinalWork/
└── 1-IINyx_dataset/
    └── Nyx/
        ├── 0000.dat      ← 第 0 个时间步
        ├── 0001.dat
        ├── ...
        └── 0099.dat      ← 第 99 个时间步 (共 100 个文件)
```

**数据格式：**
- 每个 `.dat` 文件为 128x128x128 三维密度场
- 数据类型：little-endian float32 (每文件 8,388,608 字节 = 128^3 x 4 bytes)
- 存储顺序：列优先 (Fortran order)，即 z -> y -> x

如数据集放在其他位置，修改 `nyx/data.py` 中的 `DATA_DIR` 变量。

## 环境安装

需要 Python 3.10+。

```bash
pip install -r requirements.txt
```

核心依赖：trame (>= 3.13)、PyVista (>= 0.48)、VTK (>= 9.6)、Plotly (>= 6.0)、NumPy、SciPy。

## 使用方式

### 交互式仪表板

```bash
python app.py
```

启动后浏览器打开 `http://localhost:8080`。

#### 界面布局

| 区域 | 内容 |
|------|------|
| **顶栏** | 播放/暂停、时间步滑块 (0-99)、3D/2D Proj 视图切换、Immersive 开关、Rotate 开关 |
| **左侧面板** | 预设按钮 (Cosmic Web / Top 1% / Voids / Filaments / Show All)、渲染选项 (Isosurface)、分析入口 (Ridge Plot / Stats Evolution) |
| **左下角** | 实时统计面板 (Mean、Std、Skew、Kurt、Range、P99) |
| **右下角** | 密度直方图 (支持框选触发密度 Brush) |
| **主区域** | 3D 体渲染视图 或 2D 投影热力图 |

#### 交互操作

- **密度 Brush** — 在直方图上框选密度区间，3D 视图自动高亮对应体素
- **空间 ROI** — 在 2D 投影图上框选区域，3D 视图显示 wireframe 包围盒，统计面板更新为 ROI 子集
- **联动面板** — Brush 和 ROI 激活时出现 Linked View 面板，展示选择统计和 Focus 3D 按钮
- **点击跳转** — 在 Ridge Plot 中点击任意脊线、在 Stats Evolution 中点击数据点，自动跳转对应时间步
- **沉浸模式** — 开启 Immersive 开关，体渲染切换为多层粒子星空，支持拖拽旋转和缩放自适应 LOD

### 批量导出

```bash
python batch_export.py --render       # 渲染关键帧 PNG (t=0,25,50,75,99)
python batch_export.py --iso          # 体渲染 + 等值面叠加
python batch_export.py --projection   # 投影密度图
python batch_export.py --panel        # 多面板时间演化拼图
python batch_export.py --animate      # 渲染全部 100 帧 + 导出 MP4/GIF
python batch_export.py --stats        # 统计演化图表 (HTML)
python batch_export.py --ridge        # 脊线图 (HTML)
python batch_export.py --all          # 以上全部
```

输出保存在 `output/` 目录。

## 项目结构

```
FinalWork/
├── app.py                     # Trame 交互仪表板 (主入口, ~1790 行)
├── batch_export.py            # 批量渲染/导出脚本
├── requirements.txt           # Python 依赖
├── nyx/                       # 核心模块
│   ├── data.py                # 数据加载 (二进制 -> NumPy -> VTK ImageData)
│   ├── stats.py               # 统计分析 + Plotly 图表
│   ├── transfer_functions.py  # 传递函数 (颜色 + 不透明度映射)
│   ├── volume.py              # VTK 体渲染管线
│   ├── visualizations.py      # 投影图、等值面、多面板拼图
│   └── postprocess.py         # 后处理 (sigma clip / bloom / Reinhard)
├── 1-IINyx_dataset/           # 数据集目录 (需自行放置)
│   └── Nyx/
│       └── *.dat
└── output/                    # 渲染输出
    └── frames/
```

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      浏览器 (Chrome/Edge)                    │
│  VtkRemoteView (服务端渲染流式推送) + Plotly 交互图表          │
└───────────────────────┬─────────────────────────────────────┘
                        │ WebSocket
┌───────────────────────┴─────────────────────────────────────┐
│                    Trame Web 服务                             │
│  Vuetify 3 组件 + 自定义 Glassmorphism 主题                    │
├─────────────────────────────────────────────────────────────┤
│  交互层    Plotly 直方图框选 / 投影图框选 / Ridge 点击跳转      │
│  联动层    密度 Brush -> 3D 高亮 / 空间 ROI -> 统计子集        │
├─────────────────────────────────────────────────────────────┤
│  渲染层    VTK GPU Ray Casting (纯自发光)                      │
│           PyVista Glyph 粒子系统 (Immersive 模式)              │
│           后处理: Sigma Clip -> Bloom -> Reinhard -> Gamma    │
├─────────────────────────────────────────────────────────────┤
│  统计层    SciPy (skewness/kurtosis) + NumPy 直方图/分位数     │
│  数据层    NumPy float32 二进制读取 + Gamma=4 对比度增强        │
└─────────────────────────────────────────────────────────────┘
```

### 渲染管线

**标准模式 (Volume Rendering)**
- `vtkSmartVolumeMapper` GPU Ray Casting
- 纯自发光模式 (`ShadeOff()`)，无 Phong 着色
- 物理驱动传递函数：空洞 (黑) -> 薄壁 (深蓝) -> 纤维 (紫) -> 节点 (红粉) -> 峰值 (白)
- 5 种预设 + 密度 Brush 自定义不透明度

**沉浸模式 (Immersive Starfield)**
- 独立粒子渲染管线，关闭体渲染
- 密度加权重要性采样 (density^1.75)，最高 120k 粒子
- 6 层渲染叠加：Field Stars / Background / Main / Mist / Nebula Glow / Veil
- 相机感知视锥剔除 + 自适应 LOD (zoom ratio 0.38-2.3x)
- 数据驱动的各向同性场星平铺 + 旋转去栅格化
- 异步监控循环 (`_immersive_sync_loop`)，每 220ms 检测相机变化

### 联动机制

- **直方图 -> 3D**：框选密度区间 -> `make_brushed_otf()` 更新不透明度 -> 点云高亮采样体素
- **投影图 -> 3D**：框选空间区域 -> wireframe 包围盒 -> 统计面板切换为 ROI 子集
- **Ridge/Stats -> 时间步**：点击图表数据点 -> `_jump_to_timestep()` -> 全视图同步更新
- **Focus 3D**：自动计算包围盒相机位姿，平滑聚焦选中区域
