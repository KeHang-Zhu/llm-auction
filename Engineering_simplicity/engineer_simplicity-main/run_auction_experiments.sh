#!/bin/bash
# Batch runner for Auction experiments
# Usage: ./run_auction_experiments.sh <model> [config_names...]
#
# Examples:
#   ./run_auction_experiments.sh claude all                    # Run all claude configs
#   ./run_auction_experiments.sh gpt4o axis1_contingent_baseline  # Run specific config
#   ./run_auction_experiments.sh gemini loss_aversion_*        # Run pattern matching

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# If no arguments, show usage
if [ $# -lt 1 ]; then
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}  Auction Experiment Batch Runner${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""
    echo "Usage: ./run_auction_experiments.sh <model> [config_names...]"
    echo ""
    echo "Models: claude, gpt4o, gemini, gemma"
    echo ""
    echo "Examples:"
    echo "  ./run_auction_experiments.sh claude all                       # Run all claude configs"
    echo "  ./run_auction_experiments.sh gpt4o axis1_contingent_baseline  # Run specific config"
    echo "  ./run_auction_experiments.sh gemini axis1_*                   # Run pattern matching"
    echo "  ./run_auction_experiments.sh gemma loss_aversion_baseline risk_averse  # Multiple configs"
    echo ""
    echo "Available models and configurations:"
    for model_dir in configs_auction/interventions_*; do
        model=$(basename "$model_dir" | sed 's/interventions_//')
        count=$(ls "$model_dir"/*.yaml 2>/dev/null | wc -l | tr -d ' ')
        echo -e "  ${GREEN}$model${NC}: $count configs"
    done
    echo ""
    echo "Config names (without .yaml extension):"
    ls configs_auction/interventions_claude/*.yaml 2>/dev/null | xargs -n 1 basename | sed 's/.yaml$//' | sed 's/^/  - /'
    exit 1
fi

MODEL=$1
shift

CONFIG_DIR="configs_auction/interventions_${MODEL}"

# Check if model directory exists
if [ ! -d "$CONFIG_DIR" ]; then
    echo -e "${RED}Error: Model directory not found: $CONFIG_DIR${NC}"
    echo "Available models:"
    for d in configs_auction/interventions_*; do
        echo "  - $(basename "$d" | sed 's/interventions_//')"
    done
    exit 1
fi

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  Auction Experiment Batch Runner${NC}"
echo -e "${BLUE}  Model: ${YELLOW}$MODEL${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Check if running all configs
if [ $# -eq 0 ] || [ "$1" = "all" ]; then
    echo -e "${GREEN}Running ALL configurations for ${MODEL}...${NC}"
    echo ""
    python3 src/run_auction_batch.py "$CONFIG_DIR"/*.yaml
else
    # Build config paths
    CONFIG_PATHS=""
    for name in "$@"; do
        # Handle wildcard patterns
        if [[ "$name" == *"*"* ]]; then
            # Pattern matching
            pattern="${CONFIG_DIR}/${name}.yaml"
            matched_files=$(ls $pattern 2>/dev/null)
            if [ -n "$matched_files" ]; then
                for f in $matched_files; do
                    CONFIG_PATHS="$CONFIG_PATHS $f"
                    echo -e "${GREEN}+${NC} Found: $f"
                done
            else
                echo -e "${RED}x${NC} No match: $pattern"
            fi
        else
            # Add .yaml extension if not present
            if [[ ! $name == *.yaml ]]; then
                name="${name}.yaml"
            fi
            config_path="${CONFIG_DIR}/$name"

            if [ -f "$config_path" ]; then
                CONFIG_PATHS="$CONFIG_PATHS $config_path"
                echo -e "${GREEN}+${NC} Found: $config_path"
            else
                echo -e "${RED}x${NC} Not found: $config_path"
            fi
        fi
    done

    if [ -n "$CONFIG_PATHS" ]; then
        echo ""
        echo -e "${BLUE}Starting experiments...${NC}"
        python3 src/run_auction_batch.py $CONFIG_PATHS
    else
        echo ""
        echo -e "${RED}No valid configurations found.${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  Batch Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
