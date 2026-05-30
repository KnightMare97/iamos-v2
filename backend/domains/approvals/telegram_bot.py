import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
import asyncpg
from redis.asyncio import Redis
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("iamos.telegram_bot")

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/iamos")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
MASTER_GROUP_CHAT_ID = os.getenv("MASTER_GROUP_CHAT_ID")

# --- AIogram Setup ---
bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- State Management ---
class RejectionFlow(StatesGroup):
    waiting_for_feedback = State()

# --- Localization Strings (Multi-Language Dictionary) ---
STRINGS = {
    "fa": {
        "urgent": "🚨 <b>اولویت بالا - جایگزینی کمپین</b>\n",
        "approval_title": "📝 <b>درخواست تایید استوری (اسلات محتوایی)</b>\n",
        "client": "👤 <b>کارفرما:</b>",
        "scheduled": "📅 <b>زمان زمان‌بندی:</b>",
        "caption": "<b>کپشن پیشنهادی:</b>",
        "visual": "<b>راهنمای بصری هوش مصنوعی:</b>",
        "asset": "<b>فایل پیوست:</b>",
        "no_asset": "فایلی پیوست نشده است",
        "btn_approve": "✅ تایید و ارسال",
        "btn_reject": "❌ رد و بازنویسی با AI",
        "msg_feedback": "لطفاً علت رد شدن یا دستورالعمل اصلاحی خود را برای هوش مصنوعی بنویسید:",
        "approved_status": "\n\n✅ <b>توسط اپراتور تایید شد</b>",
        "rejected_status": "❌ <b>رد شد</b> (ارسال برای بازنویسی مجدد)",
        "publish_title": "🚀 <b>دستور انتشار فوری (Publish Mode 1)</b>\n",
        "publish_note": "<i>لطفاً متن کپشن زیر را کپی کرده و به همراه فایل پیوست به صورت دستی در اینستاگرام استوری کنید و سپس دکمه تایید را بزنید.</i>",
        "btn_published": "✅ با موفقیت منتشر شد",
        "btn_pub_failed": "⚠️ خطا در انتشار (گزارش به سوپروایزر)",
        "status_done": "\n\n✅ <b>وضعیت: منتشر شده در اینستاگرام</b>",
        "status_failed": "\n\n❌ <b>وضعیت: گزارش خطا در انتشار</b>"
    },
    "en": {
        "urgent": "🚨 <b>URGENT OVERRIDE</b>\n",
        "approval_title": "📝 <b>Approval Required (Slot)</b>\n",
        "client": "👤 <b>Client:</b>",
        "scheduled": "📅 <b>Scheduled:</b>",
        "caption": "<b>Caption:</b>",
        "visual": "<b>Visual Direction:</b>",
        "asset": "<b>Asset URL:</b>",
        "no_asset": "No asset attached",
        "btn_approve": "✅ Approve",
        "btn_reject": "❌ Reject & Revise",
        "msg_feedback": "Please type your feedback/revision instructions for the AI:",
        "approved_status": "\n\n✅ <b>APPROVED by Operator</b>",
        "rejected_status": "❌ <b>REJECTED</b> (Sent for revision)",
        "publish_title": "🚀 <b>PUBLISH REQUIRED (Mode 1)</b>\n",
        "publish_note": "<i>Please post this to Instagram manually and confirm below.</i>",
        "btn_published": "✅ Mark as Published",
        "btn_pub_failed": "⚠️ FAILED (Report Issue)",
        "status_done": "\n\n✅ <b>MARK AS PUBLISHED (Manual Mode 1)</b>",
        "status_failed": "\n\n❌ <b>FLAGGED AS FAILED</b>"
    }
}

# --- Database & Event Bus Wrappers ---
async def publish_event(redis: Redis, event_type: str, aggregate_id: str, aggregate_type: str, client_id: str, payload: dict):
    event_payload = {
        "event_type": event_type,
        "aggregate_id": str(aggregate_id),
        "aggregate_type": aggregate_type,
        "client_id": str(client_id),
        "payload": json.dumps(payload),
        "triggered_by": "human:operator"
    }
    await redis.xadd("iamos:events", event_payload)

