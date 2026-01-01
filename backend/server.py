from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import time
import asyncio
from functools import wraps
from collections import deque
import math

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Rate Limiter System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("CORS middleware configured to allow http://localhost:3000")


# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# In-memory storage for rate limiting (for demo purposes)
# In production, use Redis or similar distributed cache
rate_limit_storage = {}
token_buckets = {}
leaky_buckets = {}
fixed_windows = {}
sliding_windows = {}

# ==================== MODELS ====================

class APIKeyModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    api_key: str = Field(default_factory=lambda: f"api_key_{uuid.uuid4().hex}")
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

class RateLimitConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    api_key: str
    algorithm: str  # token_bucket, leaky_bucket, fixed_window, sliding_window
    max_requests: int
    window_seconds: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RequestLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    api_key: str
    endpoint: str
    algorithm: str
    allowed: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    remaining_quota: int

class LoadTestRequest(BaseModel):
    api_key: str
    requests_per_second: int
    duration_seconds: int
    endpoint: str = "/api/protected/test"

class APIKeyCreate(BaseModel):
    name: str

class RateLimitConfigCreate(BaseModel):
    api_key: str
    algorithm: str
    max_requests: int
    window_seconds: int

# ==================== RATE LIMITING ALGORITHMS ====================

class TokenBucket:
    """Token Bucket Algorithm - Tokens refill at a constant rate"""
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        
        # Refill tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def get_remaining(self) -> int:
        now = time.time()
        elapsed = now - self.last_refill
        current_tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        return int(current_tokens)

class LeakyBucket:
    """Leaky Bucket Algorithm - Processes requests at constant rate"""
    def __init__(self, capacity: int, leak_rate: float):
        self.capacity = capacity
        self.queue = deque()
        self.leak_rate = leak_rate  # requests per second
        self.last_leak = time.time()
    
    def add_request(self) -> bool:
        now = time.time()
        elapsed = now - self.last_leak
        
        # Leak requests based on elapsed time
        leaks = int(elapsed * self.leak_rate)
        for _ in range(min(leaks, len(self.queue))):
            if self.queue:
                self.queue.popleft()
        self.last_leak = now
        
        if len(self.queue) < self.capacity:
            self.queue.append(now)
            return True
        return False
    
    def get_remaining(self) -> int:
        now = time.time()
        elapsed = now - self.last_leak
        leaks = int(elapsed * self.leak_rate)
        current_size = max(0, len(self.queue) - leaks)
        return self.capacity - current_size

class FixedWindow:
    """Fixed Window Counter - Resets counter at fixed intervals"""
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.counter = 0
        self.window_start = time.time()
    
    def allow_request(self) -> bool:
        now = time.time()
        
        # Check if window expired
        if now - self.window_start >= self.window_seconds:
            self.counter = 0
            self.window_start = now
        
        if self.counter < self.max_requests:
            self.counter += 1
            return True
        return False
    
    def get_remaining(self) -> int:
        now = time.time()
        if now - self.window_start >= self.window_seconds:
            return self.max_requests
        return max(0, self.max_requests - self.counter)

class SlidingWindowCounter:
    """Sliding Window Counter - Weighted counter across windows"""
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.current_window_count = 0
        self.previous_window_count = 0
        self.current_window_start = time.time()
    
    def allow_request(self) -> bool:
        now = time.time()
        elapsed = now - self.current_window_start
        
        # Move to new window if needed
        if elapsed >= self.window_seconds:
            self.previous_window_count = self.current_window_count
            self.current_window_count = 0
            self.current_window_start = now
            elapsed = 0
        
        # Calculate weighted count
        weight = (self.window_seconds - elapsed) / self.window_seconds
        estimated_count = self.previous_window_count * weight + self.current_window_count
        
        if estimated_count < self.max_requests:
            self.current_window_count += 1
            return True
        return False
    
    def get_remaining(self) -> int:
        now = time.time()
        elapsed = now - self.current_window_start
        
        if elapsed >= self.window_seconds:
            return self.max_requests
        
        weight = (self.window_seconds - elapsed) / self.window_seconds
        estimated_count = self.previous_window_count * weight + self.current_window_count
        return max(0, int(self.max_requests - estimated_count))

# ==================== RATE LIMITER MIDDLEWARE ====================

