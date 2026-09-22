@echo off
chcp 65001 > nul
echo ========================================
echo ЗАПУСК МАЛЮВАННЯ В AUTOCAD
echo ========================================
echo.
echo ІНСТРУКЦІЯ:
echo 1. Зараз КЛІКНИ в AutoCAD Drawing1
echo 2. Дочекайся поки скрипт почне малювати
echo.
pause

"D:\autocad project\autocad-mcp\venv\Scripts\python.exe" "D:\autocad project\draw_simple_NOW.py"