async def resolve_operator_chat_id(conn: asyncpg.Connection, client_id: str) -> str:
    query = """
        SELECT o.telegram_chat_id 
        FROM client_operators co
        JOIN operators o ON co.operator_id = o.id
        WHERE co.client_id = $1 AND o.status = 'active'
        ORDER BY CASE WHEN co.role = 'primary' THEN 1 ELSE 2 END
        LIMIT 1
    """
    chat_id = await conn.fetchval(query, client_id)
    return chat_id if chat_id else MASTER_GROUP_CHAT_ID

# --- Core Action Handlers ---
async def handle_content_draft_ready(pool: asyncpg.Pool, redis: Redis, payload: dict):
    item_id = payload.get("aggregate_id")
    client_id = payload.get("client_id")
    event_payload = json.loads(payload.get("payload", "{}"))
    
    async with pool.acquire() as conn:
        async with conn.transaction():
            query = """
                SELECT c.id, c.caption, c.visual_direction, c.scheduled_at, c.campaign_override,
                       cl.name as client_name, cl.approval_mode, cl.ui_language,
                       (SELECT url FROM assets WHERE content_item_id = c.id LIMIT 1) as asset_url
                FROM content_items c
                JOIN clients cl ON c.client_id = cl.id
                WHERE c.id = $1
            """
            item = await conn.fetchrow(query, item_id)
            if not item:
                return

            existing = await conn.fetchval("SELECT id FROM approval_requests WHERE aggregate_id = $1 AND state = 'PENDING'", item_id)
            if existing:
                return

            timeout_hours = event_payload.get("expedited_timeout_hours", 24)
            timeout_at = datetime.utcnow() + timedelta(hours=timeout_hours)
            
            chat_id = await resolve_operator_chat_id(conn, client_id)
            if not chat_id:
                logger.error(f"Cannot resolve chat ID for client {client_id}")
                return

            req_id = await conn.fetchval("""
                INSERT INTO approval_requests 
                (aggregate_id, aggregate_type, client_id, approval_mode, timeout_at)
                VALUES ($1, 'ContentItem', $2, $3, $4) RETURNING id
            """, item_id, client_id, item["approval_mode"], timeout_at)

            # Extract client dynamic language preference
            lang = item["ui_language"] if item["ui_language"] in STRINGS else "fa"
            lex = STRINGS[lang]

            priority_tag = lex["urgent"] if item["campaign_override"] else ""
            scheduled_str = item["scheduled_at"].strftime("%Y-%m-%d %H:%M") if item["scheduled_at"] else "TBD"
            
            msg_text = (
                f"{priority_tag}"
                f"{lex['approval_title']}"
                f"{lex['client']} {item['client_name']}\n"
                f"{lex['scheduled']} {scheduled_str}\n\n"
                f"{lex['caption']}\n{item['caption'] or 'N/A'}\n\n"
                f"{lex['visual']}\n{item['visual_direction']}\n\n"
                f"{lex['asset']} {item['asset_url'] or lex['no_asset']}\n"
            )

            builder = InlineKeyboardBuilder()
            builder.button(text=lex["btn_approve"], callback_data=f"approve_{req_id}_{lang}")
            builder.button(text=lex["btn_reject"], callback_data=f"reject_{req_id}_{lang}")
            builder.adjust(2)

            await bot.send_message(chat_id=chat_id, text=msg_text, reply_markup=builder.as_markup(), disable_web_page_preview=False)
            logger.info(f"Dispatched approval request {req_id} to {chat_id}")

