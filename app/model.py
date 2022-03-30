import email
from tokenize import Double
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
import databases, sqlalchemy, datetime, uuid  

## Postgres Database 
LOCAL_DATABASE_URL = "postgresql://postgres:password@127.0.0.1:5432/schoolsapp"
LIVE_DATABASE_URL = "postgresql://doadmin:qoXVNkR3aK6Gaita@db-postgresql-nyc3-44787-do-user-11136722-0.b.db.ondigitalocean.com:25060/schoolsapp?sslmode=require"
DATABASE_URL = LIVE_DATABASE_URL
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

roles_table = sqlalchemy.Table(
    "roles",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("rolename"     , sqlalchemy.String),
    sqlalchemy.Column("description"  , sqlalchemy.String),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

users_table = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("firstname"    , sqlalchemy.String),
    sqlalchemy.Column("lastname"     , sqlalchemy.String),
    sqlalchemy.Column("username"     , sqlalchemy.String),
    sqlalchemy.Column("email"        , sqlalchemy.String),
    sqlalchemy.Column("phone"        , sqlalchemy.String),
    sqlalchemy.Column("address"      , sqlalchemy.String),
    sqlalchemy.Column("dateofbirth"  , sqlalchemy.DateTime),
    sqlalchemy.Column("password"     , sqlalchemy.String),
    sqlalchemy.Column("gender"       , sqlalchemy.String),
    sqlalchemy.Column("photo"        , sqlalchemy.String),
    sqlalchemy.Column("roleid"       , sqlalchemy.String),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

classes_table = sqlalchemy.Table(
    "classes",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("classname"    , sqlalchemy.String),
    sqlalchemy.Column("shortcode"    , sqlalchemy.String),
    sqlalchemy.Column("classteacherid", sqlalchemy.String),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

days_table = sqlalchemy.Table(
    "days",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("dayname"     , sqlalchemy.String),
    sqlalchemy.Column("daycode"  , sqlalchemy.String),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

schedules_table = sqlalchemy.Table(
    "schedules",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("subjectid"    , sqlalchemy.String),
    sqlalchemy.Column("userid"       , sqlalchemy.String),
    sqlalchemy.Column("classid"      , sqlalchemy.String),
    sqlalchemy.Column("dayid"        , sqlalchemy.String),
    sqlalchemy.Column("start"        , sqlalchemy.Time),
    sqlalchemy.Column("end"          , sqlalchemy.Time),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

events_table = sqlalchemy.Table(
    "events",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name"         , sqlalchemy.String),
    sqlalchemy.Column("description"  , sqlalchemy.String),
    sqlalchemy.Column("start"        , sqlalchemy.DateTime),
    sqlalchemy.Column("end"          , sqlalchemy.DateTime),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

houses_table = sqlalchemy.Table(
    "houses",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("housename"    , sqlalchemy.String),
    sqlalchemy.Column("color"        , sqlalchemy.String),
    sqlalchemy.Column("patronid"     , sqlalchemy.String),
    sqlalchemy.Column("asstpatronid" , sqlalchemy.String),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

students_table = sqlalchemy.Table(
    "students",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("firstname"    , sqlalchemy.String),
    sqlalchemy.Column("lastname"     , sqlalchemy.String),
    sqlalchemy.Column("othernames"   , sqlalchemy.String),
    sqlalchemy.Column("photo"        , sqlalchemy.String),
    sqlalchemy.Column("phone"        , sqlalchemy.String),
    sqlalchemy.Column("email"        , sqlalchemy.String),
    sqlalchemy.Column("gender"       , sqlalchemy.String),
    sqlalchemy.Column("houseid"      , sqlalchemy.String),
    sqlalchemy.Column("parentone"    , sqlalchemy.String),
    sqlalchemy.Column("parenttwo"    , sqlalchemy.String),
    sqlalchemy.Column("parentthree"  , sqlalchemy.String),
    sqlalchemy.Column("dateofbirth"  , sqlalchemy.DateTime),
    sqlalchemy.Column("address"      , sqlalchemy.String),
    sqlalchemy.Column("weight"       , sqlalchemy.Float),
    sqlalchemy.Column("height"       , sqlalchemy.Float),
    sqlalchemy.Column("studentid"    , sqlalchemy.String),
    sqlalchemy.Column("classid"      , sqlalchemy.String),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

subjects_table = sqlalchemy.Table(
    "subjects",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("subjectname"     , sqlalchemy.String),
    sqlalchemy.Column("shortcode"  , sqlalchemy.String),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

classteachersubjects_table = sqlalchemy.Table(
    "classteachersubjects",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("subjectid"    , sqlalchemy.String),
    sqlalchemy.Column("classid"      , sqlalchemy.String),
    sqlalchemy.Column("userid"       , sqlalchemy.String),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

clubs_table = sqlalchemy.Table(
    "clubs",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("clubname"     , sqlalchemy.String),
    sqlalchemy.Column("shortcode"    , sqlalchemy.String),
    sqlalchemy.Column("description"    , sqlalchemy.String),
    sqlalchemy.Column("patronid"     , sqlalchemy.String),
    sqlalchemy.Column("asstpatronid" , sqlalchemy.String),
    sqlalchemy.Column("feesid"       , sqlalchemy.String),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

fees_table = sqlalchemy.Table(
    "fees",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("feesname"     , sqlalchemy.String),
    sqlalchemy.Column("description"  , sqlalchemy.String),
    sqlalchemy.Column("type"         , sqlalchemy.String),
    sqlalchemy.Column("interval"     , sqlalchemy.String),
    sqlalchemy.Column("startdate"    , sqlalchemy.DateTime),
    sqlalchemy.Column("enddate"      , sqlalchemy.DateTime),
    sqlalchemy.Column("duedate"      , sqlalchemy.DateTime),
    sqlalchemy.Column("amount"       , sqlalchemy.Float),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

userwallet_table = sqlalchemy.Table(
    "userwallet",
    metadata,
    sqlalchemy.Column("id"                  , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("userid"              , sqlalchemy.String),
    sqlalchemy.Column("availablebalance"    , sqlalchemy.Float),
    sqlalchemy.Column("currentbalance"      , sqlalchemy.Float),
    sqlalchemy.Column("totalincoming"       , sqlalchemy.Float),
    sqlalchemy.Column("totaloutgoing"       , sqlalchemy.Float),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

userwalletlog_table = sqlalchemy.Table(
    "userwalletlog",
    metadata,
    sqlalchemy.Column("id"                  , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("userid"              , sqlalchemy.String),
    sqlalchemy.Column("userwalletid"        , sqlalchemy.String),
    sqlalchemy.Column("amount"              , sqlalchemy.Float),
    sqlalchemy.Column("type"                , sqlalchemy.String),
    sqlalchemy.Column("description"         , sqlalchemy.String),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

news_table = sqlalchemy.Table(
    "news",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("title"        , sqlalchemy.String),
    sqlalchemy.Column("content"      , sqlalchemy.String),
    sqlalchemy.Column("image"        , sqlalchemy.Text),
    sqlalchemy.Column("file1"        , sqlalchemy.Text),
    sqlalchemy.Column("file2"        , sqlalchemy.Text),
    sqlalchemy.Column("file3"        , sqlalchemy.Text),
    sqlalchemy.Column("file4"        , sqlalchemy.Text),
    sqlalchemy.Column("file5"        , sqlalchemy.Text),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

posts_table = sqlalchemy.Table(
    "posts",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("title"        , sqlalchemy.String),
    sqlalchemy.Column("content"      , sqlalchemy.String),
    sqlalchemy.Column("image"        , sqlalchemy.Text),
    sqlalchemy.Column("file1"        , sqlalchemy.Text),
    sqlalchemy.Column("file2"        , sqlalchemy.Text),
    sqlalchemy.Column("file3"        , sqlalchemy.Text),
    sqlalchemy.Column("file4"        , sqlalchemy.Text),
    sqlalchemy.Column("file5"        , sqlalchemy.Text),
    sqlalchemy.Column("likes"        , sqlalchemy.Integer),
    sqlalchemy.Column("dislikes"        , sqlalchemy.Integer),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.String),
)

comments_table = sqlalchemy.Table(
    "comments",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("postid"       , sqlalchemy.String),
    sqlalchemy.Column("comment"      , sqlalchemy.String),
    sqlalchemy.Column("file1"        , sqlalchemy.Text),
    sqlalchemy.Column("file2"        , sqlalchemy.Text),
    sqlalchemy.Column("file3"        , sqlalchemy.Text),
    sqlalchemy.Column("file4"        , sqlalchemy.Text),
    sqlalchemy.Column("file5"        , sqlalchemy.Text),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.String),
)

grades_table = sqlalchemy.Table(
    "grades",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("gradename"    , sqlalchemy.String),
    sqlalchemy.Column("shortcode"    , sqlalchemy.String),
    sqlalchemy.Column("min"          , sqlalchemy.Float),
    sqlalchemy.Column("max"          , sqlalchemy.Float),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

results_table = sqlalchemy.Table(
    "results",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("subjectid"    , sqlalchemy.String),
    sqlalchemy.Column("classid"      , sqlalchemy.String),
    sqlalchemy.Column("gradeid"      , sqlalchemy.String),
    sqlalchemy.Column("teacherid"    , sqlalchemy.String),
    sqlalchemy.Column("studentid"    , sqlalchemy.String),
    sqlalchemy.Column("resultypeid"  , sqlalchemy.String),
    sqlalchemy.Column("mark"         , sqlalchemy.Float),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

resulttypes_table = sqlalchemy.Table(
    "resulttypes",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name"         , sqlalchemy.String),
    sqlalchemy.Column("shortcode"    , sqlalchemy.String),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

engine = sqlalchemy.create_engine(
    DATABASE_URL
)
metadata.create_all(engine)

# class PostSchema(BaseModel):
#     id          : str = Field(default=None)
#     title       : str = Field(default=None)
#     content     : str = Field(default= None)
#     thumbnail   : str = Field(default= None)
#     likes       : int = Field(default= 0)
#     dislikes    : str = Field(default=0)
#     datepublished:Optional[datetime.datetime] = None
#     datecreated : datetime.datetime
#     createdby   : Optional[str] = None
#     dateupdated : Optional[datetime.datetime] = None
#     updatedby   : Optional[str] = None
#     status   : Optional[str] = None
#     class Config:
#         orm_mode = True
#         the_schema = {
#             "user_demo": {
#                 "id" : "---",
#                 "title": "My Blog",
#                 "content": "My Blog Content",
#                 "thumbnail" : "--",
#                 "likes": 0,
#                 "dislikes": 0,
#                 "datepublished": datetime.datetime,
#                 "datecreated": datetime.datetime,
#                 "createdby": "1",
#                 "dateupdated": None,
#                 "updatedby": None,
#                 "status": "1"
#             }
#         }

##################### USERS ###########################

class UserSchema(BaseModel):
    id          : str = Field(default=None)
    firstname   : str = Field(default=None)
    lastname    : str = Field(default= None)
    username    : str = Field(default= None)
    email       : EmailStr = Field(default= None)
    password    : str = Field(default=None)
    gender      : str = Field(default=None)
    roleid      : Optional[str] = None
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id" : "---",
                "firstname": "John",
                "lastname": "Doe",
                "username" : "help@bekbrace.com",
                "password": "1234",
                "gender": "Male",
                "roleid": "1",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class UserUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    firstname   : str = Field(default=None)
    lastname    : str = Field(default= None)
    username    : str = Field(default= None)
    email       : EmailStr = Field(default= None)
    password    : str = Field(default=None)
    gender      : str = Field(default=None)
    roleid      : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id":  "ID",
                "firstname": "John",
                "lastname": "Doe",
                "username" : "help@bekbrace.com",
                "password": "1234",
                "gender": "Male",
                "roleid": "1",
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class UserDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "user": {
                "id" : "---"
            }
        }

class UserLoginSchema(BaseModel):
    username : str = Field(default= None)
    password : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "username" : "help@bekbrace.com",
                "password": "1234"
            }
        }

class UserSignUpSchema(BaseModel):
    id          : str = Field(..., example="0")
    firstname   : str = Field(..., example="John")
    lastname    : str = Field(..., example="Doe")
    username    : str = Field(..., example="johndoe")
    email       : EmailStr = Field(..., example="johndoe@email.com")
    password    : str = Field(..., example="johndoe")
    gender      : str = Field(..., example="M")
    status      : str = Field(..., example="1")

##################### END_USERS ###########################

##################### ROLES ###########################
class RoleSchema(BaseModel):
    id          : str = Field(default=None)
    rolename   : str = Field(default=None)
    description    : str = Field(default= None)
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id" : "---",
                "rolename": "Role",
                "description": "Role Description",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class RoleUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    rolename    : str = Field(default=None)
    description : str = Field(default= None)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id":  "ID",
                "rolename": "Role",
                "description": "Role Description",
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class RoleDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "role": {
                "id" : "---"
            }
        }

##################### END_ROLES ###########################

##################### DAYS ###########################
class DaySchema(BaseModel):
    id          : str = Field(default=None)
    dayname     : str = Field(default=None)
    daycode     : str = Field(default= None)
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id" : "---",
                "dayname": "Monday",
                "daycode": "MON",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class DayUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    dayname     : str = Field(default=None)
    daycode     : str = Field(default= None)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id":  "ID",
                "dayname": "Monday",
                "daycode": "MON",
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class DayDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "day": {
                "id" : "---"
            }
        }

##################### END_DAYS ###########################

##################### GRADES ###########################
class GradeSchema(BaseModel):
    id          : str = Field(default=None)
    gradename   : str = Field(default=None)
    shortcode   : str = Field(default= None)
    min         : float = Field(default= None)
    max         : float = Field(default= None)
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "grade_demo": {
                "id" : "---",
                "gradename": "Distinction 1",
                "shortcode": "D1",
                "min": 0.0,
                "max": 0.0,
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class GradeUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    gradename        : str = Field(default=None)
    shortcode   : str = Field(default= None)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "grade_demo": {
                "id":  "ID",
                "gradename": "Distinction 1",
                "shortcode": "D1",
                "min": 0.0,
                "max": 0.0,
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class GradeDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "grade": {
                "id" : "---"
            }
        }

##################### END_GRADES ###########################

##################### RESULT ###########################
class ResultSchema(BaseModel):
    id          : str = Field(default=None)
    subjectid   : str = Field(default=None)
    classid     : str = Field(default= None)
    gradeid     : str = Field(default=None)
    teacherid   : str = Field(default= None)
    studentid   : str = Field(default=None)
    resultypeid : str = Field(default= None)
    mark        : float = Field(default=None)
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "result_demo": {
                "id" : "---",
                "name": "Beginning of Term",
                "shortcode": "BoT",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class ResultUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    name        : str = Field(default=None)
    shortcode   : str = Field(default= None)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "result_demo": {
                "id":  "ID",
                "name": "Beginning of Term",
                "shortcode": "BoT",
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class ResultDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "result": {
                "id" : "---"
            }
        }

##################### END_RESULTS ###########################


##################### RESULT TYPES ###########################
class ResultTypeSchema(BaseModel):
    id          : str = Field(default=None)
    name        : str = Field(default=None)
    shortcode   : str = Field(default= None)
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id" : "---",
                "name": "Beginning of Term",
                "shortcode": "BoT",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class ResultTypeUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    name        : str = Field(default=None)
    shortcode   : str = Field(default= None)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id":  "ID",
                "name": "Beginning of Term",
                "shortcode": "BoT",
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class ResultTypeDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "result_type": {
                "id" : "---"
            }
        }

##################### END_RESULT_TYPES ###########################

##################### EVENTS ###########################
class EventSchema(BaseModel):
    id          : str = Field(default=None)
    name        : str = Field(default=None)
    description : str = Field(default= None)
    start       : Optional[datetime.datetime] = None
    end         : Optional[datetime.datetime] = None
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id" : "---",
                "name": "Sports Day",
                "description": "Annual Sports Day",
                "start": "2022-05-25T09:00:00",
                "end": "2022-05-25T16:00:00",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class EventUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    name        : str = Field(default=None)
    description : str = Field(default= None)
    start       : str = Field(default= None)
    end         : str = Field(default= None)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id":  "ID",
                "name": "Sports Day",
                "description": "Annual Sports Day",
                "start": "2022-05-25T09:00:00",
                "end": "2022-05-25T16:00:00",
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class EventDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "event": {
                "id" : "---"
            }
        }

##################### END_EVENTS ###########################

##################### NEWS ###########################
class NewsSchema(BaseModel):
    id          : str = Field(default=None)
    title       : str = Field(default=None)
    content     : str = Field(default= None)
    image       : str = Field(default= None)
    file1       : str = Field(default= None)
    file2       : str = Field(default= None)
    file3       : str = Field(default= None)
    file4       : str = Field(default= None)
    file5       : str = Field(default= None)
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status      : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "news_demo": {
                "id" : "---",
                "title": "Title",
                "content": "Cotent",
                "image": "IMG Base64",
                "file1": "File",
                "file2": "File",
                "file3": "File",
                "file4": "File",
                "file5": "File",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class NewsUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    title       : str = Field(default=None)
    content     : str = Field(default= None)
    image       : str = Field(default= None)
    file1       : str = Field(default= None)
    file2       : str = Field(default= None)
    file3       : str = Field(default= None)
    file4       : str = Field(default= None)
    file5       : str = Field(default= None)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status      : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id" : "---",
                "title": "Title",
                "content": "Cotent",
                "image": "IMG Base64",
                "file1": "File",
                "file2": "File",
                "file3": "File",
                "file4": "File",
                "file5": "File",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class NewsDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "news": {
                "id" : "---"
            }
        }

##################### END_NEWS ###########################


##################### POSTS ###########################
class PostSchema(BaseModel):
    id          : str = Field(default=None)
    title       : str = Field(default=None)
    content     : str = Field(default= None)
    image       : str = Field(default= None)
    file1       : str = Field(default= None)
    file2       : str = Field(default= None)
    file3       : str = Field(default= None)
    file4       : str = Field(default= None)
    file5       : str = Field(default= None)
    likes       : int = Field(default= 0)
    likes       : int = Field(default= 0)
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status      : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "news_demo": {
                "id" : "---",
                "title": "Title",
                "content": "Cotent",
                "image": "IMG Base64",
                "file1": "File",
                "file2": "File",
                "file3": "File",
                "file4": "File",
                "file5": "File",
                "likes": 0,
                "disikes": 0,
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "PENDING"
            }
        }

class PostUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    title       : str = Field(default=None)
    content     : str = Field(default= None)
    image       : str = Field(default= None)
    file1       : str = Field(default= None)
    file2       : str = Field(default= None)
    file3       : str = Field(default= None)
    file4       : str = Field(default= None)
    file5       : str = Field(default= None)
    likes       : int = Field(default= 0)
    likes       : int = Field(default= 0)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status      : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id" : "---",
                "title": "Title",
                "content": "Cotent",
                "image": "IMG Base64",
                "file1": "File",
                "file2": "File",
                "file3": "File",
                "file4": "File",
                "file5": "File",
                "likes": 0,
                "disikes": 0,
                "dateupdated": None,
                "updatedby": None,
                "status": "PENDING"
            }
        }

class PostDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "post": {
                "id" : "---"
            }
        }

##################### END_POSTS ###########################

##################### SUBJECTS ###########################
class SubjectSchema(BaseModel):
    id          : str = Field(default=None)
    subjectname : str = Field(default=None)
    shortcode   : str = Field(default= None)
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status      : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id" : "---",
                "subjectname": "Subject",
                "shortcode": "SBJ",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class SubjectUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    subjectname : str = Field(default=None)
    shortcode   : str = Field(default= None)
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status      : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id" : "---",
                "subjectname": "Subject",
                "shortcode": "SBJ",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class SubjectDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "subject": {
                "id" : "---"
            }
        }

##################### END_SUBJECTS ###########################

##################### CLASSES ###########################
class ClassSchema(BaseModel):
    id          : str = Field(default=None)
    classname : str = Field(default=None)
    shortcode   : str = Field(default= None)
    classteacherid : str = Field(default= None)
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status      : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id" : "---",
                "classname": "Primary 7 A",
                "shortcode": "P.7.A",
                "classteacherid": "-",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class ClassUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    classname : str = Field(default=None)
    shortcode   : str = Field(default= None)
    classteacherid : str = Field(default= None)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status      : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id" : "---",
                "classname": "Primary 7A",
                "shortcode": "P.7.A",
                "classteacherid": "-",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class ClassDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "subject": {
                "id" : "---"
            }
        }

##################### END_CLASSES ###########################

##################### TEACHER-CLASS-SUBJECTS ###########################
class TeacherClassSubjectSchema(BaseModel):
    id          : str = Field(default=None)
    subjectid   : str = Field(default=None)
    classid     : str = Field(default= None)
    userid      : str = Field(default= None)
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status      : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "teacherclasssubject_demo": {
                "id" : "---",
                "subjectid": "Subject Id",
                "classid": "Class Id",
                "userid": "Teacher User Id",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class TeacherClassSubjectUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    subjectid   : str = Field(default=None)
    classid     : str = Field(default= None)
    userid      : str = Field(default= None)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "teacherclasssubject_demo": {
                "id":  "ID",
                "subjectid": "Subject Id",
                "classid": "Class Id",
                "userid": "Teacher User Id",
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class TeacherClassSubjectDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "teacherclasssubject": {
                "id" : "---"
            }
        }

##################### END_TEACHER-CLASS-SUBJECTS ###########################

##################### CLUBS ###########################
class ClubSchema(BaseModel):
    id          : str = Field(default=None)
    clubname    : str = Field(default=None)
    shortcode   : str = Field(default=None)
    description : str = Field(default= None)
    patronid    : str = Field(default= None)
    asstpatronid: str = Field(default= None)
    feesid      : str = Field(default= None)
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "club_demo": {
                "id" : "---",
                "clubname": "Club",
                "shortcode": "Code",
                "description": "Club Description",
                "patronid": "Patron Id",
                "asstpatronid": "Asst. Patron Id",
                "feesid": "Fees Id",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class ClubUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    clubname    : str = Field(default=None)
    shortcode   : str = Field(default=None)
    description : str = Field(default= None)
    patronid    : str = Field(default= None)
    asstpatronid: str = Field(default= None)
    feesid      : str = Field(default= None)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "club_demo": {
                "id":  "ID",
                "clubname": "Club",
                "shortcode": "Code",
                "description": "Club Description",
                "patronid": "Patron Id",
                "asstpatronid": "Asst. Patron Id",
                "feesid": "Fees Id",
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class ClubDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "club": {
                "id" : "---"
            }
        }

##################### END_CLUBS ###########################

##################### FEES ###########################
class FeesSchema(BaseModel):
    id          : str = Field(default=None)
    feesname    : str = Field(default=None)
    description : str = Field(default= None)    
    type        : str = Field(default=None)
    interval    : str = Field(default= None)
    startdate   : Optional[datetime.datetime] = None
    enddate     : Optional[datetime.datetime] = None
    duedate     : Optional[datetime.datetime] = None
    amount      : Optional[float] = None
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "fees_demo": {
                "id" : "---",
                "feesname": "Club",
                "description": "Club Description",
                "type": "Fees Type",
                "startdate": None,
                "enddate": None,
                "duedate": None,
                "amount" : 0,
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class FeesUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    feesname    : str = Field(default=None)
    description : str = Field(default= None)    
    type        : str = Field(default=None)
    interval    : str = Field(default= None)
    startdate   : Optional[datetime.datetime] = None
    enddate     : Optional[datetime.datetime] = None
    duedate     : Optional[datetime.datetime] = None
    amount      : Optional[float] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "fees_demo": {
                "id":  "ID",
                "feesname": "Club",
                "description": "Club Description",
                "type": "Fees Type",
                "startdate": None,
                "enddate": None,
                "duedate": None,
                "amount": 0,
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class FeesDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "fee": {
                "id" : "---"
            }
        }

##################### END_CLUBS ###########################

##################### WALLET ###########################
class WalletSchema(BaseModel):
    id                  : str = Field(default=None)
    userid              : str = Field(default=None)
    availablebalance    : float = Field(default= None)
    currentbalance      : float = Field(default= None)
    totalincoming       : float = Field(default= None)
    totaloutgoing       : float = Field(default= None)
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id" : "---",
                "userid": "UserID",
                "availablebalance": 0.0,
                "currentbalance": 0.0,
                "totalincoming": 0.0,
                "totaloutgoing": 0.0,
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class WalletUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    availablebalance    : float = Field(default= None)
    currentbalance      : float = Field(default= None)
    totalincoming       : float = Field(default= None)
    totaloutgoing       : float = Field(default= None)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id":  "ID",
                "availablebalance": 0.0,
                "currentbalance": 0.0,
                "totalincoming": 0.0,
                "totaloutgoing": 0.0,
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class WalletTopupSchema(BaseModel):
    id                  : str = Field(default=None)
    amount              : float = Field(default= None)
    userid              : str = Field(default=None)
    userwalletid        : str = Field(default=None)
    type                : str = Field(default=None)
    description         : str = Field(default=None)
    availablebalance    : float = Field(default= None)
    currentbalance      : float = Field(default= None)
    totalincoming       : float = Field(default= None)
    totaloutgoing       : float = Field(default= None)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id":  "ID",
                "availablebalance": 0.0,
                "currentbalance": 0.0,
                "totalincoming": 0.0,
                "totaloutgoing": 0.0,
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class WalletDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "wallet": {
                "id" : "---"
            }
        }

##################### END_WALLET ###########################

##################### WALLET LOGS ###########################
class WalletLogSchema(BaseModel):
    id                  : str = Field(default=None)
    userid              : str = Field(default=None)
    userwalletid        : str = Field(default=None)
    amount              : float = Field(default= None)
    type                : str = Field(default= None)
    description         : str = Field(default= None)
    datecreated         : Optional[datetime.datetime] = None
    createdby           : Optional[str] = None
    dateupdated         : Optional[datetime.datetime] = None
    updatedby           : Optional[str] = None
    status              : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "walletlog_demo": {
                "id" : "---",
                "userid": "UserID",
                "userwalletid": "",
                "amount": 0.0,
                "type": "IN",
                "descripttion": "FLutterwave Top up",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class WalletLogUpdateSchema(BaseModel):
    id                  : str = Field(default=None)
    userid              : str = Field(default=None)
    userwalletid        : str = Field(default=None)
    amount              : float = Field(default= None)
    type                : str = Field(default= None)
    description         : float = Field(default= None)
    dateupdated         : datetime.datetime
    updatedby           : Optional[str] = None
    status              : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "walletlog_demo": {
                "id":  "ID",
                "userid": "UserID",
                "userwalletid": "",
                "amount": 0.0,
                "type": "IN",
                "descripttion": "FLutterwave Top up",
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class WalletLogDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "walletlog": {
                "id" : "---"
            }
        }

##################### END_WALLET_LOGS ###########################


#################### STUDENTS #############################

class StudentSchema(BaseModel):
    id          : str = Field(..., example="0")
    firstname   : str = Field(..., example="John")
    lastname    : str = Field(..., example="Doe")
    othernames  : str = Field(..., example="Alex")
    dateofbirth : Optional[datetime.datetime] = None
    photo       : str = Field(..., example="-----")
    phone       : str = Field(..., example="0771000111")
    email       : EmailStr = Field(..., example="email@gmail.com")
    parentone   : str = Field(..., example="Parent")
    parenttwo   : str = Field(..., example="Parent")
    parentthree : str = Field(..., example="Parent")
    classid     : str = Field(..., example="Class Id")
    studentid   : str = Field(..., example="Student Id")
    gender      : str = Field(..., example="M")
    address     : str = Field(..., example="First Street, City")
    datecreated : Optional[datetime.datetime] = None
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status      : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "student_demo": {
                "id" : "---",
                "firstname": "Fname",
                "lastname": "Lname",
                "othernames": "OtherNames",
                "dateofbirth": datetime.datetime,
                "photo": "------",
                "phone": "0770111222",
                "email": "me@email.com",
                "gender": "F",
                "classid": "Class ID",
                "studentid": "Student ID",
                "address": "First Street, City",
                "parentone": "",
                "parenttwo": "",
                "parentthree": "",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class StudentSignUpSchema(BaseModel):
    id          : str = Field(..., example="0")
    firstname   : str = Field(..., example="John")
    lastname    : str = Field(..., example="Doe")
    othernames  : str = Field(..., example="Alex")
    dateofbirth : Optional[datetime.datetime] = None
    photo       : str = Field(..., example="-----")
    phone       : str = Field(..., example="0771000111")
    email       : EmailStr = Field(..., example="email@gmail.com")
    parentone   : str = Field(..., example="Parent")
    parenttwo   : str = Field(..., example="Parent")
    parentthree : str = Field(..., example="Parent")
    classid     : str = Field(..., example="Class Id")
    studentid   : str = Field(..., example="Student Id")
    gender      : str = Field(..., example="M")
    address     : str = Field(..., example="First Street, City")
    createdby   : Optional[str] = None
    datecreated : Optional[datetime.datetime] = None
    status      : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "student_demo": {
                "id" : "---",
                "firstname": "Fname",
                "lastname": "Lname",
                "othernames": "OtherNames",
                "dateofbirth": datetime.datetime,
                "photo": "------",
                "phone": "0770111222",
                "email": "me@email.com",
                "gender": "F",
                "classid": "Class ID",
                "studentid": "Student ID",
                "address": "First Street, City",
                "parentone": "",
                "parenttwo": "",
                "parentthree": "",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "status": "1"
            }
        }

##################### END_STUDENTS ##########################

##################### TIMETABLES ###########################
class ScheduleSchema(BaseModel):
    id                  : str = Field(default=None)
    subjectid           : str = Field(default=None)
    userid              : str = Field(default=None)
    classid             : str = Field(default=None)
    dayid               : str = Field(default=None)
    start               : datetime.time = Field(default= None)
    end                 : datetime.time = Field(default= None)
    datecreated         : Optional[datetime.datetime] = None
    createdby           : Optional[str] = None
    dateupdated         : Optional[datetime.datetime] = None
    updatedby           : Optional[str] = None
    status              : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "schedule_demo": {
                "id" : "---",
                "subjectid": "Subject ID",
                "userid": "User ID",
                "classid": "Class ID",
                "dayid": "Day ID",
                "start": datetime.time,
                "end": datetime.time,
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

async def get_subjectname_by_id(subjectid: str):
    query = subjects_table.select().where(subjects_table.c.id == subjectid)
    result = await database.fetch_one(query)
    if result:
        fullname = result["subjectname"]
        return fullname
    else:
        return "Unkown Subject"

class ScheduleDetailsSchema(BaseModel):
    id                  : str = Field(default=None)
    subjectid           : str = Field(default="")
    userid              : str = Field(default=None)
    classid             : str = Field(default=None)
    dayid               : str = Field(default=None)
    start               : datetime.time = Field(default= None)
    end                 : datetime.time = Field(default= None)
    datecreated         : Optional[datetime.datetime] = None
    createdby           : Optional[str] = None
    dateupdated         : Optional[datetime.datetime] = None
    updatedby           : Optional[str] = None
    status              : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "schedule_demo": {
                "id" : "---",
                "subjectid": "Subject ID",
                "userid": "User ID",
                "classid": "Class ID",
                "dayid": "Day ID",
                "start": datetime.time,
                "end": datetime.time,
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class ScheduleUpdateSchema(BaseModel):
    id                  : str = Field(default=None)
    subjectid           : str = Field(default=None)
    userid              : str = Field(default=None)
    classid             : str = Field(default=None)
    dayid               : str = Field(default=None)
    start               : datetime.time = Field(default= None)
    end                 : datetime.time = Field(default= None)
    dateupdated         : datetime.datetime
    updatedby           : Optional[str] = None
    status              : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "schedule_demo": {
                "id":  "ID",
                "subjectid": "Subject ID",
                "userid": "User ID",
                "classid": "Class ID",
                "dayid": "Day ID",
                "start": datetime.time,
                "end": datetime.time,
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class ScheduleDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "schedule": {
                "id" : "---"
            }
        }

##################### END_TIMETABLES ###########################
