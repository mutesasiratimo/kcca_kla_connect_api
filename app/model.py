from typing import Optional
from pydantic import BaseModel, Field, EmailStr, validator
import databases, sqlalchemy, datetime, uuid  
from typing import Dict, List, Optional, Union

## Postgres Database 
# TEST_DATABASE_URL = "postgresql://postgres:password@172.16.0.192/klaconnect"
TEST_DATABASE_URL = "postgresql://postgres:password@127.0.0.1/klaconnect"
LOCAL_DATABASE_URL = "postgresql://postgres:4e3w2q11423@0.0.0.0:5432/klaconnect"
LIVE_DATABASE_URL = "postgresql://doadmin:AVNS_SPpMTrX1fz2cZ7tusan@db-postgresql-nyc3-89277-do-user-11136722-0.b.db.ondigitalocean.com:25060/klaconnect?sslmode=require"
# LIVE_DATABASE_URL = "postgresql://doadmin:qoXVNkR3aK6Gaita@db-postgresql-nyc3-44787-do-user-11136722-0.b.db.ondigitalocean.com:25060/klaconnect?sslmode=require"
DATABASE_URL = LOCAL_DATABASE_URL
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData() 


users_table = sqlalchemy.Table(
    "userstable",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("fcmid"        , sqlalchemy.String),
    sqlalchemy.Column("firstname"    , sqlalchemy.String),
    sqlalchemy.Column("lastname"     , sqlalchemy.String),
    sqlalchemy.Column("username"     , sqlalchemy.String),
    sqlalchemy.Column("email"        , sqlalchemy.String),
    sqlalchemy.Column("phone"        , sqlalchemy.String),
    sqlalchemy.Column("mobile"       , sqlalchemy.String),
    sqlalchemy.Column("address"      , sqlalchemy.String),
    sqlalchemy.Column("addresslat"   , sqlalchemy.Float),
    sqlalchemy.Column("addresslong"  , sqlalchemy.Float),
    sqlalchemy.Column("dateofbirth"  , sqlalchemy.DateTime),
    sqlalchemy.Column("password"     , sqlalchemy.String),
    sqlalchemy.Column("gender"       , sqlalchemy.String),
    sqlalchemy.Column("photo"        , sqlalchemy.Text),
    sqlalchemy.Column("nin"          , sqlalchemy.String),
    sqlalchemy.Column("roleid"       , sqlalchemy.String),
    sqlalchemy.Column("iscitizen"    , sqlalchemy.Boolean),
    sqlalchemy.Column("isclerk"      , sqlalchemy.Boolean),
    sqlalchemy.Column("isengineer"   , sqlalchemy.Boolean),
    sqlalchemy.Column("isadmin"      , sqlalchemy.Boolean),
    sqlalchemy.Column("issuperadmin" , sqlalchemy.Boolean),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.String),
)

otps_table = sqlalchemy.Table(
    "otps",
    metadata,
    sqlalchemy.Column("id"            , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("userid"        , sqlalchemy.String),
    sqlalchemy.Column("sessionid"     , sqlalchemy.String),
    sqlalchemy.Column("otpcode"       , sqlalchemy.String),
    sqlalchemy.Column("otpfailedcount", sqlalchemy.Integer),
    sqlalchemy.Column("expiry"        , sqlalchemy.DateTime),
    sqlalchemy.Column("datecreated"   , sqlalchemy.DateTime),
    sqlalchemy.Column("dateupdated"   , sqlalchemy.DateTime),
    sqlalchemy.Column("status"        , sqlalchemy.String),
)

incidentcategories_table = sqlalchemy.Table(
    "incidentcategories",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name"         , sqlalchemy.String),
    sqlalchemy.Column("description"  , sqlalchemy.String),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.String),
)