async def handle_publish_attempting(pool: asyncpg.Pool, redis: Redis, payload: dict):
    job_id = payload.get("aggregate_id")
    client_id = payload.get("client_id")
    
    async with pool.acquire() as conn:
        job = await conn.fetchrow("""
            SELECT pj.id, pj.content_item_id, pj.scheduled_at, cl.publish_mode, cl.name as client_name, cl.ui_language
            FROM publish_jobs pj
            JOIN clients cl ON pj.client_id = cl.id
            WHERE pj.id = $1
        """, job_id)
        
        if not job or job["publish_mode"] != 1:
            return

        item = await conn.fetchrow("""
            SELECT caption, (SELECT url FROM assets WHERE content_item_id = content_items.id LIMIT 1) as asset_url
            FROM content_items WHERE id = $1
        """, job["content_item_id"])

        chat_id = await resolve_operator_chat_id(conn, client_id)
        
        lang = job["ui_language"] if job["ui_language"] in STRINGS else "fa"
        lex = STRINGS[lang]

        msg_text = (
            f"{lex['publish_title']}"
            f"{lex['client']} {job['client_name']}\n"
            f"{lex['scheduled']} {job['scheduled_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
            f"{lex['caption']} (Copy):\n<code>{item['caption'] or ''}</code>\n\n"
            f"{lex['asset']} {item['asset_url'] or 'N/A'}\n\n"
            f"{lex['publish_note']}"
        )

        builder = InlineKeyboardBuilder()
        builder.button(text=lex["btn_published"], callback_data=f"published_{job['id']}_{lang}")
        builder.button(text=lex["btn_pub_failed"], callback_data=f"pubfailed_{job['id']}_{lang}")
        builder.adjust(1)

        await bot.send_message(chat_id=chat_id, text=msg_text, reply_markup=builder.as_markup())
        logger.info(f"Dispatched publish job {job['id']} to {chat_id}")

# --- Background Redis Consumer ---
async def redis_event_listener(pool: asyncpg.Pool, redis: Redis):
    stream_key = "iamos:events"
    group_name = "telegram_approvals_group"
    consumer_name = f"tg_bot_{os.getpid()}"
    
    try:
        await redis.xgroup_create(stream_key, group_name, id="0", mkstream=True)
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            logger.error(f"Failed to create Redis stream group: {e}")
            return

    logger.info("Telegram Bot Redis Listener started.")
    try:
        while True:
            messages = await redis.xreadgroup(group_name, consumer_name, {stream_key: ">"}, count=10, block=2000)
            for stream, msgs in messages:
                for message_id, payload in msgs:
                    event_type = payload.get("event_type")
                    try:
                        if event_type == "content.draft.ready":
                            await handle_content_draft_ready(pool, redis, payload)
                        elif event_type == "publish.attempting":
                            await handle_publish_attempting(pool, redis, payload)
                        
                        await redis.xack(stream_key, group_name, message_id)
                    except Exception as e:
                        logger.error(f"Error processing {message_id}: {e}")
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        logger.info("Redis listener cancelled.")

