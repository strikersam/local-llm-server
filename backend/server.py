from dotenv import load_dotenv
load_dotenv()

import os
import re
import json
import secrets
import bcrypt
import jwt
import httpx
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("llm-wiki")

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "llm_wiki_dashboard")
JWT_SECRET = os.environ.get("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@llmwiki.local")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "WikiAdmin2026!")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "emergent")
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
LANGFUSE_PK = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SK = os.environ.get("LANGFUSE_SECRET_KEY", "")
LANGFUSE_BASE = os.environ.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "")
NGROK_DOMAIN = os.environ.get("NGROK_DOMAIN", "")
NGROK_TOKEN = os.environ.get("NGROK_AUTHTOKEN", "")

app = FastAPI(title="LLM Wiki — Unified Platform", version="2.0.0")

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app_url = os.environ.get("APP_URL", "")
origins = [
    frontend_url,
    "http://localhost:3000",
]
if app_url:
    origins.append(app_url)
# Add the preview domain
preview_domain = os.environ.get("REACT_APP_BACKEND_URL", "")
if preview_domain:
    origins.append(preview_domain)
# Add common patterns
origins = list(set(o for o in origins if o))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Override CORS for credentialed requests
@app.middleware("http")
async def cors_fix(request: Request, call_next):
    response = await call_next(request)
    origin = request.headers.get("origin", "")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


# ─── Auth Helpers ───────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def create_access_token(user_id: str, email: str) -> str:
    return jwt.encode(
        {"sub": user_id, "email": email, "exp": datetime.now(timezone.utc) + timedelta(hours=24), "type": "access"},
        JWT_SECRET, algorithm=JWT_ALGORITHM,
    )

