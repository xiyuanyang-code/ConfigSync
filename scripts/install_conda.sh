#!/bin/bash

# Usage: ./install_miniconda.sh /path/to/install

[ -z "$1" ] && echo "Usage: $0 <install_path>" && exit 1

INSTALL_PATH="$1"

# Download and install
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR" || exit 1

ARCH=$(uname -m)
INSTALLER="Miniconda3-latest-Linux-${ARCH}.sh"
wget -q "https://repo.anaconda.com/miniconda/$INSTALLER" || curl -s -O "https://repo.anaconda.com/miniconda/$INSTALLER"

bash "$INSTALLER" -b -p "$INSTALL_PATH"

# Cleanup and finish
cd /tmp && rm -rf "$TEMP_DIR"

echo "Miniconda installed to: $INSTALL_PATH"
echo "Add to PATH: export PATH=\"$INSTALL_PATH/bin:\$PATH\""
"$INSTALL_PATH/bin/conda" --version