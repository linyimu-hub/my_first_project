from typing import Annotated
from fastapi import Depends,FastAPI,HTTPException,status
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from pydantic import BaseModel
import jwt
from pwdlib import PasswordHash
from jwt.exceptions import InvalidTokenError
from datetime import datetime, timedelta, timezone
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$argon2id$v=19$m=65536,t=3,p=4$wagCPXjifgvUFBzq4hqe3w$CYaIb8sB+wtD+Vu/P4uod1+Qof8h+1g7bbDlBID48Rc",
        "disabled": False,
    }
}


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None

class User(BaseModel):
    username: str
    email: str  | None=None
    full_name: str|None=None
    disabled: bool|None=None

class UserInDB(User):
    hashed_password: str
#创建密码哈希实例
password_hash=PasswordHash.recommended()
#创建一个虚拟哈希，防止时间攻击
DUMMY_HASH=password_hash.hash("dummypassword")
def verify_password(plain_password: str,hashed_password: str) -> bool:
    return password_hash.verify(plain_password,hashed_password)

def get_password_hash(password: str) -> str:
    return password_hash.hash(password)

def get_user(db,username: str):
    if username in db:
        user_dict=db[username]
        return UserInDB(**user_dict)
    return None
def authenticated_user(fake_db,usrename:str,password: str):
    user=get_user(fake_db,usrename)
    #防止时间攻击:无论用户是否存在,都执行一次相同耗时的密码校验,因为黑客能根据接口相应快慢判断用户是否真实存在
    if not user:
        verify_password(password,DUMMY_HASH)
        return False
    if not verify_password(password,user.hashed_password):
        return False
    return user
#令牌生成
def create_access_token(data:dict,expires_delta:timedelta|None=None):
    #data：要放进 token 的数据，比如 {"sub": "johndoe"}
    to_encode=data.copy()
    if expires_delta:
        expire=datetime.now(timezone.utc)+expires_delta
    else:
        expire=datetime.now(timezone.utc)+timedelta(minutes=15)
    to_encode.update({"exp":expire})
    #jwt.encode：生成签名的 JWT 字符串
    encoded_jwt=jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return encoded_jwt
async def get_current_user(token: Annotated[str,Depends(oauth2_scheme)]):
    credentials_exception=HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 1. 解码 JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 2. 提取用户名（JWT 标准字段 sub）
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        token_data = TokenData(username=username)
        
    except InvalidTokenError:
        # token 无效或过期
        raise credentials_exception
    
    # 3. 从数据库获取用户
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    
    return user
async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """获取当前活跃用户（未被禁用）"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """登录端点：验证用户名密码，返回 JWT token"""
    
    # 1. 验证用户
    user = authenticated_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. 创建 token（30分钟后过期）
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},  # sub 是 JWT 标准字段
        expires_delta=access_token_expires
    )
    
    # 3. 返回 token
    return Token(access_token=access_token, token_type="bearer")

@app.get("/users/me/")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """获取当前用户信息"""
    return current_user

@app.get("/users/me/items/")
async def read_own_items(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """获取当前用户的物品列表"""
    return [{"item_id": "Foo", "owner": current_user.username}]



















