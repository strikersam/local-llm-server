from dotenv import load_dotenv
load_dotenv()

import os
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

app = FastAPI(title="LLM Wiki Dashboard", version="1.0.0")

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app_url = os.environ.get("APP_URL", "")
origins = [frontend_url]
if app_url:
    origins.append(app_url)
origins.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


# --- Password & JWT helpers ---

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "exp": datetime.now(timezone.utc) + timedelta(hours=24), "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


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


# --- Startup ---

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.wiki_pages.create_index("slug", unique=True)
    await db.wiki_pages.create_index([("title", "text"), ("content", "text")])
    await db.sources.create_index("created_at")
    await db.activity_log.create_index("created_at")
    await db.chat_sessions.create_index("user_id")
    await seed_admin()
    log.info("LLM Wiki Dashboard started — provider=%s", LLM_PROVIDER)


async def seed_admin():
    existing = await db.users.find_one({"email": ADMIN_EMAIL})
    if existing is None:
        await db.users.insert_one({
            "email": ADMIN_EMAIL,
            "password_hash": hash_password(ADMIN_PASSWORD),
            "name": "Admin",
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        log.info("Admin user seeded: %s", ADMIN_EMAIL)
    elif not verify_password(ADMIN_PASSWORD, existing["password_hash"]):
        await db.users.update_one(
            {"email": ADMIN_EMAIL},
            {"$set": {"password_hash": hash_password(ADMIN_PASSWORD)}}
        )
        log.info("Admin password updated")
    # Write credentials
    mem = Path("/app/memory")
    mem.mkdir(exist_ok=True)
    (mem / "test_credentials.md").write_text(
        f"# Test Credentials\n\n- **Email**: {ADMIN_EMAIL}\n- **Password**: {ADMIN_PASSWORD}\n- **Role**: admin\n\n"
        f"## Auth Endpoints\n- POST /api/auth/login\n- POST /api/auth/logout\n- GET /api/auth/me\n- POST /api/auth/refresh\n"
    )


# --- Auth Models ---

class LoginBody(BaseModel):
    email: str
    password: str

class RegisterBody(BaseModel):
    email: str
    password: str
    name: str = "User"


# --- Auth Endpoints ---

@app.post("/api/auth/login")
async def login(body: LoginBody, request: Request):
    email = body.email.strip().lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    uid = str(user["_id"])
    access = create_access_token(uid, email)
    refresh = create_refresh_token(uid)
    response = JSONResponse({
        "_id": uid, "email": user["email"], "name": user.get("name", ""), "role": user.get("role", "user")
    })
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


# --- Activity Logging ---

async def log_activity(category: str, message: str, user_id: str = None, meta: dict = None):
    await db.activity_log.insert_one({
        "category": category,
        "message": message,
        "user_id": user_id,
        "meta": meta or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


# --- LLM Chat ---

async def call_llm(messages: list[dict], model: str = None, temperature: float = 0.3) -> str:
    """Call LLM via Emergent integration or Ollama."""
    if LLM_PROVIDER == "emergent" and EMERGENT_KEY:
        try:
            from emergentintegrations.llm.chat import chat, ChatMessage
            chat_messages = []
            for m in messages:
                chat_messages.append(ChatMessage(role=m["role"], content=m["content"]))
            response = await chat(
                api_key=EMERGENT_KEY,
                model=model or "gpt-4o-mini",
                messages=chat_messages,
                temperature=temperature,
            )
            return response.message
        except Exception as e:
            log.error("Emergent LLM call failed: %s", e)
            raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")
    else:
        # Ollama OpenAI-compatible endpoint
        payload = {
            "model": model or "llama3.2",
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=120) as c:
                resp = await c.post(f"{OLLAMA_BASE}/v1/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            log.error("Ollama LLM call failed: %s", e)
            raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")


# --- Chat Sessions ---

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
            "user_id": uid,
            "title": body.content[:60],
            "messages": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        sid = str(result.inserted_id)

    session = await db.chat_sessions.find_one({"_id": ObjectId(sid)})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = session.get("messages", [])
    messages.append({"role": "user", "content": body.content})

    # Build wiki context
    wiki_pages = []
    async for page in db.wiki_pages.find({}, {"_id": 0, "slug": 1, "title": 1}).limit(50):
        wiki_pages.append(f"- {page['title']} ({page['slug']})")
    wiki_index = "\n".join(wiki_pages) if wiki_pages else "(empty wiki)"

    system_msg = {
        "role": "system",
        "content": (
            "You are the LLM Wiki Agent. You help the user build and maintain a persistent knowledge wiki. "
            "You can: answer questions from the wiki, suggest new pages, analyze sources, and help organize knowledge. "
            f"Current wiki pages:\n{wiki_index}\n\n"
            "When referencing wiki pages, use [[Page Title]] notation. "
            "Be concise, helpful, and reference specific wiki pages when relevant."
        )
    }

    llm_messages = [system_msg] + messages[-20:]
    response_text = await call_llm(llm_messages, model=body.model)

    messages.append({"role": "assistant", "content": response_text})

    await db.chat_sessions.update_one(
        {"_id": ObjectId(sid)},
        {"$set": {"messages": messages, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    await log_activity("chat", f"Chat message in session {sid[:8]}...", user_id=uid,
                        meta={"session_id": sid, "tokens_est": len(body.content.split()) + len(response_text.split())})

    return {
        "session_id": sid,
        "response": response_text,
        "message_count": len(messages),
    }

@app.get("/api/chat/sessions")
async def list_sessions(user: dict = Depends(get_current_user)):
    sessions = []
    async for s in db.chat_sessions.find(
        {"user_id": user["_id"]},
        {"messages": 0}
    ).sort("updated_at", -1).limit(50):
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


# --- Wiki Pages ---

class WikiPageCreate(BaseModel):
    title: str
    content: str = ""
    tags: list[str] = []

class WikiPageUpdate(BaseModel):
    title: str = None
    content: str = None
    tags: list[str] = None

def slugify(title: str) -> str:
    import re
    slug = title.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    return slug.strip('-')

@app.get("/api/wiki/pages")
async def list_wiki_pages(q: str = None, user: dict = Depends(get_current_user)):
    query = {}
    if q:
        query = {"$text": {"$search": q}}
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
    existing = await db.wiki_pages.find_one({"slug": slug})
    if existing:
        raise HTTPException(status_code=409, detail="Page with this title already exists")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "title": body.title,
        "slug": slug,
        "content": body.content,
        "tags": body.tags,
        "source_count": 0,
        "created_at": now,
        "updated_at": now,
        "created_by": user["_id"],
    }
    result = await db.wiki_pages.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    await log_activity("wiki", f"Created page: {body.title}", user_id=user["_id"])
    return doc

@app.put("/api/wiki/pages/{slug}")
async def update_wiki_page(slug: str, body: WikiPageUpdate, user: dict = Depends(get_current_user)):
    updates = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if body.title is not None:
        updates["title"] = body.title
    if body.content is not None:
        updates["content"] = body.content
    if body.tags is not None:
        updates["tags"] = body.tags
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


# --- Source Ingestion ---

@app.post("/api/sources/ingest")
async def ingest_source(
    user: dict = Depends(get_current_user),
    file: UploadFile = File(None),
    url: str = Form(None),
    title: str = Form(None),
    content_text: str = Form(None),
):
    if not file and not url and not content_text:
        raise HTTPException(status_code=400, detail="Provide a file, URL, or text content")

    raw_content = ""
    source_type = "text"
    source_name = title or "Untitled Source"

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
        source_type = "text"

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "title": source_name,
        "type": source_type,
        "url": url,
        "raw_content": raw_content[:100000],
        "status": "pending",
        "summary": None,
        "created_at": now,
        "created_by": user["_id"],
    }
    result = await db.sources.insert_one(doc)
    source_id = str(result.inserted_id)

    # Process with LLM to generate summary
    try:
        summary = await call_llm([
            {"role": "system", "content": "Summarize this source document concisely in 2-3 paragraphs. Extract key entities, concepts, and claims. Format as markdown."},
            {"role": "user", "content": raw_content[:8000]},
        ])
        await db.sources.update_one(
            {"_id": ObjectId(source_id)},
            {"$set": {"status": "processed", "summary": summary}}
        )
        await log_activity("ingest", f"Ingested source: {source_name}", user_id=user["_id"],
                            meta={"source_id": source_id, "type": source_type})
    except Exception as e:
        await db.sources.update_one(
            {"_id": ObjectId(source_id)},
            {"$set": {"status": "failed", "summary": f"Processing failed: {e}"}}
        )
        log.error("Source ingestion LLM failed: %s", e)

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


# --- Activity Log ---

@app.get("/api/activity")
async def get_activity(limit: int = 50, user: dict = Depends(get_current_user)):
    logs = []
    async for entry in db.activity_log.find({}).sort("created_at", -1).limit(limit):
        entry["_id"] = str(entry["_id"])
        logs.append(entry)
    return {"logs": logs}


# --- Dashboard Stats ---

@app.get("/api/stats")
async def get_stats(user: dict = Depends(get_current_user)):
    wiki_count = await db.wiki_pages.count_documents({})
    source_count = await db.sources.count_documents({})
    session_count = await db.chat_sessions.count_documents({})
    log_count = await db.activity_log.count_documents({})
    recent_pages = []
    async for p in db.wiki_pages.find({}, {"_id": 0, "title": 1, "slug": 1, "updated_at": 1}).sort("updated_at", -1).limit(5):
        recent_pages.append(p)
    return {
        "wiki_pages": wiki_count,
        "sources": source_count,
        "chat_sessions": session_count,
        "activity_entries": log_count,
        "recent_pages": recent_pages,
        "llm_provider": LLM_PROVIDER,
    }


# --- Wiki Lint ---

@app.post("/api/wiki/lint")
async def lint_wiki(user: dict = Depends(get_current_user)):
    pages = []
    async for p in db.wiki_pages.find({}, {"_id": 0, "title": 1, "slug": 1, "content": 1, "tags": 1}):
        pages.append(p)

    if not pages:
        return {"issues": [], "summary": "Wiki is empty. Add some pages first."}

    page_list = "\n".join([f"- {p['title']} (/{p['slug']}): {len(p.get('content',''))} chars, tags: {p.get('tags', [])}" for p in pages])

    result = await call_llm([
        {"role": "system", "content": (
            "You are a wiki health checker. Analyze the wiki structure and report issues. "
            "Check for: orphan pages (no cross-references), missing pages (referenced but don't exist), "
            "stale content, missing tags, duplicate topics, and areas that need expansion. "
            "Return a JSON object with 'issues' (array of {type, severity, page, description}) and 'summary' (string)."
        )},
        {"role": "user", "content": f"Wiki pages:\n{page_list}"},
    ])

    try:
        import re
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            await log_activity("lint", f"Wiki lint: {len(parsed.get('issues', []))} issues found", user_id=user["_id"])
            return parsed
    except (json.JSONDecodeError, Exception):
        pass

    return {"issues": [], "summary": result}


# --- Provider Settings ---

@app.get("/api/settings/providers")
async def get_providers(user: dict = Depends(get_current_user)):
    return {
        "current": LLM_PROVIDER,
        "ollama_base": OLLAMA_BASE,
        "providers": [
            {"id": "emergent", "name": "Emergent (Cloud)", "status": "active" if LLM_PROVIDER == "emergent" else "available"},
            {"id": "ollama", "name": "Ollama (Local)", "status": "active" if LLM_PROVIDER == "ollama" else "available"},
        ]
    }


# --- Health ---

@app.get("/api/health")
async def health():
    try:
        await db.command("ping")
        mongo_ok = True
    except Exception:
        mongo_ok = False
    return {"status": "ok" if mongo_ok else "degraded", "mongo": mongo_ok, "provider": LLM_PROVIDER}