incidents_table = sqlalchemy.Table(
    "incidentstable",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name"         , sqlalchemy.String),
    sqlalchemy.Column("description"  , sqlalchemy.String),
    sqlalchemy.Column("isemergency"  , sqlalchemy.Boolean),
    sqlalchemy.Column("incidentcategoryid" , sqlalchemy.String),
    sqlalchemy.Column("address"      , sqlalchemy.String),
    sqlalchemy.Column("addresslat"   , sqlalchemy.Float),
    sqlalchemy.Column("addresslong"  , sqlalchemy.Float),
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

reports_table = sqlalchemy.Table(
    "kccareports",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name"         , sqlalchemy.String),
    sqlalchemy.Column("description"  , sqlalchemy.String),
    sqlalchemy.Column("reporttype"   , sqlalchemy.String),
    sqlalchemy.Column("reference"    , sqlalchemy.String),
    sqlalchemy.Column("isemergency"  , sqlalchemy.Boolean),
    sqlalchemy.Column("address"      , sqlalchemy.String),
    sqlalchemy.Column("addresslat"   , sqlalchemy.Float),
    sqlalchemy.Column("addresslong"  , sqlalchemy.Float),
    sqlalchemy.Column("attachment"   , sqlalchemy.Text),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.String),
)

kccareports_table = sqlalchemy.Table(
    "reportskcca",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name"         , sqlalchemy.String),
    sqlalchemy.Column("description"  , sqlalchemy.String),
    sqlalchemy.Column("reporttype"   , sqlalchemy.String),
    sqlalchemy.Column("reference"    , sqlalchemy.String),
    sqlalchemy.Column("isemergency"  , sqlalchemy.Boolean),
    sqlalchemy.Column("address"      , sqlalchemy.String),
    sqlalchemy.Column("addresslat"   , sqlalchemy.Float),
    sqlalchemy.Column("addresslong"  , sqlalchemy.Float),
    sqlalchemy.Column("attachment"   , sqlalchemy.Text),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.String),
)

feedback_table = sqlalchemy.Table(
    "feedback",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("postid"       , sqlalchemy.String),
    sqlalchemy.Column("comment"      , sqlalchemy.String),
    sqlalchemy.Column("attachment"   , sqlalchemy.Text),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.String),
)

likes_table = sqlalchemy.Table(
    "likes",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("postid"       , sqlalchemy.String),
    sqlalchemy.Column("isliked"      , sqlalchemy.Boolean),
    sqlalchemy.Column("userid"       , sqlalchemy.Text),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.String),
)

savedlocations_table = sqlalchemy.Table(
    "savedlocationsnew",
    metadata,
    sqlalchemy.Column("id"             , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("locationname"   , sqlalchemy.String),
    sqlalchemy.Column("locationlat"    , sqlalchemy.Float),
    sqlalchemy.Column("locationlong"   , sqlalchemy.Float),
    sqlalchemy.Column("locationaddress", sqlalchemy.String),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.String),
)

# trips_table = sqlalchemy.Table(
#     "trips",
#     metadata,
#     sqlalchemy.Column("id"             , sqlalchemy.String, primary_key=True),
#     sqlalchemy.Column("startaddress"   , sqlalchemy.Float),
#     sqlalchemy.Column("startlat"    , sqlalchemy.Float),
#     sqlalchemy.Column("startlong"   , sqlalchemy.String),
#     sqlalchemy.Column("destinationaddress", sqlalchemy.String),
#     sqlalchemy.Column("destinationlat"    , sqlalchemy.Float),
#     sqlalchemy.Column("destinationlong"   , sqlalchemy.Float),
#     sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
#     sqlalchemy.Column("createdby"    , sqlalchemy.String),
#     sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
#     sqlalchemy.Column("updatedby"    , sqlalchemy.String),
#     sqlalchemy.Column("status"       , sqlalchemy.String),
# )

user_trips_table = sqlalchemy.Table(
    "triphistory",
    metadata,
    sqlalchemy.Column("id"             , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("startaddress"   , sqlalchemy.String),
    sqlalchemy.Column("startlat"    , sqlalchemy.Float),
    sqlalchemy.Column("startlong"   , sqlalchemy.Float),
    sqlalchemy.Column("destinationaddress", sqlalchemy.String),
    sqlalchemy.Column("destinationlat"    , sqlalchemy.Float),
    sqlalchemy.Column("destinationlong"   , sqlalchemy.Float),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.String),
)

