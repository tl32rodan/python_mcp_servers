---
name: ClioSoft SOS
description: Version control operations for ClioSoft SOS design data management
---

# ClioSoft SOS MCP Server

MCP server exposing commonly-used `soscmd` operations for daily IC design workflows.

## Configuration

| Environment Variable | Default    | Description                          |
|---------------------|------------|--------------------------------------|
| `SOS_CMD`           | `soscmd`   | Path to the soscmd binary            |
| `SOS_TIMEOUT`       | `120`      | Command timeout in seconds           |

## Tools

### Project Management

- **`sos_create(paths)`** — Add new files or directories to the SOS project
- **`sos_populate(paths)`** — Populate files in the SOS workarea

### Synchronization

- **`sos_update_selected(paths?)`** — Update selected objects to match the current RSO

### Check-out / Check-in

- **`sos_checkout(paths)`** — Check out files with default locking
- **`sos_checkin(paths, log_message?)`** — Check in files with `-D` (delete local copy) and optional log message
