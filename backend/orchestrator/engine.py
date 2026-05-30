"""IAMOS Orchestrator Engine
The central nervous system of the platform. Listens to immutable Redis Streams,
evaluates state boundaries via Postgres, and drives autonomous transitions.
"""
import os
import json
import logging
import asyncio
import asyncpg
from redis.asyncio import Redis

from backend.shared.types import ContentItemState, CampaignState, PublishJobState
from backend.shared.state_machines import (
    CONTENT_ITEM_TRANSITIONS,
    CAMPAIGN_TRANSITIONS,
    PUBLISH_JOB_TRANSITIONS,
    get_next_state
)

logger = logging.getLogger("iamos.orchestrator")

class OrchestratorEngine:
    def __init__(self, db_pool: asyncpg.Pool, redis_client: Redis):
        self.db_pool = db_pool
        self.redis = redis_client
        self.stream_key = "iamos:events"
        self.group_name = "orchestrator_engine"
        self.consumer_name = f"orchestrator_worker_{os.getpid()}"

    async def initialize_stream_group(self):
        """Ensures the append-only event stream and consumer group exist."""
        try:
            await self.redis.xgroup_create(self.stream_key, self.group_name, id="0", mkstream=True)
            logger.info(f"Consumer group '{self.group_name}' verified on stream '{self.stream_key}'.")
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                logger.error(f"Stream group initialization failure: {e}")
                raise

    async def start_loop(self):
        """Main immutable event processor loop."""
        await self.initialize_stream_group()
        logger.info("Orchestrator Engine successfully started and monitoring incoming events.")

        try:
            while True:
                # Block and fetch events from the stream
                events = await self.redis.xreadgroup(
                    self.group_name,
                    self.consumer_name,
                    {self.stream_key: ">"},
                    count=10,
                    block=2000
                )

                for stream, messages in events:
                    for message_id, payload in messages:
                        try:
                            await self.process_single_event(payload)
                            # Atomic Log Acknowledgment upon safe execution boundary
                            await self.redis.xack(self.stream_key, self.group_name, message_id)
                        except Exception as e:
                            logger.error(f"Critical transaction failure processing event {message_id}: {e}")
                            # In production, drop to a Dead Letter Queue (DLQ) here to prevent stream blockage

                await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            logger.info("Orchestrator Engine received graceful termination signal.")
        except Exception as e:
            logger.critical(f"Fatal unhandled exception in Orchestrator main thread: {e}")

    async def process_single_event(self, event_payload: dict):
        """Routes and executes transition logic based on Event Catalog invariants."""
        event_type = event_payload.get("event_type")
        aggregate_id = event_payload.get("aggregate_id")
        aggregate_type = event_payload.get("aggregate_type")
        client_id = event_payload.get("client_id")
        
        if not event_type or not aggregate_id or not aggregate_type:
            logger.warning(f"Malformed event intercepted and skipped: {event_payload}")
            return

        logger.info(f"Processing '{event_type}' for {aggregate_type} [{aggregate_id}] under Client {client_id}")

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # Route matching aggregate domains to their state validation boundaries
                if aggregate_type == "ContentItem":
                    await self.handle_content_item_transition(conn, aggregate_id, event_type, client_id)
                elif aggregate_type == "Campaign":
                    await self.handle_campaign_transition(conn, aggregate_id, event_type, client_id)
                elif aggregate_type == "PublishJob":
                    await self.handle_publish_job_transition(conn, aggregate_id, event_type, client_id)
                else:
                    logger.debug(f"Unhandled aggregate boundary type: {aggregate_type}")

    async def handle_content_item_transition(self, conn, item_id: str, event_type: str, client_id: str):
        """Enforces Granular State Machine for individual Story slots safely."""
        # Load current state from the isolated client database row
        row = await conn.fetchrow("SELECT state, revision_count FROM content_items WHERE id = $1 AND client_id = $2 FOR UPDATE", item_id, client_id)
        if not row:
            logger.error(f"ContentItem {item_id} not found under Client context. Aborting transition.")
            return

        current_state = row["state"]
        transition = get_next_state(CONTENT_ITEM_TRANSITIONS, current_state, event_type)
        
        if not transition:
            logger.debug(f"No valid state transition registered for ContentItem from '{current_state}' via '{event_type}'. Skipped.")
            return

        next_state = transition["to"]
        
        # Enforce Guard: Check System Max Revisions to prevent loops
        if next_state == ContentItemState.ESCALATED and row["revision_count"] >= 3:
            logger.warning(f"ContentItem {item_id} hit Max Revisions threshold. Escalating to supervisor.")

        # Execute atomic update transaction block
        await conn.execute(
            "UPDATE content_items SET state = $1, updated_at = NOW() WHERE id = $2",
            next_state, item_id
        )
        logger.info(f"ContentItem {item_id} advanced status: {current_state} -> {next_state}")
        await self.emit_system_event(event_type=f"content.state.{next_state.lower()}", aggregate_id=item_id, aggregate_type="ContentItem", client_id=client_id)

    async def handle_campaign_transition(self, conn, campaign_id: str, event_type: str, client_id: str):
        """Handles Monthly/Weekly strategy calendar state escalations."""
        row = await conn.fetchrow("SELECT state FROM campaigns WHERE id = $1 AND client_id = $2 FOR UPDATE", campaign_id, client_id)
        if not row:
            return

        current_state = row["state"]
        transition = get_next_state(CAMPAIGN_TRANSITIONS, current_state, event_type)
        
        if not transition:
            return

        next_state = transition["to"]
        await conn.execute("UPDATE campaigns SET state = $1, updated_at = NOW() WHERE id = $2", next_state, campaign_id)
        logger.info(f"Campaign {campaign_id} advanced status: {current_state} -> {next_state}")
        await self.emit_system_event(event_type=f"strategy.state.{next_state.lower()}", aggregate_id=campaign_id, aggregate_type="Campaign", client_id=client_id)

    async def handle_publish_job_transition(self, conn, job_id: str, event_type: str, client_id: str):
        """Enforces safe Publish Job profiles without leaking thread blocks."""
        row = await conn.fetchrow("SELECT state FROM publish_jobs WHERE id = $1 AND client_id = $2 FOR UPDATE", job_id, client_id)
        if not row:
            return

        current_state = row["state"]
        transition = get_next_state(PUBLISH_JOB_TRANSITIONS, current_state, event_type)
        
        if not transition:
            return

        next_state = transition["to"]
        await conn.execute("UPDATE publish_jobs SET state = $1, updated_at = NOW() WHERE id = $2", next_state, job_id)
        logger.info(f"PublishJob {job_id} advanced status: {current_state} -> {next_state}")
        await self.emit_system_event(event_type=f"publish.state.{next_state.lower()}", aggregate_id=job_id, aggregate_type="PublishJob", client_id=client_id)

    async def emit_system_event(self, event_type: str, aggregate_id: str, aggregate_type: str, client_id: str):
        """Appends downstream reactive triggers back to the Redis Event Bus."""
        event_payload = {
            "event_type": event_type,
            "aggregate_id": aggregate_id,
            "aggregate_type": aggregate_type,
            "client_id": client_id,
            "payload": json.dumps({"source": "orchestrator_engine_dispatch"}),
            "triggered_by": "agent:orchestrator"
        }
        await self.redis.xadd(self.stream_key, event_payload)

if __name__ == "__main__":
    # Internal runner configuration block for independent docker daemon staging
    async def main():
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/iamos")
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        
        pool = await asyncpg.create_pool(dsn=db_url, min_size=2, max_size=10)
        redis = Redis.from_url(redis_url, decode_responses=True)
        
        engine = OrchestratorEngine(pool, redis)
        await engine.start_loop()

    asyncio.run(main())
