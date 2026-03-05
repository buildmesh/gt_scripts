# Gas Town `gt_scripts`

Utility scripts for Gas Town operators.

## Setup

Recommended clone location:

```bash
cd ~/gt
git clone http://github.com/buildmesh/gt_scripts.git scripts
cd ~/gt/scripts
```

Prerequisites:
- `gt` CLI installed and authenticated
- Python 3.10+
- `make`

## `rig_watch.py`

`rig_watch.py` runs continuously (until `CTRL-C`) and every 2 minutes:
- lists rigs with `gt rig list --json`
- for each operational rig:
  - checks `gt rig status <rig>` for any polecats marked `done`; if found, nudges `<rig>/witness` to close stale polecats
  - every 10 minutes, sends an additional witness health-check nudge
  - checks `gt mq list <rig> --json`; if merge queue is non-empty, nudges `<rig>/refinery` to process it

All `gt ...` commands are logged with timestamps.

## Usage

Start the watcher:

```bash
make rig_watch
```

Recommended: run in `tmux` so you can leave it active and return to inspect logs:

```bash
tmux new -s rig-watch
cd ~/gt/scripts
make rig_watch
```

## `economy.py`

`economy.py` runs continuously (until `CTRL-C`) and every 15 seconds:
- Kills the `fm-witness` tmux session (continues silently if it doesn't exist)
- Runs `gt deacon stop`

Use this to reduce resource usage when full rig watching is not needed.

Start economy mode:

```bash
make economy
```

Run tests:

```bash
make test
```
