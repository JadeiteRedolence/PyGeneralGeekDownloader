#!/usr/bin/env python3
"""
PyGeneralGeekDownloader - Fast asynchronous file downloader with segmented downloading
"""

import asyncio
import logging
import click
import os
import sys
import time
import threading
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("pydownloader")

# Import our modules
from config import config, store_pth
from calc import CalcSegments
from fetch import DownloadManager, DownloadSegment
from getsize import FileInfoManager
from clipboard_monitor import ClipboardMonitor

class Downloader:
    """Main downloader class that orchestrates the download process"""
    
    def __init__(self):
        self.file_info = FileInfoManager()
        self.segment_calculator = CalcSegments()
        self.download_manager = DownloadManager()
    
    async def download_file_async(self, url: str, output_path: Optional[str] = None, 
                                segments: Optional[int] = None, show_progress: bool = True,
                                resume: bool = True) -> str:
        """
        Download a file asynchronously using segmented downloading
        
        Args:
            url: URL of the file to download
            output_path: Path to save the file (if None, determined automatically)
            segments: Number of segments to use (if None, uses config value)
            show_progress: Whether to show a progress bar
            resume: Whether to attempt to resume a previous download
            
        Returns:
            Path to the downloaded file
        """
        # Get file info including size and suggested filename
        logger.info(f"Getting information for {url}")
        file_info = await self.file_info.get_file_info_async(url, config["user_agent"])
        file_size = file_info["size"]
        filename = file_info["filename"]
        
        # Determine segments to use
        segments_count = segments or config["segments_amount"]
        if not file_info.get("supports_range", True):
            logger.warning("Server doesn't support range requests, using single segment")
            segments_count = 1
        
        # Calculate segments
        segment_ranges = self.segment_calculator.get_segment(file_size, segments_count)
        actual_segments = len(segment_ranges)
        
        # Determine output path
        if output_path is None:
            # No output path specified, use default directory with original filename
            output_path = os.path.join(store_pth, filename)
        elif os.path.isdir(output_path):
            # If output_path is a directory, add the original filename to it
            output_path = os.path.join(output_path, filename)
        else:
            # output_path already contains a filename, use it as is
            # Make sure the directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        output_path = os.path.abspath(output_path)
        
        # Log download information
        logger.info(f"Downloading {url} to {output_path}")
        logger.info(f"File size: {file_size / (1024**2):.2f} MB")
        logger.info(f"Using {actual_segments} segments")
        
        # Start the download
        result = await self.download_manager.download_file_async(
            url, output_path, segment_ranges, config["user_agent"], show_progress, resume
        )
        
        logger.info(f"Download completed: {result}")
        return result

    def download_file(self, url: str, output_path: Optional[str] = None, 
                    segments: Optional[int] = None, show_progress: bool = True,
                    resume: bool = True) -> str:
        """Synchronous wrapper for download_file_async"""
        return asyncio.run(self.download_file_async(url, output_path, segments, show_progress, resume))


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
def cli(debug):
    """PyGeneralGeekDownloader - Fast parallel file downloader with segmented downloading"""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)


@cli.command()
@click.argument('url')
@click.option('-o', '--output', help='Output file or directory')
@click.option('-s', '--segments', type=int, help=f'Number of segments (default: {config["segments_amount"]})')
@click.option('--no-progress', is_flag=True, help='Disable progress bar')
@click.option('--no-resume', is_flag=True, help='Disable resuming previous download')
@click.option('-f', '--filename', help='Save file with this name (in default download directory if -o not specified)')
def download(url, output, segments, no_progress, no_resume, filename):
    """Download a file from URL"""
    try:
        downloader = Downloader()
        
        # Handle filename and output path together
        if filename and not output:
            # If filename is provided but not output, use default directory
            output_path = os.path.join(store_pth, filename)
        else:
            # Otherwise, just pass output as is
            output_path = output
            
        result = downloader.download_file(url, output_path, segments, not no_progress, not no_resume)
        click.echo(f"Successfully downloaded to: {result}")
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument('url')
def info(url):
    """Get information about a file without downloading it"""
    try:
        file_info = FileInfoManager()
        info_result = asyncio.run(file_info.get_file_info_async(url, config["user_agent"]))
        
        click.echo(f"File: {info_result['filename']}")
        click.echo(f"Size: {info_result['size'] / (1024**2):.2f} MB")
        click.echo(f"Type: {info_result['content_type']}")
        click.echo(f"Supports range: {info_result.get('supports_range', False)}")
    except Exception as e:
        logger.error(f"Failed to get file info: {str(e)}")
        sys.exit(1)


