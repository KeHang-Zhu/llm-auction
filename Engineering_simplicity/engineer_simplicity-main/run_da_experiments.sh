#!/bin/bash
# Batch runner for DA experiments
# Usage: ./run_da_experiments.sh [config_names...]

# If no arguments, show usage
if [ $# -eq 0 ]; then
    echo "Usage: ./run_da_experiments.sh [config_name1] [config_name2] ..."
    echo ""
    echo "Examples:"
    echo "  ./run_da_experiments.sh baseline                    # Run baseline only"
    echo "  ./run_da_experiments.sh baseline axis3_secondorder  # Run multiple"
    echo "  ./run_da_experiments.sh all                         # Run all configs"
    echo ""
    echo "Available configurations:"
    ls configs_da/*.yaml | xargs -n 1 basename | sed 's/.yaml$//' | sed 's/^da_/  - /'
    exit 1
fi

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  DA Experiment Batch Runner${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Check if running all configs
if [ "$1" = "all" ]; then
    echo -e "${GREEN}Running ALL configurations...${NC}"
    python3 src/run_da_batch.py configs_da/*.yaml
else
    # Build config paths
    CONFIG_PATHS=""
    for name in "$@"; do
        # Add da_ prefix if not present
        if [[ ! $name == da_* ]]; then
            name="da_$name"
        fi
        # Add .yaml extension if not present
        if [[ ! $name == *.yaml ]]; then
            name="${name}_gpt4o.yaml"
        fi
        config_path="configs_da/$name"

        if [ -f "$config_path" ]; then
            CONFIG_PATHS="$CONFIG_PATHS $config_path"
            echo -e "${GREEN}✓${NC} Found: $config_path"
        else
            echo -e "${RED}✗${NC} Not found: $config_path"
        fi
    done

    if [ -n "$CONFIG_PATHS" ]; then
        echo ""
        echo -e "${BLUE}Starting experiments...${NC}"
        python3 src/run_da_batch.py $CONFIG_PATHS
    else
        echo ""
        echo "No valid configurations found."
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  Batch Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
