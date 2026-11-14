# 🏦 Banker's Algorithm Visualizer

A modern, dark-themed Python desktop application for step-by-step visualization of the **Banker's Algorithm** (Deadlock Avoidance) — built for OS Lab demonstrations and viva presentations.

## Quick Start

```bash
cd d:\OS_lab\bankers_algorithm
python app.py
```

> **Zero dependencies** — runs on Python's built-in `tkinter`. No `pip install` needed.

## Features

### Core
- **Dynamic dimensions** — set any number of processes (1–15) and resource types (1–8)
- **Custom names** — name your processes ("Game Engine", "Chrome") and resources ("CPU Cores", "RAM (GB)") instead of generic P0/A/B/C
- **Auto Need matrix** — Need = Max − Allocation, recalculated in real-time as you type
- **Auto Available vector** — Available = Total − Σ Allocation

### Visualization
- **Step-by-step stepper** with ⏮ Reset, ◀ Prev, ▶ Play/Pause, Next ▶, ⏩ Jump-to-End
- **Animated process cards** — color-coded: ⚪ Waiting, 🟡 Testing, 🟢 Executed, 🔴 Blocked
- **Safe sequence badges** — builds dynamically as processes complete
- **Plain-English explanation log** — every decision narrated with mathematical reasoning
- **Speed slider** — control animation speed (0.1s to 2.0s per step)

### Advanced
- **🔍 Resource-Request Simulator** — test if a specific process request would be granted or denied
- **🌳 All Safe Sequences** — DFS backtracking finds every valid execution order (up to 500)
- **📋 Export Summary** — one-click export to clipboard + `lab_summary.txt` for lab records

### 5 Real-World Presets
| Preset | State | Description |
|--------|-------|-------------|
| 🎮 Gaming Session | SAFE | Game Engine, Physics, Audio, Assets, Network competing for CPU/RAM/GPU/Disk |
| 🌐 Web Server | SAFE | Request Handler, Auth, DB, Cache, Logger with Threads/DB Connections/Memory |
| ☠️ Deadlock! (Video Edit) | UNSAFE | Timeline Renderer, Encoder, Preview, Audio with zero available resources |
| 📚 Classic Textbook | SAFE | Standard Silberschatz/Galvin example (P0–P4, A/B/C) |
| 🔀 Multiple Sequences | SAFE | Demonstrates 24 different valid safe orderings |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `→` | Step Forward |
| `←` | Step Backward |
| `R` | Reset Stepper |

## File Structure

```
bankers_algorithm/
├── app.py              # GUI application (run this)
├── banker_engine.py    # Core algorithm logic
└── README.md           # This file
```

## Theory Reference

The Banker's Algorithm is a **deadlock avoidance** algorithm that tests for safety by simulating the allocation of predetermined maximum possible amounts of all resources, then checks if a safe execution sequence exists.

**Safety Algorithm:**
1. Let `Work = Available` and `Finish[i] = false` for all processes
2. Find a process `i` where `Finish[i] == false` and `Need[i] ≤ Work`
3. If found: `Work = Work + Allocation[i]`, `Finish[i] = true`, go to step 2
4. If all `Finish[i] == true` → **SAFE**; otherwise → **UNSAFE**

