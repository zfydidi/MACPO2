@echo off
REM Build RL-MACPO deployment on Windows (Visual Studio + MS-MPI + Eigen3).
REM Prerequisites:
REM   - CMake 3.10+
REM   - Visual Studio 2019/2022 with C++ workload
REM   - MS-MPI (SDK): https://www.microsoft.com/en-us/download/details.aspx?id=105289
REM   - Eigen3: clone https://gitlab.com/libeigen/eigen and set EIGEN3_ROOT below

setlocal
set "ROOT=%~dp0"
set "BUILD=%ROOT%build"

if not defined EIGEN3_ROOT (
  echo ERROR: Set EIGEN3_ROOT to your Eigen3 source tree ^(folder containing Eigen/^).
  echo Example: set EIGEN3_ROOT=C:\libs\eigen-3.4.0
  exit /b 1
)

cmake -S "%ROOT%" -B "%BUILD%" -G "Visual Studio 17 2022" -A x64 ^
  -DCMAKE_PREFIX_PATH="%EIGEN3_ROOT%" ^
  -DEigen3_DIR="%EIGEN3_ROOT%\cmake" 2>nul

if errorlevel 1 (
  cmake -S "%ROOT%" -B "%BUILD%" -G "Visual Studio 17 2022" -A x64 ^
    -DCMAKE_PREFIX_PATH="%EIGEN3_ROOT%"
)

if errorlevel 1 (
  echo CMake configure failed. Try setting Eigen3_DIR manually, e.g.:
  echo   -DEigen3_DIR=C:\path\to\eigen\cmake
  exit /b 1
)

cmake --build "%BUILD%" --config Release
if errorlevel 1 exit /b 1

echo.
echo Binaries: "%BUILD%\Release\MACPO2_LLSO.exe" and "%BUILD%\Release\MACPO2_CSO.exe"
echo Run from a "MPI-enabled" shell or use mpiexec, e.g.:
echo   mpiexec -n 20 Release\MACPO2_LLSO.exe F1 ex01 Full output\
endlocal
