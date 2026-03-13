@echo off
chcp 65001 >nul
echo ============================================================
echo EFT 规则范围编辑器
echo ============================================================
echo.

if exist ".venv\Scripts\python.exe" (
	".venv\Scripts\python.exe" rule_range_editor.py
) else (
	python rule_range_editor.py
)

echo.
echo ============================================================
echo 按任意键退出...
pause >nul