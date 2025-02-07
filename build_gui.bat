@echo off
echo Starting compilation process...
echo.

:: modules
echo Compiling goldberg_gen module...
python -m nuitka --module --lto=yes --disable-ccache --static-libpython=no --python-flag=no_site --python-flag=no_docstrings --python-flag=no_asserts --remove-output --output-dir=dist goldberg_gen.py
if %errorlevel% neq 0 goto error

echo.
echo Compiling achievements module...
python -m nuitka --module --lto=yes --disable-ccache --static-libpython=no --python-flag=no_site --python-flag=no_docstrings --python-flag=no_asserts --remove-output --output-dir=dist achievements.py
if %errorlevel% neq 0 goto error

echo.
echo Compiling appID_finder module...
python -m nuitka --module --lto=yes --disable-ccache --static-libpython=no --python-flag=no_site --python-flag=no_docstrings --python-flag=no_asserts --remove-output --output-dir=dist appID_finder.py
if %errorlevel% neq 0 goto error

echo.
echo Compiling dlc_gen module...
python -m nuitka --module --lto=yes --disable-ccache --static-libpython=no --python-flag=no_site --python-flag=no_docstrings --python-flag=no_asserts --remove-output --output-dir=dist dlc_gen.py
if %errorlevel% neq 0 goto error

:: Main GUI
echo.
echo Compiling main GUI...
python -m nuitka --standalone --onefile --windows-console-mode=disable --windows-icon-from-ico=icon.ico --lto=yes --follow-imports --remove-output --output-dir=dist --jobs=6 --disable-ccache --include-data-file=icon.ico=icon.ico --static-libpython=no --python-flag=no_docstrings --python-flag=no_asserts --enable-plugin=pyside6 --include-module=goldberg_gen --include-module=setupEmu --include-module=threadManager --include-module=achievements --include-module=appID_finder --include-module=dlc_gen GSE_Generator.py
if %errorlevel% neq 0 goto error

echo.
echo Compilation completed successfully!
echo Check the dist folder for the output files.
goto end

:error
echo.
echo An error occurred during compilation!
pause
exit /b 1

:end
pause