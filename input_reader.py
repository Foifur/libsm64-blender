import os
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