async def get_rate_limit_config(api_key: str) -> Optional[RateLimitConfig]:
    """Get rate limit configuration for an API key"""
    config = await db.rate_limit_configs.find_one({"api_key": api_key}, {"_id": 0})
    if config:
        if isinstance(config['created_at'], str):
            config['created_at'] = datetime.fromisoformat(config['created_at'])
        return RateLimitConfig(**config)
    return None

async def check_rate_limit(api_key: str, endpoint: str) -> tuple[bool, int, str]:
    """Check if request is allowed based on rate limit configuration"""
    config = await get_rate_limit_config(api_key)
    
    if not config:
        # No rate limit configured, allow request
        return True, 999999, "no_limit"
    
    algorithm = config.algorithm
    key = f"{api_key}:{algorithm}"
    
    allowed = False
    remaining = 0
    
    if algorithm == "token_bucket":
        if key not in token_buckets:
            refill_rate = config.max_requests / config.window_seconds
            token_buckets[key] = TokenBucket(config.max_requests, refill_rate)
        allowed = token_buckets[key].consume()
        remaining = token_buckets[key].get_remaining()
    
    elif algorithm == "leaky_bucket":
        if key not in leaky_buckets:
            leak_rate = config.max_requests / config.window_seconds
            leaky_buckets[key] = LeakyBucket(config.max_requests, leak_rate)
        allowed = leaky_buckets[key].add_request()
        remaining = leaky_buckets[key].get_remaining()
    
    elif algorithm == "fixed_window":
        if key not in fixed_windows:
            fixed_windows[key] = FixedWindow(config.max_requests, config.window_seconds)
        allowed = fixed_windows[key].allow_request()
        remaining = fixed_windows[key].get_remaining()
    
    elif algorithm == "sliding_window":
        if key not in sliding_windows:
            sliding_windows[key] = SlidingWindowCounter(config.max_requests, config.window_seconds)
        allowed = sliding_windows[key].allow_request()
        remaining = sliding_windows[key].get_remaining()
    
    # Log the request
    log = RequestLog(
        api_key=api_key,
        endpoint=endpoint,
        algorithm=algorithm,
        allowed=allowed,
        remaining_quota=remaining
    )
    log_dict = log.model_dump()
    log_dict['timestamp'] = log_dict['timestamp'].isoformat()
    await db.request_logs.insert_one(log_dict)
    
    return allowed, remaining, algorithm

# ==================== API ENDPOINTS ====================

@api_router.get("/")
async def root():
    return {"message": "Rate Limiter System API", "version": "1.0"}

@api_router.post("/api-keys", response_model=APIKeyModel)
async def create_api_key(input: APIKeyCreate):
    """Create a new API key"""
    api_key_obj = APIKeyModel(name=input.name)
    doc = api_key_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.api_keys.insert_one(doc)
    return api_key_obj

@api_router.get("/api-keys", response_model=List[APIKeyModel])
async def get_api_keys():
    """Get all API keys"""
    keys = await db.api_keys.find({}, {"_id": 0}).to_list(1000)
    for key in keys:
        if isinstance(key['created_at'], str):
            key['created_at'] = datetime.fromisoformat(key['created_at'])
    return keys

@api_router.post("/rate-limit-configs", response_model=RateLimitConfig)
async def create_rate_limit_config(input: RateLimitConfigCreate):
    """Create or update rate limit configuration"""
    # Check if API key exists
    api_key_doc = await db.api_keys.find_one({"api_key": input.api_key})
    if not api_key_doc:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Delete existing config for this API key if any
    await db.rate_limit_configs.delete_many({"api_key": input.api_key})
    
    config = RateLimitConfig(**input.model_dump())
    doc = config.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.rate_limit_configs.insert_one(doc)
    
    # Clear in-memory cache for this key
    for storage in [token_buckets, leaky_buckets, fixed_windows, sliding_windows]:
        keys_to_delete = [k for k in storage.keys() if k.startswith(input.api_key)]
        for k in keys_to_delete:
            del storage[k]
    
    return config

@api_router.get("/rate-limit-configs", response_model=List[RateLimitConfig])
async def get_rate_limit_configs():
    """Get all rate limit configurations"""
    configs = await db.rate_limit_configs.find({}, {"_id": 0}).to_list(1000)
    for config in configs:
        if isinstance(config['created_at'], str):
            config['created_at'] = datetime.fromisoformat(config['created_at'])
    return configs

