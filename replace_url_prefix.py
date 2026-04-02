import os
import sys
import argparse
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import func
from app.core.database import SessionLocal
from app.models.models import User, Album, Photo


def main(
    direction: Optional[str],
    source_prefix: Optional[str] = None,
    target_prefix: Optional[str] = None,
    dry_run: bool = False
):
    db = SessionLocal()

    if source_prefix and target_prefix:
        source_prefix = source_prefix.strip()
        target_prefix = target_prefix.strip()
    else:
        if direction == "http":
            source_prefix = "https://"
            target_prefix = "http://"
        elif direction == "https":
            source_prefix = "http://"
            target_prefix = "https://"
        else:
            print("参数无效。请使用 --to 或同时提供 --from-prefix 和 --to-prefix")
            return

    try:
        print(f"开始将数据库中的 {source_prefix} 转换为 {target_prefix} ...")
        like_pattern = f"{source_prefix}%"

        users_count = db.query(User).filter(User.avatar_url.like(like_pattern)).count()
        albums_count = db.query(Album).filter(Album.cover_url.like(like_pattern)).count()
        photos_url_count = db.query(Photo).filter(Photo.url.like(like_pattern)).count()
        photos_thumb_count = db.query(Photo).filter(Photo.thumbnail_url.like(like_pattern)).count()

        if dry_run:
            total = users_count + albums_count + photos_url_count + photos_thumb_count
            print("Dry Run 模式：仅统计，不写入数据库")
            print(f"将更新 {users_count} 个用户的头像地址")
            print(f"将更新 {albums_count} 个相册的封面地址")
            print(f"将更新 {photos_url_count} 张照片的原图地址")
            print(f"将更新 {photos_thumb_count} 张照片的缩略图地址")
            print(f"总计将更新 {total} 条记录")
            return

        users_updated = db.query(User).filter(User.avatar_url.like(like_pattern)).update({
            User.avatar_url: func.replace(User.avatar_url, source_prefix, target_prefix)
        }, synchronize_session=False)
        print(f"已更新 {users_updated} 个用户的头像地址")

        albums_updated = db.query(Album).filter(Album.cover_url.like(like_pattern)).update({
            Album.cover_url: func.replace(Album.cover_url, source_prefix, target_prefix)
        }, synchronize_session=False)
        print(f"已更新 {albums_updated} 个相册的封面地址")

        photos_url_updated = db.query(Photo).filter(Photo.url.like(like_pattern)).update({
            Photo.url: func.replace(Photo.url, source_prefix, target_prefix)
        }, synchronize_session=False)
        print(f"已更新 {photos_url_updated} 张照片的原图地址")

        photos_thumb_updated = db.query(Photo).filter(Photo.thumbnail_url.like(like_pattern)).update({
            Photo.thumbnail_url: func.replace(Photo.thumbnail_url, source_prefix, target_prefix)
        }, synchronize_session=False)
        print(f"已更新 {photos_thumb_updated} 张照片的缩略图地址")

        db.commit()
        print("所有转换完成！")

    except Exception as e:
        db.rollback()
        print(f"发生错误，已回滚: {e}")
    finally:
        db.close()


def run_cli():
    parser = argparse.ArgumentParser(description="批量替换数据库中的图片地址前缀")
    parser.add_argument(
        "--to",
        choices=["http", "https"],
        default=None,
        help="按协议转换：to=http 表示 https:// -> http://，to=https 表示 http:// -> https://"
    )
    parser.add_argument(
        "--from-prefix",
        default=None,
        help="自定义源前缀，例如 https://yuzhuoheng.xyz"
    )
    parser.add_argument(
        "--to-prefix",
        default=None,
        help="自定义目标前缀，例如 https://www.yuzhuoheng.xyz"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅统计将被更新的记录数量，不写入数据库"
    )
    args = parser.parse_args()
    if (args.from_prefix and not args.to_prefix) or (args.to_prefix and not args.from_prefix):
        print("参数无效：--from-prefix 和 --to-prefix 必须同时提供")
        sys.exit(1)
    if args.from_prefix and args.to_prefix:
        main(None, args.from_prefix, args.to_prefix, args.dry_run)
    else:
        main(args.to if args.to else "http", dry_run=args.dry_run)


if __name__ == "__main__":
    run_cli()