designations_table = sqlalchemy.Table(
    "designations",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("designationname", sqlalchemy.String),
    sqlalchemy.Column("roledescription", sqlalchemy.String),
    sqlalchemy.Column("linemanagerid", sqlalchemy.String),
    sqlalchemy.Column("departmentid" , sqlalchemy.String),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.String),
)

departments_table = sqlalchemy.Table(
    "departments",
    metadata,
    sqlalchemy.Column("id"            , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("departmentname", sqlalchemy.String),
    sqlalchemy.Column("description"   , sqlalchemy.String),
    sqlalchemy.Column("hodid"         , sqlalchemy.String),
    sqlalchemy.Column("datecreated"   , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"     , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"   , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"     , sqlalchemy.String),
    sqlalchemy.Column("status"        , sqlalchemy.String),
)

languages_table = sqlalchemy.Table(
    "languages",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("languagename" , sqlalchemy.String),
    sqlalchemy.Column("shortcode"    , sqlalchemy.String),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.String),
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
    sqlalchemy.Column("status"       , sqlalchemy.String),
)

engine = sqlalchemy.create_engine(
    DATABASE_URL
)
metadata.create_all(engine)

##################### USERS ###########################

class UserSchema(BaseModel):
    id          : str = Field(default=None)
    fcmid       : Optional[str] = None
    firstname   : str = Field(default=None)
    lastname    : str = Field(default= None)
    username    : str = Field(default= None)
    phone       : str = Field(default= None)
    mobile      : str = Field(default= None)
    photo       : str = Field(default= None)
    address     : str = Field(default= None)
    addresslat  : float = Field(default= None)
    addresslong : float = Field(default= None)
    nin         : str = Field(default=None)
    email       : EmailStr = Field(default= None)
    password    : str = Field(default=None)
    gender      : str = Field(default=None)
    dateofbirth : Optional[datetime.datetime] = None
    roleid      : Optional[str] = None
    iscitizen   : bool = Field(default=True)
    isclerk     : bool = Field(default=False)
    isengineer  : bool = Field(default=False)
    isadmin     : bool = Field(default=False)
    issuperadmin: bool = Field(default=False)
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
                "fcmid": "",
                "firstname": "John",
                "lastname": "Doe",
                "username" : "help@bekbrace.com",
                "mobile" : "0775111222",
                "phone" : "0775111222",
                "photo" : "https://picsum.photos/200/300",
                "address": "Kampala, Uganda",
                "addresslat": 0.46666,
                "addresslong": 32.77476,
                "password": "123456",
                "gender": "Male",
                "dateofbirth": "",
                "nin": "",
                "roleid": "1",
                "iscitizen": True,
                "isclerk": False,
                "isengineer": False,
                "isadmin": False,
                "issuperadmin": False,
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class UserUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    fcmid       : Optional[str] = None
    firstname   : str = Field(default=None)
    lastname    : str = Field(default= None)
    username    : str = Field(default= None)
    phone       : str = Field(default= None)
    mobile      : str = Field(default= None)
    photo       : str = Field(default= None)
    address     : str = Field(default= None)
    addresslat  : float = Field(default= None)
    addresslong : float = Field(default= None)
    nin         : str = Field(default=None)
    email       : EmailStr = Field(default= None)
    password    : str = Field(default=None)
    gender      : str = Field(default=None)
    dateofbirth : Optional[datetime.datetime] = None
    roleid      : Optional[str] = None
    iscitizen   : bool = Field(default=True)
    isclerk     : bool = Field(default=False)
    isengineer  : bool = Field(default=False)
    isadmin     : bool = Field(default=False)
    issuperadmin: bool = Field(default=False)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id" : "---",
                "fcmid": "",
                "firstname": "John",
                "lastname": "Doe",
                "username" : "help@bekbrace.com",
                "mobile" : "0775111222",
                "phone" : "0775111222",
                "photo" : "https://picsum.photos/200/300",
                "address": "Kampala, Uganda",
                "addresslat": 0.46666,
                "addresslong": 32.77476,
                "password": "123456",
                "gender": "Male",
                "dateofbirth": "",
                "nin": "",
                "roleid": "1",
                "iscitizen": True,
                "isclerk": False,
                "isengineer": False,
                "isadmin": False,
                "issuperadmin": False,
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class UserUpdatePasswordSchema(BaseModel):
    userid         : str = Field(default=None)
    password       : str = Field(default=None)
    # issuperadmin: bool = Field(default=False)
    class Config:
        orm_mode = True
        the_schema = {
            "rights_demo": {
                "userid": "",
                "password": "",
            }
        }

class UserUpdateProfileSchema(BaseModel):
    id          : str = Field(default=None)
    firstname   : str = Field(default=None)
    lastname    : str = Field(default= None)
    phone       : str = Field(default= None)
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id" : "---",
                "firstname": "John",
                "lastname": "Doe",
                "phone": "0781780862",
            }
        }