@cli.command()
def config_info():
    """Show current configuration"""
    for key, value in config.items():
        click.echo(f"{key}: {value}")


@cli.command()
@click.option('--reset', is_flag=True, help='Reset configuration to defaults')
def config_edit(reset):
    """Edit configuration interactively"""
    import json
    from config import CONFIG_FILE, DEFAULT_CONFIG
    
    if reset:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        click.echo("Configuration reset to defaults")
        return
    
    try:
        import tempfile
        import subprocess
        
        # Write config to temp file
        fd, temp_path = tempfile.mkstemp(suffix='.json')
        with os.fdopen(fd, 'w') as f:
            json.dump(config, f, indent=4)
        
        # Open editor
        editor = os.environ.get('EDITOR', 'notepad' if os.name == 'nt' else 'nano')
        subprocess.call([editor, temp_path])
        
        # Read back config
        with open(temp_path, 'r') as f:
            new_config = json.load(f)
        
        # Validate and save
        for key in DEFAULT_CONFIG:
            if key not in new_config:
                new_config[key] = DEFAULT_CONFIG[key]
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(new_config, f, indent=4)
        
        click.echo("Configuration updated")
    except Exception as e:
        logger.error(f"Failed to edit config: {str(e)}")
        sys.exit(1)


@cli.command()
@click.option('-p', '--path', help='Directory to search for partial downloads', default=store_pth)
def list_downloads(path):
    """List all in-progress downloads that can be resumed"""
    import json
    import glob
    from datetime import datetime
    
    search_path = Path(path).expanduser() if path else Path(store_pth)
    state_files = list(search_path.glob("*.state"))
    
    if not state_files:
        click.echo("No partial downloads found.")
        return
    
    click.echo("\nResumable downloads:")
    click.echo("-------------------")
    
    for i, state_file in enumerate(state_files, 1):
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            file_path = state_file.with_suffix('')
            timestamp = datetime.fromtimestamp(state.get('timestamp', 0))
            total_size = state.get('total_size', 0) / (1024 * 1024)  # MB
            completed = len(state.get('completed_segments', []))
            total = int(total_size * 1024 * 1024 / (state.get('total_size', 1) / len(state.get('completed_segments', [1]))))
            progress = (completed / total) * 100 if total > 0 else 0
            
            click.echo(f"{i}. {file_path.name}")
            click.echo(f"   URL: {state.get('uri', 'Unknown')}")
            click.echo(f"   Size: {total_size:.2f} MB")
            click.echo(f"   Progress: {progress:.1f}% ({completed}/{total} segments)")
            click.echo(f"   Last updated: {timestamp}")
            click.echo("")
        except Exception as e:
            click.echo(f"{i}. {state_file.with_suffix('').name} (Error: {str(e)})")
    
    click.echo("\nTo resume a download:")
    click.echo("python app.py resume [URL]")


@cli.command()
@click.argument('url')
@click.option('-o', '--output', help='Custom output location')
@click.option('--no-progress', is_flag=True, help='Disable progress bar')
def resume(url, output, no_progress):
    """Resume a previously started download"""
    import glob
    import json
    
    downloader = Downloader()
    
    # If URL is provided, try to find a matching state file
    if url:
        try:
            # First try exact match with the file
            if Path(url).exists():
                state_file = Path(url)
                if not state_file.suffix == '.state':
                    state_file = Path(f"{url}.state")
            else:
                # Try to find a state file with matching URL
                state_files = list(Path(store_pth).glob("*.state"))
                state_file = None
                
                for sf in state_files:
                    try:
                        with open(sf, 'r') as f:
                            state = json.load(f)
                        if state.get('uri') == url:
                            state_file = sf
                            break
                    except:
                        continue
            
            if state_file and state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
                
                file_path = state_file.with_suffix('')
                if output:
                    result = downloader.download_file(
                        state.get('uri'), output, None, not no_progress, True
                    )
                else:
                    result = downloader.download_file(
                        state.get('uri'), str(file_path), None, not no_progress, True
                    )
                
                click.echo(f"Successfully resumed download to: {result}")
                return
            
            # No state file found for this URL, start fresh
            click.echo(f"No partial download found for {url}. Starting a new download.")
            result = downloader.download_file(url, output, None, not no_progress, False)
            click.echo(f"Successfully downloaded to: {result}")
            
        except Exception as e:
            logger.error(f"Resume failed: {str(e)}")
            sys.exit(1)
    else:
        click.echo("Please provide a URL or file path to resume.")
        sys.exit(1)


