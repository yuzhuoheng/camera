# 用户存储空间限制与计费功能设计

## 1. 需求背景
- **现状**：目前用户上传照片无限制，且未记录单张照片大小和用户总占用空间。
- **目标**：
  1.  限制用户的总存储空间。
  2.  在小程序端展示用户已用空间（总览及分相册占用）。
  3.  为将来“存储空间扩容”作为收费点或运营活动（如邀请奖励）打下基础。
  4.  **可追溯性**：确保每一笔空间配额的变动（如购买、奖励、活动）都有据可查，便于客服排查和运营分析。

## 2. 数据库设计变更 (Database Changes)

### 2.1 用户表 (`User`)
需要新增字段来追踪用户的空间使用情况和配额。

| 字段名 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `storage_used` | BigInteger | 0 | 用户当前已使用的存储空间（单位：字节 Byte） |
| `storage_limit` | BigInteger | 524,288,000 (500MB) | 用户当前的存储空间上限（单位：字节 Byte）。作为**缓存字段**存在，用于快速鉴权。 |

> **说明**：使用 `BigInteger` 以支持大容量存储（如 GB/TB 级）。`storage_used` 字段采用**累加/累减**机制，避免每次查询都全表扫描计算。

### 2.2 配额变更流水表 (`UserQuotaLog`) [新增]
用于记录用户存储空间配额的变更历史（账本模式）。

| 字段名 | 类型 | 说明 | 示例 |
| :--- | :--- | :--- | :--- |
| `id` | String | 主键 (UUID) | |
| `user_id` | String | 关联用户 (ForeignKey) | |
| `change_amount` | BigInteger | 变动大小 (正数加，负数减) | `+536870912` (512MB) |
| `current_limit` | BigInteger | 变动后的总额快照 (方便核对) | `1073741824` (1GB) |
| `reason` | String | 变动原因 | `initial_default` (初始), `invite_reward` (邀请), `purchase` (购买) |
| `reference_id` | String | 关联业务ID (可空) | 邀请了谁(user_id) / 订单号(order_id) |
| `operator` | String | 操作人 (system/admin_id) | `system` 或管理员ID |
| `created_at` | DateTime | 变动时间 | |

### 2.3 照片表 (`Photo`)
需要记录单张照片的文件大小。

| 字段名 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `size` | Integer | 0 | 照片文件大小（单位：字节 Byte） |

## 3. 业务逻辑调整 (Business Logic)

### 3.1 照片上传 (Upload Photo)
**流程**：
1.  **接收请求**：获取上传的文件对象。
2.  **前置检查 (UX)**：
    - 前端在上传前应预判 `当前已用 + 选中文件总大小 > 上限`，提前拦截并提示。
3.  **服务端并发控制 (Critical)**：
    - 不在代码中计算 `new_usage = used + size`，而是使用**原子更新 SQL**：
      ```sql
      UPDATE users 
      SET storage_used = storage_used + :file_size 
      WHERE id = :user_id AND storage_used + :file_size <= storage_limit
      ```
    - 如果 `row_count == 0`，则抛出“空间不足”异常。
4.  **执行上传**：将文件上传至 MinIO。
5.  **保存元数据**：
    - 创建 `Photo` 记录时，写入 `size = file_size`。
    - *注意*：由于步骤3已经预扣了空间，如果步骤4或5失败（如MinIO上传失败），必须执行**补偿回滚**：
      `UPDATE users SET storage_used = storage_used - :file_size WHERE id = :user_id`。

### 3.2 照片删除 (Delete Photo)
**流程**：
1.  **查询照片**：获取待删除照片的 `size`。
2.  **执行删除**：从 MinIO 和数据库删除记录。
3.  **更新统计**：
    - 更新 `User` 表：`user.storage_used = user.storage_used - photo_size`。
    - 确保 `storage_used` 不小于 0。

### 3.3 配额变更 (Quota Change) [新增]
当用户的空间上限发生变化（如购买、奖励）时：
1.  **插入流水**：在 `UserQuotaLog` 表插入一条记录，记录 `change_amount`, `reason`, `operator`。
2.  **更新用户**：`user.storage_limit = user.storage_limit + change_amount`。
3.  **事务保证**：以上两步必须在同一个数据库事务中完成。

### 3.4 分布式一致性与孤儿文件 (Consistency)
- **风险**：MinIO 上传成功但 DB 更新失败（或回滚失败）会导致 MinIO 产生孤儿文件。
- **对策**：
  - MVP 阶段：接受少量孤儿文件。
  - 长期方案：实现后台定时任务 (Cron Job)，每天比对 MinIO 对象与数据库 Photo 记录，清理无主的 MinIO 文件。

## 4. 接口与前端展示 (API & Frontend)

### 4.1 用户信息接口 (`GET /auth/me` 或类似)
- **响应增加字段**：
  - `storage_used`: 当前已用空间。
  - `storage_limit`: 总配额。
  - *前端展示*：
    - 进度条形式，如 "已用 120MB / 500MB"。
    - **临界值提示**：当使用率 > 90% 时，进度条变红或弹窗提示扩容。

### 4.2 相册列表/详情接口
- **需求**：展示每个相册的占用空间。
- **实现方式**：
  - 方式 A (实时计算)：在查询 Album 时，关联查询 Photos 并对 `size` 求和 (`SUM(photo.size)`).
  - **建议**：初期采用方式 A，数据库层面做聚合查询即可。

## 5. 未来扩展规划 (Future Roadmap)

### 5.1 付费扩容 (Monetization)
- **逻辑**：用户支付成功后，调用配额变更逻辑。
- **记录**：`UserQuotaLog` 记录 reason='purchase', reference_id=order_no。

### 5.2 邀请奖励 (Growth)
- **逻辑**：邀请新用户注册成功后，给予邀请者额外空间。
- **记录**：`UserQuotaLog` 记录 reason='invite_reward', reference_id=new_user_id。

### 5.3 空间清理
- 提供“大文件清理”或“回收站”功能，帮助用户管理空间。
