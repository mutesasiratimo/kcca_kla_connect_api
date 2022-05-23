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
    return{"Hello": "Welcome to the school system"}

################### USERS ###################


@app.get("/get_users", response_model=List[UserSchema], tags=["user"])
async def get_all_users():
    query = users_table.select()
    result = await database.fetch_all(query)
    if result:
        return result
    else:
        raise HTTPException(status_code=204, detail='No users found')


@app.get("/get_teachers", response_model=List[UserSchema], tags=["user"])
async def get_all_teachers():
    query = users_table.select().where(users_table.c.isteacher == True)
    result = await database.fetch_all(query)
    if result:
        return result
    else:
        raise HTTPException(status_code=204, detail='No teachers found')


@app.get("/get_class_teachers/available", tags=["user"])
async def get_available_class_teachers():
    query = users_table.select().where(users_table.c.isteacher == True)

    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            query2 = classes_table.select().where(
                classes_table.c.classteacherid == result.get("id"))
            results2 = await database.fetch_all(query2)
            if not results2:
                res.append(result)
        return res
    else:
        raise HTTPException(status_code=404, detail='No teachers found')


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
            print(result.get("id"))
            return {
                "userid": result.get("id"),
                "firstname": result.get("firstname"),
                "lastname": result.get("lastname"),
                "firstname": result.get("firstname"),
                "username": result.get("username"),
                "email": result.get("email"),
                "gender": result.get("gender"),
                "phone": result.get("phone"),
                "address": result.get("address"),
                "dateofbirth": result.get("dateofbirth"),
                "photo": result.get("photo"),
                "isadmin": result.get("isadmin"),
                "isparent": result.get("isparent"),
                "isteacher": result.get("isteacher"),
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
            "address": result.get("address"),
            "dateofbirth": result.get("dateofbirth"),
            "photo": result.get("photo"),
            "isadmin": result.get("isadmin"),
            "isparent": result.get("isparent"),
            "isteacher": result.get("isteacher"),
            "roleid": result.get("roleid"),
            "token": signJWT(result.get("username")),
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
        dateofbirth=datetime.datetime.strptime(
            (user.dateofbirth), "%Y-%m-%d").date(),
        address=user.address,
        photo=user.photo,
        email=user.email,
        gender=user.gender,
        isteacher=user.isteacher,
        isparent=user.isparent,
        isadmin=user.isadmin,
        datecreated=gDate,
        status="1"
    )
    exists = await check_if_user_exists(user.phone)
    student_exists = await check_if_student_exists(user.studentid)
    if exists:
        raise HTTPException(
            status_code=409, detail="User already exists with this phone/email.")
    elif not student_exists:
        raise HTTPException(
            status_code=404, detail="No student with this student number exists.")
    else:
        await database.execute(query)
        await register_wallet(gID)
        return {
            **user.dict(),
            "id": gID,
            "datecreated": gDate,
            "token": signJWT(user.username),
            "status": "1"
        }