@cli.command()
def monitor():
    """Start clipboard monitoring for URLs to download"""
    try:
        downloader = Downloader()
        monitor = ClipboardMonitor(downloader)
        
        click.echo("Starting clipboard monitor. Press Ctrl+C to stop.")
        monitor.start_monitoring()
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            click.echo("\nStopping clipboard monitor.")
            monitor.stop_monitoring()
    except Exception as e:
        logger.error(f"Clipboard monitor error: {str(e)}")
        sys.exit(1)


@cli.command()
@click.option('--monitor', is_flag=True, help='Start clipboard monitoring')
def gui(monitor):
    """Launch the graphical user interface"""
    start_gui(monitor)

def start_gui(monitor=True):
    """Start the graphical user interface with optional clipboard monitoring"""
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
        
        # Create main window
        root = tk.Tk()
        root.title("PyGeneralGeekDownloader")
        root.geometry("600x400")
        
        # Initialize downloader
        downloader = Downloader()
        
        # Initialize clipboard monitor if requested
        clipboard_mon = None
        if monitor:
            clipboard_mon = ClipboardMonitor(downloader)
            clipboard_mon.start_monitoring()
            logger.info("Clipboard monitoring started")
        
        # Function to download from URL
        def start_download():
            url = url_entry.get()
            if not url:
                messagebox.showerror("Error", "Please enter a URL")
                return
                
            output_dir = output_path_var.get()
            filename = filename_var.get()
            segments = segments_var.get()
            show_progress = progress_var.get()
            
            # Handle filename and output together
            if filename and not output_dir:
                # Use default dir with custom filename
                output_path = os.path.join(store_pth, filename)
            elif filename and output_dir:
                # Use custom dir with custom filename
                output_path = os.path.join(output_dir, filename)
            else:
                # Just use the output_dir as is
                output_path = output_dir if output_dir else None
            
            # Start download in a separate thread
            def download_thread():
                try:
                    status_label.config(text="Downloading...")
                    result = downloader.download_file(
                        url=url, 
                        output_path=output_path,
                        segments=segments if segments > 0 else None,
                        show_progress=show_progress
                    )
                    status_label.config(text=f"Downloaded to: {result}")
                except Exception as e:
                    status_label.config(text=f"Error: {str(e)}")
            
            thread = threading.Thread(target=download_thread)
            thread.daemon = True
            thread.start()
            
        def browse_output_dir():
            directory = filedialog.askdirectory()
            if directory:
                output_path_var.set(directory)
                
        def toggle_monitor():
            nonlocal clipboard_mon
            
            if clipboard_mon and clipboard_mon.monitoring:
                clipboard_mon.stop_monitoring()
                monitor_button.config(text="Start Monitor")
                logger.info("Clipboard monitoring stopped")
            else:
                if not clipboard_mon:
                    clipboard_mon = ClipboardMonitor(downloader)
                clipboard_mon.start_monitoring()
                monitor_button.config(text="Stop Monitor")
                logger.info("Clipboard monitoring started")
        
        # On window close
        def on_closing():
            if clipboard_mon:
                clipboard_mon.stop_monitoring()
            root.destroy()
            
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # URL entry
        url_frame = ttk.Frame(main_frame)
        url_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(url_frame, text="URL:").pack(side=tk.LEFT)
        url_entry = ttk.Entry(url_frame)
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Filename entry
        filename_frame = ttk.Frame(main_frame)
        filename_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(filename_frame, text="Save As:").pack(side=tk.LEFT)
        filename_var = tk.StringVar()
        filename_entry = ttk.Entry(filename_frame, textvariable=filename_var)
        filename_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Auto-detect filename when URL changes
        def update_filename(*args):
            try:
                url = url_entry.get()
                if url:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(url)
                    path_parts = parsed_url.path.split('/')
                    if path_parts and path_parts[-1]:
                        filename_var.set(path_parts[-1])
            except Exception as e:
                logger.debug(f"Error auto-detecting filename: {e}")
        
        # Watch for changes to URL entry
        url_entry.bind('<FocusOut>', update_filename)
        url_entry.bind('<Return>', update_filename)
        
        # Output directory
        output_frame = ttk.Frame(main_frame)
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(output_frame, text="Save to:").pack(side=tk.LEFT)
        output_path_var = tk.StringVar(value=store_pth)
        output_entry = ttk.Entry(output_frame, textvariable=output_path_var)
        output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        browse_button = ttk.Button(output_frame, text="Browse", command=browse_output_dir)
        browse_button.pack(side=tk.RIGHT)
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Options")
        options_frame.pack(fill=tk.X, pady=10)
        
        # Segments
        segments_frame = ttk.Frame(options_frame)
        segments_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(segments_frame, text="Segments:").pack(side=tk.LEFT, padx=5)
        segments_var = tk.IntVar(value=config["segments_amount"])
        segments_spinbox = ttk.Spinbox(
            segments_frame, 
            from_=1, 
            to=128, 
            textvariable=segments_var, 
            width=5
        )
        segments_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Progress bar option
        progress_var = tk.BooleanVar(value=True)
        progress_check = ttk.Checkbutton(
            options_frame, 
            text="Show progress", 
            variable=progress_var
        )
        progress_check.pack(anchor=tk.W, padx=5, pady=5)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        download_button = ttk.Button(
            button_frame, 
            text="Download", 
            command=start_download
        )
        download_button.pack(side=tk.LEFT, padx=5)
        
        monitor_button = ttk.Button(
            button_frame, 
            text="Stop Monitor" if (monitor and clipboard_mon) else "Start Monitor", 
            command=toggle_monitor
        )
        monitor_button.pack(side=tk.LEFT, padx=5)
        
        # Status label
        status_label = ttk.Label(main_frame, text="Ready")
        status_label.pack(anchor=tk.W, pady=10)
        
        # Start the GUI
        root.mainloop()
        
    except Exception as e:
        logger.error(f"GUI error: {str(e)}")
        sys.exit(1)