class UserUpdateRightsSchema(BaseModel):
    id          : str = Field(default=None)
    iscitizen   : bool = Field(default=True)
    isclerk     : bool = Field(default=False)
    isengineer  : bool = Field(default=False)
    isadmin     : bool = Field(default=False)
    # issuperadmin: bool = Field(default=False)
    class Config:
        orm_mode = True
        the_schema = {
            "rights_demo": {
                "id": "",
                "iscitizen": True,
                "isclerk": False,
                "isengineer": False,
                "isadmin": False,
                # "issuperadmin": False,
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

class UserFcmSchema(BaseModel):
    userid   : str = Field(default= None)
    fcmid    : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "userid" : "userid",
                "fcmid"  : "1234"
            }
        }

class UserSignUpSchema(BaseModel):
    id          : str = Field(..., example="0")
    fcmid       : str = Field(..., example="fmcid")
    firstname   : str = Field(..., example="John")
    lastname    : str = Field(..., example="Doe")
    username    : str = Field(..., example="johndoe")
    email       : EmailStr = Field(..., example="johndoe@email.com")
    password    : str = Field(..., example="johndoe")
    gender      : str = Field(..., example="M")
    address     : str = Field(..., example="Kanjokya House")
    addresslat  : float = Field(..., example=0.23332)
    addresslong : float = Field(..., example=32.23332)
    phone       : str = Field(..., example="+256781777888")
    mobile      : str = Field(..., example="+256781777888")
    photo       : str = Field(..., example="")
    nin         : str = Field(..., example="")
    dateofbirth : str = Field(..., example="1990-03-23")
    iscitizen   : bool = Field(..., example=True)
    isclerk     : bool = Field(..., example=False)
    isengineer  : bool = Field(..., example=False)
    isadmin     : bool = Field(..., example=False)
    issuperadmin: bool = Field(..., example=False)
    status      : str = Field(..., example="1")

##################### END_USERS ###########################

##################### INCIDENT CATEGORIES ###########################
class IncidentCategoriesSchema(BaseModel):
    id           : str = Field(default=None)
    name         : str = Field(default=None)
    description  : str = Field(default= None)
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
                "name": "Name",
                "description": "Description ....",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class IncidentCategoriesUpdateSchema(BaseModel):
    id           : str = Field(default=None)
    name         : str = Field(default=None)
    description  : str = Field(default= None)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id":  "ID",
                "name": "Name",
                "description": "Description",
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class IncidentCategoriesDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "incident_category": {
                "id" : "---"
            }
        }

##################### END_INCIDENT_CATEGORY ###########################

######################## INCIDENT #############################

