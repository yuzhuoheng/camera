import os
import sys
import argparse

# Add the project root to the sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import func
from app.core.database import SessionLocal
from app.models.models import User, Album, Photo

def main(direction: str):
    db = SessionLocal()
    
    if direction == "http":
        source_prefix = "https://"
        target_prefix = "http://"
    elif direction == "https":
        source_prefix = "http://"
        target_prefix = "https://"
    else:
        print("无效的方向参数。只能是 'http' 或 'https'")
        return

    try:
        print(f"开始将数据库中的 {source_prefix} 转换为 {target_prefix} ...")

        # 1. 更新 User.avatar_url
        users_updated = db.query(User).filter(User.avatar_url.like(f'{source_prefix}%')).update({
            User.avatar_url: func.replace(User.avatar_url, source_prefix, target_prefix)
        }, synchronize_session=False)
        print(f"已更新 {users_updated} 个用户的头像地址")

        # 2. 更新 Album.cover_url
        albums_updated = db.query(Album).filter(Album.cover_url.like(f'{source_prefix}%')).update({
            Album.cover_url: func.replace(Album.cover_url, source_prefix, target_prefix)
        }, synchronize_session=False)
        print(f"已更新 {albums_updated} 个相册的封面地址")

        # 3. 更新 Photo.url
        photos_url_updated = db.query(Photo).filter(Photo.url.like(f'{source_prefix}%')).update({
            Photo.url: func.replace(Photo.url, source_prefix, target_prefix)
        }, synchronize_session=False)
        print(f"已更新 {photos_url_updated} 张照片的原图地址")

        # 4. 更新 Photo.thumbnail_url
        photos_thumb_updated = db.query(Photo).filter(Photo.thumbnail_url.like(f'{source_prefix}%')).update({
            Photo.thumbnail_url: func.replace(Photo.thumbnail_url, source_prefix, target_prefix)
        }, synchronize_session=False)
        print(f"已更新 {photos_thumb_updated} 张照片的缩略图地址")

        # 提交更改
        db.commit()
        print("所有转换完成！")

    except Exception as e:
        db.rollback()
        print(f"发生错误，已回滚: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="转换数据库中的图片地址前缀 (HTTP/HTTPS)")
    parser.add_argument(
        "--to", 
        choices=["http", "https"], 
        default="http", 
        help="转换目标协议，可选 'http' 或 'https'，默认转为 'http'"
    )
    args = parser.parse_args()
    main(args.to)
