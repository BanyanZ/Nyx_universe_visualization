import os
import math
import numpy as np
import bpy
from mathutils import Vector


# =========================
# 题目 4：相空间联动筛选可视分析视频（侧面直方图 + 正方体旋转版）
# 在 Blender 中运行：Scripting -> Open -> 选择本文件 -> Run Script
# 输出：visualize__/Nyx_04_linked_selection_dashboard.mp4
# =========================


# 固定到本项目文件夹；在 Blender 里直接粘贴运行时也能找到数据。
PROJECT_DIR = r"C:\Users\Lenovo\Desktop\Nyx宇宙学数据可视化"


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

OUTPUT_VIDEO_PATH = os.path.join(WEB_DIR, "Nyx_04_linked_selection_dashboard.mp4")
AUTO_RENDER = False

GRID_SIZE = 128
DOWNSAMPLE = 5
HIST_BINS = 28
MAX_POINTS = 1150
KEY_STEP_STRIDE = 9
FRAMES_PER_KEY = 9
FPS = 18

SPACE_CENTER = Vector((0.0, 0.0, 0.0))
SPACE_SIZE = 5.15
HIST_WIDTH = 3.08
HIST_HEIGHT = 1.78

POINT_RADIUS_OFF = 0.010
POINT_RADIUS_MIN = 0.055
POINT_RADIUS_MAX = 0.155
ROTATE_SPACE_VIEW = True
ROTATION_DEGREES = 360
PREFIX = "NYX04_"
MATS = {}


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def key_steps():
    steps = list(range(0, 100, KEY_STEP_STRIDE))
    if steps[-1] != 99:
        steps.append(99)
    return steps


