#!/bin/bash

# Build analog-hub documentation using Sphinx

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Building analog-hub documentation...${NC}"

# Change to docs directory
cd "$(dirname "$0")/../docs"

# Activate virtual environment if it exists
if [ -f "../venv/bin/activate" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source ../venv/bin/activate
fi

# Clean previous build
echo -e "${YELLOW}Cleaning previous build...${NC}"
make clean

# Build HTML documentation
echo -e "${YELLOW}Building HTML documentation...${NC}"
make html

# Check if build was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Documentation built successfully!${NC}"
    echo -e "${GREEN}Open docs/_build/html/index.html to view the documentation.${NC}"
else
    echo -e "${RED}Documentation build failed!${NC}"
    exit 1
fi

# Optional: Open documentation in browser (macOS)
if [ "$1" = "--open" ] && command -v open >/dev/null 2>&1; then
    echo -e "${YELLOW}Opening documentation in browser...${NC}"
    open _build/html/index.html
fi