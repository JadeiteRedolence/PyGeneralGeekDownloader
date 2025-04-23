import aiohttp
import asyncio
import logging
from typing import Optional
from config import config

class FileInfoError(Exception):
    """Exception raised for errors when fetching file information"""
    pass

class FileInfoManager:
    """Class for fetching remote file information including size"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.timeout = aiohttp.ClientTimeout(total=config["timeout"])
    
    async def get_file_info_async(self, uri: str, user_agent: str) -> dict:
        """
        Get file information asynchronously
        
        Args:
            uri: URL of the file
            user_agent: User agent to use for the request
            
        Returns:
            Dictionary with file information including size, filename, content_type
            
        Raises:
            FileInfoError: If file info cannot be obtained
        """
        self.logger.info(f"Getting file info for {uri}")
        headers = {"User-Agent": user_agent}
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.head(url=uri, headers=headers, allow_redirects=True) as response:
                    if response.status >= 400:
                        raise FileInfoError(f"Error fetching file info: HTTP {response.status}")
                    
                    # Get file size using different header methods
                    file_size = self._extract_file_size(response.headers)
                    if file_size is None:
                        # If HEAD doesn't work, try a range request
                        async with session.get(url=uri, headers={**headers, "Range": "bytes=0-1"}, 
                                              allow_redirects=True) as range_response:
                            file_size = self._extract_file_size(range_response.headers)
                    
                    # Get filename from Content-Disposition or URL
                    filename = self._extract_filename(uri, response.headers)
                    
                    return {
                        "size": file_size,
                        "filename": filename,
                        "content_type": response.headers.get("Content-Type", "application/octet-stream"),
                        "supports_range": "Accept-Ranges" in response.headers or "Content-Range" in response.headers
                    }
        except asyncio.TimeoutError:
            raise FileInfoError(f"Timeout while fetching file info from {uri}")
        except aiohttp.ClientError as e:
            raise FileInfoError(f"Network error: {str(e)}")
        except Exception as e:
            raise FileInfoError(f"Unexpected error: {str(e)}")
    
    def get_file_size(self, uri: str, user_agent: str) -> int:
        """
        Synchronous wrapper to get just the file size
        
        Args:
            uri: URL of the file
            user_agent: User agent to use for the request
            
        Returns:
            File size in bytes
            
        Raises:
            FileInfoError: If file size cannot be determined
        """
        self.logger.info(f"Getting file size for {uri}")
        file_info = asyncio.run(self.get_file_info_async(uri, user_agent))
        return file_info["size"]
    
    def _extract_file_size(self, headers: dict) -> Optional[int]:
        """Extract file size from headers using various methods"""
        try:
            # Try Content-Range header (method 1)
            if "Content-Range" in headers:
                try:
                    return int(headers["Content-Range"].split("/")[-1])
                except (ValueError, IndexError):
                    try:
                        return int(headers["Content-Range"].split("-")[-1])
                    except (ValueError, IndexError):
                        pass
            
            # Try Content-Length header
            if "Content-Length" in headers:
                return int(headers["Content-Length"])
            
            return None
        except Exception as e:
            self.logger.error(f"Error extracting file size: {e}")
            return None
    
    def _extract_filename(self, uri: str, headers: dict) -> str:
        """Extract filename from Content-Disposition header or URL"""
        # Try Content-Disposition header
        if "Content-Disposition" in headers:
            content_disp = headers["Content-Disposition"]
            for part in content_disp.split(";"):
                part = part.strip()
                if part.startswith("filename="):
                    filename = part[9:].strip('"\'')
                    if filename:
                        return filename
        
        # Fallback to URL
        try:
            from urllib.parse import urlparse
            path = urlparse(uri).path
            filename = path.split("/")[-1]
            if filename:
                return filename
        except Exception:
            pass
        
        # Default filename if nothing else works
        return "downloaded_file"


# Maintain backward compatibility
getObjectSize = FileInfoManager
