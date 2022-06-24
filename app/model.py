import email
from tokenize import Double
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, validator
import databases, sqlalchemy, datetime, uuid  
import os
from enum import Enum
from mimetypes import MimeTypes
from typing import Dict, List, Optional, Union
from starlette.datastructures import UploadFile

from app.utils.errors import WrongFile

## Postgres Database 
LOCAL_DATABASE_URL = "postgresql://postgres:password@127.0.0.1:5432/kccaklaconnect"
# LIVE_DATABASE_URL = "postgresql://timo:password@178.62.198.62:5432/kccaklaconnect"
LIVE_DATABASE_URL = "postgresql://doadmin:qoXVNkR3aK6Gaita@db-postgresql-nyc3-44787-do-user-11136722-0.b.db.ondigitalocean.com:25060/kccaklaconnect?sslmode=require"
DATABASE_URL = LIVE_DATABASE_URL
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData() 


users_table = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id"           , sqlalchemy.String, primary_key=True),
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
    sqlalchemy.Column("isadmin"      , sqlalchemy.Boolean),
    sqlalchemy.Column("issuperadmin" , sqlalchemy.Boolean),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
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
    sqlalchemy.Column("status"        , sqlalchemy.CHAR),
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
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

incidents_table = sqlalchemy.Table(
    "incidents",
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
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

savedlocations_table = sqlalchemy.Table(
    "savedlocations",
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
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

trips_table = sqlalchemy.Table(
    "trips",
    metadata,
    sqlalchemy.Column("id"             , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("startaddress"   , sqlalchemy.Float),
    sqlalchemy.Column("startlat"    , sqlalchemy.Float),
    sqlalchemy.Column("startlong"   , sqlalchemy.String),
    sqlalchemy.Column("destinationaddress", sqlalchemy.String),
    sqlalchemy.Column("destinationlat"    , sqlalchemy.Float),
    sqlalchemy.Column("destinationlong"   , sqlalchemy.Float),
    sqlalchemy.Column("datecreated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"    , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"  , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"    , sqlalchemy.String),
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
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
    sqlalchemy.Column("status"       , sqlalchemy.CHAR),
)

departments_table = sqlalchemy.Table(
    "departments",
    metadata,
    sqlalchemy.Column("id"            , sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("departmentname", sqlalchemy.String),
    sqlalchemy.Column("description"   , sqlalchemy.String),
    sqlalchemy.Column("hodid      "   , sqlalchemy.String),
    sqlalchemy.Column("datecreated"   , sqlalchemy.DateTime),
    sqlalchemy.Column("createdby"     , sqlalchemy.String),
    sqlalchemy.Column("dateupdated"   , sqlalchemy.DateTime),
    sqlalchemy.Column("updatedby"     , sqlalchemy.String),
    sqlalchemy.Column("status"        , sqlalchemy.CHAR),
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
    sqlalchemy.Column("schoolid"     , sqlalchemy.String),
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

##################### USERS ###########################

class UserSchema(BaseModel):
    id          : str = Field(default=None)
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
                "isadmin": False,
                "issuperadmin": False,
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
                "dateupdated": datetime.datetime,
                "updatedby": None,
                "status": "1"
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

##################### SAVED LOCATIONS ###########################
class SavedLocationSchema(BaseModel):
    id              : str = Field(default=None)
    locationname    : str = Field(default=None)
    locationlat     : str = Field(default= None)
    locationlong     : str = Field(default= None)
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
    locationname    : str = Field(default=None)
    locationlat     : str = Field(default= None)
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
    startlat              : str = Field(default= None)
    startlong             : str = Field(default= None)
    destinationaddress    : str = Field(default=None)
    destinationlat        : str = Field(default= None)
    destinationlong       : str = Field(default= None)
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
    startlat              : str = Field(default= None)
    startlong             : str = Field(default= None)
    destinationaddress    : str = Field(default=None)
    destinationlat        : str = Field(default= None)
    destinationlong       : str = Field(default= None)
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
    userid           : str = Field(default=None)
    otpcode          : str = Field(default=None)
    class Config:
        orm_mode = True
        the_schema = {
            "otp_demo": {
                "userid": "user_id",
                "otpcode": "4321"
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

##################### MAILING ###########################

class MultipartSubtypeEnum(Enum):
    """
    for more info about Multipart subtypes visit:
        https://en.wikipedia.org/wiki/MIME#Multipart_subtypes
    """

    mixed = 'mixed'
    digest = 'digest'
    alternative = 'alternative'
    related = 'related'
    report = 'report'
    signed = 'signed'
    encrypted = 'encrypted'
    form_data = 'form-data'
    mixed_replace = 'x-mixed-replace'
    byterange = 'byterange'

class MessageSchema(BaseModel):
    recipients: List[EmailStr]
    attachments: List[Union[UploadFile, Dict, str]] = []
    subject: str = ''
    body: Optional[Union[str, list]] = None
    template_body: Optional[Union[list, dict]] = None
    html: Optional[Union[str, List, Dict]] = None
    cc: List[EmailStr] = []
    bcc: List[EmailStr] = []
    reply_to: List[EmailStr] = []
    charset: str = 'utf-8'
    subtype: Optional[str] = None
    multipart_subtype: MultipartSubtypeEnum = MultipartSubtypeEnum.mixed
    headers: Optional[Dict] = None

    @validator('attachments')
    def validate_file(cls, v):
        temp = []
        mime = MimeTypes()

        for file in v:
            file_meta = None
            if isinstance(file, dict):
                keys = file.keys()
                if 'file' not in keys:
                    raise WrongFile('missing "file" key')
                file_meta = dict.copy(file)
                del file_meta['file']
                file = file['file']
            if isinstance(file, str):
                if os.path.isfile(file) and os.access(file, os.R_OK) and validate_path(file):
                    mime_type = mime.guess_type(file)
                    f = open(file, mode='rb')
                    _, file_name = os.path.split(f.name)
                    u = UploadFile(file_name, f, content_type=mime_type[0])
                    temp.append((u, file_meta))
                else:
                    raise WrongFile('incorrect file path for attachment or not readable')
            elif isinstance(file, UploadFile):
                temp.append((file, file_meta))
            else:
                raise WrongFile('attachments field type incorrect, must be UploadFile or path')
        return temp

    @validator('subtype')
    def validate_subtype(cls, value, values, config, field):
        """Validate subtype field."""
        if values['template_body']:
            return 'html'
        return value

    class Config:
        arbitrary_types_allowed = True


def validate_path(path):
    cur_dir = os.path.abspath(os.curdir)
    requested_path = os.path.abspath(os.path.relpath(path, start=cur_dir))
    common_prefix = os.path.commonprefix([requested_path, cur_dir])
    return common_prefix == cur_dir


class EmailSchema(BaseModel):
    email: List[EmailStr]

################### END MAILING #########################

