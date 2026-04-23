'''from typing import Annotated
from fastapi import Depends,FastAPI,HTTPException,Query
from sqlmodel import SQLModel,Field,Session,create_engine,select
class Hero(SQLModel,table=True):
    id: int|None=Field(default=None,primary_key=True)
    name:str|None=Field(index=True)
    age:int|None=Field(default=None,index=True)
    secret_name:str

sqlite_file_name="database.db"
sqlite_url=f"sqlite:///{sqlite_file_name}"
#使用 check_same_thread=False 可以让 FastAPI 在不同线程中使用同一个 SQLite 数据库
connect_args={"check_same_thread":False}
engine=create_engine(sqlite_url,connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]
# Code above omitted 👆

app = FastAPI()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Code below omitted 👇
# Code above omitted 👆

@app.post("/heroes/")
def create_hero(hero: Hero, session: SessionDep) -> Hero:
    session.add(hero)
    session.commit()
    session.refresh(hero)
    return hero



@app.get("/heroes/")
def read_heroes(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[Hero]:
    heroes = session.exec(select(Hero).offset(offset).limit(limit)).all()
    return heroes

# Code above omitted 👆

@app.get("/heroes/{hero_id}")
def read_hero(hero_id: int, session: SessionDep) -> Hero:
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    return hero



@app.delete("/heroes/{hero_id}")
def delete_hero(hero_id: int, session: SessionDep):
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    session.delete(hero)
    session.commit()
    return {"ok": True}'''

# 1. 导入必要的模块
'''from collections.abc import AsyncIterable
from fastapi import FastAPI
from pydantic import BaseModel

# 2. 创建FastAPI应用
app = FastAPI()

# 3. 定义数据的格式（类似合同）
class Item(BaseModel):
    name: str
    description: str | None  # | None 表示可以不填

# 4. 准备好数据
items = [
    Item(name="Plumbus", description="一个多功能家用设备"),
    Item(name="Portal Gun", description="可以开传送门的枪"),
    Item(name="Meeseeks Box", description="召唤Meeseeks的盒子"),
]

# 5. 流式传输的API
@app.get("/items/stream")
async def stream_items() -> AsyncIterable[Item]:
    # AsyncIterable[Item] 意思是：
    # "我会异步地、一个一个地给你Item类型的数据"
    
    for item in items:  # 遍历每个数据
        yield item       # 发一个出去，继续下一个
        
# 当你访问 /items/stream 时：
# 1. 客户端看到第一个 {"name": "Plumbus", ...}
# 2. 紧接着看到第二个 {"name": "Portal Gun", ...}
# 3. 紧接着看到第三个 ...
'''
'''from fastapi import FastAPI
from fastapi.sse import EventSourceResponse  # 1. 导入SSE模块

app = FastAPI()

@app.get("/stream", response_class=EventSourceResponse)  # 2. 设置响应类型
async def stream():
    for i in range(10):
        yield {"data": f"消息{i}"}  # 3. 用yield发送'''
'''from fastapi import FastAPI

app = FastAPI(
    # 基本信息
    title="超级英雄管理API",
    summary="管理漫威和DC英雄",
    description="""
    # 欢迎使用英雄API
    
    这个API让你可以：
    * **创建**新英雄
    * **查询**英雄信息
    * **更新**英雄数据
    * **删除**英雄
    
    > 注意：所有数据都是示例数据
    """,
    version="2.5.0",
    
    # 服务条款
    terms_of_service="https://example.com/terms",
    
    # 联系方式
    contact={
        "name": "英雄API团队",
        "url": "https://example.com/support",
        "email": "api@example.com",
    },
    
    # 许可证
    license_info={
        "name": "MIT License",
        "identifier": "MIT",
    },
)

@app.get("/heroes")
async def get_heroes():
    return [{"name": "Iron Man"}, {"name": "Spider Man"}]'''
from fastapi import FastAPI

# 定义标签的元数据
tags_metadata = [
    {
        "name": "users",                    # 标签名
        "description": "用户相关操作。**登录**功能也在这里。",  # 描述
    },
    {
        "name": "items",
        "description": "商品管理。很_高级_的功能。",
        "externalDocs": {                   # 外部文档链接
            "description": "商品API详细文档",
            "url": "https://example.com/items-docs",
        },
    },
]

app = FastAPI(openapi_tags=tags_metadata)  # 传入标签元数据

# 使用标签
@app.get("/users/", tags=["users"])
async def get_users():
    return [{"name": "张三"}]

@app.get("/items/", tags=["items"])
async def get_items():
    return [{"name": "手机"}, {"name": "电脑"}]