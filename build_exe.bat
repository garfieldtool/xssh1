@echo off
chcp 65001 > NUL
echo ========================================================
echo   Windows 打印店书籍封面拼版生成工具 打包脚本
echo ========================================================
echo.

pip install pillow reportlab pyinstaller

echo.
echo 开始打包成独立的 Windows 可执行程序 (.exe)...
python build_exe.py

echo.
pause
