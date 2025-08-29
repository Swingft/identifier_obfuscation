


# Identifier Obfuscation

This project provides tools for generating obfuscation mappings for Swift project identifiers.

## Main Script

- **service_mapping.py**  
  Generates a mapping from target identifiers to obfuscated replacements, ensuring:
  - No collisions with existing project identifiers.
  - No duplicate replacements across different kinds.

## Usage

```bash
python3 service_mapping.py \
  --targets targets.json \
  --exclude project_identifiers.json \
  --output mapping_result.json
```

- `targets.json`: identifiers you want to obfuscate.
- `project_identifiers.json`: full list of project identifiers (from `id.py`) used as a whitelist to prevent collisions.

## Notes
- `id.py` can scan an entire Swift project and output identifiers as JSON, but it's mainly a helper for preparing the exclude list. You usually won’t need to run it directly.