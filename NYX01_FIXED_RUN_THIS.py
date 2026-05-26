import os
import math
import numpy as np
import bpy
from mathutils import Vector


# =========================
# 题目 1：Nyx 体数据渲染与密度演化视频
# 在 Blender 中运行：Scripting -> Open -> 选择本文件 -> Run Script
# 输出：visualize__/Nyx_01_volume_animation.mp4
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

OUTPUT_VIDEO_PATH = os.path.join(WEB_DIR, "Nyx_01_volume_animation.mp4")
AUTO_RENDER = False

GRID_SIZE = 128
MODEL_SCALE = 5.2
DOWNSAMPLE = 3
STEP_STRIDE = 4
FRAMES_PER_STEP = 7
FPS = 18
GLOW_PERCENTILE = 95.8
CORE_PERCENTILE = 99.55
MAX_POINTS = 4300
PARTICLE_RADIUS_BASE = 0.012
PARTICLE_RADIUS_SCALE = 0.78
ENABLE_ROTATION = False
ROTATION_DEGREES = 18
ENHANCE_TEMPORAL_CHANGE = True
TEMPORAL_GAMMA = 0.55


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def read_nyx_density(step):
    path = os.path.normpath(os.path.join(DATA_DIR, f"{int(step):04d}.dat"))
    if not os.path.isfile(path):
        raise FileNotFoundError("找不到数据文件：" + path)

    expected = GRID_SIZE ** 3
    dtype = np.dtype("<f4")
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


