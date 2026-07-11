#!/usr/bin/env bash
STDLIB_DIR=$(python3 -c "import sysconfig; print(sysconfig.get_path('stdlib'))")
if [ -z "$STDLIB_DIR" ] || [ ! -d "$STDLIB_DIR" ]; then
    exit 1
fi
cd "$STDLIB_DIR" || exit 1
EXPECTED_NAME=_sysconfigdata__linux_arm-linux-androideabi.py
EXISTING_FILE=$(find . -maxdepth 1 -type f -name "_sysconfigdata*.py" | sed 's|^\./||' | head -n 1)
if [ -z "$EXISTING_FILE" ]; then
    exit 1
fi
if [ "$EXISTING_FILE" = "$EXPECTED_NAME" ]; then
    echo "Already patched"
else
    echo "Creating symlink"
    ln -sf "$EXISTING_FILE" "$EXPECTED_NAME"
    rm -rf __pycache__
fi
