# Fellow Setup Guide

This guide gets you up and running with OpenCode for the model-blind evaluation. The recommended approach uses Docker so you don't need to install any dependencies on your machine.

## Prerequisites

- **Docker Desktop** installed and running ([download here](https://www.docker.com/products/docker-desktop/))
- A **virtual key** (`sk-...`) provided by the operator
- One of: **macOS**, **Linux**, or **Windows 10/11**

> **Windows users:** Use **Git Bash** (included with [Git for Windows](https://gitforwindows.org/)) for all commands in this guide. CMD and PowerShell are not supported.

## Quick Start

### 1. Pull the Docker image

You only need to do this once:

```bash
docker pull mohammedmhs/opencode-fellow
```

### 2. Add your API key

Open `scripts/.env` and replace `sk-paste-your-key-here` with the key you were given:

```
LITELLM_API_KEY=sk-your-actual-key
```

This is the **only file you need to edit**. When you receive a new key for a new task, update it here.

### 3. Start a task

Open your terminal, `cd` into the project you want to work on, and run:

```bash
./scripts/start.sh
```

> **Windows / permission error?** Run `bash scripts/start.sh` instead.

OpenCode can read and write files in whatever directory you `cd` into. The first time you run it, you'll see a one-time database migration message — this is normal.

If everything is set up correctly, you should see a TUI that looks like this:

![OpenCode TUI](opencode%20picture.png)

### 4. Work in your IDE alongside OpenCode

Files created or modified by OpenCode appear in your working directory in real time:

1. Open the same directory in your IDE (VS Code, Cursor, etc.)
2. You'll see all files that OpenCode creates or modifies as they happen
3. Use your IDE normally to browse, search, and review code

### 5. Export sessions when done

After finishing a task, exit OpenCode (`/quit` or Ctrl+C), then run:

```bash
./scripts/export.sh
```

> **Windows / permission error?** Run `bash scripts/export.sh` instead.

You'll see a numbered list of your sessions. Enter the ones you want to export (e.g. `1, 3`) or type `all`. The exported JSON files are saved to the `trajectories/` folder.

## Switching Models

You have access to three model aliases. You will **not** know which real model is behind each one.

| Alias     | Display Name in OpenCode |
| --------- | ------------------------ |
| `model_A` | Model A (default)        |
| `model_B` | Model B                  |
| `model_C` | Model C                  |

Use `/models` within the OpenCode TUI to switch between them.

## Exiting and Restarting

- To exit OpenCode, type `/quit` or press Ctrl+C
- To start a new session, run `./scripts/start.sh` again
- Each run starts a fresh container, but your working directory files and session history persist

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `permission denied: ./scripts/start.sh` | Run `bash scripts/start.sh` instead |
| `Error: Update your API key` | Edit `scripts/.env` with your actual key |
| `command not found: docker` | Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and make sure it's running |
| 401 error when using OpenCode | Your key is invalid or expired — contact the operator for a new one |

## Rules

- **Do not** attempt to identify which real model is behind each alias.
- **Do not** share your key with other fellows.
- You will receive a **new key** for each task.
