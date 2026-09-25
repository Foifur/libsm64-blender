import bpy
from .surface_terrains import SurfaceTypes, TerrainTypes

class OBJECT_PT_SM64_Settings(bpy.types.Panel):
    bl_label = "SM64 Settings"
    bl_idname = "OBJECT_PT_sm64_settings"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        layout = self.layout
        obj = context.object

        layout.use_property_split = True

        # Dynamic Object Checkbox
        layout.prop(obj, "sm64_dynamic_object_checkbox", text="Dynamic Object")

        # Terrain Type Dropdown
        layout.prop(obj, "sm64_terrain_type_dropdown")

        current_name = obj.sm64_terrain_type_dropdown
        current_hex = getattr(TerrainTypes, current_name, None)

        row = layout.row()
        row.label(text=f"Active Hex: {current_hex}")

        # Surface Type Dropdown
        layout.prop(obj, "sm64_surface_type_dropdown")

        current_name = obj.sm64_surface_type_dropdown
        current_hex = getattr(SurfaceTypes, current_name, None)

        row = layout.row()
        row.label(text=f"Active Hex: {current_hex}")

def make_enum_items(enum):
    items = []
    for member in enum:
        identifier = member.name
        name = member.name.replace("SEQ_", "").replace("_", " ").title()
        description = f"Sequence ID: {hex(member.value)}"

        items.append((identifier, name, description, "", member.value))
    return items

def register_types():
    bpy.types.Object.sm64_dynamic_object_checkbox = bpy.props.BoolProperty(
        name="Dynamic Object",
        description="Tells the SM64 library that this is an object that can move dynamically",
        default=False
    )

    bpy.types.Object.sm64_terrain_type_dropdown = bpy.props.EnumProperty(
        name="Terrain Type",
        description="Sets the terrain type for Mario to interact with",
        items=make_enum_items(TerrainTypes)
    )

    bpy.types.Object.sm64_surface_type_dropdown = bpy.props.EnumProperty(
        name="Surface Type",
        description="Sets the surface type for Mario to interact with",
        items=make_enum_items(SurfaceTypes)
    )

def unregister_types():
    del bpy.types.Object.sm64_dynamic_object_checkbox
    del bpy.types.Object.sm64_terrain_type_dropdown
    del bpy.types.Object.sm64_surface_type_dropdown