import logging
import os
import re
import shutil
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from loguru import logger
import platform
import subprocess
import time
import threading


class M3UExporter:
    def __init__(self, root):
        self.root = root
        self.root.title("M3U Copy Tool")
        self.root.geometry("700x700")
        self.root.resizable(True, True)
        icon_path = self.resource_path('icon.png')
        root.iconphoto(True, tk.PhotoImage(file=icon_path))

        self.m3u_files = []
        self.output_folder = None
        self.rename_pattern = tk.StringVar(value="{index} - {title}")
        self.index_format = tk.StringVar(value="underscore")
        self.create_subfolder = tk.BooleanVar(value=True)
        self.open_outputfolder = tk.BooleanVar(value=True)

        # Time estimation variables
        self.start_time = None
        self.files_processed = 0

        # Abort flag
        self.abort_flag = False

        # Thread for export operation
        self.export_thread = None

        self.setup_ui()
        self.setup_drag_drop()

    def resource_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def setup_ui(self):
        main_frame = tk.Frame(self.root, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_frame = tk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Label(title_frame, text="M3U Copy Tool", font=('Arial', 14, 'bold')).pack(anchor=tk.W)
        tk.Label(title_frame, text="Copy music files from M3U playlists to folders",
                 font=('Arial', 9)).pack(anchor=tk.W)

        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 10))

        source_frame = tk.LabelFrame(main_frame, text="Source Playlist(s)", padx=10, pady=10)
        source_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        list_frame = tk.Frame(source_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.files_listbox = tk.Listbox(list_frame, height=6, selectmode=tk.EXTENDED)
        self.files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_frame, command=self.files_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.files_listbox.config(yscrollcommand=scrollbar.set)

        # Create context menu
        self.context_menu = tk.Menu(self.files_listbox, tearoff=0)
        self.context_menu.add_command(label="Add Playlist(s)...", command=self.select_m3u_files)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Remove Selected", command=self.remove_selected_playlists)
        self.context_menu.add_command(label="Clear All", command=self.clear_all_playlists)

        # Bind right-click to show context menu
        self.files_listbox.bind("<Button-3>", self.show_context_menu)
        # For Mac users (Command+Click or Control+Click)
        self.files_listbox.bind("<Button-2>", self.show_context_menu)

        btn_frame = tk.Frame(source_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        tk.Button(btn_frame, text="Add Playlist(s)...", command=self.select_m3u_files, width=15).pack(side=tk.LEFT,
                                                                                                      padx=(0, 5))
        tk.Button(btn_frame, text="Remove Selected", command=self.remove_selected_playlists, width=15).pack(
            side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_frame, text="Clear All", command=self.clear_all_playlists, width=15).pack(side=tk.LEFT)

        dest_frame = tk.LabelFrame(main_frame, text="Destination Folder", padx=10, pady=10)
        dest_frame.pack(fill=tk.X, pady=(0, 10))

        dest_input_frame = tk.Frame(dest_frame)
        dest_input_frame.pack(fill=tk.X)

        self.output_entry = tk.Entry(dest_input_frame, state='readonly')
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        tk.Button(dest_input_frame, text="Browse...", command=self.select_output_folder, width=12).pack(side=tk.RIGHT)

        options_frame = tk.LabelFrame(main_frame, text="Options", padx=10, pady=10)
        options_frame.pack(fill=tk.X, pady=(0, 10))

        index_frame = tk.Frame(options_frame)
        index_frame.pack(fill=tk.X, pady=(0, 5))
        tk.Label(index_frame, text="Index Format:").pack(side=tk.LEFT)
        tk.Radiobutton(index_frame, text="0_0_0 (underscore)", variable=self.index_format, value="underscore").pack(
            side=tk.LEFT, padx=(10, 5))
        tk.Radiobutton(index_frame, text="000 (zero-padded)", variable=self.index_format, value="padded").pack(
            side=tk.LEFT)

        tk.Checkbutton(options_frame, text="Create subfolder for each playlist",
                       variable=self.create_subfolder).pack(anchor=tk.W)
        tk.Checkbutton(options_frame,
                       text="Open folder after export",
                       variable=self.open_outputfolder).pack(anchor=tk.W, pady=2)

        pattern_frame = tk.Frame(options_frame)
        pattern_frame.pack(fill=tk.X, pady=(5, 0))
        tk.Label(pattern_frame, text="Filename pattern:").pack(side=tk.LEFT)
        pattern_entry = tk.Entry(pattern_frame, textvariable=self.rename_pattern, width=30)
        pattern_entry.pack(side=tk.LEFT, padx=(5, 5))
        tk.Label(pattern_frame, text="({index}, {title}, {ext})", font=('Arial', 8), fg='gray').pack(side=tk.LEFT)

        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        self.status_label = tk.Label(progress_frame, text="Ready", anchor=tk.W)
        self.status_label.pack(fill=tk.X)

        # Time estimation label
        self.time_label = tk.Label(progress_frame, text="", anchor=tk.E, font=('Arial', 8), fg='gray')
        self.time_label.pack(fill=tk.X, pady=(2, 0))

        self.progress = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(5, 0))

        bottom_frame = tk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X)

        self.start_button = tk.Button(bottom_frame, text="Start Copy", command=self.start_export,
                                      bg="#4CAF50", fg="white", font=('Arial', 10, 'bold'),
                                      width=15, height=2, state=tk.DISABLED)
        self.start_button.pack(side=tk.RIGHT, padx=(5, 0))

        # Exit/Abort button - changes function during operation
        self.exit_abort_button = tk.Button(bottom_frame, text="Exit", command=self.root.quit,
                                           width=15, height=2)
        self.exit_abort_button.pack(side=tk.RIGHT)

    def abort_export(self):
        """Set the abort flag to stop the export process"""
        if messagebox.askyesno("Abort Copy",
                               "Are you sure you want to abort the copy process?\n\nFiles copied so far will remain in the destination folder."):
            self.abort_flag = True
            self.status_label.config(text="Aborting...")
            self.time_label.config(text="Abort requested, stopping after current file...")
            self.exit_abort_button.config(state=tk.DISABLED)
            logger.info("User requested abort")

    def set_button_to_abort(self):
        """Change Exit button to Abort button"""
        self.exit_abort_button.config(
            text="Abort",
            command=self.abort_export,
            bg="#f44336",
            fg="white",
            font=('Arial', 10, 'bold')
        )

    def set_button_to_exit(self):
        """Change Abort button back to Exit button"""
        self.exit_abort_button.config(
            text="Exit",
            command=self.root.quit,
            bg="#f0f0f0",
            fg="black",
            font=('TkDefaultFont'),
            state=tk.NORMAL
        )

    def format_time(self, seconds):
        """Format seconds into human-readable time string"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    def update_time_estimation(self, current, total):
        """Update the time estimation label (thread-safe)"""
        if current == 0:
            self.root.after(0, lambda: self.time_label.config(text="Calculating time..."))
            return

        elapsed = time.time() - self.start_time

        # Calculate average time per file
        avg_time_per_file = elapsed / current

        # Estimate remaining time
        remaining_files = total - current
        estimated_remaining = avg_time_per_file * remaining_files

        # Format the display
        elapsed_str = self.format_time(elapsed)
        remaining_str = self.format_time(estimated_remaining)

        percentage = (current / total) * 100

        time_text = f"Progress: {current}/{total} ({percentage:.1f}%) | Elapsed: {elapsed_str} | Remaining: ~{remaining_str}"
        self.root.after(0, lambda: self.time_label.config(text=time_text))

    def setup_drag_drop(self):
        """Setup drag and drop for playlist listbox"""
        self.files_listbox.drop_target_register(DND_FILES)
        self.files_listbox.dnd_bind('<<Drop>>', self.on_drop)
        self.files_listbox.dnd_bind('<<DragEnter>>', self.on_drag_enter)
        self.files_listbox.dnd_bind('<<DragLeave>>', self.on_drag_leave)

        # Enable dragging items out of the listbox
        self.files_listbox.bind('<ButtonPress-1>', self.on_drag_start)
        self.files_listbox.bind('<B1-Motion>', self.on_drag_motion)
        self.files_listbox.bind('<ButtonRelease-1>', self.on_drag_release)

        # Store drag state
        self.drag_data = {'item': None, 'x': 0, 'y': 0, 'dragging': False}

    def on_drag_enter(self, event):
        """Visual feedback when dragging over"""
        self.files_listbox.configure(background='#e3f2fd')
        return event.action

    def on_drag_leave(self, event):
        """Remove visual feedback"""
        self.files_listbox.configure(background='white')
        return event.action

    def on_drop(self, event):
        """Handle dropped files"""
        try:
            # Get the dropped files
            files = self.root.tk.splitlist(event.data)

            added_count = 0
            skipped_count = 0

            for file_path in files:
                # Clean the path (remove curly braces if present on Windows)
                file_path = file_path.strip('{}').strip('"').strip("'")

                # Check if file exists
                if not os.path.exists(file_path):
                    logger.warning(f"File does not exist: {file_path}")
                    skipped_count += 1
                    continue

                # Check if it's an m3u or m3u8 file
                if file_path.lower().endswith(('.m3u', '.m3u8')):
                    # Check if already added
                    if file_path not in self.m3u_files:
                        self.m3u_files.append(file_path)
                        display_name = os.path.basename(file_path)
                        self.files_listbox.insert(tk.END, display_name)
                        added_count += 1
                        logger.info(f"Added playlist via drag & drop: {display_name}")
                    else:
                        logger.info(f"Playlist already added: {file_path}")
                        skipped_count += 1
                else:
                    logger.warning(f"Skipped non-M3U file: {file_path}")
                    skipped_count += 1

            # Update export button state
            self.check_ready_to_export()

            # Show result message if something was skipped
            if added_count > 0:
                msg = f"Added {added_count} playlist(s)"
                if skipped_count > 0:
                    msg += f"\nSkipped {skipped_count} file(s)"
                    messagebox.showinfo("Success", msg)
            elif skipped_count > 0:
                messagebox.showwarning("Warning",
                                       f"No valid M3U/M3U8 files were added.\n"
                                       f"Skipped {skipped_count} file(s).")

        except Exception as e:
            logger.error(f"Error handling dropped files: {str(e)}")
            messagebox.showerror("Error", f"Failed to process dropped files:\n{str(e)}")

    def on_drag_start(self, event):
        """Start dragging an item from the listbox"""
        # Get the item under the cursor
        index = self.files_listbox.nearest(event.y)
        if index >= 0 and index < self.files_listbox.size():
            self.drag_data['item'] = index
            self.drag_data['x'] = event.x
            self.drag_data['y'] = event.y
            self.drag_data['dragging'] = False

    def on_drag_motion(self, event):
        """Track mouse motion during drag"""
        if self.drag_data['item'] is not None:
            # Calculate distance moved
            dx = abs(event.x - self.drag_data['x'])
            dy = abs(event.y - self.drag_data['y'])

            # If moved more than 10 pixels, consider it a drag
            if dx > 10 or dy > 10:
                self.drag_data['dragging'] = True

                # Change cursor to indicate drag-to-delete
                self.files_listbox.config(cursor="X_cursor")

    def on_drag_release(self, event):
        """Handle drag release - delete if dragged outside"""
        if self.drag_data['item'] is not None and self.drag_data['dragging']:
            # Get the widget boundaries
            listbox_widget = self.files_listbox
            widget_x = listbox_widget.winfo_rootx()
            widget_y = listbox_widget.winfo_rooty()
            widget_width = listbox_widget.winfo_width()
            widget_height = listbox_widget.winfo_height()

            # Get absolute mouse position
            abs_x = event.x_root
            abs_y = event.y_root

            # Check if mouse is outside the listbox
            outside = (abs_x < widget_x or
                       abs_x > widget_x + widget_width or
                       abs_y < widget_y or
                       abs_y > widget_y + widget_height)

            if outside:
                # Remove the item
                index = self.drag_data['item']
                playlist_name = self.files_listbox.get(index)

                # Confirm deletion
                if messagebox.askyesno("Remove Playlist",
                                       f"Remove '{playlist_name}' from the list?"):
                    self.files_listbox.delete(index)
                    del self.m3u_files[index]
                    logger.info(f"Removed playlist via drag-out: {playlist_name}")
                    self.check_ready_to_export()

        # Reset cursor and drag data
        self.files_listbox.config(cursor="")
        self.drag_data = {'item': None, 'x': 0, 'y': 0, 'dragging': False}

    def show_context_menu(self, event):
        """Display context menu at cursor position"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def select_m3u_files(self):
        files = filedialog.askopenfilenames(
            title="Select M3U Playlist File(s)",
            filetypes=[("M3U Playlist", "*.m3u"), ("M3U8 Playlist", "*.m3u8"), ("All Files", "*.*")]
        )
        if files:
            for file in files:
                if file not in self.m3u_files:
                    self.m3u_files.append(file)
                    self.files_listbox.insert(tk.END, os.path.basename(file))
            self.check_ready_to_export()

    def remove_selected_playlists(self):
        selected_indices = self.files_listbox.curselection()
        for index in reversed(selected_indices):
            self.files_listbox.delete(index)
            del self.m3u_files[index]
        self.check_ready_to_export()

    def clear_all_playlists(self):
        self.files_listbox.delete(0, tk.END)
        self.m3u_files = []
        self.check_ready_to_export()

    def select_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_entry.config(state='normal')
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, folder)
            self.output_entry.config(state='readonly')
            self.check_ready_to_export()

    def check_ready_to_export(self):
        if self.m3u_files and self.output_folder:
            self.start_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.DISABLED)

    def normalize_path(self, path):
        """Normalize file path and handle special characters"""
        # Strip whitespace and quotes
        path = path.strip().strip('"').strip("'").strip()
        # Normalize path separators
        path = os.path.normpath(path)
        return path

    def find_file_case_insensitive(self, filepath):
        """Try to find file with case-insensitive search if exact match fails"""
        if os.path.exists(filepath):
            return filepath

        # Try the normalized version
        normalized = self.normalize_path(filepath)
        if os.path.exists(normalized):
            return normalized

        # Try case-insensitive search in the directory
        directory = os.path.dirname(normalized)
        filename = os.path.basename(normalized)

        if not os.path.exists(directory):
            return None

        try:
            for file in os.listdir(directory):
                if file.lower() == filename.lower():
                    found_path = os.path.join(directory, file)
                    logger.debug(f"Found file via case-insensitive search: {found_path}")
                    return found_path
        except Exception as e:
            logger.error(f"Error in case-insensitive search: {e}")

        return None

    def parse_m3u(self, m3u_file):
        """Parse M3U file and return list of (title, filepath) tuples"""
        tracks = []
        try:
            with open(m3u_file, 'r', encoding='utf-8-sig', errors='ignore') as f:
                lines = f.readlines()

            current_title = None
            m3u_dir = os.path.dirname(m3u_file)

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith('#EXTINF:'):
                    parts = line.split(',', 1)
                    if len(parts) > 1:
                        current_title = parts[1].strip()
                elif not line.startswith('#'):
                    # Normalize the path from M3U file
                    filepath = self.normalize_path(line)

                    # Handle relative paths
                    if not os.path.isabs(filepath):
                        filepath = os.path.join(m3u_dir, filepath)
                        filepath = os.path.normpath(filepath)

                    # Try to find the file (with case-insensitive fallback)
                    actual_path = self.find_file_case_insensitive(filepath)

                    if actual_path:
                        filepath = actual_path
                    else:
                        logger.warning(f"File not found: {filepath}")

                    if current_title is None:
                        current_title = os.path.splitext(os.path.basename(filepath))[0]

                    tracks.append((current_title, filepath))
                    current_title = None

        except Exception as e:
            logger.error(f"Parse error: {e}")
            # Use root.after for thread-safe messagebox
            self.root.after(0, lambda: messagebox.showerror("Parse Error",
                                                            f"Error parsing {os.path.basename(m3u_file)}:\n{str(e)}"))

        return tracks

    def sanitize_filename(self, filename):
        """Remove invalid characters from filename"""
        # Remove leading/trailing quotes and whitespace
        filename = filename.strip().strip('"').strip("'").strip()
        # Replace problematic characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Replace multiple spaces with single space (but keep underscores)
        filename = re.sub(r'\s+', ' ', filename)
        return filename.strip()

    def format_index(self, index):
        """Format index according to selected format with proper underscore separation"""
        if self.index_format.get() == "underscore":
            # Convert number to string and insert underscores between each digit
            # Example: 11 -> "0_1_1", 99 -> "0_9_9", 123 -> "1_2_3"
            index_str = f"{index:03d}"
            return "_".join(index_str)
        else:
            return f"{index:03d}"

    def verify_exported_files(self, expected_files, playlist_folder):
        """Verify that all expected files were exported"""
        missing_files = []

        for expected_file in expected_files:
            if not os.path.exists(expected_file):
                missing_files.append(os.path.basename(expected_file))

        return missing_files

    def open_output_directory(self):
        """Open the output directory in the system's file explorer"""
        if not self.output_folder or not os.path.exists(self.output_folder):
            logger.warning("Output folder not set or doesn't exist")
            return

        try:
            # Convert to absolute path
            abs_path = os.path.abspath(self.output_folder)
            system = platform.system()

            if system == "Windows":
                # Method 1: Try os.startfile
                try:
                    os.startfile(abs_path)
                except Exception as e:
                    # Method 2: Fallback to explorer command
                    subprocess.run(['explorer', abs_path], check=False)

            elif system == "Darwin":  # macOS
                subprocess.run(["open", abs_path], check=False)
            else:  # Linux and others
                subprocess.run(["xdg-open", abs_path], check=False)

            logger.info(f"Opened output directory: {abs_path}")
        except Exception as e:
            logger.warning(f"Could not open output directory: {e}")
            # Don't show error to user - it's not critical

    def start_export(self):
        """Start the export in a separate thread"""
        if not self.m3u_files:
            messagebox.showwarning("No Files", "Please select at least one M3U file.")
            return

        if not self.output_folder:
            messagebox.showwarning("No Output", "Please select an output folder.")
            return

        # Start export in a separate thread
        self.export_thread = threading.Thread(target=self.export_files, daemon=True)
        self.export_thread.start()

    def export_files(self):
        """Export files - runs in separate thread"""
        # Reset abort flag
        self.abort_flag = False

        # Change Exit button to Abort button and disable Start button (thread-safe)
        self.root.after(0, self.set_button_to_abort)
        self.root.after(0, lambda: self.start_button.config(state=tk.DISABLED))

        total_copied = 0
        total_failed = 0
        all_failed_files = []
        all_expected_files = {}

        # Initialize timing
        self.start_time = time.time()
        self.files_processed = 0

        try:
            total_files = 0
            for m3u_file in self.m3u_files:
                tracks = self.parse_m3u(m3u_file)
                total_files += len(tracks)

            self.root.after(0, lambda: self.progress.config(maximum=total_files, value=0))
            self.root.after(0, lambda: self.status_label.config(text="Copying files..."))
            self.root.after(0, lambda: self.time_label.config(text="Starting..."))

            for m3u_file in self.m3u_files:
                if self.abort_flag:
                    break

                tracks = self.parse_m3u(m3u_file)
                failed_files = []
                expected_files = []

                if self.create_subfolder.get():
                    playlist_name = os.path.splitext(os.path.basename(m3u_file))[0]
                    playlist_name = self.sanitize_filename(playlist_name)
                    playlist_folder = os.path.join(self.output_folder, playlist_name)
                    if not os.path.exists(playlist_folder):
                        os.makedirs(playlist_folder)
                else:
                    playlist_folder = self.output_folder

                for idx, (title, source_file) in enumerate(tracks, start=1):
                    # Check abort flag
                    if self.abort_flag:
                        logger.info("Export aborted by user")
                        break

                    if not os.path.exists(source_file):
                        failed_files.append(f"{title} (File not found)")
                        total_failed += 1
                        logger.warning(f"File not found: {source_file}")
                        self.files_processed += 1
                        self.root.after(0, lambda v=self.files_processed: self.progress.config(value=v))
                        self.update_time_estimation(self.files_processed, total_files)
                        continue

                    _, ext = os.path.splitext(source_file)

                    sanitized_title = self.sanitize_filename(title)
                    formatted_idx = self.format_index(idx)

                    pattern = self.rename_pattern.get()
                    new_filename = pattern.replace("{index}", formatted_idx)
                    new_filename = new_filename.replace("{title}", sanitized_title)
                    new_filename = new_filename.replace("{ext}", ext.lstrip('.'))

                    if not new_filename.endswith(ext):
                        new_filename = new_filename + ext

                    destination = os.path.join(playlist_folder, new_filename)
                    expected_files.append(destination)

                    try:
                        shutil.copy2(source_file, destination)
                        total_copied += 1
                        logger.debug(f"Copied: {source_file} -> {destination}")
                    except Exception as e:
                        failed_files.append(f"{title} ({str(e)})")
                        total_failed += 1
                        logger.error(f"Copy failed: {source_file} - {e}")

                    self.files_processed += 1
                    self.root.after(0, lambda v=self.files_processed: self.progress.config(value=v))
                    self.update_time_estimation(self.files_processed, total_files)

                # Store expected files for this playlist
                all_expected_files[os.path.basename(m3u_file)] = {
                    'folder': playlist_folder,
                    'files': expected_files,
                    'expected_count': len(tracks)
                }

                if failed_files:
                    m3u_name = os.path.basename(m3u_file)
                    all_failed_files.extend([f"{m3u_name}: {f}" for f in failed_files])

            # Check if aborted
            if self.abort_flag:
                total_time = time.time() - self.start_time
                total_time_str = self.format_time(total_time)

                self.root.after(0, lambda: self.status_label.config(text="Aborted by user"))
                self.root.after(0, lambda: self.time_label.config(text=f"Aborted after {total_time_str}"))

                message = f"Copy process aborted by user.\n\n"
                message += f"Files copied before abort: {total_copied}\n"
                message += f"Time elapsed: {total_time_str}\n\n"
                message += "Copied files remain in the destination folder."

                self.root.after(0, lambda: messagebox.showwarning("Aborted", message))
                logger.warning(f"Export aborted. Copied {total_copied} files before abort.")
                return

            # Verification phase (only if not aborted)
            self.root.after(0, lambda: self.status_label.config(text="Verifying exported files..."))
            self.root.after(0, lambda: self.time_label.config(text="Verifying..."))
            verification_issues = []

            for playlist_name, data in all_expected_files.items():
                missing = self.verify_exported_files(data['files'], data['folder'])
                if missing:
                    verification_issues.append(f"{playlist_name}: {len(missing)} files missing")
                    logger.warning(f"{playlist_name}: Missing files: {missing}")

                # Count actual files in the folder
                if self.create_subfolder.get():
                    actual_files = [f for f in os.listdir(data['folder'])
                                    if os.path.isfile(os.path.join(data['folder'], f))]
                    if len(actual_files) != data['expected_count']:
                        verification_issues.append(
                            f"{playlist_name}: Expected {data['expected_count']} files, found only {len(actual_files)}!"
                        )
                        logger.warning(
                            f"{playlist_name}: File count mismatch - expected {data['expected_count']}, found {len(actual_files)}")

            # Calculate total time
            total_time = time.time() - self.start_time
            total_time_str = self.format_time(total_time)

            # Build completion message
            message = f"Operation complete!\n\nSuccessfully copied: {total_copied} files"
            message += f"\nProcessed {len(self.m3u_files)} playlist(s)"
            message += f"\nTotal time: {total_time_str}"

            if all_failed_files:
                message += f"\n\nFailed: {total_failed} files:\n"
                message += "\n".join(all_failed_files[:10])
                if len(all_failed_files) > 10:
                    message += f"\n... and {len(all_failed_files) - 10} more"

            if verification_issues:
                message += "\n\n⚠️ VERIFICATION WARNINGS:\n"
                message += "\n".join(verification_issues)

            self.root.after(0, lambda: self.status_label.config(text="Completed"))
            self.root.after(0, lambda: self.time_label.config(text=f"Completed in {total_time_str}"))

            if verification_issues or all_failed_files:
                self.root.after(0, lambda: messagebox.showwarning("Complete with Issues", message))
                logger.warning(message)
            else:
                self.root.after(0, lambda: messagebox.showinfo("Complete", message))
                logger.info(message)

            if self.open_outputfolder.get():
                self.root.after(0, self.open_output_directory)

        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text="Error occurred"))
            self.root.after(0, lambda: self.time_label.config(text=""))
            self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred:\n{str(e)}"))
            logger.error(f"Export error: {e}")
        finally:
            # Change Abort button back to Exit button (thread-safe)
            self.root.after(0, self.set_button_to_exit)
            self.root.after(0, self.check_ready_to_export)
            # Reset abort flag
            self.abort_flag = False


def main():
    root = TkinterDnD.Tk()
    app = M3UExporter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
