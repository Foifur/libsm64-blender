import ctypes as ct
import os
import platform

from . import sm64_types

class SM64Library:
    def __init__(self):
        self._this_path = os.path.dirname(os.path.realpath(__file__))
        self._dll_name = 'sm64.dll' if platform.system() == 'Windows' else 'libsm64.so'
        self._dll_path = os.path.join(self._this_path, 'lib', self._dll_name)

        self._dll = ct.CDLL(self._dll_path)

        self.initialize_sm64_functions(self._dll)

    def initialize_sm64_functions(self, dll):
        global sm64
        dll.sm64_global_init.argtypes = [ ct.c_char_p, ct.POINTER(ct.c_ubyte) ]
        dll.sm64_static_surfaces_load.argtypes = [ ct.POINTER(sm64_types.SM64Surface), ct.c_uint32 ]
        dll.sm64_mario_create.argtypes = [ ct.c_float, ct.c_float, ct.c_float ]
        dll.sm64_mario_create.restype = ct.c_int32
        dll.sm64_mario_tick.argtypes = [ ct.c_uint32, ct.POINTER(sm64_types.SM64MarioInputs), ct.POINTER(sm64_types.SM64MarioState), ct.POINTER(sm64_types.SM64MarioGeometryBuffers) ]
        dll.sm64_mario_interact_cap.argtypes = [ ct.c_int32, ct.c_uint32, ct.c_uint16, ct.c_uint8 ]

        dll.sm64_audio_init.argtypes = [ct.c_char_p]
        dll.sm64_audio_init.restype = None
        dll.sm64_audio_tick.argtypes = [ ct.c_uint32, ct.c_uint32, ct.POINTER(ct.c_int16)]
        dll.sm64_audio_tick.restype = ct.c_uint32
        dll.sm64_play_music.argtypes = [ ct.c_uint8, ct.c_uint16, ct.c_uint16 ]
        dll.sm64_play_sound.argtypes = [ ct.c_int32, ct.POINTER(ct.c_float) ]

        dll.sm64_set_mario_action.argtypes = [ ct.c_int32, ct.c_uint32 ]
        dll.sm64_set_mario_water_level.argtypes = [ ct.c_int32, ct.c_int ]

        dll.sm64_surface_object_create.argtypes = [ ct.POINTER(sm64_types.SM64SurfaceObject) ]
        dll.sm64_surface_object_create.restype = ct.c_uint32
        dll.sm64_surface_object_move.argtypes = [ ct.c_uint32, ct.POINTER(sm64_types.SM64ObjectTransform) ]


    def global_init(self, rom: ct.c_char_p, outTexture: ct.c_ubyte) -> None:
        return self._dll.sm64_global_init(rom, outTexture)

    def global_terminate(self) -> None:
        return self._dll.sm64_global_terminate()

    def static_surfaces_load(self, surfaceArray: sm64_types.SM64Surface, numSurfaces: ct.c_uint32) -> None:
        return self._dll.sm64_static_surfaces_load(surfaceArray, numSurfaces)

    def mario_create(self, x: ct.c_float, y: ct.c_float, z: ct.c_float) -> ct.c_int32:
        return self._dll.sm64_mario_create(x, y, z)

    def mario_tick(self, marioId: ct.c_uint32, inputs: sm64_types.SM64MarioInputs, 
                   outState: sm64_types.SM64MarioState, outBuffers: sm64_types.SM64MarioGeometryBuffers) -> None:
        return self._dll.sm64_mario_tick(marioId, inputs, outState, outBuffers)

    def mario_interact_cap(self, marioId: ct.c_int32, capFlag: ct.c_uint32, capTime: ct.c_uint16, playMusic: ct.c_uint8) -> None:
        return self._dll.sm64_mario_interact_cap(marioId, capFlag, capTime, playMusic)

    def audio_init(self, rom: ct.c_char_p) -> None:
        return self._dll.sm64_audio_init(rom)

    def audio_tick(self, numQueuedSamples: ct.c_uint32, numDesiredSamples: ct.c_uint32, audio_buffer: ct.c_int16) -> ct.c_uint32:
        return self._dll.sm64_audio_tick(numQueuedSamples, numDesiredSamples, audio_buffer)

    def play_music(self, player: ct.c_uint8, seqArgs: ct.c_uint16, fadeTimer: ct.c_uint16) -> None:
        return self._dll.sm64_play_music(player, seqArgs, fadeTimer)

    def play_sound(self, soundBits: ct.c_int32, pos: ct.c_float) -> None:
        return self._dll.sm64_play_sound(soundBits, pos)

    def set_mario_action(self, marioId: ct.c_int32, action: ct.c_uint32) -> None:
        return self._dll.sm64_set_mario_action(marioId, action)

    def set_mario_water_level(self, marioId: ct.c_int32, level: ct.c_int) -> None:
        return self._dll.sm64_set_mario_water_level(marioId, level)

    def surface_object_create(self, surfaceObject: sm64_types.SM64SurfaceObject) -> ct.c_uint32:
        return self._dll.sm64_surface_object_create(surfaceObject)

    def surface_object_move(self, objectId: ct.c_uint32, transform: sm64_types.SM64ObjectTransform) -> None:
        return self._dll.sm64_surface_object_move(objectId, transform)