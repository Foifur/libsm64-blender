import bpy
import mathutils
from typing import cast, List
from . surface_terrains import SURFACE_TYPES
from . surface_terrains import TERRAIN_TYPES
from . sm64_types import SM64Surface, SM64MarioGeometryBuffers

SM64_GEO_MAX_TRIANGLES = 1024
SM64_TEXTURE_WIDTH = 64 * 11
SM64_TEXTURE_HEIGHT = 64

sm64_scale_factor = 50
mario_geo = SM64MarioGeometryBuffers()

def set_scale_factor(scale_factor):
    global sm64_scale_factor
    sm64_scale_factor = scale_factor

def clamp_bounds(val):
    val = int(val)
    bounds = 0x7FFF
    if val < -bounds:
        return (-bounds, False)
    if val > bounds:
        return (bounds, False)
    return (val, True)

def add_mesh(obj: bpy.types.Object, out):
    mesh = obj.data
    mesh.calc_loop_triangles()
    for tri in cast(List[bpy.types.MeshLoopTriangle], mesh.loop_triangles):
        out_elem = {}
        for i in range(3):
            tri_idx = tri.vertices[i]
            vx = mesh.vertices[tri_idx].co.x
            vy = mesh.vertices[tri_idx].co.y
            vz = mesh.vertices[tri_idx].co.z
            vworld = obj.matrix_world @ mathutils.Vector((vx, vy, vz, 1))
            out_elem['v' + str(i) + 'x'] = vworld.x
            out_elem['v' + str(i) + 'y'] = vworld.y
            out_elem['v' + str(i) + 'z'] = vworld.z

        out_elem['terrain'] = TERRAIN_TYPES[obj.sm64_terrain_type_dropdown]
        out_elem['surftype'] = SURFACE_TYPES[obj.sm64_surface_type_dropdown]
        out.append(out_elem)

def build_surface_array(surfaces, origin_offset):
    surface_array = (SM64Surface * len(surfaces))()
    j = 0

    for i in range(len(surfaces)):
        (v0x, in00) = clamp_bounds(sm64_scale_factor * ( surfaces[i]['v0x'] - origin_offset.x))
        (v0y, in01) = clamp_bounds(sm64_scale_factor * ( surfaces[i]['v0z'] - origin_offset.z))
        (v0z, in02) = clamp_bounds(sm64_scale_factor * (-surfaces[i]['v0y'] + origin_offset.y))
        (v1x, in10) = clamp_bounds(sm64_scale_factor * ( surfaces[i]['v1x'] - origin_offset.x))
        (v1y, in11) = clamp_bounds(sm64_scale_factor * ( surfaces[i]['v1z'] - origin_offset.z))
        (v1z, in12) = clamp_bounds(sm64_scale_factor * (-surfaces[i]['v1y'] + origin_offset.y))
        (v2x, in20) = clamp_bounds(sm64_scale_factor * ( surfaces[i]['v2x'] - origin_offset.x))
        (v2y, in21) = clamp_bounds(sm64_scale_factor * ( surfaces[i]['v2z'] - origin_offset.z))
        (v2z, in22) = clamp_bounds(sm64_scale_factor * (-surfaces[i]['v2y'] + origin_offset.y))

        if not in00 and not in01 and not in02:
            continue
        if not in10 and not in11 and not in12:
            continue
        if not in20 and not in21 and not in22:
            continue

        surface_array[j].surftype = surfaces[i]['surftype']
        surface_array[j].force = 0
        surface_array[j].terrain = surfaces[i]['terrain']
        surface_array[j].v0x = v0x
        surface_array[j].v0y = v0y
        surface_array[j].v0z = v0z
        surface_array[j].v1x = v1x
        surface_array[j].v1y = v1y
        surface_array[j].v1z = v1z
        surface_array[j].v2x = v2x
        surface_array[j].v2y = v2y
        surface_array[j].v2z = v2z
        j += 1

    return (surface_array, j)

