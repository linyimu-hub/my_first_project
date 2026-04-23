#创建异步引擎
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker,AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column,Integer,String,DateTime,Text,select
from datetime import datetime
import asyncio
SQLALCHEMY_DATABASE_URL=f"mysql+aiomysql://root:15727624563@Lxy@localhost:3306/f2?charset=utf9mb4"
engine=create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,
    future=True,
    pool_size=10,
    max_overflow=20
)
Base=declarative_base()
class User(Base):
    __tablename__ = "users"
    id = Column(Integer,primary_key=True)
    username=Column(String(50),comment="用户名")
    email = Column(String(100), nullable=False, unique=True, comment="邮箱")
    password = Column(String(255), nullable=False, comment="密码（加密存储）")
    full_name = Column(String(100), nullable=True, comment="真实姓名")
    age = Column(Integer, nullable=True, comment="年龄")
    bio = Column(Text, nullable=True, comment="个人简介")
    created_time = Column(DateTime, default=datetime.now, nullable=False, comment="创建时间")
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False, comment="更新时间")
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
# ==================== 第46-50行：创建异步会话工厂 ====================
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False  # 提交后不过期对象
)   
# ==================== 第52-58行：异步创建表 ====================
async def create_tables():
    """异步创建所有表"""
    async with engine.begin() as conn:
        # run_sync 用于在异步中运行同步代码
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 用户表创建成功！")
# ==================== 第68-90行：异步添加用户 ====================
async def add_user(username: str, email: str, password: str, full_name: str = None, age: int = None, bio: str = None):
    """异步添加用户"""
    async with AsyncSessionLocal() as session:
        # 创建用户对象
        new_user = User(
            username=username,
            email=email,
            password=password,  # 注意：实际应用要加密！
            full_name=full_name,
            age=age,
            bio=bio
        )
        
        # 添加到会话
        session.add(new_user)
        
        # 提交事务
        await session.commit()
        
        # 刷新获取生成的id
        await session.refresh(new_user)
        
        print(f"✅ 添加用户成功: id={new_user.id}, username={new_user.username}, email={new_user.email}")
        return new_user
# ==================== 第92-107行：异步查询所有用户 ====================
async def get_all_users():
    """异步查询所有用户"""
    async with AsyncSessionLocal() as session:
        # 构建查询语句
        stmt = select(User).order_by(User.id)
        
        # 执行查询
        result = await session.execute(stmt)
        
        # 获取所有用户
        users = result.scalars().all()
        
        print(f"📋 共有 {len(users)} 个用户：")
        for user in users:
            print(f"   ID:{user.id} | {user.username} | {user.email} | 年龄:{user.age}")
        
        return users
# ==================== 第109-126行：按ID查询单个用户 ====================
async def get_user_by_id(user_id: int):
    """按ID异步查询用户"""
    async with AsyncSessionLocal() as session:
        # 条件查询
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()  # 获取一个结果或None
        
        if user:
            print(f"🔍 找到用户: {user}")
            return user
        else:
            print(f"❌ 用户 ID={user_id} 不存在")
            return None
# ==================== 第128-147行：按用户名查询用户 ====================
async def get_user_by_username(username: str):
    """按用户名异步查询用户"""
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            print(f"🔍 找到用户: {user}")
            return user
        else:
            print(f"❌ 用户名 '{username}' 不存在")
            return None
# ==================== 第149-169行：更新用户 ====================
async def update_user_email(user_id: int, new_email: str):
    """异步更新用户邮箱"""
    async with AsyncSessionLocal() as session:
        # 先查询用户
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            # 修改字段
            user.email = new_email
            # 提交更改
            await session.commit()
            print(f"✅ 更新成功: ID={user_id} 的新邮箱是 {new_email}")
            return user
        else:
            print(f"❌ 用户 ID={user_id} 不存在")
            return None
# ==================== 第171-189行：删除用户 ====================
async def delete_user(user_id: int):
    """异步删除用户"""
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            await session.delete(user)
            await session.commit()
            print(f"✅ 删除成功: ID={user_id} 的用户已删除")
            return True
        else:
            print(f"❌ 用户 ID={user_id} 不存在")
            return False
# ==================== 第191-202行：批量添加用户 ====================
async def batch_add_users():
    """批量添加测试用户"""
    users_data = [
        {"username": "zhangsan", "email": "zhangsan@example.com", "password": "123456", "full_name": "张三", "age": 25, "bio": "Python开发者"},
        {"username": "lisi", "email": "lisi@example.com", "password": "123456", "full_name": "李四", "age": 30, "bio": "Java开发者"},
        {"username": "wangwu", "email": "wangwu@example.com", "password": "123456", "full_name": "王五", "age": 28, "bio": "前端开发者"},
    ]
    
    for user_data in users_data:
        await add_user(**user_data)
# ==================== 第204-248行：主函数 ====================
async def main():
    """主函数：执行所有操作"""
    print("=" * 50)
    print("MySQL 异步数据库操作演示")
    print("=" * 50)
    
    # 1. 创建表
    print("\n1. 创建数据表...")
    await create_tables()
    
    # 2. 批量添加用户
    print("\n2. 批量添加用户...")
    await batch_add_users()
    
    # 3. 查询所有用户
    print("\n3. 查询所有用户...")
    await get_all_users()
    
    # 4. 按ID查询
    print("\n4. 按ID查询用户(ID=1)...")
    await get_user_by_id(1)
    
    # 5. 按用户名查询
    print("\n5. 按用户名查询用户(username='lisi')...")
    await get_user_by_username("lisi")
    
    # 6. 更新用户
    print("\n6. 更新用户邮箱...")
    await update_user_email(1, "zhangsan_new@example.com")
    
    # 7. 再次查询验证更新
    print("\n7. 验证更新结果...")
    await get_user_by_id(1)
    
    # 8. 删除用户
    print("\n8. 删除用户(ID=3)...")
    await delete_user(3)
    
    # 9. 最终用户列表
    print("\n9. 最终用户列表...")
    await get_all_users()
    
    print("\n" + "=" * 50)
    print("演示完成！")
    print("=" * 50)

# ==================== 第250-252行：运行入口 ====================
if __name__ == "__main__":
    asyncio.run(main())