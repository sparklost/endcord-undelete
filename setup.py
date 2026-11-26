import os
import shutil
import subprocess
import sys

PACKAGES = ["psycopg==3.3.4"]

def install_packages(libraries):
    """Install specified packages in extension dir"""
    subprocess.run(["python", "-m", "venv", "env"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for lib in libraries:
        if lib.startswith("psycopg") and sys.platform =="android" and shutil.which("termux-backup") and shutil.which("clang"):
            lib = lib.replace("psycopg", "psycopg[c]")   # noqa
        subprocess.run(
            ["./env/bin/python", "-m", "pip", "install", "--target=temp", lib],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    current_dir = os.getcwd()
    temp_dir = os.path.join(current_dir, "temp")
    if not os.path.exists(temp_dir):
        return
    for lib in libraries:
        if lib.startswith("psycopg") and sys.platform =="android" and shutil.which("termux-backup") and shutil.which("clang"):
            shutil.move(os.path.join(temp_dir, "psycopg_c"), os.path.join(current_dir, "psycopg_c"))
        lib_name = lib.split("<")[0].split(">")[0].split("=")[0]
        shutil.move(os.path.join(temp_dir, lib_name), os.path.join(current_dir, lib_name))
    shutil.rmtree(temp_dir)
    shutil.rmtree(os.path.join(current_dir, "env"))


def main():
    """Setup environment"""
    install_packages(PACKAGES)


if __name__ == "__main__":
    main()