class IncidentSchema(BaseModel):
    id                  : str = Field(default=None)
    name                : str = Field(default=None)
    description         : str = Field(default= None)
    isemergency         : bool = Field(default= False)
    incidentcategoryid  : str = Field(default= None)
    address             : str = Field(default= None)
    addresslat          : float = Field(default= 0.22222)
    addresslong         : float = Field(default= 0.32888)
    file1               : str = Field(default=None)
    file2               : str = Field(default= None)
    file3               : str = Field(default= None)
    file4               : str = Field(default= None)
    file5               : str = Field(default= None)
    createdby           : Optional[str] = None
    datecreated         : datetime.datetime
    dateupdated         : Optional[datetime.datetime] = None
    updatedby           : Optional[str] = None
    status              : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "incident_demo": {
                "id" : "---",
                "name": "Incident",
                "description": "Incident Details",
                "incidentcategoryid": "Categ -ID",
                "address": "Kampala, Uganda",
                "addresslat": 0.32222,
                "addresslong": 32.3555,
                "isemergency": False,
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

class IncidentUpdateSchema(BaseModel):
    id                  : str = Field(default=None)
    name                : str = Field(default=None)
    description         : str = Field(default= None)
    isemergency         : bool = Field(default= False)
    incidentcategoryid  : str = Field(default= None)
    incidentcategory    : str = Field(default= None)
    address             : str = Field(default= None)
    addresslat          : float = Field(default= 0.22222)
    addresslong         : float = Field(default= 0.32888)
    file1               : str = Field(default=None)
    file2               : str = Field(default= None)
    file3               : str = Field(default= None)
    file4               : str = Field(default= None)
    file5               : str = Field(default= None)
    dateupdated         : Optional[datetime.datetime] = None
    updatedby           : Optional[str] = None
    status              : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "incident_demo": {
                "id" : "---",
                "name": "Incident",
                "description": "Incident",
                "incidentcategoryid": "Categ -ID",
                "incidentcategory": "Pothole",
                "address": "Kampala, Uganda",
                "addresslat": 0.32222,
                "addresslong": 32.3555,
                "isemergency": False,
                "file1": "File",
                "file2": "File",
                "file3": "File",
                "file4": "File",
                "file5": "File",
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class IncidentStatusSchema(BaseModel):
    id                  : str = Field(default=None)
    updatedby           : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "incident_demo": {
                "id" : "---",
                "updatedby": "User ID",
            }
        }

class IncidentUpdateStatusSchema(BaseModel):
    id                  : str = Field(default=None)
    status              : str = Field(default=None)
    updatedby           : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "incident_demo": {
                "id" : "---",
                "status": "1",
                "updatedby": "User ID",
            }
        }

class IncidentDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "incident": {
                "id" : "---"
            }
        }

######################## END INCIDENT #########################

######################## REPORT #############################

