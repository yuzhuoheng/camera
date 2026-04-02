from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from app.models.models import User, Album, Photo, UserQuotaLog
from app.core.config import get_settings

settings = get_settings()

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        # 简单的硬编码认证，实际生产环境建议改为数据库验证或环境变量配置
        # 更新账号为 yuzhuoheng / jx665389=
        if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
            request.session.update({"token": "admin_token"})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        return bool(token)

class UserAdmin(ModelView, model=User):
    name = "用户"
    name_plural = "用户管理"
    icon = "fa-solid fa-user"

    column_list = [User.id, User.nickname, User.last_login_at, "album_count", "photo_count", User.storage_used, User.storage_limit, User.created_at]
    column_details_list = [User.id, User.nickname, User.last_login_at, User.storage_used, User.storage_limit, User.created_at, User.albums, User.quota_logs]
    column_searchable_list = [User.nickname, User.id]
    column_labels = {
        User.id: "OpenID",
        User.nickname: "昵称",
        User.last_login_at: "最近登录时间",
        "album_count": "相册数",
        "photo_count": "照片数",
        User.storage_used: "已用空间 (Bytes)",
        User.storage_limit: "空间限额 (Bytes)",
        User.created_at: "注册时间"
    }
    can_view_details = True
    can_create = False
    can_edit = False
    can_delete = False

class AlbumAdmin(ModelView, model=Album):
    name = "相册"
    name_plural = "相册管理"
    icon = "fa-solid fa-images"

    column_list = [Album.id, Album.name, Album.owner_id, "photo_count", Album.is_default, Album.created_at]
    column_details_list = [Album.id, Album.name, Album.owner_id, "photo_count", Album.is_default, Album.created_at, Album.photos]
    column_searchable_list = [Album.name, Album.owner_id]
    column_labels = {
        Album.id: "相册ID",
        Album.name: "相册名称",
        Album.owner_id: "所有者ID",
        "photo_count": "照片数",
        Album.is_default: "默认相册",
        Album.created_at: "创建时间"
    }
    can_view_details = True
    can_create = False
    can_edit = False
    can_delete = False

class PhotoAdmin(ModelView, model=Photo):
    name = "照片"
    name_plural = "照片管理"
    icon = "fa-solid fa-image"

    column_list = [Photo.id, Photo.filename, Photo.album_id, Photo.size, Photo.owner_id, Photo.created_at]
    column_details_list = [Photo.id, Photo.filename, Photo.url, Photo.thumbnail_url, Photo.album_id, Photo.size, Photo.owner_id, Photo.created_at]
    column_searchable_list = [Photo.filename, Photo.owner_id]
    column_labels = {
        Photo.id: "照片ID",
        Photo.filename: "文件名",
        Photo.album_id: "所属相册ID",
        Photo.url: "原图URL",
        Photo.thumbnail_url: "缩略图URL",
        Photo.size: "大小 (Bytes)",
        Photo.owner_id: "上传者ID",
        Photo.created_at: "上传时间"
    }
    can_view_details = True
    can_create = False
    can_edit = False
    can_delete = False

class QuotaLogAdmin(ModelView, model=UserQuotaLog):
    name = "配额日志"
    name_plural = "配额变动记录"
    icon = "fa-solid fa-chart-line"

    column_list = [UserQuotaLog.user_id, UserQuotaLog.change_amount, UserQuotaLog.current_limit, UserQuotaLog.reason, UserQuotaLog.reference_id, UserQuotaLog.operator, UserQuotaLog.created_at]
    column_searchable_list = [UserQuotaLog.user_id, UserQuotaLog.reason]
    can_view_details = True
    can_create = False
    can_edit = False
    can_delete = False

def setup_admin(app, engine):
    authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
    # 使用 base_url 参数设置基础路由前缀
    admin = Admin(app, engine, title="一册一刻 · 管理后台", authentication_backend=authentication_backend, base_url="/cs-server/admin")
    
    admin.add_view(UserAdmin)
    admin.add_view(AlbumAdmin)
    admin.add_view(PhotoAdmin)
    admin.add_view(QuotaLogAdmin)
