import bpy
import os
import platform
import ctypes as ct
import time
import math
import mathutils
import copy
import random
from typing import cast, List
from . import audio_types
from . import mesh_helpers
from . mesh_helpers import sm64_scale_factor, mario_geo
from . mesh_helpers import set_scale_factor
from . import sm64_types
from .audio_types import MusicSeqId
from . import audio_stream as audio
from . surface_terrains import SURFACE_TYPES
from . surface_terrains import TERRAIN_TYPES

if platform.system() == 'Windows':
    from . input_reader import sample_input_reader

origin_offset = mathutils.Vector((0.0, 0.0, 0.0))
original_fps = 0

last_known_mario_mode = "OBJECT"
mesh_vertex_offsets = {}

MARIO_NORMAL_CAP        = 0x00000001
MARIO_VANISH_CAP        = 0x00000002
MARIO_METAL_CAP         = 0x00000004
MARIO_WING_CAP          = 0x00000008

MARIO_SPECIAL_CAPS = (MARIO_VANISH_CAP | MARIO_METAL_CAP | MARIO_WING_CAP)
MARIO_CAPS = (MARIO_NORMAL_CAP | MARIO_SPECIAL_CAPS)

ACT_FLAG_SWIMMING               = 0x00002000
ACT_FLAG_SWIMMING_OR_FLYING     = 0x10000000


# Specifically handles camera rotation to maintain a consistent framerate for camera rotation, regardless of the framerate of the scene. 
class BackgroundLoop:
    def __init__(self):
        self.fps = 60
        self.interval = 1.0 / self.fps
        self.last_time = time.perf_counter()
        self.frame_count = 0

    def __call__(self):
        current_time = time.perf_counter()
        delta = current_time - self.last_time

        if delta >= self.interval:
            self.frame_count += 1
            self.last_time = current_time

            r3d = get_camera_r3d()

            if r3d is None:
                return 0.0

            current_euler = r3d.view_rotation.to_euler('XYZ')
            
            new_pitch = max(min(current_euler.x + mario_inputs.camLookX * self.interval * look_sens, math.radians(89)), math.radians(-89))
            new_yaw = current_euler.z + mario_inputs.camLookZ * self.interval * look_sens
            
            new_euler = mathutils.Euler((new_pitch, 0.0, new_yaw), 'XYZ')
            
            r3d.view_rotation = new_euler.to_quaternion()

        return 0.0

sm64: ct.CDLL = None
sm64_mario_id = -1

mario_inputs = sm64_types.SM64MarioInputs()
mario_state = sm64_types.SM64MarioState()
follow_cam = False
tick_count = 0

music_select = MusicSeqId.SEQ_RANDOM_MUSIC

moving_objects = []
moving_objects_cache = {}
water_blocks = []
follow_camera_distance = None
base_zoom_distance = None

background_loop = None


