from asyncio import streams
from collections import UserList
from email.mime import image
import hashlib
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
    if result:
        return result
    else:
        raise HTTPException(status_code=204, detail='No users found')

@app.get("/get_citizens", response_model=List[UserSchema], tags=["user"])
async def get_all_citizens(schoolid: str):
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

@app.get("/get_school_parents/{schoolid}", response_model=List[UserSchema], tags=["user"])
async def get_all_school_parents(schoolid: str):
    query = users_table.select().where(users_table.c.isparent == True).where(users_table.c.schoolid == schoolid)
    result = await database.fetch_all(query)
    if result:
        return result
    else:
        raise HTTPException(status_code=204, detail='No parents found')


@app.get("/users/{userid}", response_model=UserSchema, tags=["user"])
async def get_user_by_id(userid: str):
    query = users_table.select().where(users_table.c.id == userid)
    result = await database.fetch_one(query)
    if result:
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
    query = users_table.select().where(users_table.c.username ==
                                       user.username or users_table.c.email == user.username)
    result = await database.fetch_one(query)
    if result:
        if result.get("password") == user.password:
            return {
                "userid": result.get("id"),
                "firstname": result.get("firstname"),
                "lastname": result.get("lastname"),
                "firstname": result.get("firstname"),
                "username": result.get("username"),
                "email": result.get("email"),
                "gender": result.get("gender"),
                "phone": result.get("phone"),
                "mobile": result.get("mobile"),
                "address": result.get("address"),
                "addresslat": result.get("addresslat"),
                "addresslong": result.get("addresslong"),
                "nin": result.get("nin"),
                "dateofbirth": result.get("dateofbirth"),
                "photo": result.get("photo"),
                "isadmin": result.get("isadmin"),
                "issuperadmin": result.get("issuperadmin"),
                "isclerk": result.get("isclerk"),
                "iscitizen": result.get("iscitizen"),
                "roleid": result.get("roleid"),
                "token": signJWT(user.username),
                "status": result.get("status")
            }
        else:
            raise HTTPException(status_code=401, detail='Not authorized')
    else:
        raise HTTPException(status_code=404, detail='User does not exist')


@app.get("/users/emailauth/{email}", tags=["user"])
async def user_email_authentication(email: EmailStr):
    query = users_table.select().where(users_table.c.email == email)
    result = await database.fetch_one(query)
    if result:
        return {
            "userid": result.get("id"),
                "firstname": result.get("firstname"),
                "lastname": result.get("lastname"),
                "firstname": result.get("firstname"),
                "username": result.get("username"),
                "email": result.get("email"),
                "gender": result.get("gender"),
                "phone": result.get("phone"),
                "mobile": result.get("mobile"),
                "address": result.get("address"),
                "addresslat": result.get("addresslat"),
                "addresslong": result.get("addresslong"),
                "nin": result.get("nin"),
                "dateofbirth": result.get("dateofbirth"),
                "photo": result.get("photo"),
                "isadmin": result.get("isadmin"),
                "issuperadmin": result.get("issuperadmin"),
                "isclerk": result.get("isclerk"),
                "iscitizen": result.get("iscitizen"),
                "roleid": result.get("roleid"),
                "token": signJWT(email),
                "status": result.get("status")
        }
    else:
        raise HTTPException(status_code=401, detail='Not Authorized')


@app.get("/users/checkexistence/{email}", tags=["user"])
async def check_if_user_exists(email: str):
    query = users_table.select().where(users_table.c.email ==
                                       email or users_table.c.phone == email)
    result = await database.fetch_one(query)
    if result:
        return True
    else:
        return False


@app.post("/users/signup", response_model=UserSignUpSchema, tags=["user"])
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
    
    return {
        **user.dict(),
        "id": gID,
        "datecreated": gDate,
        "token": signJWT(user.username),
        "status": "1"
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


################### END USERS ###################

###################### INCIDENTS ######################

@app.get("/incidents", response_model=List[IncidentSchema], tags=["incidents"])
async def get_all_incidents():
    query = incidents_table.select()
    return await database.fetch_all(query)


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
            res.append(await get_incident_by_id(result["schoolid"]))
        return res
    else:
        raise HTTPException(
            status_code=204, detail="User isn't attached to any school.")
    


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
async def update_user_school(category: IncidentCategoriesUpdateSchema):
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
async def archive_user_school(incidentcategoryid: str):
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
async def restore_user_school(incidentcategoryid: str):
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
async def delete_user_school(incidentcategoryid: str):
    query = incidentcategories_table.delete().where(incidentcategories_table.c.id == incidentcategoryid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This Incident category has been deleted!"
    }

###################### END INCIDENT_CATEGORIES ##################

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

###################### END LANGUAGES ##################
