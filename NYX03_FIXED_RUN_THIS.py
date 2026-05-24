import os
import math
import numpy as np
import bpy
from mathutils import Vector

# =========================
# 题目 3：宇宙密度时序统计特征视频
# 在 Blender 中运行：Scripting -> Open/Paste -> Run Script
# 输出：Nyx_03_timeseries_statistics.mp4
# =========================


# 固定到本项目文件夹；在 Blender 里直接粘贴运行时也能找到数据。
PROJECT_DIR = r"C:\Users\Lenovo\Desktop\可视化大作业"


def resolve_base_dir():
    if "__file__" in globals():
        script_dir = os.path.abspath(os.path.dirname(__file__))
        if os.path.isdir(os.path.join(script_dir, "Nyx")):
            return script_dir

    try:
        text = getattr(getattr(bpy.context, "space_data", None), "text", None)
        text_path = getattr(text, "filepath", "")
        if text_path:
            text_dir = os.path.abspath(os.path.dirname(text_path))
            if os.path.isdir(os.path.join(text_dir, "Nyx")):
                return text_dir
    except Exception:
        pass

    return PROJECT_DIR


BASE_DIR = resolve_base_dir()
DATA_DIR = os.path.join(BASE_DIR, "Nyx")
WEB_DIR = BASE_DIR
if not os.path.isdir(DATA_DIR):
    raise FileNotFoundError("DATA_DIR 路径不存在：" + DATA_DIR)
if not os.path.isfile(os.path.join(DATA_DIR, "0000.dat")):
    raise FileNotFoundError("DATA_DIR 中找不到 0000.dat：" + DATA_DIR)
OUTPUT_VIDEO_PATH = os.path.join(WEB_DIR, "Nyx_03_timeseries_statistics.mp4")
AUTO_RENDER = True

