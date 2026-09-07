bl_info = {
    "name" : "libsm64-blender",
    "author" : "libsm64",
    "description" : "Add a playble Mario to your Blender Scene",
    "blender" : (2, 80, 0),
    "version" : (2, 0, 0),
    "location" : "View3D",
    "warning" : "",
    "category" : "Generic"
}

import os
import sys
import bpy
import platform
from .mario import insert_mario
from .mario import mario_inputs
from . import mario
from .audio_types import MusicSeqId
from .surface_terrains import SURFACE_TYPES
from .surface_terrains import TERRAIN_TYPES
from .input_reader import process_controller_event
from .input_reader import reset_controller_inputs
import ctypes

addon_dir = os.path.dirname(os.path.realpath(__file__))
libs_path = os.path.join(addon_dir, "lib")

if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

os.environ["PYSDL2_DLL_PATH"] = libs_path

from .lib import sdl2 as sdl

def make_enum_items():
    items = []
    for member in MusicSeqId:
        identifier = member.name
        name = member.name.replace("SEQ_", "").replace("_", " ").title()
        description = f"Sequence ID: {hex(member.value)}"

        items.append((identifier, name, description, "", member.value))
    return items

def update_music_selection(self, context):
    selected_string = context.scene.music_dropdown
    enum_member = MusicSeqId[selected_string]
    mario.music_select = enum_member.value

bpy.types.Scene.music_dropdown = bpy.props.EnumProperty(
    name="Music Select",
    items=make_enum_items(),
    update=update_music_selection,
    default=MusicSeqId.SEQ_RANDOM_MUSIC.name
)

def update_follow_cam(self, context):
    mario.follow_cam = self.camera_follow

class LibSm64Properties(bpy.types.PropertyGroup):
    camera_follow: bpy.props.BoolProperty (
        name="Follow Mario with 3D cursor + camera",
        default=True,
        update=update_follow_cam
    ) # type: ignore
    camera_shift: bpy.props.FloatVectorProperty (
        name='Camera Offset',
        description='Camera Offset from Mario Origin.',
        default=(0.0, 0.0, 1.0),
        soft_min =-10.0,
        soft_max = 10.0,
        step=10,
        precision=3,
        subtype='XYZ',
        unit='LENGTH',
        size=3
    ) # type: ignore
    mario_scale: bpy.props.FloatProperty(
        name="Blender to SM64 Scale",
        default=100
    ) # type: ignore

class LibSm64Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    rom_path: bpy.props.StringProperty(
        name="Path",
        description="Path to an unmodified US SM64 ROM",
        subtype='FILE_PATH',
        default=('c:\\sm64.us.z64' if platform.system() == 'Windows' else '~/sm64.us.z64')
    ) # type: ignore
    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text="SM64 US ROM (Unmodified, 8 MB, z64)")
        col.prop(self, 'rom_path')

class Main_PT_Panel(bpy.types.Panel):
    bl_idname = "LIBSM64_PT_main_panel"
    bl_label = "Insert Mario"
    bl_category = "LibSM64"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        preferences = context.preferences.addons[__package__].preferences

        col = layout.column()
        prop_split(col, scene.libsm64, "mario_scale", "Blender to SM64 Scale")
        col.prop(preferences, "rom_path")
        col.prop(scene.libsm64, "camera_follow")
        col.prop(scene, "music_dropdown", text = "Choose")
        col.operator(InsertMario_OT_Operator.bl_idname, text='Insert Mario')
        col.prop(scene.libsm64, "camera_shift")
        col.operator(ControlMario_OT_Operator.bl_idname, text='Control Mario with keyboard')
        col.label(text="WASD + JKL to move. ESC to stop.")
        col.operator("object.sdl_modal", text="Connect Controller")
        col.operator(AddWingCap_OT_Operator.bl_idname, text='Add Wing Cap')
        col.operator(AddMetalCap_OT_Operator.bl_idname, text='Add Metal Cap')

class InsertMario_OT_Operator(bpy.types.Operator):
    bl_idname = "view3d.libsm64_insert_mario"
    bl_label = "Insert Mario"
    bl_description = "Inserts a Mario into the scene"

    def execute(self, context):
        scene = context.scene
        preferences = context.preferences.addons[__package__].preferences
        err = insert_mario(preferences.rom_path, scene.libsm64.mario_scale, scene.libsm64.camera_follow)
        if err != None:
            self.report({"ERROR"}, err)
        return {'FINISHED'}

class AddWingCap_OT_Operator(bpy.types.Operator):
    bl_idname = "view3d.libsm64_add_wing_cap"
    bl_label = "Add Wing Cap"

    def execute(self, context):
        scene = context.scene
        err = mario.add_cap(mario.MARIO_WING_CAP)
        if err != None:
            self.report({"ERROR"}, err)
        return {'FINISHED'}

