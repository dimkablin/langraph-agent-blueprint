---
name: debug
description: Diagnose failures systematically before proposing a fix.
allowed_tools:
  - read_file
  - grep
  - glob
  - bash
  - powershell
---
Reproduce the symptom, inspect the smallest relevant code path, identify evidence, and propose the minimal fix. Arguments: {{args}}

