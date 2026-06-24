@echo off
REM 示例：在 build\Release 下运行（请先 build_windows.bat 编译）
REM 根据你的问题规模修改 -n 进程数
setlocal
cd /d "%~dp0"
if not exist "build\Release\MACPO2_LLSO.exe" (
  echo Build first: set EIGEN3_ROOT=... ^&^& build_windows.bat
  exit /b 1
)
cd build\Release
mpiexec -n 20 MACPO2_LLSO.exe F1 ex01 Full ..\..\output\
mpiexec -n 20 MACPO2_CSO.exe  F1 ex01 Full ..\..\output\
echo Done. Check ..\..\output\
endlocal
