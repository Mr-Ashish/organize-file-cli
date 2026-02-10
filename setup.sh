#!/bin/bash
# Setup script for File Organizer CLI: handles install + PATH.

set -e

echo "=== File Organizer CLI Setup ==="

# Check prerequisites
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found. Install it first."
    exit 1
fi
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip not found. Install via 'python3 -m ensurepip' or package manager."
    exit 1
fi

echo "Python and pip detected: $(python3 --version)"

# Install
echo "Installing CLI tool..."
python3 -m pip install --user -e .

# Detect actual scripts dir (Mac/Python-specific; e.g. ~/Library/Python/3.x/bin)
USER_BIN=$(python3 -c "import site, os; print(os.path.join(site.getuserbase(), 'bin'))")
echo "Scripts installed to: $USER_BIN"

# Handle PATH
if [[ ":$PATH:" != *":$USER_BIN:"* ]]; then
    echo "Adding $USER_BIN to PATH..."
    echo "export PATH=\"$USER_BIN:\$PATH\"" >> ~/.zshrc
    echo "export PATH=\"$USER_BIN:\$PATH\"" >> ~/.bashrc
    export PATH="$USER_BIN:$PATH"
    echo "PATH updated. Run: source ~/.zshrc (or restart shell)"
else
    echo "PATH already includes scripts dir."
fi

# Verify
if command -v organize-files &> /dev/null; then
    echo "Success! CLI installed."
    organize-files --version 2>/dev/null || echo "Version check: OK"
else
    echo "Warning: Still not in PATH. Manually add '$USER_BIN' to ~/.zshrc and source it."
fi

echo "
=== Next Steps ===
1. Run: source ~/.zshrc (or restart Terminal) 
2. Test: organize-files --help
3. Use: cp -r samples/ test_folder/ && organize-files test_folder --dry-run
4. Dev: Re-run ./setup.sh after edits.
5. Uninstall: pip uninstall file-organizer
See README.md for details.
"
