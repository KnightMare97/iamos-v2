"""IAMOS Strategy Domain Service
Manages Flow A (Advanced Calendar Strategy Generation), delta database mapping,
selective slot regeneration, and atomic calendar slot swapping.
"""
import json
import logging
from typing import Dict, Any, List, Optional
import asyncpg
from redis.asyncio import Redis

from backend.shared.ai_router import AIRouter
from backend.shared.types import ContentItemState

logger = logging.getLogger("iamos.strategy.service")
ai_router = AIRouter()

# Stub representing our internal production LLM caller wrapper
async def _invoke_llm(model_config: Any, prompt: str, system: str = "") -> str:
    """Invokes the designated model provider from the AIRouter distribution."""
    # In production, this ties directly to our unified Google / OpenRouter client engine.
    pass

async def publish_strategy_event(redis: Redis, event_type: str, aggregate_id: str, client_id: str, payload: dict):
    """Utility to append an immutable event to the Redis event bus."""
    event_payload = {
        "event_type": event_type,
        "aggregate_id": str(aggregate_id),
        "aggregate_type": "Campaign",
        "client_id": str(client_id),
        "payload": json.dumps(payload),
        "triggered_by": "agent:strategy"
    }
    await redis.xadd("iamos:events", event_payload)


async def generate_monthly_calendar_backbone(
    db_pool: asyncpg.Pool, 
    redis: Redis, 
    campaign_id: str, 
    client_id: str, 
    month_context: str
) -> bool:
    """
    Executes Flow A: High-level Tier 3 Strategy Engine.
    Generates a full structured calendar mapping of narrative slots based on Client DNA.
    """
    async with db_pool.acquire() as conn:
        # 1. Fetch Client DNA context to feed the high-context prompt window
        client_query = """
            SELECT brand_voice, industry_vertical, target_audience
            FROM clients WHERE id = $1
        """
        client = await conn.fetchrow(client_query, client_id)
        if not client:
            logger.error(f"Client {client_id} context missing. Strategy generation aborted.")
            return False

        # 2. Route to Tier 3 AI (Gemini 1.5 Pro or DeepSeek V4 Pro) for complex ideation
        model_config = ai_router.route("strategy_generation", {"client_id": client_id})
        
        system_prompt = f"""
        You are the Head of Growth and Content Strategy for a premier Iranian digital marketing agency.
        Your task is to build a highly optimized, conversion-driven story calendar mapping.
        Brand Voice: {client['brand_voice']}
        Industry: {client['industry_vertical']}
        Audience Profile: {client['target_audience']}
        
        Generate content pillars structured for Persian social dynamics, holidays, and high-engagement hooks.
        Output MUST be a strict JSON array of slots. Do not include markdown wrappers outside the raw JSON block.
        Format example:
        [
            {{"day_number": 1, "visual_direction": "Brief concept desc", "pillar": "Educational", "notes": "RTL directive"}}
        ]
        """

        raw_response = await _invoke_llm(model_config, prompt=f"Generate 30 days calendar for: {month_context}", system=system_prompt)
        
        try:
            slots = json.loads(raw_response)
        except json.JSONDecodeError:
            logger.error(f"Tier 3 Strategy JSON extraction failed for Campaign {campaign_id}")
            return False

        # 3. Transactional Delta Mapping to Database
        async with conn.transaction():
            # Set the campaign to active deployment state
            await conn.execute(
                "UPDATE campaigns SET state = 'ACTIVE', updated_at = NOW() WHERE id = $1", 
                campaign_id
            )
            
            # Inject empty shell slots into content_items table for the granular pipeline
            for slot in slots:
                await conn.execute("""
                    INSERT INTO content_items 
                    (client_id, campaign_id, state, visual_direction, metadata, scheduled_at)
                    VALUES ($1, $2, $3, $4, $5, NOW() + (INTERVAL '1 day' * $6))
                """, 
                client_id, campaign_id, ContentItemState.PENDING, 
                slot['visual_direction'], json.dumps({"pillar": slot.get("pillar"), "notes": slot.get("notes")}),
                slot['day_number'])

        # 4. Notify Event Bus
        await publish_strategy_event(redis, "strategy.calendar.deployed", campaign_id, client_id, {"slots_count": len(slots)})
        return True


async def swap_calendar_slots(db_pool: asyncpg.Pool, client_id: str, item_id_1: str, item_id_2: str) -> bool:
    """
    Enforces Flow A List-View Flexibility Invariant.
    Atomics-level database swap of scheduled timestamps between two distinct content slots.
    """
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            # Lock both items inside the tenant boundary to prevent race conditions
            item1 = await conn.fetchrow("SELECT scheduled_at FROM content_items WHERE id = $1 AND client_id = $2 FOR UPDATE", item_id_1, client_id)
            item2 = await conn.fetchrow("SELECT scheduled_at FROM content_items WHERE id = $1 AND client_id = $2 FOR UPDATE", item_id_2, client_id)
            
            if not item1 or not item2:
                logger.warning(f"Failed to swap slots: One or both items do not exist under Client context.")
                return False
                
            # Perform atomic assignment swap
            await conn.execute("UPDATE content_items SET scheduled_at = $1, updated_at = NOW() WHERE id = $2", item2['scheduled_at'], item_id_1)
            await conn.execute("UPDATE content_items SET scheduled_at = $1, updated_at = NOW() WHERE id = $2", item1['scheduled_at'], item_id_2)
            
            logger.info(f"Successfully swapped execution slots: {item_id_1} <=> {item_id_2}")
            return True


async def trigger_selective_slot_regeneration(db_pool: asyncpg.Pool, redis: Redis, client_id: str, content_item_id: str, adjustments_note: str) -> bool:
    """
    Granular Revision Shield Execution.
    Regenerates a single failed or operator-rejected slot without breaking the rest of the calendar.
    """
    async with db_pool.acquire() as conn:
        # Enforce multi-tenancy check and lock row
        item = await conn.fetchrow("SELECT state, visual_direction FROM content_items WHERE id = $1 AND client_id = $2 FOR UPDATE", content_item_id, client_id)
        if not item:
            return False
            
        # Re-queue single slot into the Content Generation pipeline loop
        async with conn.transaction():
            await conn.execute("""
                UPDATE content_items 
                SET state = 'GENERATION_QUEUED', 
                    visual_direction = visual_direction || $1,
                    revision_count = revision_count + 1,
                    updated_at = NOW() 
                WHERE id = $2
            """, f" [Adjustment Override: {adjustments_note}]", content_item_id)
            
        # Push event to trigger the content app execution loop
        event_payload = {
            "event_type": "content.slot.regeneration_triggered",
            "aggregate_id": str(content_item_id),
            "aggregate_type": "ContentItem",
            "client_id": str(client_id),
            "payload": json.dumps({"adjustment": adjustments_note}),
            "triggered_by": "operator:override"
        }
        await redis.xadd("iamos:events", event_payload)
        logger.info(f"Selective isolation patch deployed for item slot: {content_item_id}")
        return True
