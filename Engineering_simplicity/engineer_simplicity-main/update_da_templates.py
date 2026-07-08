#!/usr/bin/env python3
"""
Batch update DA templates: Replace value specifications with preference order.

This script updates all DA template files to use ordinal preferences
(e.g., "x > y > w > z") instead of cardinal utilities (e.g., "x=$82, y=$75").
"""

import os
import re

# Templates directory
templates_dir = "rule_template/DA/"

# Pattern to match value specifications
old_pattern = r"Your values for each school:\s+w = \$\{\{vw\}\}, x = \$\{\{vx\}\}, y = \$\{\{vy\}\}, z = \$\{\{vz\}\}"

# Replacement text
new_text = """Your preference ordering (most preferred to least preferred):
  {{preference_order}}"""

def update_template(filepath):
    """Update a single template file."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Check if old pattern exists
        if re.search(old_pattern, content):
            # Replace
            new_content = re.sub(old_pattern, new_text, content)

            # Write back
            with open(filepath, 'w') as f:
                f.write(new_content)

            print(f"✓ Updated: {filepath}")
            return True
        else:
            print(f"  Skipped: {filepath} (already updated or different format)")
            return False

    except Exception as e:
        print(f"✗ Error updating {filepath}: {e}")
        return False

def main():
    """Update all DA template files."""
    print("=" * 70)
    print("DA Template Updater: Values → Preference Order")
    print("=" * 70)

    updated_count = 0
    skipped_count = 0

    # Get all .txt files in templates_dir
    for filename in sorted(os.listdir(templates_dir)):
        if filename.endswith('.txt'):
            filepath = os.path.join(templates_dir, filename)
            if update_template(filepath):
                updated_count += 1
            else:
                skipped_count += 1

    print("\n" + "=" * 70)
    print(f"Summary: {updated_count} files updated, {skipped_count} files skipped")
    print("=" * 70)

if __name__ == "__main__":
    main()
