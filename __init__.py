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
from . import mario
from . import object_properties as obj_props
from .audio_types import MusicSeqId
from .surface_terrains import SURFACE_TYPES
from .surface_terrains import TERRAIN_TYPES
from .input_reader import process_controller_event, reset_controller_inputs
from .controller_bindings import bindings as ctrl_bindings
import ctypes
from bpy.app.handlers import persistent

active_popup_regions = set()

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
        col.operator("object.controller_bindings_popup_dialog", text="Controller Bindings")
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

@persistent
def auto_connect_controller(dummy):
    bpy.ops.object.sdl_modal('INVOKE_DEFAULT')

class ConnectController_OT_Operator(bpy.types.Operator):
    """Read SDL2 Controller inputs inside Blender"""
    bl_idname = "object.sdl_modal"
    bl_label = "Start SDL2 Controller Reader"
    
    _timer = None
    _controller = None
    _event = None

    def _init_sdl_controller(self):
        sdl.SDL_SetHint(b"SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS", b"1")
        sdl.SDL_Init(sdl.SDL_INIT_JOYSTICK | sdl.SDL_INIT_GAMECONTROLLER)
        sdl.SDL_PumpEvents()
        
        # Check for connected physical hardware
        if sdl.SDL_NumJoysticks() <= 0:
            return None
        
        for idx in range(sdl.SDL_NumJoysticks()):
            if sdl.SDL_IsGameController(idx):
                return sdl.SDL_GameControllerOpen(idx)

        return None

    def _handle_rebind_logic(self, operator, ev) -> bool:
        target = rebind_manager.state["target"]
        is_axis_target = target in controller_bindings.AXIS_INPUTS

        if is_axis_target:
            # Make sure the axis is moved far enough to count as a rebind
            if ev.type == sdl.SDL_CONTROLLERAXISMOTION and abs(ev.caxis.value) > 19500:
                controller_bindings.update_bindings(target, ev.caxis.axis)
                rebind_manager.finish()
                return True
        else:
            if ev.type == sdl.SDL_CONTROLLERBUTTONDOWN:
                controller_bindings.update_bindings(target, ev.cbutton.button)
                rebind_manager.finish()
                return True
            
        return False


    def _reset_state(self):
        self._timer = None
        self._controller = None
        self._event = None

    def invoke(self, context, event):
        return self.execute(context)
    
    def modal(self, context, event):
        if not (self._controller and self._event):
            return {'PASS_THROUGH'}

        while sdl.SDL_PollEvent(ctypes.byref(self._event)) != 0:
            if rebind_manager.state["active"]:
                if self._handle_rebind_logic(self, self._event):
                    return {'PASS_THROUGH'}
                continue # Skip normal processing during rebinding

            process_controller_event(self._event, sdl)

        return {'PASS_THROUGH'}

    def execute(self, context):
        if self._controller:
            self.cancel(context)

        self._reset_state()

        self._controller = self._init_sdl_controller()
        if not self._controller:
            self.report({'ERROR'}, "No compatible game controller found or failed to open.")
            sdl.SDL_Quit()
            return {'CANCELLED'}

        name = sdl.SDL_GameControllerName(self._controller)
        self.report({'INFO'}, f"Connected Controller: {name}")

        self._event = sdl.SDL_Event()
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.01, window=context.window)
        wm.modal_handler_add(self)
        
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)

        if self._controller:
            sdl.SDL_GameControllerClose(self._controller)

        self._reset_state()
        reset_controller_inputs()
        sdl.SDL_Quit()

class OBJECT_OT_controller_bindings_popup_dialog(bpy.types.Operator):
    """Open a simple popup dialog"""
    bl_idname = "object.controller_bindings_popup_dialog"
    bl_label = "Controller Bindings"

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout

        popup_reg = context.region_popup
        if popup_reg and popup_reg not in active_popup_regions:
            active_popup_regions.add(popup_reg)
            
        # ── Axes ──
        layout.label(text="Analog Joystick Axes:")
        for prop in controller_bindings.AXIS_INPUTS:
            row = layout.row()
            row.label(text=controller_bindings.FUNCTIONAL_NAME.get(prop, prop))
            listening = rebind_manager.state["active"] and rebind_manager.state["target"] == prop
            if listening:
                row.label(text="…press an axis…", icon="NONE")
            else:
                btn = row.operator("object.rebind_input",
                                  text=f"Axis {ctrl_bindings[prop]}")
                btn.target_property = prop
                btn.is_axis_type = True

        layout.separator()

        # ── Buttons ──
        layout.label(text="Controller Buttons:")
        for prop in controller_bindings.BUTTON_INPUTS:
            row = layout.row()
            row.label(text=controller_bindings.FUNCTIONAL_NAME.get(prop, prop))
            listening = rebind_manager.state["active"] and rebind_manager.state["target"] == prop
            if listening:
                row.label(text="…press a button…", icon="NONE")
            else:
                btn = row.operator("object.rebind_input",
                                  text=f"Button {ctrl_bindings[prop]}")
                btn.target_property = prop
                btn.is_axis_type = False


class OBJECT_OT_rebind_input(bpy.types.Operator):
    """Click to listen for the next SDL input and assign it"""
    bl_idname = "object.rebind_input"
    bl_label = ""

    target_property: bpy.props.StringProperty() # type: ignore
    is_axis_type: bpy.props.BoolProperty(default=False) #  type: ignore

    def execute(self, context):
        rebind_manager.start(self.target_property)
        

        self.report({'INFO'},
            f"Waiting for input... (rebinding '{self.target_property}')"
        )
        return {'FINISHED'}

    def modal(self, context, event):
        if event.type in {'ESC'}:
            if rebind_manager.state["active"]:
                rebind_manager.finish()
                return {'PASS_THROUGH'}
            self.cancel(context)
            return {'CANCELLED'}

class RebindManager:
    def __init__(self):
        self.state = {
            "active": False,
            "target": None
        }

    def start(self, target: str):
        self.state["active"] = True
        self.state["target"] = target
        bpy.app.timers.register(self.timeout, first_interval=5.0)

    def finish(self):
        self.state["active"] = False
        self.state["target"] = None

        if bpy.app.timers.is_registered(self._timeout):
            bpy.app.timers.unregister(self._timeout)

        for region in list(active_popup_regions):
            region.tag_redraw()
            region.tag_refresh_ui()

    def _timeout(self):
        print("Rebinding timed out.")
        if self.state["active"]:
            self.finish()
        return None

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


rebind_manager = RebindManager()
register_classes, unregister_classes = bpy.utils.register_classes_factory((
    LibSm64Properties,
    LibSm64Preferences,
    Main_PT_Panel,
    InsertMario_OT_Operator,
    ControlMario_OT_Operator,
    ConnectController_OT_Operator,
    AddWingCap_OT_Operator,
    AddMetalCap_OT_Operator,
    obj_props.OBJECT_PT_terrain_types,
    obj_props.OBJECT_PT_surface_types,
    OBJECT_OT_controller_bindings_popup_dialog,
    OBJECT_OT_rebind_input,     
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
    bpy.app.handlers.load_post.append(auto_connect_controller)

def unregister():
    unregister_classes()

    del bpy.types.Object.sm64_terrain_type_dropdown
    del bpy.types.Object.sm64_surface_type_dropdown

    del bpy.types.Scene.libsm64

    if auto_connect_controller in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(auto_connect_controller)

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
