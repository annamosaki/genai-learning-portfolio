"""In-memory IP-based rate limiting."""

import time
from collections import defaultdict, deque
from typing import Dict, Deque
from fastapi import HTTPException, Request
import asyncio


class RateLimiter:
    """Simple in-memory rate limiter by IP address."""
    
    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        
        # Store request timestamps per IP
        self.minute_requests: Dict[str, Deque[float]] = defaultdict(deque)
        self.hour_requests: Dict[str, Deque[float]] = defaultdict(deque)
        
        # Cleanup old entries periodically
        self._last_cleanup = time.time()
        
    async def check_rate_limit(self, request: Request) -> bool:
        """Check if request is within rate limits."""
        # Get client IP
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Cleanup old entries periodically (every 5 minutes)
        if current_time - self._last_cleanup > 300:
            await self._cleanup_old_entries(current_time)
            self._last_cleanup = current_time
        
        # Check minute limit
        minute_window = current_time - 60
        minute_queue = self.minute_requests[client_ip]
        
        # Remove old entries from minute window
        while minute_queue and minute_queue[0] <= minute_window:
            minute_queue.popleft()
        
        if len(minute_queue) >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {self.requests_per_minute} requests per minute"
            )
        
        # Check hour limit
        hour_window = current_time - 3600
        hour_queue = self.hour_requests[client_ip]
        
        # Remove old entries from hour window
        while hour_queue and hour_queue[0] <= hour_window:
            hour_queue.popleft()
            
        if len(hour_queue) >= self.requests_per_hour:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {self.requests_per_hour} requests per hour"
            )
        
        # Add current request
        minute_queue.append(current_time)
        hour_queue.append(current_time)
        
        return True
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        forwarded = request.headers.get("x-forwarded")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct client
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def _cleanup_old_entries(self, current_time: float):
        """Remove old entries to prevent memory leaks."""
        minute_cutoff = current_time - 60
        hour_cutoff = current_time - 3600
        
        # Clean up minute requests
        ips_to_remove = []
        for ip, queue in self.minute_requests.items():
            while queue and queue[0] <= minute_cutoff:
                queue.popleft()
            if not queue:
                ips_to_remove.append(ip)
        
        for ip in ips_to_remove:
            del self.minute_requests[ip]
        
        # Clean up hour requests
        ips_to_remove = []
        for ip, queue in self.hour_requests.items():
            while queue and queue[0] <= hour_cutoff:
                queue.popleft()
            if not queue:
                ips_to_remove.append(ip)
        
        for ip in ips_to_remove:
            del self.hour_requests[ip]


# Global rate limiter instance
rate_limiter = RateLimiter()