import os
import json
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable

from fastapi import FastAPI, HTTPException, Response, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from redis.asyncio import Redis

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("iamos.core")

# --- Global Connection Pools ---
db_pool: asyncpg.Pool = None
redis_client: Redis = None
orchestrator_task: asyncio.Task = None

# --- Redis Streams Orchestrator Event Loop ---
async def orchestrator_event_loop(redis: Redis):
    """
    Core IAMOS Orchestrator worker loop.
    Monitors the Redis event stream, coordinates state machine transitions,
    and dispatches execution boundaries. 
    """
    stream_key = "iamos:events"
    group_name = "orchestrator_engine"
    consumer_name = f"orchestrator_worker_{os.getpid()}"
    
    try:
        await redis.xgroup_create(stream_key, group_name, id="0", mkstream=True)
        logger.info(f"Initialized Redis Stream Group: {group_name} on {stream_key}")
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            logger.error(f"Failed to create Redis stream group: {e}")
            return

    logger.info("IAMOS Orchestrator Event Loop actively listening.")
    
    try:
        while True:
            # Block and wait for new events
            messages = await redis.xreadgroup(
                group_name,
                consumer_name,
                {stream_key: ">"},
                count=20,
                block=5000
            )
            
            for stream, msgs in messages:
                for message_id, payload in msgs:
                    event_type = payload.get("event_type")
                    aggregate_id = payload.get("aggregate_id")
                    
                    logger.info(f"Orchestrator received {event_type} for {aggregate_id} (ID: {message_id})")
                    
                    try:
                        # Engine transition dispatch would be invoked here
                        # engine.dispatch_event(payload)
                        
                        # Atomic Log Acknowledgment
                        await redis.xack(stream_key, group_name, message_id)
                    except Exception as e:
                        logger.error(f"Failed to process event {message_id}: {e}")
                        
            await asyncio.sleep(0.05)
            
    except asyncio.CancelledError:
        logger.info("Orchestrator Event Loop terminated gracefully.")
    except Exception as e:
        logger.critical(f"Fatal error in Orchestrator Event Loop: {e}")

# --- Application Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, redis_client, orchestrator_task
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/iamos")
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    try:
        # 1. Establish PostgreSQL Transactional Pool
        db_pool = await asyncpg.create_pool(
            dsn=db_url, 
            min_size=5, 
            max_size=30,
            command_timeout=60
        )
        logger.info("PostgreSQL connection pool established.")
        
        # 2. Establish Redis Event Bus Connection
        redis_client = Redis.from_url(redis_url, decode_responses=True)
        await redis_client.ping()
        logger.info("Redis connection established.")
        
        # 3. Spawn Orchestrator
        orchestrator_task = asyncio.create_task(orchestrator_event_loop(redis_client))
        
        yield
        
    finally:
        # Graceful Teardown
        if orchestrator_task:
            orchestrator_task.cancel()
            try:
                await orchestrator_task
            except asyncio.CancelledError:
                pass
                
        if db_pool:
            await db_pool.close()
            logger.info("PostgreSQL pool closed.")
            
        if redis_client:
            await redis_client.close()
            logger.info("Redis connection closed.")

