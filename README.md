# Config Sync

> One-line server provisioning. Define your config files, run one command, done.

A unified sequence-based tool for syncing configuration files to a new server. Supports three action types: **copy** files with pre/post hooks, **append** content to existing files, and **execute** arbitrary shell scripts. Every step is interactive — you see what's being replaced before it happens.

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/xiyuanyang-code/ConfigSync.git && cd ConfigSync

# 2. Activate environment and install dependencies
source .venv/bin/activate
uv sync

# 3. Preview what will happen (read-only, no changes)
config-sync --dry-run

# 4. Run the full sequence
config-sync
```

## How It Works

The core idea is simple: define an ordered `sequence` of steps in `config/config.yaml`, then run `config-sync`. Each step is one of three types:

| Action | What it does | Extra fields |
|--------|-------------|--------------|
| `copy` | Copy src -> dst (file or directory) | `pre_install`, `post_check` |
| `append` | Append src file content to dst file | - |
| `exe_bash` | Run a shell command | `command` |

For `copy` actions targeting directories, files are **overlaid** — only files present in `src` are replaced in `dst`. Existing files in `dst` that aren't in `src` are preserved. Before each overwrite, you see the **current destination file content** and decide whether to proceed.

All bash commands (`pre_install`, `post_check`, `exe_bash`) stream their stdout/stderr in real-time. If a `pre_install` fails, you can choose to skip that step.

## Project Structure

```
public/
├── config/
│   └── config.yaml              # The sequence definition (edit this)
├── backup/                      # Source config files to sync
│   ├── .codex/                  #   codex auth + config
│   ├── .claude/                 #   claude settings
│   ├── .claude-code-router/     #   router config
│   └── .ssh/                    #   ssh keys + config
├── scripts/                     # Standalone bash scripts
│   └── ssh_postcheck.sh
├── src/config_sync/             # Core Python package
│   ├── cli.py                   #   CLI argument parsing
│   ├── sync.py                  #   Execution engine
│   └── utils.py                 #   Display, prompts, command runner
├── pyproject.toml               # Package metadata
├── main.py                      # Legacy entry point
└── scripts.py                   # Legacy entry point
```

## Configuration

Edit `config/config.yaml`. Here's the full schema:

```yaml
# Base directory for all relative paths and cwd for bash commands.
# "." means the directory where you run config-sync.
work_dir: .

sequence:
  # ── copy: install tool + sync config files ──
  - action: copy
    name: codex
    src: ./backup/.codex                   # relative to work_dir
    dst: ~/.codex                          # supports ~ expansion
    pre_install: "which codex || npm install -g @openai/codex"
    post_check: "codex --version"

  - action: copy
    name: claude
    src: ./backup/.claude
    dst: ~/.claude
    pre_install: "npm install -g @anthropic-ai/claude-code"

  - action: copy
    name: ssh_config
    src: ./backup/.ssh
    dst: ~/.ssh
    post_check: "bash scripts/ssh_postcheck.sh"

  # ── append: add lines to an existing file ──
  - action: append
    name: bashrc-extra
    src: ./backup/.bashrc_extra
    dst: ~/.bashrc

  # ── exe_bash: run arbitrary commands ──
  - action: exe_bash
    name: ssh_check
    command: "bash scripts/ssh_postcheck.sh"
```

### Action: `copy`

Copies files or directories from `src` to `dst`. For directories, performs an **overlay merge** — only files in `src` are touched; other files in `dst` are left alone.

| Field | Required | Description |
|-------|----------|-------------|
| `src` | yes | Source path (relative to `work_dir`) |
| `dst` | yes | Destination path (supports `~`) |
| `pre_install` | no | Shell command to run **before** copying |
| `post_check` | no | Shell command to run **after** copying |

**Lifecycle:** `pre_install` -> show existing dst content -> user confirms -> copy -> `post_check`

### Action: `append`

Appends the full content of `src` file to `dst` file. Creates `dst` if it doesn't exist.

| Field | Required | Description |
|-------|----------|-------------|
| `src` | yes | Source file path |
| `dst` | yes | Target file to append to |

### Action: `exe_bash`

Runs a shell command with `work_dir` as the working directory.

| Field | Required | Description |
|-------|----------|-------------|
| `command` | yes | The shell command to execute |
| `pre_install` | no | Shell command to run before the main command |

## CLI Reference

```
config-sync [OPTIONS]

Options:
  -h, --help            Show help message and exit
  --version             Show version number
  -c, --config CONFIG   Path to config.yaml (default: config/config.yaml)
  -o, --only NAMES      Only run steps with these names
  -n, --dry-run         Preview changes without writing
  -f, --force           Skip all confirmation prompts
  -l, --list            List all sequence steps as a table
```

### Examples

```bash
# List all steps
config-sync --list

# Preview only (no side effects)
config-sync --dry-run

# Run only the codex and claude steps
config-sync --only codex claude

# Skip all confirmation prompts (dangerous!)
config-sync --force

# Use a different config file
config-sync -c /path/to/custom-config.yaml
```

### Alternative Entry Points

```bash
python main.py --dry-run
python -m config_sync --dry-run
```

## Adding Your Own Steps

1. Place your config files in `backup/`
2. Add a new entry to the `sequence` in `config/config.yaml`
3. (Optional) Add scripts to `scripts/` for `exe_bash` steps
4. Run `config-sync --dry-run` to preview, then `config-sync` to apply
