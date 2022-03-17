from collections import UserList
import hashlib
from typing import List
from unittest import result
from xmlrpc.client import DateTime
import uvicorn
from fastapi import FastAPI, Body, Depends
from app.model import *
from app.auth.jwt_handler import signJWT
from app.auth.jwt_bearer import jwtBearer
from decouple import config



posts = [
    {
        "id": 1,
        "title": "Penguins",
        "content": "Penguin content"
    }
]


app = FastAPI()

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.get("/", tags=["test"])
def greet():
    return{"Hello" : "World"}

################### USERS ###################

@app.get("/get_users", response_model=List[UserSchema], tags=["user"])
async def get_all_users():
    query = users_table.select()
    return await database.fetch_all(query)

@app.get("/users/{userid}", response_model=UserSchema, tags=["user"])
async def get_user_by_id(userid: str):
    query = users_table.select().where(users_table.c.id == userid)
    result = await database.fetch_one(query)
    return result


@app.post("/user/login", tags=["user"])
async def user_login(user: UserLoginSchema = Body(default=None)):
    query = users_table.select().where(users_table.c.username == user.username)
    result =  await database.fetch_one(query)
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
                "photo": result.get("photo"),
                "roleid": result.get("roleid"),
                "token": signJWT(user.username),
                "status": result.get("status")
            }
    else:
        return{
            "error": "Invalid login details"
        }

