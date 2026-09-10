import os
import bpy
from threading  import Thread
from subprocess import PIPE, Popen
from queue import Queue
from . import controller_bindings
from . import mario

g_proc = None

def sample_input_reader():
    global g_proc
    from . import config, input_value

    if config['keyboard_control']:
        stickX = input_value['LEFT']*1 - input_value['RIGHT']*1
        stickY = input_value['UP']*1 - input_value['DOWN']*1

        stickX = max(-1.0, min(stickX, 1.0))
        stickY = max(-1.0, min(stickY, 1.0))

        mario.mario_inputs.stickX = stickX
        mario.mario_inputs.stickY = stickY
        mario.mario_inputs.camLookX = 0.0
        mario.mario_inputs.camLookZ = 0.0
        mario.mario_inputs.buttonA = input_value['A']
        mario.mario_inputs.buttonB = input_value['B']
        mario.mario_inputs.buttonZ = input_value['C']

def process_controller_event(event, sdl):
    if event.type == sdl.SDL_CONTROLLERAXISMOTION:
        axis_num = event.caxis.axis
        raw_value = float(event.caxis.value)

        scaled_value = raw_value / 512.0
        if abs(scaled_value) < 8.0:
            scaled_value = 0.0

        normalized_value = scaled_value / 64.0

        axis_name = controller_bindings.sdl_axis_to_sm64(axis_num)
        if axis_name:
            setattr(mario.mario_inputs, axis_name, -normalized_value)

    elif event.type == sdl.SDL_CONTROLLERBUTTONDOWN:
        button_name = controller_bindings.sdl_button_to_sm64(event.cbutton.button)

        is_mario_input = any(name == button_name for name, _ in mario.mario_inputs._fields_)
        if is_mario_input:
            print(f"has {button_name}")
            setattr(mario.mario_inputs, button_name, True)
        else:
            print(f"doesn't have {button_name}")
            handle_client_button(button_name)

    elif event.type == sdl.SDL_CONTROLLERBUTTONUP:
        button_name = controller_bindings.sdl_button_to_sm64(event.cbutton.button)
        if button_name:
            setattr(mario.mario_inputs, button_name, False)

def reset_controller_inputs():
    mario.mario_inputs.stickX = 0.0
    mario.mario_inputs.stickY = 0.0
    mario.mario_inputs.camLookX = 0.0
    mario.mario_inputs.camLookZ = 0.0
    mario.mario_inputs.buttonA = False
    mario.mario_inputs.buttonB = False
    mario.mario_inputs.buttonZ = False

def handle_client_button(button_name):
    print(button_name)
    match button_name:
        case "changeCamera":
            if mario.base_zoom_distance is not None:
                if mario.base_zoom_distance > 5.0:
                    mario.base_zoom_distance = 5.0
                else:
                    mario.base_zoom_distance = 20.0