GRID_SIZE = 128
SAMPLE_STRIDE = 4
HIST_BINS = 36
ANIMATION_STEP_STRIDE = 4
FRAMES_PER_STEP = 4


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def read_nyx_density(step):
    path = os.path.normpath(os.path.join(DATA_DIR, f"{int(step):04d}.dat"))
    if not os.path.isfile(path):
        raise FileNotFoundError("找不到数据文件：" + path)

    expected = GRID_SIZE ** 3
    expected_bytes = expected * np.dtype("<f4").itemsize
    actual_bytes = os.path.getsize(path)
    if actual_bytes != expected_bytes:
        guessed = round((actual_bytes // np.dtype("<f4").itemsize) ** (1.0 / 3.0))
        raise ValueError(f"时间步 {step:04d} 文件大小为 {actual_bytes} 字节，期望 {expected_bytes} 字节，可尝试 GRID_SIZE={guessed}")

    try:
        with open(path, "rb") as file:
            buffer = file.read()
    except OSError as exc:
        raise OSError("无法打开数据文件：" + path) from exc

    raw = np.frombuffer(buffer, dtype="<f4").copy()
    if raw.size != expected:
        guessed = round(raw.size ** (1.0 / 3.0))
        raise ValueError(f"时间步 {step:04d} 数据量为 {raw.size}，期望 {expected}，可尝试 GRID_SIZE={guessed}")
    return raw.reshape((GRID_SIZE, GRID_SIZE, GRID_SIZE))


def log_sample(volume):
    sampled = volume[::SAMPLE_STRIDE, ::SAMPLE_STRIDE, ::SAMPLE_STRIDE].astype(np.float32)
    min_value = float(np.nanmin(sampled))
    if min_value <= 0:
        sampled = sampled - min_value + 1e-6
    return np.log10(np.nan_to_num(sampled, nan=0.0, posinf=0.0, neginf=0.0) + 1e-6).ravel()


def animation_steps():
    steps = list(range(0, 100, ANIMATION_STEP_STRIDE))
    if steps[-1] != 99:
        steps.append(99)
    return steps


def collect_statistics():
    steps = list(range(100))
    logs_by_step = {}
    rows = []
    for step in steps:
        logged = log_sample(read_nyx_density(step))
        logs_by_step[step] = logged
        rows.append({
            "step": step,
            "mean": float(np.mean(logged)),
            "std": float(np.std(logged)),
            "p99": float(np.percentile(logged, 99.0)),
            "p999": float(np.percentile(logged, 99.9)),
        })
        print(f"统计时间步 {step:04d}")
    all_values = np.concatenate(list(logs_by_step.values()))
    hist_range = tuple(np.percentile(all_values, [0.5, 99.95]))
    global_tail = float(np.percentile(all_values, 99.0))
    for row in rows:
        row["top1_fraction"] = float(np.mean(logs_by_step[row["step"]] >= global_tail))
    return logs_by_step, rows, hist_range, global_tail


def make_material(name, color, alpha=1.0, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = "BLEND"
    mat.diffuse_color = color
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Alpha"].default_value = alpha
        bsdf.inputs["Roughness"].default_value = 0.42
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = color
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def make_emission_material(name, color, strength=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = color
    nodes = mat.node_tree.nodes
    nodes.clear()
    emission = nodes.new(type="ShaderNodeEmission")
    emission.inputs["Color"].default_value = color
    emission.inputs["Strength"].default_value = strength
    output = nodes.new(type="ShaderNodeOutputMaterial")
    mat.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return mat


def add_text(body, location, size=0.11, align="CENTER"):
    bpy.ops.object.text_add(location=location, rotation=(math.radians(63), 0, 0))
    text = bpy.context.object
    text.name = "NYX_03_说明文字"
    text.data.body = body
    text.data.size = size
    text.data.align_x = align
    text.data.materials.append(make_material("NYX_03_文字白", (0.91, 0.96, 1.0, 1.0), emission=0.35))
    return text


def add_bar(name, x, y, z0, width, depth, height, material):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, y, z0 + height / 2.0))
    bar = bpy.context.object
    bar.name = name
    bar.scale = (width, depth, max(height, 0.02))
    bar.data.materials.append(material)
    return bar


def add_curve_line(name, points, material, bevel=0.016):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = bevel
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, co in zip(spline.points, points):
        point.co = (co[0], co[1], co[2], 1.0)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def keyframe_histogram(logs_by_step, hist_range):
    anim_steps = animation_steps()
    x0, y0, z0 = -4.3, -1.95, -1.45
    x_span = 8.2
    z_span = 2.25
    width = x_span / HIST_BINS * 0.72
    normal_mat = make_material("NYX_03_直方图蓝", (0.08, 0.34, 1.0, 0.64), 0.64, 0.32)
    tail_mat = make_material("NYX_03_高密度尾部金", (1.0, 0.58, 0.10, 0.88), 0.88, 0.85)
    axis_mat = make_emission_material("NYX_03_坐标轴", (0.58, 0.95, 1.0, 1.0), 1.0)

    histograms = []
    max_density = 0.0
    for step in anim_steps:
        hist, _ = np.histogram(logs_by_step[step], bins=HIST_BINS, range=hist_range, density=True)
        histograms.append(hist)
        max_density = max(max_density, float(hist.max()))

    bars = []
    for index in range(HIST_BINS):
        x = x0 + (index + 0.5) / HIST_BINS * x_span
        mat = tail_mat if index >= int(HIST_BINS * 0.78) else normal_mat
        bars.append(add_bar(f"NYX_03_动画直方图柱_{index:02d}", x, y0, z0, width, 0.28, 0.03, mat))

    for step_index, step in enumerate(anim_steps):
        frame = 1 + step_index * FRAMES_PER_STEP
        for bar, value in zip(bars, histograms[step_index]):
            height = max(0.025, value / max_density * z_span)
            bar.location.z = z0 + height / 2.0
            bar.scale.z = height
            bar.keyframe_insert("location", frame=frame)
            bar.keyframe_insert("scale", frame=frame)

    add_curve_line("NYX_03_直方图x轴", [(x0, y0, z0), (x0 + x_span, y0, z0)], axis_mat, 0.01)
    add_curve_line("NYX_03_直方图z轴", [(x0, y0, z0), (x0, y0, z0 + z_span + 0.25)], axis_mat, 0.01)
    add_text("动态对数密度直方图：分布展宽并向高密度尾部延伸", (0, y0 - 0.45, z0 + z_span + 0.48), 0.10)
    return 1 + (len(anim_steps) - 1) * FRAMES_PER_STEP


def build_timeseries_curves(rows, frame_end):
    x0, y0, z0 = -4.1, 1.15, -1.25
    x_span = 8.0
    z_span = 2.45
    axis_mat = make_emission_material("NYX_03_曲线坐标轴", (0.58, 0.95, 1.0, 1.0), 1.0)
    add_curve_line("NYX_03_曲线x轴", [(x0, y0, z0), (x0 + x_span, y0, z0)], axis_mat, 0.01)
    add_curve_line("NYX_03_曲线z轴", [(x0, y0, z0), (x0, y0, z0 + z_span + 0.25)], axis_mat, 0.01)

    steps = np.array([row["step"] for row in rows], dtype=np.float32)
    metrics = [
        ("p99", np.array([row["p99"] for row in rows]), make_emission_material("NYX_03_p99玫红", (1.0, 0.15, 0.86, 1.0), 2.0), "p99"),
        ("p999", np.array([row["p999"] for row in rows]), make_emission_material("NYX_03_p999金", (1.0, 0.67, 0.08, 1.0), 2.3), "p99.9"),
        ("std", np.array([row["std"] for row in rows]), make_emission_material("NYX_03_std青", (0.10, 0.92, 1.0, 1.0), 1.8), "std"),
    ]
    curve_lookup = {}
    for offset, (name, values, mat, label) in enumerate(metrics):
        lo = float(values.min())
        hi = float(values.max())
        points = []
        for step, value in zip(steps, values):
            x = x0 + (step - steps.min()) / max(float(steps.max() - steps.min()), 1.0) * x_span
            z = z0 + (value - lo) / max(hi - lo, 1e-6) * z_span
            points.append((x, y0 - offset * 0.15, z))
        add_curve_line(f"NYX_03_时序曲线_{name}", points, mat, 0.015)
        add_text(label, (x0 + x_span + 0.34, y0 - offset * 0.15, points[-1][2]), 0.07, "LEFT")
        curve_lookup[name] = (values, lo, hi, y0 - offset * 0.15)

    cursor_mat = make_emission_material("NYX_03_时间游标", (1.0, 0.95, 0.25, 1.0), 2.5)
    add_curve_line("NYX_03_时间游标线", [(x0, y0 + 0.22, z0), (x0, y0 + 0.22, z0 + z_span + 0.25)], cursor_mat, 0.018)
    cursor = bpy.data.objects["NYX_03_时间游标线"]
    cursor.location.x = 0.0
    cursor.keyframe_insert("location", frame=1)
    cursor.location.x = x_span
    cursor.keyframe_insert("location", frame=frame_end)

    marker_values, lo, hi, marker_y = curve_lookup["p999"]
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.08, location=(x0, marker_y, z0))
    marker = bpy.context.object
    marker.name = "NYX_03_p999动态标记"
    marker.data.materials.append(cursor_mat)
    for step_index, step in enumerate(animation_steps()):
        frame = 1 + step_index * FRAMES_PER_STEP
        value = marker_values[step]
        marker.location.x = x0 + step / 99.0 * x_span
        marker.location.z = z0 + (value - lo) / max(hi - lo, 1e-6) * z_span
        marker.keyframe_insert("location", frame=frame)

    add_text("时序统计曲线：标准差、p99、p99.9 量化团块化增强", (0, y0 + 0.55, z0 + z_span + 0.50), 0.105)


def setup_scene(frame_end):
    try:
        bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        bpy.context.scene.render.engine = "BLENDER_EEVEE"
    eevee = getattr(bpy.context.scene, "eevee", None)
    if eevee and hasattr(eevee, "use_bloom"):
        eevee.use_bloom = True
        eevee.bloom_intensity = 0.15
    bpy.context.scene.world = bpy.data.worlds.new("Nyx 03 深空背景") if bpy.context.scene.world is None else bpy.context.scene.world
    bpy.context.scene.world.color = (0.0, 0.0, 0.003)
    bpy.context.scene.view_settings.view_transform = "Standard"
    bpy.context.scene.view_settings.look = "Medium High Contrast"
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frame_end
    bpy.context.scene.render.fps = 18
    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080
    bpy.context.scene.render.filepath = OUTPUT_VIDEO_PATH
    bpy.context.scene.render.image_settings.file_format = "FFMPEG"
    bpy.context.scene.render.ffmpeg.format = "MPEG4"
    bpy.context.scene.render.ffmpeg.codec = "H264"
    bpy.context.scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    bpy.context.scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    bpy.context.scene.render.ffmpeg.audio_codec = "NONE"

    bpy.ops.object.light_add(type="AREA", location=(0, -5.8, 5.0))
    light = bpy.context.object
    light.name = "NYX_03_统计主光"
    light.data.energy = 300
    light.data.size = 7.0

    bpy.ops.object.camera_add(location=(0, -8.8, 4.25), rotation=(math.radians(61), 0, 0))
    camera = bpy.context.object
    bpy.context.scene.camera = camera
    direction = Vector((0, -0.25, 0.20)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 36


def main():
    clear_scene()
    logs_by_step, rows, hist_range, global_tail = collect_statistics()
    frame_end = keyframe_histogram(logs_by_step, hist_range)
    build_timeseries_curves(rows, frame_end)
    add_text("Nyx 密度时序统计特征分析", (0, -2.65, 2.72), 0.18)
    add_text(f"100 个时间步 | 采样步长 1/{SAMPLE_STRIDE} | 全局 Top1% 阈值 log10(density)={global_tail:.3f}", (0, -2.65, 2.47), 0.08)
    setup_scene(frame_end)
    print("题目 3 完成：已设置为 MP4 动画输出，按 Ctrl+F12 渲染到", OUTPUT_VIDEO_PATH)
    if AUTO_RENDER:
        bpy.ops.render.render(animation=True)


main()
