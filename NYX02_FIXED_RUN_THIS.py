import os
import math
import numpy as np
import bpy
from mathutils import Vector

# =========================
# 题目 2：宇宙密度空间结构演化视频
# 在 Blender 中运行：Scripting -> Open/Paste -> Run Script
# 输出：Nyx_02_structure_evolution.mp4
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
OUTPUT_VIDEO_PATH = os.path.join(WEB_DIR, "Nyx_02_structure_evolution.mp4")
AUTO_RENDER = True

GRID_SIZE = 128
BAKED_STEP_STRIDE = 5
FRAMES_PER_STEP = 5
DOWNSAMPLE = 3
MODEL_SCALE = 5.0
GLOW_PERCENTILE = 96.0
MAX_POINTS = 4600


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


def log_density(volume):
    clean = np.nan_to_num(volume.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    min_value = float(clean.min())
    if min_value <= 0:
        clean = clean - min_value + 1e-6
    return np.log10(clean + 1e-6)


def estimate_global_range():
    values = []
    for step in [0, 25, 50, 75, 99]:
        values.append(log_density(read_nyx_density(step)[::4, ::4, ::4]).ravel())
    combined = np.concatenate(values)
    return tuple(np.percentile(combined, [1.0, 99.85]))


def normalized_sample(step, log_range):
    logged = log_density(read_nyx_density(step))
    lo, hi = log_range
    normalized = np.clip((logged - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    return normalized[::DOWNSAMPLE, ::DOWNSAMPLE, ::DOWNSAMPLE]


def animation_steps():
    steps = list(range(0, 100, BAKED_STEP_STRIDE))
    if steps[-1] != 99:
        steps.append(99)
    return steps


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


def make_material(name, color, alpha=1.0, emission_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = "BLEND"
    mat.diffuse_color = color
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Alpha"].default_value = alpha
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = color
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def octa_geometry(points, values, threshold, shape):
    cell_size = MODEL_SCALE / shape[0]
    half = shape[0] * cell_size / 2.0
    octa = [(0, 0, 1), (1, 0, 0), (0, 1, 0), (-1, 0, 0), (0, -1, 0), (0, 0, -1)]
    octa_faces = [(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1), (5, 2, 1), (5, 3, 2), (5, 4, 3), (5, 1, 4)]
    vertices = []
    faces = []
    material_ids = []
    for (z, y, x), value in zip(points, values):
        glow = float(np.clip((value - threshold) / max(1.0 - threshold, 1e-6), 0.0, 1.0))
        radius = cell_size * (0.04 + glow * 1.45)
        cx = (x + 0.5) * cell_size - half
        cy = (y + 0.5) * cell_size - half
        cz = (z + 0.5) * cell_size - half
        start = len(vertices)
        for dx, dy, dz in octa:
            vertices.append((cx + dx * radius, cy + dy * radius, cz + dz * radius))
        mat_id = 2 if glow > 0.78 else (1 if glow > 0.38 else 0)
        for face in octa_faces:
            faces.append(tuple(start + i for i in face))
            material_ids.append(mat_id)
    return vertices, faces, material_ids


def build_baked_structure_animation():
    steps = animation_steps()
    log_range = estimate_global_range()
    fields = {}
    max_field = None
    for step in steps:
        field = normalized_sample(step, log_range)
        fields[step] = field
        max_field = field.copy() if max_field is None else np.maximum(max_field, field)
        print(f"读取演化时间步 {step:04d}")

    threshold = np.percentile(max_field, GLOW_PERCENTILE)
    points = np.argwhere(max_field >= threshold)
    max_values = max_field[max_field >= threshold]
    if len(points) > MAX_POINTS:
        order = np.argsort(max_values)[-MAX_POINTS:]
        points = points[order]
        max_values = max_values[order]

    vertices, faces, material_ids = octa_geometry(points, max_values, threshold, max_field.shape)
    mesh = bpy.data.meshes.new("NYX_02_宇宙网演化_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("NYX_02_宇宙网演化点云", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(make_emission_material("蓝色低密度纤维", (0.06, 0.35, 1.0, 0.55), 1.1))
    obj.data.materials.append(make_emission_material("玫紫高密度桥接", (0.85, 0.14, 1.0, 0.82), 2.7))
    obj.data.materials.append(make_emission_material("金白星系团节点", (1.0, 0.78, 0.24, 1.0), 6.2))
    for polygon, mat_id in zip(obj.data.polygons, material_ids):
        polygon.material_index = mat_id

    obj.shape_key_add(name="Basis")
    for index, step in enumerate(steps):
        values = fields[step][tuple(points.T)]
        step_vertices, _, _ = octa_geometry(points, values, threshold, max_field.shape)
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

    obj.rotation_euler[2] = 0.0
    obj.keyframe_insert("rotation_euler", frame=1)
    obj.rotation_euler[2] = math.radians(360)
    obj.keyframe_insert("rotation_euler", frame=1 + (len(steps) - 1) * FRAMES_PER_STEP)
    return obj, len(points), steps


def add_reference_box():
    mat = make_material("透明低密度空间参考框", (0.05, 0.28, 0.55, 0.08), alpha=0.08)
    bpy.ops.mesh.primitive_cube_add(size=MODEL_SCALE, location=(0, 0, 0))
    box = bpy.context.object
    box.name = "NYX_02_透明参考框"
    box.data.materials.append(mat)
    wire = box.modifiers.new("参考网格", "WIREFRAME")
    wire.thickness = 0.012


def add_text(body, location, size=0.12):
    bpy.ops.object.text_add(location=location, rotation=(math.radians(70), 0, 0))
    text = bpy.context.object
    text.name = "NYX_02_说明文字"
    text.data.body = body
    text.data.align_x = "CENTER"
    text.data.size = size
    text.data.materials.append(make_material("NYX_02_文字白", (0.92, 0.97, 1.0, 1.0), emission_strength=0.35))


def setup_scene(frame_end):
    try:
        bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        bpy.context.scene.render.engine = "BLENDER_EEVEE"
    # 设置更亮的背景色
    if bpy.context.scene.world is None:
        bpy.context.scene.world = bpy.data.worlds.new("明亮背景")
    bpy.context.scene.world.color = (0.12, 0.14, 0.22)

    # 添加柔和环境光
    if not any(l.type == 'AREA' for l in bpy.data.lights):
        light_data = bpy.data.lights.new(name="Soft_Area", type='AREA')
        light_data.energy = 1200
        light_data.color = (0.9, 0.95, 1.0)
        light_obj = bpy.data.objects.new(name="Soft_Area", object_data=light_data)
        light_obj.location = (6, -6, 8)
        bpy.context.collection.objects.link(light_obj)

    # 科学时序动画使用线性插值，避免 Shape Key 数值过冲
    for obj in bpy.data.objects:
        if obj.data and hasattr(obj.data, 'shape_keys') and obj.data.shape_keys and obj.data.shape_keys.animation_data:
            action = obj.data.shape_keys.animation_data.action
            if action:
                for fcurve in action.fcurves:
                    for point in fcurve.keyframe_points:
                        point.interpolation = "LINEAR"
    eevee = getattr(bpy.context.scene, "eevee", None)
    if eevee and hasattr(eevee, "use_bloom"):
        eevee.use_bloom = True
        eevee.bloom_intensity = 0.20
    bpy.context.scene.world = bpy.data.worlds.new("Nyx 02 深空背景") if bpy.context.scene.world is None else bpy.context.scene.world
    bpy.context.scene.world.color = (0.0, 0.0, 0.004)
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

    bpy.ops.object.light_add(type="AREA", location=(0, -5.2, 5.0))
    light = bpy.context.object
    light.name = "NYX_02_主光"
    light.data.energy = 280
    light.data.size = 6.0

    bpy.ops.object.camera_add(location=(6.4, -7.0, 4.8), rotation=(math.radians(60), 0, math.radians(42)))
    camera = bpy.context.object
    bpy.context.scene.camera = camera
    direction = Vector((0, 0, 0)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 42


def main():
    clear_scene()
    obj, point_count, steps = build_baked_structure_animation()
    add_reference_box()
    add_text("Nyx 宇宙密度结构演化视频", (0, -3.2, 2.95), 0.20)
    add_text(f"固定拓扑 Shape Key 动画 | 时间步 {steps[0]:04d}-{steps[-1]:04d} | 采样节点 {point_count}", (0, -3.2, 2.65), 0.105)
    frame_end = 1 + (len(steps) - 1) * FRAMES_PER_STEP
    setup_scene(frame_end)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    print("题目 2 完成：已设置为 MP4 动画输出，按 Ctrl+F12 渲染到", OUTPUT_VIDEO_PATH)
    if AUTO_RENDER:
        bpy.ops.render.render(animation=True)


main()