@app.post("/users/signup", response_model=UserSignUpSchema, tags=["user"])
async def register_user(user: UserSignUpSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = users_table.insert().values(
        id           = gID,
        username     = user.username,
        password     = user.password,
        firstname    = user.firstname,
        lastname     =  user.lastname,
        gender       = user.gender,
        datecreated  = gDate,
        status       = "1"
    )

    await database.execute(query)
    return {
        "id": gID,
        **user.dict(),
        "datecreated": gDate,
        "token": signJWT(user.username),
        "status": "1"
    }

@app.put("/users/update", response_model=UserUpdateSchema, tags=["user"])
async def update_user(user: UserUpdateSchema):
    gDate = datetime.datetime.now()
    query = users_table.update().\
        where(users_table.c.id == user.id).\
        values(
            firstname = user.firstname,
            lastname = user.lastname,
            gender = user.gender,
            password = user.password,
            roleid = user.roleid,
            email = user.email,
            status = user.status,
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_user_by_id(user.id)

@app.put("/users/archive", response_model=UserUpdateSchema, tags=["user"])
async def archive_user(user: UserUpdateSchema):
    gDate = datetime.datetime.now()
    query = users_table.update().\
        where(users_table.c.id == user.id).\
        values(
            firstname = user.firstname,
            lastname = user.lastname,
            gender = user.gender,
            password = user.password,
            roleid = user.roleid,
            email = user.email,
            status = "0",
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_user_by_id(user.id)
    
@app.put("/users/restore", response_model=UserUpdateSchema, tags=["user"])
async def restore_user(user: UserUpdateSchema):
    gDate = datetime.datetime.now()
    query = users_table.update().\
        where(users_table.c.id == user.id).\
        values(
            firstname = user.firstname,
            lastname = user.lastname,
            gender = user.gender,
            password = user.password,
            roleid = user.roleid,
            email = user.email,
            status = "1",
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_user_by_id(user.id)

@app.delete("/users/{userid}", tags=["user"])
async def delete_user(userid: str):
    query = users_table.delete().where(users_table.c.id == userid)
    result = await database.execute(query)

    return {
        "status"  : True,
        "message" : "This user has been deleted!"
    }
     

################### END USERS ###################

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

@app.post("/roles/register", response_model=RoleSchema, tags=["role"])
async def register_role(role: RoleSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = roles_table.insert().values(
        id           = gID,
        rolename     = role.rolename,
        description     = role.description,
        datecreated  = gDate,
        status       = "1"
    )

    await database.execute(query)
    return {
        "id": gID,
        **role.dict(),
        "datecreated": gDate
    }

@app.put("/roles/update", response_model=RoleUpdateSchema, tags=["role"])
async def update_role(role: RoleUpdateSchema):
    gDate = datetime.datetime.now()
    query = roles_table.update().\
        where(roles_table.c.id == role.id).\
        values(
            rolename = role.rolename,
            description = role.description,
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_role_by_id(role.id)

@app.put("/roles/archive", response_model=RoleUpdateSchema, tags=["role"])
async def archive_role(role: RoleUpdateSchema):
    gDate = datetime.datetime.now()
    query = roles_table.update().\
        where(roles_table.c.id == role.id).\
        values(
            rolename = role.rolename,
            description = role.description,
            status = "0",
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_role_by_id(role.id)
    
@app.put("/roles/restore", response_model=RoleUpdateSchema, tags=["role"])
async def restore_role(role: RoleUpdateSchema):
    gDate = datetime.datetime.now()
    query = roles_table.update().\
        where(roles_table.c.id == role.id).\
        values(
            rolename = role.rolename,
            description = role.description,
            status = "1",
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_role_by_id(role.id)

@app.delete("/roles/{roleid}", tags=["role"])
async def delete_role(roleid: str):
    query = roles_table.delete().where(roles_table.c.id == roleid)
    result = await database.execute(query)

    return {
        "status"  : True,
        "message" : "This role has been deleted!"
    }

###################### END ROLES ##################

###################### SUBJECTS ######################

@app.get("/subjects", response_model=List[SubjectSchema], tags=["subject"])
async def get_all_subjects():
    query = subjects_table.select()
    return await database.fetch_all(query)

@app.get("/subjects/{roleid}", response_model=SubjectSchema, tags=["subject"])
async def get_subject_by_id(subjectid: str):
    query = subjects_table.select().where(subjects_table.c.id == subjectid)
    result = await database.fetch_one(query)
    return result

@app.post("/subjects/register", response_model=SubjectSchema, tags=["subject"])
async def register_subject(subject: SubjectSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = subjects_table.insert().values(
        id           = gID,
        subjectname = subject.subjectname,
        shortcode = subject.shortcode,
        datecreated  = gDate,
        status       = "1"
    )

    await database.execute(query)
    return {
        "id": gID,
        **subject.dict(),
        "datecreated": gDate
    }

@app.put("/subjects/update", response_model=SubjectSchema, tags=["subject"])
async def update_subject(subject: SubjectSchema):
    gDate = datetime.datetime.now()
    query = subjects_table.update().\
        where(subjects_table.c.id == subject.id).\
        values(
            subjectname = subject.subjectname,
            shortcode = subject.shortcode,
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_subject_by_id(subject.id)

@app.put("/subjects/archive", response_model=SubjectSchema, tags=["subject"])
async def archive_subject(subject: SubjectSchema):
    gDate = datetime.datetime.now()
    query = subjects_table.update().\
        where(subjects_table.c.id == subject.id).\
        values(
            subjectname = subject.subjectname,
            shortcode = subject.shortcode,
            status = "0",
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_subject_by_id(subject.id)
    
@app.put("/subjects/restore", response_model=SubjectSchema, tags=["subject"])
async def restore_subject(subject: SubjectSchema):
    gDate = datetime.datetime.now()
    query = subjects_table.update().\
        where(subjects_table.c.id == subject.id).\
        values(
            subjectname = subject.subjectname,
            shortcode = subject.shortcode,
            status = "1",
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_subject_by_id(subject.id)

@app.delete("/subjects/{subjectid}", tags=["subject"])
async def delete_subject(subjectid: str):
    query = subjects_table.delete().where(subjects_table.c.id == subjectid)
    result = await database.execute(query)

    return {
        "status"  : True,
        "message" : "This subject has been deleted!"
    }

###################### END SUBJECTS ##################

###################### CLASSES ######################

@app.get("/classes", response_model=List[ClassSchema], tags=["class"])
async def get_all_classes():
    query = classes_table.select()
    return await database.fetch_all(query)

@app.get("/classes/{roleid}", response_model=ClassSchema, tags=["class"])
async def get_class_by_id(classid: str):
    query = classes_table.select().where(classes_table.c.id == classid)
    result = await database.fetch_one(query)
    return result

@app.post("/classes/register", response_model=ClassSchema, tags=["class"])
async def register_class(subject: ClassSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = classes_table.insert().values(
        id           = gID,
        classname = subject.classname,
        shortcode = subject.shortcode,
        datecreated  = gDate,
        status       = "1"
    )

    await database.execute(query)
    return {
        "id": gID,
        **subject.dict(),
        "datecreated": gDate
    }

@app.put("/classes/update", response_model=ClassUpdateSchema, tags=["class"])
async def update_class(classs: ClassUpdateSchema):
    gDate = datetime.datetime.now()
    query = classes_table.update().\
        where(classes_table.c.id == classs.id).\
        values(
            classname = classs.classname,
            shortcode = classs.shortcode,
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_class_by_id(classs.id)

@app.put("/classes/archive", response_model=ClassUpdateSchema, tags=["class"])
async def archive_class(classs: ClassUpdateSchema):
    gDate = datetime.datetime.now()
    query = classes_table.update().\
        where(classes_table.c.id == classs.id).\
        values(
            classname = classs.classname,
            shortcode = classs.shortcode,
            status = "0",
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_class_by_id(classs.id)
    
@app.put("/classes/restore", response_model=ClassUpdateSchema, tags=["class"])
async def restore_class(classs: ClassUpdateSchema):
    gDate = datetime.datetime.now()
    query = classes_table.update().\
        where(classes_table.c.id == classs.id).\
        values(
            classname = classs.classname,
            shortcode = classs.shortcode,
            status = "1",
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_class_by_id(classs.id)

@app.delete("/classes/{subjectid}", tags=["class"])
async def delete_class(subjectid: str):
    query = classes_table.delete().where(classes_table.c.id == subjectid)
    result = await database.execute(query)

    return {
        "status"  : True,
        "message" : "This class has been deleted!"
    }

###################### END CLASSES ##################

###################### TEACHER-SUBJECT-CLASS ASSIGMENTS ######################

@app.get("/teacherclasssubjects", response_model=List[TeacherClassSubjectSchema], tags=["teacherclasssubject"])
async def get_all_classes():
    query = classteachersubjects_table.select()
    results =  await database.fetch_all(query)
    return results

@app.get("/teacherclasssubjects/{tcsid}", response_model=TeacherClassSubjectSchema, tags=["teacherclasssubject"])
async def get_teacherclasssubject_by_id(tcsid: str):
    query = classteachersubjects_table.select().where(classteachersubjects_table.c.id == tcsid)
    result = await database.fetch_one(query)
    return result

@app.post("/teacherclasssubjects/register", response_model=TeacherClassSubjectSchema, tags=["teacherclasssubject"])
async def register_teacherclasssubject(tcs: TeacherClassSubjectSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = classteachersubjects_table.insert().values(
        id           = gID,
        subjectid = tcs.subjectid,
        classid = tcs.classid,
        userid = tcs.userid,
        datecreated  = gDate,
        status       = "1"
    )

    await database.execute(query)
    return {
        "id": gID,
        **tcs.dict(),
        "datecreated": gDate
    }

@app.put("/teacherclasssubjects/update", response_model=TeacherClassSubjectUpdateSchema, tags=["teacherclasssubject"])
async def update_teacherclasssubject(tcs: TeacherClassSubjectUpdateSchema):
    gDate = datetime.datetime.now()
    query = classteachersubjects_table.update().\
        where(classteachersubjects_table.c.id == tcs.id).\
        values(
            classid = tcs.classid,
            subjectid = tcs.subjectid,
            userid = tcs.userid,
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_teacherclasssubject_by_id(tcs.id)

@app.put("/teacherclasssubjects/archive", response_model=TeacherClassSubjectUpdateSchema, tags=["teacherclasssubject"])
async def archive_teacherclasssubject(tcs: TeacherClassSubjectUpdateSchema):
    gDate = datetime.datetime.now()
    query = classteachersubjects_table.update().\
        where(classteachersubjects_table.c.id == tcs.id).\
        values(
            classid = tcs.classid,
            subjectid = tcs.subjectid,
            userid = tcs.userid,
            status = "0",
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_teacherclasssubject_by_id(tcs.id)
    
@app.put("/teacherclasssubjects/restore", response_model=TeacherClassSubjectUpdateSchema, tags=["teacherclasssubject"])
async def restore_teacherclasssubject(tcs: TeacherClassSubjectUpdateSchema):
    gDate = datetime.datetime.now()
    query = classteachersubjects_table.update().\
        where(classteachersubjects_table.c.id == tcs.id).\
        values(
            classid = tcs.classid,
            subjectid = tcs.subjectid,
            userid = tcs.userid,
            status = "1",
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_teacherclasssubject_by_id(tcs.id)

@app.delete("/teacherclasssubjects/{tcsid}", tags=["teacherclasssubject"])
async def delete_teacherclasssubject(tcsid: str):
    query = classteachersubjects_table.delete().where(classteachersubjects_table.c.id == tcsid)
    result = await database.execute(query)

    return {
        "status"  : True,
        "message" : "This teacher-class-subject relation has been deleted!"
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

@app.post("/clubs/register", response_model=ClubSchema, tags=["club"])
async def register_club(club: ClubSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = clubs_table.insert().values(
        id           = gID,
       clubname = club.clubname,
        shortcode = club.shortcode,
        description = club.description,
        patronid = club.patronid,
        asstpatronid = club.asstpatronid,
        feesid = club.feesid,
        datecreated  = gDate,
        status       = "1"
    )

    await database.execute(query)
    return {
        "id": gID,
        **club.dict(),
        "datecreated": gDate
    }

@app.put("/clubs/update", response_model=ClubUpdateSchema, tags=["club"])
async def update_club(club: ClubUpdateSchema):
    gDate = datetime.datetime.now()
    query = clubs_table.update().\
        where(clubs_table.c.id == club.id).\
        values(
            clubname = club.clubname,
            shortcode = club.shortcode,
            description = club.description,
            patronid = club.patronid,
            asstpatronid = club.asstpatronid,
            feesid = club.feesid,
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_club_by_id(club.id)

@app.put("/clubs/archive", response_model=ClubUpdateSchema, tags=["club"])
async def archive_club(club: ClubUpdateSchema):
    gDate = datetime.datetime.now()
    query = clubs_table.update().\
        where(clubs_table.c.id == club.id).\
        values(
            clubname = club.clubname,
            shortcode = club.shortcode,
            description = club.description,
            patronid = club.patronid,
            asstpatronid = club.asstpatronid,
            feesid = club.feesid,
            status = "0",
            dateupdated = gDate
        ) 

    await database.execute(query)
    return await get_club_by_id(club.id)
    
@app.put("/clubs/restore", response_model=ClubUpdateSchema, tags=["club"])
async def restore_club(club: ClubUpdateSchema):
    gDate = datetime.datetime.now()
    query = clubs_table.update().\
        where(clubs_table.c.id == club.id).\
        values(
            clubname = club.clubname,
            shortcode = club.shortcode,
            description = club.description,
            patronid = club.patronid,
            asstpatronid = club.asstpatronid,
            feesid = club.feesid,
            status = "1",
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_club_by_id(club.id)

@app.delete("/clubs/{clubid}", tags=["club"])
async def delete_club(clubid: str):
    query = clubs_table.delete().where(clubs_table.c.id == clubid)
    result = await database.execute(query)

    return {
        "status"  : True,
        "message" : "This club has been deleted!"
    }

###################### END CLUBS ##################

###################### FEES ######################

@app.get("/fees", response_model=List[FeesSchema], tags=["fees"])
async def get_all_fees():
    query = fees_table.select()
    return await database.fetch_all(query)

@app.get("/fees/{feeid}", response_model=FeesSchema, tags=["fees"])
async def get_fee_by_id(feeid: str):
    query = fees_table.select().where(fees_table.c.id == feeid)
    result = await database.fetch_one(query)
    return result

@app.post("/fees/register", response_model=FeesSchema, tags=["fees"])
async def register_fee(fee: FeesSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = fees_table.insert().values(
        id           = gID,
        feesname = fee.feesname,
        type = fee.type,
        description = fee.description,
        interval = fee.interval,
        startdate = fee.startdate,
        enddate = fee.enddate,
        duedate = fee.duedate,
        amount = fee.amount,
        datecreated  = gDate,
        status       = "1"
    )

    await database.execute(query)
    return {
        "id": gID,
        **fee.dict(),
        "datecreated": gDate
    }

@app.put("/fees/update", response_model=FeesUpdateSchema, tags=["fees"])
async def update_fee(fee: FeesUpdateSchema):
    gDate = datetime.datetime.now()
    query = fees_table.update().\
        where(fees_table.c.id == fee.id).\
        values(
            feesname = fee.feesname,
            type = fee.type,
            description = fee.description,
            interval = fee.interval,
            startdate = fee.startdate,
            enddate = fee.enddate,
            duedate = fee.duedate,
            amount = fee.amount,
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_fee_by_id(fee.id)

@app.put("/fees/archive", response_model=FeesUpdateSchema, tags=["fees"])
async def archive_fee(fee: FeesUpdateSchema):
    gDate = datetime.datetime.now()
    query = fees_table.update().\
        where(fees_table.c.id == fee.id).\
        values(
            feesname = fee.feesname,
            type = fee.type,
            description = fee.description,
            interval = fee.interval,
            startdate = fee.startdate,
            enddate = fee.enddate,
            duedate = fee.duedate,
            amount = fee.amount,
            status = "0",
            dateupdated = gDate
        ) 

    await database.execute(query)
    return await get_fee_by_id(fee.id)
    
@app.put("/fees/restore", response_model=FeesUpdateSchema, tags=["fees"])
async def restore_fee(fee: FeesUpdateSchema):
    gDate = datetime.datetime.now()
    query = fees_table.update().\
        where(fees_table.c.id == fee.id).\
        values(
            feesname = fee.feesname,
            type = fee.type,
            description = fee.description,
            interval = fee.interval,
            startdate = fee.startdate,
            enddate = fee.enddate,
            duedate = fee.duedate,
            amount = fee.amount,
            status = "1",
            dateupdated = gDate
        )

    await database.execute(query)
    return await get_club_by_id(fee.id)

@app.delete("/fees/{feeid}", tags=["fees"])
async def delete_fee(feeid: str):
    query = fees_table.delete().where(fees_table.c.id == feeid)
    result = await database.execute(query)

    return {
        "status"  : True,
        "message" : "This fee has been deleted!"
    }

###################### END FEES ##################



################### STUDENTS ###################

@app.get("/students/", tags=["students"])
async def get_all_students():
    query = students_table.select()
    results =  await database.fetch_all(query)
    return results

@app.get("/students/{parentid}", tags=["students"])
async def get_parent_students(parentid : str):
    query = students_table.select().where(students_table.c.parentone == parentid)
    results =  await database.fetch_all(query)
    if results:
        return results
            
    else:
        return{
            "error": "Parent has no Students"
        }

@app.post("/students/signup", response_model=StudentSignUpSchema, tags=["students"])
async def register_student(student: StudentSignUpSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = students_table.insert().values(
        id           = gID,
        firstname    = student.firstname,
        lastname     =  student.lastname,
        othernames   = student.othernames,
        gender       = student.gender,
        datecreated  = gDate,
        status       = "1"
    )

    await database.execute(query)
    return {
        "id": gID,
        **student.dict(),
        "datecreated": gDate,
    }

################### END STUDENTS ###################

################### POSTS ###################

## Get all posts
@app.get("/posts" ,tags=["posts"])
def get_posts():
    return {"data": posts}

## Get post by id
@app.get("/posts{id}", tags=["posts"])
def get_one_post(id : int):
    if id > len(posts):
        return {
            "error": "post does not exist"
        } 
    for post in posts:
        if post["id"] == id:
            return{
                "data": post
            }

@app.post("/posts", dependencies=[Depends(jwtBearer())], tags=["posts"])
def add_posts(post: PostSchema):
    """ Function to add new post"""
    post.id = len(posts) + 1
    posts.append(post.dict())
    return{
        "info": "Post Added!"
    }


##################### END POSTS ###################