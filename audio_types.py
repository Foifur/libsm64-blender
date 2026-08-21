from enum import IntEnum
import ctypes as ct

def SOUND_ARG_LOAD(bank: ct.c_int8, play_flags: ct.c_int8, sound_id: ct.c_int8, priority: ct.c_int8, flags2: ct.c_int8) -> ct.c_int32:
    return (
        (bank << 28) |
        (play_flags << 24) |
        (sound_id << 16) |
        (priority << 8) |
        (flags2 << 4) |
        1
    )

SOUND_MARIO_HERE_WE_GO = SOUND_ARG_LOAD(2, 4, 0x0C, 0x80, 8)

SOUND_MENU_STAR_SOUND_LETS_A_GO = SOUND_ARG_LOAD(7, 0, 0x24, 0xFF, 8) 

class MusicSeqId(IntEnum):
    SEQ_LEVEL_GRASS                 = 0x03               
    SEQ_LEVEL_INSIDE_CASTLE         = 0x04       
    SEQ_LEVEL_WATER                 = 0x05               
    SEQ_LEVEL_HOT                   = 0x06                
    SEQ_LEVEL_BOSS_KOOPA            = 0x07         
    SEQ_LEVEL_SNOW                  = 0x08                 
    SEQ_LEVEL_SLIDE                 = 0x09               
    SEQ_LEVEL_SPOOKY                = 0x0A       
    SEQ_EVENT_PIRANHA_PLANT         = 0x0B    
    SEQ_LEVEL_UNDERGROUND           = 0x0C   
    SEQ_LEVEL_KOOPA_ROAD            = 0x11         
    SEQ_EVENT_MERRY_GO_ROUND        = 0x13   
    SEQ_EVENT_BOSS                  = 0x16     
    SEQ_EVENT_ENDLESS_STAIRS        = 0x18  
    SEQ_LEVEL_BOSS_KOOPA_FINAL      = 0x19   
    SEQ_EVENT_CUTSCENE_CREDITS      = 0x1A
    SEQ_MENU_FILE_SELECT            = 0x21
    SEQ_RANDOM_MUSIC                = 0xFF

class SeqId(IntEnum):
    SEQ_SOUND_PLAYER                = 0x00
    SEQ_EVENT_CUTSCENE_COLLECT_STAR = 0x01
    SEQ_MENU_TITLE_SCREEN           = 0x02          
    SEQ_LEVEL_GRASS                 = 0x03               
    SEQ_LEVEL_INSIDE_CASTLE         = 0x04       
    SEQ_LEVEL_WATER                 = 0x05               
    SEQ_LEVEL_HOT                   = 0x06                
    SEQ_LEVEL_BOSS_KOOPA            = 0x07         
    SEQ_LEVEL_SNOW                  = 0x08                 
    SEQ_LEVEL_SLIDE                 = 0x09               
    SEQ_LEVEL_SPOOKY                = 0x0A              
    SEQ_EVENT_PIRANHA_PLANT         = 0x0B        
    SEQ_LEVEL_UNDERGROUND           = 0x0C        
    SEQ_MENU_STAR_SELECT            = 0x0D           
    SEQ_EVENT_POWERUP               = 0x0E             
    SEQ_EVENT_METAL_CAP             = 0x0F         
    SEQ_EVENT_KOOPA_MESSAGE         = 0x10        
    SEQ_LEVEL_KOOPA_ROAD            = 0x11           
    SEQ_EVENT_HIGH_SCORE            = 0x12         
    SEQ_EVENT_MERRY_GO_ROUND        = 0x13   
    SEQ_EVENT_RACE                  = 0x14                 
    SEQ_EVENT_CUTSCENE_STAR_SPAWN   = 0x15
    SEQ_EVENT_BOSS                  = 0x16                 
    SEQ_EVENT_CUTSCENE_COLLECT_KEY  = 0x17  
    SEQ_EVENT_ENDLESS_STAIRS        = 0x18        
    SEQ_LEVEL_BOSS_KOOPA_FINAL      = 0x19   
    SEQ_EVENT_CUTSCENE_CREDITS      = 0x1A 
    SEQ_EVENT_SOLVE_PUZZLE          = 0x1B
    SEQ_EVENT_TOAD_MESSAGE          = 0x1C
    SEQ_EVENT_PEACH_MESSAGE         = 0x1D
    SEQ_EVENT_CUTSCENE_INTRO        = 0x1E
    SEQ_EVENT_CUTSCENE_VICTORY      = 0x1F
    SEQ_EVENT_CUTSCENE_ENDING       = 0x20
    SEQ_MENU_FILE_SELECT            = 0x21
    SEQ_EVENT_CUTSCENE_LAKITU       = 0x22
    SEQ_COUNT                       = 0x23
