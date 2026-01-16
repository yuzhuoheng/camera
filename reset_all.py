import os
import shutil
import logging
from sqlalchemy import create_engine, text
from minio import Minio
from app.core.config import get_settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reset_script")

settings = get_settings()

def reset_database():
    """清空并重建数据库"""
    logger.info("开始重置数据库...")
    
    # 连接到默认的 postgres 数据库
    postgres_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
    engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
    
    target_db = settings.POSTGRES_DB
    
    with engine.connect() as conn:
        # 终止所有连接到目标数据库的会话
        logger.info(f"正在终止所有连接到 {target_db} 的会话...")
        conn.execute(text(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{target_db}'
            AND pid <> pg_backend_pid();
        """))
        
        # 删除数据库
        logger.info(f"正在删除数据库 {target_db}...")
        conn.execute(text(f"DROP DATABASE IF EXISTS {target_db}"))
        
        # 重新创建数据库
        logger.info(f"正在重新创建数据库 {target_db}...")
        conn.execute(text(f"CREATE DATABASE {target_db}"))
        
    logger.info("数据库重置完成。应用重启后将自动重建表结构。")

def reset_minio():
    """清空 MinIO Bucket"""
    logger.info("开始重置 MinIO...")
    
    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE
    )
    
    bucket_name = settings.MINIO_BUCKET_NAME
    
    if client.bucket_exists(bucket_name):
        logger.info(f"正在清空 Bucket: {bucket_name}")
        # 获取所有对象
        # 注意：Minio 的 remove_objects 需要的是 DeleteObject 列表或简单的对象名迭代器
        # list_objects 返回的是 Object 类实例，直接传给 remove_objects 在某些版本可能报错
        # 稳妥做法是手动提取名称并逐个删除（虽然慢点但兼容性好）或者构造 DeleteObject
        objects = client.list_objects(bucket_name, recursive=True)
        
        for obj in objects:
            client.remove_object(bucket_name, obj.object_name)
            logger.info(f"已删除对象: {obj.object_name}")
            
        logger.info("Bucket 已清空。")
    else:
        logger.info(f"Bucket {bucket_name} 不存在，无需清理。")

if __name__ == "__main__":
    confirm = input("⚠️  警告：此操作将永久删除所有数据（数据库和文件）！\n确认要继续吗？(输入 'yes' 继续): ")
    if confirm.lower() == 'yes':
        try:
            reset_database()
            reset_minio()
            logger.info("✅ 所有数据已成功清除。")
        except Exception as e:
            logger.error(f"❌ 重置过程中发生错误: {e}")
    else:
        logger.info("操作已取消。")