def update_mesh_data(mesh: bpy.types.Mesh, origin_offset, mesh_vertex_offsets: dict = {}):
    num_tris = mario_geo.numTrianglesUsed
    num_verts = num_tris * 3
    
    coords = get_mesh_coords(mesh, origin_offset, mesh_vertex_offsets)
    mesh.vertices.foreach_set("co", coords)

    uv_layer = mesh.uv_layers.active
    if uv_layer and mario_geo.uv_data:
        uv_data = [0.0] * (len(mesh.loops) * 2)
        for i in range(num_tris):
            base = 6 * i
            l_idx = 3 * i
            uv_data[2 * (l_idx + 0): 2 * (l_idx + 0) + 2] = [mario_geo.uv_data[base + 0], mario_geo.uv_data[base + 1]]
            uv_data[2 * (l_idx + 1): 2 * (l_idx + 1) + 2] = [mario_geo.uv_data[base + 2], mario_geo.uv_data[base + 3]]
            uv_data[2 * (l_idx + 2): 2 * (l_idx + 2) + 2] = [mario_geo.uv_data[base + 4], mario_geo.uv_data[base + 5]]
        uv_layer.data.foreach_set("uv", uv_data)

    color_attr = mesh.attributes.get("Col")
    if color_attr and mario_geo.color_data:
        colors = [1.0] * (len(mesh.loops) * 4)
        for i in range(num_tris):
            base_sm64 = 9 * i
            
            c0 = (3 * i + 0) * 4
            colors[c0:c0+3] = [mario_geo.color_data[base_sm64+0], mario_geo.color_data[base_sm64+1], mario_geo.color_data[base_sm64+2]]
            if num_tris > 752 and i >= num_tris - 8:
                colors[c0+3] = 0.0
            
            c1 = (3 * i + 1) * 4
            colors[c1:c1+3] = [mario_geo.color_data[base_sm64+3], mario_geo.color_data[base_sm64+4], mario_geo.color_data[base_sm64+5]]
            if num_tris > 752 and i >= num_tris - 8:
                colors[c1+3] = 0.0
            
            c2 = (3 * i + 2) * 4
            colors[c2:c2+3] = [mario_geo.color_data[base_sm64+6], mario_geo.color_data[base_sm64+7], mario_geo.color_data[base_sm64+8]]
            if num_tris > 752 and i >= num_tris - 8:
                colors[c2+3] = 0.0
            
        color_attr.data.foreach_set("color", colors)

    mesh.validate(verbose=False)
    mesh.update()

def update_mesh_data_fast(mesh: bpy.types.Mesh, origin_offset, mesh_vertex_offsets: dict = {}):
    mario_obj = bpy.data.objects.get('LibSM64 Mario')
    if mario_obj and mario_obj.mode == 'EDIT':
        return
    
    coords = get_mesh_coords(mesh, origin_offset, mesh_vertex_offsets)

    mesh.vertices.foreach_set("co", coords)
    mesh.validate(verbose=False)
    mesh.update()

def get_mesh_coords(mesh: bpy.types.Mesh, origin_offset, mesh_vertex_offsets):
    num_tris = mario_geo.numTrianglesUsed
    if num_tris == 0 or len(mesh.vertices) == 0:
        return

    coords = [0.0] * (len(mesh.vertices) * 3)
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
                
            edge1, edge2 = sim_v[1] - sim_v[0], sim_v[2] - sim_v[0]
            valid_basis = False
            
            if edge1.length > 0.0001 and edge2.length > 0.0001:
                v_tangent = edge1.normalized()
                cross_prod = edge1.cross(edge2)
                if cross_prod.length > 0.0001:
                    v_normal = cross_prod.normalized()
                    v_bitangent = v_normal.cross(v_tangent).normalized()
                    tri_basis = mathutils.Matrix((v_tangent, v_bitangent, v_normal)).transposed()
                    valid_basis = True
                    
            for v in range(3):
                vert_number = (i * 3) + v
                final_pos = sim_v[v].copy()
                
                if vert_number in mesh_vertex_offsets:
                    off_x, off_y, off_z, is_local = mesh_vertex_offsets[vert_number]
                    local_delta_vec = mathutils.Vector((off_x, off_y, off_z))
                    
                    if is_local == 1 and valid_basis:
                        final_pos += tri_basis @ local_delta_vec
                    else:
                        final_pos += local_delta_vec
                
                b_sub = base_blender + (v * 3)
                coords[b_sub : b_sub + 3] = final_pos

    return coords

def is_inside_volume(vector, obj):
    #Transform the world-space vector into the object's local space
    matrix_invert = obj.matrix_world.inverted()
    local_vector = matrix_invert @ vector

    ray_destination = local_vector + mathutils.Vector((0, 0, 10000))

    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    bvh = mathutils.bvhtree.BVHTree.FromObject(obj_eval, depsgraph)

    intersections = 0
    ray_origin = local_vector

    while True:
        location, normal, index, distance = bvh.ray_cast(ray_origin, ray_destination - ray_origin)

        if location is None:
            break

        intersections += 1
        
        ray_origin = location + (ray_destination - ray_origin).normalized() * 0.0001

    # An odd number of intersections means the point started *inside* the closed volume
    return (intersections % 2) == 1