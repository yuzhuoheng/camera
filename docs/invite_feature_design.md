# 邀请裂变扩容功能设计 (Invite & Earn Storage)

## 1. 需求背景 (Background)
为了低成本获取新用户并提升现有用户的活跃度，计划推出“邀请好友得空间”的裂变活动。利用存储空间作为核心激励，鼓励老用户通过微信社交关系链邀请新用户注册。

## 2. 核心规则 (Core Rules)
- **奖励对象**：邀请人（Inviter）和被邀请人（Invitee）。
- **触发条件**：被邀请人必须是**从未注册过的新用户**，且通过邀请链接/海报首次进入并完成登录。
- **奖励内容**：
  - **邀请人**：每成功邀请 1 人，奖励 **100MB** 永久空间。
  - **被邀请人**：注册即得初始空间 + **100MB** 额外奖励空间。
- **限制条件**：
  - 单个用户每天最多通过邀请获得 1GB 奖励（防止恶意刷量）。
  - 单个用户总计通过邀请获得的奖励上限为 5GB。

## 3. 数据库设计 (Database Design)

### 3.1 新增表：邀请记录 (`UserInvite`)
用于记录邀请关系，防止重复邀请和循环邀请。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | String | UUID 主键 |
| `inviter_id` | String | 邀请人 ID (ForeignKey -> User.id) |
| `invitee_id` | String | 被邀请人 ID (ForeignKey -> User.id) |
| `status` | String | 状态：`completed` (已完成), `fraud` (疑似欺诈) |
| `reward_granted` | Boolean | 奖励是否已发放 (True/False) |
| `created_at` | DateTime | 邀请时间 |

> **唯一性约束**：`invitee_id` 必须唯一。一个用户只能被邀请一次。

### 3.2 现有表变更
- **UserQuotaLog**：继续使用现有的配额流水表。
  - `reason` 字段新增枚举值：`invite_reward_inviter` (邀请人奖励), `invite_reward_invitee` (新人奖励)。
  - `reference_id` 字段记录对应的 `UserInvite.id`。

## 4. 业务流程与接口 (Workflows & APIs)

### 4.1 生成邀请 (Generate Invite)
- **前端逻辑**：
  - 用户在“设置”页点击“邀请好友”。
  - 调用 `wx.onShareAppMessage`。
  - **分享路径**：`/pages/index/index?invite_code={current_user_id}`。
  - 无需后端专门接口，直接利用 User ID 作为邀请码。

### 4.2 接受邀请与注册 (Accept & Register)
这是核心流程，发生在 `POST /auth/login` 接口中。

**请求参数变更**：
- 新增可选参数 `invite_code` (String)。

**后端逻辑 (Python)**：
1.  **验证 Code**：调用微信 API 获取 openid。
2.  **查找用户**：查询数据库是否存在该 openid。
3.  **分支 A：老用户 (已存在)**
    - 忽略 `invite_code`。
    - 正常返回登录 Token。
4.  **分支 B：新用户 (不存在)**
    - 创建新用户 (`User`)。
    - **检查邀请码**：
      - 如果 `invite_code` 存在且有效（对应的 User 存在，且不是自己）：
      - **记录邀请关系**：插入 `UserInvite` 表。
      - **发放奖励 (事务)**：
        1.  **给新人 (Invitee)**：
            - `storage_limit` += 100MB。
            - 插入 `UserQuotaLog` (reason=`invite_reward_invitee`).
        2.  **给邀请人 (Inviter)**：
            - 检查邀请人今日/总计奖励是否超限。
            - **奖励补齐逻辑**：若未超限，计算 `actual_reward = min(100MB, daily_limit - today_gained)`。
            - 只要 `actual_reward > 0`，则执行：
              - `storage_limit` += `actual_reward`。
              - 插入 `UserQuotaLog` (reason=`invite_reward_inviter`, amount=`actual_reward`).
              - 更新 `UserInvite.reward_granted = True`。
    - 返回登录 Token。

### 4.3 邀请记录查询 (Query Invites)
供前端展示“由于邀请了谁，获得了多少空间”。

- **接口**：`GET /invites`
- **响应**：
  ```json
  {
    "total_reward": 524288000, // 总获得奖励 (Bytes)
    "invite_count": 5,         // 成功邀请人数
    "history": [
      {
        "invitee_nickname": "User***", // 脱敏显示
        "invitee_avatar": "...",
        "reward_amount": 104857600,
        "created_at": "2023-10-27T10:00:00"
      }
    ]
  }
  ```

## 5. 前端界面 (Frontend UI)

### 5.1 设置页入口
- 在“存储空间”卡片下方增加 Banner 或 列表项：“🎁 邀请好友，免费扩容”。

### 5.2 邀请详情页 (`pages/invite/invite`)
- **顶部**：显示当前已获得的奖励总额。
- **中部**：
  - “立即邀请”按钮（触发分享）。
  - 进度条：显示距离上限（5GB）还有多少。
- **底部**：邀请记录列表。

### 5.3 落地页处理 (`app.js` & `index.js`)
- **场景**：用户点击卡片进入。
- **逻辑**：
  - `onLaunch` / `onLoad` 解析 `options.query.invite_code`。
  - 将 `invite_code` 存入 `wx.setStorageSync('pending_invite_code', code)`。
  - 用户点击登录时，读取缓存中的 `invite_code` 传给后端。
  - 登录成功后，清除缓存。

## 6. 安全与防刷 (Security)
1.  **同人校验**：后端检查 `inviter_id != invitee_id`。
2.  **上限控制**：严格执行每日 1GB、总量 5GB 的限制。
3.  **风险控制**（二期）：
    - 如果发现大量新用户注册后无任何上传行为，可能是僵尸号。
    - 可增加策略：新用户需上传至少 1 张照片，邀请人才发放奖励（延迟到账）。
    - *MVP 阶段暂不实现此风控，优先跑通流程。*
