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
    global follow_cam
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
        layout.prop(scene, "music_dropdown", text = "Choose")
        col.operator(InsertMario_OT_Operator.bl_idname, text='Insert Mario')
        col.prop(scene.libsm64, "camera_shift")
        col.operator(ControlMario_OT_Operator.bl_idname, text='Control Mario with keyboard')
        col.label(text="WASD + JKL to move. ESC to stop.")
        col.operator("object.sdl_modal", text="Connect Controller")

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
                # Handle Axis Motion
                if self._event.type == sdl.SDL_JOYAXISMOTION:
                    axis_num = self._event.jaxis.axis
                    raw_val = float(self._event.jaxis.value)
                    #print(f"Axis {axis_num}: {raw_val}")

                    scaled_val = raw_val / 512.0

                    if abs(scaled_val) < 8.0:
                        scaled_val = 0.0

                    normalized_val = scaled_val / 64.0

                    match axis_num:
                        case 0:
                            mario_inputs.stickX = -normalized_val
                        case 1:
                            mario_inputs.stickY = -normalized_val
                        case 2:
                            mario_inputs.camLookZ = -normalized_val
                        case 3:
                            mario_inputs.camLookX = -normalized_val

                # Handle Button Presses
                elif self._event.type == sdl.SDL_JOYBUTTONDOWN:
                    btn_num = self._event.jbutton.button
                    print(f"Button {btn_num} Pressed")

                    match btn_num:
                        case 0:
                            mario_inputs.buttonA = True
                        case 1:
                            mario_inputs.buttonB = True
                        case 2:
                            mario_inputs.buttonZ = True
                    
                # Handle Button Releases
                elif self._event.type == sdl.SDL_JOYBUTTONUP:
                    btn_num = self._event.jbutton.button
                    print(f"Button {btn_num} Released")

                    match btn_num:
                        case 0:
                            mario_inputs.buttonA = False
                        case 1:
                            mario_inputs.buttonB = False
                        case 2:
                            mario_inputs.buttonZ = False

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
        sdl.SDL_Quit()
        
        print("SDL2 Controller Reader Stopped.")

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
    ConnectController_OT_Operator
))

def register():
    register_classes()
    bpy.types.Scene.libsm64 = bpy.props.PointerProperty(type=LibSm64Properties)

def unregister():
    unregister_classes()
    del bpy.types.Scene.libsm64

def prop_split(layout, data, field, name):
    split = layout.split(factor = 0.5)
    split.label(text = name)
    split.prop(data, field, text = '')
