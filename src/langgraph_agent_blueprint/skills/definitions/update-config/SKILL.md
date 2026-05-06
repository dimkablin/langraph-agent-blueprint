---
name: update-config
description: Safely update assistant configuration.
allowed_tools:
  - read_file
  - write_file
  - edit_file
---
Inspect current configuration, explain the requested change, and update only the relevant setting after permission. Arguments: {{args}}

