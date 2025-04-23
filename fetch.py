import asyncio
import aiohttp
import aiofiles
import logging
import time
import os
import json
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from config import config
from config import trytimes_when_failed
from time import sleep
 
try:
    import requests
except:
    from os import system as cmd
    cmd('pip config set global.index-url https://mirrors.cloud.tencent.com/pypi/simple')
    cmd('pip install -U requests')
    import requests
 
class DownloadError(Exception):
    """Exception raised for errors during file downloading"""
    pass

class DownloadSegment:
    """Class for downloading a segment of a file"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.chunk_size = config["chunk_size"]
        self.timeout = aiohttp.ClientTimeout(total=config["timeout"])
        self.retry_times = config["retry_times"]
    
    async def download_segment_async(self, 
                               file_path: str, 
                               byte_range: List[int], 
                               uri: str, 
                               user_agent: str, 
                               segment_id: int,
                               resume_offset: int = 0) -> bool:
        """
        Download a segment of a file asynchronously
        
        Args:
            file_path: Path to save the file
            byte_range: Range of bytes to download [start, end]
            uri: URL of the file
            user_agent: User agent string
            segment_id: ID of the segment for logging
            resume_offset: Offset to resume from if segment is partially downloaded
            
        Returns:
            True if download was successful
            
        Raises:
            DownloadError: If the segment couldn't be downloaded after retries
        """
        start_byte, end_byte = byte_range
        
        # Adjust range if resuming
        if resume_offset > 0 and resume_offset < (end_byte - start_byte + 1):
            self.logger.info(f"Resuming segment {segment_id} from offset {resume_offset}")
            start_byte = start_byte + resume_offset
        
        headers = {
            'User-Agent': user_agent,
            'Range': f'bytes={start_byte}-{end_byte}'
        }
        
        for attempt in range(self.retry_times):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.get(url=uri, headers=headers) as response:
                        if response.status not in [200, 206]:
                            raise DownloadError(f"Error downloading segment {segment_id}: HTTP {response.status}")
                        
                        # Read the entire segment data before writing
                        segment_data = await response.read()
                        
                        # Open file in binary mode and seek to the correct position
                        async with aiofiles.open(file_path, 'r+b') as file:
                            await file.seek(start_byte)
                            await file.write(segment_data)
                        
                        self.logger.info(f"Segment {segment_id} ({start_byte}-{end_byte}) downloaded successfully")
                        return True
                        
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout downloading segment {segment_id} (attempt {attempt+1}/{self.retry_times})")
            except aiohttp.ClientError as e:
                self.logger.warning(f"Network error downloading segment {segment_id}: {str(e)} (attempt {attempt+1}/{self.retry_times})")
            except Exception as e:
                self.logger.warning(f"Error downloading segment {segment_id}: {str(e)} (attempt {attempt+1}/{self.retry_times})")
            
            # Wait before retrying
            if attempt < self.retry_times - 1:
                await asyncio.sleep(3)
        
        raise DownloadError(f"Failed to download segment {segment_id} after {self.retry_times} attempts")

    def fetch(self, file_path: str, byte_range: List[int], uri: str, user_agent: str, segment_id: int) -> bool:
        """
        Synchronous wrapper for downloading a segment
        
        Args:
            file_path: Path to save the file
            byte_range: Range of bytes to download [start, end]
            uri: URL of the file
            user_agent: User agent string
            segment_id: ID of the segment for logging
            
        Returns:
            True if download was successful
        """
        try:
            result = asyncio.run(self.download_segment_async(file_path, byte_range, uri, user_agent, segment_id))
            if result:
                print(f"{segment_id}. {file_path} ({byte_range}) fetching completed.")
            return result
        except Exception as e:
            print(f"{segment_id}. Error downloading segment: {str(e)}")
            return False


class DownloadManager:
    """Manager for parallel downloads with progress tracking"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def download_file_async(self, uri: str, file_path: str, 
                                 segments: List[List[int]], user_agent: str, 
                                 show_progress: bool = True,
                                 resume: bool = True) -> str:
        """
        Download file in parallel using multiple segments
        
        Args:
            uri: URL of the file
            file_path: Path to save the file
            segments: List of byte ranges to download
            user_agent: User agent string
            show_progress: Whether to show a progress bar
            resume: Whether to attempt to resume a previous download
            
        Returns:
            Path to the downloaded file
        """
        file_path = Path(file_path)
        total_segments = len(segments)
        total_size = segments[-1][-1] + 1
        
        # State file for resumable downloads
        state_file = file_path.with_suffix(f"{file_path.suffix}.state")
        completed_segments = set()
        segment_progress = {}
        
        # Check if we can resume
        if resume and file_path.exists() and state_file.exists():
            try:
                self.logger.info(f"Found existing download state, attempting to resume")
                async with aiofiles.open(state_file, 'r') as f:
                    state_data = json.loads(await f.read())
                    
                if state_data.get('uri') == uri and state_data.get('total_size') == total_size:
                    # Valid state file for this download
                    completed_segments = set(state_data.get('completed_segments', []))
                    segment_progress = state_data.get('segment_progress', {})
                    
                    self.logger.info(f"Resuming download with {len(completed_segments)} completed segments")
                else:
                    self.logger.warning("State file exists but is for a different file, starting fresh")
                    # Different file, clear state
                    if file_path.exists():
                        file_path.unlink(missing_ok=True)
                    if state_file.exists():
                        state_file.unlink(missing_ok=True)
            except Exception as e:
                self.logger.warning(f"Error reading state file: {e}, starting fresh")
                if file_path.exists():
                    file_path.unlink(missing_ok=True)
                if state_file.exists():
                    state_file.unlink(missing_ok=True)
        
        try:
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create the file if it doesn't exist
            if not file_path.exists():
                # Create a sparse file of the right size if supported
                try:
                    # Create empty file
                    async with aiofiles.open(file_path, 'wb') as f:
                        pass
                    
                    # Try to allocate as sparse file on supported platforms
                    if os.name == 'posix':  # Linux, macOS
                        import fcntl
                        with open(file_path, 'rb+') as f:
                            f.seek(total_size - 1)
                            f.write(b'\0')
                    elif os.name == 'nt':  # Windows
                        with open(file_path, 'rb+') as f:
                            f.seek(total_size - 1)
                            f.write(b'\0')
                except Exception as e:
                    self.logger.warning(f"Could not create sparse file, using standard allocation: {e}")
                    async with aiofiles.open(file_path, 'wb') as f:
                        await f.truncate(total_size)
        except Exception as e:
            raise DownloadError(f"Error creating file: {str(e)}")
        
        # Set up progress tracking if requested
        if show_progress:
            try:
                from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
                from rich.console import Console
                
                # Create the progress bar without using async context manager
                progress = Progress(
                    TextColumn("[bold blue]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=Console()
                )
                
                # Manually start the progress bar
                progress.start()
                task_id = progress.add_task(f"Downloading {file_path.name}", total=total_segments, 
                                           completed=len(completed_segments))
                
                # Create and start download tasks
                tasks = []
                downloader = DownloadSegment()
                
                # Create a task to periodically update the state file
                async def update_state_periodically():
                    while True:
                        await self._save_state(state_file, uri, total_size, completed_segments, segment_progress)
                        await asyncio.sleep(5)  # Update every 5 seconds
                
                state_updater = asyncio.create_task(update_state_periodically())
                
                # Create download tasks for incomplete segments
                for i, byte_range in enumerate(segments):
                    if i in completed_segments:
                        continue
                    
                    # Get resume offset for this segment if any
                    resume_offset = int(segment_progress.get(str(i), 0))
                    
                    task = asyncio.create_task(
                        downloader.download_segment_async(str(file_path), byte_range, uri, 
                                                         user_agent, i, resume_offset)
                    )
                    
                    # Add callback to update progress and track completion
                    def make_callback(segment_id):
                        def callback(future):
                            try:
                                if future.result():
                                    completed_segments.add(segment_id)
                                    # Remove progress tracking once complete
                                    if str(segment_id) in segment_progress:
                                        del segment_progress[str(segment_id)]
                                    progress.update(task_id, advance=1)
                            except Exception:
                                pass
                        return callback
                    
                    task.add_done_callback(make_callback(i))
                    tasks.append(task)
                
                if not tasks:
                    self.logger.info("All segments already completed, download is already finished")
                else:
                    # Wait for all downloads to complete
                    try:
                        await asyncio.gather(*tasks)
                    except Exception as e:
                        self.logger.error(f"Error during download: {e}")
                    finally:
                        # Cancel the state updater
                        state_updater.cancel()
                        try:
                            await state_updater
                        except asyncio.CancelledError:
                            pass
                
                # Manually stop the progress bar
                progress.stop()
                
                # Save final state
                await self._save_state(state_file, uri, total_size, completed_segments, segment_progress)
                
                # If all segments completed, remove state file
                if len(completed_segments) == total_segments:
                    if state_file.exists():
                        state_file.unlink()
                    self.logger.info(f"Downloaded {file_path} successfully")
                else:
                    remaining = total_segments - len(completed_segments)
                    self.logger.warning(f"Download paused with {remaining} segments remaining")
            except ImportError:
                self.logger.warning("Rich library not available, progress bar will not be shown")
                show_progress = False
                # Fallback to no-progress version
                await self._download_without_progress(uri, file_path, segments, user_agent, 
                                                    state_file, completed_segments, segment_progress)
        else:
            # Download without progress bar
            await self._download_without_progress(uri, file_path, segments, user_agent, 
                                                state_file, completed_segments, segment_progress)
        
        return str(file_path)
    
    async def _download_without_progress(self, uri, file_path, segments, user_agent, 
                                        state_file, completed_segments, segment_progress):
        """Helper method to download without progress bar"""
        tasks = []
        downloader = DownloadSegment()
        
        # Create a task to periodically update the state file
        async def update_state_periodically():
            while True:
                await self._save_state(state_file, uri, segments[-1][-1] + 1, 
                                      completed_segments, segment_progress)
                await asyncio.sleep(5)  # Update every 5 seconds
        
        state_updater = asyncio.create_task(update_state_periodically())
        
        # Create download tasks for incomplete segments
        for i, byte_range in enumerate(segments):
            if i in completed_segments:
                continue
            
            # Get resume offset for this segment if any
            resume_offset = int(segment_progress.get(str(i), 0))
            
            task = asyncio.create_task(
                downloader.download_segment_async(str(file_path), byte_range, uri, 
                                                 user_agent, i, resume_offset)
            )
            
            # Add callback to track completion
            def make_callback(segment_id):
                def callback(future):
                    try:
                        if future.result():
                            completed_segments.add(segment_id)
                            # Remove progress tracking once complete
                            if str(segment_id) in segment_progress:
                                del segment_progress[str(segment_id)]
                    except Exception:
                        pass
                return callback
            
            task.add_done_callback(make_callback(i))
            tasks.append(task)
        
        if not tasks:
            self.logger.info("All segments already completed, download is already finished")
        else:
            # Wait for all downloads to complete
            try:
                await asyncio.gather(*tasks)
            except Exception as e:
                self.logger.error(f"Error during download: {e}")
            finally:
                # Cancel the state updater
                state_updater.cancel()
                try:
                    await state_updater
                except asyncio.CancelledError:
                    pass
        
        # Save final state
        await self._save_state(state_file, uri, segments[-1][-1] + 1, 
                              completed_segments, segment_progress)
        
        # If all segments completed, remove state file
        if len(completed_segments) == len(segments):
            if Path(state_file).exists():
                Path(state_file).unlink()
            self.logger.info(f"Downloaded {file_path} successfully")
        else:
            remaining = len(segments) - len(completed_segments)
            self.logger.warning(f"Download paused with {remaining} segments remaining")
    
    async def _save_state(self, state_file, uri, total_size, completed_segments, segment_progress):
        """Save download state to file"""
        state = {
            'uri': uri,
            'total_size': total_size,
            'completed_segments': list(completed_segments),
            'segment_progress': segment_progress,
            'timestamp': time.time()
        }
        
        try:
            async with aiofiles.open(state_file, 'w') as f:
                await f.write(json.dumps(state))
        except Exception as e:
            self.logger.warning(f"Error saving state file: {e}")


# Maintain backward compatibility
fetchObject = DownloadSegment