class ReportSchema(BaseModel):
    id                  : str = Field(default=None)
    name                : str = Field(default=None)
    description         : str = Field(default= None)
    reporttype                : str = Field(default= None)
    reference           : str = Field(default= None)
    isemergency         : bool = Field(default= False)
    address             : str = Field(default= None)
    addresslat          : float = Field(default= 0.22222)
    addresslong         : float = Field(default= 0.32888)
    attachment          : str = Field(default=None)
    createdby           : Optional[str] = None
    datecreated         : datetime.datetime
    dateupdated         : Optional[datetime.datetime] = None
    updatedby           : Optional[str] = None
    status              : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "report_demo": {
                "id" : "---",
                "name": "Report",
                "description": "Report Details",
                "address": "Kampala, Uganda",
                "reporttype": "Road Works",
                "reference": "REP-0001-27-07",
                "addresslat": 0.32222,
                "addresslong": 32.3555,
                "isemergency": False,
                "attachment": "File",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class ReportUpdateSchema(BaseModel):
    id                  : str = Field(default=None)
    name                : str = Field(default=None)
    description         : str = Field(default= None)    
    reporttype                : str = Field(default= None)
    reference           : str = Field(default= None)
    isemergency         : bool = Field(default= False)
    address             : str = Field(default= None)
    addresslat          : float = Field(default= 0.22222)
    addresslong         : float = Field(default= 0.32888)
    attachment          : str = Field(default=None)
    dateupdated         : Optional[datetime.datetime] = None
    updatedby           : Optional[str] = None
    status              : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "report_demo": {
                "id" : "---",
                "name": "Report",
                "description": "Report Details",
                "reporttype": "Road Works",
                "reference": "REP-0001-27-07",
                "address": "Kampala, Uganda",
                "addresslat": 0.32222,
                "addresslong": 32.3555,
                "isemergency": False,
                "attachment": "File",
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class ReportDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "report": {
                "id" : "---"
            }
        }

class CommentSchema(BaseModel):
    id          : str = Field(default=None)
    postid      : str = Field(default=None)
    comment     : str = Field(default= None)
    attachment  : str = Field(default= None)
    datecreated : Optional[datetime.datetime] = None
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status      : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "comment_demo": {
                "id" : "---",
                "postid": "ID",
                "comment": "Comment",
                "attachment": "File",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class LikeSchema(BaseModel):
    id          : str = Field(default=None)
    postid      : str = Field(default=None)
    userid      : str = Field(default= None)
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status      : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "like_demo": {
                "id" : "---",
                "postid": "ID",
                "userid": "ID",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

######################## END REPORT #########################

##################### SAVED LOCATIONS ###########################
class SavedLocationSchema(BaseModel):
    id              : str = Field(default=None)
    locationname    : str = Field(default=None)
    locationlat     : float = Field(default= None)
    locationlong    : float = Field(default= None)
    locationaddress : str = Field(default= None)
    datecreated     : datetime.datetime
    createdby       : Optional[str] = None
    dateupdated     : Optional[datetime.datetime] = None
    updatedby       : Optional[str] = None
    status          : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id" : "---",
                "locationname": "Home",
                "locationlat": 0.22233,
                "locationlong": 23.44433,
                "locationaddress": "Buziga, Kampala",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class SavedLocationUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    locationname    : float = Field(default=None)
    locationlat     : float = Field(default= None)
    locationlong     : str = Field(default= None)
    locationaddress : str = Field(default= None)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id":  "ID",
                "locationname": "Home",
                "locationlat": 0.22233,
                "locationlong": 23.44433,
                "locationaddress": "Buziga, Kampala",
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class SavedLocationDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "saved_location": {
                "id" : "---"
            }
        }

##################### END_SAVED LOCATIONS ###########################

##################### TRIPS ###########################
class TripSchema(BaseModel):
    id                    : str = Field(default=None)
    startaddress          : str = Field(default=None)
    startlat              : float = Field(default= None)
    startlong             : float = Field(default= None)
    destinationaddress    : str = Field(default=None)
    destinationlat        : float = Field(default= None)
    destinationlong       : float = Field(default= None)
    datecreated           : datetime.datetime
    createdby             : Optional[str] = None
    dateupdated           : Optional[datetime.datetime] = None
    updatedby             : Optional[str] = None
    status                : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id" : "---",
                "startaddress": "Gayaza",
                "startlat": 0.22233,
                "startlong": 23.44433,
                "destinationaddress": "Buziga, Kampala",
                "destinationlat": 0.22233,
                "destinationlong": 23.44433,
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class TripUpdateSchema(BaseModel):
    id                    : str = Field(default=None)
    startaddress          : str = Field(default=None)
    startlat              : float = Field(default= None)
    startlong             : float = Field(default= None)
    destinationaddress    : str = Field(default=None)
    destinationlat        : float = Field(default= None)
    destinationlong       : float = Field(default= None)
    dateupdated           : Optional[datetime.datetime] = None
    updatedby             : Optional[str] = None
    status                : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id":  "ID",
                "startaddress": "Gayaza", 
                "startlat": 0.22233,
                "startlong": 23.44433,
                "destinationaddress": "Buziga, Kampala",
                "destinationlat": 0.22233,
                "destinationlong": 23.44433,
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class TripDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "saved_location": {
                "id" : "---"
            }
        }

##################### END TRIPS ###########################

##################### DESIGNATIONS ###########################
class DesignationSchema(BaseModel):
    id          : str = Field(default=None)
    designationname    : str = Field(default=None)
    roledescription : str = Field(default= None)
    linemanagerid : str = Field(default= None)
    departmentid : str = Field(default= None)
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
                "designationname": "Role",
                "roledescription": "Role Description",
                "linemanagerid": "staff userid",
                "departmentid": "departmentid",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class DesignationUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    designationname    : str = Field(default=None)
    roledescription : str = Field(default= None)
    linemanagerid : str = Field(default= None)
    departmentid : str = Field(default= None)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id":  "ID",
                "designationname": "Role",
                "roledescription": "Role Description",
                "linemanagerid": "staff userid",
                "departmentid": "departmentid",
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class DesignationDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "role": {
                "id" : "---"
            }
        }