# Legacy interface for backward compatibility
def legacy_main():
    """Legacy command-line interface for backward compatibility"""
    try:
        downloader = Downloader()
        
        # Get URL from user
        url = input('Download link (eg. https://....): ')
        
        # Suggest filename from URL
        parsed_url = urlparse(url)
        suggested_name = os.path.basename(parsed_url.path) or 'downloaded_file'
        filename = input(f'Download as (filename) [{suggested_name}]: ') or suggested_name
        
        # Ask about resuming
        resume = True
        output_path = os.path.join(store_pth, filename)
        if os.path.exists(output_path) or os.path.exists(f"{output_path}.state"):
            resume_choice = input('Resume previous download if available? [Y/n]: ').lower()
            resume = resume_choice != 'n'
        
        # Download file
        result = downloader.download_file(url, output_path, None, True, resume)
        
        print(f"\nDownload completed: {result}")
        input('Press Enter to exit...')
    except KeyboardInterrupt:
        print("\nDownload cancelled.")
    except Exception as e:
        print(f"\nError: {str(e)}")
        input('Press Enter to exit...')


if __name__ == "__main__":
    # If arguments provided, use CLI interface
    if len(sys.argv) > 1:
        cli()
    else:
        # Try to launch GUI if no arguments provided
        try:
            import tkinter
            start_gui(monitor=True)  # Start GUI with clipboard monitoring by default
        except ImportError:
            # Fall back to legacy interface if tkinter is not available
            legacy_main()