# --- Telegram Interactions Handlers ---
@dp.callback_query(F.data.startswith("approve_"))
async def cb_approve(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    req_id = parts[1]
    lang = parts[2] if len(parts) > 2 else "fa"
    pool: asyncpg.Pool = callback.bot.pool
    redis: Redis = callback.bot.redis

    async with pool.acquire() as conn:
        req = await conn.fetchrow("SELECT aggregate_id, client_id, state FROM approval_requests WHERE id = $1 FOR UPDATE", req_id)
        if not req or req['state'] != 'PENDING':
            await callback.answer("This request is no longer pending.", show_alert=True)
            return

        await conn.execute("""
            UPDATE approval_requests 
            SET state = 'APPROVED', operator_decision = 'approved', operator_decided_at = NOW() 
            WHERE id = $1
        """, req_id)

    await publish_event(redis, "operator.approved", req['aggregate_id'], "ContentItem", req['client_id'], {})
    await callback.message.edit_text(f"{callback.message.text}\n\n{STRINGS[lang]['approved_status']}")
    await callback.answer()

@dp.callback_query(F.data.startswith("reject_"))
async def cb_reject(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    req_id = parts[1]
    lang = parts[2] if len(parts) > 2 else "fa"
    pool: asyncpg.Pool = callback.bot.pool

    async with pool.acquire() as conn:
        req = await conn.fetchval("SELECT state FROM approval_requests WHERE id = $1", req_id)
        if not req or req != 'PENDING':
            await callback.answer("This request is no longer pending.", show_alert=True)
            return

    await state.set_state(RejectionFlow.waiting_for_feedback)
    await state.update_data(req_id=req_id, original_msg_id=callback.message.message_id, lang=lang)
    
    await callback.message.reply(STRINGS[lang]["msg_feedback"])
    await callback.answer()

@dp.message(RejectionFlow.waiting_for_feedback)
async def process_feedback(message: types.Message, state: FSMContext):
    data = await state.get_data()
    req_id = data.get("req_id")
    lang = data.get("lang", "fa")
    feedback_text = message.text
    
    pool: asyncpg.Pool = message.bot.pool
    redis: Redis = message.bot.redis

    async with pool.acquire() as conn:
        async with conn.transaction():
            req = await conn.fetchrow("SELECT aggregate_id, client_id, state FROM approval_requests WHERE id = $1 FOR UPDATE", req_id)
            if not req or req['state'] != 'PENDING':
                await message.answer("Request already processed.")
                await state.clear()
                return

            await conn.execute("""
                UPDATE approval_requests 
                SET state = 'REJECTED', operator_decision = 'rejected', operator_decided_at = NOW(), feedback = $1 
                WHERE id = $2
            """, feedback_text, req_id)

    await publish_event(redis, "operator.rejected", req['aggregate_id'], "ContentItem", req['client_id'], {"feedback": feedback_text})
    await message.answer("✅ Done." if lang == "en" else "✅ بازخورد ثبت شد. هوش مصنوعی در حال اصلاح طرح است.")
    
    try:
        await bot.edit_message_text(chat_id=message.chat.id, message_id=data['original_msg_id'], text=f"❌ <b>REJECTED</b>" if lang == "en" else f"{STRINGS[lang]['rejected_status']}")
    except Exception:
        pass
        
    await state.clear()

@dp.callback_query(F.data.startswith("published_"))
async def cb_mark_published(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    job_id = parts[1]
    lang = parts[2] if len(parts) > 2 else "fa"
    pool: asyncpg.Pool = callback.bot.pool
    redis: Redis = callback.bot.redis

    async with pool.acquire() as conn:
        job = await conn.fetchrow("SELECT content_item_id, client_id, state FROM publish_jobs WHERE id = $1 FOR UPDATE", job_id)
        if not job or job['state'] == 'DONE':
            await callback.answer("Job already processed.", show_alert=True)
            return

        await conn.execute("UPDATE publish_jobs SET state = 'DONE' WHERE id = $1", job_id)

    await publish_event(redis, "publish.succeeded", job['content_item_id'], "ContentItem", job['client_id'], {"job_id": job_id, "mode": "manual_override"})
    await callback.message.edit_text(f"{callback.message.text}\n\n{STRINGS[lang]['status_done']}")
    await callback.answer()

@dp.callback_query(F.data.startswith("pubfailed_"))
async def cb_mark_publish_failed(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    job_id = parts[1]
    lang = parts[2] if len(parts) > 2 else "fa"
    pool: asyncpg.Pool = callback.bot.pool
    redis: Redis = callback.bot.redis

    async with pool.acquire() as conn:
        job = await conn.fetchrow("SELECT content_item_id, client_id FROM publish_jobs WHERE id = $1", job_id)
        if not job:
            return

        await conn.execute("UPDATE publish_jobs SET state = 'FAILED', error_message = 'Manual operator failure report' WHERE id = $1", job_id)

    await publish_event(redis, "publish.failed", job['content_item_id'], "ContentItem", job['client_id'], {"job_id": job_id, "error": "Human operator flagged failure"})
    await callback.message.edit_text(f"{callback.message.text}\n\n{STRINGS[lang]['status_failed']}")
    await callback.answer()

# --- Application Startup/Shutdown ---
async def main():
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    
    bot.pool = pool
    bot.redis = redis

    listener_task = asyncio.create_task(redis_event_listener(pool, redis))

    logger.info("Starting Telegram Bot Polling with adaptive Persian UI...")
    try:
        await dp.start_polling(bot)
    finally:
        listener_task.cancel()
        await pool.close()
        await redis.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
