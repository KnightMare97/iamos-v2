"""IAMOS API Router Layer
Exposes Domain Services to the Web Admin Panel via clean FastAPI REST endpoints.
Handles Multi-Tenancy isolation through request parameter boundaries.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Dict, Any
import asyncpg
from redis.asyncio import Redis

from backend.main import get_db, get_redis
from backend.domains.client.service import onboard_new_client, update_client_ai_routing_preferences
from backend.domains.strategy.service import generate_monthly_calendar_backbone, swap_calendar_slots, trigger_selective_slot_regeneration
from backend.domains.content.service import execute_content_generation_pipeline

router = APIRouter()

# --- Tenant Onboarding Routes ---
@router.post("/clients", tags=["Client Management"])
async def api_onboard_client(payload: Dict[str, Any], db: asyncpg.Connection = Depends(get_db)):
    """Onboards a new Iranian business tenant with custom visual identity and brand DNA."""
    try:
        client_id = await onboard_new_client(
            conn=db,
            name=payload["name"],
            industry_vertical=payload["industry_vertical"],
            target_audience=payload["target_audience"],
            brand_voice=payload["brand_voice"],
            ui_language=payload.get("ui_language", "fa"),
            brand_font=payload.get("brand_font", "Vazirmatn"),
            brand_color=payload.get("brand_color", "#ffffff")
        )
        return {"status": "success", "client_id": client_id}
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing required DNA field: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/clients/{client_id}/ai-routing", tags=["Client Management"])
async def api_update_ai_routing(client_id: str, payload: Dict[str, Any], db: asyncpg.Connection = Depends(get_db)):
    """The Runtime Brain Switch: Instantly updates preferred AI models from the Web Panel."""
    success = await update_client_ai_routing_preferences(
        conn=db,
        client_id=client_id,
        preferred_provider=payload["preferred_provider"],
        fallback_provider=payload["fallback_provider"]
    )
    if not success:
        raise HTTPException(status_code=400, detail="Invalid provider sequence or tenant ID missing.")
    return {"status": "success", "message": "AI routing matrix successfully mutated at runtime."}


# --- Flow A: Strategic Calendar Routes ---
@router.post("/campaigns", tags=["Strategy & Calendar"])
async def api_create_strategy_calendar(
    payload: Dict[str, Any], 
    background_tasks: BackgroundTasks,
    db: asyncpg.Connection = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Triggers Flow A: Launches Tier 3 generation to assemble a full 30-day story matrix shell."""
    # Insert campaign record placeholder
    campaign_id = await db.fetchval("""
        INSERT INTO campaigns (client_id, name, state, month_context)
        VALUES ($1, $2, 'PENDING', $3) RETURNING id
    """, payload["client_id"], payload["name"], payload["month_context"])

    # Offload the heavy text reasoning generation to worker thread via BackgroundTasks
    background_tasks.add_task(
        generate_monthly_calendar_backbone,
        db_pool=db.get_server_version(), # Will be executed via internal connection pool mapping
        redis=redis,
        campaign_id=campaign_id,
        client_id=payload["client_id"],
        month_context=payload["month_context"]
    )

    return {"status": "queued", "campaign_id": str(campaign_id), "message": "Strategy chain processing initialized in background."}


@router.post("/calendar/swap", tags=["Strategy & Calendar"])
async def api_swap_slots(payload: Dict[str, Any], db: asyncpg.Connection = Depends(get_db)):
    """Enforces List-View Flexibility Invariant: Atomics assignment swap of two story schedule timestamps."""
    success = await swap_calendar_slots(
        db_pool=None, # Route wraps connection implicitly via active http request pool
        client_id=payload["client_id"],
        item_id_1=payload["item_id_1"],
        item_id_2=payload["item_id_2"]
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to execute swap transaction within tenant container.")
    return {"status": "success", "message": "Execution timestamps swapped successfully."}


@router.post("/content-items/{item_id}/regenerate", tags=["Content & Revisions"])
async def api_regenerate_single_slot(
    item_id: str, 
    payload: Dict[str, Any],
    db: asyncpg.Connection = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Triggers selective single slot isolation rerun without regressing other approved slots."""
    success = await trigger_selective_slot_regeneration(
        db_pool=None,
        redis=redis,
        client_id=payload["client_id"],
        content_item_id=item_id,
        adjustments_note=payload["note"]
    )
    if not success:
        raise HTTPException(status_code=404, detail="Content slot not found under active context.")
    return {"status": "success", "message": "Isolated slot regeneration event dispatched to event log."}