def log_density(volume):
    clean = np.nan_to_num(volume.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    min_value = float(clean.min())
    if min_value <= 0:
        clean = clean - min_value + 1e-6
    return np.log10(clean + 1e-6)


def estimate_global_range():
    samples = []
    for step in [0, 25, 50, 75, 99]:
        volume = read_nyx_density(step)
        samples.append(log_density(volume[::4, ::4, ::4]).ravel())
        print(f"估计全局密度范围：读取 {step:04d}")
    combined = np.concatenate(samples)
    return tuple(np.percentile(combined, [1.0, 99.85]))


def normalized_sample(step, log_range):
    logged = log_density(read_nyx_density(step))
    lo, hi = log_range
    normalized = np.clip((logged - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    return normalized[::DOWNSAMPLE, ::DOWNSAMPLE, ::DOWNSAMPLE]


def animation_steps():
    steps = list(range(0, 100, STEP_STRIDE))
    if steps[-1] != 99:
        steps.append(99)
    return steps


def make_material(name, color, alpha=1.0, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = "BLEND"
    mat.diffuse_color = color
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Alpha"].default_value = alpha
        bsdf.inputs["Roughness"].default_value = 0.45
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


def add_text(name, body, location, size=0.12):
    bpy.ops.object.text_add(location=location, rotation=(math.radians(70), 0, 0))
    text = bpy.context.object
    text.name = name
    text.data.body = body
    text.data.align_x = "CENTER"
    text.data.size = size
    text.data.materials.append(make_material("NYX01_文字白", (0.92, 0.97, 1.0, 1.0), 1.0, 0.38))
    return text


def octa_geometry(points, values, threshold, core_threshold, shape):
    cell_size = MODEL_SCALE / shape[0]
    half = shape[0] * cell_size / 2.0
    octa = [(0, 0, 1), (1, 0, 0), (0, 1, 0), (-1, 0, 0), (0, -1, 0), (0, 0, -1)]
    octa_faces = [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1), (5, 2, 1), (5, 3, 2), (5, 4, 3), (5, 1, 4)]
    vertices = []
    faces = []
    material_ids = []

    for (z, y, x), value in zip(points, values):
        glow = float(np.clip((value - threshold) / max(1.0 - threshold, 1e-6), 0.0, 1.0))
        radius = cell_size * (PARTICLE_RADIUS_BASE + glow * PARTICLE_RADIUS_SCALE)
        cx = (x + 0.5) * cell_size - half
        cy = (y + 0.5) * cell_size - half
        cz = (z + 0.5) * cell_size - half
        start = len(vertices)
        for dx, dy, dz in octa:
            vertices.append((cx + dx * radius, cy + dy * radius, cz + dz * radius))
        if value >= core_threshold or glow > 0.88:
            mat_id = 4
        elif glow > 0.66:
            mat_id = 3
        elif glow > 0.42:
            mat_id = 2
        elif glow > 0.18:
            mat_id = 1
        else:
            mat_id = 0
        for face in octa_faces:
            faces.append(tuple(start + i for i in face))
            material_ids.append(mat_id)
    return vertices, faces, material_ids


def build_density_animation():
    steps = animation_steps()
    log_range = estimate_global_range()
    fields = {}
    max_field = None

    for step in steps:
        field = normalized_sample(step, log_range)
        fields[step] = field
        max_field = field.copy() if max_field is None else np.maximum(max_field, field)
        print(f"题目 1 读取时间步 {step:04d}")

    threshold = float(np.percentile(max_field, GLOW_PERCENTILE))
    core_threshold = float(np.percentile(max_field, CORE_PERCENTILE))
    points = np.argwhere(max_field >= threshold)
    max_values = max_field[max_field >= threshold]
    if len(points) > MAX_POINTS:
        order = np.argsort(max_values)[-MAX_POINTS:]
        points = points[order]
        max_values = max_values[order]

    point_series = np.stack([fields[step][tuple(points.T)] for step in steps], axis=0)
    point_min = point_series.min(axis=0)
    point_max = point_series.max(axis=0)
    point_span = np.maximum(point_max - point_min, 1e-6)

    vertices, faces, material_ids = octa_geometry(points, max_values, threshold, core_threshold, max_field.shape)
    mesh = bpy.data.meshes.new("NYX01_density_glow_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("NYX01_密度体渲染发光点云", mesh)
    bpy.context.collection.objects.link(obj)

    obj.data.materials.append(make_emission_material("NYX01_低密度冷色云雾", (0.08, 0.16, 0.85, 0.42), 0.85))
    obj.data.materials.append(make_emission_material("NYX01_电蓝丝状结构", (0.05, 0.48, 1.0, 0.62), 1.55))
    obj.data.materials.append(make_emission_material("NYX01_玫紫高密度纤维", (0.90, 0.12, 1.0, 0.80), 2.6))
    obj.data.materials.append(make_emission_material("NYX01_金色节点外晕", (1.0, 0.55, 0.16, 0.92), 4.2))
    obj.data.materials.append(make_emission_material("NYX01_白金极高密度核心", (1.0, 0.94, 0.88, 1.0), 7.2))
    for polygon, mat_id in zip(obj.data.polygons, material_ids):
        polygon.material_index = mat_id

    obj.shape_key_add(name="Basis")
    for index, step in enumerate(steps):
        values = fields[step][tuple(points.T)]
        if ENHANCE_TEMPORAL_CHANGE:
            temporal = np.clip((values - point_min) / point_span, 0.0, 1.0)
            contrast_values = threshold + np.power(temporal, TEMPORAL_GAMMA) * (1.0 - threshold)
            values = np.maximum(values, contrast_values)
        step_vertices, _, _ = octa_geometry(points, values, threshold, core_threshold, max_field.shape)
        key = obj.shape_key_add(name=f"step_{step:04d}")
        for vertex, co in zip(key.data, step_vertices):
            vertex.co = co
        frame = 1 + index * FRAMES_PER_STEP
        key.value = 0.0
        key.keyframe_insert("value", frame=max(1, frame - FRAMES_PER_STEP))
        key.value = 1.0
        key.keyframe_insert("value", frame=frame)
        key.value = 0.0
        key.keyframe_insert("value", frame=frame + FRAMES_PER_STEP)

    if obj.data.shape_keys and obj.data.shape_keys.animation_data:
        action = obj.data.shape_keys.animation_data.action
        if action:
            for fcurve in action.fcurves:
                for point in fcurve.keyframe_points:
                    point.interpolation = "LINEAR"

    if ENABLE_ROTATION and ROTATION_DEGREES:
        obj.rotation_euler[2] = 0.0
        obj.keyframe_insert("rotation_euler", frame=1)
        obj.rotation_euler[2] = math.radians(ROTATION_DEGREES)
        obj.keyframe_insert("rotation_euler", frame=1 + (len(steps) - 1) * FRAMES_PER_STEP)
    return obj, len(points), steps


def add_reference_box():
    mat = make_material("NYX01_低密度空间透明参考框", (0.05, 0.28, 0.55, 0.08), 0.08, 0.08)
    bpy.ops.mesh.primitive_cube_add(size=MODEL_SCALE, location=(0, 0, 0))
    box = bpy.context.object
    box.name = "NYX01_空间参考框"
    box.data.materials.append(mat)
    wire = box.modifiers.new("参考网格", "WIREFRAME")
    wire.thickness = 0.012


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
            eevee.bloom_intensity = 0.20

    bpy.context.scene.world = bpy.data.worlds.new("NYX01_深空背景") if bpy.context.scene.world is None else bpy.context.scene.world
    bpy.context.scene.world.color = (0.0, 0.0, 0.003)
    bpy.context.scene.view_settings.view_transform = "Standard"
    bpy.context.scene.view_settings.look = "Medium High Contrast"
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frame_end
    bpy.context.scene.render.fps = FPS
    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080
    bpy.context.scene.render.filepath = OUTPUT_VIDEO_PATH
    bpy.context.scene.render.image_settings.file_format = "FFMPEG"
    bpy.context.scene.render.ffmpeg.format = "MPEG4"
    bpy.context.scene.render.ffmpeg.codec = "H264"
    bpy.context.scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    bpy.context.scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    bpy.context.scene.render.ffmpeg.audio_codec = "NONE"

    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree
    tree.nodes.clear()
    render_layers = tree.nodes.new(type="CompositorNodeRLayers")
    glare = tree.nodes.new(type="CompositorNodeGlare")
    glare.glare_type = "FOG_GLOW"
    glare.quality = "HIGH"
    glare.threshold = 0.18
    glare.size = 8
    composite = tree.nodes.new(type="CompositorNodeComposite")
    tree.links.new(render_layers.outputs["Image"], glare.inputs["Image"])
    tree.links.new(glare.outputs["Image"], composite.inputs["Image"])

    bpy.ops.object.light_add(type="AREA", location=(0, -5.2, 5.2))
    light = bpy.context.object
    light.name = "NYX01_主光"
    light.data.energy = 300
    light.data.size = 6.0

    bpy.ops.object.light_add(type="POINT", location=(-3.8, 2.8, 2.4))
    rim = bpy.context.object
    rim.name = "NYX01_轮廓光"
    rim.data.energy = 130
    rim.data.color = (0.72, 0.30, 1.0)

    bpy.ops.object.camera_add(location=(6.8, -7.2, 5.2), rotation=(math.radians(60), 0, math.radians(42)))
    camera = bpy.context.object
    bpy.context.scene.camera = camera
    direction = Vector((0, 0, 0)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 42


def main():
    clear_scene()
    obj, point_count, steps = build_density_animation()
    add_reference_box()
    add_text("NYX01_title", "Nyx 宇宙密度场体渲染", (0, -3.25, 2.95), 0.20)
    add_text("NYX01_subtitle", f"对数传递函数 | 时间步 {steps[0]:04d}-{steps[-1]:04d} | 发光采样点 {point_count} | 固定视角", (0, -3.25, 2.66), 0.088)
    add_text("NYX01_hint", "已增强同一空间点的时间变化：半径变大表示该位置密度相对自身历史增强", (0, -3.25, 2.46), 0.070)
    frame_end = 1 + (len(steps) - 1) * FRAMES_PER_STEP
    setup_scene(frame_end)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    print("题目 1 场景已生成。按 Ctrl+F12 渲染 MP4：", OUTPUT_VIDEO_PATH)
    if AUTO_RENDER:
        bpy.ops.render.render(animation=True)


main()
