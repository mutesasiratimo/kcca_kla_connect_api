from fastapi import FastAPI, File, UploadFile
import hashlib
import math
import random
from typing import List
import urllib.request 
from urllib.parse import urlparse, parse_qs
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
from fastapi import BackgroundTasks, FastAPI, Body, Depends, HTTPException, Request, Query
from app.model import *
from app.auth.jwt_handler import signJWT
from app.auth.jwt_bearer import jwtBearer
import jwt
from sqlalchemy import select, join, func, extract, case, or_, and_, desc, asc
from decouple import config
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from app.send_mail import send_email_background, send_email_async, send_email_async_test
import os
import websockets
import json
import requests
import google.auth.transport.requests
from google.oauth2 import service_account
import google.oauth2.id_token
import firebase_admin
from firebase_admin import credentials
from fastapi_pagination import Page, LimitOffsetPage, paginate, add_pagination, Params
from app.utils.email_templates import send_welcome_email, send_password_reset_email
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
import asyncio
from collections import deque, defaultdict

UPLOAD_FOLDER = "uploads"

#Create upload folder if it does not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


app = FastAPI(
    title="KCCA Kla Konnect",
    description="A system for reporting and managing incidents.",
    version="0.1.1",
    contact={
        "name": "KCCA",
        "url": "http://kcca.go.ug",
        "email": "info@kcca.go.ug",
    },
    # docs_url=None,
    # redoc_url=None,
    # openapi_url=None,
)
add_pagination(app)
# =============== Simple Rate Limiter Middleware ===============


class _SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets = defaultdict(deque)  # key -> deque[timestamps]
        self._lock = asyncio.Lock()

    async def allow(self, key: str, now: float) -> tuple[bool, int, float]:
        # Returns (allowed, remaining, reset_epoch_seconds)
        async with self._lock:
            q = self._buckets[key]
            # prune old
            cutoff = now - self.window_seconds
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) < self.max_requests:
                q.append(now)
                remaining = self.max_requests - len(q)
                reset = (q[0] + self.window_seconds) if q else (now + self.window_seconds)
                return True, remaining, reset
            # rejected
            reset = q[0] + self.window_seconds
            remaining = 0
            return False, remaining, reset

# Config from environment
def _get_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}

RATE_LIMIT_ENABLED = _get_bool("RATE_LIMIT_ENABLED", True)
RATE_LIMIT_WINDOW_SEC = int(os.environ.get("RATE_LIMIT_WINDOW_SEC", "60"))
RATE_LIMIT_REQS = int(os.environ.get("RATE_LIMIT_REQS", "120"))

_rate_limiter = _SlidingWindowRateLimiter(RATE_LIMIT_REQS, RATE_LIMIT_WINDOW_SEC) if RATE_LIMIT_ENABLED else None

def _is_probe_like(path: str, ua: str) -> bool:
    path_lower = (path or "").lower()
    ua_lower = (ua or "").lower()
    return (
        "kube-probe" in ua_lower
        or "readiness" in ua_lower
        or "liveness" in ua_lower
        or path_lower in {"/health", "/healthz", "/ready", "/readyz"}
        or path_lower.startswith("/metrics")
        or path_lower.startswith("/docs")
        or path_lower.startswith("/openapi")
    )

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if not RATE_LIMIT_ENABLED:
        return await call_next(request)

    ua = request.headers.get("user-agent") or ""
    if _is_probe_like(request.url.path, ua):
        return await call_next(request)

    # Key by authenticated user if available (JWT parsed later in activity logger),
    # but here we only have headers; try to parse lightweight
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    key = None
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            key = str(payload.get("userID") or payload.get("userid") or payload.get("user_id") or payload.get("sub"))
        except Exception:
            key = None
    if not key:
        key = request.client.host if request.client else "anonymous"

    now = datetime.datetime.now().timestamp()
    allowed, remaining, reset_epoch = await _rate_limiter.allow(f"rl:{key}", now)
    if not allowed:
        reset_in = max(0, int(reset_epoch - now))
        headers = {
            "Retry-After": str(reset_in),
            "X-RateLimit-Limit": str(RATE_LIMIT_REQS),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(reset_epoch)),
        }
        return JSONResponse(status_code=429, content={"detail": "Too Many Requests"}, headers=headers)

    response = await call_next(request)
    # Attach rate headers to successful responses for observability
    try:
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_REQS)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(reset_epoch))
    except Exception:
        pass
    return response

# =============== Activity Logs Middleware ===============
MAX_BODY_LEN = 8192

def _infer_module_from_path(path: str) -> str:
    try:
        first = path.strip("/").split("/")[0]
        return first or "root"
    except Exception:
        return "unknown"

def _infer_action(method: str, path: str) -> str:
    method = (method or "").upper()
    if method == "POST":
        if any(x in path for x in ["approve", "resolve", "restore", "publish"]):
            return "approve"
        if any(x in path for x in ["reject"]):
            return "reject"
        if any(x in path for x in ["archive"]):
            return "archive"
        if any(x in path for x in ["login", "signin"]):
            return "login"
        if any(x in path for x in ["logout", "signout"]):
            return "logout"
        if any(x in path for x in ["update"]):
            return "update"
        return "add"
    if method == "PUT":
        return "update"
    if method == "PATCH":
        return "update"
    if method == "DELETE":
        return "delete"
    return "get"

def _redact_in_obj(obj):
    if isinstance(obj, dict):
        redacted = {}
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in {"password", "newpassword", "confirmpassword", "pass", "pwd"}:
                redacted[k] = "***REDACTED***"
            elif kl in {"token", "accesstoken", "access_token", "refreshtoken", "refresh_token", "jwt", "jwttoken", "bearer"}:
                redacted[k] = "***REDACTED_TOKEN***"
            else:
                redacted[k] = _redact_in_obj(v)
        return redacted
    if isinstance(obj, list):
        return [_redact_in_obj(x) for x in obj]
    return obj

def _redact_text(text: str) -> str:
    if not text:
        return text
    try:
        import json as _json
        obj = _json.loads(text)
        obj = _redact_in_obj(obj)
        return _json.dumps(obj)
    except Exception:
        pass
    # Fallback regex redactions for JWT-like tokens (header.payload.signature)
    try:
        import re
        # Basic JWT pattern: three base64url segments separated by dots
        jwt_regex = re.compile(r"\beyJ[\w-]+\.[\w-]+\.[\w-]+\b")
        text = jwt_regex.sub("***REDACTED_TOKEN***", text)
        # Password query/body patterns
        # redact password-like assignments inside JSON/text
        pw_regex = re.compile(r'("?password"?\s*[:=]\s*")([^"\n\r]*)(")', re.IGNORECASE)
        text = pw_regex.sub(r'\1***REDACTED***\3', text)
    except Exception:
        pass
    return text

@app.middleware("http")
async def activity_logs_middleware(request: Request, call_next):
    start_time = datetime.datetime.now()
    
    # Don't consume request body; capture it safely
    request_body = None
    try:
        if request.method in ["POST", "PUT", "PATCH"]:
            body_bytes = await request.body()
            if body_bytes:
                request_body_raw = body_bytes[:MAX_BODY_LEN].decode("utf-8", errors="ignore")
                request_body = _redact_text(request_body_raw) if request_body_raw else None
                # Re-wrap body for FastAPI consumption
                async def receive():
                    return {"type": "http.request", "body": body_bytes}
                request._receive = receive
    except Exception:
        pass

    response = await call_next(request)

    # Capture response safely
    status_code = getattr(response, "status_code", 0)
    response_body = None
    try:
        from starlette.responses import StreamingResponse
        if isinstance(response, StreamingResponse):
            # Don't try to capture streaming responses
            response_body = None
        elif hasattr(response, "body") and response.body:
            # Direct body access
            body_content = response.body
            if isinstance(body_content, bytes):
                response_body = body_content[:MAX_BODY_LEN].decode("utf-8", errors="ignore")
            else:
                response_body = str(body_content)[:MAX_BODY_LEN]
        else:
            # Fallback: try to get the rendered body
            pass
    except Exception as e:
        # Debug: uncomment to see what's happening
        # print(f"Response body capture failed: {e}")
        response_body = None
    
    # Redact sensitive data in response body as well
    if response_body:
        response_body = _redact_text(response_body)

    # Parse auth for user id/email if present
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    userid = None
    email = None
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            # Decode without verification
            payload = jwt.decode(token, options={"verify_signature": False})
            # Try multiple common JWT field names for user identification
            userid = payload.get("userID") or payload.get("userid") or payload.get("user_id") or payload.get("sub")
            email = payload.get("email") or payload.get("username") or payload.get("userID") or userid
        except Exception as e:
            # Debug: uncomment to see what's failing
            # print(f"JWT decode failed: {e}, token: {token[:50]}...")
            pass

    # Build log row
    log_id = str(uuid.uuid1())
    module_name = _infer_module_from_path(request.url.path)
    action_type = _infer_action(request.method, request.url.path)
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Balanced anonymous logging to reduce clutter but keep signals
    # 1) Skip well-known health checks and probes entirely
    path_lower = (request.url.path or "").lower()
    ua_lower = (request.headers.get("user-agent") or "").lower()
    known_probe = (
        "kube-probe" in ua_lower
        or "readiness" in ua_lower
        or "liveness" in ua_lower
        or path_lower in {"/health", "/healthz", "/ready", "/readyz"}
        or path_lower.startswith("/metrics")
        or path_lower.startswith("/docs")
        or path_lower.startswith("/openapi")
    )
    if known_probe:
        return response

    # 2) If anonymous (no userid/email), log only suspicious or sampled
    if (userid is None) or (email is None):
        # Log suspicious: auth errors, not found spikes, rate limits, server errors
        is_suspicious = False
        try:
            sc = int(status_code or 0)
            is_suspicious = (
                sc in (401, 403, 404, 429) or (500 <= sc <= 599)
            )
        except Exception:
            pass

        if not is_suspicious:
            # Sample remaining anonymous traffic
            try:
                sample_rate = float(os.environ.get("ANON_LOG_SAMPLE_RATE", "0.01"))
            except Exception:
                sample_rate = 0.01
            try:
                import random as _random
                if _random.random() >= max(0.0, min(1.0, sample_rate)):
                    return response
            except Exception:
                # If sampling fails, default to skipping to avoid noise
                return response

    try:
        await database.execute(
            activitylogs_table.insert().values(
                id=log_id,
                action_type=action_type,
                module=module_name,
                userid=userid,
                email=email,
                method=request.method,
                path=str(request.url.path),
                ip=ip,
                user_agent=user_agent,
                status_code=int(status_code or 0),
                request_body_json=request_body,
                response_body_json=(response_body[:MAX_BODY_LEN] if response_body else None),
                datecreated=start_time,
            )
        )
    except Exception:
        # Avoid breaking the response due to logging failure
        pass

    return response


origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://klakonnect.kcca.go.ug",
        "https://klakonnect.kcca.go.ug/",
        "https://kcca.go.ug",
        "http://localhost:3000",  # For local development
        "http://localhost:8000",  # For local development
        "http://localhost:8080",  # For local development
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

local_background_tasks = BackgroundTasks()

@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.get("/", tags=["welcome"])
def greet():
    return{"Hello": "Welcome to the KLA CONNECT API"}

# @app.get("/docs", include_in_schema=False)
# async def custom_swagger_ui():
#     return get_swagger_ui_html(
#         openapi_url="/apiklakonnect/openapi.json",  # <-- set full path
#         title="KCCA Kla Konnect - Swagger UI",
#     )

# @app.get("/redoc", include_in_schema=False)
# async def custom_redoc():
#     return get_redoc_html(
#         openapi_url="/apiklakonnect/openapi.json",  # full path to OpenAPI spec
#         title="KCCA Kla Konnect - ReDoc",
#     )

############# FILES ###########################

@app.post("/upload_file")
async def upload_file(file: UploadFile = File(...)):
    print(str(file))
    #TO DO: Add date str before file name
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    return JSONResponse(content={"message": "File uploaded successfully", "filename": file.filename, "content_type": file.content_type})

@app.get("/download_file/{filename}")
async def download_file(filename: str):
    file_name = filename
    # DEPENDS ON WHERE YOUR FILE LOCATES
    file_path = UPLOAD_FOLDER + "/" + file_name
    return FileResponse(path=file_path, media_type='application/octet-stream', filename=file_name)
################# END FILES ###################


################### FCM NOTIFICATIONS ############ 

service_acount_file ="ug-kla-konnect-firebase-adminsdk-fbsvc-f2479ab9d6.json"
credentials = service_account.Credentials.from_service_account_file(service_acount_file, scopes=["https://www.googleapis.com/auth/cloud-platform"])

@app.get('/get-access-token/', tags=["notification"])
def get_access_token():
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    return credentials.token

@app.post('/send-notification-post/', tags=["notification"])
def send_push(notification: FcmSchema):
    
    url = "https://fcm.googleapis.com/v1/projects/ug-kla-konnect/messages:send"
    data = {
        "message": {
            "token": notification.fcmid,
            "notification": {
                "title": notification.title,
                "body": notification.body
            }
        }
    }
    
    headers = {
        'Authorization': f'Bearer {get_access_token()}',
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, json=data)
    print("Successfully sent notification:", response)
    return response.json()

@app.get('/send-notification/', tags=["notification"])
def send_push_post(fcm_id, body, title):
    
    url = "https://fcm.googleapis.com/v1/projects/ug-kla-konnect/messages:send"
    data = {
        "message": {
            "token": fcm_id,
            "notification": {
                "title": title,
                "body": body
            }
        }
    }
    
    headers = {
        'Authorization': f'Bearer {get_access_token()}',
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, json=data)
    print("Successfully sent notification:", response)
    return response.json()

@app.get('/send-notification/topic/', tags=["notification"])
def send_push_post_topic(topic, body, title):
    
    url = "https://fcm.googleapis.com/v1/projects/ug-kla-konnect/messages:send"
    data = {
        "message": {
            "topic": topic,
            "notification": {
                "title": title,
                "body": body
            }
        }
    }
    
    headers = {
        'Authorization': f'Bearer {get_access_token()}',
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, json=data)
    print("Successfully sent notification:", response)
    return response.json()

################# END FCM NOTIFICATIONS ############

################ EMAILS #####################

# @app.get('/send-email/asynchronous', tags=["mailer"])
async def send_email_asynchronous(title: str, body: str, to: EmailStr):
    await send_email_async(title, to, body)
    # await send_email_async_test()
    return 'Success'

# @app.get('/send-email/backgroundtasks', tags=["mailer"])
def send_email_backgroundtasks(title: str, body: str, to: EmailStr):
    background_tasks = BackgroundTasks(),
    send_email_background(background_tasks, title, body, to)
    # return 'Success'

################ END EMAILS #################

################### USERS ###################

# response_model=List[UserSchema],

@app.get("/get_users",  tags=["user"])
async def get_all_users():
    query = users_table.select()
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            res.append({
                    "userid": result["id"],
                    "firstname": result["firstname"],
                    "lastname": result["lastname"],
                    "fcmid": result["fcmid"],
                    "username": result["username"],
                    "email": result["email"],
                    "gender": result["gender"],
                    "phone": result["phone"],                    
                    "mobile": result["mobile"],
                    "issuperadmin": result["issuperadmin"],
                    "isadmin": result["isadmin"],
                    "isengineer": result["isengineer"],
                    "isclerk": result["isclerk"],
                    "iscitizen": result["iscitizen"],
                    "status": result["status"]
                    })
    return res
    # else:
    #     raise HTTPException(status_code=204, detail='No users found')

@app.get("/users/default", response_model=Page[UserSchema], tags=["user"])
@app.get("/users/limit-offset",  response_model=LimitOffsetPage[UserSchema], tags=["user"])
async def get_all_users_paginate(params: Params = Depends(),):
    query = users_table.select()
    result = await database.fetch_all(query)
    # if result:
    return paginate(result)

