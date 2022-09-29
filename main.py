from asyncio import streams
from collections import UserList
from email.mime import image
import hashlib
import math
import random
from turtle import title
from typing import List
from unittest import result
from xmlrpc.client import DateTime
import uvicorn
from fastapi import BackgroundTasks, FastAPI, Body, Depends, HTTPException
from app.model import *
from app.auth.jwt_handler import signJWT
from app.auth.jwt_bearer import jwtBearer
from decouple import config
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import desc
from sqlalchemy import asc
from app.send_mail import send_email_background, send_email_async, send_email_async_test

app = FastAPI(
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


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.get("/", tags=["welcome"])
def greet():
    return{"Hello": "Welcome to the KLA CONNECT API"}


################ EMAILS #####################

# @app.get('/send-email/asynchronous', tags=["mailer"])
async def send_email_asynchronous(title: str, body: str, to: EmailStr):
    await send_email_async(title, to, body)
    # await send_email_async_test()
    return 'Success'

# @app.get('/send-email/backgroundtasks', tags=["mailer"])


def send_email_backgroundtasks(background_tasks: BackgroundTasks):
    send_email_background(background_tasks, 'Hello World',
                          'mutestimo72@gmail.com', {'title': 'Hello World', 'name':       'John Doe'})
    return 'Success'

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
                    "firstname": result["firstname"],
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
async def register_user(user: UserSignUpSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = users_table.insert().values(
        id=gID,
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
        iscitizen=user.iscitizen,
        issuperadmin=user.issuperadmin,
        isadmin=user.isadmin,
        datecreated=gDate,
        status="1"
    )
    exists = await check_if_user_exists(user.email)
    if exists:
        raise HTTPException(
            status_code=409, detail="User already exists with this phone number or email.")
    else:
        await database.execute(query)
        return {
            **user.dict(),
            "id": gID,
            "datecreated": gDate,
            "token": signJWT(user.username),
            "status": "1"
        }


@app.put("/users/update", response_model=UserUpdateSchema, tags=["user"], dependencies=[Depends(jwtBearer())])
async def update_user(user: UserUpdateSchema):
    # dateofbirth=datetime.datetime.strptime((user.dateofbirth), "%Y-%m-%d").date(),
    gDate = datetime.datetime.now()
    query = users_table.update().\
        where(users_table.c.id == user.id).\
        values(
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

@app.put("/users/updateprofile", response_model=UserUpdateSchema, tags=["user"], dependencies=[Depends(jwtBearer())])
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

@app.put("/users/updateuserrights", tags=["user"], dependencies=[Depends(jwtBearer())])
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


@app.get("/users/resetpassword/{email}", tags=["user"], dependencies=[Depends(jwtBearer())])
async def reset_password(email: str):
    # dateofbirth=datetime.datetime.strptime((user.dateofbirth), "%Y-%m-%d").date(),
    gDate = datetime.datetime.now()
    query = users_table.select().where(users_table.c.email ==
                                       email)
    result = await database.fetch_one(query)
    if result:
        email = result["email"]
        userid = result["id"]
        otp = await generate_otp(userid)
        print(otp)
        await send_email_asynchronous("Kla Connect Password Reset", "The OTP for resetting your password is "+otp + "\n", email)

        return {
            "otp": otp
        }
    else:
        raise HTTPException(
            status_code=204, detail="User does not exist.")


@app.put("/users/archive", response_model=UserUpdateSchema, tags=["user"], dependencies=[Depends(jwtBearer())])
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


@app.put("/users/restore", response_model=UserUpdateSchema, tags=["user"], dependencies=[Depends(jwtBearer())])
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
            return "Password updated successfully"
    else:
        raise HTTPException(
            status_code=401, detail="Invalid OTP Code.")


@app.post("/users/updatepassword", tags=["user"], dependencies=[Depends(jwtBearer())])
async def update_password(userid: str, password: str):
    gDate = datetime.datetime.now()
    query = users_table.update().\
        where(users_table.c.id == userid).\
        values(
            password=password,
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

@app.get("/incidents",  tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def get_all_incidents():
    query = incidents_table.select().order_by(desc(incidents_table.c.datecreated))
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            incidentcategory = await get_incident_category_name_by_id(result["incidentcategoryid"])
            # incidentcategory = "Unkown"
            res.append({
                "id": result["id"],
                "name": result["name"],
                "description": result["description"],
                "incidentcategoryid": "",
                "incidentcategory": result["incidentcategoryid"],
                "incidentcategoryobj": {},
                # "incidentcategoryobj": await get_incident_category_by_id(result["incidentcategoryid"]),
                "address": result["address"],
                "addresslat": result["addresslat"],
                "addresslong": result["addresslong"],
                "isemergency": result["isemergency"],
                "file1": result["file1"],
                "file2": result["file2"],
                "file3": result["file3"],
                "file4": result["file4"],
                "file5": result["file5"],
                "datecreated": result["datecreated"],
                "createdby": result["createdby"],
                "createdbyobj": {},
                # "createdbyobj": await get_user_by_id(result["createdby"]),
                "dateupdated": result["dateupdated"],
                "updatedby": result["updatedby"],
                "status": result["status"]
            })
        return res
    else:
        raise HTTPException(
            status_code=204, detail="No incidents nearby.")

@app.get("/incidents/approved",  tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def get_approved_incidents():
    query = incidents_table.select().where(incidents_table.c.status == "1").order_by(desc(incidents_table.c.datecreated))
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            # incidentcategory = await get_incident_category_name_by_id(result["incidentcategoryid"])
            # incidentcategory = "Unkown"
            res.append({
                "id": result["id"],
                "name": result["name"],
                "description": result["description"],
                "incidentcategoryid": "",
                "incidentcategory": result["incidentcategoryid"],
                "address": result["address"],
                "addresslat": result["addresslat"],
                "addresslong": result["addresslong"],
                "isemergency": result["isemergency"],
                "file1": result["file1"],
                "file2": result["file2"],
                "file3": result["file3"],
                "file4": result["file4"],
                "file5": result["file5"],
                "datecreated": result["datecreated"],
                "createdby": result["createdby"],
                "dateupdated": result["dateupdated"],
                "updatedby": result["updatedby"],
                "status": result["status"]
            })
        return res
    else:
        raise HTTPException(
            status_code=204, detail="No approved incidents.")

@app.get("/incidents/unapproved",  tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def get_unapproved_incidents():
    query = incidents_table.select().where(incidents_table.c.status == "0").order_by(desc(incidents_table.c.datecreated))
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            incidentcategory = await get_incident_category_name_by_id(result["incidentcategoryid"])
            # incidentcategory = "Unkown"
            res.append({
                "id": result["id"],
                "name": result["name"],
                "description": result["description"],
                "incidentcategoryid": "",
                "incidentcategory": result["incidentcategoryid"],
                "address": result["address"],
                "addresslat": result["addresslat"],
                "addresslong": result["addresslong"],
                "isemergency": result["isemergency"],
                "file1": result["file1"],
                "file2": result["file2"],
                "file3": result["file3"],
                "file4": result["file4"],
                "file5": result["file5"],
                "datecreated": result["datecreated"],
                "createdby": result["createdby"],
                "dateupdated": result["dateupdated"],
                "updatedby": result["updatedby"],
                "status": result["status"]
            })
        return res
    else:
        raise HTTPException(
            status_code=204, detail="No unapproved incidents.")

@app.get("/incidents/resolved",  tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def get_resolved_incidents():
    query = incidents_table.select().where(incidents_table.c.status == "2").order_by(desc(incidents_table.c.datecreated))
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            incidentcategory = await get_incident_category_name_by_id(result["incidentcategoryid"])
            # incidentcategory = "Unkown"
            res.append({
                "id": result["id"],
                "name": result["name"],
                "description": result["description"],
                "incidentcategoryid": "",
                "incidentcategory": result["incidentcategoryid"],
                "address": result["address"],
                "addresslat": result["addresslat"],
                "addresslong": result["addresslong"],
                "isemergency": result["isemergency"],
                "file1": result["file1"],
                "file2": result["file2"],
                "file3": result["file3"],
                "file4": result["file4"],
                "file5": result["file5"],
                "datecreated": result["datecreated"],
                "createdby": result["createdby"],
                "dateupdated": result["dateupdated"],
                "updatedby": result["updatedby"],
                "status": result["status"]
            })
        return res
    else:
        raise HTTPException(
            status_code=204, detail="No incidents nearby.")

@app.get("/incidents/rejected",  tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def get_rejected_incidents():
    query = incidents_table.select().where(incidents_table.c.status == "3").order_by(desc(incidents_table.c.datecreated))
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            incidentcategory = await get_incident_category_name_by_id(result["incidentcategoryid"])
            # incidentcategory = "Unkown"
            res.append({
                "id": result["id"],
                "name": result["name"],
                "description": result["description"],
                "incidentcategoryid": "",
                "incidentcategory": result["incidentcategoryid"],
                "address": result["address"],
                "addresslat": result["addresslat"],
                "addresslong": result["addresslong"],
                "isemergency": result["isemergency"],
                "file1": result["file1"],
                "file2": result["file2"],
                "file3": result["file3"],
                "file4": result["file4"],
                "file5": result["file5"],
                "datecreated": result["datecreated"],
                "createdby": result["createdby"],
                "dateupdated": result["dateupdated"],
                "updatedby": result["updatedby"],
                "status": result["status"]
            })
        return res
    else:
        raise HTTPException(
            status_code=204, detail="No incidents nearby.")

@app.get("/incidents/count", tags=["incidents"])
async def get_incidents_count():
    counter = 0
    query = incidents_table.select()
    results = await database.fetch_all(query)
    if results:
        for result in results:
            counter += 1

    return counter

@app.get("/incidents/stats", tags=["incidents"])
async def get_incidents_stats():
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
        
    approvedquery = incidents_table.select().where(incidents_table.c.status == "1")
    approvedresults = await database.fetch_all(approvedquery)
    if approvedresults:
        for result in approvedresults:
            approvedcounter += 1
    
    rejectedquery = incidents_table.select().where(incidents_table.c.status == "3")
    rejectedresults = await database.fetch_all(rejectedquery)
    if rejectedresults:
        for result in rejectedresults:
            rejectedcounter += 1

    resolvedquery = incidents_table.select().where(incidents_table.c.status == "2")
    resolvedresults = await database.fetch_all(resolvedquery)
    if resolvedresults:
        for result in resolvedresults:
            resolvedcounter += 1

    return {
        "unapproved": unapprovedcounter,
        "approved": approvedcounter,
        "resolved": resolvedcounter,
        "rejected": rejectedcounter,
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


@app.put("/incidents/update", response_model=IncidentUpdateSchema, tags=["incidents"], dependencies=[Depends(jwtBearer())])
async def update_incident(incident: IncidentUpdateSchema):
    gDate = datetime.datetime.now()
    query = incidents_table.update().\
        where(incidents_table.c.id == incident.id).\
        values(
            name=incident.name,
            description=incident.description,
            isemergency=incident.isemergency,
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
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_incident_by_id(incident.id)


@app.put("/incidents/archive", response_model=IncidentUpdateSchema, tags=["incidents"], dependencies=[Depends(jwtBearer())])
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


@app.put("/incidents/restore", response_model=IncidentUpdateSchema, tags=["incidents"], dependencies=[Depends(jwtBearer())])
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

@app.put("/incidents/resolve", response_model=IncidentUpdateSchema, tags=["incidents"], dependencies=[Depends(jwtBearer())])
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

@app.put("/incidents/reject", response_model=IncidentUpdateSchema, tags=["incidents"], dependencies=[Depends(jwtBearer())])
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

@app.put("/incidents/state", response_model=IncidentUpdateSchema, tags=["incidents"], dependencies=[Depends(jwtBearer())])
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
    query = kccareports_table.select().order_by(desc(kccareports_table.c.datecreated))
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            res.append({
                "id": result["id"],
                "name": result["name"],
                "description": result["description"],
                "reporttype": result["reporttype"],
                "reference": result["reference"],
                "address": result["address"],
                "addresslat": result["addresslat"],
                "addresslong": result["addresslong"],
                "isemergency": result["isemergency"],
                "attachment": result["attachment"],
                "likes": await get_post_likes_count_by_id(result["id"]),
                "dislikes": await get_post_dislikes_count_by_id(result["id"]),
                "commentscount": await get_post_comments_count_by_id(result["id"]),
                "datecreated": result["datecreated"],
                "createdby": result["createdby"],
                # "createdbyobj": await get_user_by_id(result["createdby"]),
                "dateupdated": result["dateupdated"],
                "updatedby": result["updatedby"],
                "status": result["status"]
            })
        return res
    else:
        raise HTTPException(
            status_code=204, detail="No incidents nearby.")

@app.get("/reports/count", tags=["reports"])
async def get_reports_count():
    counter = 0
    query = kccareports_table.select()
    results = await database.fetch_all(query)
    if results:
        for result in results:
            counter += 1

    return counter


@app.get("/reports/{reportid}", response_model=ReportSchema, tags=["reports"], dependencies=[Depends(jwtBearer())])
async def get_report_by_id(reportid: str):
    query = kccareports_table.select().where(kccareports_table.c.id == reportid)
    result = await database.fetch_one(query)
    if result:
        return {
            "id": result["id"],
            "name": result["name"],
            "description": result["description"],
            "reporttype": result["reporttype"],
            "reference": result["reference"],
            "address": result["address"],
            "addresslat": result["addresslat"],
            "addresslong": result["addresslong"],
            "isemergency": result["isemergency"],
            "attachment": result["attachment"],
            "likes": await get_post_likes_count_by_id(result["id"]),
            "dislikes": await get_post_dislikes_count_by_id(result["id"]),
            "commentscount": await get_post_comments_count_by_id(result["id"]),
            "datecreated": result["datecreated"],
            "createdby": result["createdby"],
            # "createdbyobj": await get_user_by_id(result["createdby"]),
            "dateupdated": result["dateupdated"],
            "updatedby": result["updatedby"],
            "status": result["status"]
        }


@app.get("/reports/user/{userid}", tags=["reports"], dependencies=[Depends(jwtBearer())])
async def get_reports_by_userid(userid: str):
    query = kccareports_table.select().where(kccareports_table.c.createdby == userid)
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            res.append(await get_incident_by_id(result["id"]))
        return res
    else:
        raise HTTPException(
            status_code=204, detail="User has not posted any reports.")


@app.get("/reports/usercount/{userid}", tags=["reports"], dependencies=[Depends(jwtBearer())])
async def get_reportcounts_by_userid(userid: str):
    query = kccareports_table.select().where(kccareports_table.c.createdby == userid)
    results = await database.fetch_all(query)
    res = 0
    if results:
        for result in results:
            res += 1

    return res


@app.post("/reports/register", response_model=ReportSchema, tags=["reports"], dependencies=[Depends(jwtBearer())])
async def register_report(report: ReportSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = kccareports_table.insert().values(
        id=gID,
        name=report.name,
        description=report.description,
        reporttype=report.reporttype,
        reference=report.reference,
        isemergency=report.isemergency,
        address=report.address,
        addresslat=report.addresslat,
        addresslong=report.addresslong,
        attachment=report.attachment,
        createdby=report.createdby,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **report.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/reports/update", response_model=ReportUpdateSchema, tags=["reports"], dependencies=[Depends(jwtBearer())])
async def update_report(report: ReportUpdateSchema):
    gDate = datetime.datetime.now()
    query = kccareports_table.update().\
        where(kccareports_table.c.id == report.id).\
        values(
            name=report.name,
            description=report.description,
            reporttype=report.reporttype,
            reference=report.reference,
            isemergency=report.isemergency,
            address=report.address,
            addresslat=report.addresslat,
            addresslong=report.addresslong,
            attachment=report.attachment,
            createdby=report.createdby,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_report_by_id(report.id)


@app.put("/reports/archive", response_model=ReportUpdateSchema, tags=["reports"], dependencies=[Depends(jwtBearer())])
async def archive_report(reportid: str):
    gDate = datetime.datetime.now()
    query = kccareports_table.update().\
        where(kccareports_table.c.id == reportid).\
        values(
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_report_by_id(reportid)


@app.put("/reports/restore", response_model=ReportUpdateSchema, tags=["reports"], dependencies=[Depends(jwtBearer())])
async def restore_report(incidentid: str):
    gDate = datetime.datetime.now()
    query = kccareports_table.update().\
        where(kccareports_table.c.id == incidentid).\
        values(
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_report_by_id(incidentid)


@app.delete("/reports/{reportid}", tags=["reports"], dependencies=[Depends(jwtBearer())])
async def delete_report(reportid: str):
    query = kccareports_table.delete().where(kccareports_table.c.id == reportid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This report has been deleted!"
    }


@app.post("/reports/comments", response_model=CommentSchema, tags=["posts"])
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

@app.delete("/reports/comments/{feedbackid}", tags=["reports"])
async def delete_comment(feedbackid: str):
    query = feedback_table.delete().where(feedback_table.c.id == feedbackid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This feedback has been deleted!"
    }

@app.get("/reports/comments/{postid}", tags=["reports"])
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

@app.get("/reports/commentscount/{postid}", tags=["reports"])
async def get_post_comments_count_by_id(postid: str):
    counter = 0
    query = feedback_table.select().where(feedback_table.c.postid == postid)
    results = await database.fetch_all(query)
    if results:
        for result in results:
            counter += 1

    return counter

@app.post("/reports/like", tags=["reports"])
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

@app.post("/reports/dislike", tags=["reports"])
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

@app.get("/reports/likes/{postid}", tags=["reports"])
async def get_post_likes_count_by_id(postid: str):
    counter = 0
    query = likes_table.select().where(likes_table.c.postid == postid).where(likes_table.c.isliked == True)
    results = await database.fetch_all(query)
    if results:
        for result in results:
            counter += 1

    return counter

@app.get("/reports/dislikes/{postid}", tags=["reports"])
async def get_post_dislikes_count_by_id(postid: str):
    counter = 0
    query = likes_table.select().where(likes_table.c.postid == postid).where(likes_table.c.isliked == False)
    results = await database.fetch_all(query)
    if results:
        for result in results:
            counter += 1

    return counter

@app.post("/reports/userliked/{postid}/{userid}", tags=["reports"])
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


@app.put("/news/update", response_model=NewsUpdateSchema, tags=["news"])
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


@app.put("/news/archive", response_model=NewsUpdateSchema, tags=["news"])
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
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_news_by_id(news.id)


@app.put("/news/restore", response_model=NewsUpdateSchema, tags=["news"])
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
        description=category.description,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **category.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/incidentcategories/update", response_model=IncidentCategoriesUpdateSchema, tags=["incidentcategories"], dependencies=[Depends(jwtBearer())])
async def update_incident_category(category: IncidentCategoriesUpdateSchema):
    gDate = datetime.datetime.now()
    query = incidentcategories_table.update().\
        where(incidentcategories_table.c.id == category.id).\
        values(
            name=category.name,
            description=category.description,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_incident_category_by_id(category.id)


@app.put("/incidentcategories/archive", response_model=IncidentCategoriesUpdateSchema, tags=["incidentcategories"], dependencies=[Depends(jwtBearer())])
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


@app.put("/incidentcategories/restore", response_model=IncidentCategoriesUpdateSchema, tags=["incidentcategories"], dependencies=[Depends(jwtBearer())])
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


@app.put("/savedlocations/update", response_model=SavedLocationUpdateSchema, tags=["savedlocations"], dependencies=[Depends(jwtBearer())])
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


@app.put("/savedlocations/archive", response_model=SavedLocationUpdateSchema, tags=["savedlocations"], dependencies=[Depends(jwtBearer())])
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


@app.put("/savedlocations/restore", response_model=SavedLocationUpdateSchema, tags=["savedlocations"], dependencies=[Depends(jwtBearer())])
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


@app.put("/trips/update", response_model=TripUpdateSchema, tags=["trips"], dependencies=[Depends(jwtBearer())])
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


@app.put("/trips/archive", response_model=TripUpdateSchema, tags=["trips"], dependencies=[Depends(jwtBearer())])
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


@app.put("/trips/restore", response_model=TripUpdateSchema, tags=["trips"], dependencies=[Depends(jwtBearer())])
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


@app.put("/designations/update", response_model=DesignationUpdateSchema, tags=["designations"], dependencies=[Depends(jwtBearer())])
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


@app.put("/designations/archive", response_model=DesignationUpdateSchema, tags=["designations"], dependencies=[Depends(jwtBearer())])
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


@app.put("/designations/restore", response_model=DesignationUpdateSchema, tags=["designations"], dependencies=[Depends(jwtBearer())])
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


@app.put("/departments/update", response_model=DepartmentSchema, tags=["departments"], dependencies=[Depends(jwtBearer())])
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


@app.put("/departments/archive", response_model=DepartmentSchema, tags=["departments"], dependencies=[Depends(jwtBearer())])
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


@app.put("/departments/restore", response_model=DepartmentSchema, tags=["departments"], dependencies=[Depends(jwtBearer())])
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


@app.put("/languages/update", response_model=LanguageUpdateSchema, tags=["languages"], dependencies=[Depends(jwtBearer())])
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


@app.put("/languages/archive", response_model=LanguageUpdateSchema, tags=["languages"], dependencies=[Depends(jwtBearer())])
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


@app.put("/languages/restore", response_model=LanguageUpdateSchema, tags=["languages"], dependencies=[Depends(jwtBearer())])
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
