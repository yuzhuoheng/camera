from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
from app.models.models import User, Album, Photo, Share, UserQuotaLog, UserInvite
from app.core.config import get_settings

settings = get_settings()

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        # 简单的硬编码认证，实际生产环境建议改为数据库验证或环境变量配置
        # 这里仅作示例，使用默认账号 admin / admin
        if username == "admin" and password == "admin":
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
    
    column_list = [User.id, User.nickname, User.storage_used, User.storage_limit, User.created_at]
    column_searchable_list = [User.nickname, User.id]
    column_labels = {
        User.id: "OpenID",
        User.nickname: "昵称",
        User.storage_used: "已用空间 (Bytes)",
        User.storage_limit: "空间限额 (Bytes)",
        User.created_at: "注册时间"
    }
    can_create = False  # 用户通常由微信授权创建

class AlbumAdmin(ModelView, model=Album):
    name = "相册"
    name_plural = "相册管理"
    icon = "fa-solid fa-images"
    
    column_list = [Album.id, Album.name, Album.owner_id, Album.is_default, Album.created_at]
    column_searchable_list = [Album.name, Album.owner_id]
    column_labels = {
        Album.name: "相册名称",
        Album.owner_id: "所有者ID",
        Album.is_default: "默认相册",
        Album.created_at: "创建时间"
    }

class PhotoAdmin(ModelView, model=Photo):
    name = "照片"
    name_plural = "照片管理"
    icon = "fa-solid fa-image"
    
    column_list = [Photo.id, Photo.filename, Photo.size, Photo.owner_id, Photo.created_at]
    column_searchable_list = [Photo.filename, Photo.owner_id]
    column_labels = {
        Photo.filename: "文件名",
        Photo.size: "大小 (Bytes)",
        Photo.owner_id: "上传者ID",
        Photo.created_at: "上传时间"
    }

class QuotaLogAdmin(ModelView, model=UserQuotaLog):
    name = "配额日志"
    name_plural = "配额变动记录"
    icon = "fa-solid fa-chart-line"
    
    column_list = [UserQuotaLog.user_id, UserQuotaLog.change_amount, UserQuotaLog.reason, UserQuotaLog.created_at]
    column_searchable_list = [UserQuotaLog.user_id, UserQuotaLog.reason]
    can_create = False
    can_edit = False

def setup_admin(app, engine):
    authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
    # 使用 base_url 参数设置基础路由前缀
    admin = Admin(app, engine, title="一册一刻 · 管理后台", authentication_backend=authentication_backend, base_url="/cs-server/admin")
    
    admin.add_view(UserAdmin)
    admin.add_view(AlbumAdmin)
    admin.add_view(PhotoAdmin)
    admin.add_view(QuotaLogAdmin)
