from typing import List, Tuple
import logging

class CalcSegments:
    """Class for calculating download segments for parallel downloading"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_segment(self, max_size: int, segments_amount: int) -> List[List[int]]:
        """
        Calculate download segments based on file size and desired segment count
        
        Args:
            max_size: Total size of the file in bytes
            segments_amount: Number of segments to divide the download into
            
        Returns:
            List of segment ranges as [start, end] pairs
            
        Raises:
            ValueError: If file size is invalid or server forbids access
        """
        self.logger.info(f"Calculating segments for {max_size} bytes file into {segments_amount} parts")
        
        if max_size <= 0:
            raise ValueError('Invalid file size. This link may be expired or forbidden by the remote server.')
            
        # Adjust segment amount if file is too small
        actual_segments = min(segments_amount, max_size)
        if actual_segments < segments_amount:
            self.logger.warning(f"File too small for {segments_amount} segments, using {actual_segments} instead")
            segments_amount = actual_segments
            
        # Calculate segment size and create segment ranges
        standard_size = max_size // segments_amount
        l1_segments = list(range(0, max_size, standard_size))
        
        # Create segments as [start, end] pairs
        segments = [[x, x + standard_size - 1] for x in l1_segments]
        
        # Ensure the last segment reaches the end of file
        segments[-1][-1] = max_size - 1
        
        return segments