def insert_mario(rom_path: str, scale: float, camera_follow: bool):
    global sm64, sm64_mario_id, sm64_scale_factor, original_fps, tick_count, origin_offset, follow_cam, background_loop, follow_camera_distance
    global last_known_mario_mode, mesh_vertex_offsets, base_zoom_distance

    set_scale_factor(scale)
    sm64_scale_factor = scale

    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except:
        pass
    bpy.ops.object.select_all(action='DESELECT')

    follow_cam = camera_follow
    follow_camera_distance = None
    camera_r3d = get_camera_r3d()
    base_zoom_distance = camera_r3d.view_distance if camera_r3d else None

    origin_offset = bpy.context.scene.cursor.location.copy()

    if 'LibSM64 Mario' in bpy.data.objects:
        bpy.data.objects['LibSM64 Mario'].select_set(True) # Blender 2.8x
        bpy.ops.object.delete()

    if sm64 != None:
        try:
            stop_tick_mario()
            audio.stop_audio_stream()
        except:
            pass

    this_path = os.path.dirname(os.path.realpath(__file__))
    dll_name = 'sm64.dll' if platform.system() == 'Windows' else 'libsm64.so'
    dll_path = os.path.join(this_path, 'lib', dll_name)
    sm64 = ct.cdll.LoadLibrary(dll_path)

    initialize_sm64_functions()

    if ('libsm64_mario_mesh' in bpy.data.meshes):
        old_mesh = bpy.data.meshes['libsm64_mario_mesh']
        old_mesh.user_clear()
        bpy.data.meshes.remove(old_mesh)

    with open(os.path.expanduser(rom_path), 'rb') as file:
        rom_bytes = bytearray(file.read())
        rom_chars = ct.c_char * len(rom_bytes)
        texture_buff = (ct.c_ubyte * (4 * mesh_helpers.SM64_TEXTURE_WIDTH * mesh_helpers.SM64_TEXTURE_HEIGHT))()
        sm64.sm64_global_init(rom_chars.from_buffer(rom_bytes), texture_buff)
        initialize_all_data(texture_buff)
        sm64.sm64_audio_init(rom_chars.from_buffer(rom_bytes))

    (surface_array, surface_array_len) = get_surface_array_from_scene()

    sm64.sm64_static_surfaces_load(surface_array, surface_array_len)

    sm64_mario_id = sm64.sm64_mario_create(0, 0, 0)

    if sm64_mario_id < 0:
        sm64.sm64_global_terminate()
        sm64 = None
        return "There is no ground under the 3D cursor where mario will spawn"

    mario_obj = bpy.data.objects.new('LibSM64 Mario', bpy.data.meshes['libsm64_mario_mesh'])
    bpy.context.scene.collection.objects.link(mario_obj)

    original_fps = bpy.context.scene.render.fps
    bpy.context.scene.render.fps = 30
    bpy.ops.screen.animation_play()
    bpy.app.handlers.frame_change_pre.append(tick_mario)

    audio.start_audio_stream(sm64)

    seqArgs = 0x80 | + (random.choice(list(MusicSeqId)) if music_select == MusicSeqId.SEQ_RANDOM_MUSIC else music_select)
    sm64.sm64_play_music(0, seqArgs, 0)

    sm64.sm64_play_sound(audio_types.SOUND_MENU_STAR_SOUND_LETS_A_GO, ct.c_float(0.0))

    if background_loop == None:
        background_loop = BackgroundLoop()
        bpy.app.timers.register(background_loop, first_interval=0.0)

    mesh_vertex_offsets.clear()
    last_known_mario_mode = 'OBJECT'

    bpy.app.handlers.depsgraph_update_post[:] = [
        h for h in bpy.app.handlers.depsgraph_update_post if getattr(h, '__name__', '') != 'on_mode_change'
    ]
    bpy.app.handlers.depsgraph_update_post.append(mario_mode_property_update_callback)

    tick_count = 0

    return None

def initialize_sm64_functions():
    global sm64

    sm64.sm64_global_init.argtypes = [ ct.c_char_p, ct.POINTER(ct.c_ubyte) ]
    sm64.sm64_static_surfaces_load.argtypes = [ ct.POINTER(sm64_types.SM64Surface), ct.c_uint32 ]
    sm64.sm64_mario_create.argtypes = [ ct.c_float, ct.c_float, ct.c_float ]
    sm64.sm64_mario_create.restype = ct.c_int32
    sm64.sm64_mario_tick.argtypes = [ ct.c_uint32, ct.POINTER(sm64_types.SM64MarioInputs), ct.POINTER(sm64_types.SM64MarioState), ct.POINTER(sm64_types.SM64MarioGeometryBuffers) ]

    sm64.sm64_audio_init.argtypes = [ct.c_char_p]
    sm64.sm64_audio_init.restype = None
    sm64.sm64_audio_tick.argtypes = [ ct.c_uint32, ct.c_uint32, ct.POINTER(ct.c_int16)]
    sm64.sm64_audio_tick.restype = ct.c_uint32
    sm64.sm64_play_music.argtypes = [ ct.c_uint8, ct.c_uint16, ct.c_uint16 ]
    sm64.sm64_play_sound.argtypes = [ ct.c_int32, ct.POINTER(ct.c_float) ]

    sm64.sm64_set_mario_action.argtypes = [ ct.c_int32, ct.c_uint32 ]
    sm64.sm64_set_mario_water_level.argtypes = [ ct.c_int32, ct.c_int ]

    sm64.sm64_surface_object_create.argtypes = [ ct.POINTER(sm64_types.SM64SurfaceObject) ]
    sm64.sm64_surface_object_create.restype = ct.c_uint32
    sm64.sm64_surface_object_move.argtypes = [ ct.c_uint32, ct.POINTER(sm64_types.SM64ObjectTransform) ]
    sm64.sm64_surface_object_delete.argtypes = [ ct.c_uint32 ]

    sm64.sm64_mario_interact_cap.argtypes = [ ct.c_int32, ct.c_uint32, ct.c_uint16, ct.c_uint8 ]