def read_density(step):
    path = os.path.normpath(os.path.join(DATA_DIR, f"{int(step):04d}.dat"))
    if not os.path.isfile(path):
        raise FileNotFoundError("找不到数据文件：" + path)
    dtype = np.dtype("<f4")
    expected = GRID_SIZE ** 3
    expected_bytes = expected * dtype.itemsize
    actual_bytes = os.path.getsize(path)
    if actual_bytes != expected_bytes:
        guessed = round((actual_bytes // dtype.itemsize) ** (1.0 / 3.0))
        raise ValueError(f"时间步 {step:04d} 文件大小为 {actual_bytes} 字节，期望 {expected_bytes} 字节，可尝试 GRID_SIZE={guessed}")
    with open(path, "rb") as file:
        buffer = file.read()
    raw = np.frombuffer(buffer, dtype=dtype).copy()
    if raw.size != expected:
        guessed = round(raw.size ** (1.0 / 3.0))
        raise ValueError(f"时间步 {step:04d} 数据量为 {raw.size}，期望 {expected}，可尝试 GRID_SIZE={guessed}")
    return raw.reshape((GRID_SIZE, GRID_SIZE, GRID_SIZE))


def read_log_sample(step):
    volume = read_density(step)[::DOWNSAMPLE, ::DOWNSAMPLE, ::DOWNSAMPLE]
    volume = np.nan_to_num(volume.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    min_value = float(volume.min())
    if min_value <= 0:
        volume = volume - min_value + 1e-6
    return np.log10(volume + 1e-6)


def collect_data():
    steps = key_steps()
    logs = {}
    samples = []
    for step in steps:
        logged = read_log_sample(step)
        logs[step] = logged
        samples.append(logged.ravel())
        print(f"题目 4 读取时间步 {step:04d}")

    all_values = np.concatenate(samples)
    log_range = tuple(np.percentile(all_values, [0.8, 99.9]))
    lo, hi = log_range
    normalized = {}
    for step, logged in logs.items():
        normalized[step] = np.clip((logged - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    return steps, logs, normalized, log_range


def percentile_band(index, total):
    progress = index / max(total - 1, 1)
    return 96.0 + 3.3 * progress, 100.0


def make_material(name, color, alpha=1.0, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = "BLEND"
    mat.diffuse_color = color
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Alpha"].default_value = alpha
        bsdf.inputs["Roughness"].default_value = 0.50
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


def setup_materials():
    MATS["panel"] = make_material("NYX04_hist_panel", (0.015, 0.055, 0.11, 0.40), 0.40, 0.08)
    MATS["hist"] = make_material("NYX04_hist_blue", (0.08, 0.30, 0.95, 0.50), 0.50, 0.16)
    MATS["hist_tail"] = make_material("NYX04_hist_tail", (0.95, 0.52, 0.10, 0.70), 0.70, 0.44)
    MATS["hist_select"] = make_material("NYX04_hist_selected_bins", (1.0, 0.88, 0.10, 0.86), 0.86, 1.15)
    MATS["band"] = make_material("NYX04_selected_band", (1.0, 0.78, 0.12, 0.25), 0.25, 0.55)
    MATS["axis"] = make_emission_material("NYX04_axis", (0.50, 0.86, 1.0, 1.0), 0.85)
    MATS["line"] = make_emission_material("NYX04_threshold", (1.0, 0.92, 0.20, 1.0), 1.75)
    MATS["dim"] = make_emission_material("NYX04_dim_points", (0.05, 0.18, 0.40, 0.22), 0.18)
    MATS["selected"] = make_emission_material("NYX04_selected_points", (0.15, 0.68, 1.0, 0.88), 1.35)
    MATS["core"] = make_emission_material("NYX04_core_points", (1.0, 0.72, 0.18, 1.0), 3.0)
    MATS["text"] = make_material("NYX04_text", (0.88, 0.94, 1.0, 1.0), 1.0, 0.25)
    MATS["panel_text"] = make_emission_material("NYX04_panel_text", (0.94, 0.98, 1.0, 1.0), 1.25)


def add_text(name, body, location, size=0.055, align="CENTER"):
    bpy.ops.object.text_add(location=location, rotation=(math.radians(66), 0, 0))
    text = bpy.context.object
    text.name = PREFIX + name
    text.data.body = body
    text.data.size = size
    text.data.align_x = align
    text.data.materials.append(MATS["text"])
    return text


def add_panel_text(name, body, y, z, size=0.10, align="CENTER", pivot=None):
    x = SPACE_CENTER.x - SPACE_SIZE * 0.5 - 0.18
    bpy.ops.object.text_add(location=(x, y, z), rotation=(0, math.radians(90), math.radians(90)))
    text = bpy.context.object
    text.name = PREFIX + name
    text.data.body = body
    text.data.size = size
    text.data.align_x = align
    text.data.align_y = "CENTER"
    text.data.materials.append(MATS["panel_text"])
    parent_to_pivot(text, pivot)
    return text


def add_curve(name, points, material, bevel=0.006):
    curve = bpy.data.curves.new(PREFIX + name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = bevel
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, co in zip(spline.points, points):
        point.co = (co[0], co[1], co[2], 1.0)
    obj = bpy.data.objects.new(PREFIX + name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def add_cube(name, location, scale, material):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = PREFIX + name
    obj.scale = scale
    obj.data.materials.append(material)
    return obj


def parent_to_pivot(obj, pivot):
    if pivot is not None:
        obj.parent = pivot
    return obj


def create_rotation_pivot():
    pivot = bpy.data.objects.new(PREFIX + "cube_rotation_pivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.empty_display_type = "PLAIN_AXES"
    pivot.empty_display_size = 0.45
    pivot.location = SPACE_CENTER
    return pivot


def animate_rotation_pivot(pivot, frame_end):
    if not ROTATE_SPACE_VIEW or pivot is None:
        return
    pivot.rotation_euler[2] = math.radians(-48)
    pivot.keyframe_insert("rotation_euler", frame=1)
    pivot.rotation_euler[2] = math.radians(-48 + ROTATION_DEGREES)
    pivot.keyframe_insert("rotation_euler", frame=frame_end)
    if pivot.animation_data and pivot.animation_data.action:
        for fcurve in pivot.animation_data.action.fcurves:
            for point in fcurve.keyframe_points:
                point.interpolation = "LINEAR"


def add_dynamic_status_text(steps, selected_counts, point_count):
    for idx, step in enumerate(steps):
        frame = 1 + idx * FRAMES_PER_KEY
        low, high = percentile_band(idx, len(steps))
        ratio = selected_counts[idx] / max(point_count, 1) * 100.0
        body = f"时间步 {step:04d} | 刷选 {low:.1f}-{high:.0f} 百分位 | 命中 {selected_counts[idx]}/{point_count} ({ratio:.1f}%)"
        text = add_text(f"dynamic_status_{step:04d}", body, (0.0, -3.60, 2.86), 0.058)
        text.hide_viewport = True
        text.hide_render = True
        text.keyframe_insert("hide_viewport", frame=max(1, frame - 1))
        text.keyframe_insert("hide_render", frame=max(1, frame - 1))
        text.hide_viewport = False
        text.hide_render = False
        text.keyframe_insert("hide_viewport", frame=frame)
        text.keyframe_insert("hide_render", frame=frame)
        text.keyframe_insert("hide_viewport", frame=frame + FRAMES_PER_KEY - 1)
        text.keyframe_insert("hide_render", frame=frame + FRAMES_PER_KEY - 1)
        text.hide_viewport = True
        text.hide_render = True
        text.keyframe_insert("hide_viewport", frame=frame + FRAMES_PER_KEY)
        text.keyframe_insert("hide_render", frame=frame + FRAMES_PER_KEY)


def build_histogram(steps, logs, log_range, pivot=None):
    x0 = SPACE_CENTER.x - SPACE_SIZE * 0.5 - 0.035
    y0 = SPACE_CENTER.y - HIST_WIDTH * 0.5
    z0 = SPACE_CENTER.z - HIST_HEIGHT * 0.5
    bar_x = x0 - 0.055
    line_x = x0 - 0.105
    bar_width = HIST_WIDTH / HIST_BINS * 0.58
    hists = []
    max_hist = 0.0
    for step in steps:
        hist, _ = np.histogram(logs[step].ravel(), bins=HIST_BINS, range=log_range, density=True)
        hists.append(hist)
        max_hist = max(max_hist, float(hist.max()))

    panel = add_cube(
        "hist_panel_on_cube_face",
        (x0 + 0.006, SPACE_CENTER.y, SPACE_CENTER.z),
        (0.024, HIST_WIDTH + 0.34, HIST_HEIGHT + 0.34),
        MATS["panel"],
    )
    parent_to_pivot(panel, pivot)
    add_panel_text("hist_title", "密度直方图", SPACE_CENTER.y, z0 + HIST_HEIGHT + 0.30, 0.18, "CENTER", pivot)
    add_panel_text("hist_x_label", "log10 density  ->", SPACE_CENTER.y, z0 - 0.22, 0.075, "CENTER", pivot)
    add_panel_text("hist_y_label", "cell count", y0 - 0.28, z0 + HIST_HEIGHT * 0.52, 0.070, "CENTER", pivot)
    add_panel_text("hist_select_label", "黄色柱 = 当前刷选尾部", SPACE_CENTER.y, z0 + HIST_HEIGHT + 0.10, 0.085, "CENTER", pivot)

    bars = []
    selected_bars = []
    for i in range(HIST_BINS):
        y = y0 + (i + 0.5) / HIST_BINS * HIST_WIDTH
        material = MATS["hist_tail"] if i >= int(HIST_BINS * 0.78) else MATS["hist"]
        bar = add_cube(f"hist_bar_{i:02d}", (bar_x, y, z0 + 0.012), (0.075, bar_width, 0.018), material)
        parent_to_pivot(bar, pivot)
        bars.append(bar)
        selected_bar = add_cube(f"hist_selected_bar_{i:02d}", (bar_x - 0.105, y, z0 + 0.004), (0.055, bar_width * 0.88, 0.001), MATS["hist_select"])
        parent_to_pivot(selected_bar, pivot)
        selected_bars.append(selected_bar)

    parent_to_pivot(add_curve("hist_y_axis", [(line_x, y0, z0), (line_x, y0 + HIST_WIDTH, z0)], MATS["axis"], 0.008), pivot)
    parent_to_pivot(add_curve("hist_z_axis", [(line_x, y0, z0), (line_x, y0, z0 + HIST_HEIGHT + 0.08)], MATS["axis"], 0.008), pivot)
    low_line = add_curve("low_threshold", [(line_x - 0.018, y0, z0), (line_x - 0.018, y0, z0 + HIST_HEIGHT + 0.08)], MATS["line"], 0.014)
    high_line = add_curve("high_threshold", [(line_x - 0.018, y0, z0), (line_x - 0.018, y0, z0 + HIST_HEIGHT + 0.08)], MATS["line"], 0.014)
    parent_to_pivot(low_line, pivot)
    parent_to_pivot(high_line, pivot)
    band = add_cube("threshold_band", (line_x - 0.035, y0, z0 + HIST_HEIGHT * 0.5), (0.020, 0.018, HIST_HEIGHT * 0.5), MATS["band"])
    parent_to_pivot(band, pivot)

    lo, hi = log_range
    bin_edges = np.linspace(lo, hi, HIST_BINS + 1)
    for idx, step in enumerate(steps):
        frame = 1 + idx * FRAMES_PER_KEY
        band_low, band_high = percentile_band(idx, len(steps))
        q_low = float(np.percentile(logs[step], band_low))
        q_high = float(np.percentile(logs[step], band_high))
        low_y = np.clip((q_low - lo) / max(hi - lo, 1e-6), 0.0, 1.0) * HIST_WIDTH
        high_y = np.clip((q_high - lo) / max(hi - lo, 1e-6), 0.0, 1.0) * HIST_WIDTH

        for bar, selected_bar, value, bin_left, bin_right in zip(bars, selected_bars, hists[idx], bin_edges[:-1], bin_edges[1:]):
            height = max(0.012, value / max(max_hist, 1e-6) * HIST_HEIGHT)
            bar.location.z = z0 + height / 2.0
            bar.scale.z = height
            bar.keyframe_insert("location", frame=frame)
            bar.keyframe_insert("scale", frame=frame)

            selected_height = height if (bin_left <= q_high and bin_right >= q_low) else 0.001
            selected_bar.location.z = z0 + selected_height / 2.0
            selected_bar.scale.z = selected_height
            selected_bar.keyframe_insert("location", frame=frame)
            selected_bar.keyframe_insert("scale", frame=frame)

        low_line.location.y = low_y
        high_line.location.y = high_y
        low_line.keyframe_insert("location", frame=frame)
        high_line.keyframe_insert("location", frame=frame)

        band.location.y = y0 + (low_y + high_y) * 0.5
        band.scale.y = max((high_y - low_y) * 0.5, 0.018)
        band.keyframe_insert("location", frame=frame)
        band.keyframe_insert("scale", frame=frame)


def select_candidate_points(steps, normalized):
    max_field = None
    for step in steps:
        field = normalized[step]
        max_field = field.copy() if max_field is None else np.maximum(max_field, field)
    threshold = np.percentile(max_field, 96.6)
    points = np.argwhere(max_field >= threshold)
    values = max_field[max_field >= threshold]
    if len(points) > MAX_POINTS:
        order = np.argsort(values)[-MAX_POINTS:]
        points = points[order]
    return points


def point_mesh(points, values, selected, shape):
    cell = SPACE_SIZE / shape[0]
    half = shape[0] * cell / 2.0
    octa = [(0, 0, 1), (1, 0, 0), (0, 1, 0), (-1, 0, 0), (0, -1, 0), (0, 0, -1)]
    faces_template = [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1), (5, 2, 1), (5, 3, 2), (5, 4, 3), (5, 1, 4)]
    vertices = []
    faces = []
    material_ids = []

    for (z, y, x), value, is_selected in zip(points, values, selected):
        strength = float(np.clip((value - 0.62) / 0.38, 0.0, 1.0))
        radius = POINT_RADIUS_OFF if not is_selected else POINT_RADIUS_MIN + strength * (POINT_RADIUS_MAX - POINT_RADIUS_MIN)
        cx = SPACE_CENTER.x + (x + 0.5) * cell - half
        cy = SPACE_CENTER.y + (y + 0.5) * cell - half
        cz = SPACE_CENTER.z + (z + 0.5) * cell - half
        start = len(vertices)
        for dx, dy, dz in octa:
            vertices.append((cx + dx * radius, cy + dy * radius, cz + dz * radius))
        mat_id = 0 if not is_selected else (2 if strength > 0.72 else 1)
        for face in faces_template:
            faces.append(tuple(start + i for i in face))
            material_ids.append(mat_id)
    return vertices, faces, material_ids


def build_spatial_view(steps, logs, normalized, pivot=None):
    points = select_candidate_points(steps, normalized)
    first_step = steps[0]
    first_values = normalized[first_step][tuple(points.T)]
    first_selected = np.ones(len(points), dtype=bool)
    vertices, faces, material_ids = point_mesh(points, first_values, first_selected, normalized[first_step].shape)

    mesh = bpy.data.meshes.new(PREFIX + "spatial_points_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(PREFIX + "spatial_points", mesh)
    bpy.context.collection.objects.link(obj)
    parent_to_pivot(obj, pivot)
    obj.data.materials.append(MATS["dim"])
    obj.data.materials.append(MATS["selected"])
    obj.data.materials.append(MATS["core"])
    for poly, mat_id in zip(obj.data.polygons, material_ids):
        poly.material_index = mat_id

    obj.shape_key_add(name="Basis")
    selected_counts = []
    for idx, step in enumerate(steps):
        low, high = percentile_band(idx, len(steps))
        q_low = float(np.percentile(logs[step], low))
        q_high = float(np.percentile(logs[step], high))
        step_logs = logs[step][tuple(points.T)]
        values = normalized[step][tuple(points.T)]
        selected = np.logical_and(step_logs >= q_low, step_logs <= q_high)
        selected_counts.append(int(np.count_nonzero(selected)))
        verts, _, _ = point_mesh(points, values, selected, normalized[step].shape)
        key = obj.shape_key_add(name=f"step_{step:04d}")
        for vertex, co in zip(key.data, verts):
            vertex.co = co
        frame = 1 + idx * FRAMES_PER_KEY
        key.value = 0.0
        key.keyframe_insert("value", frame=max(1, frame - FRAMES_PER_KEY))
        key.value = 1.0
        key.keyframe_insert("value", frame=frame)
        key.value = 0.0
        key.keyframe_insert("value", frame=frame + FRAMES_PER_KEY)

    if obj.data.shape_keys and obj.data.shape_keys.animation_data:
        action = obj.data.shape_keys.animation_data.action
        if action:
            for fcurve in action.fcurves:
                for point in fcurve.keyframe_points:
                    point.interpolation = "LINEAR"

    box_mat = make_material("NYX04_box", (0.06, 0.25, 0.48, 0.050), 0.050, 0.04)
    bpy.ops.mesh.primitive_cube_add(size=SPACE_SIZE, location=SPACE_CENTER)
    box = bpy.context.object
    box.name = PREFIX + "spatial_box"
    parent_to_pivot(box, pivot)
    box.data.materials.append(box_mat)
    wire = box.modifiers.new("space_wire", "WIREFRAME")
    wire.thickness = 0.007
    return len(points), selected_counts


def setup_scene(frame_end):
    try:
        bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        bpy.context.scene.render.engine = "BLENDER_EEVEE"
    eevee = getattr(bpy.context.scene, "eevee", None)
    if eevee:
        if hasattr(eevee, "use_bloom"):
            eevee.use_bloom = True
        if hasattr(eevee, "bloom_intensity"):
            eevee.bloom_intensity = 0.07

    bpy.context.scene.world = bpy.data.worlds.new("NYX04_world") if bpy.context.scene.world is None else bpy.context.scene.world
    bpy.context.scene.world.color = (0.0, 0.0, 0.004)
    bpy.context.scene.view_settings.view_transform = "Standard"
    bpy.context.scene.view_settings.look = "Medium High Contrast"
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frame_end
    bpy.context.scene.render.fps = FPS
    bpy.context.scene.render.resolution_x = 1280
    bpy.context.scene.render.resolution_y = 720
    bpy.context.scene.render.filepath = OUTPUT_VIDEO_PATH
    bpy.context.scene.render.image_settings.file_format = "FFMPEG"
    bpy.context.scene.render.ffmpeg.format = "MPEG4"
    bpy.context.scene.render.ffmpeg.codec = "H264"
    bpy.context.scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    bpy.context.scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    bpy.context.scene.render.ffmpeg.audio_codec = "NONE"

    bpy.ops.object.light_add(type="AREA", location=(0, -6.4, 6.0))
    light = bpy.context.object
    light.name = PREFIX + "key_light"
    light.data.energy = 320
    light.data.size = 7.0

    bpy.ops.object.camera_add(location=(6.7, -7.4, 5.25), rotation=(math.radians(61), 0, math.radians(42)))
    camera = bpy.context.object
    camera.name = PREFIX + "camera"
    bpy.context.scene.camera = camera
    direction = Vector((0.0, 0.0, 0.05)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 38


def main():
    clear_scene()
    setup_materials()
    steps, logs, normalized, log_range = collect_data()
    frame_end = 1 + (len(steps) - 1) * FRAMES_PER_KEY
    pivot = create_rotation_pivot()
    build_histogram(steps, logs, log_range, pivot)
    point_count, selected_counts = build_spatial_view(steps, logs, normalized, pivot)
    animate_rotation_pivot(pivot, frame_end)
    add_dynamic_status_text(steps, selected_counts, point_count)
    add_text("title", "Nyx 相空间联动筛选分析", (0.0, -3.48, 3.42), 0.145)
    add_text("spatial_label", f"侧面直方图黄柱为当前刷选区间 | 候选体素 {point_count} 个", (0.0, -3.54, 3.12), 0.070)
    add_text("hint", "正方体旋转时，侧面直方图会转到正面；空间高亮同步收缩到高密度节点", (0.0, -3.62, -2.72), 0.060)
    setup_scene(frame_end)
    print("题目 4 侧面直方图 + 正方体旋转版场景已生成。按 Ctrl+F12 渲染 MP4：", OUTPUT_VIDEO_PATH)
    if AUTO_RENDER:
        bpy.ops.render.render(animation=True)


main()
