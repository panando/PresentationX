# PresentationX - Video Mark Player

> 中文文档：[README.zh-CN.md](README.zh-CN.md)

A desktop video mark player built with PyQt6 and OpenCV. Add, edit, import, and export time-based marks on the video timeline — ideal for content analysis, presentation rehearsal, and footage review.

## Features

- **Video Playback** — Load local video files with play, pause, stop, and seek-bar dragging
- **Timeline Marks** — Add marks at any time point, displayed as triangle indicators below the timeline
- **Mark Management** — Edit annotations, modify timestamps, batch delete, select all / invert selection
- **Mark Navigation** — Jump to previous/next mark instantly; auto-pause when a mark is reached
- **Import/Export Marks** — Export marks to `.txt` files, edit manually, and re-import for precise playback control
- **Fullscreen Mode** — Borderless fullscreen playback, perfect for presentations
- **Audio Sync** — Synchronized video and audio playback with adjustable volume
- **Keyboard Shortcuts** — All common operations accessible via keyboard

## UI Layout

```
┌──────────────────────────────┬──────────────┐
│                              │  Mark List    │
│       Video Display          │  ├ 00:00.000  │
│                              │  ├ 00:05.320  │
│                              │  ├ ...        │
├──────────────────────────────┤              │
│ 00:00:00 ──●── 00:10:00 🔊 │ [Export][Import]│
│ 00:00.000 ▲▲▲ 00:05.320 ... │              │
├──────────────────────────────┤              │
│[Load][Play][Mark][Stop][Full]│              │
└──────────────────────────────┴──────────────┘
```

## Requirements

- **Python** 3.9+
- **OS**: Windows / macOS / Linux

### Python Dependencies

| Package | Purpose |
|---------|---------|
| `PyQt6` | GUI framework |
| `opencv-python` | Video decoding and frame processing |

> PyQt6 includes `QtMultimedia` for audio playback — no extra packages needed.

## Installation & Usage

### 1. Clone the repository

```bash
git clone https://github.com/your-username/PresentationX.git
cd PresentationX
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
# or
venv\Scripts\activate      # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run

```bash
python video_player.py
```

## User Guide

### Basic Controls

| Action | How |
|--------|-----|
| Load video | Click "Load" and select a video file |
| Play/Pause | Click "Play" or press **Space** |
| Add mark | Click "Add Mark" or press **M** at the current frame |
| Stop | Click "Stop" to return to the beginning |
| Fullscreen | Click "Fullscreen" or press **F / F11 / \`** |

### Mark Operations

| Action | How |
|--------|-----|
| Jump to mark | Double-click a mark in the mark list |
| Edit annotation | Right-click mark → "Edit Note" |
| Edit timestamp | Right-click mark → "Edit Time", format: `MM:SS.xxx` |
| Delete mark | Select and press **Delete** / **Backspace**, or right-click → "Delete Selected" |
| Select all / Invert | Right-click → "Select" → "All" / "Invert"; or **Ctrl+A** |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **→ / ↓** | Jump to next mark and play |
| **← / ↑** | Jump to the mark before previous and play |
| **Enter / R / Shift** | Jump to previous mark and play |
| **Space** | Play / Pause |
| **M** | Add mark at current frame |
| **Delete / Backspace** | Delete selected marks |
| **F / F11 / \`** | Toggle fullscreen |
| **Esc** | Exit fullscreen |

### Mark File Format

Exported `.txt` files contain one mark per line:

```
00:00.000 Start
00:05.320 First section
01:23.450 Key review
```

- Time format: `MM:SS.mmm` (minutes:seconds.milliseconds)
- Time and annotation separated by a space
- Edit manually and re-import for precise playback sequencing

## Project Structure

```
PresentationX/
├── video_player.py    # Main application (UI, video playback, mark logic)
├── styles.py          # UI style definitions (QSS/CSS)
├── requirements.txt   # Python dependencies
├── README.md          # Project documentation (English)
└── README.zh-CN.md    # 中文文档
```

## Use Cases

- **Presentation Rehearsal** — Mark each segment's timing for precise pacing control
- **Footage Review** — Place marks at key frames for easy revisiting
- **Teaching Content Analysis** — Segment and annotate instructional videos
- **Video Editing Reference** — Record edit points for post-production

## License

MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
