@echo off
chcp 65001 > NUL
echo ========================================================
echo   Windows 7 / 10 / 11 打印店书籍封面拼版辅助工具 打包脚本
echo ========================================================
echo.
echo 提示: 如果在 Windows 7 上打包，请使用 Python 3.8.10 32位或64位版本。
echo.

pip install pillow reportlab pyinstaller pypdfium2 pymupdf

echo.
echo 开始打包成独立的 Windows 可执行程序 (.exe)...
python build_exe.py

echo.
pause
