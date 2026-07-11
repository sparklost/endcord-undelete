import glob
import os
import shutil
import subprocess
import sys

PACKAGES = ["apsw==3.53.3.1", "psycopg==3.3.4"]
TERMUX_PACKAGES = ["apsw"]


def install_packages_termux(packages):
    """Install specified packages in extension dir, for termux"""
    for package in packages:
        if not shutil.which(package):
            subprocess.run(["pkg", "i", f"python-{package}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        current_dir = os.getcwd()
        system_dir = glob.glob(os.path.expandvars("$PREFIX/lib/python*/site-packages"))[0]
        shutil.copytree(os.path.join(system_dir, package), os.path.join(current_dir, package))


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
    if sys.platform =="android" and shutil.which("termux-backup"):
        install_packages_termux(TERMUX_PACKAGES)
        install_packages([x for x in PACKAGES if not any(x.startswith(y) for y in TERMUX_PACKAGES)])
        return
    install_packages(PACKAGES)


if __name__ == "__main__":
    main()
