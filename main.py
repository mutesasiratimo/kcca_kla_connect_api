from fastapi import FastAPI, File, UploadFile
from asyncio import streams
from collections import UserList
from email.mime import image
import hashlib
import math
import random
from turtle import title
from typing import List
import urllib.request 
from urllib.parse import urlparse, parse_qs
from unittest import result
from xmlrpc.client import DateTime
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
from fastapi import BackgroundTasks, FastAPI, Body, Depends, HTTPException
from app.model import *
from app.auth.jwt_handler import signJWT
from app.auth.jwt_bearer import jwtBearer
from sqlalchemy import select, join
from decouple import config
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import desc
from sqlalchemy import asc
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

UPLOAD_FOLDER = "uploads"

#Create upload folder if it does not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = FastAPI(
    # root_path="/apiklakonnect",
    title="KCCA Kla Connect",
    description= 'A system for reporting and managing incidents.',
    version="0.1.1",
    # terms_of_service="http://example.com/terms/",
    contact={
        "name": "KCCA",
        "url": "http://kcca.go.ug",
        "email": "info@kcca.go.ug",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
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
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = users_table.insert().values(
        id=gID,
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
        isclerk=user.isclerk,
        isengineer=user.isengineer,
        iscitizen=user.iscitizen,
        issuperadmin=user.issuperadmin,
        isadmin=user.isadmin,
        datecreated=gDate,
        status="1"
    )
    exists = await check_if_user_exists(user.email)
    if (exists):
        raise HTTPException(
            status_code=409, detail="User already exists with this phone number or email.")
    else:
        # otp = ""
        # otp = await generate_otp(gID)
        digits = "0123456789"
        OTP = ""
        for i in range(4):
            OTP += digits[math.floor(random.random() * 10)]
        email_address = user.email
        sms_number = user.phone
        sms_message = f"Welcome to Kla Konnect! Kindly use "+OTP+" as the OTP to activate your account"
        print(OTP)
        print(user.phone)
        print(sms_message)
        sms_gateway_url = 'https://sms.dmarkmobile.com/v2/api/send_sms/?spname=spesho@dmarkmobile.com&sppass=t4x1sms&numbers='+sms_number+'&msg='+sms_message+'&type=json'.replace(" ", "%20")
        
        # contents = urllib.request.urlopen(parsed_url).read()
        # background_tasks = BackgroundTasks()
        # background_tasks.add_task(send_email_asynchronous, title="Welcome to Kla Konnect", body=sms_message, to=email_address)
        # send_email_backgroundtasks(BackgroundTasks(), "Welcome to Kla Konnect", sms_message, email_address)
        # await send_email_asynchronous("Welcome to Kla Konnect", sms_message, email_address)
        
        await database.execute(query)
        parsed_url = urlparse(sms_gateway_url).query
        parse_qs(parsed_url)
        contents = urllib.request.urlopen(sms_gateway_url.replace(" ", "%20")).read()

        print(str(contents))
        # await send_email_asynchronous("Welcome to Kla Konnect", sms_message, email_address)
        # TO DO MAKE BACKGROUND EMAIL SENDING FUNCTIONAL, AWAIT SLOWS DOWN RESPONSE.
        background_tasks.add_task(send_welcome_email, email_address, user.firstname, OTP)
        return {
            **user.dict(), 
            "id": gID,
            "datecreated": gDate,
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
        incidentcategories_table.c.name.label("category_name"),
        incidentcategories_table.c.description.label("category_description"),
        incidentcategories_table.c.image.label("category_image"),
        incidentcategories_table.c.autoapprove.label("category_autoapprove"),
        incidentcategories_table.c.doesexpire.label("category_doesexpire"),
        incidentcategories_table.c.hourstoexpire.label("category_hourstoexpire"),
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
        incidentcategories_table.c.name.label("category_name"),
        incidentcategories_table.c.description.label("category_description"),
        incidentcategories_table.c.image.label("category_image"),
        incidentcategories_table.c.autoapprove.label("category_autoapprove"),
        incidentcategories_table.c.doesexpire.label("category_doesexpire"),
        incidentcategories_table.c.hourstoexpire.label("category_hourstoexpire"),
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
        incidentcategories_table.c.name.label("category_name"),
        incidentcategories_table.c.description.label("category_description"),
        incidentcategories_table.c.image.label("category_image"),
        incidentcategories_table.c.autoapprove.label("category_autoapprove"),
        incidentcategories_table.c.doesexpire.label("category_doesexpire"),
        incidentcategories_table.c.hourstoexpire.label("category_hourstoexpire"),
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
            "status": result["status"]
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
        status= incident.status
    )

    await database.execute(query)
    return {
        **incident.dict(),
        "id": gID,
        "datecreated": gDate
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
        incidentcategories_table.c.name.label("category_name"),
        incidentcategories_table.c.description.label("category_description"),
        incidentcategories_table.c.image.label("category_image"),
        incidentcategories_table.c.autoapprove.label("category_autoapprove"),
        incidentcategories_table.c.doesexpire.label("category_doesexpire"),
        incidentcategories_table.c.hourstoexpire.label("category_hourstoexpire"),
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
        incidentcategories_table.c.name.label("category_name"),
        incidentcategories_table.c.description.label("category_description"),
        incidentcategories_table.c.image.label("category_image"),
        incidentcategories_table.c.autoapprove.label("category_autoapprove"),
        incidentcategories_table.c.doesexpire.label("category_doesexpire"),
        incidentcategories_table.c.hourstoexpire.label("category_hourstoexpire"),
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
        incidentcategories_table.c.name.label("category_name"),
        incidentcategories_table.c.description.label("category_description"),
        incidentcategories_table.c.image.label("category_image"),
        incidentcategories_table.c.autoapprove.label("category_autoapprove"),
        incidentcategories_table.c.doesexpire.label("category_doesexpire"),
        incidentcategories_table.c.hourstoexpire.label("category_hourstoexpire"),
        incidents_table.c.createdby,
        incidents_table.c.datecreated,
        incidents_table.c.dateupdated,
        incidents_table.c.updatedby,
        incidents_table.c.status
    ).select_from(j).where(incidents_table.c.status == status and incidents_table.c.iscityreport == True).order_by(desc(incidents_table.c.datecreated))

    result = await database.fetch_all(query)
    return paginate(result)


@app.post("/reports/register", response_model=IncidentSchema, tags=["reports"], dependencies=[Depends(jwtBearer())])
async def register_report(incident: IncidentSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
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
            updatedby=incident.updatedby,
            dateupdated=gDate
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

@router.get("/news/archives", response_model=List[NewsArchiveGroup], tags=["news"])
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

##################### MAILER #########################

# test email standart sending mail
# @app.post('/email')
# async def simple_send(email: EmailSchema) -> JSONResponse:

#     message = MessageSchema(
#         subject='Fastapi-Mail module',
#         recipients=email.dict().get('email'),
#         body=html,
#         subtype='html',
#     )

#     fm = FastMail(conf)
#     await fm.send_message(message)
#     return JSONResponse(status_code=200, content={'message': 'email has been sent'})


# # this mail sending using starlettes background tasks, faster than the above one
# @app.post('/emailbackground')
# async def send_in_background(background_tasks: BackgroundTasks, email: EmailSchema) -> JSONResponse:

#     message = MessageSchema(
#         subject='Fastapi mail module',
#         recipients=email.dict().get('email'),
#         body='Simple background task ',
#     )

#     fm = FastMail(conf)

#     background_tasks.add_task(fm.send_message, message)

#     return JSONResponse(status_code=200, content={'message': 'email has been sent'})


####################### END MAILER ###################

add_pagination(app) 