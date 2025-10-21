# M3U Playlist Exporter

A modern, user-friendly desktop application for exporting music files from M3U/M3U8 playlists as files in seperate folders. Built with Python and tkinter.

![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

<img width="701" height="686" alt="2025-10-15 23_31_39-M3uFileExporter – m3u_exporter py" src="https://github.com/user-attachments/assets/54b1920c-c5d1-4f6f-88e5-237f9ddf6c3c" />

## 🎵 Features

### Playlist Management
- ✅ **Multiple Playlist Support** - Add and manage multiple M3U/M3U8 playlists simultaneously
- ✅ **Drag & Drop** - Easily add playlists by dragging files into the application
- ✅ **Context Menu** - Right-click to remove, clear all, or open playlists

### File Organization
- ✅ **Smart File Copying** - Copy music files to your destination folder
- ✅ **Subfolder Creation** - Optionally create separate folders for each playlist
- ✅ **Flexible Indexing** - Choose between underscore (`0_0_1_Song.mp3`) or zero-padded (`001_Song.mp3`) numbering
- ✅ **Custom Filename Patterns** - Use templates like `{index}_{title}` or `{title}_{index}` to control file naming

### Error Handling
- ✅ **Robust Error Detection** - Identifies missing files, invalid paths, and permission issues
- ✅ **Detailed Logging** - Complete log of all operations for troubleshooting
- ✅ **Graceful Failures** - Continues processing even if individual files fail

## 📋 Requirements

- Python 3.7 or higher
- tkinter with dnd support
- Standard library modules: `os`, `shutil`, `pathlib`, `re`, `logging`

## 🚀 Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/m3u-playlist-exporter.git
cd m3u-playlist-exporter
python m3u_exporter.py
```
2. **Install with pyinstaller:**
```bash
pyinstaller --onefile --noconsole --icon=icon.png --add-data "icon.png;." --name "M3U Copy Tool" m3u_exporter.py
