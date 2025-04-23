import re
import threading
import time
import tkinter as tk
from tkinter import messagebox
import pyperclip
from urllib.parse import urlparse
import logging

# Logger setup
logger = logging.getLogger("clipboard_monitor")

class ClipboardMonitor:
    """Monitor clipboard for URLs and prompt user to download them"""
    
    def __init__(self, downloader=None):
        """
        Initialize the clipboard monitor
        
        Args:
            downloader: Instance of the Downloader class
        """
        self.downloader = downloader
        self.monitoring = False
        self.monitor_thread = None
        self.last_clipboard_content = ""
        self.url_pattern = re.compile(
            r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*\??[/\w\.-=&%]*'
        )
        
    def is_valid_url(self, text):
        """Check if the text contains a valid URL"""
        if not text:
            return False
            
        # Check if it matches URL pattern
        if self.url_pattern.search(text):
            try:
                # Verify it's a proper URL with urlparse
                parsed = urlparse(text)
                return all([parsed.scheme, parsed.netloc])
            except:
                return False
        return False
        
    def show_download_prompt(self, url):
        """Show a dialog asking if user wants to download the URL"""
        try:
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            
            # Set window position to center of screen
            root.attributes('-topmost', True)
            
            download_frame = tk.Toplevel(root)
            download_frame.title("Download link detected")
            download_frame.geometry("500x200")  # Make the window taller for the new field
            download_frame.resizable(False, False)
            
            # Center the window
            window_width = 500
            window_height = 200  # Updated height
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            center_x = int(screen_width/2 - window_width/2)
            center_y = int(screen_height/2 - window_height/2)
            download_frame.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
            
            # Address entry
            tk.Label(download_frame, text="Address").grid(row=0, column=0, padx=10, pady=10, sticky='w')
            url_var = tk.StringVar(value=url)
            url_entry = tk.Entry(download_frame, textvariable=url_var, width=50)
            url_entry.grid(row=0, column=1, padx=10, pady=10, sticky='we')
            url_entry.insert(0, url)  # Explicitly set text to ensure it's visible
            
            # Try to get a default filename from the URL
            default_filename = ""
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                path_parts = parsed_url.path.split('/')
                if path_parts and path_parts[-1]:
                    default_filename = path_parts[-1]
            except:
                pass
            
            # Filename entry
            tk.Label(download_frame, text="Save As").grid(row=1, column=0, padx=10, pady=10, sticky='w')
            filename_var = tk.StringVar(value=default_filename)
            filename_entry = tk.Entry(download_frame, textvariable=filename_var, width=50)
            filename_entry.grid(row=1, column=1, padx=10, pady=10, sticky='we')
            filename_entry.insert(0, default_filename)  # Explicitly set text
            
            # Authentication frame
            auth_frame = tk.LabelFrame(download_frame, text="Use authorization")
            auth_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky='we')
            
            # Login and password fields
            tk.Label(auth_frame, text="Login").grid(row=0, column=0, padx=5, pady=5)
            login_entry = tk.Entry(auth_frame, width=20)
            login_entry.grid(row=0, column=1, padx=5, pady=5)
            
            tk.Label(auth_frame, text="Password").grid(row=0, column=2, padx=5, pady=5)
            password_entry = tk.Entry(auth_frame, width=20, show="*")
            password_entry.grid(row=0, column=3, padx=5, pady=5)
            
            # Button frame
            button_frame = tk.Frame(download_frame)
            button_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky='e')
            
            result = {"ok": False, "url": url, "filename": default_filename, "login": "", "password": ""}  # Use dict to store result
            
            def on_ok():
                try:
                    # Capture values before destroying widgets
                    result["ok"] = True
                    result["url"] = url_var.get()
                    result["filename"] = filename_var.get()
                    result["login"] = login_entry.get()
                    result["password"] = password_entry.get()
                except Exception as e:
                    logger.error(f"Error capturing entry values: {e}")
                finally:
                    # Always destroy windows
                    download_frame.destroy()
                    root.destroy()
                
            def on_cancel():
                download_frame.destroy()
                root.destroy()
            
            # OK and Cancel buttons
            ok_button = tk.Button(button_frame, text="OK", width=10, command=on_ok)
            ok_button.grid(row=0, column=0, padx=5)
            
            cancel_button = tk.Button(button_frame, text="Cancel", width=10, command=on_cancel)
            cancel_button.grid(row=0, column=1, padx=5)
            
            # Capture Enter key to confirm dialog
            download_frame.bind("<Return>", lambda event: on_ok())
            download_frame.bind("<Escape>", lambda event: on_cancel())
            
            # Focus on the URL entry
            url_entry.focus_set()
            url_entry.select_range(0, tk.END)
            
            # Wait for user response
            root.wait_window(download_frame)
            
            if result["ok"]:
                # User clicked OK
                credentials = None
                
                if result["login"] and result["password"]:
                    credentials = (result["login"], result["password"])
                    
                filename = result["filename"] if result["filename"] else None
                
                return True, result["url"], credentials, filename
            
            return False, None, None, None
            
        except Exception as e:
            logger.error(f"Error showing download prompt: {e}")
            return False, None, None, None
        
    def _monitor_clipboard(self):
        """Background thread to monitor clipboard"""
        while self.monitoring:
            try:
                # Get current clipboard content
                clipboard_content = pyperclip.paste()
                
                # Check if content changed and is a URL
                if (clipboard_content != self.last_clipboard_content and 
                        self.is_valid_url(clipboard_content)):
                    
                    logger.info(f"URL detected in clipboard: {clipboard_content}")
                    
                    # Store original URL before showing prompt to prevent race conditions
                    detected_url = clipboard_content
                    self.last_clipboard_content = clipboard_content
                    
                    # Run the download prompt in the main thread
                    try:
                        download, url, credentials, filename = self.show_download_prompt(detected_url)
                        
                        if download and self.downloader:
                            # Start download in a separate thread to avoid blocking
                            thread = threading.Thread(
                                target=self._start_download, 
                                args=(url, credentials, filename)
                            )
                            thread.daemon = True
                            thread.start()
                    except Exception as e:
                        logger.error(f"Error handling download prompt: {e}")
                        
            except Exception as e:
                logger.error(f"Error monitoring clipboard: {e}")
                # Short pause to prevent CPU spinning when there's an error
                time.sleep(1)
            
            # Short sleep to avoid high CPU usage
            time.sleep(0.5)
    
    def _start_download(self, url, credentials=None, filename=None):
        """Start a download with the downloader"""
        try:
            if credentials:
                # If we had authentication, we'd need to handle it
                # For now, just log it
                logger.info(f"Download with auth: {url} (auth: {credentials[0]})")
            
            logger.info(f"Starting download: {url}")
            
            # If filename is provided, create full path in the default download directory
            output_path = None
            if filename:
                from config import store_pth
                import os
                output_path = os.path.join(store_pth, filename)
                logger.info(f"Custom filename: {output_path}")
                
            self.downloader.download_file(url=url, output_path=output_path)
        except Exception as e:
            logger.error(f"Error starting download: {e}")
    
    def start_monitoring(self):
        """Start monitoring the clipboard"""
        if not self.monitoring:
            logger.info("Starting clipboard monitoring")
            self.monitoring = True
            self.last_clipboard_content = pyperclip.paste()  # Initialize with current clipboard
            
            self.monitor_thread = threading.Thread(target=self._monitor_clipboard)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring the clipboard"""
        if self.monitoring:
            logger.info("Stopping clipboard monitoring")
            self.monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=1.0)
                self.monitor_thread = None 