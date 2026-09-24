import json
import bpy

DEFAULT_BINDINGS = {
    "buttonA":  0,
    "buttonB":  1,
    "buttonZ":  10,
    "changeCamera": 8,
    "stickX":   0,
    "stickY":   1,
    "camLookX": 2,
    "camLookZ": 3,
}

FUNCTIONAL_NAME = {
    "buttonA": "Jump",
    "buttonB": "Punch",
    "buttonZ": "Crouch",
    "changeCamera": "Change Camera Distance",
    "stickX": "Move X Axis",
    "stickY": "Move Y Axis",
    "camLookX": "Camera Look X Axis",
    "camLookZ": "Camera Look Y Axis",
}

AXIS_INPUTS = tuple(dict.fromkeys(["stickX", "stickY", "camLookX", "camLookZ"]))
BUTTON_INPUTS = tuple(dict.fromkeys(["buttonA", "buttonB", "buttonZ", "changeCamera"]))

bindings: dict[str, int] = dict(DEFAULT_BINDINGS)

class OBJECT_OT_Reset_Bindings(bpy.types.Operator):
    bl_idname = "object.reset_bindings"
    bl_label = ""

    def execute(self, context):
        reset()
        self.report({'INFO'},
                    f"Controller bindings reset to default.")

        return {'FINISHED'}

def get_bindings_string(pref_instance):
    sys_props = pref_instance.bl_system_properties_get(do_create=True)

    stored_str = sys_props.get("bindings_json")
    if not stored_str:
        return json.dumps(DEFAULT_BINDINGS)
    return stored_str

def set_bindings_string(pref_instance, value):
    sys_props = pref_instance.bl_system_properties_get(do_create=True)
    sys_props["bindings_json"] = value

def load_as_dict(pref_instance):
    global bindings
    try:
        json_str = get_bindings_string(pref_instance)
        bindings = json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        print(f"Failed to find saved controller bindings, loading default")
        bindings = DEFAULT_BINDINGS.copy()

def save_from_dict(pref_instance, py_dict):
    pref_instance.bindings_json = json.dumps(py_dict)

def reset():
    bindings.clear()
    bindings.update(DEFAULT_BINDINGS)
    save_from_dict(bpy.context.preferences.addons[__package__].preferences, bindings)
    bpy.ops.wm.save_userpref()

def get_functional_name(property):
    return FUNCTIONAL_NAME.get(property, property)

def is_axis(name: str) -> bool:
    return name in AXIS_INPUTS


def is_button(name: str) -> bool:
    return name in BUTTON_INPUTS


def sdl_axis_to_sm64(axis_index: int) -> str | None:
    for name, idx in bindings.items():
        if idx == axis_index and name in AXIS_INPUTS:
            return name
    return None


def sdl_button_to_sm64(button_index: int) -> str | None:
    for name, idx in bindings.items():
        if idx == button_index and name in BUTTON_INPUTS:
            return name
    return None

def update_bindings(target: str, new_value: int) -> None:
    """Swap the bindings of two logical names if they are currently bound to the same index."""
    current_value = bindings.get(target)
    target_is_axis = is_axis(target)

    for key, value in bindings.items():
        if value == new_value and key != target:
            if is_axis(key) == target_is_axis:
                bindings[key] = current_value
            
    bindings[target] = new_value
    save_from_dict(bpy.context.preferences.addons[__package__].preferences, bindings)
    bpy.ops.wm.save_userpref()