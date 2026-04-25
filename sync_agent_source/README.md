# SyncAgent Documentation
## Background
Designed for professional synchronization of segmented ODF files and standard directories.

## Testing
Run tests using: `pytest tests/`

## Usage
- `sync-agent mirror <src> <tgt> --exclude venv`
- `sync-agent content <src.odt> <tgt.odt> --threshold 0.95 --dry-run`
