import ctypes as ct
from . import mesh_helpers

class SM64Surface(ct.Structure):
    surftype: int
    force: int
    terrain: int
    v0x: int
    v0y: int
    v0z: int
    v1x: int
    v1y: int
    v1z: int
    v2x: int
    v2y: int
    v2z: int

    _fields_ = [
        ('surftype', ct.c_int16),
        ('force', ct.c_int16),
        ('terrain', ct.c_uint16),
        ('v0x', ct.c_int32), ('v0y', ct.c_int32), ('v0z', ct.c_int32),
        ('v1x', ct.c_int32), ('v1y', ct.c_int32), ('v1z', ct.c_int32),
        ('v2x', ct.c_int32), ('v2y', ct.c_int32), ('v2z', ct.c_int32)
    ]

class SM64MarioInputs(ct.Structure):
    camLookX: float
    camLookZ: float
    stickX: float
    stickY: float
    buttonA: int
    buttonB: int
    buttonZ: int

    _fields_ = [
        ('camLookX', ct.c_float), ('camLookZ', ct.c_float),
        ('stickX', ct.c_float), ('stickY', ct.c_float),
        ('buttonA', ct.c_ubyte), ('buttonB', ct.c_ubyte), ('buttonZ', ct.c_ubyte),
    ]

class SM64ObjectTransform(ct.Structure):
    posX: float
    posY: float
    posZ: float
    eulX: float
    eulY: float
    eulZ: float

    _fields_ = [
        ('posX', ct.c_float), ('posY', ct.c_float), ('posZ', ct.c_float),
        ('eulX', ct.c_float), ('eulY', ct.c_float), ('eulZ', ct.c_float),
    ]

class SM64SurfaceObject(ct.Structure):
    transform: SM64ObjectTransform
    surfaceCount: int
    surfaces: "ct._Pointer[SM64Surface]"

    _fields_ = [
        ('transform', SM64ObjectTransform),
        ('surfaceCount', ct.c_uint32),
        ('surfaces', ct.POINTER(SM64Surface))
    ]

class SM64MarioState(ct.Structure):
    posX: float
    posY: float
    posZ: float
    velX: float
    velY: float
    velZ: float
    faceAngle: float
    forwardVelocity: float
    health: int
    action: int
    animID: int
    animFrame: int
    flags: int
    particleFlags: int
    invicTimer: int

    _fields_ = [
        ('posX', ct.c_float), ('posY', ct.c_float), ('posZ', ct.c_float),
        ('velX', ct.c_float), ('velY', ct.c_float), ('velZ', ct.c_float),
        ('faceAngle', ct.c_float),
        ('forwardVelocity', ct.c_float),
        ('health', ct.c_int16),
        ('action', ct.c_uint32),
        ('animID', ct.c_int32),
        ('animFrame', ct.c_int16),
        ('flags', ct.c_uint32),
        ('particleFlags', ct.c_uint32),
        ('invicTimer', ct.c_int16),        
    ]

class SM64MarioGeometryBuffers(ct.Structure):
    position: "ct._Pointer[float]"
    normal: "ct._Pointer[float]"
    color: "ct._Pointer[float]"
    uv: "ct._Pointer[float]"
    numTrianglesUsed: int

    _fields_ = [
        ('position', ct.POINTER(ct.c_float)),
        ('normal', ct.POINTER(ct.c_float)),
        ('color', ct.POINTER(ct.c_float)),
        ('uv', ct.POINTER(ct.c_float)),
        ('numTrianglesUsed', ct.c_uint16)
    ]

    def __init__(self):
        self.position_data = (ct.c_float * (mesh_helpers.SM64_GEO_MAX_TRIANGLES * 3 * 3))()
        self.position = ct.cast(self.position_data , ct.POINTER(ct.c_float))
        self.normal_data = (ct.c_float * (mesh_helpers.SM64_GEO_MAX_TRIANGLES * 3 * 3))()
        self.normal = ct.cast(self.normal_data , ct.POINTER(ct.c_float))
        self.color_data = (ct.c_float * (mesh_helpers.SM64_GEO_MAX_TRIANGLES * 3 * 3))()
        self.color = ct.cast(self.color_data , ct.POINTER(ct.c_float))
        self.uv_data = (ct.c_float * (mesh_helpers.SM64_GEO_MAX_TRIANGLES * 3 * 2))()
        self.uv = ct.cast(self.uv_data , ct.POINTER(ct.c_float))
        self.numTrianglesUsed = 0

    def __del__(self):
        pass
