import os
import bpy
from threading  import Thread
from subprocess import PIPE, Popen
from queue import Queue

g_proc = None

def sample_input_reader(mario_inputs):
    global g_proc
    from . import config, input_value

    if config['keyboard_control']:
        stickX = input_value['LEFT']*1 - input_value['RIGHT']*1
        stickY = input_value['UP']*1 - input_value['DOWN']*1

        stickX = max(-1.0, min(stickX, 1.0))
        stickY = max(-1.0, min(stickY, 1.0))

        mario_inputs.stickX = stickX
        mario_inputs.stickY = stickY
        mario_inputs.camLookX = 0.0
        mario_inputs.camLookZ = 0.0
        mario_inputs.buttonA = input_value['A']
        mario_inputs.buttonB = input_value['B']
        mario_inputs.buttonZ = input_value['C']

def process_controller_event(event, mario_inputs, sdl):
    if event.type == sdl.SDL_JOYAXISMOTION:
        axis_num = event.jaxis.axis
        raw_value = float(event.jaxis.value)

        scaled_value = raw_value / 512.0
        if abs(scaled_value) < 8.0:
            scaled_value = 0.0

        normalized_value = scaled_value / 64.0

        match axis_num:
            case 0:
                mario_inputs.stickX = -normalized_value
            case 1:
                mario_inputs.stickY = -normalized_value
            case 2:
                mario_inputs.camLookZ = -normalized_value
            case 3:
                mario_inputs.camLookX = -normalized_value

    elif event.type == sdl.SDL_JOYBUTTONDOWN:
        match event.jbutton.button:
            case 0:
                mario_inputs.buttonA = True
            case 1:
                mario_inputs.buttonB = True
            case 2:
                mario_inputs.buttonZ = True

    elif event.type == sdl.SDL_JOYBUTTONUP:
        match event.jbutton.button:
            case 0:
                mario_inputs.buttonA = False
            case 1:
                mario_inputs.buttonB = False
            case 2:
                mario_inputs.buttonZ = False

def reset_controller_inputs(mario_inputs):
    mario_inputs.stickX = 0.0
    mario_inputs.stickY = 0.0
    mario_inputs.camLookX = 0.0
    mario_inputs.camLookZ = 0.0
    mario_inputs.buttonA = False
    mario_inputs.buttonB = False
    mario_inputs.buttonZ = False