@api_router.get("/protected/test")
async def protected_test_endpoint(api_key: str):
    """Test endpoint with rate limiting"""
    allowed, remaining, algorithm = await check_rate_limit(api_key, "/api/protected/test")
    
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "algorithm": algorithm,
                "remaining": remaining
            }
        )
    
    return {
        "success": True,
        "message": "Request allowed",
        "algorithm": algorithm,
        "remaining_quota": remaining,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@api_router.get("/analytics/summary")
async def get_analytics_summary(api_key: Optional[str] = None):
    """Get analytics summary"""
    query = {}
    if api_key:
        query["api_key"] = api_key
    
    total_requests = await db.request_logs.count_documents(query)
    allowed_requests = await db.request_logs.count_documents({**query, "allowed": True})
    blocked_requests = await db.request_logs.count_documents({**query, "allowed": False})
    
    # Get algorithm breakdown
    algorithm_stats = {}
    for algo in ["token_bucket", "leaky_bucket", "fixed_window", "sliding_window"]:
        algo_query = {**query, "algorithm": algo}
        total = await db.request_logs.count_documents(algo_query)
        allowed = await db.request_logs.count_documents({**algo_query, "allowed": True})
        blocked = await db.request_logs.count_documents({**algo_query, "allowed": False})
        algorithm_stats[algo] = {
            "total": total,
            "allowed": allowed,
            "blocked": blocked,
            "success_rate": round(allowed / total * 100, 2) if total > 0 else 0
        }
    
    return {
        "total_requests": total_requests,
        "allowed_requests": allowed_requests,
        "blocked_requests": blocked_requests,
        "success_rate": round(allowed_requests / total_requests * 100, 2) if total_requests > 0 else 0,
        "algorithm_stats": algorithm_stats
    }

@api_router.get("/analytics/recent-logs")
async def get_recent_logs(limit: int = 100, api_key: Optional[str] = None):
    """Get recent request logs"""
    query = {}
    if api_key:
        query["api_key"] = api_key
    
    logs = await db.request_logs.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    
    for log in logs:
        if isinstance(log['timestamp'], str):
            log['timestamp'] = datetime.fromisoformat(log['timestamp'])
    
    return logs

@api_router.post("/load-test")
async def run_load_test(test_request: LoadTestRequest):
    """Run load test against rate limiter"""
    api_key = test_request.api_key
    rps = test_request.requests_per_second
    duration = test_request.duration_seconds
    endpoint = test_request.endpoint
    
    # Verify API key exists
    api_key_doc = await db.api_keys.find_one({"api_key": api_key})
    if not api_key_doc:
        raise HTTPException(status_code=404, detail="API key not found")
    
    total_requests = rps * duration
    delay_between_requests = 1.0 / rps
    
    results = {
        "total_requests": total_requests,
        "allowed": 0,
        "blocked": 0,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "requests_per_second": rps,
        "duration_seconds": duration
    }
    
    start_time = time.time()
    
    for i in range(total_requests):
        allowed, remaining, algorithm = await check_rate_limit(api_key, endpoint)
        
        if allowed:
            results["allowed"] += 1
        else:
            results["blocked"] += 1
        
        # Sleep to maintain target RPS
        await asyncio.sleep(delay_between_requests)
        
        # Check if duration exceeded
        if time.time() - start_time > duration:
            break
    
    results["end_time"] = datetime.now(timezone.utc).isoformat()
    results["actual_duration"] = time.time() - start_time
    results["success_rate"] = round(results["allowed"] / total_requests * 100, 2) if total_requests > 0 else 0
    
    return results

@api_router.delete("/reset-stats")
async def reset_stats():
    """Reset all statistics and in-memory storage"""
    await db.request_logs.delete_many({})
    
    token_buckets.clear()
    leaky_buckets.clear()
    fixed_windows.clear()
    sliding_windows.clear()
    
    return {"message": "Statistics and rate limiters reset successfully"}

@api_router.get("/system-status")
async def get_system_status():
    """Get system status and active rate limiters"""
    total_api_keys = await db.api_keys.count_documents({})
    total_configs = await db.rate_limit_configs.count_documents({})
    total_logs = await db.request_logs.count_documents({})
    
    return {
        "status": "operational",
        "active_api_keys": total_api_keys,
        "active_configs": total_configs,
        "total_requests_logged": total_logs,
        "active_rate_limiters": {
            "token_bucket": len(token_buckets),
            "leaky_bucket": len(leaky_buckets),
            "fixed_window": len(fixed_windows),
            "sliding_window": len(sliding_windows)
        }
    }

# Include the router in the main app
app.include_router(api_router)



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()