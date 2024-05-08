from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from pydantic import BaseModel
from passlib.context import CryptContext
from datetime import datetime, timedelta
# from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import certifi

from market.overview import market_overview
from scanner.scanner import crypto_scanner




# MongoDB connection
# Create a new client and connect to the server
uri = "uri"
client = MongoClient(uri, tlsCAFile = certifi.where())
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)


db = client["mydatabase"]
votes_collection = db["votes"]
users_collection = db["users"]

app = FastAPI()

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Secret key for JWT token encoding and decoding
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(BaseModel):
    username: str
    email: str
    full_name: str = None

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str = None

class Login(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserInDB(User):
    hashed_password: str


def get_user(username: str):
    print("get user "+ username)
    user = users_collection.find_one({"username": username})
    if user:
        return UserInDB(**user)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@app.post("/register/", response_model=User)
async def register(register: RegisterRequest):
    if users_collection.find_one({"username": register.username}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered"
        )
    if users_collection.find_one({"email": register.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
    user = User(username=register.username, email=register.email, full_name=register.full_name)

    user_dict = user.dict()
    user_dict["hashed_password"] = get_password_hash(register.password)
    users_collection.insert_one(user_dict)
    return user


def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


@app.post("/token/", response_model=Token)
async def login(userLogin: Login):
    username = userLogin.username
    password = userLogin.password
    print(username, password)
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}




# ------------------------
# ========================
# -------------------------


class ScanRequest(BaseModel):
    tf: str
    rsiPeriod: int
    rsiMoreThan: bool
    rsiTheshole: float


@app.post("/symbols/{symbol_type}")
async def scan_symbol(request: ScanRequest, symbol_type: str):
    if symbol_type == "crypto":
        return crypto_scanner(request.tf, request.rsiPeriod, request.rsiMoreThan, request.rsiTheshole)
    else:
        raise HTTPException(status_code=404, detail="Symbol type not found")


@app.get("/market/overview")
async def read_vote():
    return market_overview()


@app.get("/")
async def root():
    return {"message": "hello world"}
