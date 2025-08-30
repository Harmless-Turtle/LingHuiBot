from nonebot import get_driver
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime, Boolean, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, Any, List, Optional
import logging

# 获取配置
driver = get_driver()
config = driver.config

# 数据库配置
DATABASE_URL = getattr(config, "database_url", "mysql+pymysql://user:password@localhost/dbname")

# 创建引擎和会话
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()
Base = declarative_base()

logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.engine = engine
        self.metadata = metadata
        self.inspector = inspect(engine)
    
    def check_table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            return self.inspector.has_table(table_name)
        except SQLAlchemyError as e:
            logger.error(f"检查表 {table_name} 是否存在时出错: {e}")
            return False
    
    def create_table(self, table_name: str, columns: Dict[str, Dict[str, Any]]) -> bool:
        """
        创建表
        
        Args:
            table_name: 表名
            columns: 列定义字典，格式如：
                {
                    "id": {"type": Integer, "primary_key": True, "autoincrement": True},
                    "name": {"type": String(50), "nullable": False},
                    "description": {"type": Text, "nullable": True}
                }
        """
        try:
            if self.check_table_exists(table_name):
                logger.info(f"表 {table_name} 已存在")
                return True
            
            # 构建列定义
            table_columns = []
            for col_name, col_config in columns.items():
                col_type = col_config.get("type", String(255))
                col_args = {k: v for k, v in col_config.items() if k != "type"}
                table_columns.append(Column(col_name, col_type, **col_args))
            
            # 创建表
            table = Table(table_name, self.metadata, *table_columns)
            table.create(self.engine, checkfirst=True)
            
            logger.info(f"表 {table_name} 创建成功")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"创建表 {table_name} 时出错: {e}")
            return False
    
    def drop_table(self, table_name: str) -> bool:
        """删除表"""
        try:
            if not self.check_table_exists(table_name):
                logger.warning(f"表 {table_name} 不存在")
                return False
            
            table = Table(table_name, self.metadata, autoload_with=self.engine)
            table.drop(self.engine)
            
            logger.info(f"表 {table_name} 删除成功")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"删除表 {table_name} 时出错: {e}")
            return False
    
    def add_column(self, table_name: str, column_name: str, column_config: Dict[str, Any]) -> bool:
        """添加列"""
        try:
            if not self.check_table_exists(table_name):
                logger.error(f"表 {table_name} 不存在")
                return False
            
            col_type = column_config.get("type", String(255))
            col_args = {k: v for k, v in column_config.items() if k != "type"}
            
            with self.engine.connect() as conn:
                # 这里需要使用原生SQL，因为SQLAlchemy不直接支持ADD COLUMN
                sql_type = self._get_mysql_type(col_type)
                nullable = "NULL" if col_args.get("nullable", True) else "NOT NULL"
                default = f"DEFAULT '{col_args.get('default', '')}'" if "default" in col_args else ""
                
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type} {nullable} {default}"
                conn.execute(sql)
                conn.commit()
            
            logger.info(f"表 {table_name} 添加列 {column_name} 成功")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"添加列时出错: {e}")
            return False
    
    def drop_column(self, table_name: str, column_name: str) -> bool:
        """删除列"""
        try:
            if not self.check_table_exists(table_name):
                logger.error(f"表 {table_name} 不存在")
                return False
            
            with self.engine.connect() as conn:
                sql = f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
                conn.execute(sql)
                conn.commit()
            
            logger.info(f"表 {table_name} 删除列 {column_name} 成功")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"删除列时出错: {e}")
            return False
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表的列信息"""
        try:
            if not self.check_table_exists(table_name):
                return []
            
            columns = self.inspector.get_columns(table_name)
            return columns
            
        except SQLAlchemyError as e:
            logger.error(f"获取表 {table_name} 列信息时出错: {e}")
            return []
    
    def _get_mysql_type(self, sqlalchemy_type) -> str:
        """将SQLAlchemy类型转换为MySQL类型字符串"""
        type_mapping = {
            Integer: "INT",
            String: "VARCHAR(255)",
            Text: "TEXT",
            DateTime: "DATETIME",
            Boolean: "BOOLEAN"
        }
        
        for sa_type, mysql_type in type_mapping.items():
            if isinstance(sqlalchemy_type, sa_type):
                if hasattr(sqlalchemy_type, 'length') and sqlalchemy_type.length:
                    return f"VARCHAR({sqlalchemy_type.length})"
                return mysql_type
        
        return "VARCHAR(255)"  # 默认类型
    
    def execute_query(self, query: str, params: Optional[Dict] = None):
        """执行自定义查询"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, params or {})
                conn.commit()
                return result
        except SQLAlchemyError as e:
            logger.error(f"执行查询时出错: {e}")
            return None

# 创建数据库管理器实例
db_manager = DatabaseManager()

# 示例使用
def create_user_table():
    """创建用户表示例"""
    columns = {
        "id": {"type": Integer, "primary_key": True, "autoincrement": True},
        "user_id": {"type": String(50), "nullable": False, "unique": True},
        "username": {"type": String(100), "nullable": False},
        "email": {"type": String(255), "nullable": True},
        "created_at": {"type": DateTime, "nullable": False},
        "is_active": {"type": Boolean, "default": True}
    }
    return db_manager.create_table("users", columns)

def create_message_table():
    """创建消息表示例"""
    columns = {
        "id": {"type": Integer, "primary_key": True, "autoincrement": True},
        "user_id": {"type": String(50), "nullable": False},
        "content": {"type": Text, "nullable": False},
        "timestamp": {"type": DateTime, "nullable": False}
    }
    return db_manager.create_table("messages", columns)

# 初始化数据库
def init_database():
    """初始化数据库"""
    try:
        # 创建基础表
        create_user_table()
        create_message_table()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")