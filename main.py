from collections import UserList
from email.mime import image
import hashlib
from turtle import title
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
    return{"Hello": "World"}

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
    query = users_table.select().where(users_table.c.username == user.username)
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
        id=gID,
        username=user.username,
        password=user.password,
        firstname=user.firstname,
        lastname=user.lastname,
        gender=user.gender,
        datecreated=gDate,
        status="1"
    )

    await database.execute(query)
    await register_wallet(gID)
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
            firstname=user.firstname,
            lastname=user.lastname,
            gender=user.gender,
            password=user.password,
            roleid=user.roleid,
            email=user.email,
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
        datecreated=gDate,
        status="1"
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

###################### CLASSES ######################


@app.get("/classes", response_model=List[ClassSchema], tags=["class"])
async def get_all_classes():
    query = classes_table.select()
    return await database.fetch_all(query)


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
        fullname = result["classname"]
        return fullname
    else:
        return "Unknown Class"


@app.post("/classes/register", response_model=ClassSchema, tags=["class"])
async def register_class(subject: ClassSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = classes_table.insert().values(
        id=gID,
        classname=subject.classname,
        shortcode=subject.shortcode,
        datecreated=gDate,
        status="1"
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
            classname=classs.classname,
            shortcode=classs.shortcode,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_class_by_id(classs.id)


@app.put("/classes/archive", response_model=ClassUpdateSchema, tags=["class"])
async def archive_class(classs: ClassUpdateSchema):
    gDate = datetime.datetime.now()
    query = classes_table.update().\
        where(classes_table.c.id == classs.id).\
        values(
            classname=classs.classname,
            shortcode=classs.shortcode,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_class_by_id(classs.id)


@app.put("/classes/restore", response_model=ClassUpdateSchema, tags=["class"])
async def restore_class(classs: ClassUpdateSchema):
    gDate = datetime.datetime.now()
    query = classes_table.update().\
        where(classes_table.c.id == classs.id).\
        values(
            classname=classs.classname,
            shortcode=classs.shortcode,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_class_by_id(classs.id)


@app.delete("/classes/{subjectid}", tags=["class"])
async def delete_class(subjectid: str):
    query = classes_table.delete().where(classes_table.c.id == subjectid)
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
        feesid=club.feesid,
        datecreated=gDate,
        status="1"
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
            clubname=club.clubname,
            shortcode=club.shortcode,
            description=club.description,
            patronid=club.patronid,
            asstpatronid=club.asstpatronid,
            feesid=club.feesid,
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
            feesid=club.feesid,
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
            feesid=club.feesid,
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


@app.get("/fees/name/{feeid}", tags=["fees"])
async def get_feename_by_id(feeid: str):
    query = fees_table.select().where(fees_table.c.id == feeid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["feesname"]
        return fullname
    else:
        return "Unknown Fee"


@app.post("/fees/register", response_model=FeesSchema, tags=["fees"])
async def register_fee(fee: FeesSchema):
    gID = str(uuid.uuid1())
    gDate = datetime.datetime.now()
    query = fees_table.insert().values(
        id=gID,
        feesname=fee.feesname,
        type=fee.type,
        description=fee.description,
        interval=fee.interval,
        startdate=fee.startdate,
        enddate=fee.enddate,
        duedate=fee.duedate,
        amount=fee.amount,
        datecreated=gDate,
        status="1"
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
            feesname=fee.feesname,
            type=fee.type,
            description=fee.description,
            interval=fee.interval,
            startdate=fee.startdate,
            enddate=fee.enddate,
            duedate=fee.duedate,
            amount=fee.amount,
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_fee_by_id(fee.id)


@app.put("/fees/archive", response_model=FeesUpdateSchema, tags=["fees"])
async def archive_fee(fee: FeesUpdateSchema):
    gDate = datetime.datetime.now()
    query = fees_table.update().\
        where(fees_table.c.id == fee.id).\
        values(
            feesname=fee.feesname,
            type=fee.type,
            description=fee.description,
            interval=fee.interval,
            startdate=fee.startdate,
            enddate=fee.enddate,
            duedate=fee.duedate,
            amount=fee.amount,
            status="0",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_fee_by_id(fee.id)


@app.put("/fees/restore", response_model=FeesUpdateSchema, tags=["fees"])
async def restore_fee(fee: FeesUpdateSchema):
    gDate = datetime.datetime.now()
    query = fees_table.update().\
        where(fees_table.c.id == fee.id).\
        values(
            feesname=fee.feesname,
            type=fee.type,
            description=fee.description,
            interval=fee.interval,
            startdate=fee.startdate,
            enddate=fee.enddate,
            duedate=fee.duedate,
            amount=fee.amount,
            status="1",
            dateupdated=gDate
    )

    await database.execute(query)
    return await get_club_by_id(fee.id)


@app.delete("/fees/{feeid}", tags=["fees"])
async def delete_fee(feeid: str):
    query = fees_table.delete().where(fees_table.c.id == feeid)
    result = await database.execute(query)

    return {
        "status": True,
        "message": "This fee has been deleted!"
    }

###################### END FEES ##################


################### STUDENTS ###################

@app.get("/students/", tags=["students"])
async def get_all_students():
    query = students_table.select()
    results = await database.fetch_all(query)
    return results


@app.get("/students/{studentid}", response_model=StudentSchema, tags=["fees"])
async def get_student_by_id(studentid: str):
    query = students_table.select().where(students_table.c.id == studentid)
    result = await database.fetch_one(query)
    return result


@app.get("/students/name/{studentid}", tags=["fees"])
async def get_studentname_by_id(studentid: str):
    query = students_table.select().where(students_table.c.id == studentid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["firstname"] + " " + result["lastname"]
        return fullname
    else:
        return "Unknown Student"


@app.get("/students/parent/{parentid}", tags=["students"])
async def get_parent_students(parentid: str):
    query = students_table.select().where(students_table.c.parentone == parentid)
    results = await database.fetch_all(query)
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
        id=gID,
        firstname=student.firstname,
        lastname=student.lastname,
        othernames=student.othernames,
        # dateofbirth=student.dateofbirth,
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
        "id": gID,
        **student.dict(),
        "datecreated": gDate,
    }


@app.put("/students/update", response_model=StudentSchema, tags=["students"])
async def update_student(student: StudentSchema):

    gDate = datetime.datetime.now()
    query = students_table.update().\
        where(students_table.c.id == student.id).\
        values(
            firtname=student.firstname,
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
        "id": gID,
        **news.dict(),
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

# Get all posts
@app.get("/posts", tags=["posts"])
def get_posts():
    return {"data": posts}

# Get post by id


@app.get("/posts{id}", tags=["posts"])
def get_one_post(id: int):
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


@app.put("/wallet/topup", response_model=WalletTopupSchema, tags=["wallet"])
async def topup_wallet(wallet: WalletTopupSchema):
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
        return{
            "error": "User has no previous transactions."
        }


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
        "id": gID,
        **schedule.dict(),
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
        "id": gID,
        **day.dict(),
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
async def archive_news(day: DayUpdateSchema):
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
async def restore_news(day: DayUpdateSchema):
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
