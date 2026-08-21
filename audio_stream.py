import threading
import ctypes as ct
from enum import IntEnum

SAMPLE_RATE = 32000
CHANNELS = 2
BITS_PER_SAMPLE = 16

SAMPLES_HIGH = 544
MAX_TOTAL_SAMPLES = SAMPLES_HIGH * 2 * 2
MAX_BYTE_SIZE = MAX_TOTAL_SAMPLES * 2

WAVE_FORMAT_PCM =1

POOL_SIZE = 4

class WaveHdrFlags(IntEnum):
    WHDR_DONE = 1,
    WHDR_PREPARED = 2,
    WHDR_BEGINLOOP = 4,
    WHDR_ENDLOOP = 8,
    WHDR_INQUEUE = 16

class WAVEFORMATEX(ct.Structure):
    _fields_ = [("wFormatTag", ct.c_ushort), ("nChannels", ct.c_ushort),
                ("nSamplesPerSec", ct.c_uint), ("nAvgBytesPerSec", ct.c_uint),
                ("nBlockAlign", ct.c_ushort), ("wBitsPerSample", ct.c_ushort), ("cbSize", ct.c_ushort)]

class WAVEHDR(ct.Structure):
    pass
WAVEHDR._fields_ = [("lpData", ct.c_void_p), ("dwBufferLength", ct.c_uint),
                    ("dwBytesRecorded", ct.c_uint), ("dwUser", ct.c_void_p),
                    ("dwFlags", ct.c_uint), ("dwLoops", ct.c_uint),
                    ("lpNext", ct.POINTER(WAVEHDR)), ("reserved", ct.c_void_p)]

class AudioStreamState:
    def __init__(self):
        self.shutdown_event = threading.Event()
        self.thread_running = False
        self.hWaveOut = ct.c_void_p()
        self.raw_byte_pools = [ct.create_string_buffer(MAX_BYTE_SIZE) for _ in range(POOL_SIZE)]
        self.headers = [WAVEHDR() for _ in range(POOL_SIZE)]
        self.playback_thread = None

sm64 = None
winmm = ct.windll.winmm
_audio = None

def tick_audio(audio):
    """Runs on a background thread. Technically doesn't tick at the usual rate, but"""
    """shouldn't really matter since it's just checking the buffer for new audio to stream."""
    global sm64

    buf_idx = 0

    pre_cast_buffers = [ ct.cast(pool, ct.POINTER(ct.c_int16)) for pool in audio.raw_byte_pools ]
    
    while audio.thread_running and not audio.shutdown_event.is_set():
        current_hdr = audio.headers[buf_idx]

        if (current_hdr.dwFlags & WaveHdrFlags.WHDR_INQUEUE):
            audio.shutdown_event.wait(timeout=0.002)
            continue

        if current_hdr.dwFlags & WaveHdrFlags.WHDR_DONE:
            winmm.waveOutUnprepareHeader(audio.hWaveOut, ct.byref(current_hdr), ct.sizeof(WAVEHDR))

        if audio.shutdown_event.is_set() or not audio.thread_running:
            break
            
        buffer_ptr = pre_cast_buffers[buf_idx]
        samples_per_pass = sm64.sm64_audio_tick(1024, 2048, buffer_ptr)

        if samples_per_pass > 0:
            total_elements = samples_per_pass * 4 
            total_bytes = total_elements * 2
            
            for i in range(total_elements):
                buffer_ptr[i] = buffer_ptr[i] >> 1
            
            current_hdr.lpData = ct.cast(buffer_ptr, ct.c_void_p)
            current_hdr.dwBufferLength = total_bytes
            current_hdr.dwFlags = 0

            winmm.waveOutPrepareHeader(audio.hWaveOut, ct.byref(current_hdr), ct.sizeof(WAVEHDR))
            winmm.waveOutWrite(audio.hWaveOut, ct.byref(current_hdr), ct.sizeof(WAVEHDR))
            
            buf_idx = (buf_idx + 1) % POOL_SIZE
        else:
            audio.shutdown_event.wait(timeout=0.002)

def start_audio_stream(sm64_lib):
    global _audio, sm64
    
    if _audio and _audio.thread_running:
        return

    _audio = AudioStreamState()
    _audio.shutdown_event.clear()

    sm64 = sm64_lib
        
    print("Launching audio thread...")
    wfx = WAVEFORMATEX(WAVE_FORMAT_PCM, CHANNELS, SAMPLE_RATE, SAMPLE_RATE * 4, 4, BITS_PER_SAMPLE, 0)
    if winmm.waveOutOpen(ct.byref(_audio.hWaveOut), -1, ct.byref(wfx), 0, 0, 0) != 0:
        print("Failed to map waveOut audio driver channels.")
        return

    _audio.thread_running = True
    _audio.playback_thread = threading.Thread(
        target=tick_audio,
        args=(_audio,),
        daemon=True)
    _audio.playback_thread.start()

    print("Audio thread is now running.")

def stop_audio_stream():
    global _audio, sm64
    
    print("Stopping audio thread...")
    _audio.thread_running = False
    _audio.shutdown_event.set()

    if _audio.hWaveOut:
        winmm.waveOutReset(_audio.hWaveOut)
    
    if _audio.playback_thread and _audio.playback_thread.is_alive():
        _audio.playback_thread.join(timeout=0.5)

    if _audio.hWaveOut:
        for hdr in _audio.headers:
            if hdr.dwFlags & WaveHdrFlags.WHDR_INQUEUE:
                winmm.waveOutUnprepareHeader(_audio.hWaveOut, ct.byref(hdr), ct.sizeof(WAVEHDR))
        winmm.waveOutClose(_audio.hWaveOut)


    sm64 = None
    _audio = None
        
    print("Audio thread is now stopped.")
