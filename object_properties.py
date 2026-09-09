import bpy
from .surface_terrains import SURFACE_TYPES
from .surface_terrains import TERRAIN_TYPES

class OBJECT_PT_terrain_types(bpy.types.Panel):
    bl_label = "Terrain Type"
    bl_idname = "OBJECT_PT_terrain_types"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        layout = self.layout
        obj = context.object

        box = layout.box()

        box.prop(obj, "sm64_terrain_type_dropdown")

        current_name = obj.sm64_terrain_type_dropdown
        current_hex = TERRAIN_TYPES.get(current_name, "N/A")

        row = box.row()
        row.label(text=f"Active Hex: {current_hex}")

class OBJECT_PT_surface_types(bpy.types.Panel):
    bl_label = "Surface Type"
    bl_idname = "OBJECT_PT_surface_types"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        layout = self.layout
        obj = context.object

        box = layout.box()

        box.prop(obj, "sm64_surface_type_dropdown")

        current_name = obj.sm64_surface_type_dropdown
        current_hex = SURFACE_TYPES.get(current_name, "N/A")

        row = box.row()
        row.label(text=f"Active Hex: {current_hex}")