def create_refresh_token(user_id: str) -> str:
    return jwt.encode(
        {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"},
        JWT_SECRET, algorithm=JWT_ALGORITHM,
    )

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except (jwt.InvalidTokenError, Exception):
        raise HTTPException(status_code=401, detail="Invalid token")


# ─── Startup ────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.wiki_pages.create_index("slug", unique=True)
    await db.wiki_pages.create_index([("title", "text"), ("content", "text")])
    await db.sources.create_index("created_at")
    await db.activity_log.create_index("created_at")
    await db.chat_sessions.create_index("user_id")
    await db.providers.create_index("provider_id", unique=True)
    await db.api_keys.create_index("key_id", unique=True)
    await seed_admin()
    await seed_default_providers()
    log.info("LLM Wiki Unified Platform started — provider=%s", LLM_PROVIDER)


async def seed_admin():
    existing = await db.users.find_one({"email": ADMIN_EMAIL})
    if existing is None:
        await db.users.insert_one({
            "email": ADMIN_EMAIL, "password_hash": hash_password(ADMIN_PASSWORD),
            "name": "Admin", "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        log.info("Admin user seeded: %s", ADMIN_EMAIL)
    elif not verify_password(ADMIN_PASSWORD, existing["password_hash"]):
        await db.users.update_one({"email": ADMIN_EMAIL}, {"$set": {"password_hash": hash_password(ADMIN_PASSWORD)}})


async def seed_default_providers():
    defaults = [
        {
            "provider_id": "ollama-local",
            "name": "Ollama (Local)",
            "type": "ollama",
            "base_url": OLLAMA_BASE,
            "api_key": "",
            "default_model": "llama3.2",
            "is_default": LLM_PROVIDER != "emergent",
            "status": "configured",
        },
    ]
    if EMERGENT_KEY:
        defaults.append({
            "provider_id": "emergent-cloud",
            "name": "Emergent (Cloud)",
            "type": "openai-compatible",
            "base_url": "https://api.openai.com/v1",
            "api_key": EMERGENT_KEY,
            "default_model": "gpt-4o-mini",
            "is_default": LLM_PROVIDER == "emergent",
            "status": "configured",
        })
    for p in defaults:
        existing = await db.providers.find_one({"provider_id": p["provider_id"]})
        if not existing:
            p["created_at"] = datetime.now(timezone.utc).isoformat()
            await db.providers.insert_one(p)


# ─── Activity Logging ──────────────────────────────────────────────────────────

async def log_activity(category: str, message: str, user_id: str = None, meta: dict = None):
    await db.activity_log.insert_one({
        "category": category, "message": message, "user_id": user_id, "meta": meta or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


# ─── Auth Endpoints ─────────────────────────────────────────────────────────────

class LoginBody(BaseModel):
    email: str
    password: str

@app.post("/api/auth/login")
async def login(body: LoginBody):
    email = body.email.strip().lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    uid = str(user["_id"])
    access = create_access_token(uid, email)
    refresh = create_refresh_token(uid)
    response = JSONResponse({"_id": uid, "email": user["email"], "name": user.get("name", ""), "role": user.get("role", "user")})
    response.set_cookie("access_token", access, httponly=True, secure=False, samesite="lax", max_age=86400, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    await log_activity("auth", f"User {email} logged in", user_id=uid)
    return response

@app.post("/api/auth/logout")
async def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return response

@app.get("/api/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user

@app.post("/api/auth/refresh")
async def refresh_token(request: Request):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        uid = str(user["_id"])
        access = create_access_token(uid, user["email"])
        response = JSONResponse({"ok": True})
        response.set_cookie("access_token", access, httponly=True, secure=False, samesite="lax", max_age=86400, path="/")
        return response
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")


# ─── LLM Engine ─────────────────────────────────────────────────────────────────

async def get_active_provider():
    prov = await db.providers.find_one({"is_default": True})
    if not prov:
        prov = await db.providers.find_one({})
    return prov

async def call_llm(messages: list[dict], model: str = None, temperature: float = 0.3) -> str:
    provider = await get_active_provider()
    ptype = provider["type"] if provider else "emergent"
    api_key = provider.get("api_key", "") if provider else EMERGENT_KEY
    base_url = provider.get("base_url", OLLAMA_BASE) if provider else OLLAMA_BASE
    use_model = model or (provider.get("default_model") if provider else None) or "gpt-4o-mini"

    if (ptype == "openai-compatible" or ptype == "emergent") and api_key:
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            system_msg, user_text = "", ""
            for m in messages:
                if m["role"] == "system":
                    system_msg += m["content"] + "\n"
                elif m["role"] == "user":
                    user_text += m["content"] + "\n"
                elif m["role"] == "assistant":
                    user_text += f"[Previous: {m['content'][:200]}]\n"
            sid = secrets.token_hex(8)
            llm = LlmChat(api_key=api_key, session_id=sid, system_message=system_msg.strip()
            ).with_model("openai", use_model).with_params(temperature=temperature)
            return await llm.send_message(UserMessage(text=user_text.strip()))
        except Exception as e:
            log.error("Cloud LLM call failed: %s", e)
            raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")
    else:
        payload = {"model": use_model, "messages": messages, "temperature": temperature, "stream": False}
        try:
            async with httpx.AsyncClient(timeout=120) as c:
                resp = await c.post(f"{base_url}/v1/chat/completions", json=payload)
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            log.error("Ollama LLM call failed: %s", e)
            raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")


# ─── Chat Sessions ──────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    content: str
    session_id: str = None
    model: str = None

@app.post("/api/chat/send")
async def chat_send(body: ChatMessage, user: dict = Depends(get_current_user)):
    uid = user["_id"]
    sid = body.session_id
    if not sid:
        result = await db.chat_sessions.insert_one({
            "user_id": uid, "title": body.content[:60], "messages": [],
            "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        sid = str(result.inserted_id)
    session = await db.chat_sessions.find_one({"_id": ObjectId(sid)})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = session.get("messages", [])
    messages.append({"role": "user", "content": body.content})
    wiki_pages = []
    async for page in db.wiki_pages.find({}, {"_id": 0, "slug": 1, "title": 1}).limit(50):
        wiki_pages.append(f"- {page['title']} ({page['slug']})")
    wiki_index = "\n".join(wiki_pages) if wiki_pages else "(empty wiki)"
    system_msg = {
        "role": "system",
        "content": f"You are the LLM Wiki Agent. You help build and maintain a persistent knowledge wiki. Current wiki pages:\n{wiki_index}\nUse [[Page Title]] notation for references. Be concise and helpful.",
    }
    llm_messages = [system_msg] + messages[-20:]
    response_text = await call_llm(llm_messages, model=body.model)
    messages.append({"role": "assistant", "content": response_text})
    await db.chat_sessions.update_one({"_id": ObjectId(sid)}, {"$set": {"messages": messages, "updated_at": datetime.now(timezone.utc).isoformat()}})
    await log_activity("chat", f"Chat in session {sid[:8]}...", user_id=uid, meta={"session_id": sid})
    return {"session_id": sid, "response": response_text, "message_count": len(messages)}

@app.get("/api/chat/sessions")
async def list_sessions(user: dict = Depends(get_current_user)):
    sessions = []
    async for s in db.chat_sessions.find({"user_id": user["_id"]}, {"messages": 0}).sort("updated_at", -1).limit(50):
        s["_id"] = str(s["_id"])
        sessions.append(s)
    return {"sessions": sessions}

@app.get("/api/chat/sessions/{session_id}")
async def get_session(session_id: str, user: dict = Depends(get_current_user)):
    session = await db.chat_sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session["_id"] = str(session["_id"])
    return session

@app.delete("/api/chat/sessions/{session_id}")
async def delete_session(session_id: str, user: dict = Depends(get_current_user)):
    await db.chat_sessions.delete_one({"_id": ObjectId(session_id)})
    return {"ok": True}


# ─── Wiki Pages ─────────────────────────────────────────────────────────────────

class WikiPageCreate(BaseModel):
    title: str
    content: str = ""
    tags: list[str] = []

class WikiPageUpdate(BaseModel):
    title: str = None
    content: str = None
    tags: list[str] = None

def slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    return slug.strip('-')

@app.get("/api/wiki/pages")
async def list_wiki_pages(q: str = None, user: dict = Depends(get_current_user)):
    query = {"$text": {"$search": q}} if q else {}
    pages = []
    async for p in db.wiki_pages.find(query, {"content": 0}).sort("updated_at", -1).limit(200):
        p["_id"] = str(p["_id"])
        pages.append(p)
    return {"pages": pages}

@app.get("/api/wiki/pages/{slug}")
async def get_wiki_page(slug: str, user: dict = Depends(get_current_user)):
    page = await db.wiki_pages.find_one({"slug": slug})
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    page["_id"] = str(page["_id"])
    return page

@app.post("/api/wiki/pages")
async def create_wiki_page(body: WikiPageCreate, user: dict = Depends(get_current_user)):
    slug = slugify(body.title)
    if await db.wiki_pages.find_one({"slug": slug}):
        raise HTTPException(status_code=409, detail="Page with this title already exists")
    now = datetime.now(timezone.utc).isoformat()
    doc = {"title": body.title, "slug": slug, "content": body.content, "tags": body.tags, "source_count": 0, "created_at": now, "updated_at": now, "created_by": user["_id"]}
    result = await db.wiki_pages.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    await log_activity("wiki", f"Created page: {body.title}", user_id=user["_id"])
    return doc

@app.put("/api/wiki/pages/{slug}")
async def update_wiki_page(slug: str, body: WikiPageUpdate, user: dict = Depends(get_current_user)):
    updates = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if body.title is not None: updates["title"] = body.title
    if body.content is not None: updates["content"] = body.content
    if body.tags is not None: updates["tags"] = body.tags
    result = await db.wiki_pages.update_one({"slug": slug}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Page not found")
    page = await db.wiki_pages.find_one({"slug": slug})
    page["_id"] = str(page["_id"])
    await log_activity("wiki", f"Updated page: {slug}", user_id=user["_id"])
    return page

@app.delete("/api/wiki/pages/{slug}")
async def delete_wiki_page(slug: str, user: dict = Depends(get_current_user)):
    result = await db.wiki_pages.delete_one({"slug": slug})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Page not found")
    await log_activity("wiki", f"Deleted page: {slug}", user_id=user["_id"])
    return {"ok": True}

@app.post("/api/wiki/lint")
async def lint_wiki(user: dict = Depends(get_current_user)):
    pages = []
    async for p in db.wiki_pages.find({}, {"_id": 0, "title": 1, "slug": 1, "content": 1, "tags": 1}):
        pages.append(p)
    if not pages:
        return {"issues": [], "summary": "Wiki is empty. Add some pages first."}
    page_list = "\n".join([f"- {p['title']} (/{p['slug']}): {len(p.get('content',''))} chars, tags: {p.get('tags', [])}" for p in pages])
    result = await call_llm([
        {"role": "system", "content": "Analyze wiki structure. Return JSON with 'issues' (array of {type, severity, page, description}) and 'summary' (string)."},
        {"role": "user", "content": f"Wiki pages:\n{page_list}"},
    ])
    try:
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            return parsed
    except Exception:
        pass
    return {"issues": [], "summary": result}


# ─── Source Ingestion ───────────────────────────────────────────────────────────

@app.post("/api/sources/ingest")
async def ingest_source(user: dict = Depends(get_current_user), file: UploadFile = File(None), url: str = Form(None), title: str = Form(None), content_text: str = Form(None)):
    if not file and not url and not content_text:
        raise HTTPException(status_code=400, detail="Provide a file, URL, or text content")
    raw_content, source_type, source_name = "", "text", title or "Untitled Source"
    if file:
        raw_content = (await file.read()).decode("utf-8", errors="replace")
        source_name = title or file.filename or "Uploaded File"
        source_type = "file"
    elif url:
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                resp = await c.get(url, follow_redirects=True)
                raw_content = resp.text[:50000]
            source_name = title or url
            source_type = "url"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}")
    elif content_text:
        raw_content = content_text
    now = datetime.now(timezone.utc).isoformat()
    doc = {"title": source_name, "type": source_type, "url": url, "raw_content": raw_content[:100000], "status": "pending", "summary": None, "created_at": now, "created_by": user["_id"]}
    result = await db.sources.insert_one(doc)
    source_id = str(result.inserted_id)
    try:
        summary = await call_llm([
            {"role": "system", "content": "Summarize this source in 2-3 paragraphs. Extract key concepts. Format as markdown."},
            {"role": "user", "content": raw_content[:8000]},
        ])
        await db.sources.update_one({"_id": ObjectId(source_id)}, {"$set": {"status": "processed", "summary": summary}})
        await log_activity("ingest", f"Ingested: {source_name}", user_id=user["_id"], meta={"source_id": source_id})
    except Exception as e:
        await db.sources.update_one({"_id": ObjectId(source_id)}, {"$set": {"status": "failed", "summary": f"Processing failed: {e}"}})
    doc["_id"] = source_id
    return doc

@app.get("/api/sources")
async def list_sources(user: dict = Depends(get_current_user)):
    sources = []
    async for s in db.sources.find({}, {"raw_content": 0}).sort("created_at", -1).limit(100):
        s["_id"] = str(s["_id"])
        sources.append(s)
    return {"sources": sources}

@app.get("/api/sources/{source_id}")
async def get_source(source_id: str, user: dict = Depends(get_current_user)):
    source = await db.sources.find_one({"_id": ObjectId(source_id)})
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    source["_id"] = str(source["_id"])
    return source

@app.delete("/api/sources/{source_id}")
async def delete_source(source_id: str, user: dict = Depends(get_current_user)):
    await db.sources.delete_one({"_id": ObjectId(source_id)})
    return {"ok": True}


# ─── Activity & Stats ──────────────────────────────────────────────────────────

@app.get("/api/activity")
async def get_activity(limit: int = 50, user: dict = Depends(get_current_user)):
    logs = []
    async for entry in db.activity_log.find({}).sort("created_at", -1).limit(limit):
        entry["_id"] = str(entry["_id"])
        logs.append(entry)
    return {"logs": logs}

@app.get("/api/stats")
async def get_stats(user: dict = Depends(get_current_user)):
    wiki_count = await db.wiki_pages.count_documents({})
    source_count = await db.sources.count_documents({})
    session_count = await db.chat_sessions.count_documents({})
    log_count = await db.activity_log.count_documents({})
    provider_count = await db.providers.count_documents({})
    key_count = await db.api_keys.count_documents({})
    recent_pages = []
    async for p in db.wiki_pages.find({}, {"_id": 0, "title": 1, "slug": 1, "updated_at": 1}).sort("updated_at", -1).limit(5):
        recent_pages.append(p)
    active_provider = await get_active_provider()
    return {
        "wiki_pages": wiki_count, "sources": source_count, "chat_sessions": session_count,
        "activity_entries": log_count, "providers": provider_count, "api_keys": key_count,
        "recent_pages": recent_pages,
        "llm_provider": active_provider.get("name", "None") if active_provider else "None",
        "ngrok_domain": NGROK_DOMAIN,
        "langfuse_configured": bool(LANGFUSE_PK and LANGFUSE_SK),
    }


# ─── Providers CRUD ─────────────────────────────────────────────────────────────

class ProviderCreate(BaseModel):
    provider_id: str
    name: str
    type: str = "openai-compatible"
    base_url: str
    api_key: str = ""
    default_model: str = ""
    is_default: bool = False

class ProviderUpdate(BaseModel):
    name: str = None
    base_url: str = None
    api_key: str = None
    default_model: str = None
    is_default: bool = None

@app.get("/api/providers")
async def list_providers(user: dict = Depends(get_current_user)):
    providers = []
    async for p in db.providers.find({}).sort("created_at", 1):
        p["_id"] = str(p["_id"])
        if p.get("api_key"):
            p["api_key_masked"] = p["api_key"][:8] + "..." + p["api_key"][-4:] if len(p["api_key"]) > 12 else "***"
        else:
            p["api_key_masked"] = ""
        p.pop("api_key", None)
        providers.append(p)
    return {"providers": providers}

@app.post("/api/providers")
async def create_provider(body: ProviderCreate, user: dict = Depends(get_current_user)):
    if await db.providers.find_one({"provider_id": body.provider_id}):
        raise HTTPException(status_code=409, detail="Provider ID already exists")
    if body.is_default:
        await db.providers.update_many({}, {"$set": {"is_default": False}})
    doc = body.dict()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    doc["status"] = "configured"
    await db.providers.insert_one(doc)
    await log_activity("provider", f"Added provider: {body.name}", user_id=user["_id"])
    return {"ok": True, "provider_id": body.provider_id}

@app.put("/api/providers/{provider_id}")
async def update_provider(provider_id: str, body: ProviderUpdate, user: dict = Depends(get_current_user)):
    updates = {}
    for k, v in body.dict(exclude_none=True).items():
        updates[k] = v
    if body.is_default:
        await db.providers.update_many({"provider_id": {"$ne": provider_id}}, {"$set": {"is_default": False}})
    if updates:
        result = await db.providers.update_one({"provider_id": provider_id}, {"$set": updates})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Provider not found")
    await log_activity("provider", f"Updated provider: {provider_id}", user_id=user["_id"])
    return {"ok": True}

@app.delete("/api/providers/{provider_id}")
async def delete_provider(provider_id: str, user: dict = Depends(get_current_user)):
    result = await db.providers.delete_one({"provider_id": provider_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Provider not found")
    await log_activity("provider", f"Deleted provider: {provider_id}", user_id=user["_id"])
    return {"ok": True}

@app.post("/api/providers/{provider_id}/test")
async def test_provider(provider_id: str, user: dict = Depends(get_current_user)):
    prov = await db.providers.find_one({"provider_id": provider_id})
    if not prov:
        raise HTTPException(status_code=404, detail="Provider not found")
    try:
        if prov["type"] == "ollama":
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"{prov['base_url']}/api/tags")
                models = [m["name"] for m in r.json().get("models", [])]
            await db.providers.update_one({"provider_id": provider_id}, {"$set": {"status": "online"}})
            return {"ok": True, "models": models}
        else:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"{prov['base_url']}/models", headers={"Authorization": f"Bearer {prov.get('api_key', '')}"})
            await db.providers.update_one({"provider_id": provider_id}, {"$set": {"status": "online"}})
            return {"ok": True, "status": "connected"}
    except Exception as e:
        await db.providers.update_one({"provider_id": provider_id}, {"$set": {"status": "error"}})
        return {"ok": False, "error": str(e)}


# ─── Models Hub ─────────────────────────────────────────────────────────────────

@app.get("/api/models")
async def list_models(user: dict = Depends(get_current_user)):
    models = []
    # Try Ollama
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{OLLAMA_BASE}/api/tags")
            if r.status_code == 200:
                for m in r.json().get("models", []):
                    models.append({
                        "name": m["name"],
                        "size": m.get("size", 0),
                        "modified_at": m.get("modified_at", ""),
                        "source": "ollama-local",
                        "details": m.get("details", {}),
                    })
    except Exception:
        pass
    # Add cloud model references from providers
    async for prov in db.providers.find({"type": {"$ne": "ollama"}}):
        if prov.get("default_model"):
            models.append({
                "name": prov["default_model"],
                "size": 0,
                "modified_at": "",
                "source": prov["provider_id"],
                "details": {"provider": prov["name"]},
            })
    return {"models": models}

class ModelPullRequest(BaseModel):
    name: str

@app.post("/api/models/pull")
async def pull_model(body: ModelPullRequest, user: dict = Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=600) as c:
            r = await c.post(f"{OLLAMA_BASE}/api/pull", json={"name": body.name, "stream": False})
            r.raise_for_status()
        await log_activity("models", f"Pulled model: {body.name}", user_id=user["_id"])
        return {"ok": True, "model": body.name}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Pull failed: {e}")

@app.delete("/api/models/{model_name}")
async def delete_model(model_name: str, user: dict = Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.delete(f"{OLLAMA_BASE}/api/delete", json={"name": model_name})
            r.raise_for_status()
        await log_activity("models", f"Deleted model: {model_name}", user_id=user["_id"])
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Delete failed: {e}")


# ─── API Keys Management ───────────────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    email: str
    department: str = "general"
    label: str = ""

@app.get("/api/keys")
async def list_api_keys(user: dict = Depends(get_current_user)):
    keys = []
    async for k in db.api_keys.find({}, {"secret_hash": 0}).sort("created_at", -1):
        k["_id"] = str(k["_id"])
        keys.append(k)
    return {"keys": keys}

@app.post("/api/keys")
async def create_api_key(body: ApiKeyCreate, user: dict = Depends(get_current_user)):
    plain = "sk-wiki-" + secrets.token_urlsafe(32)
    key_id = "key_" + secrets.token_hex(4)
    hashed = bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
    doc = {
        "key_id": key_id, "email": body.email, "department": body.department,
        "label": body.label, "secret_hash": hashed, "prefix": plain[:12] + "...",
        "created_at": datetime.now(timezone.utc).isoformat(), "created_by": user["_id"],
    }
    await db.api_keys.insert_one(doc)
    await log_activity("keys", f"Created API key for {body.email}", user_id=user["_id"])
    return {"key_id": key_id, "api_key": plain, "email": body.email}

@app.delete("/api/keys/{key_id}")
async def delete_api_key(key_id: str, user: dict = Depends(get_current_user)):
    result = await db.api_keys.delete_one({"key_id": key_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Key not found")
    await log_activity("keys", f"Revoked API key: {key_id}", user_id=user["_id"])
    return {"ok": True}


# ─── Observability (Langfuse) ───────────────────────────────────────────────────

@app.get("/api/observability/status")
async def observability_status(user: dict = Depends(get_current_user)):
    configured = bool(LANGFUSE_PK and LANGFUSE_SK)
    status = {"configured": configured, "base_url": LANGFUSE_BASE, "public_key_prefix": LANGFUSE_PK[:12] + "..." if LANGFUSE_PK else ""}
    if configured:
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"{LANGFUSE_BASE}/api/public/health", auth=(LANGFUSE_PK, LANGFUSE_SK))
                if r.status_code == 200:
                    status["connected"] = True
                    status["message"] = "Langfuse connected"
                else:
                    status["connected"] = False
                    status["message"] = f"HTTP {r.status_code}"
        except Exception as e:
            status["connected"] = False
            status["message"] = str(e)
    else:
        status["connected"] = False
        status["message"] = "Not configured — set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY"
    return status

@app.get("/api/observability/dashboard-url")
async def observability_dashboard(user: dict = Depends(get_current_user)):
    return {"url": LANGFUSE_BASE, "configured": bool(LANGFUSE_PK)}


# ─── System / Platform Info ─────────────────────────────────────────────────────

@app.get("/api/platform")
async def platform_info(user: dict = Depends(get_current_user)):
    return {
        "name": "LLM Wiki Platform",
        "version": "2.0.0",
        "ngrok_domain": NGROK_DOMAIN,
        "ngrok_configured": bool(NGROK_TOKEN),
        "langfuse_configured": bool(LANGFUSE_PK and LANGFUSE_SK),
        "langfuse_url": LANGFUSE_BASE,
        "ollama_base": OLLAMA_BASE,
        "github_repo": "https://github.com/strikersam/local-llm-server",
    }

@app.get("/api/health")
async def health():
    try:
        await db.command("ping")
        mongo_ok = True
    except Exception:
        mongo_ok = False
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=3) as c:
            r = await c.get(f"{OLLAMA_BASE}/api/tags")
            ollama_ok = r.status_code == 200
    except Exception:
        pass
    return {"status": "ok" if mongo_ok else "degraded", "mongo": mongo_ok, "ollama": ollama_ok, "provider": LLM_PROVIDER}
