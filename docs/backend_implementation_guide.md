# 后端实现指南 (Backend Implementation Guide)

本指南基于 `docs/storage_feature_design.md`，提供了后端所需的 SQL 变更和 Python/FastAPI 代码示例。请将这些更改应用到你的后端项目中。

## 1. 数据库迁移 (SQL Migration)

请在你的数据库中执行以下 SQL 语句。

### 1.1 修改 User 表
```sql
-- 添加存储空间字段
ALTER TABLE users ADD COLUMN storage_used BIGINT DEFAULT 0;
ALTER TABLE users ADD COLUMN storage_limit BIGINT DEFAULT 524288000; -- 500MB

-- 创建索引（可选，如果经常查询配额）
-- CREATE INDEX idx_users_storage ON users(storage_used, storage_limit);
```

### 1.2 创建 UserQuotaLog 表
```sql
CREATE TABLE user_quota_logs (
    id VARCHAR(36) PRIMARY KEY, -- UUID
    user_id VARCHAR(36) NOT NULL,
    change_amount BIGINT NOT NULL,
    current_limit BIGINT NOT NULL,
    reason VARCHAR(50) NOT NULL,
    reference_id VARCHAR(100),
    operator VARCHAR(50) DEFAULT 'system',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 1.3 修改 Photo 表
```sql
-- 添加文件大小字段
ALTER TABLE photos ADD COLUMN size INTEGER DEFAULT 0;
```

---

## 2. 后端代码实现 (Python/FastAPI)

### 2.1 更新模型 (Models)

在 `models.py` (或类似文件) 中更新 Pydantic 模型：

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class User(BaseModel):
    id: str
    # ... 其他字段
    storage_used: int
    storage_limit: int

class UserQuotaLog(BaseModel):
    id: str
    user_id: str
    change_amount: int
    current_limit: int
    reason: str
    reference_id: Optional[str] = None
    operator: str
    created_at: datetime
```

### 2.2 上传接口逻辑 (Upload Logic)

在处理上传的 API (如 `POST /photos`) 中，**替换**原有的逻辑：

```python
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
# 假设你有 get_db 和 get_current_user 依赖
# from dependencies import get_db, get_current_user

router = APIRouter()

@router.post("/photos", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    file: UploadFile = File(...),
    album_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. 获取文件大小 (如果不准确，可能需要先读取到内存或临时文件)
    # file.file.seek(0, 2)
    # file_size = file.file.tell()
    # file.file.seek(0)
    # 注意：上述方法对于大文件可能会消耗内存。
    # 更好的方式是读取 Content-Length (如果不被欺骗) 或流式读取计算。
    # 这里假设我们能获取到准确的 file_size
    file_content = await file.read()
    file_size = len(file_content)
    await file.seek(0) # 重置指针以便上传

    # 2. 数据库原子检查与预扣费 (Critical)
    # 使用原生 SQL 确保并发安全
    stmt = text("""
        UPDATE users 
        SET storage_used = storage_used + :size 
        WHERE id = :uid AND storage_used + :size <= storage_limit
    """)
    result = db.execute(stmt, {"size": file_size, "uid": current_user.id})
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Storage quota exceeded (存储空间不足)"
        )

    try:
        # 3. 上传到 MinIO
        # minio_client.put_object(...)
        # file_url = ...
        
        # 4. 保存 Photo 记录
        # new_photo = Photo(..., size=file_size)
        # db.add(new_photo)
        # db.commit()
        pass # 这里填入你原本的上传逻辑

    except Exception as e:
        # 5. 失败回滚 (Compensation)
        # 必须把预扣的空间还回去
        rollback_stmt = text("""
            UPDATE users 
            SET storage_used = storage_used - :size 
            WHERE id = :uid
        """)
        db.execute(rollback_stmt, {"size": file_size, "uid": current_user.id})
        db.commit()
        raise e

    return {"detail": "Upload successful"}
```

### 2.3 删除接口逻辑 (Delete Logic)

在删除照片的 API 中：

```python
@router.delete("/photos/{photo_id}")
async def delete_photo(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. 查询照片获取大小
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    photo_size = photo.size
    
    # 2. 删除 MinIO 文件
    # minio_client.remove_object(...)

    # 3. 删除数据库记录
    db.delete(photo)
    
    # 4. 释放空间 (原子更新，防止减成负数)
    stmt = text("""
        UPDATE users 
        SET storage_used = GREATEST(0, storage_used - :size)
        WHERE id = :uid
    """)
    db.execute(stmt, {"size": photo_size, "uid": current_user.id})
    
    db.commit()
    return {"detail": "Deleted"}
```

### 2.4 用户信息接口 (User Info)

确保 `GET /auth/me` 返回新的字段：

```python
@router.get("/auth/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user 
    # 确保 Pydantic User 模型中包含了 storage_used 和 storage_limit
```
