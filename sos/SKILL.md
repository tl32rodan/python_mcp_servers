---
name: ClioSoft SOS
description: Version control operations for ClioSoft SOS design data management
---

# ClioSoft SOS MCP Server

MCP server exposing commonly-used `soscmd` operations for daily IC design workflows.

## What is ClioSoft SOS?

ClioSoft SOS (Source Object Server) is a **server-based version control system** purpose-built for semiconductor / IC design data. Unlike Git (which is file-based and distributed), SOS is centralized and manages **design objects** — Verilog/VHDL sources, netlists, layout databases, libraries, and other EDA tool artifacts that are often large, binary, or directory-structured.

### Key Concepts

| Concept | Description |
|---------|-------------|
| **SOS Server** | Central server that stores all versioned design data (the "vault"). |
| **Project** | A top-level container on the server that groups related design objects. |
| **RSO (Reference Selected Object)** | A named configuration / snapshot of specific object versions — similar to a tag or baseline. |
| **Workarea** | A local working copy on the designer's machine, analogous to a Git checkout. Files are populated from the server into the workarea. |
| **Check-out / Check-in** | SOS uses a **lock-modify-unlock** model. A designer checks out a file (acquiring a lock), edits it locally, then checks it back in. This prevents merge conflicts on binary design data. |
| **Populate** | Copies files from the server vault into the local workarea so they can be viewed or edited. |
| **Create** | Registers new files or directories into the SOS project so they become version-controlled. |

### Typical Workflow

```
1. Populate workarea     →  soscmd populate <paths>
2. Check out files       →  soscmd co <paths>        (acquires lock)
3. Edit files locally    →  (use EDA tools)
4. Check in files        →  soscmd ci -D <paths>     (releases lock, uploads changes)
5. Update to latest RSO  →  soscmd updatesel          (sync workarea to baseline)
```

### How SOS Differs from Git

- **Centralized**: single source of truth on the SOS server; no local repository.
- **Lock-based**: prevents concurrent edits to the same file — critical for binary EDA formats that cannot be merged.
- **Design-data aware**: handles large binary files, deep directory hierarchies, and EDA library structures natively.
- **No branching/merging in the Git sense**: uses RSOs and project configurations for parallel development.

## Configuration

| Environment Variable | Default  | Description                |
|---------------------|----------|----------------------------|
| `SOS_CMD`           | `soscmd` | Path to the soscmd binary  |
| `SOS_TIMEOUT`       | `120`    | Command timeout in seconds |

## Tools

### Project Management

- **`sos_create(paths)`** — Register new files or directories into the SOS project so they become version-controlled.
- **`sos_populate(paths)`** — Copy files from the server vault into the local workarea.

### Synchronization

- **`sos_update_selected(paths?)`** — Update selected objects in the workarea to match the current RSO (baseline). If no paths given, updates everything.

### Check-out / Check-in

- **`sos_checkout(paths)`** — Check out files, acquiring a lock so no other designer can edit them concurrently.
- **`sos_checkin(paths, log_message?)`** — Check in files with `-D` (delete local writable copy after upload) and an optional log message describing the change.