@app.post("/users/register", response_model=UserSignUpSchema, tags=["user"])
async def register_non_app_user(user: UserSignUpSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = users_table.insert().values(
        id=gID,
        username=user.username,
        password=user.password,
        firstname=user.firstname,
        lastname=user.lastname,
        phone=user.phone,
        dateofbirth=datetime.datetime.strptime(
            (user.dateofbirth), "%Y-%m-%d").date(),
        address=user.address,
        photo=user.photo,
        email=user.email,
        gender=user.gender,
        isteacher=user.isteacher,
        isparent=user.isparent,
        isadmin=user.isadmin,
        datecreated=gDate,
        status="1"
    )
    exists = await check_if_user_exists(user.phone)
    if exists:
        raise HTTPException(
            status_code=409, detail="User already exists with this phone/email.")
    else:
        await database.execute(query)
        await register_wallet(gID)
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
async def archive_user(user: UserUpdateSchema):
    gDate = datetime.datetime.now()
    query = users_table.update().\
        where(users_table.c.id == user.id).\
        values(
            firstname=user.firstname,
            lastname=user.lastname,
            gender=user.gender,
            password=user.password,
            roleid=user.roleid,
            email=user.email,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_user_by_id(user.id)


@app.put("/users/restore", response_model=UserUpdateSchema, tags=["user"])
async def restore_user(user: UserUpdateSchema):
    gDate = datetime.datetime.now()
    query = users_table.update().\
        where(users_table.c.id == user.id).\
        values(
            firstname=user.firstname,
            lastname=user.lastname,
            gender=user.gender,
            password=user.password,
            roleid=user.roleid,
            email=user.email,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_user_by_id(user.id)


@app.delete("/users/{userid}", tags=["user"])
async def delete_user(userid: str):
    query = users_table.delete().where(users_table.c.id == userid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This user has been deleted!"
    }


################### END USERS ###################

###################### SCHOOL ######################

@app.get("/schools", response_model=List[SchoolSchema], tags=["school"])
async def get_all_schools():
    query = schools_table.select()
    return await database.fetch_all(query)


@app.get("/schools/{schoolid}", response_model=SchoolSchema, tags=["school"])
async def get_school_by_id(schoolid: str):
    query = schools_table.select().where(schools_table.c.id == schoolid)
    result = await database.fetch_one(query)
    return result


@app.get("/schools/name/{schoolid}", tags=["school"])
async def get_schoolname_by_id(schoolid: str):
    query = schools_table.select().where(schools_table.c.id == schoolid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["schoolname"]
        return fullname
    else:
        return "Unkown School"


@app.post("/schools/register", response_model=RoleSchema, tags=["school"])
async def register_school(role: RoleSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = schools_table.insert().values(
        id=gID,
        rolename=role.rolename,
        description=role.description,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **role.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/schools/update", response_model=SchoolUpdateSchema, tags=["school"])
async def update_school(school: SchoolUpdateSchema):
    gDate = datetime.datetime.now()
    query = schools_table.update().\
        where(schools_table.c.id == school.id).\
        values(
            schoolname=school.schoolname,
            slogan=school.slogan,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_school_by_id(school.id)


@app.put("/schools/archive", response_model=SchoolUpdateSchema, tags=["school"])
async def archive_school(school: SchoolUpdateSchema):
    gDate = datetime.datetime.now()
    query = schools_table.update().\
        where(schools_table.c.id == school.id).\
        values(
            schoolname=school.schoolname,
            slogan=school.slogan,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_school_by_id(school.id)


@app.put("/schools/restore", response_model=SchoolUpdateSchema, tags=["school"])
async def restore_school(school: SchoolUpdateSchema):
    gDate = datetime.datetime.now()
    query = schools_table.update().\
        where(schools_table.c.id == school.id).\
        values(
            schoolname=school.schoolname,
            slogan=school.slogan,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_school_by_id(school.id)


@app.delete("/schools/{schoolid}", tags=["school"])
async def delete_school(schoolid: str):
    query = schools_table.delete().where(schools_table.c.id == schoolid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This school has been deleted!"
    }

###################### END SCHOOL ##################

###################### ROLES ######################


@app.get("/roles", response_model=List[RoleSchema], tags=["role"])
async def get_all_roles():
    query = roles_table.select()
    return await database.fetch_all(query)


@app.get("/roles/{roleid}", response_model=RoleSchema, tags=["role"])
async def get_role_by_id(roleid: str):
    query = roles_table.select().where(roles_table.c.id == roleid)
    result = await database.fetch_one(query)
    return result


@app.get("/roles/name/{roleid}", tags=["role"])
async def get_rolename_by_id(roleid: str):
    query = roles_table.select().where(roles_table.c.id == roleid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["rolename"]
        return fullname
    else:
        return "Unkown Role"


@app.post("/roles/register", response_model=RoleSchema, tags=["role"])
async def register_role(role: RoleSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = roles_table.insert().values(
        id=gID,
        rolename=role.rolename,
        description=role.description,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **role.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/roles/update", response_model=RoleUpdateSchema, tags=["role"])
async def update_role(role: RoleUpdateSchema):
    gDate = datetime.datetime.now()
    query = roles_table.update().\
        where(roles_table.c.id == role.id).\
        values(
            rolename=role.rolename,
            description=role.description,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_role_by_id(role.id)


@app.put("/roles/archive", response_model=RoleUpdateSchema, tags=["role"])
async def archive_role(role: RoleUpdateSchema):
    gDate = datetime.datetime.now()
    query = roles_table.update().\
        where(roles_table.c.id == role.id).\
        values(
            rolename=role.rolename,
            description=role.description,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_role_by_id(role.id)


@app.put("/roles/restore", response_model=RoleUpdateSchema, tags=["role"])
async def restore_role(role: RoleUpdateSchema):
    gDate = datetime.datetime.now()
    query = roles_table.update().\
        where(roles_table.c.id == role.id).\
        values(
            rolename=role.rolename,
            description=role.description,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_role_by_id(role.id)


@app.delete("/roles/{roleid}", tags=["role"])
async def delete_role(roleid: str):
    query = roles_table.delete().where(roles_table.c.id == roleid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This role has been deleted!"
    }

###################### END ROLES ##################

###################### SUBJECTS ######################


@app.get("/subjects", response_model=List[SubjectSchema], tags=["subject"])
async def get_all_subjects():
    query = subjects_table.select()
    return await database.fetch_all(query)


@app.get("/subjects/{subjectid}", response_model=SubjectSchema, tags=["subject"])
async def get_subject_by_id(subjectid: str):
    query = subjects_table.select().where(subjects_table.c.id == subjectid)
    result = await database.fetch_one(query)
    return result


@app.get("/subjects/name/{subjectid}", tags=["subject"])
async def get_subjectname_by_id(subjectid: str):
    query = subjects_table.select().where(subjects_table.c.id == subjectid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["subjectname"]
        return fullname
    else:
        return "Unkown Subject"


@app.post("/subjects/register", response_model=SubjectSchema, tags=["subject"])
async def register_subject(subject: SubjectSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = subjects_table.insert().values(
        id=gID,
        subjectname=subject.subjectname,
        shortcode=subject.shortcode,
        requireskit=subject.requireskit,
        kitdescription=subject.kitdescription,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **subject.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/subjects/update", response_model=SubjectSchema, tags=["subject"])
async def update_subject(subject: SubjectSchema):
    gDate = datetime.datetime.now()
    query = subjects_table.update().\
        where(subjects_table.c.id == subject.id).\
        values(
            subjectname=subject.subjectname,
            shortcode=subject.shortcode,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_subject_by_id(subject.id)


@app.put("/subjects/archive", response_model=SubjectSchema, tags=["subject"])
async def archive_subject(subject: SubjectSchema):
    gDate = datetime.datetime.now()
    query = subjects_table.update().\
        where(subjects_table.c.id == subject.id).\
        values(
            subjectname=subject.subjectname,
            shortcode=subject.shortcode,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_subject_by_id(subject.id)


@app.put("/subjects/restore", response_model=SubjectSchema, tags=["subject"])
async def restore_subject(subject: SubjectSchema):
    gDate = datetime.datetime.now()
    query = subjects_table.update().\
        where(subjects_table.c.id == subject.id).\
        values(
            subjectname=subject.subjectname,
            shortcode=subject.shortcode,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_subject_by_id(subject.id)


@app.delete("/subjects/{subjectid}", tags=["subject"])
async def delete_subject(subjectid: str):
    query = subjects_table.delete().where(subjects_table.c.id == subjectid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This subject has been deleted!"
    }

###################### END SUBJECTS ##################

###################### CLASS LEVELS ######################


@app.get("/classlevels", tags=["classlevels"])
async def get_all_class_levels():
    query = classlevels_table.select()
    results = await database.fetch_all(query)
    if results:        
        return results
    else:
        raise HTTPException(status_code=204, detail="No class levels found")


@app.get("/classlevels/{classlevelid}", response_model=ClassLevelSchema, tags=["classlevels"])
async def get_class_level_by_id(classid: str):
    query = classlevels_table.select().where(classlevels_table.c.id == classid)
    result = await database.fetch_one(query)
    if result:        
        return result
    else:
        raise HTTPException(status_code=204, detail="No class level found")


@app.get("/classlevels/name/{classlevelid}", tags=["classlevels"])
async def get_classlevelname_by_id(classlevelid: str):
    query = classlevels_table.select().where(classlevels_table.c.id == classlevelid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["levelname"]
        return fullname
    else:
        return "Unknown Class"

@app.get("/classlevels/fees/{classlevelid}", tags=["classlevels"])
async def get_classlevelfees_by_id(classlevelid: str):
    query = classlevels_table.select().where(classlevels_table.c.id == classlevelid)
    result = await database.fetch_one(query)
    if result:
        fees = result["fees"]
        return fees
    else:
        return 0


@app.post("/classlevels/register", response_model=ClassLevelSchema, tags=["classlevels"])
async def register_class_level(classlevelobj: ClassLevelSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = classlevels_table.insert().values(
        id=gID,
        levelname=classlevelobj.levelname,
        shortcode=classlevelobj.shortcode,
        fees=classlevelobj.fees,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **classlevelobj.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/classlevels/update", response_model=ClassLevelUpdateSchema, tags=["classlevels"])
async def update_class_level(classlevel: ClassLevelUpdateSchema):
    gDate = datetime.datetime.now()
    query = classlevels_table.update().\
        where(classlevels_table.c.id == classlevel.id).\
        values(
            levelname=classlevel.levelname,
            shortcode=classlevel.shortcode,
            fees = classlevel.fees,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_class_level_by_id(classlevel.id)


@app.put("/classlevels/archive", response_model=ClassLevelUpdateSchema, tags=["classlevels"])
async def archive_class_level(classlevel: ClassLevelUpdateSchema):
    gDate = datetime.datetime.now()
    query = classlevels_table.update().\
        where(classlevels_table.c.id == classlevel.id).\
        values(
            levelname=classlevel.levelname,
            shortcode=classlevel.shortcode,
            fees = classlevel.fees,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_class_level_by_id(classlevel.id)


@app.put("/classlevels/restore", response_model=ClassLevelUpdateSchema, tags=["classlevels"])
async def restore_class_level(classlevel: ClassLevelUpdateSchema):
    gDate = datetime.datetime.now()
    query = classlevels_table.update().\
        where(classlevels_table.c.id == classlevel.id).\
        values(
            levelname=classlevel.levelname,
            shortcode=classlevel.shortcode,
            fees = classlevel.fees,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_class_level_by_id(classlevel.id)


@app.delete("/classlevels/{classlevelid}", tags=["classlevels"])
async def delete_class_level(classlevelid: str):
    query = classlevels_table.delete().where(classlevels_table.c.id == classlevelid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This class level has been deleted!"
    }

###################### END CLASS LEVELS ##################

###################### CLASSES ######################


@app.get("/classes", tags=["class"])
async def get_all_classes():
    query = classes_table.select()
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            teachername = await get_usernames_by_id(result.get("classteacherid"))
            classlevelname = await get_classlevelname_by_id(result.get("classlevelid"))
            classfees = await get_classlevelfees_by_id(result.get("classlevelid"))

            res.append({
                "id": result.get("id"),
                "classname": classlevelname +" "+ result.get("classname"),
                "classfees": classfees,
                # "shortcode": result.get("shortcode"),
                "classteacherid": result.get("classteacherid"),
                "classlevelid": result.get("classlevelid"),
                "classteachername": teachername,
                "datecreated": result.get("datecreated"),
                "createdby": result.get("createdby"),
                "dateupdated": result.get("dateupdated"),
                "updatedby": result.get("updatedby"),
                "status": result.get("status")
            })
        return res


@app.get("/classes/{classid}", response_model=ClassSchema, tags=["class"])
async def get_class_by_id(classid: str):
    query = classes_table.select().where(classes_table.c.id == classid)
    result = await database.fetch_one(query)
    return result


@app.get("/classes/name/{classid}", tags=["class"])
async def get_classname_by_id(classid: str):
    query = classes_table.select().where(classes_table.c.id == classid)
    result = await database.fetch_one(query)
    if result:
        classlevelname = await get_classlevelname_by_id(result.get("classlevelid"))
        fullname = classlevelname +" "+result["classname"]
        return fullname
    else:
        return "Unknown Class"

@app.get("/classes/schoolfees/{classid}", tags=["class"])
async def get_school_fees_by_classid(classid: str):
    query = classes_table.select().where(classes_table.c.id == classid)
    result = await database.fetch_one(query)
    if result:
        classlevelid = result.get("classlevelid")
        queryclasslevel = classlevels_table.select().where(classlevels_table.c.id == classlevelid)
        resultclasslevel = await database.fetch_one(queryclasslevel)
        if resultclasslevel:
            return resultclasslevel["fees"]
        else:
            return 0
    else:
        return 0


@app.post("/classes/register", response_model=ClassSchema, tags=["class"])
async def register_class(classobj: ClassSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = classes_table.insert().values(
        id=gID,
        classname=classobj.classname,
        classlevelid=classobj.classlevelid,
        classteacherid=classobj.classteacherid,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **classobj.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/classes/update", response_model=ClassUpdateSchema, tags=["class"])
async def update_class(classobj: ClassUpdateSchema):
    gDate = datetime.datetime.now()
    query = classes_table.update().\
        where(classes_table.c.id == classobj.id).\
        values(
            classname=classobj.classname,
            classlevelid=classobj.classlevelid,
            classteacherid=classobj.classteacherid,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_class_by_id(classobj.id)


@app.put("/classes/archive", response_model=ClassUpdateSchema, tags=["class"])
async def archive_class(classobj: ClassUpdateSchema):
    gDate = datetime.datetime.now()
    query = classes_table.update().\
        where(classes_table.c.id == classobj.id).\
        values(
            classname=classobj.classname,
            classlevelid=classobj.classlevelid,
            classteacherid=classobj.classteacherid,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_class_by_id(classobj.id)


@app.put("/classes/restore", response_model=ClassUpdateSchema, tags=["class"])
async def restore_class(classobj: ClassUpdateSchema):
    gDate = datetime.datetime.now()
    query = classes_table.update().\
        where(classes_table.c.id == classobj.id).\
        values(
            classname=classobj.classname,
            classlevelid=classobj.classlevelid,
            classteacherid=classobj.classteacherid,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_class_by_id(classobj.id)


@app.delete("/classes/{classid}", tags=["class"])
async def delete_class(classid: str):
    query = classes_table.delete().where(classes_table.c.id == classid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This class has been deleted!"
    }

###################### END CLASSES ##################

###################### TEACHER-SUBJECT-CLASS ASSIGMENTS ######################


@app.get("/teacherclasssubjects", response_model=List[TeacherClassSubjectSchema], tags=["teacherclasssubject"])
async def get_all_classes():
    query = classteachersubjects_table.select()
    results = await database.fetch_all(query)
    return results


@app.get("/teacherclasssubjects/{tcsid}", response_model=TeacherClassSubjectSchema, tags=["teacherclasssubject"])
async def get_teacherclasssubject_by_id(tcsid: str):
    query = classteachersubjects_table.select().where(
        classteachersubjects_table.c.id == tcsid)
    result = await database.fetch_one(query)
    return result


@app.post("/teacherclasssubjects/register", response_model=TeacherClassSubjectSchema, tags=["teacherclasssubject"])
async def register_teacherclasssubject(tcs: TeacherClassSubjectSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = classteachersubjects_table.insert().values(
        id=gID,
        subjectid=tcs.subjectid,
        classid=tcs.classid,
        userid=tcs.userid,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **tcs.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/teacherclasssubjects/update", response_model=TeacherClassSubjectUpdateSchema, tags=["teacherclasssubject"])
async def update_teacherclasssubject(tcs: TeacherClassSubjectUpdateSchema):
    gDate = datetime.datetime.now()
    query = classteachersubjects_table.update().\
        where(classteachersubjects_table.c.id == tcs.id).\
        values(
            classid=tcs.classid,
            subjectid=tcs.subjectid,
            userid=tcs.userid,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_teacherclasssubject_by_id(tcs.id)


@app.put("/teacherclasssubjects/archive", response_model=TeacherClassSubjectUpdateSchema, tags=["teacherclasssubject"])
async def archive_teacherclasssubject(tcs: TeacherClassSubjectUpdateSchema):
    gDate = datetime.datetime.now()
    query = classteachersubjects_table.update().\
        where(classteachersubjects_table.c.id == tcs.id).\
        values(
            classid=tcs.classid,
            subjectid=tcs.subjectid,
            userid=tcs.userid,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_teacherclasssubject_by_id(tcs.id)


@app.put("/teacherclasssubjects/restore", response_model=TeacherClassSubjectUpdateSchema, tags=["teacherclasssubject"])
async def restore_teacherclasssubject(tcs: TeacherClassSubjectUpdateSchema):
    gDate = datetime.datetime.now()
    query = classteachersubjects_table.update().\
        where(classteachersubjects_table.c.id == tcs.id).\
        values(
            classid=tcs.classid,
            subjectid=tcs.subjectid,
            userid=tcs.userid,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_teacherclasssubject_by_id(tcs.id)


@app.delete("/teacherclasssubjects/{tcsid}", tags=["teacherclasssubject"])
async def delete_teacherclasssubject(tcsid: str):
    query = classteachersubjects_table.delete().where(
        classteachersubjects_table.c.id == tcsid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This teacher-class-subject relation has been deleted!"
    }

###################### END TEACHER-SUBJECT-CLASS ASSIGMENTS ##################

###################### CLUBS ######################


@app.get("/clubs", response_model=List[ClubSchema], tags=["club"])
async def get_all_clubs():
    query = clubs_table.select()
    return await database.fetch_all(query)


@app.get("/clubs/{clubid}", response_model=ClubSchema, tags=["club"])
async def get_club_by_id(clubid: str):
    query = clubs_table.select().where(clubs_table.c.id == clubid)
    result = await database.fetch_one(query)
    return result


@app.get("/clubs/name/{clubid}", tags=["club"])
async def get_clubname_by_id(clubid: str):
    query = clubs_table.select().where(clubs_table.c.id == clubid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["clubname"]
        return fullname
    else:
        return "Unknown Club"


@app.post("/clubs/register", response_model=ClubSchema, tags=["club"])
async def register_club(club: ClubSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = clubs_table.insert().values(
        id=gID,
        clubname=club.clubname,
        shortcode=club.shortcode,
        description=club.description,
        patronid=club.patronid,
        asstpatronid=club.asstpatronid,
        fees=club.fees,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **club.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/clubs/update", response_model=ClubUpdateSchema, tags=["club"])
async def update_club(club: ClubUpdateSchema):
    gDate = datetime.datetime.now()
    query = clubs_table.update().\
        where(clubs_table.c.id == club.id).\
        values(
            clubname=club.clubname,
            shortcode=club.shortcode,
            description=club.description,
            patronid=club.patronid,
            asstpatronid=club.asstpatronid,
            fees=club.fees,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_club_by_id(club.id)


@app.put("/clubs/archive", response_model=ClubUpdateSchema, tags=["club"])
async def archive_club(club: ClubUpdateSchema):
    gDate = datetime.datetime.now()
    query = clubs_table.update().\
        where(clubs_table.c.id == club.id).\
        values(
            clubname=club.clubname,
            shortcode=club.shortcode,
            description=club.description,
            patronid=club.patronid,
            asstpatronid=club.asstpatronid,
            fees=club.fees,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_club_by_id(club.id)


@app.put("/clubs/restore", response_model=ClubUpdateSchema, tags=["club"])
async def restore_club(club: ClubUpdateSchema):
    gDate = datetime.datetime.now()
    query = clubs_table.update().\
        where(clubs_table.c.id == club.id).\
        values(
            clubname=club.clubname,
            shortcode=club.shortcode,
            description=club.description,
            patronid=club.patronid,
            asstpatronid=club.asstpatronid,
            fees=club.fees,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_club_by_id(club.id)


@app.delete("/clubs/{clubid}", tags=["club"])
async def delete_club(clubid: str):
    query = clubs_table.delete().where(clubs_table.c.id == clubid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This club has been deleted!"
    }

###################### END CLUBS ##################


###################### EVENTS ######################

@app.get("/events", response_model=List[EventSchema], tags=["events"])
async def get_all_events():
    query = events_table.select()
    return await database.fetch_all(query)


@app.get("/events/{eventid}", response_model=EventSchema, tags=["events"])
async def get_event_by_id(eventid: str):
    query = events_table.select().where(events_table.c.id == eventid)
    result = await database.fetch_one(query)
    return result


@app.get("/events/name/{eventid}", tags=["events"])
async def get_eventname_by_id(eventid: str):
    query = events_table.select().where(events_table.c.id == eventid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["name"]
        return fullname
    else:
        return "Unkown Event"


@app.post("/events/register", response_model=EventSchema, tags=["events"])
async def register_event(event: EventAddSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = events_table.insert().values(
        id=gID,
        name=event.name,
        description=event.description,
        start=datetime.datetime.strptime(
            (event.start), "%Y-%m-%dT%H:%M:%S").date(),
        end=datetime.datetime.strptime(
            (event.end), "%Y-%m-%dT%H:%M:%S").date(),
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **event.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/events/update", response_model=EventUpdateSchema, tags=["events"])
async def update_event(event: EventUpdateSchema):
    gDate = datetime.datetime.now()
    query = events_table.update().\
        where(events_table.c.id == event.id).\
        values(
            name=event.name,
        description=event.description,
        start=event.start,
        end=event.end,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_event_by_id(event.id)


@app.put("/events/archive", response_model=EventUpdateSchema, tags=["events"])
async def archive_event(event: EventUpdateSchema):
    gDate = datetime.datetime.now()
    query = events_table.update().\
        where(events_table.c.id == event.id).\
        values(
            name=event.name,
            description=event.description,
            start=event.start,
            end=event.end,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_event_by_id(event.id)


@app.put("/events/restore", response_model=EventUpdateSchema, tags=["events"])
async def restore_event(event: EventUpdateSchema):
    gDate = datetime.datetime.now()
    query = events_table.update().\
        where(events_table.c.id == event.id).\
        values(
            name=event.name,
            description=event.description,
            start=event.start,
            end=event.end,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_event_by_id(event.id)


@app.delete("/events/{eventid}", tags=["events"])
async def delete_events(eventid: str):
    query = events_table.delete().where(events_table.c.id == eventid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This event has been deleted!"
    }

###################### END ROLES ##################

###################### RESULT TYPES ######################


@app.get("/resulttypes", response_model=List[ResultTypeSchema], tags=["resulttypes"])
async def get_all_result_types():
    query = resulttypes_table.select()
    return await database.fetch_all(query)


@app.get("/resulttypes/{resulttypeid}", response_model=ResultTypeSchema, tags=["resulttypes"])
async def get_result_type_by_id(resulttypeid: str):
    query = resulttypes_table.select().where(
        resulttypes_table.c.id == resulttypeid)
    result = await database.fetch_one(query)
    return result


@app.get("/resulttypes/name/{resulttypeid}", tags=["resulttypes"])
async def get_result_type_name_by_id(resulttypeid: str):
    query = resulttypes_table.select().where(
        resulttypes_table.c.id == resulttypeid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["name"]
        return fullname
    else:
        return "Unkown Result Type"


@app.post("/resulttypes/register", response_model=ResultTypeSchema, tags=["resulttypes"])
async def register_result_type(resulttype: ResultTypeSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = resulttypes_table.insert().values(
        id=gID,
        name=resulttype.name,
        shortcode=resulttype.shortcode,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **resulttype.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/resulttypes/update", response_model=ResultTypeUpdateSchema, tags=["resulttypes"])
async def update_result_type(resulttype: ResultTypeUpdateSchema):
    gDate = datetime.datetime.now()
    query = resulttypes_table.update().\
        where(resulttypes_table.c.id == resulttype.id).\
        values(
            name=resulttype.name,
            shortcode=resulttype.shortcode,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_result_type_by_id(resulttype.id)


@app.put("/resulttypes/archive", response_model=ResultTypeUpdateSchema, tags=["resulttypes"])
async def archive_result_type(resulttype: ResultTypeUpdateSchema):
    gDate = datetime.datetime.now()
    query = resulttypes_table.update().\
        where(resulttypes_table.c.id == resulttype.id).\
        values(
            name=resulttype.name,
            shortcode=resulttype.shortcode,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_result_type_by_id(resulttype.id)


@app.put("/resulttypes/restore", response_model=ResultTypeUpdateSchema, tags=["resulttypes"])
async def restore_result_type(resulttype: ResultTypeUpdateSchema):
    gDate = datetime.datetime.now()
    query = resulttypes_table.update().\
        where(resulttypes_table.c.id == resulttype.id).\
        values(
            name=resulttype.name,
            shortcode=resulttype.shortcode,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_result_type_by_id(resulttype.id)


@app.delete("/resulttypes/{eventid}", tags=["resulttypes"])
async def delete_result_types(eventid: str):
    query = resulttypes_table.delete().where(resulttypes_table.c.id == eventid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This result type has been deleted!"
    }

###################### END RESULT_TYPES ##################

###################### GRADES ######################


@app.get("/grades", response_model=List[GradeSchema], tags=["grades"])
async def get_all_grades():
    query = grades_table.select()
    return await database.fetch_all(query)


@app.get("/grades/{resulttypeid}", response_model=GradeSchema, tags=["grades"])
async def get_grade_by_id(resulttypeid: str):
    query = grades_table.select().where(grades_table.c.id == resulttypeid)
    result = await database.fetch_one(query)
    return result


@app.get("/grades/name/{resulttypeid}", tags=["grades"])
async def get_grade_name_by_id(resulttypeid: str):
    query = grades_table.select().where(grades_table.c.id == resulttypeid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["gradename"]
        return fullname
    else:
        return "Unkown Grade"


@app.post("/grades/register", response_model=GradeSchema, tags=["grades"])
async def register_grade(resulttype: GradeSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = grades_table.insert().values(
        id=gID,
        name=resulttype.gradename,
        shortcode=resulttype.shortcode,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **resulttype.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/grades/update", response_model=GradeUpdateSchema, tags=["grades"])
async def update_grade(resulttype: GradeUpdateSchema):
    gDate = datetime.datetime.now()
    query = grades_table.update().\
        where(grades_table.c.id == resulttype.id).\
        values(
            name=resulttype.gradename,
            shortcode=resulttype.shortcode,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_grade_by_id(resulttype.id)


@app.put("/grades/archive", response_model=GradeUpdateSchema, tags=["grades"])
async def archive_grade(resulttype: GradeUpdateSchema):
    gDate = datetime.datetime.now()
    query = grades_table.update().\
        where(grades_table.c.id == resulttype.id).\
        values(
            name=resulttype.gradename,
            shortcode=resulttype.shortcode,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_grade_by_id(resulttype.id)


@app.put("/grades/restore", response_model=GradeUpdateSchema, tags=["grades"])
async def restore_grade(grade: GradeUpdateSchema):
    gDate = datetime.datetime.now()
    query = grades_table.update().\
        where(grades_table.c.id == grade.id).\
        values(
            name=grade.gradename,
            shortcode=grade.shortcode,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_grade_by_id(grade.id)


@app.delete("/grades/{gradeid}", tags=["grades"])
async def delete_grade(gradeid: str):
    query = grades_table.delete().where(grades_table.c.id == gradeid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This grade has been deleted!"
    }

###################### END GRADES ##################

###################### RESULTS ######################


@app.get("/results", response_model=List[ResultSchema], tags=["results"])
async def get_all_results():
    query = results_table.select()
    return await database.fetch_all(query)


@app.get("/results/{resultid}", response_model=ResultSchema, tags=["results"])
async def get_result_by_id(resultid: str):
    query = results_table.select().where(results_table.c.id == resultid)
    result = await database.fetch_one(query)
    return result


@app.get("/results/student/{studentid}", tags=["results"])
async def get_result_by_studentid(studentid: str):
    query = results_table.select().where(results_table.c.studentid == studentid)
    results = await database.fetch_all(query)
    if results:
        result_sets = []
        for resulttit in results:
            result_title = resulttit["resulttitle"]
            if result_title not in result_sets:
                result_sets.append(result_title)
        
        res = []
        for result_set in result_sets:
            marks = {}
            for result in results:            
                subjectname = await get_subjectname_by_id(result["subjectid"])                
                if not subjectname in marks and result["resulttitle"] == result_set:
                    marks.update( {subjectname : result["mark"]} )
            res.append({
                "result_title": result_set,
                "details": marks
            })
        return res

    else:
        raise HTTPException(status_code=404, detail="No student results found")

# {
            #         "subjectname": await get_subjectname_by_id(result["subjectid"]),
            #         "classname": await get_classname_by_id(result["classid"]),
            #         "teachername": await get_usernames_by_id(result["teacherid"]),
            #         "resulttype": await get_result_type_name_by_id(result["resultypeid"]),
            #         "mark": result["mark"],
            #         "dateadded": result["datecreated"]
            #     }


@app.get("/results/name/{resultid}", tags=["results"])
async def get_result_name_by_id(resultid: str):
    query = results_table.select().where(results_table.c.id == resultid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["gradename"]
        return fullname
    else:
        return "Unkown Grade"


@app.post("/results/register", response_model=ResultSchema, tags=["results"])
async def register_result(result: ResultSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = results_table.insert().values(
        id=gID,
        resulttitle = result.resulttitle,
        resultperiod = result.resultperiod,
        subjectid=result.subjectid,
        classid=result.classid,
        gradeid=result.gradeid,
        teacherid=result.teacherid,
        studentid=result.studentid,
        resultypeid=result.resultypeid,
        mark=result.mark,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **result.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/results/update", response_model=ResultUpdateSchema, tags=["results"])
async def update_result(result: ResultUpdateSchema):
    gDate = datetime.datetime.now()
    query = results_table.update().\
        where(results_table.c.id == result.id).\
        values(
            subjectid=result.subjectid,
            classid=result.classid,
            gradeid=result.gradeid,
            teacherid=result.teacherid,
            studentid=result.studentid,
            resultypeid=result.resultypeid,
            mark=result.mark,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_result_by_id(result.id)


@app.put("/results/archive", response_model=ResultUpdateSchema, tags=["results"])
async def archive_result(result: ResultUpdateSchema):
    gDate = datetime.datetime.now()
    query = results_table.update().\
        where(results_table.c.id == result.id).\
        values(
            subjectid=result.subjectid,
            classid=result.classid,
            gradeid=result.gradeid,
            teacherid=result.teacherid,
            studentid=result.studentid,
            resultypeid=result.resultypeid,
            mark=result.mark,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_result_by_id(result.id)


@app.put("/results/restore", response_model=ResultUpdateSchema, tags=["results"])
async def restore_result(result: ResultUpdateSchema):
    gDate = datetime.datetime.now()
    query = results_table.update().\
        where(results_table.c.id == result.id).\
        values(
            subjectid=result.subjectid,
            classid=result.classid,
            gradeid=result.gradeid,
            teacherid=result.teacherid,
            studentid=result.studentid,
            resultypeid=result.resultypeid,
            mark=result.mark,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_result_by_id(result.id)


@app.delete("/results/{gradeid}", tags=["results"])
async def delete_result(resultid: str):
    query = results_table.delete().where(results_table.c.id == resultid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This result has been deleted!"
    }

###################### END RESULTS ##################


###################### FEES PAYMENTS ######################


@app.get("/feespayments", response_model=List[FeesPaymentSchema], tags=["payments"])
async def get_all_fees_payments():
    query = feespayments_table.select()
    return await database.fetch_all(query)


@app.get("/feespayments/{feespaymentid}", response_model=FeesPaymentSchema, tags=["payments"])
async def get_fees_payment_by_id(feespaymentid: str):
    query = feespayments_table.select().where(feespayments_table.c.id == feespaymentid)
    result = await database.fetch_one(query)
    return result


@app.get("/feespayments/ref/{feespaymentid}", tags=["payments"])
async def get_feespaymentref_by_id(feespaymentid: str):
    query = feespayments_table.select().where(feespayments_table.c.id == feespaymentid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["paymentref"]
        return fullname
    else:
        return "Unknown Payment"

@app.get("/feespayments/classlevel/{classlevelid}", tags=["payments"])
async def get_student_payments_at_class_level(classlevelid: str):
    
    fees_paid = 0
    query = classes_table.select().where(classes_table.c.classlevelid == classlevelid)
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            queryclass = feespayments_table.select().where(feespayments_table.c.classid == result["id"])
            resultsclass = await database.fetch_all(queryclass)
            if resultsclass:
                for resultclass in resultsclass:
                    fees_paid += resultclass["transamount"]
                return fees_paid

@app.get("/paymentclasslevels", tags=["payments"])
async def get_all_payment_class_levels():
    query = classlevels_table.select()
    results = await database.fetch_all(query)
    res = [] 
    if results:        
        for result in results:
            studentcount = await get_students_at_class_level(result["id"])
            fees_expected = result["fees"] * studentcount
            fees_paid = await get_student_payments_at_class_level(result["id"])
            res.append({
                "classlevelid": result["id"],
                "classlevelname": result["levelname"],
                "fees": result["fees"],
                "studentcount": studentcount,
                "totalfeesexpected": fees_expected,
                "totalfeescollected": fees_paid,
            })
        return res
    else:
        raise HTTPException(status_code=204, detail="No class levels found")

@app.post("/feespayments/register", response_model=FeesPaymentSchema, tags=["payments"])
async def register_fees_payment(feespayment: FeesPaymentSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = feespayments_table.insert().values(
        id=gID,
        paymentref=feespayment.paymentref,
        academicperiodid=feespayment.academicperiodid,
        studentid=feespayment.studentid,
        classid=feespayment.classid,
        transamount=feespayment.transamount,
        feesamount=feespayment.feesamount,
        amountpaid=feespayment.amountpaid,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **feespayment.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/feespayments/update", response_model=FeesPaymentUpdateSchema, tags=["payments"])
async def update_fees_payment(feespayment: FeesPaymentUpdateSchema):
    gDate = datetime.datetime.now()
    query = feespayments_table.update().\
        where(feespayments_table.c.id == feespayment.id).\
        values(
            paymentref=feespayment.paymentref,
            academicperiodid=feespayment.academicperiodid,
            studentid=feespayment.studentid,
            classid=feespayment.classid,
            transamount=feespayment.transamount,
            feesamount=feespayment.feesamount,
            amountpaid=feespayment.amountpaid,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_fees_payment_by_id(feespayment.id)


@app.put("/feespayments/archive", response_model=FeesPaymentUpdateSchema, tags=["payments"])
async def archive_fees_payment(feespayment: FeesPaymentUpdateSchema):
    gDate = datetime.datetime.now()
    query = feespayments_table.update().\
        where(feespayments_table.c.id == feespayment.id).\
        values(
            paymentref=feespayment.paymentref,
            academicperiodid=feespayment.academicperiodid,
            studentid=feespayment.studentid,
            classid=feespayment.classid,
            transamount=feespayment.transamount,
            feesamount=feespayment.feesamount,
            amountpaid=feespayment.amountpaid,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_fees_payment_by_id(feespayment.id)


@app.put("/feespayments/restore", response_model=FeesPaymentUpdateSchema, tags=["payments"])
async def restore_fees_payment(feespayment: FeesPaymentUpdateSchema):
    gDate = datetime.datetime.now()
    query = feespayments_table.update().\
        where(feespayments_table.c.id == feespayment.id).\
        values(
            paymentref=feespayment.paymentref,
            academicperiodid=feespayment.academicperiodid,
            studentid=feespayment.studentid,
            classid=feespayment.classid,
            transamount=feespayment.transamount,
            feesamount=feespayment.feesamount,
            amountpaid=feespayment.amountpaid,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_fees_payment_by_id(feespayment.id)


@app.delete("/feespayments/{feespaymentid}", tags=["payments"])
async def delete_fees_payment(feespaymentid: str):
    query = feespayments_table.delete().where(feespayments_table.c.id == feespaymentid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This fees payment has been deleted!"
    }

###################### END FEES PAYMENTS ##################

###################### CLUB PAYMENTS ######################


@app.get("/clubpayments", response_model=List[ClubsPaymentSchema], tags=["payments"])
async def get_all_club_payments():
    query = clubpayments_table.select()
    return await database.fetch_all(query)


@app.get("/clubpayments/{clubpaymentid}", response_model=ClubsPaymentSchema, tags=["payments"])
async def get_club_payment_by_id(clubpaymentid: str):
    query = clubpayments_table.select().where(clubpayments_table.c.id == clubpaymentid)
    result = await database.fetch_one(query)
    return result


@app.get("/clubpayments/ref/{clubpaymentid}", tags=["payments"])
async def get_clubpaymentref_by_id(clubpaymentid: str):
    query = clubpayments_table.select().where(clubpayments_table.c.id == clubpaymentid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["paymentref"]
        return fullname
    else:
        return "Unknown Club Payment"


@app.post("/clubpayments/register", response_model=ClubsPaymentSchema, tags=["payments"])
async def register_club_payment(clubpayment: ClubsPaymentSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = clubpayments_table.insert().values(
        id=gID,
        paymentref=clubpayment.paymentref,
        academicperiodid=clubpayment.academicperiodid,
        studentid=clubpayment.studentid,
        classid=clubpayment.classid,
        clubid=clubpayment.clubid,
        transamount=clubpayment.transamount,
        feesamount=clubpayment.feesamount,
        amountpaid=clubpayment.amountpaid,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **clubpayment.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/clubpayments/update", response_model=ClubsPaymentUpdateSchema, tags=["payments"])
async def update_club_payment(clubpayment: ClubsPaymentUpdateSchema):
    gDate = datetime.datetime.now()
    query = clubpayments_table.update().\
        where(clubpayments_table.c.id == clubpayment.id).\
        values(
            paymentref=clubpayment.paymentref,
            academicperiodid=clubpayment.academicperiodid,
            studentid=clubpayment.studentid,
            classid=clubpayment.classid,
            clubid=clubpayment.clubid,
            transamount=clubpayment.transamount,
            feesamount=clubpayment.feesamount,
            amountpaid=clubpayment.amountpaid,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_club_payment_by_id(clubpayment.id)


@app.put("/clubpayments/archive", response_model=ClubsPaymentUpdateSchema, tags=["payments"])
async def archive_club_payment(clubpayment: ClubsPaymentUpdateSchema):
    gDate = datetime.datetime.now()
    query = clubpayments_table.update().\
        where(clubpayments_table.c.id == clubpayment.id).\
        values(
            paymentref=clubpayment.paymentref,
            academicperiodid=clubpayment.academicperiodid,
            studentid=clubpayment.studentid,
            classid=clubpayment.classid,
            clubid=clubpayment.clubid,
            transamount=clubpayment.transamount,
            feesamount=clubpayment.feesamount,
            amountpaid=clubpayment.amountpaid,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_club_payment_by_id(clubpayment.id)


@app.put("/clubpayments/restore", response_model=ClubsPaymentUpdateSchema, tags=["payments"])
async def restore_club_payment(clubpayment: ClubsPaymentUpdateSchema):
    gDate = datetime.datetime.now()
    query = clubpayments_table.update().\
        where(clubpayments_table.c.id == clubpayment.id).\
        values(
            paymentref=clubpayment.paymentref,
            academicperiodid=clubpayment.academicperiodid,
            studentid=clubpayment.studentid,
            classid=clubpayment.classid,
            clubid=clubpayment.clubid,
            transamount=clubpayment.transamount,
            feesamount=clubpayment.feesamount,
            amountpaid=clubpayment.amountpaid,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_club_payment_by_id(clubpayment.id)


@app.delete("/clubpayments/{clubpaymentid}", tags=["payments"])
async def delete_club_payment(clubpaymentid: str):
    query = clubpayments_table.delete().where(clubpayments_table.c.id == clubpaymentid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This club payment has been deleted!"
    }

###################### END CLUB PAYMENTS ##################


################### STUDENTS ###################

@app.get("/students/", tags=["students"])
async def get_all_students():
    query = students_table.select()
    results = await database.fetch_all(query)
    if results:
        return results
    else:
        raise HTTPException(status_code=404, detail="No students found")


@app.get("/students/{studentid}", response_model=StudentSchema, tags=["students"])
async def get_student_by_id(studentid: str):
    query = students_table.select().where(students_table.c.id == studentid)
    result = await database.fetch_one(query)
    if result:
        return result
    else:
        raise HTTPException(status_code=404, detail="Student not found")


@app.get("/students/name/{studentid}", tags=["students"])
async def get_studentname_by_id(studentid: str):
    query = students_table.select().where(students_table.c.id == studentid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["firstname"] + " " + result["lastname"]
        return fullname
    else:
        return "Unknown Student"


@app.get("/students/checkexistence/{studentno}", tags=["students"])
async def check_if_student_exists(studentno: str):
    query = students_table.select().where(students_table.c.studentid == studentno)
    result = await database.fetch_one(query)
    print(result)
    if result:
        return True
    else:
        return False

@app.get("/students/classlevel/{classlevelid}", tags=["students"])
async def get_students_at_class_level(classlevelid: str):
    studentCount = 0
    query = classes_table.select().where(classes_table.c.classlevelid == classlevelid)
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            queryclass = students_table.select().where(students_table.c.classid == result["id"])
            resultsclass = await database.fetch_all(queryclass)
            if resultsclass:
                for resultclass in resultsclass:
                    studentCount += 1
    return studentCount

@app.get("/students/feesstatus/{studentid}/{academicperiodid}", tags=["students"])
async def get_student_fees_status(studentid: str, academicperiodid: str):
    query = feespayments_table.select().where(feespayments_table.c.studentid == studentid).where(feespayments_table.c.academicperiodid == academicperiodid).order_by(desc(feespayments_table.c.datecreated))
    result = await database.fetch_one(query)
    if result:
        status = "partially paid"
        if ( result["amountpaid"] >= result["feesamount"]):
            status = "fully paid"
        
        res = {
            "lastpayment": result["transamount"],
            "feesamount": result["feesamount"],
            "amountpaid": result["amountpaid"], 
            "feesstatus": status           
        }
        return res
    else:
        return{
            "lastpayment": 0,
            "feesamount": 0,
            "amountpaid": 0, 
            "feesstatus": "not paid"
        }
        # raise HTTPException(status_code=204, detail="Student not found")


@app.get("/students/parent/{parentid}", tags=["students"])
async def get_parent_students(parentid: str):
    academicperiodid =""
    periodquery = academicperiods_table.select().where(academicperiods_table.c.startdate < datetime.datetime.now()).where(academicperiods_table.c.enddate > datetime.datetime.now())
    periodresults = await database.fetch_one(periodquery)
    if periodresults:
        print("It is "+ periodresults["periodname"])
        academicperiodid = periodresults["id"]

    query = students_table.select().where(students_table.c.parentone == parentid)
    results = await database.fetch_all(query)
    if results:
        # return results
        res = []
        for result in results:            
            classlevelname = await get_classlevelname_by_id(result.get("classlevelid"))
            classname = await get_classname_by_id(result.get("classid"))
            payment_dict = await get_student_fees_status(result.get("id"), academicperiodid)
            fees_amount = 0
            if(payment_dict["feesamount"] == 0):
                fees_amount = await get_school_fees_by_classid(result.get("classid"))
            else:
                fees_amount = payment_dict["feesamount"]

            res.append({
                "id": result.get("id"),
                "firstname": result.get("firstname"),
                "lastname": result.get("lastname"),
                "othernames": result.get("othernames"),
                "photo": result.get("photo"),
                "phone": result.get("phone"),
                "email": result.get("email"),
                "gender": result.get("gender"),
                "houseid": result.get("houseid"),
                "parentone": result.get("parentone"),
                "parenttwo": result.get("parenttwo"),
                "parentthree": result.get("parentthree"),
                "dateofbirth": result.get("dateofbirth"),
                "address": result.get("address"),
                "weight": result.get("weight"),
                "height": result.get("height"),
                "studentid": result.get("studentid"),
                "classid": result.get("classid"),
                "classname": classname,
                "lastpayment": payment_dict["lastpayment"],
                "feesamount": fees_amount,
                "amountpaid": payment_dict["amountpaid"],
                "feesstatus": payment_dict["feesstatus"],
                "datecreated": result.get("datecreated"),
                "createdby": result.get("createdby"),
                "dateupdated": result.get("dateupdated"),
                "updatedby": result.get("updatedby"),
                "status": "1"}
                # .update(payment_dict)
                )
                

        return res

    else:
        raise HTTPException(status_code=404, detail="No students found")


@app.post("/students/signup", response_model=StudentSignUpSchema, tags=["students"])
async def register_student(student: StudentSignUpSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = students_table.insert().values(
        id=gID,
        firstname=student.firstname,
        lastname=student.lastname,
        othernames=student.othernames,
        dateofbirth=datetime.datetime.strptime(
            (student.dateofbirth), "%Y-%m-%d").date(),
        classid=student.classid,
        studentid=student.studentid,
        photo=student.photo,
        phone=student.phone,
        email=student.email,
        parentone=student.parentone,
        parenttwo=student.parenttwo,
        parentthree=student.parentthree,
        gender=student.gender,
        address=student.address,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **student.dict(),
        "id": gID,
        "datecreated": gDate,
    }


@app.put("/students/update", response_model=StudentSchema, tags=["students"])
async def update_student(student: StudentSchema):

    gDate = datetime.datetime.now()
    query = students_table.update().\
        where(students_table.c.id == student.id).\
        values(
            firstname=student.firstname,
            lastname=student.lastname,
            othernames=student.othernames,
            dateofbirth=student.dateofbirth,
            classid=student.classid,
            studentid=student.studentid,
            photo=student.photo,
            phone=student.phone,
            email=student.email,
            parentone=student.parentone,
            parenttwo=student.parenttwo,
            parentthree=student.parentthree,
            gender=student.gender,
            address=student.address,
            status=student.status,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_student_by_id(student.id)

################### END STUDENTS ###################

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
        datecreated=gDate,
        status="1"
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


################### POSTS ###################

@app.get("/posts", tags=["posts"])
async def get_all_posts():
    query = posts_table.select()
    results = await database.fetch_all(query)
    if results:
        res = []
        for result in results:
            res.append({
                "id": result["id"],
                "content": result["content"],
                "likes": await get_post_likes_count_by_id(result["id"]),
                "dislikes": await get_post_dislikes_count_by_id(result["id"]),
                "commentscount": await get_post_comments_count_by_id(result["id"]),
                "datecreated": result["datecreated"],
                "createdby": await get_usernames_by_id(result["createdby"]),
                "dateupdated": result["dateupdated"],
                "updatedby": result["updatedby"],
                "status": result["status"],
            })
        return res
    else:
        raise HTTPException(status_code=404, detail='There are no posts')

@app.get("/posts/likedetails/{userid}", tags=["posts"])
async def get_posts_with_like_details(userid: str):
    query = posts_table.select()
    results = await database.fetch_all(query)
    if results:
        res = []
        for result in results:
            res.append({
                "id": result["id"],
                "content": result["content"],
                "likes": await get_post_likes_count_by_id(result["id"]),
                "dislikes": await get_post_dislikes_count_by_id(result["id"]),
                "commentscount": await get_post_comments_count_by_id(result["id"]),
                "datecreated": result["datecreated"],
                "diduserlike": await check_if_user_liked_post(result["id"], userid),
                "createdby": await get_usernames_by_id(result["createdby"]),
                "dateupdated": result["dateupdated"],
                "updatedby": result["updatedby"],
                "status": result["status"],
            })
        return res
    else:
        raise HTTPException(status_code=404, detail='There are no posts')


@app.get("/posts/{postid}", response_model=PostSchema, tags=["posts"])
async def get_post_by_id(postid: str):
    query = posts_table.select().where(posts_table.c.id == postid)
    result = await database.fetch_one(query)
    return result


@app.get("/posts/user/{userid}", tags=["posts"])
async def get_posts_by_userid(userid: str):
    query = posts_table.select().where(posts_table.c.createdby == userid)
    results = await database.fetch_all(query)
    if results:
        res = []
        for result in results:
            res.append({
                "id": result["id"],
                "title": result["title"],
                "content": result["content"],
                "image": result["image"],
                "file1": result["file1"],
                "file2": result["file2"],
                "file3": result["file3"],
                "file4": result["file4"],
                "file5": result["file5"],
                "likes": result["likes"],
                "dislikes": result["dislikes"],
                "datecreated": result["datecreated"],
                "createdby": await get_usernames_by_id(result["createdby"]),
                "dateupdated": result["dateupdated"],
                "updatedby": result["updatedby"],
                "status": result["status"],
            })
        return res

    else:
        return{
            "error": "User has no posts"
        }


@app.get("/posts/details/{postid}", tags=["posts"])
async def get_post_details_by_id(postid: str):
    query = posts_table.select().where(posts_table.c.id == postid)
    result = await database.fetch_one(query)
    if result:
        return{
            "id": result["id"],
            "title": result["title"],
            "content": result["content"],
            "image": result["image"],
            "file1": result["file1"],
            "file2": result["file2"],
            "file3": result["file3"],
            "file4": result["file4"],
            "file5": result["file5"],
            "likes": result["likes"],
            "dislikes": result["dislikes"],
            "datecreated": result["datecreated"],
            "createdby": await get_usernames_by_id(result["createdby"]),
            "dateupdated": result["dateupdated"],
            "updatedby": result["updatedby"],
            "status": result["status"],
        }
    else:
        return {
            "Error": "This post does not exist!"
        }


@app.post("/posts", response_model=PostSchema, tags=["posts"])
async def add_post(post: PostSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = posts_table.insert().values(
        id=gID,
        title=post.title,
        content=post.content,
        image=post.image,
        file1=post.file1,
        file2=post.file2,
        file3=post.file3,
        file4=post.file4,
        file5=post.file5,
        likes=post.likes,
        dislikes=post.dislikes,
        createdby=post.createdby,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **post.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/posts/update",  tags=["posts"])
async def update_post(post: PostUpdateSchema):
    gDate = datetime.datetime.now()
    query = posts_table.update().\
        where(posts_table.c.id == post.id).\
        values(
            title=post.title,
            content=post.content,
            image=post.image,
            file1=post.file1,
            file2=post.file2,
            file3=post.file3,
            file4=post.file4,
            file5=post.file5,
            likes=post.likes,
            dislikes=post.dislikes,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_post_by_id(post.id)


@app.put("/posts/archive", tags=["posts"])
async def archive_post(post: PostUpdateSchema):
    gDate = datetime.datetime.now()
    query = posts_table.update().\
        where(posts_table.c.id == post.id).\
        values(
            title=post.title,
            content=post.content,
            image=post.image,
            file1=post.file1,
            file2=post.file2,
            file3=post.file3,
            file4=post.file4,
            file5=post.file5,
            likes=post.likes,
            dislikes=post.dislikes,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_post_by_id(post.id)


@app.put("/posts/restore", tags=["posts"])
async def restore_post(post: PostUpdateSchema):
    gDate = datetime.datetime.now()
    query = posts_table.update().\
        where(posts_table.c.id == post.id).\
        values(
            title=post.title,
            content=post.content,
            image=post.image,
            file1=post.file1,
            file2=post.file2,
            file3=post.file3,
            file4=post.file4,
            file5=post.file5,
            likes=post.likes,
            dislikes=post.dislikes,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_post_by_id(post.id)


@app.delete("/posts/{scheduleid}", tags=["posts"])
async def delete_post(scheduleid: str):
    query = posts_table.delete().where(posts_table.c.id == scheduleid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This post has been deleted!"
    }

@app.post("/posts/comments", response_model=CommentSchema, tags=["posts"])
async def add_comment(comment: CommentSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = comments_table.insert().values(
        id=gID,
        comment=comment.comment,
        postid=comment.postid,
        file1=comment.file1,
        file2=comment.file2,
        file3=comment.file3,
        file4=comment.file4,
        file5=comment.file5,
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

@app.get("/posts/comments/{postid}", tags=["posts"])
async def get_post_comments_by_id(postid: str):
    query = comments_table.select().where(comments_table.c.postid == postid)
    results = await database.fetch_all(query)
    res = []
    if results:
        for result in results:
            res.append({
            "id": result["id"],
            "postid": result["postid"],
            "comment": result["comment"],
            "file1": result["file1"],
            "file2": result["file2"],
            "file3": result["file3"],
            "file4": result["file4"],
            "file5": result["file5"],
            "datecreated": result["datecreated"],
            "createdby": await get_usernames_by_id(result["createdby"]),
            "dateupdated": result["dateupdated"],
            "updatedby": result["updatedby"],
            "status": result["status"]
            })
        
        return res
    else:
        raise HTTPException(status_code=204, detail='No comments found')

@app.get("/posts/commentscount/{postid}", tags=["posts"])
async def get_post_comments_count_by_id(postid: str):
    counter = 0
    query = comments_table.select().where(comments_table.c.postid == postid)
    results = await database.fetch_all(query)
    if results:
        for result in results:
            counter += 1

    return counter

@app.post("/posts/like", tags=["posts"])
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

@app.post("/posts/dislike", tags=["posts"])
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

@app.get("/posts/likes/{postid}", tags=["posts"])
async def get_post_likes_count_by_id(postid: str):
    counter = 0
    query = likes_table.select().where(likes_table.c.postid == postid).where(likes_table.c.isliked == True)
    results = await database.fetch_all(query)
    if results:
        for result in results:
            counter += 1

    return counter

@app.get("/posts/dislikes/{postid}", tags=["posts"])
async def get_post_dislikes_count_by_id(postid: str):
    counter = 0
    query = likes_table.select().where(likes_table.c.postid == postid).where(likes_table.c.isliked == False)
    results = await database.fetch_all(query)
    if results:
        for result in results:
            counter += 1

    return counter

@app.post("/posts/userliked/{postid}/{userid}", tags=["posts"])
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

##################### END POSTS ###################

###################### WALLET ######################

@app.get("/wallet", response_model=List[WalletSchema], tags=["wallet"])
async def get_all_wallets():
    query = userwallet_table.select()
    return await database.fetch_all(query)


@app.get("/wallet/{walletid}", response_model=WalletSchema, tags=["wallet"])
async def get_wallet_by_id(roleid: str):
    query = userwallet_table.select().where(userwallet_table.c.id == roleid)
    result = await database.fetch_one(query)
    return result


@app.get("/wallet/userid/{userid}", response_model=WalletSchema, tags=["wallet"])
async def get_wallet_by_userid(userid: str):
    query = userwallet_table.select().where(userwallet_table.c.userid == userid)
    result = await database.fetch_one(query)
    return result


@app.post("/wallet/register/{userid}", response_model=WalletSchema, tags=["wallet"])
async def register_wallet(userid: str):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = userwallet_table.insert().values(
        id=gID,
        userid=userid,
        availablebalance=0,
        currentbalance=0,
        totalincoming=0,
        totaloutgoing=0,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    await create_walletlog(0, "IN", "Wallet Created", userid, gID)

    return {
        "id": gID,
        "userid": userid,
        "currentbalance": 0,
        "datecreated": gDate,
        "status": "1"
    }


@app.put("/wallet/update", response_model=WalletUpdateSchema, tags=["wallet"])
async def update_wallet(wallet: WalletUpdateSchema):
    gDate = datetime.datetime.now()
    query = userwallet_table.update().\
        where(userwallet_table.c.id == wallet.id).\
        values(
            availablebalance=wallet.availablebalance,
            currentbalance=wallet.currentbalance,
            totalincoming=wallet.totalincoming,
            totaloutgoing=wallet.totaloutgoing,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_wallet_by_id(wallet.id)


@app.put("/wallet/archive", response_model=WalletUpdateSchema, tags=["wallet"])
async def archive_wallet(wallet: WalletUpdateSchema):
    gDate = datetime.datetime.now()
    query = userwallet_table.update().\
        where(userwallet_table.c.id == wallet.id).\
        values(
            availablebalance=wallet.availablebalance,
            currentbalance=wallet.currentbalance,
            totalincoming=wallet.totalincoming,
            totaloutgoing=wallet.totaloutgoing,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_wallet_by_id(wallet.id)


@app.put("/wallet/restore", response_model=WalletUpdateSchema, tags=["wallet"])
async def restore_wallet(wallet: WalletUpdateSchema):
    gDate = datetime.datetime.now()
    query = userwallet_table.update().\
        where(userwallet_table.c.id == wallet.id).\
        values(
            availablebalance=wallet.availablebalance,
            currentbalance=wallet.currentbalance,
            totalincoming=wallet.totalincoming,
            totaloutgoing=wallet.totaloutgoing,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_wallet_by_id(wallet.id)


@app.put("/wallet/topup", response_model=WalletTopupSchema, tags=["wallet"], dependencies=[Depends(jwtBearer())])
async def topup_wallet(wallet: WalletTopupSchema):
    gDate = datetime.datetime.now()
    query = userwallet_table.update().\
        where(userwallet_table.c.id == wallet.userwalletid).\
        values(
            availablebalance=wallet.availablebalance,
            currentbalance=wallet.currentbalance,
            totalincoming=wallet.totalincoming,
            totaloutgoing=wallet.totaloutgoing,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    await create_walletlog(wallet.amount, wallet.type, wallet.description, wallet.userid, wallet.userwalletid)
    return await get_wallet_by_id(wallet.id)


@app.delete("/wallet/{walletid}", tags=["wallet"])
async def delete_wallet(walletid: str):
    query = userwallet_table.delete().where(userwallet_table.c.id == walletid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This user wallet has been deleted!"
    }

###################### END WALLET ##################

###################### WALLET LOGS ######################


@app.get("/walletlogs", response_model=List[WalletLogSchema], tags=["walletlogs"])
async def get_all_walletlogs():
    query = userwalletlog_table.select()
    return await database.fetch_all(query)


@app.get("/walletlogs/{walletlogid}", response_model=WalletLogSchema, tags=["walletlogs"])
async def get_walletlog_by_id(walletlogid: str):
    query = userwalletlog_table.select().where(
        userwalletlog_table.c.id == walletlogid)
    result = await database.fetch_one(query)
    return result


@app.get("/walletlogs/userid/{userid}", tags=["walletlogs"])
async def get_walletlog_by_userid(userid: str):
    # query = userwalletlog_table.select().where(userwalletlog_table.c.userid == userid)
    # result = await database.fetch_all(query)
    # return result
    query = userwalletlog_table.select().where(
        userwalletlog_table.c.userid == userid)
    results = await database.fetch_all(query)
    if results:
        return results

    else:
        raise HTTPException(status_code=404, detail='No transactions found')


@app.post("/walletlogs/create", response_model=WalletLogSchema, tags=["walletlogs"])
async def create_walletlog(amount: float, type: str, description: str, userid: str, userwalletid: str):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = userwalletlog_table.insert().values(
        id=gID,
        userid=userid,
        userwalletid=userwalletid,
        amount=amount,
        type=type,
        description=description,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        "id": gID,
        "userid": userid,
        "userwalletid": userwalletid,
        "amount": amount,
        "type": type,
        "description": description,
        "datecreated": gDate
    }


@app.put("/walletlogs/update", response_model=WalletLogUpdateSchema, tags=["walletlogs"])
async def update_walletlog(walletlog: WalletLogUpdateSchema):
    gDate = datetime.datetime.now()
    query = userwalletlog_table.update().\
        where(userwalletlog_table.c.id == walletlog.id).\
        values(
            amount=walletlog.amount,
            type=walletlog.type,
            description=walletlog.description,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_walletlog_by_id(walletlog.id)


@app.put("/walletlogs/archive", response_model=WalletLogUpdateSchema, tags=["walletlogs"])
async def archive_walletlog(walletlog: WalletLogUpdateSchema):
    gDate = datetime.datetime.now()
    query = userwalletlog_table.update().\
        where(userwalletlog_table.c.id == walletlog.id).\
        values(
            amount=walletlog.amount,
            type=walletlog.type,
            description=walletlog.description,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_walletlog_by_id(walletlog.id)


@app.put("/walletlogs/restore", response_model=WalletLogUpdateSchema, tags=["walletlogs"])
async def restore_walletlog(walletlog: WalletLogUpdateSchema):
    gDate = datetime.datetime.now()
    query = userwalletlog_table.update().\
        where(userwalletlog_table.c.id == walletlog.id).\
        values(
            amount=walletlog.amount,
            type=walletlog.type,
            description=walletlog.description,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_walletlog_by_id(walletlog.id)


@app.delete("/walletlogs/{walletid}", tags=["walletlogs"])
async def delete_walletlog(walletid: str):
    query = userwalletlog_table.delete().where(
        userwalletlog_table.c.id == walletid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This user wallet log has been deleted!"
    }

###################### END WALLET LOGS ##################


###################### TIMETABLE ######################

@app.get("/timetable", response_model=List[ScheduleSchema], tags=["timetable"])
async def get_all_schedules():
    query = schedules_table.select()
    return await database.fetch_all(query)


@app.get("/timetable/{scheduleid}", response_model=ScheduleDetailsSchema, tags=["timetable"])
async def get_schedule_by_id(scheduleid: str):
    query = schedules_table.select().where(schedules_table.c.id == scheduleid)
    result = await database.fetch_one(query)
    return result


@app.get("/timetable/class/{classid}", tags=["timetable"])
async def get_schedule_by_classid(classid: str):
    query = schedules_table.select().where(schedules_table.c.classid == classid)
    results = await database.fetch_all(query)
    if results:
        res = []
        for result in results:
            res.append({
                "subjectname": await get_subjectname_by_id(result["subjectid"]),
                "classname": await get_classname_by_id(result["classid"]),
                "teachername": await get_usernames_by_id(result["userid"]),
                "dayname": await get_dayname_by_id(result["dayid"]),
                "start": result["start"],
                "end": result["end"],
            })
        return res

    else:
        raise HTTPException(
            status_code=404, detail='No timetable for this class')


@app.get("/timetable/classandday/{classid}/{dayid}", tags=["timetable"])
async def get_schedule_by_classid_and_dayid(classid: str, dayid: str):
    print("Class id: "+classid)
    print("Day id: "+dayid)
    query = schedules_table.select().where(schedules_table.c.classid ==
                                           classid).where(schedules_table.c.dayid == dayid)
    results = await database.fetch_all(query)
    if results:
        res = []
        for result in results:
            res.append({
                "subjectname": await get_subjectname_by_id(result["subjectid"]),
                "classname": await get_classname_by_id(result["classid"]),
                "teachername": await get_usernames_by_id(result["userid"]),
                "dayname": await get_dayname_by_id(result["dayid"]),
                "start": result["start"],
                "end": result["end"],
            })
        return res

    else:
        return{
            "error": "Class has no schedules"
        }


@app.get("/timetable/details/{scheduleid}", tags=["timetable"])
async def get_scheduled_details_by_id(scheduleid: str):
    query = schedules_table.select().where(schedules_table.c.id == scheduleid)
    result = await database.fetch_one(query)
    if result:
        print(result)
        subject = await get_subjectname_by_id(result["subjectid"])
        teacher = await get_usernames_by_id(result["userid"])
        day = await get_dayname_by_id(result["dayid"])
        classname = await get_classname_by_id(result["classid"])
        return{
            "subject": subject,
            "teacher": teacher,
            "day":  day,
            "class": classname,
            "start": result["start"],
            "end": result["end"]
        }
    else:
        return {
            "Error": "This schedule does not exist!"
        }


@app.post("/timetable", response_model=ScheduleSchema, tags=["timetable"])
async def add_schedule(schedule: ScheduleSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = schedules_table.insert().values(
        id=gID,
        classid=schedule.classid,
        subjectid=schedule.subjectid,
        userid=schedule.userid,
        dayid=schedule.dayid,
        start=schedule.start,
        end=schedule.end,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **schedule.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/timetable/update", response_model=ScheduleUpdateSchema, tags=["timetable"])
async def update_schedule(schedule: ScheduleUpdateSchema):
    gDate = datetime.datetime.now()
    query = schedules_table.update().\
        where(schedules_table.c.id == schedule.id).\
        values(
            title=schedule.title,
            content=schedule.content,
            image=schedule.image,
            file1=schedule.file1,
            file2=schedule.file2,
            file3=schedule.file3,
            file4=schedule.file4,
            file5=schedule.file5,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_schedule_by_id(schedule.id)


@app.put("/timetable/archive", response_model=ScheduleUpdateSchema, tags=["timetable"])
async def archive_schedule(schedule: ScheduleUpdateSchema):
    gDate = datetime.datetime.now()
    query = schedules_table.update().\
        where(schedules_table.c.id == schedule.id).\
        values(
            title=schedule.title,
            content=schedule.content,
            image=schedule.image,
            file1=schedule.file1,
            file2=schedule.file2,
            file3=schedule.file3,
            file4=schedule.file4,
            file5=schedule.file5,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_schedule_by_id(schedule.id)


@app.put("/timetable/restore", response_model=ScheduleUpdateSchema, tags=["timetable"])
async def restore_schedule(schedule: ScheduleUpdateSchema):
    gDate = datetime.datetime.now()
    query = schedules_table.update().\
        where(schedules_table.c.id == schedule.id).\
        values(
            title=schedule.title,
            content=schedule.content,
            image=schedule.image,
            file1=schedule.file1,
            file2=schedule.file2,
            file3=schedule.file3,
            file4=schedule.file4,
            file5=schedule.file5,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_schedule_by_id(schedule.id)


@app.delete("/timetable/{scheduleid}", tags=["timetable"])
async def delete_schedule(scheduleid: str):
    query = schedules_table.delete().where(schedules_table.c.id == scheduleid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This schedule has been deleted!"
    }

###################### END TIMETABLE ##################


###################### DAYS ######################


@app.get("/days", response_model=List[DaySchema], tags=["days"])
async def get_all_days():
    query = days_table.select()
    return await database.fetch_all(query)


@app.get("/days/{dayid}", response_model=NewsSchema, tags=["days"])
async def get_day_by_id(dayid: str):
    query = days_table.select().where(days_table.c.id == dayid)
    result = await database.fetch_one(query)
    return result


@app.get("/days/{dayid}", response_model=NewsSchema, tags=["days"])
async def get_dayname_by_id(dayid: str):
    query = days_table.select().where(days_table.c.id == dayid)
    result = await database.fetch_one(query)
    if result:
        return result["dayname"]
    else:
        return "Uknown Day"


@app.post("/days/post", response_model=DaySchema, tags=["days"])
async def post_day(day: DaySchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = days_table.insert().values(
        id=gID,
        dayname=day.dayname,
        daycode=day.daycode,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **day.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/days/update", response_model=DayUpdateSchema, tags=["days"])
async def update_day(day: DayUpdateSchema):
    gDate = datetime.datetime.now()
    query = days_table.update().\
        where(days_table.c.id == day.id).\
        values(
            dayname=day.dayname,
            daycode=day.daycode,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_day_by_id(day.id)


@app.put("/days/archive", response_model=DayUpdateSchema, tags=["days"])
async def archive_day(day: DayUpdateSchema):
    gDate = datetime.datetime.now()
    query = days_table.update().\
        where(days_table.c.id == day.id).\
        values(
            dayname=day.dayname,
            daycode=day.daycode,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_day_by_id(day.id)


@app.put("/days/restore", response_model=DayUpdateSchema, tags=["days"])
async def restore_day(day: DayUpdateSchema):
    gDate = datetime.datetime.now()
    query = days_table.update().\
        where(days_table.c.id == day.id).\
        values(
            dayname=day.dayname,
            daycode=day.daycode,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_day_by_id(day.id)


@app.delete("/days/{dayid}", tags=["days"])
async def delete_day(dayid: str):
    query = days_table.delete().where(days_table.c.id == dayid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This day has been deleted!"
    }

###################### END DAYS ##################


###################### ACADEMIC PERIODS ######################


@app.get("/academicperiods", response_model=List[AcademicPeriodSchema], tags=["academics"])
async def get_all_academic_periods():
    query = academicperiods_table.select()
    return await database.fetch_all(query)


@app.get("/academicperiods/{periodid}", response_model=AcademicPeriodSchema, tags=["academics"])
async def get_academic_period_by_id(periodid: str):
    query = academicperiods_table.select().where(academicperiods_table.c.id == periodid)
    result = await database.fetch_one(query)
    return result


@app.get("/academicperiods/{periodid}", response_model=AcademicPeriodSchema, tags=["academics"])
async def get_academic_period_name_by_id(periodid: str):
    query = academicperiods_table.select().where(academicperiods_table.c.id == periodid)
    result = await database.fetch_one(query)
    if result:
        return result["periodname"]
    else:
        return "Unknown Academic Period"


@app.post("/academicperiods/", response_model=AcademicPeriodInsertSchema, tags=["academics"])
async def register_academic_period(period: AcademicPeriodInsertSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = academicperiods_table.insert().values(
        id=gID,
        periodname=period.periodname,
        description = period.description,
        startdate = datetime.datetime.strptime((period.startdate), "%Y-%m-%d").date(),
        enddate = datetime.datetime.strptime((period.enddate), "%Y-%m-%d").date(),
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    return {
        **period.dict(),
        "id": gID,
        "datecreated": gDate
    }


@app.put("/academicperiods/update", response_model=AcademicPeriodUpdateSchema, tags=["academics"])
async def update_academic_period(period: AcademicPeriodUpdateSchema):
    gDate = datetime.datetime.now()
    query = academicperiods_table.update().\
        where(academicperiods_table.c.id == period.id).\
        values(
            periodname=period.periodname,
            description = period.description,
            startdate = datetime.datetime.strptime((period.startdate), "%Y-%m-%d").date(),
            enddate = datetime.datetime.strptime((period.enddate), "%Y-%m-%d").date(),
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_academic_period_by_id(period.id)


@app.put("/academicperiods/archive", response_model=AcademicPeriodUpdateSchema, tags=["academics"])
async def archive_academic_period(period: AcademicPeriodUpdateSchema):
    gDate = datetime.datetime.now()
    query = academicperiods_table.update().\
        where(academicperiods_table.c.id == period.id).\
        values(
            periodname=period.periodname,
            description = period.description,
            startdate = datetime.datetime.strptime((period.startdate), "%Y-%m-%d").date(),
            enddate = datetime.datetime.strptime((period.enddate), "%Y-%m-%d").date(),
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_academic_period_by_id(period.id)


@app.put("/academicperiods/restore", response_model=AcademicPeriodUpdateSchema, tags=["academics"])
async def restore_academic_period(period: AcademicPeriodUpdateSchema):
    gDate = datetime.datetime.now()
    query = academicperiods_table.update().\
        where(academicperiods_table.c.id == period.id).\
        values(
            periodname=period.periodname,
            description = period.description,
            startdate = datetime.datetime.strptime((period.startdate), "%Y-%m-%d").date(),
            enddate = datetime.datetime.strptime((period.enddate), "%Y-%m-%d").date(),
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_academic_period_by_id(period.id)


@app.delete("/academicperiods/{periodid}", tags=["academics"])
async def delete_academic_period(periodid: str):
    query = academicperiods_table.delete().where(academicperiods_table.c.id == periodid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This academic period has been deleted!"
    }

###################### END ACADEMIC PERIODS ##################