class AddMetalCap_OT_Operator(bpy.types.Operator):
    bl_idname = "view3d.libsm64_add_metal_cap"
    bl_label = "Add Metal Cap"

    def execute(self, context):
        scene = context.scene
        err = mario.add_cap(mario.MARIO_METAL_CAP)
        if err != None:
            self.report({"ERROR"}, err)
        return {'FINISHED'}

class ControlMario_OT_Operator(bpy.types.Operator):
    bl_idname = "view3d.libsm64_control_mario"
    bl_label = "Control with keyboard"
    bl_description = "Control Mario with keyboard"

    def invoke(self, context, event):
        global config
        config["keyboard_control"] = True
        if 'LibSM64 Mario' not in bpy.data.objects:
            return self.report({"ERROR"}, 'Insert Mario first.')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if not config["keyboard_control"]:
            return {'FINISHED'}
        if event.type == 'ESC':
            config["keyboard_control"] = False
            return {'FINISHED'}

        process_input(event)

        return {'RUNNING_MODAL'}

class ConnectController_OT_Operator(bpy.types.Operator):
    """Read SDL2 Controller inputs inside Blender"""
    bl_idname = "object.sdl_modal"
    bl_label = "Start SDL2 Controller Reader"
    
    _timer = None
    _joystick = None
    _event = None

    def modal(self, context, event):
        # Stop tracking instantly if the user presses ESC inside the Blender Viewport
        if event.type in {'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}

        if self._event:
            while sdl.SDL_PollEvent(ctypes.byref(self._event)) != 0:
                process_controller_event(self._event, mario_inputs, sdl)

        # Pass event through so normal Blender navigation (mouse pan, zoom) still works
        return {'PASS_THROUGH'}

    def execute(self, context):
        sdl.SDL_Init(sdl.SDL_INIT_JOYSTICK)
        
        # Check for connected physical hardware
        if sdl.SDL_NumJoysticks() > 0:
            self._joystick = sdl.SDL_JoystickOpen(0)
            print(f"Connected Controller: {sdl.SDL_JoystickName(self._joystick)}")
        else:
            self.report({'WARNING'}, "No controller detected! Connect a device and retry.")
            return {'CANCELLED'}

        self._event = sdl.SDL_Event()
        
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.01, window=context.window)
        wm.modal_handler_add(self)
        
        print("SDL2 Controller Reader Started. Press 'ESC' in the 3D Viewport to stop.")
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)

        if self._joystick:
            sdl.SDL_JoystickClose(self._joystick)
        reset_controller_inputs(mario_inputs)
        sdl.SDL_Quit()
        
        print("SDL2 Controller Reader Stopped.")

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

config = {
    'keyboard_control': False
}

input_value = {
    'UP': False,
    'DOWN': False,
    'LEFT': False,
    'RIGHT': False,
    'A': False,
    'B': False,
    'C': False,
}

input_config = {
    'UP': 'W',
    'DOWN': 'S',
    'LEFT': 'A',
    'RIGHT': 'D',
    'A': 'J',
    'B': 'K',
    'C': 'L',
}

def process_input(event):
    for k, v in input_config.items():
        if event.type == v:
            if event.value == 'PRESS':
                input_value[k] = True
            else:
                input_value[k] = False


register_classes, unregister_classes = bpy.utils.register_classes_factory((
    LibSm64Properties,
    LibSm64Preferences,
    Main_PT_Panel,
    InsertMario_OT_Operator,
    ControlMario_OT_Operator,
    ConnectController_OT_Operator,
    AddWingCap_OT_Operator,
    AddMetalCap_OT_Operator,
    OBJECT_PT_terrain_types,
    OBJECT_PT_surface_types
))

def register():

    bpy.types.Object.sm64_terrain_type_dropdown = bpy.props.EnumProperty(
        name="SM64 Terrain Type",
        description="Sets the terrain type for Mario to interact with",
        items=get_terrain_types
    )

    bpy.types.Object.sm64_surface_type_dropdown = bpy.props.EnumProperty(
        name="SM64 Surface Type",
        description="Sets the surface type for Mario to interact with",
        items=get_surface_types
    )

    register_classes()
    bpy.types.Scene.libsm64 = bpy.props.PointerProperty(type=LibSm64Properties)

def unregister():
    unregister_classes()

    del bpy.types.Object.sm64_terrain_type_dropdown
    del bpy.types.Object.sm64_surface_type_dropdown

    del bpy.types.Scene.libsm64

def prop_split(layout, data, field, name):
    split = layout.split(factor = 0.5)
    split.label(text = name)
    split.prop(data, field, text = '')

def get_terrain_types(self, context):
    types = []

    for index, (col_type, value) in enumerate(TERRAIN_TYPES.items()):
        entry = (col_type, col_type, f"Hex Code: {value}", "", index)
        types.append(entry)

    return types

def get_surface_types(self, context):
    types = []

    for index, (col_type, value) in enumerate(SURFACE_TYPES.items()):
        entry = (col_type, col_type, f"Hex Code: {value}", "", index)
        types.append(entry)

    return types