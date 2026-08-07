@echo off
rd /s /q libsm64-blender
mkdir libsm64-blender
robocopy lib libsm64-blender/lib /E
xcopy "*.py" libsm64-blender /Y
tar -caf "libsm64-blender.zip" -C libsm64-blender .
pause