# --- FastAPI Initialization ---
app = FastAPI(
    title="IAMOS (Iranian AI Media Operating System)",
    description="Multi-tenant, scalable, AI-native media OS optimized for Iranian businesses.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependencies ---
async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """Provide a transactional database connection to endpoints."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    async with db_pool.acquire() as connection:
        yield connection

async def get_redis() -> Redis:
    """Provide Redis connection for appending events to the bus."""
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis client not initialized")
    return redis_client

# --- Core Infrastructure Routes ---
@app.get("/health", tags=["Infrastructure"])
async def health_check(db: asyncpg.Connection = Depends(get_db)):
    """Liveness & Readiness probe verifying Postgres and Redis health."""
    try:
        await db.execute("SELECT 1")
        redis_ping = await redis_client.ping()
        return {
            "status": "healthy",
            "postgres": "connected",
            "redis": "connected" if redis_ping else "unreachable"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service Unavailable")

# --- Assembly Layer Endpoint (RTL/Persian Graphics) ---
@app.get("/content-items/{item_id}/preview", tags=["Assembly Layer"])
async def generate_content_preview(item_id: str, db: asyncpg.Connection = Depends(get_db)):
    """
    Server-side HTML/CSS canvas rendering.
    Generates a headless screenshot with absolute `direction: rtl` and custom Iranian fonts.
    Returns a high-quality PNG buffer without relying on AI image generators for text.
    """
    query = """
        SELECT c.caption, a.url as bg_url, cl.brand_font, cl.brand_color
        FROM content_items c
        JOIN clients cl ON c.client_id = cl.id
        LEFT JOIN assets a ON a.content_item_id = c.id AND a.type IN ('photo', 'ai_generated')
        WHERE c.id = $1
        LIMIT 1
    """
    
    try:
        record = await db.fetchrow(query, item_id)
        if not record:
            raise HTTPException(status_code=404, detail="Content item or asset data not found")
            
        caption = record['caption'] or ""
        bg_url = record['bg_url'] or "https://via.placeholder.com/1080x1920/222222/FFFFFF/?text=No+Background+Asset"
        brand_font = record['brand_font'] or "sans-serif"
        brand_color = record['brand_color'] or "#ffffff"
        
        # Strictly structured RTL template for Iranian visual compliance
        html_content = f"""
        <!DOCTYPE html>
        <html lang="fa" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <style>
                @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.0.0/Vazirmatn-font-face.css');
                body, html {{
                    margin: 0; padding: 0; width: 1080px; height: 1920px;
                    overflow: hidden; background-color: #000;
                }}
                .canvas {{
                    position: relative; width: 1080px; height: 1920px;
                    background-image: url('{bg_url}');
                    background-size: cover; background-position: center;
                }}
                .gradient-shield {{
                    position: absolute; bottom: 0; left: 0; width: 100%; height: 55%;
                    background: linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 100%);
                }}
                .typography-layer {{
                    position: absolute; bottom: 180px; left: 80px; right: 80px;
                    font-family: '{brand_font}', 'Vazirmatn', Tahoma, sans-serif;
                    font-size: 54px; color: {brand_color}; line-height: 1.6;
                    text-align: right; text-shadow: 2px 4px 12px rgba(0,0,0,0.8);
                    direction: rtl; word-wrap: break-word;
                }}
            </style>
        </head>
        <body>
            <div class="canvas">
                <div class="gradient-shield"></div>
                <div class="typography-layer">{caption}</div>
            </div>
        </body>
        </html>
        """

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("Playwright package missing. Required for HTML->PNG assembly.")
            raise HTTPException(status_code=501, detail="Assembly engine dependencies not installed.")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1080, "height": 1920})
            await page.set_content(html_content, wait_until="networkidle")
            png_buffer = await page.screenshot(type="png", full_page=True)
            await browser.close()
            
        return Response(content=png_buffer, media_type="image/png")
        
    except asyncpg.PostgresError as e:
        logger.error(f"PostgreSQL state failure during canvas rendering: {e}")
        raise HTTPException(status_code=500, detail="Database transaction failed")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Fatal error generating canvas preview: {e}")
        raise HTTPException(status_code=500, detail="Assembly layer rendering failure")

# --- Event Bus Publisher Utility ---
async def publish_event(redis: Redis, event_type: str, aggregate_id: str, aggregate_type: str, client_id: str, payload: dict, triggered_by: str):
    """
    Appends an immutable event to the Redis Stream event bus.
    Ensures architectural invariants (Event log is append-only).
    """
    event_payload = {
        "event_type": event_type,
        "aggregate_id": aggregate_id,
        "aggregate_type": aggregate_type,
        "client_id": client_id,
        "payload": json.dumps(payload),
        "triggered_by": triggered_by
    }
    await redis.xadd("iamos:events", event_payload)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
