import subprocess

def run_command(command):
    try:
        subprocess.run(command, check=True, shell=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\nError executing command: {e}")
        return False

def main():
    print("Starting compilation process...")

    # Nuitka compilation parameters
    nuitka_params = [
        "python -m nuitka",
        "--standalone",
        "--windows-console-mode=disable",
        "--lto=yes",
        "--follow-imports",
        "--remove-output",
        "--output-dir=dist",
        "--jobs=6",
        "--disable-ccache",
        "--include-data-file=icon.ico=icon.ico",
        "--windows-icon-from-ico=icon.ico",
        "--static-libpython=no",
        "--python-flag=no_docstrings",
        "--python-flag=no_asserts",
        "--enable-plugin=pyside6",
        "--python-flag=no_site",
        "--python-flag=isolated",
        "--prefer-source-code",
        "--nofollow-import-to=tkinter",
        "--nofollow-import-to=PIL",
        "--nofollow-import-to=numpy",
        "--no-deployment-flag=debug"
        "--python-flag=no_warnings",
        "--python-flag=no_randomization"
    ]

    # Include modules
    modules_to_include = [
        "src.core.achievements",
        "src.core.appID_finder",
        "src.core.dlc_gen",
        "src.core.goldberg_gen",
        "src.core.setupEmu",
        "src.core.threadManager",
        "src.gui.GSE_Generator"
    ]

    for module in modules_to_include:
        nuitka_params.append(f"--include-module={module}")

    # Add main script
    nuitka_params.append("main.py")

    # Combine all parameters
    command = " ".join(nuitka_params)

    print("Compiling main GUI...")
    
    if run_command(command):
        print("\nCompilation completed successfully!")
        print("Check the dist folder for the output files.")
    else:
        print("\nAn error occurred during compilation!")

    input("Press Enter to exit...")

if __name__ == "__main__":
    main()