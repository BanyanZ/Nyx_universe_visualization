# Nyx 可视化成果说明

本文件夹是最终展示成果目录，直接打开 `index.html` 即可查看网页展示。网页中的视频文件使用当前文件夹相对路径引用，请保持 `index.html` 与四个 MP4 文件在同一目录下，否则单独移动 `index.html` 后别人会看不到视频。

## 目录内容

- `index.html`：四个题目的网页展示入口。
- `answerSheet.pdf`：答题说明 PDF。
- `answerSheet.tex`：答题说明 LaTeX 源文件。
- `Nyx/`：原始数据文件夹，包含 `0000.dat` 到 `0099.dat`。
- `NYX01_FIXED_RUN_THIS.py`：题目 1 Blender 脚本。
- `NYX02_FIXED_RUN_THIS.py`：题目 2 Blender 脚本。
- `NYX03_FIXED_RUN_THIS.py`：题目 3 Blender 脚本。
- `nyx_04_interactive_linked_dashboard.py`：题目 4 Blender 脚本。
- `Nyx_01_volume_animation.mp4`：题目 1，Nyx 密度场三维体素/粒子动画。
- `Nyx_02_structure_evolution.mp4`：题目 2，固定拓扑结构演化动画。
- `Nyx_03_timeseries_statistics.mp4`：题目 3，时序统计与分布变化分析。
- `Nyx_04_linked_selection_dashboard.mp4`：题目 4，相空间联动筛选，正方体侧面直方图与空间高亮同步旋转展示。

## Blender 下载

推荐从 Blender 官网下载最新版稳定版：

- 官网下载页：https://www.blender.org/download/
- 历史版本页：https://www.blender.org/download/releases/

Windows 用户可直接下载 Installer 安装版；如果不想安装，也可以下载 Zip 便携版，解压后运行 `blender.exe`。

## 重新生成视频

1. 打开 Blender。
2. 进入顶部菜单 `Scripting`。
3. 点击 `Open`，选择对应的 `.py` 脚本。
4. 运行前先检查脚本开头的路径配置。
5. 点击 `Run Script` 生成场景。
6. 若脚本中 `AUTO_RENDER = False`，需要在 Blender 中按 `Ctrl+F12` 手动渲染动画。

对应脚本：

- 题目 1：`NYX01_FIXED_RUN_THIS.py`
- 题目 2：`NYX02_FIXED_RUN_THIS.py`
- 题目 3：`NYX03_FIXED_RUN_THIS.py`
- 题目 4：`nyx_04_interactive_linked_dashboard.py`

## 路径修改提示

每个 Python 脚本开头都有路径配置。换电脑、换文件夹、提交给别人运行前，请手动修改为实际路径：

```python
PROJECT_DIR = r"C:\你的实际目录\可视化大作业"
```

脚本会从 `PROJECT_DIR/Nyx` 读取 `.dat` 数据，并把 MP4 输出到 `PROJECT_DIR`。如果需要分开数据目录和输出目录，可以继续修改脚本开头的 `DATA_DIR`、`WEB_DIR` 或 `OUTPUT_VIDEO_PATH`。

推荐目录结构：

```text
可视化大作业/
├─ Nyx/
│  ├─ 0000.dat
│  ├─ 0001.dat
│  └─ ...
├─ NYX01_FIXED_RUN_THIS.py
├─ NYX02_FIXED_RUN_THIS.py
├─ NYX03_FIXED_RUN_THIS.py
├─ nyx_04_interactive_linked_dashboard.py
├─ index.html
├─ README.md
├─ answerSheet.pdf
├─ Nyx_01_volume_animation.mp4
├─ Nyx_02_structure_evolution.mp4
├─ Nyx_03_timeseries_statistics.mp4
└─ Nyx_04_linked_selection_dashboard.mp4
```

## 网页视频路径

`index.html` 中的视频地址只写文件名，例如：

```html
<source src="Nyx_01_volume_animation.mp4" type="video/mp4" />
```

这样把整个文件夹发给别人时，网页会直接从同一目录索引视频，不会绑定到某台电脑的本地绝对路径。
