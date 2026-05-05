---
name: verify
description: Run verification commands and report evidence before claiming success.
allowed_tools:
  - bash
  - powershell
  - grep
  - glob
  - read_file
---
Identify the command that proves the claim, run it when approved, read the output, and report evidence. Arguments: {{args}}

