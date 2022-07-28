## This file handles signing, encoding, decoding and returning JWTs
import time
import jwt
from decouple import config

JWT_SECRET = config("secret")
JWT_ALGORITHM = config("algorithm")

def token_response(token: str):
    """ Function returns generated tokens """
    return token

def signJWT(userID : str):
    """ Function for signing the JWT String"""
    payload = {
       "userID": userID,
       "expiry": int(time.time() + 60000)
    }
    token  = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token_response(token)

def decodeJWT(token: str):
    decode_token = jwt.decode(token, JWT_SECRET, algorithm=JWT_ALGORITHM)
    try: 
        return decode_token if decode_token["expires"] >= time.time() else None
    except:
        return {}