@app.get("/users/stats", tags=["user"])
async def get_users_stats():
    citizens = 0
    engineers = 0
    clerks = 0
    admins = 0
    counter = 0
    query = users_table.select()
    results = await database.fetch_all(query)
    if results:
        for result in results:
            counter += 1

    clerkquery = users_table.select().where(users_table.c.isclerk == True)
    clerkresults = await database.fetch_all(clerkquery)
    if clerkresults:
        for result in clerkresults:
            clerks += 1
        
    citizensquery = users_table.select().where(users_table.c.iscitizen == True)
    citizensresults = await database.fetch_all(citizensquery)
    if citizensresults:
        for result in citizensresults:
            citizens += 1
    
    adminquery = users_table.select().where(users_table.c.isadmin == True)
    adminresults = await database.fetch_all(adminquery)
    if adminresults:
        for result in adminresults:
            admins += 1

    engineerquery = users_table.select().where(users_table.c.isengineer == True)
    engineerresults = await database.fetch_all(engineerquery)
    if engineerresults:
        for result in engineerresults:
            engineers += 1

    return {
        "citizens": citizens,
        "clerks": clerks,
        "admins": admins,
        "engineers": engineers,
        "total": counter
    }

@app.get("/users/count", tags=["user"])
async def get_users_count():
    counter = 0
    query = users_table.select()
    results = await database.fetch_all(query)
    if results:
        for result in results:
            counter += 1

    return counter


@app.get("/get_citizens", response_model=List[UserSchema], tags=["user"], dependencies=[Depends(jwtBearer())])
async def get_all_citizens():
    query = users_table.select().where(users_table.c.iscitizen == True)
    result = await database.fetch_all(query)
    if result:
        return result
    else:
        raise HTTPException(status_code=204, detail='No citizens found')


@app.get("/get_clerks", response_model=List[UserSchema], tags=["user"], dependencies=[Depends(jwtBearer())])
async def get_all_clerks():
    query = users_table.select().where(users_table.c.isclerk == True)
    result = await database.fetch_all(query)
    if result:
        return result
    else:
        raise HTTPException(status_code=204, detail='No clerks found')


@app.get("/get_engineers", response_model=List[UserSchema], tags=["user"], dependencies=[Depends(jwtBearer())])
async def get_all_engineers():
    query = users_table.select().where(users_table.c.isengineer == True)
    result = await database.fetch_all(query)
    if result:
        return result
    else:
        raise HTTPException(status_code=204, detail='No engineers found')

@app.get("/get_admins", response_model=List[UserSchema], tags=["user"], dependencies=[Depends(jwtBearer())])
async def get_all_admins():
    query = users_table.select().where(users_table.c.isadmin == True)
    result = await database.fetch_all(query)
    if result:
        return result
    else:
        raise HTTPException(status_code=204, detail='No admins found')


@app.get("/users/{userid}", response_model=UserSchema, tags=["user"], dependencies=[Depends(jwtBearer())])
async def get_user_by_id(userid: str):
    query = users_table.select().where(users_table.c.id == userid)
    result = await database.fetch_one(query)
    if result:
        # print(result["firstname"])
        return result
    else:
        return{"error": "Unkown User"}
        # raise HTTPException(status_code=404, detail='User not found')


@app.get("/users/photo/{userid}", tags=["user"], dependencies=[Depends(jwtBearer())])
async def get_user_photo_by_id(userid: str):
    query = users_table.select().where(users_table.c.id == userid)
    result = await database.fetch_one(query)
    if result:
        # print(result["firstname"])
        return result["photo"]
    else:
        return{"error": ""}
        # raise HTTPException(status_code=404, detail='User not found')


