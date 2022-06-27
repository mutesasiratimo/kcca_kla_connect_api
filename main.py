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
from fastapi import FastAPI, Body, Depends, HTTPException
from app.model import *
from app.auth.jwt_handler import signJWT
from app.auth.jwt_bearer import jwtBearer
from decouple import config
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import desc
from sqlalchemy import asc


app = FastAPI()

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

################### USERS ###################


@app.get("/get_users", response_model=List[UserSchema], tags=["user"])
async def get_all_users():
    query = users_table.select()
    result = await database.fetch_all(query)
    # if result:
    return result
    # else:
    #     raise HTTPException(status_code=204, detail='No users found')

@app.get("/get_citizens", response_model=List[UserSchema], tags=["user"])
async def get_all_citizens():
    query = users_table.select().where(users_table.c.iscitizen == True)
    result = await database.fetch_all(query)
    if result:
        return result
    else:
        raise HTTPException(status_code=204, detail='No citizens found')


@app.get("/get_clerks", response_model=List[UserSchema], tags=["user"])
async def get_all_clerks():
    query = users_table.select().where(users_table.c.isclerk == True)
    result = await database.fetch_all(query)
    if result:
        return result
    else:
        raise HTTPException(status_code=204, detail='No clerks found')

@app.get("/get_admins", response_model=List[UserSchema], tags=["user"])
async def get_all_admins():
    query = users_table.select().where(users_table.c.isadmin == True)
    result = await database.fetch_all(query)
    if result:
        return result
    else:
        raise HTTPException(status_code=204, detail='No admins found')

@app.get("/users/{userid}", response_model=UserSchema, tags=["user"])
async def get_user_by_id(userid: str):
    query = users_table.select().where(users_table.c.id == userid)
    result = await database.fetch_one(query)
    if result:
        print(result["firstname"])
        return result
    else:
        raise HTTPException(status_code=404, detail='User not found')


@app.get("/users/name/{userid}", tags=["user"])
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
    query = users_table.select().where( users_table.c.email == user.username)
    result = await database.fetch_one(query)
    if result:
        # return result
        if result["password"] == user.password:
            print(result["password"])
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
        raise HTTPException(status_code=401, detail='Not authorized')
    # else:
    #     raise HTTPException(status_code=404, detail='User does not exist')


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


@app.post("/users/signup", tags=["user"])
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
            "token": signJWT(user.username),
            # "otp": await generate_otp(gID)
        }
    