##################### END_DESIGNATIONS ###########################

##################### DEPARTMENTS ###########################
class DepartmentSchema(BaseModel):
    id              : str = Field(default=None)
    departmentname  : str = Field(default=None)
    description     : str = Field(default= None)
    hodid           : str = Field(default= None)
    datecreated     : datetime.datetime
    createdby       : Optional[str] = None
    dateupdated     : Optional[datetime.datetime] = None
    updatedby       : Optional[str] = None
    status          : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "department_demo": {
                "id" : "---",
                "departmentname": "Accounts",
                "description": "Finance and Accounting",
                "hodid": "staffid of HOD",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class DepartmentUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    departmentname  : str = Field(default=None)
    description     : str = Field(default= None)
    hodid           : str = Field(default= None)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "user_demo": {
                "id":  "ID",
                "departmentname": "Accounts",
                "description": "Finance and Accounting",
                "hodid": "staffid of HOD",
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class DepartmentDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "department": {
                "id" : "---"
            }
        }

##################### END_DEPARTMENTS ###########################

##################### LANGUAGES ###########################
class LanguageSchema(BaseModel):
    id          : str = Field(default=None)
    languagename: str = Field(default=None)
    shortcode   : str = Field(default= None)
    datecreated : datetime.datetime
    createdby   : Optional[str] = None
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "language_demo": {
                "id" : "---",
                "languagename": "English",
                "shortcode": "ENG",
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class LanguageUpdateSchema(BaseModel):
    id          : str = Field(default=None)
    languagename: str = Field(default=None)
    shortcode   : str = Field(default= None)
    dateupdated : Optional[datetime.datetime] = None
    updatedby   : Optional[str] = None
    status   : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "language_demo": {
                "id":  "ID",
                "languagename": "English",
                "shortcode": "ENG",
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
            }
        }

class LanguageDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "language": {
                "id" : "---"
            }
        }

##################### END_LANGUAGES ###########################

##################### OTPS ###########################
class OtpSchema(BaseModel):
    id               : str = Field(default=None)
    userid           : str = Field(default=None)
    sessionid        : str = Field(default= None)
    otpcode          : str = Field(default=None)
    otpfailedcount   : int = Field(default=0)
    expiry           : Optional[datetime.datetime] = None
    datecreated      : datetime.datetime
    createdby        : Optional[str] = None
    dateupdated      : Optional[datetime.datetime] = None
    updatedby        : Optional[str] = None
    status           : Optional[str] = None
    class Config:
        orm_mode = True
        the_schema = {
            "otp_demo": {
                "id" : "---",
                "userid": "user_id",
                "sessionid": "-",
                "otpfailedcount": 0,
                "otpcode": "xaV$5T",
                "expiry": datetime.datetime,
                "datecreated": datetime.datetime,
                "createdby": "1",
                "dateupdated": None,
                "updatedby": None,
                "status": "1"
            }
        }

class OtpVerifySchema(BaseModel):
    email            : EmailStr = Field(default=None)
    otpcode          : str = Field(default=None)
    password         : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "otp_demo": {
                "email": "user@mail.com",
                "otpcode": "4321",
                "password": "password"
            }
        }

class OtpDeleteSchema(BaseModel):
    id : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "otp": {
                "id" : "---"
            }
        }

##################### END_OTPS ###########################

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


