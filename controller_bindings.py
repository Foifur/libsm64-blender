DEFAULT_BINDINGS = {
    "buttonA":  0,
    "buttonB":  1,
    "buttonZ":  2,
    "stickX":   0,
    "stickY":   1,
    "camLookX": 2,
    "camLookZ": 3,
}

FUNCTIONAL_NAME = {
    "buttonA": "Jump",
    "buttonB": "Punch",
    "buttonZ": "Crouch",
    "stickX": "Move X Axis",
    "stickY": "Move Y Axis",
    "camLookX": "Camera Look X Axis",
    "camLookZ": "Camera Look Y Axis",
}

AXIS_INPUTS = tuple(dict.fromkeys(["stickX", "stickY", "camLookX", "camLookZ"]))
BUTTON_INPUTS = tuple(dict.fromkeys(["buttonA", "buttonB", "buttonZ"]))

bindings: dict[str, int] = dict(DEFAULT_BINDINGS)


def reset():
    bindings.clear()
    bindings.update(DEFAULT_BINDINGS)


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

def update_bindings(target: str, new_value: int) -> str | None:
    """Swap the bindings of two logical names if they are currently bound to the same index."""
    current_value = bindings.get(target)
    target_is_axis = is_axis(target)

    for key, value in bindings.items():
        if value == new_value and key != target:
            if is_axis(key) == target_is_axis:
                bindings[key] = current_value
                bindings[target] = new_value
                return key
            
    bindings[target] = new_value
    return None