@app.get("/users/name/{userid}", tags=["user"], dependencies=[Depends(jwtBearer())])
async def get_usernames_by_id(userid: str):
    query = users_table.select().where(users_table.c.id == userid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["firstname"] + " " + result["lastname"]
        return fullname
    else:
        return "Unkown User"


@app.post("/user/login", tags=["user"])
async def user_login(user: UserLoginSchema = Body(default=None)):
    # data: OAuth2PasswordRequestForm = Depends()
    query = users_table.select().where(users_table.c.email == user.username)
    result = await database.fetch_one(query)
    if result:
        if result["password"] == user.password:
            if result["status"] == "1":
                return {
                    "userid": result["id"],
                    "firstname": result["firstname"],
                    "lastname": result["lastname"],
                    "fcmid": result["fcmid"],
                    "username": result["username"],
                    "email": result["email"],
                    "gender": result["gender"],
                    "phone": result["phone"],
                    "mobile": result["mobile"],
                    "address": result["address"],
                    "addresslat": result["addresslat"],
                    "addresslong": result["addresslong"],
                    "nin": result["nin"],
                    "dateofbirth": result["dateofbirth"],
                    "photo": result["photo"],
                    "isadmin": result["isadmin"],
                    "issuperadmin": result["issuperadmin"],
                    "isclerk": result["isclerk"],
                    "iscitizen": result["iscitizen"],
                    "isengineer": result["isengineer"],
                    "roleid": result["roleid"],
                    "datecreated": result["datecreated"],
                    "incidentscount": await get_incidentcounts_by_userid(result["id"]),
                    # "incidentscount": 0,
                    "token": signJWT(user.username),
                    "status": result["status"]
                }
            else:
                raise HTTPException(
                    status_code=409, detail='User has not been verified')
    else:
        raise HTTPException(status_code=401, detail='Not authorized')
    # else:
    #     raise HTTPException(status_code=404, detail='User does not exist')


@app.post("/user/login/mobile", tags=["user"])
async def user_login(user: UserLoginSchema = Body(default=None)):
    # data: OAuth2PasswordRequestForm = Depends()
    query = users_table.select().where(users_table.c.phone == user.username)
    result = await database.fetch_one(query)
    if result:
        if result["password"] == user.password:
            if result["status"] == "1":
                return {
                    "userid": result["id"],
                    "firstname": result["firstname"],
                    "lastname": result["lastname"],
                    "firstname": result["firstname"],
                    "username": result["username"],
                    "email": result["email"],
                    "gender": result["gender"],
                    "phone": result["phone"],
                    "mobile": result["mobile"],
                    "address": result["address"],
                    "addresslat": result["addresslat"],
                    "addresslong": result["addresslong"],
                    "nin": result["nin"],
                    "dateofbirth": result["dateofbirth"],
                    "photo": result["photo"],
                    "isadmin": result["isadmin"],
                    "issuperadmin": result["issuperadmin"],
                    "isclerk": result["isclerk"],
                    "iscitizen": result["iscitizen"],
                    "roleid": result["roleid"],
                    "datecreated": result["datecreated"],
                    "incidentscount": await get_incidentcounts_by_userid(result["id"]),
                    # "incidentscount": 0,
                    "token": signJWT(user.username),
                    "status": result["status"]
                }
            else:
                raise HTTPException(
                    status_code=409, detail='User has not been verified')
    else:
        raise HTTPException(status_code=401, detail='Not authorized')


@app.get("/users/emailauth/{email}", tags=["user"])
async def user_email_authentication(email: EmailStr):
    query = users_table.select().where(users_table.c.email == email)
    result = await database.fetch_one(query)
    if result:
        return {
            "userid": result["id"],
            "firstname": result["firstname"],
            "lastname": result["lastname"],
            "firstname": result["firstname"],
            "username": result["username"],
            "email": result["email"],
            "gender": result["gender"],
            "phone": result["phone"],
            "mobile": result["mobile"],
            "address": result["address"],
            "addresslat": result["addresslat"],
            "addresslong": result["addresslong"],
            "nin": result["nin"],
            "dateofbirth": result["dateofbirth"],
            "photo": result["photo"],
            "isadmin": result["isadmin"],
            "issuperadmin": result["issuperadmin"],
            "isclerk": result["isclerk"],
            "iscitizen": result["iscitizen"],
            "roleid": result["roleid"],
            "token": signJWT(email),
            "status": result["status"]
        }
    else:
        raise HTTPException(status_code=401, detail='Not Authorized')


@app.get("/users/checkexistence/{email}", tags=["user"])
async def check_if_user_exists(email: str):
    query = users_table.select().where(users_table.c.email ==
                                       email)
    result = await database.fetch_one(query)
    if result:
        return True
    else:
        return False


@app.post("/users/signup", tags=["user"], status_code=201)
async def register_user(user: UserSignUpSchema, background_tasks: BackgroundTasks):
    gDate = datetime.datetime.now()
    date_of_birth_value = datetime.datetime.strptime(
        (user.dateofbirth), "%Y-%m-%d").date()

    existing_users_query = users_table.select().where(
        or_(
            users_table.c.email == user.email,
            users_table.c.phone == user.phone
        )
    )
    existing_users = await database.fetch_all(existing_users_query)

    for record in existing_users:
        if record["status"] != "2":
            raise HTTPException(
                status_code=409, detail="User already exists with this phone number or email.")

    digits = "0123456789"
    OTP = ""
    for i in range(4):
        OTP += digits[math.floor(random.random() * 10)]

    email_address = user.email
    sms_number = user.phone
    sms_message = f"Welcome to Kla Konnect! Kindly use " + OTP + " as the OTP to activate your account"
    sms_gateway_url = 'https://sms.dmarkmobile.com/v2/api/send_sms/?spname=spesho@dmarkmobile.com&sppass=t4x1sms&numbers=' + sms_number + '&msg=' + sms_message + '&type=json'.replace(" ", "%20")

    base_user_values = {
        "fcmid": user.fcmid,
        "username": user.username,
        "password": user.password,
        "firstname": user.firstname,
        "lastname": user.lastname,
        "phone": user.phone,
        "mobile": user.mobile,
        "dateofbirth": date_of_birth_value,
        "address": user.address,
        "addresslat": user.addresslat,
        "addresslong": user.addresslong,
        "photo": user.photo,
        "email": user.email,
        "nin": user.nin,
        "gender": user.gender,
        "isclerk": user.isclerk,
        "isengineer": user.isengineer,
        "iscitizen": user.iscitizen,
        "issuperadmin": user.issuperadmin,
        "isadmin": user.isadmin,
        "status": "1"
    }

    if existing_users:
        inactive_user = existing_users[0]
        for record in existing_users:
            if record["email"] == user.email:
                inactive_user = record
                break
            if record["phone"] == user.phone:
                inactive_user = record
        target_user_id = inactive_user["id"]
        update_values = {**base_user_values, "dateupdated": gDate}
        await database.execute(
            users_table.update()
            .where(users_table.c.id == target_user_id)
            .values(**update_values)
        )
        date_created_value = inactive_user["datecreated"]
    else:
        target_user_id = str(uuid.uuid1())
        insert_values = {**base_user_values, "id": target_user_id, "datecreated": gDate}
        await database.execute(users_table.insert().values(**insert_values))
        date_created_value = gDate

    parsed_url = urlparse(sms_gateway_url).query
    parse_qs(parsed_url)
    contents = urllib.request.urlopen(sms_gateway_url.replace(" ", "%20")).read()

    print(OTP)
    print(user.phone)
    print(sms_message)
    print(str(contents))

    background_tasks.add_task(send_welcome_email, email_address, user.firstname, OTP)
    return {
        **user.dict(),
        "id": target_user_id,
        "datecreated": date_created_value,
        "otp": OTP,
        "token": signJWT(user.username),
        "status": "1"
    }


@app.post("/users/update", response_model=UserUpdateSchema, tags=["user"], dependencies=[Depends(jwtBearer())])
async def update_user(user: UserUpdateSchema):
    # dateofbirth=datetime.datetime.strptime((user.dateofbirth), "%Y-%m-%d").date(),
    gDate = datetime.datetime.now()
    query = users_table.update().\
        where(users_table.c.id == user.id).\
        values(
            fcmid=user.fcmid,
            username=user.username,
            password=user.password,
            firstname=user.firstname,
            lastname=user.lastname,
            phone=user.phone,
            mobile=user.mobile,
            dateofbirth=datetime.datetime.strptime(
                (user.dateofbirth), "%Y-%m-%d").date(),
            address=user.address,
            addresslat=user.addresslat,
            addresslong=user.addresslong,
            photo=user.photo,
            email=user.email,
            nin=user.nin,
            gender=user.gender,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_user_by_id(user.id)

@app.post("/users/updatefcmid", response_model=UserUpdateSchema, tags=["user"], dependencies=[Depends(jwtBearer())])
async def update_userfcmid(user: UserFcmSchema):
    gDate = datetime.datetime.now()
    query = users_table.update().\
        where(users_table.c.id == user.userid).\
        values(
            fcmid=user.fcmid,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_user_by_id(user.id)

@app.post("/users/updateprofile", response_model=UserUpdateSchema, tags=["user"], dependencies=[Depends(jwtBearer())])
async def update_userprofile(user: UserUpdateProfileSchema):
    gDate = datetime.datetime.now()
    query = users_table.update().\
        where(users_table.c.id == user.id).\
        values(
            firstname=user.firstname,
            lastname=user.lastname,
            phone=user.phone,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_user_by_id(user.id)

@app.post("/users/updateuserrights", tags=["user"], dependencies=[Depends(jwtBearer())])
async def update_user_rights(user: UserUpdateRightsSchema):
    gDate = datetime.datetime.now()
    query = users_table.update().\
        where(users_table.c.id == user.id).\
        values(
            isclerk=user.isclerk,
            iscitizen=user.iscitizen,
            # issuperadmin=user.issuperadmin,
            isadmin=user.isadmin,
            isengineer=user.isengineer,
    )

    await database.execute(query)
    return {
        "success": "User rights updated"
    }

@app.post("/users/deactivate", tags=["user"], dependencies=[Depends(jwtBearer())])
async def deactivate_user_account(payload: UserDeactivateSchema):
    user = await database.fetch_one(users_table.select().where(users_table.c.id == payload.userid))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    gDate = datetime.datetime.now()
    async with database.transaction():
        await database.execute(
            users_table.update()
            .where(users_table.c.id == payload.userid)
            .values(status="2", dateupdated=gDate, updatedby=payload.updatedby)
        )
        await database.execute(
            incidents_table.update()
            .where(incidents_table.c.createdby == payload.userid)
            .values(status="2", dateupdated=gDate, updatedby=payload.updatedby)
        )
        await database.execute(
            user_trips_table.update()
            .where(user_trips_table.c.createdby == payload.userid)
            .values(status="2", dateupdated=gDate, updatedby=payload.updatedby)
        )

    return {
        "message": "User account and related records deactivated"
    }

@app.get("/users/resetpassword/{email}", tags=["user"])
async def reset_password(email: str, background_tasks: BackgroundTasks):
    # dateofbirth=datetime.datetime.strptime((user.dateofbirth), "%Y-%m-%d").date(),
    gDate = datetime.datetime.now()
    query = users_table.select().where(users_table.c.email ==
                                       email)
    result = await database.fetch_one(query)
    if result:
        first_name = result["firstname"]
        email = result["email"]
        sms_number = result["phone"].replace("+", "")
        email_address=result["email"]
        userid = result["id"]
        password = result["password"]
        # otp = await generate_otp(userid)
        digits = "0123456789"
        otp = ""
        for i in range(4):
            otp += digits[math.floor(random.random() * 10)]

        sms_message = f"Kindly use "+otp+" as the OTP for resetting your Kla Konnect password"
        print(otp)
        print(sms_number)
        print(sms_message)
        sms_gateway_url = 'https://sms.dmarkmobile.com/v2/api/send_sms/?spname=spesho@dmarkmobile.com&sppass=t4x1sms&numbers='+sms_number+'&msg='+sms_message+'&type=json'.replace(" ", "%20")
        parsed_url = urlparse(sms_gateway_url).query
        parse_qs(parsed_url)
        contents = urllib.request.urlopen(sms_gateway_url.replace(" ", "%20")).read()

        print(str(contents))
        # await send_email_asynchronous("Kla Konnect Password Reset", sms_message, email_address)
        background_tasks.add_task(send_password_reset_email, email_address, first_name, otp)
        # contents = urllib.request.urlopen(parsed_url).read()
        # await send_email_backgroundtasks(BackgroundTasks, "Kla Konnect Password Reset", sms_message, email_address)
        # await send_email_asynchronous("Kla Connect Password Reset", "The OTP for resetting your password is "+otp + "\n", email) .replace(" ", "%20")
        # password key returned as gateway in case of M.I.T.M attack
        return {
            "otp": otp,
            "phone": result["phone"],
            "gateway": password,
            "email": email,
            "userid": userid,
        }
    else:
        raise HTTPException(
            status_code=204, detail="User does not exist.")

@app.get("/users/searchuser/{name}", tags=["user"])
async def search_user_by_name(name: str):
    query = users_table.select()
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            if result["firstname"] and name.lower() in str(result["firstname"]).lower():
                res.append(result)
            else:
                if result["lastname"] and name.lower() in str(result["lastname"]).lower():
                    res.append(result)
    return res


@app.post("/users/archive", response_model=UserUpdateSchema, tags=["user"], dependencies=[Depends(jwtBearer())])
async def archive_user(userid: str):
    gDate = datetime.datetime.now()
    query = users_table.update().\
        where(users_table.c.id == userid).\
        values(
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_user_by_id(userid)


@app.post("/users/restore", response_model=UserUpdateSchema, tags=["user"], dependencies=[Depends(jwtBearer())])
async def restore_user(userid: str):
    gDate = datetime.datetime.now()
    query = users_table.update().\
        where(users_table.c.id == userid).\
        values(
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_user_by_id(userid)


@app.delete("/users/{userid}", tags=["user"], dependencies=[Depends(jwtBearer())])
async def delete_user(userid: str):
    query = users_table.delete().where(users_table.c.id == userid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This user has been deleted!"
    }


@app.get("/users/activate/{userid}", response_model=UserUpdateSchema, tags=["user"], dependencies=[Depends(jwtBearer())])
async def activate_user(userid: str):
    gDate = datetime.datetime.now()
    query = users_table.update().\
        where(users_table.c.id == userid).\
        values(
            status="1",
            dateupdated=gDate
    )
    await database.execute(query)
    return await get_user_by_id(userid)


@app.post("/users/otp", tags=["user"], dependencies=[Depends(jwtBearer())])
async def generate_otp(userid: str):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    expiry = datetime.datetime.now() + datetime.timedelta(hours=1)
    digits = "0123456789"
    OTP = ""
    queryuser = users_table.select().where(users_table.c.id == userid)
    result = await database.fetch_one(queryuser)
    if result:
        for i in range(4):
            OTP += digits[math.floor(random.random() * 10)]
        query = otps_table.insert().values(
            id=gID,
            userid=userid,
            sessionid="",
            otpcode=OTP,
            otpfailedcount=0,
            expiry=expiry,
            datecreated=gDate,
            status="1"
        )
        await database.execute(query)
        return OTP
    else:
        raise HTTPException(
            status_code=204, detail="User does not exist.")


@app.post("/users/verify", tags=["user"], dependencies=[Depends(jwtBearer())])
async def verify_otp(otp_obj: OtpVerifySchema):
    gDate = datetime.datetime.now()
    expiry = datetime.datetime.now() + datetime.timedelta(hours=1)
    queryuser = users_table.select().where(users_table.c.email == otp_obj.email)
    resultuser = await database.fetch_one(queryuser)
    if resultuser:
        userid = resultuser["id"]
        queryotp = otps_table.select().where(otps_table.c.otpcode ==
                                             otp_obj.otpcode and otps_table.c.userid == userid)
        resultotp = await database.fetch_one(queryotp)
        if resultotp:
            queryotppass = otps_table.update().\
                where(otps_table.c.otpcode == otp_obj.otpcode).\
                values(
                    status="0",
                    dateupdated=gDate
            )
            await database.execute(queryotppass)

            await update_password(userid, otp_obj.password)
            return "User verified successfully"
    else:
        raise HTTPException(
            status_code=401, detail="Invalid OTP Code.")


@app.post("/users/updatepassword", tags=["user"])
async def update_password(user: UserUpdatePasswordSchema):
    gDate = datetime.datetime.now()
    query = users_table.update().\
        where(users_table.c.id == user.userid).\
        values(
            password=user.password,
            dateupdated=gDate
    )

    await database.execute(query)
    return {
        "success": "Password updated successfully."
    }

@app.post("/users/updatephoto", tags=["user"], dependencies=[Depends(jwtBearer())])
async def update_photo(userid: str, photo: str):
    gDate = datetime.datetime.now()
    query = users_table.update().\
        where(users_table.c.id == userid).\
        values(
            photo=photo,
            dateupdated=gDate
    )

    await database.execute(query)
    return {
        "success": "Photo updated successfully."
    }

################## END USERS ###################

##################### INCIDENTS ######################

@app.get("/incidents",  response_model=List[IncidentWithCategorySchema], tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def get_all_incidents():
    # query = incidents_table.select().order_by(desc(incidents_table.c.datecreated))
    # Perform the JOIN
    j = join(
        incidents_table,
        incidentcategories_table,
        incidents_table.c.incidentcategoryid == incidentcategories_table.c.id
    )

    # Select desired fields
    query = select(
        incidents_table.c.id.label("incident_id"),
        incidents_table.c.name.label("incident_name"),
        incidents_table.c.description.label("incident_description"),
        incidents_table.c.isemergency,
        incidents_table.c.iscityreport,
        incidents_table.c.address,
        incidents_table.c.addresslat,
        incidents_table.c.addresslong,
        incidents_table.c.file1,
        incidents_table.c.file2,
        incidents_table.c.file3,
        incidents_table.c.file4,
        incidents_table.c.file5,
        incidents_table.c.upvotes,
        incidentcategories_table.c.name.label("category_name"),
        incidentcategories_table.c.description.label("category_description"),
        incidentcategories_table.c.image.label("category_image"),
        incidentcategories_table.c.autoapprove.label("category_autoapprove"),
        incidentcategories_table.c.doesexpire.label("category_doesexpire"),
        incidentcategories_table.c.hourstoexpire.label("category_hourstoexpire"),
        incidents_table.c.startdate,
        incidents_table.c.enddate,
        incidents_table.c.cause,
        incidents_table.c.fulldisruption,
        incidents_table.c.createdby,
        incidents_table.c.datecreated,
        incidents_table.c.dateupdated,
        incidents_table.c.updatedby,
        incidents_table.c.status
    ).select_from(j).order_by(desc(incidents_table.c.datecreated))

    result = await database.fetch_all(query)
    if result:
        return result
    else:
        raise HTTPException(
            status_code=204, detail="No incidents nearby.")
    

@app.get("/incidents/default", response_model=Page[IncidentWithCategorySchema], tags=["incidents"])
@app.get("/incidents/limit-offset", response_model=LimitOffsetPage[IncidentWithCategorySchema], tags=["incidents"])
async def get_all_incidents_paginate(params: Params = Depends()):
    # Perform the JOIN
    j = join(
        incidents_table,
        incidentcategories_table,
        incidents_table.c.incidentcategoryid == incidentcategories_table.c.id
    )

    # Select desired fields
    query = select(
        incidents_table.c.id.label("incident_id"),
        incidents_table.c.name.label("incident_name"),
        incidents_table.c.description.label("incident_description"),
        incidents_table.c.isemergency,
        incidents_table.c.iscityreport,
        incidents_table.c.address,
        incidents_table.c.addresslat,
        incidents_table.c.addresslong,
        incidents_table.c.file1,
        incidents_table.c.file2,
        incidents_table.c.file3,
        incidents_table.c.file4,
        incidents_table.c.file5,
        incidents_table.c.upvotes,
        incidentcategories_table.c.name.label("category_name"),
        incidentcategories_table.c.description.label("category_description"),
        incidentcategories_table.c.image.label("category_image"),
        incidentcategories_table.c.autoapprove.label("category_autoapprove"),
        incidentcategories_table.c.doesexpire.label("category_doesexpire"),
        incidentcategories_table.c.hourstoexpire.label("category_hourstoexpire"),
        incidents_table.c.startdate,
        incidents_table.c.enddate,
        incidents_table.c.cause,
        incidents_table.c.fulldisruption,
        incidents_table.c.createdby,
        incidents_table.c.datecreated,
        incidents_table.c.dateupdated,
        incidents_table.c.updatedby,
        incidents_table.c.status
    ).select_from(j)

    result = await database.fetch_all(query)
    return paginate(result)

@app.get("/incidents/status/default/{status}", response_model=Page[IncidentWithCategorySchema], tags=["incidents"])
@app.get("/incidents/status/limit-offset/{status}",  response_model=LimitOffsetPage[IncidentWithCategorySchema], tags=["incidents"])
async def get_all_incidents_by_status_paginate(status: str, params: Params = Depends(),):
    # Perform the JOIN
    j = join(
        incidents_table,
        incidentcategories_table,
        incidents_table.c.incidentcategoryid == incidentcategories_table.c.id
    )

    # Select desired fields
    query = select(
        incidents_table.c.id.label("incident_id"),
        incidents_table.c.name.label("incident_name"),
        incidents_table.c.description.label("incident_description"),
        incidents_table.c.isemergency,
        incidents_table.c.iscityreport,
        incidents_table.c.address,
        incidents_table.c.addresslat,
        incidents_table.c.addresslong,
        incidents_table.c.file1,
        incidents_table.c.file2,
        incidents_table.c.file3,
        incidents_table.c.file4,
        incidents_table.c.file5,
        incidents_table.c.upvotes,
        incidentcategories_table.c.name.label("category_name"),
        incidentcategories_table.c.description.label("category_description"),
        incidentcategories_table.c.image.label("category_image"),
        incidentcategories_table.c.autoapprove.label("category_autoapprove"),
        incidentcategories_table.c.doesexpire.label("category_doesexpire"),
        incidentcategories_table.c.hourstoexpire.label("category_hourstoexpire"),
        incidents_table.c.startdate,
        incidents_table.c.enddate,
        incidents_table.c.cause,
        incidents_table.c.fulldisruption,
        incidents_table.c.createdby,
        incidents_table.c.datecreated,
        incidents_table.c.dateupdated,
        incidents_table.c.updatedby,
        incidents_table.c.status
    ).select_from(j).where(incidents_table.c.status == status).order_by(desc(incidents_table.c.datecreated))

    # query = incidents_table.select().where(incidents_table.c.status == "1").order_by(desc(incidents_table.c.datecreated))
    result = await database.fetch_all(query)
    return paginate(result)


@app.get("/incidents/count", tags=["incidents"])
async def get_incidents_count():
    counter = 0
    query = incidents_table.select()
    results = await database.fetch_all(query)
    if results:
        for result in results:
            counter += 1

    return counter

@app.get("/incidents/searchincident/{name}", tags=["incidents"])
async def search_incidents_by_title_and_category(name: str):
    query = incidents_table.select()
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            if result["name"] and name.lower() in str(result["name"]).lower():
                res.append(result)
            elif result["address"] and name.lower() in str(result["address"]).lower():
                    res.append(result)
            else:
                if result["incidentcategoryid"] and name.lower() in str(result["incidentcategoryid"]).lower():
                    res.append(result)
    return res

@app.get("/incidents/stats", tags=["incidents"])
async def get_incidents_stats():
    approved_today_counter = 0
    resolved_today_counter = 0
    rejected_today_counter = 0
    unapproved_today_counter = 0
    approvedcounter = 0
    resolvedcounter = 0
    rejectedcounter = 0
    unapprovedcounter = 0
    counter = 0
    query = incidents_table.select()
    results = await database.fetch_all(query)
    if results:
        for result in results:
            counter += 1

    unapprovedquery = incidents_table.select().where(incidents_table.c.status == "0")
    unapprovedresults = await database.fetch_all(unapprovedquery)
    if unapprovedresults:
        for result in unapprovedresults:
            unapprovedcounter += 1
            if result["datecreated"] == datetime.datetime.now():
                unapproved_today_counter += 1
        
    approvedquery = incidents_table.select().where(incidents_table.c.status == "1")
    approvedresults = await database.fetch_all(approvedquery)
    if approvedresults:
        for result in approvedresults:
            approvedcounter += 1
            if result["dateupdated"] == datetime.datetime.now():
                approved_today_counter += 1
    
    rejectedquery = incidents_table.select().where(incidents_table.c.status == "3")
    rejectedresults = await database.fetch_all(rejectedquery)
    if rejectedresults:
        for result in rejectedresults:
            rejectedcounter += 1
            if result["dateupdated"] == datetime.datetime.now():
                rejected_today_counter += 1

######################## DASHBOARD STATS #############################

@app.get("/dash/stats/incidents-by-category", tags=["dash/stats"])
async def get_incidents_by_category_stats():
    """
    Returns incident distribution by category for a pie/donut chart.
    Response shape:
    {
        "labels": ["Potholes", "Traffic Jam", ...],
        "series": [120, 85, ...],
        "percents": [52.2, 37.0, ...],
        "total": 230
    }
    """
    # Join incidents with categories and aggregate counts per category
    j = join(
        incidents_table,
        incidentcategories_table,
        incidents_table.c.incidentcategoryid == incidentcategories_table.c.id
    )

    query = (
        select(
            incidentcategories_table.c.name.label("category_name"),
            func.count(incidents_table.c.id).label("count")
        )
        .select_from(j)
        .where(incidents_table.c.iscityreport == False)
        .group_by(incidentcategories_table.c.name)
        .order_by(func.count(incidents_table.c.id).desc())
    )

    rows = await database.fetch_all(query)
    if not rows:
        return {"labels": [], "series": [], "percents": [], "total": 0}

    labels = [row["category_name"] or "Uncategorized" for row in rows]
    series = [int(row["count"]) for row in rows]
    total = sum(series)
    percents = [round((c / total) * 100, 1) if total else 0 for c in series]

    return {
        "labels": labels,
        "series": series,
        "percents": percents,
        "total": total,
    }

@app.get("/dash/stats/incidents-by-month-this-year", tags=["dash/stats"])
async def get_incidents_by_month_this_year():
    """
    Returns incident count by month for the current year.
    Response shape:
    {
        "labels": ["Jan", "Feb", "Mar", ...],
        "series": [10, 15, 23, ...],
        "total": 150
    }
    """
    # Get current year
    current_year = datetime.datetime.now().year
    
    # Extract month and count incidents
    query = (
        select(
            func.extract('month', incidents_table.c.datecreated).label("month"),
            func.count(incidents_table.c.id).label("count")
        )
        .where(func.extract('year', incidents_table.c.datecreated) == current_year)
        .group_by("month")
        .order_by("month")
    )
    
    rows = await database.fetch_all(query)
    if not rows:
        return {"labels": [], "series": [], "total": 0}
    
    # Map month numbers to names
    month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    # Create results for all 12 months (fill with 0 if no data)
    data = {int(row["month"]): int(row["count"]) for row in rows}
    labels = [month_names[i] for i in range(1, 13)]
    series = [data.get(i, 0) for i in range(1, 13)]
    
    total = sum(series)
    
    return {
        "labels": labels,
        "series": series,
        "total": total,
    }

@app.get("/dash/stats/incidents-by-quarter-this-year", tags=["dash/stats"])
async def get_incidents_by_quarter_this_year():
    """
    Returns incident count by quarter for the current year.
    Response shape:
    {
        "labels": ["Q1", "Q2", "Q3", "Q4"],
        "series": [45, 67, 89, 34],
        "total": 235
    }
    """
    # Get current year
    current_year = datetime.datetime.now().year
    
    # Get all incidents for this year
    query = (
        select(
            func.extract('month', incidents_table.c.datecreated).label("month"),
            incidents_table.c.id
        )
        .where(func.extract('year', incidents_table.c.datecreated) == current_year)
    )
    
    rows = await database.fetch_all(query)
    
    # Process quarters in Python
    quarter_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    
    for row in rows:
        month = int(row["month"])
        if month <= 3:
            quarter_counts[1] += 1
        elif month <= 6:
            quarter_counts[2] += 1
        elif month <= 9:
            quarter_counts[3] += 1
        else:
            quarter_counts[4] += 1
    
    labels = ["Q1", "Q2", "Q3", "Q4"]
    series = [quarter_counts[i] for i in range(1, 5)]
    total = sum(series)
    
    return {
        "labels": labels,
        "series": series,
        "total": total,
    }

@app.get("/dash/stats/incidents-by-year", tags=["dash/stats"])
async def get_incidents_by_year():
    """
    Returns incident count for all available years.
    Response shape:
    {
        "labels": ["2020", "2021", "2022", ...],
        "series": [150, 234, 345, ...],
        "total": 729
    }
    """
    # Extract year and count incidents
    query = (
        select(
            func.extract('year', incidents_table.c.datecreated).label("year"),
            func.count(incidents_table.c.id).label("count")
        )
        .group_by("year")
        .order_by("year")
    )
    
    rows = await database.fetch_all(query)
    if not rows:
        return {"labels": [], "series": [], "total": 0}
    
    labels = [str(int(row["year"])) for row in rows]
    series = [int(row["count"]) for row in rows]
    total = sum(series)
    
    return {
        "labels": labels,
        "series": series,
        "total": total,
    }


@app.get("/dash/stats/incident-stats", tags=["dash/stats"])
async def get_incident_status_stats():
    """
    Returns incident counts by status overall and for today.

    Response shape:
    {
        "overall": {"0": n, "1": n, "2": n, "3": n, "total": n_total},
        "today":   {"0": n, "1": n, "2": n, "3": n, "total": n_total}
    }
    """
    # Helper to build a status->count dictionary
    async def fetch_counts(where_clauses=None):
        where_clauses = where_clauses or []
        base = select(
            incidents_table.c.status.label("status"),
            func.count(incidents_table.c.id).label("count")
        ).group_by(incidents_table.c.status)

        # Only incidents (exclude city reports)
        base = base.where(incidents_table.c.iscityreport == False)

        # Apply filters if provided
        for clause in where_clauses:
            base = base.where(clause)

        rows = await database.fetch_all(base)

        # Map numeric codes to human-readable labels
        status_labels = {
            "0": "archived",
            "1": "published",
            "2": "resolved",
            "3": "draft" if False else "rejected"
        }

        # Initialize all known labels to 0
        counts_by_label = {label: 0 for label in set(status_labels.values())}

        total = 0
        for row in rows:
            code = str(row["status"]) if row["status"] is not None else ""
            label = status_labels.get(code, code)
            value = int(row["count"]) if row["count"] is not None else 0
            counts_by_label[label] = counts_by_label.get(label, 0) + value
            total += value

        counts_by_label["total"] = total
        return counts_by_label

    # Overall counts (incidents only)
    overall_counts = await fetch_counts()

    # Today counts (from start of today to start of tomorrow)
    start_today = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    start_tomorrow = start_today + datetime.timedelta(days=1)
    today_counts = await fetch_counts([
        (incidents_table.c.datecreated >= start_today) & (incidents_table.c.datecreated < start_tomorrow)
    ])

    return {"overall": overall_counts, "today": today_counts}

    resolvedquery = incidents_table.select().where(incidents_table.c.status == "2")
    resolvedresults = await database.fetch_all(resolvedquery)
    if resolvedresults:
        for result in resolvedresults:
            resolvedcounter += 1
            if result["dateupdated"] == datetime.datetime.now():
                resolved_today_counter += 1

    return {
        "unapproved": unapprovedcounter,
        "unapproved_today": unapproved_today_counter,
        "approved": approvedcounter,
        "approved_today": approved_today_counter,
        "resolved": resolvedcounter,
        "resolved_today": resolved_today_counter,
        "rejected": rejectedcounter,
        "rejected_today": rejected_today_counter,
        "total": counter
    }

@app.get("/incidents/{incidentid}", response_model=IncidentSchema, tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def get_incident_by_id(incidentid: str):
    query = incidents_table.select().where(incidents_table.c.id == incidentid)
    result = await database.fetch_one(query)
    if result:
        incidentcategory = await get_incident_category_name_by_id(result["incidentcategoryid"])
        return {
            "id": result["id"],
            "name": result["name"],
            "description": result["description"],
            "incidentcategoryid": "",
            "incidentcategory": result["incidentcategoryid"],
            "incidentcategoryobj": await get_incident_category_by_id(result["incidentcategoryid"]),
            "address": result["address"],
            "addresslat": result["addresslat"],
            "addresslong": result["addresslong"],
            "isemergency": result["isemergency"],
            "iscityreport": result["iscityreport"],
            "file1": result["file1"],
            "file2": result["file2"],
            "file3": result["file3"],
            "file4": result["file4"],
            "file5": result["file5"],
            "datecreated": result["datecreated"],
            "createdby": result["createdby"],
            "createdbyobj": await get_user_by_id(result["createdby"]),
            "dateupdated": result["dateupdated"],
            "updatedby": result["updatedby"],
            "status": result["status"],
            "cause": result["cause"],
            "fulldisruption": result["fulldisruption"],
        }


@app.get("/incidents/name/{incidentid}", tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def get_incidentname_by_id(incidentid: str):
    query = incidents_table.select().where(incidents_table.c.id == incidentid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["name"]
        return fullname
    else:
        return "Unkown Incident"


@app.get("/incidents/user/{userid}", tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def get_incidents_by_userid(userid: str):
    query = incidents_table.select().where(incidents_table.c.createdby == userid)
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            res.append(await get_incident_by_id(result["id"]))
        return res
    else:
        raise HTTPException(
            status_code=204, detail="User has not posted any incidents.")

@app.get("/incidents/photo/{incidentid}", tags=["user"], dependencies=[Depends(jwtBearer())])
async def get_incident_photo_by_id(incidentid: str):
    query = incidents_table.select().where(incidents_table.c.id == incidentid)
    result = await database.fetch_one(query)
    if result:
        # print(result["firstname"])
        return result["file1"]
    else:
        return{"error": "No photo available"}
        # raise HTTPException(status_code=404, detail='User not found')

@app.get("/incidents/usercount/{userid}", tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def get_incidentcounts_by_userid(userid: str):
    query = incidents_table.select().where(incidents_table.c.createdby == userid)
    results = await database.fetch_all(query)
    res = 0
    if results:
        for result in results:
            res += 1

    return res


@app.post("/incidents/register", response_model=IncidentSchema, tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def register_incident(incident: IncidentSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()

    # Duplicate detection helpers
    def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000.0  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    radius_m = 500.0
    time_window_minutes = 5
    time_threshold = gDate - datetime.timedelta(minutes=time_window_minutes)

    # Join category to apply expiry logic
    j = incidents_table.join(incidentcategories_table, incidents_table.c.incidentcategoryid == incidentcategories_table.c.id)
    candidate_query = (
        select(
            incidents_table.c.id,
            incidents_table.c.name,
            incidents_table.c.description,
            incidents_table.c.isemergency,
            incidents_table.c.iscityreport,
            incidents_table.c.incidentcategoryid,
            incidents_table.c.address,
            incidents_table.c.addresslat,
            incidents_table.c.addresslong,
            incidents_table.c.file1,
            incidents_table.c.file2,
            incidents_table.c.file3,
            incidents_table.c.file4,
            incidents_table.c.file5,
            incidents_table.c.upvotes,
            incidents_table.c.createdby,
            incidents_table.c.datecreated,
            incidents_table.c.dateupdated,
            incidents_table.c.updatedby,
            incidents_table.c.status,
            incidents_table.c.startdate,
            incidents_table.c.enddate,
            incidentcategories_table.c.doesexpire.label("category_doesexpire"),
            incidentcategories_table.c.hourstoexpire.label("category_hourstoexpire"),
        )
        .select_from(j)
        .where(
            (incidents_table.c.incidentcategoryid == incident.incidentcategoryid)
            & (
                (incidents_table.c.datecreated >= time_threshold)
                | (incidents_table.c.createdby == incident.createdby)
            )
        )
        .order_by(desc(incidents_table.c.datecreated))
    )
    candidates = await database.fetch_all(candidate_query)

    same_user_duplicate = None
    nearby_same_category = None

    for row in candidates:
        try:
            row_lat = float(row["addresslat"]) if row["addresslat"] is not None else None
            row_lon = float(row["addresslong"]) if row["addresslong"] is not None else None
        except Exception:
            row_lat, row_lon = None, None

        if row_lat is None or row_lon is None:
            continue

        distance_m = haversine_distance_meters(
            float(incident.addresslat), float(incident.addresslong), row_lat, row_lon
        )
        minutes_diff = abs((gDate - row["datecreated"]).total_seconds()) / 60.0 if row["datecreated"] else 9999
        is_same_user = (row["createdby"] == incident.createdby)

        # Skip inactive statuses
        if str(row["status"]) in ("0", "2"):
            continue

        # Skip expired incidents if category expires
        does_expire = bool(row["category_doesexpire"]) if "category_doesexpire" in row.keys() else False
        hours_to_expire = row["category_hourstoexpire"] if "category_hourstoexpire" in row.keys() else None
        is_expired = False
        if does_expire and hours_to_expire is not None:
            try:
                expiry_time = row["datecreated"] + datetime.timedelta(hours=int(hours_to_expire))
                if gDate >= expiry_time:
                    is_expired = True
            except Exception:
                is_expired = False
        if is_expired:
            continue

        # Rule 1: Same user, similar coordinates within 500m OR within 5 minutes → duplicate
        if is_same_user and (distance_m <= radius_m or minutes_diff <= time_window_minutes):
            same_user_duplicate = row
            break

        # Rule 2: Different user, same category within 500m → treat as success but link to existing
        if (not is_same_user) and (distance_m <= radius_m):
            if nearby_same_category is None:
                nearby_same_category = (row, distance_m)
            elif distance_m < nearby_same_category[1]:
                nearby_same_category = (row, distance_m)

    def build_response(refreshed: dict) -> dict:
        return {
            "id": refreshed["id"],
            "name": refreshed["name"],
            "description": refreshed["description"],
            "incidentcategoryid": refreshed["incidentcategoryid"],
            "address": refreshed["address"],
            "addresslat": refreshed["addresslat"],
            "addresslong": refreshed["addresslong"],
            "file1": refreshed["file1"],
            "file2": refreshed["file2"],
            "file3": refreshed["file3"],
            "file4": refreshed["file4"],
            "file5": refreshed["file5"],
            "upvotes": refreshed["upvotes"],
            "isemergency": refreshed["isemergency"],
            "iscityreport": refreshed["iscityreport"],
            "startdate": refreshed["startdate"],
            "enddate": refreshed["enddate"],
            "cause": refreshed.get("cause"),
            "fulldisruption": refreshed.get("fulldisruption"),
            "createdby": refreshed["createdby"],
            "datecreated": refreshed["datecreated"],
            "dateupdated": refreshed["dateupdated"],
            "updatedby": refreshed["updatedby"],
            "status": refreshed["status"],
        }

    async def upvote_and_return(existing_id: str) -> dict:
        await database.execute(
            incidents_table.update()
            .where(incidents_table.c.id == existing_id)
            .values(
                upvotes=(func.coalesce(incidents_table.c.upvotes, 0) + 1),
                dateupdated=gDate,
                updatedby=incident.createdby,
            )
        )
        refreshed = await database.fetch_one(incidents_table.select().where(incidents_table.c.id == existing_id))
        return build_response(refreshed)

    if same_user_duplicate is not None:
        return await upvote_and_return(same_user_duplicate["id"])

    if nearby_same_category is not None:
        existing, _ = nearby_same_category
        return await upvote_and_return(existing["id"])

    # Auto-set startdate/enddate from category expiry if not provided
    incident_startdate = incident.startdate
    incident_enddate = incident.enddate

    if incident_startdate is None or incident_enddate is None:
        category_row = await database.fetch_one(
            select(incidentcategories_table).where(incidentcategories_table.c.id == incident.incidentcategoryid)
        )
        if category_row and bool(category_row["doesexpire"]) and category_row["hourstoexpire"] is not None:
            if incident_startdate is None:
                incident_startdate = gDate
            if incident_enddate is None:
                incident_enddate = gDate + datetime.timedelta(hours=int(category_row["hourstoexpire"]))

    query = incidents_table.insert().values(
        id=gID,
        name=incident.name,
        description=incident.description,
        isemergency=incident.isemergency,
        iscityreport=incident.iscityreport,
        incidentcategoryid=incident.incidentcategoryid,
        address=incident.address,
        addresslat=incident.addresslat,
        addresslong=incident.addresslong,
        file1=incident.file1,
        file2=incident.file2,
        file3=incident.file3,
        file4=incident.file4,
        file5=incident.file5,
        createdby=incident.createdby,
        datecreated=gDate,
        status=incident.status,
        startdate=incident_startdate,
        enddate=incident_enddate,
        cause=incident.cause,
        fulldisruption=incident.fulldisruption,
    )

    await database.execute(query)
    return {
        **incident.dict(),
        "id": gID,
        "datecreated": gDate,
        "startdate": incident_startdate,
        "enddate": incident_enddate,
    }


@app.post("/incidents/update", response_model=IncidentUpdateSchema, tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def update_incident(incident: IncidentUpdateSchema):
    gDate = datetime.datetime.now()
    query = incidents_table.update().\
        where(incidents_table.c.id == incident.id).\
        values(
            name=incident.name,
            description=incident.description,
            isemergency=incident.isemergency,
            iscityreport=incident.iscityreport,
            incidentcategoryid=incident.incidentcategoryid,
            address=incident.address,
            addresslat=incident.addresslat,
            addresslong=incident.addresslong,
            file1=incident.file1,
            file2=incident.file2,
            file3=incident.file3,
            file4=incident.file4,
            file5=incident.file5,
            cause=incident.cause,
            fulldisruption=incident.fulldisruption,
            updatedby=incident.updatedby,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_incident_by_id(incident.id)


@app.post("/incidents/archive", response_model=IncidentUpdateSchema, tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def archive_incident(incident: IncidentStatusSchema):
    gDate = datetime.datetime.now()
    query = incidents_table.update().\
        where(incidents_table.c.id == incident.id).\
        values(
            status="0",
            updatedby = incident.updatedby,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_incident_by_id(incident.id)


@app.post("/incidents/restore", response_model=IncidentUpdateSchema, tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def restore_incident(incident: IncidentStatusSchema):
    gDate = datetime.datetime.now()
    query = incidents_table.update().\
        where(incidents_table.c.id == incident.id).\
        values(
            status="1",
            updatedby = incident.updatedby,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_incident_by_id(incident.id)

@app.post("/incidents/resolve", response_model=IncidentUpdateSchema, tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def resolve_incident(incident: IncidentStatusSchema):
    gDate = datetime.datetime.now()
    query = incidents_table.update().\
        where(incidents_table.c.id == incident.id).\
        values(
            status="2",
            updatedby = incident.updatedby,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_incident_by_id(incident.id)

@app.post("/incidents/reject", response_model=IncidentUpdateSchema, tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def reject_incident(incident: IncidentStatusSchema):
    gDate = datetime.datetime.now()
    query = incidents_table.update().\
        where(incidents_table.c.id == incident.id).\
        values(
            status="3",
            updatedby = incident.updatedby,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_incident_by_id(incident.id)

@app.post("/incidents/state", response_model=IncidentUpdateSchema, tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def restore_incident(incident: IncidentUpdateStatusSchema):
    gDate = datetime.datetime.now()
    query = incidents_table.update().\
        where(incidents_table.c.id == incident.id).\
        values(
            status=incident.status,
            updatedby = incident.updatedby,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_incident_by_id(incident.id)


@app.delete("/incidents/{incidentid}", tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def delete_incident(incidentid: str):
    query = incidents_table.delete().where(incidents_table.c.id == incidentid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This incident has been deleted!"
    }

@app.post("/incidents/comments", response_model=CommentSchema, tags=["incidents"])
async def add_comment(comment: CommentSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = feedback_table.insert().values(
        id=gID,
        comment=comment.comment,
        postid=comment.postid,
        attachment=comment.attachment,
        createdby=comment.createdby,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **comment.dict(),
        "id": gID,
        "datecreated": gDate
    }

@app.delete("/incidents/comments/{feedbackid}", tags=["incidents"])
async def delete_comment(feedbackid: str):
    query = feedback_table.delete().where(feedback_table.c.id == feedbackid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This feedback has been deleted!"
    }

@app.get("/incidents/comments/{postid}", tags=["incidents"])
async def get_post_comments_by_id(postid: str):
    query = feedback_table.select().where(feedback_table.c.postid == postid)
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            res.append({
            "id": result["id"],
            "postid": result["postid"],
            "comment": result["comment"],
            "attachment": result["attachment"],
            "datecreated": result["datecreated"],
            "createdby": await get_usernames_by_id(result["createdby"]),
            "dateupdated": result["dateupdated"],
            "updatedby": result["updatedby"],
            "status": result["status"]
            })
        
        return res
    else:
        raise HTTPException(status_code=204, detail='No comments found')

@app.get("/incidents/commentscount/{postid}", tags=["incidents"])
async def get_post_comments_count_by_id(postid: str):
    counter = 0
    query = feedback_table.select().where(feedback_table.c.postid == postid)
    results = await database.fetch_all(query)
    if results:
        for result in results:
            counter += 1

    return counter

@app.post("/incidents/like", tags=["incidents"])
async def like_post(like: LikeSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    querylikes = likes_table.select().where(likes_table.c.postid == like.postid).where(likes_table.c.userid == like.userid)
    resultlikes = await database.fetch_all(querylikes)
    if resultlikes:
        query = likes_table.update().\
        where(likes_table.c.postid == like.postid).where(likes_table.c.userid == like.userid).\
        values(
            userid=like.userid,
            postid=like.postid,
            isliked=True,
            updatedby=like.userid,
            status="1",
            dateupdated=gDate
    )
    else:
        query = likes_table.insert().values(
            id=gID,
            userid=like.userid,
            postid=like.postid,
            isliked=True,
            createdby=like.userid,
            datecreated=gDate,
            status="1"
        )

    await database.execute(query)
    return {
        **like.dict(),
        "id": gID,
        "datecreated": gDate
    }

@app.post("/incidents/dislike", tags=["incidents"])
async def dislike_post(like: LikeSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    querylikes = likes_table.select().where(likes_table.c.postid == like.postid).where(likes_table.c.userid == like.userid)
    resultlikes = await database.fetch_all(querylikes)
    if resultlikes:
        query = likes_table.update().\
        where(likes_table.c.postid == like.postid).where(likes_table.c.userid == like.userid).\
        values(
            userid=like.userid,
            postid=like.postid,
            isliked=False,
            updatedby=like.userid,
            status="1",
            dateupdated=gDate
    )
    else:
        query = likes_table.insert().values(
            id=gID,
            userid=like.userid,
            postid=like.postid,
            isliked=False,
            createdby=like.userid,
            datecreated=gDate,
            status="1"
        )

    await database.execute(query)
    return {
        **like.dict(),
        "id": gID,
        "datecreated": gDate
    }

@app.get("/incidents/likes/{postid}", tags=["incidents"])
async def get_post_likes_count_by_id(postid: str):
    counter = 0
    query = likes_table.select().where(likes_table.c.postid == postid).where(likes_table.c.isliked == True)
    results = await database.fetch_all(query)
    if results:
        for result in results:
            counter += 1

    return counter

@app.get("/incidents/dislikes/{postid}", tags=["incidents"])
async def get_post_dislikes_count_by_id(postid: str):
    counter = 0
    query = likes_table.select().where(likes_table.c.postid == postid).where(likes_table.c.isliked == False)
    results = await database.fetch_all(query)
    if results:
        for result in results:
            counter += 1

    return counter

@app.post("/incidents/userliked/{postid}/{userid}", tags=["incidents"])
async def check_if_user_liked_post(postid: str, userid: str):
    query = likes_table.select().where(likes_table.c.postid == postid).where(likes_table.c.userid == userid)
    result = await database.fetch_one(query)
    if result:
        if(result["isliked"]):
            return "yes"
        else:
            return "no"
    else:
        return "none"


###################### END INCIDENTS ##################

##################### REPORTS ######################

@app.get("/reports",  tags=["reports"], dependencies=[Depends(jwtBearer())])
async def get_all_reports():
    
    j = join(
        incidents_table,
        incidentcategories_table,
        incidents_table.c.incidentcategoryid == incidentcategories_table.c.id
    )

    # Select desired fields
    query = select(
        incidents_table.c.id.label("incident_id"),
        incidents_table.c.name.label("incident_name"),
        incidents_table.c.description.label("incident_description"),
        incidents_table.c.isemergency,
        incidents_table.c.iscityreport,
        incidents_table.c.address,
        incidents_table.c.addresslat,
        incidents_table.c.addresslong,
        incidents_table.c.file1,
        incidents_table.c.file2,
        incidents_table.c.file3,
        incidents_table.c.file4,
        incidents_table.c.file5,
        incidents_table.c.upvotes,
        incidentcategories_table.c.name.label("category_name"),
        incidentcategories_table.c.description.label("category_description"),
        incidentcategories_table.c.image.label("category_image"),
        incidentcategories_table.c.autoapprove.label("category_autoapprove"),
        incidentcategories_table.c.doesexpire.label("category_doesexpire"),
        incidentcategories_table.c.hourstoexpire.label("category_hourstoexpire"),
        incidents_table.c.startdate,
        incidents_table.c.enddate,
        incidents_table.c.cause,
        incidents_table.c.fulldisruption,
        incidents_table.c.createdby,
        incidents_table.c.datecreated,
        incidents_table.c.dateupdated,
        incidents_table.c.updatedby,
        incidents_table.c.status
    ).select_from(j).where(incidents_table.c.iscityreport == True).order_by(desc(incidents_table.c.datecreated))

    result = await database.fetch_all(query)
    if result:
        return result
    else:
        raise HTTPException(
            status_code=204, detail="No incidents nearby.")



@app.get("/reports/default", response_model=Page[IncidentWithCategorySchema], tags=["reports"])
@app.get("/reports/limit-offset", response_model=LimitOffsetPage[IncidentWithCategorySchema], tags=["reports"])
async def get_all_reports_paginate(params: Params = Depends()):
    # Perform the JOIN
    j = join(
        incidents_table,
        incidentcategories_table,
        incidents_table.c.incidentcategoryid == incidentcategories_table.c.id
    )

    # Select desired fields
    query = select(
        incidents_table.c.id.label("incident_id"),
        incidents_table.c.name.label("incident_name"),
        incidents_table.c.description.label("incident_description"),
        incidents_table.c.isemergency,
        incidents_table.c.iscityreport,
        incidents_table.c.address,
        incidents_table.c.addresslat,
        incidents_table.c.addresslong,
        incidents_table.c.file1,
        incidents_table.c.file2,
        incidents_table.c.file3,
        incidents_table.c.file4,
        incidents_table.c.file5,
        incidents_table.c.upvotes,
        incidentcategories_table.c.name.label("category_name"),
        incidentcategories_table.c.description.label("category_description"),
        incidentcategories_table.c.image.label("category_image"),
        incidentcategories_table.c.autoapprove.label("category_autoapprove"),
        incidentcategories_table.c.doesexpire.label("category_doesexpire"),
        incidentcategories_table.c.hourstoexpire.label("category_hourstoexpire"),
        incidents_table.c.startdate,
        incidents_table.c.enddate,
        incidents_table.c.cause,
        incidents_table.c.fulldisruption,
        incidents_table.c.createdby,
        incidents_table.c.datecreated,
        incidents_table.c.dateupdated,
        incidents_table.c.updatedby,
        incidents_table.c.status
    ).select_from(j).where(incidents_table.c.iscityreport == True)

    result = await database.fetch_all(query)
    return paginate(result)

@app.get("/reports/status/default/{status}", response_model=Page[IncidentWithCategorySchema], tags=["reports"])
@app.get("/reports/status/limit-offset/{status}",  response_model=LimitOffsetPage[IncidentWithCategorySchema], tags=["reports"])
async def get_all_reports_by_status_paginate(status: str, params: Params = Depends(),):
    # Perform the JOIN
    j = join(
        incidents_table,
        incidentcategories_table,
        incidents_table.c.incidentcategoryid == incidentcategories_table.c.id
    )

    # Select desired fields
    query = select(
        incidents_table.c.id.label("incident_id"),
        incidents_table.c.name.label("incident_name"),
        incidents_table.c.description.label("incident_description"),
        incidents_table.c.isemergency,
        incidents_table.c.iscityreport,
        incidents_table.c.address,
        incidents_table.c.addresslat,
        incidents_table.c.addresslong,
        incidents_table.c.file1,
        incidents_table.c.file2,
        incidents_table.c.file3,
        incidents_table.c.file4,
        incidents_table.c.file5,
        incidents_table.c.upvotes,
        incidentcategories_table.c.name.label("category_name"),
        incidentcategories_table.c.description.label("category_description"),
        incidentcategories_table.c.image.label("category_image"),
        incidentcategories_table.c.autoapprove.label("category_autoapprove"),
        incidentcategories_table.c.doesexpire.label("category_doesexpire"),
        incidentcategories_table.c.hourstoexpire.label("category_hourstoexpire"),
        incidents_table.c.startdate,
        incidents_table.c.enddate,
        incidents_table.c.cause,
        incidents_table.c.fulldisruption,
        incidents_table.c.createdby,
        incidents_table.c.datecreated,
        incidents_table.c.dateupdated,
        incidents_table.c.updatedby,
        incidents_table.c.status
    ).select_from(j).where(
        (incidents_table.c.status == status) & (incidents_table.c.iscityreport == True)
    ).order_by(desc(incidents_table.c.datecreated))

    result = await database.fetch_all(query)
    return paginate(result)


@app.post("/reports/register", response_model=IncidentSchema, tags=["reports"], dependencies=[Depends(jwtBearer())])
async def register_report(incident: IncidentSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()

    # Duplicate detection (mirror incidents/register logic)
    def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    radius_m = 500.0
    time_window_minutes = 5
    time_threshold = gDate - datetime.timedelta(minutes=time_window_minutes)

    candidate_query = (
        select(incidents_table)
        .where(
            (incidents_table.c.incidentcategoryid == incident.incidentcategoryid)
            & (
                (incidents_table.c.datecreated >= time_threshold)
                | (incidents_table.c.createdby == incident.createdby)
            )
        )
    )
    candidates = await database.fetch_all(candidate_query)

    same_user_duplicate = None
    nearby_same_category = None
    for row in candidates:
        try:
            row_lat = float(row["addresslat"]) if row["addresslat"] is not None else None
            row_lon = float(row["addresslong"]) if row["addresslong"] is not None else None
        except Exception:
            row_lat, row_lon = None, None

        if row_lat is None or row_lon is None:
            continue

        distance_m = haversine_distance_meters(
            float(incident.addresslat), float(incident.addresslong), row_lat, row_lon
        )
        minutes_diff = abs((gDate - row["datecreated"]).total_seconds()) / 60.0 if row["datecreated"] else 9999
        is_same_user = (row["createdby"] == incident.createdby)

        if is_same_user and (distance_m <= radius_m or minutes_diff <= time_window_minutes):
            same_user_duplicate = row
            break

        if (not is_same_user) and (distance_m <= radius_m):
            if nearby_same_category is None:
                nearby_same_category = (row, distance_m)
            elif distance_m < nearby_same_category[1]:
                nearby_same_category = (row, distance_m)

    if same_user_duplicate is not None:
        existing = same_user_duplicate
        return {
            "id": existing["id"],
            "name": existing["name"],
            "description": existing["description"],
            "incidentcategoryid": existing["incidentcategoryid"],
            "address": existing["address"],
            "addresslat": existing["addresslat"],
            "addresslong": existing["addresslong"],
            "file1": existing["file1"],
            "file2": existing["file2"],
            "file3": existing["file3"],
            "file4": existing["file4"],
            "file5": existing["file5"],
            "isemergency": existing["isemergency"],
            "iscityreport": existing["iscityreport"],
            "createdby": existing["createdby"],
            "startdate": existing["startdate"],
            "enddate": existing["enddate"],
            "datecreated": existing["datecreated"],
            "dateupdated": existing["dateupdated"],
            "updatedby": existing["updatedby"],
            "status": existing["status"],
        }

    if nearby_same_category is not None:
        existing, _ = nearby_same_category
        return {
            "id": existing["id"],
            "name": existing["name"],
            "description": existing["description"],
            "incidentcategoryid": existing["incidentcategoryid"],
            "address": existing["address"],
            "addresslat": existing["addresslat"],
            "addresslong": existing["addresslong"],
            "file1": existing["file1"],
            "file2": existing["file2"],
            "file3": existing["file3"],
            "file4": existing["file4"],
            "file5": existing["file5"],
            "isemergency": existing["isemergency"],
            "iscityreport": existing["iscityreport"],
            "createdby": existing["createdby"],
            "startdate": existing["startdate"],
            "enddate": existing["enddate"],
            "datecreated": existing["datecreated"],
            "dateupdated": existing["dateupdated"],
            "updatedby": existing["updatedby"],
            "status": existing["status"],
        }

    # Insert when no duplicate conditions met
    query = incidents_table.insert().values(
        id=gID,
        name=incident.name,
        description=incident.description,
        isemergency=incident.isemergency,
        iscityreport=True,
        incidentcategoryid=incident.incidentcategoryid,
        address=incident.address,
        addresslat=incident.addresslat,
        addresslong=incident.addresslong,
        file1=incident.file1,
        file2=incident.file2,
        file3=incident.file3,
        file4=incident.file4,
        file5=incident.file5,
        startdate=incident.startdate,
        enddate=incident.enddate,
        cause=incident.cause,
        fulldisruption=incident.fulldisruption,
        createdby=incident.createdby,
        datecreated=gDate,
        status= incident.status
    )

    await database.execute(query)
    return {
        **incident.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.post("/reports/update", response_model=IncidentUpdateSchema, tags=["reports"], dependencies=[Depends(jwtBearer())])
async def update_report(incident: IncidentUpdateSchema):
    gDate = datetime.datetime.now()
    query = incidents_table.update().\
        where(incidents_table.c.id == incident.id).\
        values(
            name=incident.name,
            description=incident.description,
            isemergency=incident.isemergency,
            iscityreport=True,
            incidentcategoryid=incident.incidentcategoryid,
            address=incident.address,
            addresslat=incident.addresslat,
            addresslong=incident.addresslong,
            file1=incident.file1,
            file2=incident.file2,
            file3=incident.file3,
            file4=incident.file4,
            file5=incident.file5,
            cause=incident.cause,
            fulldisruption=incident.fulldisruption,
            updatedby=incident.updatedby,
            dateupdated=gDate,
            startdate=incident.startdate,
            enddate=incident.enddate,
    )

    await database.execute(query)
    return await get_incident_by_id(incident.id)


@app.post("/reports/archive", response_model=IncidentUpdateSchema, tags=["reports"], dependencies=[Depends(jwtBearer())])
async def archive_report(incident: IncidentStatusSchema):
    gDate = datetime.datetime.now()
    query = incidents_table.update().\
        where(incidents_table.c.id == incident.id).\
        values(
            status="0",
            updatedby = incident.updatedby,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_incident_by_id(incident.id)


@app.post("/reports/restore", response_model=IncidentUpdateSchema, tags=["reports"], dependencies=[Depends(jwtBearer())])
async def restore_report(incident: IncidentStatusSchema):
    gDate = datetime.datetime.now()
    query = incidents_table.update().\
        where(incidents_table.c.id == incident.id).\
        values(
            status="1",
            updatedby = incident.updatedby,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_incident_by_id(incident.id)

###################### END REPORTS ##################


###################### NEWS ######################

@app.get("/news", response_model=List[NewsSchema], tags=["news"])
async def get_all_news():
    query = news_table.select()
    return await database.fetch_all(query)

@app.get("/news/{newsid}", response_model=NewsSchema, tags=["news"])
async def get_news_by_id(newsid: str):
    query = news_table.select().where(news_table.c.id == newsid)
    result = await database.fetch_one(query)
    return result

@app.get("/news/archives", response_model=List[NewsArchiveGroup], tags=["news"])
async def get_news_archives():
    # Fetch all news entries with status '1' only, ordered by datecreated
    query = select(news_table).where(news_table.c.status == '1').order_by(news_table.c.datecreated.desc())
    news_items = await database.fetch_all(query)

    # Defensive grouping by (year, month)
    grouped = {}
    for item in news_items:
        if item is None:
            continue  # skip malformed rows

        created: datetime = item["datecreated"]
        year = created.year
        month = created.strftime("%B")
        key = (year, month)

        if key not in grouped:
            grouped[key] = []

        grouped[key].append(NewsSchema(**dict(item)))  # enforce schema

    # Format the result
    result = []
    for (year, month), articles in sorted(grouped.items(), reverse=True):
        result.append({
            "month": month,
            "year": year,
            "count": len(articles),
            "articles": articles
        })

    return result


@app.post("/news/post", response_model=NewsSchema, tags=["news"])
async def post_news_article(news: NewsSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = news_table.insert().values(
        id=gID,
        title=news.title,
        content=news.content,
        image=news.image,
        file1=news.file1,
        file2=news.file2,
        file3=news.file3,
        file4=news.file4,
        file5=news.file5,
        createdby=news.createdby,
        datecreated=gDate,
        status=news.status
    )

    await database.execute(query)
    return {
        **news.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.post("/news/update", response_model=NewsUpdateSchema, tags=["news"])
async def update_news(news: NewsUpdateSchema):
    gDate = datetime.datetime.now()
    query = news_table.update().\
        where(news_table.c.id == news.id).\
        values(
            title=news.title,
            content=news.content,
            image=news.image,
            file1=news.file1,
            file2=news.file2,
            file3=news.file3,
            file4=news.file4,
            file5=news.file5,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_news_by_id(news.id)


@app.post("/news/archive", response_model=NewsUpdateSchema, tags=["news"])
async def archive_news(news: NewsUpdateSchema):
    gDate = datetime.datetime.now()
    query = news_table.update().\
        where(news_table.c.id == news.id).\
        values(
            title=news.title,
            content=news.content,
            image=news.image,
            file1=news.file1,
            file2=news.file2,
            file3=news.file3,
            file4=news.file4,
            file5=news.file5,
            status="2",
            dateupdated=gDate,
            updatedby=news.updatedby
    )

    await database.execute(query)
    return await get_news_by_id(news.id)


@app.post("/news/restore", response_model=NewsUpdateSchema, tags=["news"])
async def restore_news(news: NewsUpdateSchema):
    gDate = datetime.datetime.now()
    query = news_table.update().\
        where(news_table.c.id == news.id).\
        values(
            title=news.title,
            content=news.content,
            image=news.image,
            file1=news.file1,
            file2=news.file2,
            file3=news.file3,
            file4=news.file4,
            file5=news.file5,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_news_by_id(news.id)


@app.delete("/news/{newsid}", tags=["news"])
async def delete_news(newsid: str):
    query = news_table.delete().where(news_table.c.id == newsid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This news article has been deleted!"
    }

###################### END NEWS ##################


###################### INCIDENT_CATEGORIES ######################


@app.get("/incidentcategories", response_model=List[IncidentCategoriesSchema], tags=["incidentcategories"], dependencies=[Depends(jwtBearer())])
async def get_all_incident_categories():
    query = incidentcategories_table.select()
    return await database.fetch_all(query)

@app.get("/incidentcategories/default", response_model=Page[IncidentCategoriesSchema], tags=["incidentcategories"])
@app.get("/incidentcategories/limit-offset",  response_model=LimitOffsetPage[IncidentCategoriesSchema], tags=["incidentcategories"])
async def get_all_incidents_categories_paginate(params: Params = Depends(),):
    query = incidentcategories_table.select()
    result = await database.fetch_all(query)
    # if result:
    return paginate(result)

@app.get("/incidentcategories/count", tags=["incidentcategories"])
async def get_incidentcategories_count():
    counter = 0
    query = incidentcategories_table.select()
    results = await database.fetch_all(query)
    if results:
        for result in results:
            counter += 1

    return counter

@app.get("/incidentcategories/{incidentcategoryid}", response_model=IncidentCategoriesSchema, tags=["incidentcategories"], dependencies=[Depends(jwtBearer())])
async def get_incident_category_by_id(incidentcategoryid: str):
    query = incidentcategories_table.select().where(
        incidentcategories_table.c.id == incidentcategoryid)
    result = await database.fetch_one(query)
    if result:
        return result


@app.get("/incidents/name/{incidentid}", tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def get_incident_category_name_by_id(incidentcategoryid: str):
    query = incidentcategories_table.select().where(
        incidentcategories_table.c.id == incidentcategoryid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["name"]
        return fullname
    else:
        return "Unkown"


@app.post("/incidentcategories/register", response_model=IncidentCategoriesSchema, tags=["incidentcategories"], dependencies=[Depends(jwtBearer())])
async def add_incident_category(category: IncidentCategoriesSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = incidentcategories_table.insert().values(
        id=gID,
        name=category.name,
        image=category.image,
        description=category.description,
        autoapprove=category.autoapprove,
        doesexpire=category.doesexpire,
        hourstoexpire=category.hourstoexpire,
        datecreated=gDate,
        createdby=category.createdby,
        status=category.status
    )

    await database.execute(query)
    return {
        **category.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.post("/incidentcategories/update", response_model=IncidentCategoriesUpdateSchema, tags=["incidentcategories"], dependencies=[Depends(jwtBearer())])
async def update_incident_category(category: IncidentCategoriesUpdateSchema):
    gDate = datetime.datetime.now()
    query = incidentcategories_table.update().\
        where(incidentcategories_table.c.id == category.id).\
        values(
            name=category.name,
            image=category.image,
            description=category.description,
            autoapprove=category.autoapprove,
            doesexpire=category.doesexpire,
            hourstoexpire=category.hourstoexpire,
            datecreated=gDate,
            updatedby=category.updatedby,
            dateupdated=gDate,
            status=category.status
    )

    await database.execute(query)
    return await get_incident_category_by_id(category.id)


@app.post("/incidentcategories/archive", response_model=IncidentCategoriesUpdateSchema, tags=["incidentcategories"], dependencies=[Depends(jwtBearer())])
async def archive_incident_category(incidentcategoryid: str):
    gDate = datetime.datetime.now()
    query = incidentcategories_table.update().\
        where(incidentcategories_table.c.id == incidentcategoryid).\
        values(
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_incident_category_by_id(incidentcategoryid)


@app.post("/incidentcategories/restore", response_model=IncidentCategoriesUpdateSchema, tags=["incidentcategories"], dependencies=[Depends(jwtBearer())])
async def restore_incident_category(incidentcategoryid: str):
    gDate = datetime.datetime.now()
    query = incidentcategories_table.update().\
        where(incidentcategories_table.c.id == incidentcategoryid).\
        values(
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_incident_category_by_id(incidentcategoryid)


@app.delete("/incidentcategories/{incidentcategoryid}", tags=["incidentcategories"], dependencies=[Depends(jwtBearer())])
async def delete_incident_category(incidentcategoryid: str):
    query = incidentcategories_table.delete().where(
        incidentcategories_table.c.id == incidentcategoryid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This Incident category has been deleted!"
    }

###################### END INCIDENT_CATEGORIES ##################

###################### SAVED LOCATIONS ######################


@app.get("/savedlocations", response_model=List[SavedLocationSchema], tags=["savedlocations"], dependencies=[Depends(jwtBearer())])
async def get_all_saved_locations():
    query = savedlocations_table.select()
    return await database.fetch_all(query)


@app.get("/savedlocations/{savedlocationid}", response_model=SavedLocationSchema, tags=["savedlocations"], dependencies=[Depends(jwtBearer())])
async def get_saved_location_by_id(savedlocationid: str):
    query = savedlocations_table.select().where(
        savedlocations_table.c.id == savedlocationid)
    result = await database.fetch_one(query)
    return result


@app.get("/savedlocations/name/{savedlocationid}", tags=["savedlocations"], dependencies=[Depends(jwtBearer())])
async def get_saved_location_name_by_id(savedlocationid: str):
    query = savedlocations_table.select().where(
        savedlocations_table.c.id == savedlocationid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["name"]
        return fullname
    else:
        return "Unkown Incident"


@app.get("/savedlocations/user/{userid}", tags=["savedlocations"], dependencies=[Depends(jwtBearer())])
async def get_saved_locations_by_userid(userid: str):
    query = savedlocations_table.select().where(
        savedlocations_table.c.createdby == userid)
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            res.append(await get_saved_location_by_id(result["createdby"]))
        return res
    else:
        raise HTTPException(
            status_code=204, detail="User does not have any saved locations.")


@app.post("/savedlocations/register", response_model=SavedLocationSchema, tags=["savedlocations"], dependencies=[Depends(jwtBearer())])
async def register_saved_location(savedlocation: SavedLocationSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = savedlocations_table.insert().values(
        id=gID,
        locationname=savedlocation.locationname,
        locationlat=savedlocation.locationlat,
        locationlong=savedlocation.locationlong,
        locationaddress=savedlocation.locationaddress,
        createdby=savedlocation.createdby,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **savedlocation.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.post("/savedlocations/update", response_model=SavedLocationUpdateSchema, tags=["savedlocations"], dependencies=[Depends(jwtBearer())])
async def update_saved_location(savedlocation: SavedLocationUpdateSchema):
    gDate = datetime.datetime.now()
    query = savedlocations_table.update().\
        where(savedlocations_table.c.id == savedlocation.id).\
        values(
            locationname=savedlocation.locationname,
            locationlat=savedlocation.locationlat,
            locationlong=savedlocation.locationlong,
            locationaddress=savedlocation.locationaddress,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_saved_location_by_id(savedlocation.id)


@app.post("/savedlocations/archive", response_model=SavedLocationUpdateSchema, tags=["savedlocations"], dependencies=[Depends(jwtBearer())])
async def archive_saved_location(savedlocationid: str):
    gDate = datetime.datetime.now()
    query = savedlocations_table.update().\
        where(savedlocations_table.c.id == savedlocationid).\
        values(
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_saved_location_by_id(savedlocationid)


@app.post("/savedlocations/restore", response_model=SavedLocationUpdateSchema, tags=["savedlocations"], dependencies=[Depends(jwtBearer())])
async def restore_saved_location(savedlocationid: str):
    gDate = datetime.datetime.now()
    query = savedlocations_table.update().\
        where(savedlocations_table.c.id == savedlocationid).\
        values(
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_saved_location_by_id(savedlocationid)


@app.delete("/savedlocations/{savedlocationid}", tags=["savedlocations"], dependencies=[Depends(jwtBearer())])
async def delete_saved_location(savedlocationid: str):
    query = savedlocations_table.delete().where(
        savedlocations_table.c.id == savedlocationid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This Saved Location has been deleted!"
    }

###################### END SAVED LOCATIONS ##################

###################### TRIPS ######################


@app.get("/trips", response_model=List[TripSchema], tags=["trips"], dependencies=[Depends(jwtBearer())])
async def get_all_trips():
    query = user_trips_table.select()
    return await database.fetch_all(query)


@app.get("/trips/{savedlocationid}", response_model=TripSchema, tags=["trips"], dependencies=[Depends(jwtBearer())])
async def get_trip_by_id(savedlocationid: str):
    query = user_trips_table.select().where(
        user_trips_table.c.id == savedlocationid)
    result = await database.fetch_one(query)
    return result


@app.get("/trips/name/{savedlocationid}", tags=["trips"], dependencies=[Depends(jwtBearer())])
async def get_trip_name_by_id(savedlocationid: str):
    query = user_trips_table.select().where(
        user_trips_table.c.id == savedlocationid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["name"]
        return fullname
    else:
        return "Unkown Trip"


@app.get("/trips/user/{userid}", tags=["trips"], dependencies=[Depends(jwtBearer())])
async def get_trips_by_userid(userid: str):
    query = user_trips_table.select().where(user_trips_table.c.createdby == userid)
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            res.append(await get_trip_by_id(result["id"]))
        return res
    else:
        raise HTTPException(
            status_code=204, detail="User does not have any saved locations.")


@app.post("/trips/register", response_model=TripSchema, tags=["trips"], dependencies=[Depends(jwtBearer())])
async def register_trip(trip: TripSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = user_trips_table.insert().values(
        id=gID,
        startaddress=trip.startaddress,
        startlat=trip.startlat,
        startlong=trip.startlong,
        destinationaddress=trip.destinationaddress,
        destinationlat=trip.destinationlat,
        destinationlong=trip.destinationlong,
        createdby=trip.createdby,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **trip.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.post("/trips/update", response_model=TripUpdateSchema, tags=["trips"], dependencies=[Depends(jwtBearer())])
async def update_trip(trip: TripUpdateSchema):
    gDate = datetime.datetime.now()
    query = user_trips_table.update().\
        where(user_trips_table.c.id == trip.id).\
        values(
            startaddress=trip.startaddress,
            startlat=trip.startlat,
            startlong=trip.startlong,
            destinationaddress=trip.destinationaddress,
            destinationlat=trip.destinationlat,
            destinationlong=trip.destinationlong,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_trip_by_id(trip.id)


@app.post("/trips/archive", response_model=TripUpdateSchema, tags=["trips"], dependencies=[Depends(jwtBearer())])
async def archive_trip(tripid: str):
    gDate = datetime.datetime.now()
    query = user_trips_table.update().\
        where(user_trips_table.c.id == tripid).\
        values(
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_trip_by_id(id)


@app.post("/trips/restore", response_model=TripUpdateSchema, tags=["trips"], dependencies=[Depends(jwtBearer())])
async def restore_trip(tripid: str):
    gDate = datetime.datetime.now()
    query = user_trips_table.update().\
        where(user_trips_table.c.id == tripid).\
        values(
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_trip_by_id(tripid)


@app.delete("/trips/{tripid}", tags=["trips"], dependencies=[Depends(jwtBearer())])
async def delete_trip(tripid: str):
    query = user_trips_table.delete().where(user_trips_table.c.id == tripid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This Trip has been deleted!"
    }

###################### END TRIPS ##################

###################### DESIGNATIONS ######################


@app.get("/designations", response_model=List[DesignationSchema], tags=["designations"], dependencies=[Depends(jwtBearer())])
async def get_all_designations():
    query = designations_table.select()
    return await database.fetch_all(query)


@app.get("/designations/{roleid}", response_model=DesignationSchema, tags=["designations"], dependencies=[Depends(jwtBearer())])
async def get_designation_by_id(roleid: str):
    query = designations_table.select().where(designations_table.c.id == roleid)
    result = await database.fetch_one(query)
    return result


@app.get("/designations/name/{roleid}", tags=["designations"], dependencies=[Depends(jwtBearer())])
async def get_designationname_by_id(roleid: str):
    query = designations_table.select().where(designations_table.c.id == roleid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["designationname"]
        return fullname
    else:
        return "Unkown Role"


@app.post("/designations/register", response_model=DesignationSchema, tags=["designations"], dependencies=[Depends(jwtBearer())])
async def register_designation(designation: DesignationSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = designations_table.insert().values(
        id=gID,
        designationname=designation.designationname,
        roledescription=designation.roledescription,
        linemanagerid=designation.linemanagerid,
        departmentid=designation.departmentid,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **designation.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.post("/designations/update", response_model=DesignationUpdateSchema, tags=["designations"], dependencies=[Depends(jwtBearer())])
async def update_designation(designation: DesignationUpdateSchema):
    gDate = datetime.datetime.now()
    query = designations_table.update().\
        where(designations_table.c.id == designation.id).\
        values(
            designationname=designation.designationname,
            roledescription=designation.roledescription,
            linemanagerid=designation.linemanagerid,
            departmentid=designation.departmentid,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_designation_by_id(designation.id)


@app.post("/designations/archive", response_model=DesignationUpdateSchema, tags=["designations"], dependencies=[Depends(jwtBearer())])
async def archive_designation(designationid: str):
    gDate = datetime.datetime.now()
    query = designations_table.update().\
        where(designations_table.c.id == designationid).\
        values(
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_designation_by_id(designationid)


@app.post("/designations/restore", response_model=DesignationUpdateSchema, tags=["designations"], dependencies=[Depends(jwtBearer())])
async def restore_role(designationid: str):
    gDate = datetime.datetime.now()
    query = designations_table.update().\
        where(designations_table.c.id == designationid).\
        values(
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_designation_by_id(designationid)


@app.delete("/designations/{designationid}", tags=["designations"], dependencies=[Depends(jwtBearer())])
async def delete_designation(designationid: str):
    query = designations_table.delete().where(
        designations_table.c.id == designationid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This designation has been deleted!"
    }

###################### END DESIGNATION ##################

###################### DEPARTMENTS ######################


@app.get("/departments", response_model=List[DepartmentSchema], tags=["departments"], dependencies=[Depends(jwtBearer())])
async def get_all_departments():
    query = departments_table.select()
    return await database.fetch_all(query)


@app.get("/departments/{departmentid}", response_model=DepartmentSchema, tags=["departments"], dependencies=[Depends(jwtBearer())])
async def get_department_by_id(departmentid: str):
    query = departments_table.select().where(
        departments_table.c.id == departmentid)
    result = await database.fetch_one(query)
    return result


@app.get("/departments/name/{departmentid}", tags=["departments"], dependencies=[Depends(jwtBearer())])
async def get_department_name_by_id(departmentid: str):
    query = departments_table.select().where(
        departments_table.c.id == departmentid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["departmentname"]
        return fullname
    else:
        return "Unkown Department"


@app.post("/departments/register", response_model=DepartmentSchema, tags=["departments"], dependencies=[Depends(jwtBearer())])
async def register_departments(department: DepartmentSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = departments_table.insert().values(
        id=gID,
        departmentname=department.departmentname,
        description=department.description,
        hodid=department.hodid,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **department.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.post("/departments/update", response_model=DepartmentSchema, tags=["departments"], dependencies=[Depends(jwtBearer())])
async def update_department(department: DepartmentSchema):
    gDate = datetime.datetime.now()
    query = departments_table.update().\
        where(departments_table.c.id == department.id).\
        values(
            departmentname=department.departmentname,
            description=department.description,
            hodid=department.hodid,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_department_by_id(department.id)


@app.post("/departments/archive", response_model=DepartmentSchema, tags=["departments"], dependencies=[Depends(jwtBearer())])
async def archive_department(departmentid: str):
    gDate = datetime.datetime.now()
    query = departments_table.update().\
        where(departments_table.c.id == departmentid).\
        values(
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_department_by_id(departmentid)


@app.post("/departments/restore", response_model=DepartmentSchema, tags=["departments"], dependencies=[Depends(jwtBearer())])
async def restore_department(departmentid: str):
    gDate = datetime.datetime.now()
    query = departments_table.update().\
        where(departments_table.c.id == departmentid).\
        values(
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_department_by_id(departmentid)


@app.delete("/departments/{departmentid}", tags=["departments"], dependencies=[Depends(jwtBearer())])
async def delete_department(departmentid: str):
    query = departments_table.delete().where(
        departments_table.c.id == departmentid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This department has been deleted!"
    }

###################### END DEPARTMENTS ##################

###################### LANGUAGES ######################


@app.get("/languages", tags=["languages"], dependencies=[Depends(jwtBearer())])
async def get_all_languages():
    query = languages_table.select()
    results = await database.fetch_all(query)
    if results:
        return results
    else:
        raise HTTPException(status_code=204, detail="No languages found")


@app.get("/languages/{languageid}", response_model=LanguageSchema, tags=["languages"], dependencies=[Depends(jwtBearer())])
async def get_language_by_id(languageid: str):
    query = languages_table.select().where(languages_table.c.id == languageid)
    result = await database.fetch_one(query)
    if result:
        return result
    else:
        raise HTTPException(status_code=204, detail="No language found")


@app.get("/languages/name/{languageid}", tags=["languages"], dependencies=[Depends(jwtBearer())])
async def get_languagename_by_id(languageid: str):
    query = languages_table.select().where(languages_table.c.id == languageid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["levelname"]
        return fullname
    else:
        return "Unknown Language"


@app.post("/languages/register", response_model=LanguageSchema, tags=["languages"], dependencies=[Depends(jwtBearer())])
async def register_language(language: LanguageSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = languages_table.insert().values(
        id=gID,
        languagename=language.languagename,
        shortcode=language.shortcode,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **language.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.post("/languages/update", response_model=LanguageUpdateSchema, tags=["languages"], dependencies=[Depends(jwtBearer())])
async def update_language(language: LanguageUpdateSchema):
    gDate = datetime.datetime.now()
    query = languages_table.update().\
        where(languages_table.c.id == language.id).\
        values(
            languagename=language.languagename,
            shortcode=language.shortcode,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_language_by_id(language.id)


@app.post("/languages/archive", response_model=LanguageUpdateSchema, tags=["languages"], dependencies=[Depends(jwtBearer())])
async def archive_language(languageid: str):
    gDate = datetime.datetime.now()
    query = languages_table.update().\
        where(languages_table.c.id == languageid).\
        values(
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_language_by_id(languageid)


@app.post("/languages/restore", response_model=LanguageUpdateSchema, tags=["languages"], dependencies=[Depends(jwtBearer())])
async def restore_language(languageid: str):
    gDate = datetime.datetime.now()
    query = languages_table.update().\
        where(languages_table.c.id == languageid).\
        values(
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_language_by_id(languageid)


@app.delete("/languages/{languageid}", tags=["languages"], dependencies=[Depends(jwtBearer())])
async def delete_language(languageid: str):
    query = languages_table.delete().where(languages_table.c.id == languageid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This language has been deleted!"
    }

##################### END LANGUAGES ##################

###################### REPORTS ######################
@app.get("/analytics/incidents/overview", tags=["analytics"])
async def get_incidents_overview(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    include_city_reports: bool = Query(False, description="Include city reports")
):
    """
    Get comprehensive incident overview with counts, trends, and status breakdown
    """
    # Build base filter
    base_filter = []
    
    if start_date:
        start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(incidents_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1)
        base_filter.append(incidents_table.c.datecreated < end_dt)
    
    if not include_city_reports:
        base_filter.append(incidents_table.c.iscityreport == False)
    
    # Total counts by status
    status_query = select(
        incidents_table.c.status,
        func.count(incidents_table.c.id).label("count")
    ).group_by(incidents_table.c.status)
    
    if base_filter:
        status_query = status_query.where(and_(*base_filter))
    
    status_results = await database.fetch_all(status_query)
    
    status_mapping = {
        "0": "archived",
        "1": "published", 
        "2": "resolved",
        "3": "rejected"
    }
    
    status_breakdown = {
        "archived": 0,
        "published": 0,
        "resolved": 0,
        "rejected": 0,
        "total": 0
    }
    
    for row in status_results:
        status_key = status_mapping.get(str(row["status"]), "unknown")
        count = int(row["count"])
        status_breakdown[status_key] = count
        status_breakdown["total"] += count
    
    # Emergency incidents
    emergency_query = select(
        func.count(incidents_table.c.id)
    ).where(incidents_table.c.isemergency == True)
    
    if base_filter:
        emergency_query = emergency_query.where(and_(*base_filter))
    
    emergency_count = await database.fetch_one(emergency_query)
    
    # Average resolution time (for resolved incidents)
    resolution_query = select(
        func.avg(
            func.extract('epoch', incidents_table.c.dateupdated - incidents_table.c.datecreated) / 3600
        ).label("avg_hours")
    ).where(incidents_table.c.status == "2")
    
    if base_filter:
        resolution_query = resolution_query.where(and_(*base_filter))
    
    avg_resolution = await database.fetch_one(resolution_query)
    avg_resolution_hours = float(avg_resolution["avg_hours"]) if avg_resolution["avg_hours"] else 0
    
    # Daily trend (last 30 days or within date range)
    if not start_date:
        trend_start = datetime.datetime.now() - datetime.timedelta(days=30)
    else:
        trend_start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    
    trend_query = select(
        func.date(incidents_table.c.datecreated).label("date"),
        func.count(incidents_table.c.id).label("count")
    ).where(incidents_table.c.datecreated >= trend_start).group_by(
        func.date(incidents_table.c.datecreated)
    ).order_by(func.date(incidents_table.c.datecreated))
    
    if end_date:
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1)
        trend_query = trend_query.where(incidents_table.c.datecreated < end_dt)
    
    if not include_city_reports:
        trend_query = trend_query.where(incidents_table.c.iscityreport == False)
    
    trend_results = await database.fetch_all(trend_query)
    
    daily_trend = [
        {
            "date": str(row["date"]),
            "count": int(row["count"])
        }
        for row in trend_results
    ]
    
    return {
        "status_breakdown": status_breakdown,
        "emergency_incidents": int(emergency_count[0]) if emergency_count else 0,
        "avg_resolution_hours": round(avg_resolution_hours, 2),
        "daily_trend": daily_trend,
        "date_range": {
            "start": start_date or (datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d"),
            "end": end_date or datetime.datetime.now().strftime("%Y-%m-%d")
        }
    }


@app.get("/analytics/incidents/by-category", tags=["analytics"])
async def get_incidents_by_category(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    include_city_reports: bool = Query(False),
    top_n: int = Query(10, ge=1, le=50, description="Number of top categories to return")
):
    """
    Get incident distribution by category with detailed breakdown
    """
    from sqlalchemy import join as sql_join
    
    j = sql_join(
        incidents_table,
        incidentcategories_table,
        incidents_table.c.incidentcategoryid == incidentcategories_table.c.id
    )
    
    base_filter = []
    
    if start_date:
        start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(incidents_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1)
        base_filter.append(incidents_table.c.datecreated < end_dt)
    
    if not include_city_reports:
        base_filter.append(incidents_table.c.iscityreport == False)
    
    # Category breakdown with status counts - FIXED to handle TEXT status
    query = select(
        incidentcategories_table.c.id.label("category_id"),
        incidentcategories_table.c.name.label("category_name"),
        incidentcategories_table.c.image.label("category_image"),
        func.count(incidents_table.c.id).label("total_count"),
        # Fixed: Use COUNT without CASE instead of SUM
        func.count().filter(incidents_table.c.status == "1").label("published"),
        func.count().filter(incidents_table.c.status == "2").label("resolved"),
        func.count().filter(incidents_table.c.status == "3").label("rejected"),
        func.count().filter(incidents_table.c.isemergency == True).label("emergency"),
        func.avg(incidents_table.c.upvotes).label("avg_upvotes")
    ).select_from(j).group_by(
        incidentcategories_table.c.id,
        incidentcategories_table.c.name,
        incidentcategories_table.c.image
    ).order_by(func.count(incidents_table.c.id).desc()).limit(top_n)
    
    if base_filter:
        query = query.where(and_(*base_filter))
    
    results = await database.fetch_all(query)
    
    categories = []
    total_incidents = 0
    
    for row in results:
        count = int(row["total_count"])
        total_incidents += count
        
        # Need to subtract total from filtered counts since COUNT counts all including NULLs
        published = int(row["published"]) if row["published"] else 0
        resolved = int(row["resolved"]) if row["resolved"] else 0
        rejected = int(row["rejected"]) if row["rejected"] else 0
        emergency = int(row["emergency"]) if row["emergency"] else 0
        
        categories.append({
            "category_id": row["category_id"],
            "category_name": row["category_name"],
            "category_image": row["category_image"],
            "total_count": count,
            "published": published,
            "resolved": resolved,
            "rejected": rejected,
            "emergency": emergency,
            "avg_upvotes": round(float(row["avg_upvotes"] or 0), 2),
            "percentage": 0  # Will calculate after getting total
        })
    
    # Calculate percentages
    for cat in categories:
        if total_incidents > 0:
            cat["percentage"] = round((cat["total_count"] / total_incidents) * 100, 2)
    
    return {
        "categories": categories,
        "total_incidents": total_incidents,
        "total_categories": len(categories)
    }


@app.get("/analytics/incidents/by-category-v2", tags=["analytics"])
async def get_incidents_by_category_v2(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    include_city_reports: bool = Query(False),
    top_n: int = Query(10, ge=1, le=50)
):
    """
    Alternative implementation using separate queries for accuracy
    """
    from sqlalchemy import join as sql_join
    
    base_filter = []
    
    if start_date:
        start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(incidents_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1)
        base_filter.append(incidents_table.c.datecreated < end_dt)
    
    if not include_city_reports:
        base_filter.append(incidents_table.c.iscityreport == False)
    
    # Get all categories first
    cat_query = select(
        incidentcategories_table.c.id,
        incidentcategories_table.c.name,
        incidentcategories_table.c.image
    )
    categories_data = await database.fetch_all(cat_query)
    
    results = []
    total_incidents = 0
    
    for cat in categories_data:
        cat_filter = base_filter + [incidents_table.c.incidentcategoryid == cat["id"]]
        
        # Total count for this category
        count_query = select(func.count(incidents_table.c.id)).where(and_(*cat_filter))
        total_count = await database.fetch_one(count_query)
        total = int(total_count[0]) if total_count else 0
        
        if total == 0:
            continue
        
        # Status breakdown
        status_counts = {"published": 0, "resolved": 0, "rejected": 0, "emergency": 0}
        
        for status, key in [("1", "published"), ("2", "resolved"), ("3", "rejected")]:
            status_query = select(func.count(incidents_table.c.id)).where(
                and_(*cat_filter, incidents_table.c.status == status)
            )
            status_result = await database.fetch_one(status_query)
            status_counts[key] = int(status_result[0]) if status_result else 0
        
        # Emergency count
        emergency_query = select(func.count(incidents_table.c.id)).where(
            and_(*cat_filter, incidents_table.c.isemergency == True)
        )
        emergency_result = await database.fetch_one(emergency_query)
        status_counts["emergency"] = int(emergency_result[0]) if emergency_result else 0
        
        # Average upvotes
        avg_query = select(func.avg(incidents_table.c.upvotes)).where(and_(*cat_filter))
        avg_result = await database.fetch_one(avg_query)
        avg_upvotes = float(avg_result[0] or 0) if avg_result else 0
        
        total_incidents += total
        
        results.append({
            "category_id": cat["id"],
            "category_name": cat["name"],
            "category_image": cat["image"],
            "total_count": total,
            **status_counts,
            "avg_upvotes": round(avg_upvotes, 2),
            "percentage": 0
        })
    
    # Sort by total count and limit
    results.sort(key=lambda x: x["total_count"], reverse=True)
    results = results[:top_n]
    
    # Calculate percentages
    for cat in results:
        if total_incidents > 0:
            cat["percentage"] = round((cat["total_count"] / total_incidents) * 100, 2)
    
    return {
        "categories": results,
        "total_incidents": total_incidents,
        "total_categories": len(results)
    }


@app.get("/analytics/incidents/hotspots", tags=["analytics"])
async def get_incident_hotspots(
    radius_meters: float = Query(500, ge=100, le=5000, description="Radius in meters for clustering"),
    min_incidents: int = Query(3, ge=2, le=20, description="Minimum incidents to qualify as hotspot"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None, description="Filter by category"),
    include_city_reports: bool = Query(False),
    top_n: int = Query(10, ge=1, le=50)
):
    """
    Identify geographic hotspots where incidents cluster within specified radius
    """
    base_filter = [
        incidents_table.c.addresslat.isnot(None),
        incidents_table.c.addresslong.isnot(None)
    ]
    
    if start_date:
        start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(incidents_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1)
        base_filter.append(incidents_table.c.datecreated < end_dt)
    
    if category_id:
        base_filter.append(incidents_table.c.incidentcategoryid == category_id)
    
    if not include_city_reports:
        base_filter.append(incidents_table.c.iscityreport == False)
    
    # Fetch all incidents with coordinates
    query = select(
        incidents_table.c.id,
        incidents_table.c.name,
        incidents_table.c.addresslat,
        incidents_table.c.addresslong,
        incidents_table.c.address,
        incidents_table.c.incidentcategoryid,
        incidents_table.c.status,
        incidents_table.c.datecreated
    ).where(and_(*base_filter))
    
    incidents = await database.fetch_all(query)
    
    if not incidents:
        return {
            "hotspots": [],
            "total_hotspots": 0,
            "parameters": {
                "radius_meters": radius_meters,
                "min_incidents": min_incidents
            }
        }
    
    # Haversine distance function
    def haversine_distance(lat1, lon1, lat2, lon2):
        R = 6371000  # Earth radius in meters
        phi1 = math.radians(float(lat1))
        phi2 = math.radians(float(lat2))
        dphi = math.radians(float(lat2) - float(lat1))
        dlambda = math.radians(float(lon2) - float(lon1))
        
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    # Simple grid-based clustering
    incident_list = [dict(inc) for inc in incidents]
    processed = set()
    hotspots = []
    
    for i, incident in enumerate(incident_list):
        if i in processed:
            continue
        
        lat1 = float(incident["addresslat"])
        lon1 = float(incident["addresslong"])
        
        # Find all incidents within radius
        cluster = [incident]
        cluster_indices = {i}
        
        for j, other in enumerate(incident_list):
            if j in processed or j == i:
                continue
            
            lat2 = float(other["addresslat"])
            lon2 = float(other["addresslong"])
            
            distance = haversine_distance(lat1, lon1, lat2, lon2)
            
            if distance <= radius_meters:
                cluster.append(other)
                cluster_indices.add(j)
        
        # If cluster meets minimum size, it's a hotspot
        if len(cluster) >= min_incidents:
            # Calculate centroid
            avg_lat = sum(float(inc["addresslat"]) for inc in cluster) / len(cluster)
            avg_lon = sum(float(inc["addresslong"]) for inc in cluster) / len(cluster)
            
            # Get status breakdown
            status_counts = defaultdict(int)
            category_counts = defaultdict(int)
            
            for inc in cluster:
                status_counts[inc["status"]] += 1
                if inc["incidentcategoryid"]:
                    category_counts[inc["incidentcategoryid"]] += 1
            
            # Get most common address
            addresses = [inc["address"] for inc in cluster if inc["address"]]
            most_common_address = max(set(addresses), key=addresses.count) if addresses else "Unknown Location"
            
            hotspots.append({
                "center_lat": round(avg_lat, 6),
                "center_long": round(avg_lon, 6),
                "incident_count": len(cluster),
                "location_name": most_common_address,
                "radius_meters": radius_meters,
                "status_breakdown": dict(status_counts),
                "top_category_id": max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else None,
                "incident_ids": [inc["id"] for inc in cluster]
            })
            
            # Mark as processed
            processed.update(cluster_indices)
    
    # Sort by incident count
    hotspots.sort(key=lambda x: x["incident_count"], reverse=True)
    hotspots = hotspots[:top_n]
    
    # Enrich with category names
    for hotspot in hotspots:
        if hotspot["top_category_id"]:
            cat_query = select(incidentcategories_table.c.name).where(
                incidentcategories_table.c.id == hotspot["top_category_id"]
            )
            cat_result = await database.fetch_one(cat_query)
            hotspot["top_category_name"] = cat_result["name"] if cat_result else "Unknown"
        else:
            hotspot["top_category_name"] = None
    
    return {
        "hotspots": hotspots,
        "total_hotspots": len(hotspots),
        "parameters": {
            "radius_meters": radius_meters,
            "min_incidents": min_incidents,
            "top_n": top_n
        }
    }


@app.get("/analytics/incidents/time-series", tags=["analytics"])
async def get_incidents_time_series(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    granularity: str = Query("day", description="day, week, month, year"),
    category_id: Optional[str] = Query(None),
    include_city_reports: bool = Query(False)
):
    """
    Get time-series data - FIXED to handle TEXT status
    """
    base_filter = []
    
    if start_date:
        start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(incidents_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1)
        base_filter.append(incidents_table.c.datecreated < end_dt)
    
    if category_id:
        base_filter.append(incidents_table.c.incidentcategoryid == category_id)
    
    if not include_city_reports:
        base_filter.append(incidents_table.c.iscityreport == False)
    
    # Build query based on granularity
    if granularity == "day":
        time_expr = func.date(incidents_table.c.datecreated)
    elif granularity == "week":
        time_expr = func.date_trunc('week', incidents_table.c.datecreated)
    elif granularity == "month":
        time_expr = func.date_trunc('month', incidents_table.c.datecreated)
    elif granularity == "year":
        time_expr = func.date_trunc('year', incidents_table.c.datecreated)
    else:
        time_expr = func.date(incidents_table.c.datecreated)
    
    # FIXED: Use COUNT with CASE instead of SUM
    query = select(
        time_expr.label("period"),
        func.count(incidents_table.c.id).label("total"),
        func.count().filter(incidents_table.c.status == "1").label("published"),
        func.count().filter(incidents_table.c.status == "2").label("resolved"),
        func.count().filter(incidents_table.c.status == "3").label("rejected"),
        func.count().filter(incidents_table.c.isemergency == True).label("emergency")
    ).group_by("period").order_by("period")
    
    if base_filter:
        query = query.where(and_(*base_filter))
    
    results = await database.fetch_all(query)
    
    return {
        "granularity": granularity,
        "data": [
            {
                "period": str(row["period"]),
                "total": int(row["total"]),
                "published": int(row["published"] or 0),
                "resolved": int(row["resolved"] or 0),
                "rejected": int(row["rejected"] or 0),
                "emergency": int(row["emergency"] or 0)
            }
            for row in results
        ]
    }

@app.get("/analytics/users/activity", tags=["analytics"])
async def get_user_activity_stats(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user_type: Optional[str] = Query(None, description="citizen, clerk, engineer, admin")
):
    """
    Get user activity statistics
    """
    base_filter = []
    
    if start_date:
        start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(users_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1)
        base_filter.append(users_table.c.datecreated < end_dt)
    
    # User type filter
    type_filter = None
    if user_type:
        if user_type == "citizen":
            type_filter = users_table.c.iscitizen == True
        elif user_type == "clerk":
            type_filter = users_table.c.isclerk == True
        elif user_type == "engineer":
            type_filter = users_table.c.isengineer == True
        elif user_type == "admin":
            type_filter = users_table.c.isadmin == True
    
    if type_filter is not None:
        base_filter.append(type_filter)
    
    # Total users
    total_query = select(func.count(users_table.c.id))
    if base_filter:
        total_query = total_query.where(and_(*base_filter))
    
    total_users = await database.fetch_one(total_query)
    
    # Active users (status = 1)
    active_query = select(func.count(users_table.c.id)).where(
        users_table.c.status == "1"
    )
    if base_filter:
        active_query = active_query.where(and_(*base_filter))
    
    active_users = await database.fetch_one(active_query)
    
    # User registrations over time
    reg_query = select(
        func.date(users_table.c.datecreated).label("date"),
        func.count(users_table.c.id).label("count")
    ).group_by(func.date(users_table.c.datecreated)).order_by(
        func.date(users_table.c.datecreated)
    )
    
    if base_filter:
        reg_query = reg_query.where(and_(*base_filter))
    
    registrations = await database.fetch_all(reg_query)
    
    # Top contributors
    from sqlalchemy import join as sql_join
    
    contributor_query = select(
        users_table.c.id,
        users_table.c.firstname,
        users_table.c.lastname,
        users_table.c.email,
        func.count(incidents_table.c.id).label("incident_count")
    ).select_from(
        sql_join(users_table, incidents_table, users_table.c.id == incidents_table.c.createdby)
    ).group_by(
        users_table.c.id,
        users_table.c.firstname,
        users_table.c.lastname,
        users_table.c.email
    ).order_by(func.count(incidents_table.c.id).desc()).limit(10)
    
    contributors = await database.fetch_all(contributor_query)
    
    return {
        "total_users": int(total_users[0]) if total_users else 0,
        "active_users": int(active_users[0]) if active_users else 0,
        "registration_trend": [
            {
                "date": str(row["date"]),
                "count": int(row["count"])
            }
            for row in registrations
        ],
        "top_contributors": [
            {
                "user_id": row["id"],
                "name": f"{row['firstname']} {row['lastname']}",
                "email": row["email"],
                "incident_count": int(row["incident_count"])
            }
            for row in contributors
        ]
    }


@app.get("/analytics/incidents/resolution-time", tags=["analytics"])
async def get_resolution_time_analysis(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None)
):
    """
    Analyze incident resolution times by category
    """
    from sqlalchemy import join as sql_join
    
    base_filter = [
        incidents_table.c.status == "2",  # Only resolved
        incidents_table.c.dateupdated.isnot(None)
    ]
    
    if start_date:
        start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(incidents_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1)
        base_filter.append(incidents_table.c.datecreated < end_dt)
    
    if category_id:
        base_filter.append(incidents_table.c.incidentcategoryid == category_id)
    
    j = sql_join(
        incidents_table,
        incidentcategories_table,
        incidents_table.c.incidentcategoryid == incidentcategories_table.c.id
    )
    
    # Resolution time in hours
    resolution_time_expr = func.extract(
        'epoch', 
        incidents_table.c.dateupdated - incidents_table.c.datecreated
    ) / 3600
    
    query = select(
        incidentcategories_table.c.id.label("category_id"),
        incidentcategories_table.c.name.label("category_name"),
        func.count(incidents_table.c.id).label("resolved_count"),
        func.avg(resolution_time_expr).label("avg_hours"),
        func.min(resolution_time_expr).label("min_hours"),
        func.max(resolution_time_expr).label("max_hours")
    ).select_from(j).where(and_(*base_filter)).group_by(
        incidentcategories_table.c.id,
        incidentcategories_table.c.name
    ).order_by(func.avg(resolution_time_expr))
    
    results = await database.fetch_all(query)
    
    return {
        "by_category": [
            {
                "category_id": row["category_id"],
                "category_name": row["category_name"],
                "resolved_count": int(row["resolved_count"]),
                "avg_hours": round(float(row["avg_hours"] or 0), 2),
                "min_hours": round(float(row["min_hours"] or 0), 2),
                "max_hours": round(float(row["max_hours"] or 0), 2),
                "avg_days": round(float(row["avg_hours"] or 0) / 24, 2)
            }
            for row in results
        ]
    }


@app.get("/analytics/categories/performance", tags=["analytics"])
async def get_category_performance(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """
    Analyze category performance - FIXED for TEXT status
    """
    from sqlalchemy import join as sql_join
    
    base_filter = [incidents_table.c.iscityreport == False]
    
    if start_date:
        start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        base_filter.append(incidents_table.c.datecreated >= start_dt)
    
    if end_date:
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d") + datetime.timedelta(days=1)
        base_filter.append(incidents_table.c.datecreated < end_dt)
    
    j = sql_join(
        incidents_table,
        incidentcategories_table,
        incidents_table.c.incidentcategoryid == incidentcategories_table.c.id
    )
    
    # Resolution time calculation
    resolution_time = func.extract(
        'epoch',
        incidents_table.c.dateupdated - incidents_table.c.datecreated
    ) / 3600  # Hours
    
    # FIXED: Use COUNT with CASE instead of SUM
    query = select(
        incidentcategories_table.c.id,
        incidentcategories_table.c.name,
        func.count(incidents_table.c.id).label("total_incidents"),
        func.count().filter(incidents_table.c.status == "2").label("resolved"),
        func.count().filter(incidents_table.c.status == "1").label("published"),
        func.count().filter(incidents_table.c.status == "3").label("rejected"),
        func.avg(
            case((incidents_table.c.status == "2", resolution_time))
        ).label("avg_resolution_hours")
    ).select_from(j).where(and_(*base_filter)).group_by(
        incidentcategories_table.c.id,
        incidentcategories_table.c.name
    ).order_by(func.count(incidents_table.c.id).desc())
    
    results = await database.fetch_all(query)
    
    performance_data = []
    
    for row in results:
        total = int(row['total_incidents'])
        resolved = int(row['resolved'] or 0)
        published = int(row['published'] or 0)
        rejected = int(row['rejected'] or 0)
        
        resolution_rate = (resolved / total * 100) if total > 0 else 0
        
        performance_data.append({
            "category_id": row['id'],
            "category_name": row['name'],
            "total_incidents": total,
            "resolved": resolved,
            "published": published,
            "rejected": rejected,
            "resolution_rate_pct": round(resolution_rate, 2),
            "avg_resolution_hours": round(float(row['avg_resolution_hours'] or 0), 2),
            "avg_resolution_days": round(float(row['avg_resolution_hours'] or 0) / 24, 2)
        })
    
    return {
        "categories": performance_data,
        "total_categories": len(performance_data)
    }


@app.get("/analytics/dashboard/widgets", tags=["analytics/dashboard"])
async def get_dashboard_widgets():
    """
    Get pre-configured widget data for dashboard
    """
    now = datetime.datetime.now()
    today_start = datetime.datetime.combine(now.date(), datetime.datetime.min.time())
    week_start = today_start - datetime.timedelta(days=7)
    month_start = today_start - datetime.timedelta(days=30)
    
    # Today's stats
    today_query = select(
        func.count(incidents_table.c.id).label("total"),
        func.count().filter(incidents_table.c.isemergency == True).label("emergency")
    ).where(
        and_(
            incidents_table.c.datecreated >= today_start,
            incidents_table.c.iscityreport == False
        )
    )
    today_stats = await database.fetch_one(today_query)
    
    # This week's stats
    week_query = select(
        func.count(incidents_table.c.id)
    ).where(
        and_(
            incidents_table.c.datecreated >= week_start,
            incidents_table.c.iscityreport == False
        )
    )
    week_count = await database.fetch_one(week_query)
    
    # Pending approval count
    pending_query = select(
        func.count(incidents_table.c.id)
    ).where(
        and_(
            incidents_table.c.status == "0",
            incidents_table.c.iscityreport == False
        )
    )
    pending_count = await database.fetch_one(pending_query)
    
    # Active users this month
    active_users_query = select(
        func.count(func.distinct(incidents_table.c.createdby))
    ).where(
        and_(
            incidents_table.c.datecreated >= month_start,
            incidents_table.c.iscityreport == False
        )
    )
    active_users = await database.fetch_one(active_users_query)
    
    return {
        "today": {
            "total_incidents": int(today_stats['total']) if today_stats else 0,
            "emergency_incidents": int(today_stats['emergency'] or 0) if today_stats else 0
        },
        "this_week": {
            "total_incidents": int(week_count[0]) if week_count else 0
        },
        "pending_approval": int(pending_count[0]) if pending_count else 0,
        "active_users_this_month": int(active_users[0]) if active_users else 0,
        "timestamp": now.isoformat()
    }


@app.get("/analytics/reports/summary", tags=["analytics"])
async def get_comprehensive_report_summary(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """
    Generate comprehensive summary report
    """
    incidents_overview = await get_incidents_overview(start_date, end_date, False)
    category_breakdown = await get_incidents_by_category_v2(start_date, end_date, False, 10)
    hotspots = await get_incident_hotspots(500, 3, start_date, end_date, None, False, 5)
    user_activity = await get_user_activity_stats(start_date, end_date, None)
    
    return {
        "period": {
            "start": start_date or (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d"),
            "end": end_date or datetime.datetime.now().strftime("%Y-%m-%d")
        },
        "incidents_overview": incidents_overview,
        "top_categories": category_breakdown,
        "top_hotspots": hotspots["hotspots"][:5],
        "user_activity": user_activity,
        "generated_at": datetime.datetime.now().isoformat()
    }

###################### END REPORTS ##################
# =============== Activity Logs API ===============

@app.get("/activitylogs", response_model=Page[ActivityLogSchema], tags=["activitylogs"], dependencies=[Depends(jwtBearer())])
async def get_activity_logs(
    start: str = None,
    end: str = None,
    module: str = None,
    action: str = None,
    userid: str = None,
    status_code: int = None,
    params: Params = Depends(),
):
    query = activitylogs_table.select()

    if start:
        try:
            start_dt = datetime.datetime.fromisoformat(start)
            query = query.where(activitylogs_table.c.datecreated >= start_dt)
        except Exception:
            pass
    if end:
        try:
            end_dt = datetime.datetime.fromisoformat(end)
            query = query.where(activitylogs_table.c.datecreated <= end_dt)
        except Exception:
            pass
    if module:
        query = query.where(activitylogs_table.c.module == module)
    if action:
        query = query.where(activitylogs_table.c.action_type == action)
    if userid:
        query = query.where(activitylogs_table.c.userid == userid)
    if status_code is not None:
        query = query.where(activitylogs_table.c.status_code == status_code)

    query = query.order_by(activitylogs_table.c.datecreated.desc())
    rows = await database.fetch_all(query)
    return paginate(rows)

add_pagination(app) 