@app.put("/users/update", response_model=UserUpdateSchema, tags=["user"])
async def update_user(user: UserUpdateSchema):
    # dateofbirth=datetime.datetime.strptime((user.dateofbirth), "%Y-%m-%d").date(),
    gDate = datetime.datetime.now()
    query = users_table.update().\
        where(users_table.c.id == user.id).\
        values(
            firstname=user.firstname,
            lastname=user.lastname,
            gender=user.gender,
            password=user.password,            
            roleid=user.roleid,
            photo=user.photo,
            email=user.email,
            address = user.address,
            status=user.status,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_user_by_id(user.id)


@app.put("/users/archive", response_model=UserUpdateSchema, tags=["user"])
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


@app.put("/users/restore", response_model=UserUpdateSchema, tags=["user"])
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


@app.delete("/users/{userid}", tags=["user"])
async def delete_user(userid: str):
    query = users_table.delete().where(users_table.c.id == userid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This user has been deleted!"
    }

@app.post("/users/otp", tags=["user"])
async def generate_otp(userid: str):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    expiry = datetime.datetime.now() + datetime.timedelta(hours=1)
    digits = "0123456789"
    OTP = ""
    queryuser = users_table.select().where(users_table.c.id == userid )
    result = await database.fetch_one(queryuser)
    if result:
        for i in range(4) :
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

@app.post("/users/verify", tags=["user"])
async def verify_otp(otp_obj: OtpVerifySchema):
    gDate = datetime.datetime.now()
    expiry = datetime.datetime.now() + datetime.timedelta(hours=1)
    queryuser = users_table.select().where(users_table.c.id == otp_obj.userid )
    resultuser = await database.fetch_one(queryuser)
    if resultuser:
        queryotp = otps_table.select().where(otps_table.c.otpcode == otp_obj.otpcode )
        resultotp = await database.fetch_one(queryotp)
        if resultotp:
            queryotppass = otps_table.update().\
                where(otps_table.c.otpcode == otp_obj.otpcode).\
                values(
                    status="0",
                    dateupdated=gDate
            )
            await database.execute(queryotppass)
        # else:
        #     queryotppass = otps_table.update().\
        #         where(otps_table.c.otpcode == otp_obj.otpcode).\
        #         values(
        #             status="0",
        #             dateupdated=gDate

        #     )
        #     await database.execute(queryotppass)
    else:
        raise HTTPException(
            status_code=401, detail="Invalid OTP Code.")


################## END USERS ###################

##################### INCIDENTS ######################

@app.get("/incidents",  tags=["incidents"])
async def get_all_incidents():
    query = incidents_table.select()
    results = await database.fetch_all(query)    
    res = []
    if results:
        for result in results:
            # incidentcategory = await get_incident_category_name_by_id(result["incidentcategoryid"))
            incidentcategory = "Unkown"
            res.append({
                "id" : result["id"],
                "name": result["name"],
                "description": result["description"],
                "incidentcategoryid": result["incidentcategoryid"],
                "incidentcategory": incidentcategory,
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
    


@app.get("/incidents/{incidentid}", response_model=IncidentSchema, tags=["incidents"])
async def get_incident_by_id(incidentid: str):
    query = incidents_table.select().where(incidents_table.c.id == incidentid)
    result = await database.fetch_one(query)
    return result


@app.get("/incidents/name/{incidentid}", tags=["incidents"])
async def get_incidentname_by_id(incidentid: str):
    query = incidents_table.select().where(incidents_table.c.id == incidentid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["name"]
        return fullname
    else:
        return "Unkown Incident"

@app.get("/incidents/user/{userid}", tags=["incidents"])
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

@app.get("/incidents/usercount/{userid}", tags=["incidents"])
async def get_incidentcounts_by_userid(userid: str):
    query = incidents_table.select().where(incidents_table.c.createdby == userid)
    results = await database.fetch_all(query)
    res = 0
    if results:
        for result in results:
            res +=1
    
    return res
    


@app.post("/incidents/register", response_model=IncidentSchema, tags=["incidents"])
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
        status="1"
    )

    await database.execute(query)
    return {
        **incident.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/incidents/update", response_model=IncidentUpdateSchema, tags=["incidents"])
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
            createdby = incident.createdby,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_incident_by_id(incident.id)


@app.put("/incidents/archive", response_model=IncidentUpdateSchema, tags=["incidents"])
async def archive_incident(incidentid: str):
    gDate = datetime.datetime.now()
    query = incidents_table.update().\
        where(incidents_table.c.id == incidentid).\
        values(
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_incident_by_id(incidentid)


@app.put("/incidents/restore", response_model=IncidentUpdateSchema, tags=["incidents"])
async def restore_incident(incidentid: str):
    gDate = datetime.datetime.now()
    query = incidents_table.update().\
        where(incidents_table.c.id == incidentid).\
        values(
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_incident_by_id(incidentid)


@app.delete("/incidents/{incidentid}", tags=["incidents"])
async def delete_incident(incidentid: str):
    query = incidents_table.delete().where(incidents_table.c.id == incidentid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This incident has been deleted!"
    }

###################### END INCIDENTS ##################

###################### INCIDENT_CATEGORIES ######################

@app.get("/incidentcategories", response_model=List[IncidentCategoriesSchema], tags=["incidentcategories"])
async def get_all_incident_categories():
    query = incidentcategories_table.select()
    return await database.fetch_all(query)


@app.get("/incidentcategories/{incidentcategoryid}", response_model=IncidentCategoriesSchema, tags=["incidentcategories"])
async def get_incident_category_by_id(incidentcategoryid: str):
    query = incidentcategories_table.select().where(incidentcategories_table.c.id == incidentcategoryid)
    result = await database.fetch_one(query)
    return result

@app.get("/incidents/name/{incidentid}", tags=["incidents"])
async def get_incident_category_name_by_id(incidentcategoryid: str):
    query = incidentcategories_table.select().where(incidentcategories_table.c.id == incidentcategoryid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["name"]
        return fullname
    else:
        return "Unkown"


@app.post("/incidentcategories/register", response_model=IncidentCategoriesSchema, tags=["incidentcategories"])
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


@app.put("/incidentcategories/update", response_model=IncidentCategoriesUpdateSchema, tags=["incidentcategories"])
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


@app.put("/incidentcategories/archive", response_model=IncidentCategoriesUpdateSchema, tags=["incidentcategories"])
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


@app.put("/incidentcategories/restore", response_model=IncidentCategoriesUpdateSchema, tags=["incidentcategories"])
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


@app.delete("/incidentcategories/{incidentcategoryid}", tags=["incidentcategories"])
async def delete_incident_category(incidentcategoryid: str):
    query = incidentcategories_table.delete().where(incidentcategories_table.c.id == incidentcategoryid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This Incident category has been deleted!"
    }

###################### END INCIDENT_CATEGORIES ##################

###################### SAVED LOCATIONS ######################

@app.get("/savedlocations", response_model=List[SavedLocationSchema], tags=["savedlocations"])
async def get_all_saved_locations():
    query = savedlocations_table.select()
    return await database.fetch_all(query)


@app.get("/savedlocations/{savedlocationid}", response_model=SavedLocationSchema, tags=["savedlocations"])
async def get_saved_location_by_id(savedlocationid: str):
    query = savedlocations_table.select().where(savedlocations_table.c.id == savedlocationid)
    result = await database.fetch_one(query)
    return result


@app.get("/savedlocations/name/{savedlocationid}", tags=["savedlocations"])
async def get_saved_location_name_by_id(savedlocationid: str):
    query = savedlocations_table.select().where(savedlocations_table.c.id == savedlocationid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["name"]
        return fullname
    else:
        return "Unkown Incident"

@app.get("/savedlocations/user/{userid}", tags=["savedlocations"])
async def get_saved_locations_by_userid(userid: str):
    query = savedlocations_table.select().where(savedlocations_table.c.createdby == userid)
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            res.append(await get_saved_location_by_id(result["createdby"]))
        return res
    else:
        raise HTTPException(
            status_code=204, detail="User does not have any saved locations.")
    


@app.post("/savedlocations/register", response_model=SavedLocationSchema, tags=["savedlocations"])
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


@app.put("/savedlocations/update", response_model=SavedLocationUpdateSchema, tags=["savedlocations"])
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


@app.put("/savedlocations/archive", response_model=SavedLocationUpdateSchema, tags=["savedlocations"])
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


@app.put("/savedlocations/restore", response_model=SavedLocationUpdateSchema, tags=["savedlocations"])
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


@app.delete("/savedlocations/{savedlocationid}", tags=["savedlocations"])
async def delete_saved_location(savedlocationid: str):
    query = savedlocations_table.delete().where(savedlocations_table.c.id == savedlocationid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This Saved Location has been deleted!"
    }

###################### END SAVED LOCATIONS ##################

###################### TRIPS ######################

@app.get("/trips", response_model=List[TripSchema], tags=["trips"])
async def get_all_trips():
    query = trips_table.select()
    return await database.fetch_all(query)


@app.get("/trips/{savedlocationid}", response_model=TripSchema, tags=["trips"])
async def get_trip_by_id(savedlocationid: str):
    query = trips_table.select().where(trips_table.c.id == savedlocationid)
    result = await database.fetch_one(query)
    return result


@app.get("/trips/name/{savedlocationid}", tags=["trips"])
async def get_trip_name_by_id(savedlocationid: str):
    query = trips_table.select().where(trips_table.c.id == savedlocationid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["name"]
        return fullname
    else:
        return "Unkown Incident"

@app.get("/trips/user/{userid}", tags=["trips"])
async def get_trips_by_userid(userid: str):
    query = trips_table.select().where(trips_table.c.createdby == userid)
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            res.append(await get_trip_by_id(result["createdby"]))
        return res
    else:
        raise HTTPException(
            status_code=204, detail="User does not have any saved locations.")
    


@app.post("/trips/register", response_model=TripSchema, tags=["trips"])
async def register_trip(trip: TripSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = trips_table.insert().values(
        id=gID,
        startaddress=trip.startaddress,
        startlat=trip.startlat,
        startlong=trip.startlong,
        destinationaddress=trip.destinationaddress,
        destinationlat=trip.destinationlat,
        destinationlong=trip.destinationlong,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **trip.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/trips/update", response_model=TripUpdateSchema, tags=["trips"])
async def update_trip(trip: TripUpdateSchema):
    gDate = datetime.datetime.now()
    query = trips_table.update().\
        where(trips_table.c.id == trip.id).\
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


@app.put("/trips/archive", response_model=TripUpdateSchema, tags=["trips"])
async def archive_trip(tripid: str):
    gDate = datetime.datetime.now()
    query = trips_table.update().\
        where(trips_table.c.id == tripid).\
        values(
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_trip_by_id(id)


@app.put("/trips/restore", response_model=TripUpdateSchema, tags=["trips"])
async def restore_trip(tripid: str):
    gDate = datetime.datetime.now()
    query = trips_table.update().\
        where(trips_table.c.id == tripid).\
        values(
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_trip_by_id(tripid)


@app.delete("/trips/{tripid}", tags=["trips"])
async def delete_trip(tripid: str):
    query = trips_table.delete().where(trips_table.c.id == tripid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This Trip has been deleted!"
    }

###################### END TRIPS ##################

###################### DESIGNATIONS ######################


@app.get("/designations", response_model=List[DesignationSchema], tags=["designations"])
async def get_all_designations():
    query = designations_table.select()
    return await database.fetch_all(query)


@app.get("/designations/{roleid}", response_model=DesignationSchema, tags=["designations"])
async def get_designation_by_id(roleid: str):
    query = designations_table.select().where(designations_table.c.id == roleid)
    result = await database.fetch_one(query)
    return result


@app.get("/designations/name/{roleid}", tags=["designations"])
async def get_designationname_by_id(roleid: str):
    query = designations_table.select().where(designations_table.c.id == roleid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["designationname"]
        return fullname
    else:
        return "Unkown Role"


@app.post("/designations/register", response_model=DesignationSchema, tags=["designations"])
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


@app.put("/designations/update", response_model=DesignationUpdateSchema, tags=["designations"])
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


@app.put("/designations/archive", response_model=DesignationUpdateSchema, tags=["designations"])
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


@app.put("/designations/restore", response_model=DesignationUpdateSchema, tags=["designations"])
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


@app.delete("/designations/{designationid}", tags=["designations"])
async def delete_designation(designationid: str):
    query = designations_table.delete().where(designations_table.c.id == designationid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This designation has been deleted!"
    }

###################### END DESIGNATION ##################

###################### DEPARTMENTS ######################


@app.get("/departments", response_model=List[DepartmentSchema], tags=["departments"])
async def get_all_departments():
    query = departments_table.select()
    return await database.fetch_all(query)


@app.get("/departments/{departmentid}", response_model=DepartmentSchema, tags=["departments"])
async def get_department_by_id(departmentid: str):
    query = departments_table.select().where(departments_table.c.id == departmentid)
    result = await database.fetch_one(query)
    return result


@app.get("/departments/name/{departmentid}", tags=["departments"])
async def get_department_name_by_id(departmentid: str):
    query = departments_table.select().where(departments_table.c.id == departmentid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["departmentname"]
        return fullname
    else:
        return "Unkown Department"


@app.post("/departments/register", response_model=DepartmentSchema, tags=["departments"])
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


@app.put("/departments/update", response_model=DepartmentSchema, tags=["departments"])
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


@app.put("/departments/archive", response_model=DepartmentSchema, tags=["departments"])
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


@app.put("/departments/restore", response_model=DepartmentSchema, tags=["departments"])
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


@app.delete("/departments/{departmentid}", tags=["departments"])
async def delete_department(departmentid: str):
    query = departments_table.delete().where(departments_table.c.id == departmentid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This department has been deleted!"
    }

###################### END SUBJECTS ##################

###################### CLASS LEVELS ######################


@app.get("/languages", tags=["languages"])
async def get_all_languages():
    query = languages_table.select()
    results = await database.fetch_all(query)
    if results:        
        return results
    else:
        raise HTTPException(status_code=204, detail="No languages found")

@app.get("/languages/{languageid}", response_model=LanguageSchema, tags=["languages"])
async def get_language_by_id(languageid: str):
    query = languages_table.select().where(languages_table.c.id == languageid)
    result = await database.fetch_one(query)
    if result:        
        return result
    else:
        raise HTTPException(status_code=204, detail="No language found")


@app.get("/languages/name/{languageid}", tags=["languages"])
async def get_languagename_by_id(languageid: str):
    query = languages_table.select().where(languages_table.c.id == languageid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["levelname"]
        return fullname
    else:
        return "Unknown Language"


@app.post("/languages/register", response_model=LanguageSchema, tags=["languages"])
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


@app.put("/languages/update", response_model=LanguageUpdateSchema, tags=["languages"])
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


@app.put("/languages/archive", response_model=LanguageUpdateSchema, tags=["languages"])
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


@app.put("/languages/restore", response_model=LanguageUpdateSchema, tags=["languages"])
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


@app.delete("/languages/{languageid}", tags=["languages"])
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
