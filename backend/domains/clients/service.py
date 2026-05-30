"""IAMOS Client Domain Service
Handles tenant onboarding, client brand DNA updates, supervisor notes injection,
and dynamic AI provider preferences management for runtime routing isolation.
"""
import json
import logging
from typing import Dict, Any, List, Optional
import asyncpg

logger = logging.getLogger("iamos.client.service")

async def onboard_new_client(
    conn: asyncpg.Connection,
    name: str,
    industry_vertical: str,
    target_audience: str,
    brand_voice: str,
    ui_language: str = "fa",
    brand_font: str = "Vazirmatn",
    brand_color: str = "#ffffff"
) -> str:
    """
    Onboards a new business tenant into the multi-tenant architecture.
    Sets default fallback AI providers and establishes baseline visual brand identity.
    """
    query = """
        INSERT INTO clients 
        (name, industry_vertical, target_audience, brand_voice, ui_language, brand_font, brand_color, preferred_provider, fallback_provider, status)
        VALUES ($1, $2, $3, $4, $5, $6, $7, 'google', 'openrouter', 'active')
        RETURNING id
    """
    try:
        client_id = await conn.fetchval(
            query, name, industry_vertical, target_audience, brand_voice, ui_language, brand_font, brand_color
        )
        logger.info(f"Successfully onboarded tenant: '{name}' with ID: {client_id}")
        
        # Initialize default asset content configuration to manual/raw placeholder
        await conn.execute(
            "INSERT INTO client_content_type_config (client_id, asset_source) VALUES ($1, 'raw_upload')", 
            client_id
        )
        return str(client_id)
    except asyncpg.PostgresError as e:
        logger.error(f"PostgreSQL failure onboarding new client '{name}': {e}")
        raise


async def update_client_ai_routing_preferences(
    conn: asyncpg.Connection,
    client_id: str,
    preferred_provider: str,
    fallback_provider: str
) -> bool:
    """
    The Ultimate Brain Switch.
    Dynamically re-routes a client's AI traffic at runtime via database state update.
    """
    query = """
        UPDATE clients 
        SET preferred_provider = $1, fallback_provider = $2, updated_at = NOW() 
        WHERE id = $3
    """
    valid_providers = ["google", "openrouter", "anthropic", "openai", "xai"]
    if preferred_provider.lower() not in valid_providers or fallback_provider.lower() not in valid_providers:
        logger.error(f"Invalid provider assignment attempted for client {client_id}")
        return False

    result = await conn.execute(query, preferred_provider.lower(), fallback_provider.lower(), client_id)
    if result == "UPDATE 1":
        logger.info(f"Dynamic Switch Engaged for Client {client_id}: Primary='{preferred_provider}', Fallback='{fallback_provider}'")
        return True
    return False


async def fetch_client_runtime_ai_context(conn: asyncpg.Connection, client_id: str) -> Dict[str, Any]:
    """
    Extracts the isolated Client DNA context and configuration metadata.
    This dict is directly injected into the AIRouter.route method at execution runtime.
    """
    query = """
        SELECT id, brand_voice, ui_language, preferred_provider, fallback_provider
        FROM clients WHERE id = $1 AND status = 'active'
    """
    row = await conn.fetchrow(query, client_id)
    if not row:
        return {"preferred_provider": "google", "fallback_provider": "openrouter"}
        
    return {
        "client_id": str(row["id"]),
        "brand_voice": row["brand_voice"],
        "ui_language": row["ui_language"],
        "preferred_provider": row["preferred_provider"],
        "fallback_provider": row["fallback_provider"]
    }


async def add_supervisor_note_to_client(conn: asyncpg.Connection, client_id: str, note_text: str, author: str) -> bool:
    """
    Appends live operational notes from the content team lead or planning supervisor.
    These notes carry critical priority in the system prompt layer to tweak output context.
    """
    query = """
        INSERT INTO client_notes (client_id, note_text, author, created_at)
        VALUES ($1, $2, $3, NOW())
    """
    try:
        await conn.execute(query, client_id, note_text, author)
        logger.info(f"New supervisor note added for client {client_id} by {author}")
        return True
    except asyncpg.PostgresError as e:
        logger.error(f"Failed to append supervisor note: {e}")
        return False