def add_cap(capId):
    sm64.sm64_mario_interact_cap(sm64_mario_id, capId, 0, 1)

def stop_tick_mario():
    global sm64, sm64_mario_id, original_fps
    bpy.app.handlers.frame_change_pre.clear()
    bpy.context.scene.render.fps = original_fps

    bpy.ops.screen.animation_cancel()
    sm64_mario_id = -1
    sm64.sm64_global_terminate()
    sm64 = None

def get_sm64_rotation(obj):
    blender_rotation = obj.matrix_world.to_quaternion()

    blender_to_sm64 = mathutils.Matrix((
        (1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
        (0.0, -1.0, 0.0),
    ))
    sm64_rotation = (
        blender_to_sm64
        @ blender_rotation.to_matrix()
        @ blender_to_sm64.transposed()
    )

    return sm64_rotation.to_euler('XYZ')

CAMERA_CLEARANCE = 0.3
CAMERA_MIN_DISTANCE = 1.0
CAMERA_SPHERE_RADIUS = 0.3
CAMERA_POSITION_INTERPOLATION_SPEED = 10.0
CAMERA_DISTANCE_INTERPOLATION_SPEED = 14.0
look_sens = 3.0
zoom_distance = 5.0

def get_camera_distance(scene, depsgraph, target, direction, desired_distance):
    direction = direction.normalized()
    side = direction.cross(mathutils.Vector((0.0, 0.0, 1.0)))
    if side.length < 0.001:
        side = direction.cross(mathutils.Vector((0.0, 1.0, 0.0)))
    side.normalize()
    up = side.cross(direction).normalized()

    ray_origins = [
        target,
        target + side * CAMERA_SPHERE_RADIUS,
        target - side * CAMERA_SPHERE_RADIUS,
        target + up * CAMERA_SPHERE_RADIUS,
        target - up * CAMERA_SPHERE_RADIUS,
    ]
    nearest_distance = desired_distance

    for ray_origin in ray_origins:
        remaining_distance = desired_distance
        cast_origin = ray_origin.copy()

        while remaining_distance > 0.0:
            hit, hit_location, _, _, hit_object, _ = scene.ray_cast(
                depsgraph,
                cast_origin,
                direction,
                distance=remaining_distance,
            )
            if not hit:
                break

            hit_distance = (hit_location - ray_origin).length
            if hit_object and hit_object.name != 'LibSM64 Mario' and 'water' not in hit_object.name.lower():
                nearest_distance = min(nearest_distance, hit_distance)
                break

            advance = hit_distance + 0.001
            cast_origin += direction * advance
            remaining_distance -= advance

    return max(CAMERA_MIN_DISTANCE, nearest_distance - CAMERA_CLEARANCE)

def get_camera_r3d():
    view3d = None
    for area in bpy.context.window.screen.areas:
        if area.type == 'VIEW_3D':
            view3d = area
            break

    if view3d is None or not view3d.spaces:
        return None

    r3d = view3d.spaces[0].region_3d
    return r3d

def update_follow_camera(delta_time):
    global base_zoom_distance, follow_camera_distance

    r3d = get_camera_r3d()

    if r3d is None:
        return 0.0
    
    mario_world_pos = mathutils.Vector((
        origin_offset.x + mario_state.posX / sm64_scale_factor,
        origin_offset.y - mario_state.posZ / sm64_scale_factor,
        origin_offset.z + mario_state.posY / sm64_scale_factor
    ))
    camera_target = mario_world_pos + mathutils.Vector(bpy.context.scene.libsm64.camera_shift)
    cam_forward = r3d.view_rotation @ mathutils.Vector((0.0, 0.0, -1.0))

    if base_zoom_distance is None:
        base_zoom_distance = r3d.view_distance
    elif follow_camera_distance is not None:
        user_zoom_delta = r3d.view_distance - follow_camera_distance
        if abs(user_zoom_delta) > 0.001:
            base_zoom_distance = max(CAMERA_MIN_DISTANCE, base_zoom_distance + user_zoom_delta)

    depsgraph = bpy.context.evaluated_depsgraph_get()
    camera_distance = get_camera_distance(
        bpy.context.scene,
        depsgraph,
        camera_target,
        -cam_forward,
        base_zoom_distance,
    )

    position_factor = 1.0 - math.exp(-CAMERA_POSITION_INTERPOLATION_SPEED * delta_time)
    distance_factor = 1.0 - math.exp(-CAMERA_DISTANCE_INTERPOLATION_SPEED * delta_time)

    r3d.view_location = r3d.view_location.lerp(camera_target, position_factor)
    if camera_distance < r3d.view_distance: # If the camera is too far away, snap to the new distance to avoid clipping through walls
        r3d.view_distance = camera_distance
    else:
        r3d.view_distance += (camera_distance - r3d.view_distance) * distance_factor
    follow_camera_distance = r3d.view_distance

def tick_mario(scene, depsgraph=None):
    global tick_count

    if depsgraph is None:
        depsgraph = bpy.context.evaluated_depsgraph_get()

    for moving_object in moving_objects:
        obj = bpy.data.objects[moving_object['name']]
        location, rotation_quat, scale = obj.matrix_world.decompose()
        transform_matrix = (
            mathutils.Matrix.Translation(location)
            @ rotation_quat.to_matrix().to_4x4()
        )

        euler_current = get_sm64_rotation(obj)
        location_relative = location - origin_offset
        rotation_delta = rotation_quat @ moving_object['rotation'].inverted()
        rotated_origin = rotation_delta @ moving_object['origin']
        translation_delta = location_relative - rotated_origin

        transform = sm64_types.SM64ObjectTransform(
            posX = sm64_scale_factor * translation_delta.x,
            posY = sm64_scale_factor * translation_delta.z,
            posZ = -sm64_scale_factor * translation_delta.y,
            eulX = -math.degrees(euler_current.x),
            eulY = -math.degrees(euler_current.y),
            eulZ = -math.degrees(euler_current.z)
        )

        object_id = moving_object['id']
        cached_matrix = moving_objects_cache.get(object_id)
        transform_changed = cached_matrix is None or transform_matrix != cached_matrix
        if transform_changed:
            sm64.sm64_surface_object_move(object_id, transform)
            moving_objects_cache[object_id] = transform_matrix.copy()
    
    if not ('LibSM64 Mario' in bpy.data.objects):
        stop_tick_mario()
        audio.stop_audio_stream()
        return 0

    r3d = get_camera_r3d()

    if r3d is None:
        return 0.0

    cam_forward = r3d.view_rotation @ mathutils.Vector((0.0, 0.0, -1.0))
    cam_world_pos = r3d.view_location - (cam_forward * r3d.view_distance)
    update_follow_camera(1.0 / scene.render.fps)

    mario_world_pos = mathutils.Vector((
        origin_offset.x + mario_state.posX / sm64_scale_factor,
        origin_offset.y - mario_state.posZ / sm64_scale_factor,
        origin_offset.z + mario_state.posY / sm64_scale_factor
    ))

    # Check if mario is inside any water blocks and set the water level if so.
    # sm64_set_mario_water_level specifically requires the top of the water block,
    # which will teleport mario to the top if he enters from the side.
    is_in_water = False
    for obj_name in water_blocks:
        water_block = bpy.data.objects[obj_name]
        if mesh_helpers.is_inside_volume(mario_world_pos, water_block):
            water_obj = water_block
            z_loc = water_obj.location.z
            z_dim = water_obj.dimensions.z
            z_scale = water_obj.scale.z

            water_level = (z_loc - origin_offset.z + (z_dim/2.0 * z_scale)) * sm64_scale_factor
            sm64.sm64_set_mario_water_level(sm64_mario_id, ct.c_int(int(water_level)))
            is_in_water = True

    # If mario is not in water, set the water level to a very low value to ensure he is always above.
    if not is_in_water:
        sm64.sm64_set_mario_water_level(sm64_mario_id, ct.c_int(-10000))

    delta_vec = cam_world_pos - mario_world_pos
    
    if delta_vec.length > 0.001:
        delta_vec.normalize()

    sample_input_reader(mario_inputs)

    final_mario_inputs = copy.copy(mario_inputs)
    final_mario_inputs.camLookX = delta_vec.x
    final_mario_inputs.camLookZ = -delta_vec.y

    if (mario_state.action & ACT_FLAG_SWIMMING_OR_FLYING):
        final_mario_inputs.stickX *= -1
        final_mario_inputs.stickY *= -1

    sm64.sm64_mario_tick(sm64_mario_id, ct.byref(final_mario_inputs), ct.byref(mario_state), ct.byref(mario_geo))

    target_mesh = bpy.data.meshes.get('libsm64_mario_mesh')
    if target_mesh:
        if tick_count < 15: 
            mesh_helpers.update_mesh_data(target_mesh, origin_offset, mesh_vertex_offsets)
        else:
            ##TODO: Add functionality to determine when a full update is required
            ##      (e.g. switching to flying requires texture updates)
            mesh_helpers.update_mesh_data(target_mesh, origin_offset, mesh_vertex_offsets)
            #mesh_helpers.update_mesh_data_fast(target_mesh, origin_offset, mesh_vertex_offsets)

    tick_count += 1
    return None

def initialize_all_data(texture_buffer):
    size = mesh_helpers.SM64_TEXTURE_WIDTH, mesh_helpers.SM64_TEXTURE_HEIGHT

    if 'libsm64_mario_texture' in bpy.data.images:
        image = bpy.data.images["libsm64_mario_texture"]
    else:
        image = bpy.data.images.new("libsm64_mario_texture", width=size[0], height=size[1])

    pixels = [None] * size[0] * size[1]
    i = 0
    for y in range(size[1]):
        for x in range(size[0]):
            r = float(texture_buffer[i]) / 255
            g = float(texture_buffer[i+1]) / 255
            b = float(texture_buffer[i+2]) / 255
            a = float(texture_buffer[i+3]) / 255
            i += 4
            pixels[(y * size[0]) + x] = [r, g, b, a]

    pixels = [chan for px in pixels for chan in px]
    image.alpha_mode = 'STRAIGHT'
    image.file_format = 'PNG'
    image.pixels = pixels

    if 'libsm64_mario_material' in bpy.data.materials:
        mat = bpy.data.materials["libsm64_mario_material"]
    else:
        mat = bpy.data.materials.new(name="libsm64_mario_material")

    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    tex_node = nodes.new(type='ShaderNodeTexImage')
    tex_node.image = bpy.data.images.get("libsm64_mario_texture")

    color_node = nodes.new(type='ShaderNodeVertexColor')
    color_node.layer_name = 'Col'

    mix_node = nodes.new(type='ShaderNodeMix')
    mix_node.data_type = 'RGBA'
    mix_node.blend_type = 'MIX'

    transparent_node = nodes.new(type='ShaderNodeBsdfTransparent')

    shader_mix_node = nodes.new(type='ShaderNodeMixShader')

    math_node = nodes.new(type='ShaderNodeMath')
    math_node.operation = 'MAXIMUM'

    diffuse_node = nodes.new(type='ShaderNodeBsdfDiffuse')

    out_node = nodes.new(type='ShaderNodeOutputMaterial')

    links.new(tex_node.outputs['Color'], mix_node.inputs['B'])
    links.new(tex_node.outputs['Alpha'], mix_node.inputs['Factor'])
    links.new(tex_node.outputs['Alpha'], math_node.inputs[1])
    links.new(color_node.outputs['Color'], mix_node.inputs['A'])
    links.new(color_node.outputs['Alpha'], math_node.inputs[0])
    links.new(mix_node.outputs['Result'], diffuse_node.inputs['Color'])
    links.new(diffuse_node.outputs['BSDF'], shader_mix_node.inputs[2])
    links.new(math_node.outputs['Value'], shader_mix_node.inputs[0])
    links.new(transparent_node.outputs['BSDF'], shader_mix_node.inputs[1])
    links.new(shader_mix_node.outputs['Shader'], out_node.inputs['Surface'])

    mesh = bpy.data.meshes.new('libsm64_mario_mesh')

    total_verts = mesh_helpers.SM64_GEO_MAX_TRIANGLES * 3
    total_faces = mesh_helpers.SM64_GEO_MAX_TRIANGLES
    total_loops = total_faces * 3
    
    mesh.vertices.add(total_verts)
    mesh.loops.add(total_loops)
    mesh.polygons.add(total_faces)
    
    loop_starts = [t * 3 for t in range(total_faces)]
    loop_totals = [3] * total_faces
    vertex_indices = []
    for t in range(total_faces):
        base = t * 3
        vertex_indices.extend([base, base + 1, base + 2])
        
    mesh.loops.foreach_set("vertex_index", vertex_indices)
    mesh.polygons.foreach_set("loop_start", loop_starts)
    mesh.polygons.foreach_set("loop_total", loop_totals)
    
    mesh.attributes.new(name="Col", type='BYTE_COLOR', domain='CORNER')
    mesh.uv_layers.new(name="uv0")
    mesh.materials.append(mat)
    
    mesh.validate(verbose=False)
    mesh.update()


def get_surface_array_from_scene():
    global water_blocks, moving_objects, moving_objects_cache

    scene = bpy.context.window.scene
    surfaces = []
    moving_objects = []
    moving_objects_cache = {}
    water_blocks = []

    for obj in cast(List[bpy.types.Object], scene.collection.all_objects):
        # water blocks don't get added to the static surfaces
        if "water" in obj.name.lower():
            water_blocks.append(obj.name)
            continue

        if obj.sm64_surface_type_dropdown == "SURFACE_NOT_SLIPPERY":
            location, rotation_quat, scale = obj.matrix_world.decompose()
            obj_surfaces = []
            mesh_helpers.add_mesh(obj, obj_surfaces)
            (surf_obj_array, surf_count) = mesh_helpers.build_surface_array(obj_surfaces, origin_offset)

            euler = get_sm64_rotation(obj)

            obj_origin = mathutils.Vector((
                location.x - origin_offset.x,
                location.y - origin_offset.y,
                location.z - origin_offset.z,
            ))

            surface_object = sm64_types.SM64SurfaceObject(
                transform = sm64_types.SM64ObjectTransform(
                    posX = obj_origin.x,
                    posY = obj_origin.z,
                    posZ = obj_origin.y,
                    eulX = -math.degrees(euler.x),
                    eulY = -math.degrees(euler.y),
                    eulZ = -math.degrees(euler.z)
                ),
                surfaceCount = surf_count,
                surfaces = surf_obj_array
            )

            objId = sm64.sm64_surface_object_create(surface_object)
            moving_objects.append({
                'id': objId,
                'name': obj.name,
                'origin': obj_origin.copy(),
                'rotation': rotation_quat.copy(),
            })
            continue


        if isinstance(obj.data, bpy.types.Mesh):
            mesh_helpers.add_mesh(obj, surfaces)

    (surface_array, j) = mesh_helpers.build_surface_array(surfaces, origin_offset)

    return (surface_array, j)

def on_mode_change(scene=None):
    global mesh_vertex_offsets, last_known_mario_mode
    
    mario_obj = bpy.data.objects.get('LibSM64 Mario')
    if not mario_obj:
        return None

    current_mode = mario_obj.mode

    if current_mode == last_known_mario_mode:
        return

    if current_mode != last_known_mario_mode:
        screen_ctx = None
        for win in bpy.context.window_manager.windows:
            if win.screen:
                screen_ctx = win.screen
                break

        if last_known_mario_mode == 'OBJECT' and current_mode == 'EDIT':
            if screen_ctx and screen_ctx.is_animation_playing:
                bpy.ops.screen.animation_cancel(restore_frame=False)
                print("Pausing Animation")

            tool_settings = bpy.context.scene.tool_settings
            tool_settings.use_proportional_edit = True
            tool_settings.proportional_edit_falloff = 'SMOOTH'
            tool_settings.proportional_size = 0.01

        elif last_known_mario_mode == 'EDIT' and current_mode == 'OBJECT':
            if mario_geo:
                mesh = mario_obj.data
                num_tris = mario_geo.numTrianglesUsed
                current_coords = [0.0] * (len(mesh.vertices) * 3)
                mesh.vertices.foreach_get("co", current_coords)
                
                for i in range(num_tris):
                    base_sm64 = 9 * i
                    base_blender = 9 * i
                    
                    sim_v = []
                    for v in range(3):
                        s_idx = base_sm64 + (v * 3)
                        sim_v.append(mathutils.Vector((
                            origin_offset.x + mario_geo.position_data[s_idx + 0] / sm64_scale_factor,
                            origin_offset.y - mario_geo.position_data[s_idx + 2] / sm64_scale_factor,
                            origin_offset.z + mario_geo.position_data[s_idx + 1] / sm64_scale_factor
                        )))
                    
                    edge1 = sim_v[1] - sim_v[0]
                    edge2 = sim_v[2] - sim_v[0]
                    
                    valid_basis = False
                    if edge1.length > 0.0001 and edge2.length > 0.0001:
                        v_tangent = edge1.normalized()
                        cross_prod = edge1.cross(edge2)
                        if cross_prod.length > 0.0001:
                            v_normal = cross_prod.normalized()
                            v_bitangent = v_normal.cross(v_tangent).normalized()

                            tri_basis_inv = mathutils.Matrix((v_tangent, v_bitangent, v_normal))
                            valid_basis = True
                    
                    for v in range(3):
                        v_idx = base_blender + (v * 3)
                        vert_number = (i * 3) + v
                        
                        edited_pos = mathutils.Vector((
                            current_coords[v_idx + 0], 
                            current_coords[v_idx + 1], 
                            current_coords[v_idx + 2]
                        ))
                        world_delta = edited_pos - sim_v[v]
                        
                        if valid_basis:
                            local_delta = tri_basis_inv @ world_delta
                            mesh_vertex_offsets[vert_number] = (local_delta.x, local_delta.y, local_delta.z, 1)
                        else:
                            mesh_vertex_offsets[vert_number] = (world_delta.x, world_delta.y, world_delta.z, 0)

            if screen_ctx and not screen_ctx.is_animation_playing:
                bpy.ops.screen.animation_play()
                print("ResumingAnimation")

            tool_settings = bpy.context.scene.tool_settings
            tool_settings.use_proportional_edit = False

        last_known_mario_mode = current_mode

def mario_mode_property_update_callback(self, context):
    bpy.app.timers.register(on_mode_change, first_interval=0.0)