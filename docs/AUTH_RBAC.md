# 账号、组织空间与 RBAC

第二阶段第 9 项为智链天河工作台增加正式账号、组织空间和基于角色的访问控制，同时保留匿名浏览器工作区作为兼容入口。

## 安全模型

登录会话采用：

- 服务端随机生成的高熵会话令牌；
- 数据库只保存令牌的 SHA-256 哈希；
- 浏览器使用 `HttpOnly`、`SameSite=Lax` Cookie 保存会话令牌；
- 组织写操作使用独立 CSRF 令牌；
- CSRF 令牌必须同时出现在浏览器 Cookie 和 `X-CSRF-Token` 请求头中；
- 密码使用带 16 字节随机盐的 `scrypt` 哈希，不保存明文密码；
- 登录失败统一提示“邮箱或密码不正确”，不暴露账号是否存在。

公开 HTTPS 部署必须设置：

```env
AUTH_COOKIE_SECURE=true
```

当前账号界面按同源部署设计。建议让前端和 FastAPI 通过同一 HTTPS 域名访问，不要直接把 Cookie 登录接口暴露给任意跨域来源。

## 环境变量

```env
AUTH_ALLOW_REGISTRATION=true
PASSWORD_MIN_LENGTH=10
SESSION_TTL_HOURS=168
AUTH_COOKIE_SECURE=false
SESSION_COOKIE_NAME=zhilink_session
CSRF_COOKIE_NAME=zhilink_csrf
```

说明：

- `AUTH_ALLOW_REGISTRATION=false` 可关闭公开注册，但不会影响现有用户登录。
- `PASSWORD_MIN_LENGTH` 会限制在 8–64 之间，密码本身最多 128 字符。
- `SESSION_TTL_HOURS` 会限制在 1–720 小时之间。
- `AUTH_COOKIE_SECURE=true` 后，浏览器只会通过 HTTPS 发送登录 Cookie。
- 修改 Cookie 名称会使现有浏览器会话失效。

## 组织角色

系统提供四种角色：

| 角色 | 主要权限 |
|---|---|
| `owner` 所有者 | 管理所有角色、组织设置、项目、版本恢复和删除 |
| `admin` 管理员 | 管理编辑者/只读成员，创建、编辑、恢复和删除项目 |
| `editor` 编辑者 | 读取、创建、编辑项目并恢复历史版本，不能删除项目或管理成员 |
| `viewer` 只读成员 | 读取项目和版本历史，不能写入或恢复 |

约束：

- 只有所有者可以授予或管理 `owner`、`admin`。
- 管理员不能修改其他管理员或所有者。
- 组织必须始终至少保留一名所有者。
- 前端会按角色隐藏不可用按钮，但真正权限始终由后端校验。

## 注册与登录

注册时系统会同时创建：

1. 用户账号；
2. 默认组织；
3. 该用户的 `owner` 成员关系；
4. 登录会话和 CSRF 令牌。

接口：

```text
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/session
POST /api/auth/logout
```

注册请求示例：

```json
{
  "email": "owner@example.com",
  "password": "a long unique passphrase",
  "display_name": "项目负责人",
  "organization_name": "天河企业服务团队"
}
```

## 组织与成员接口

```text
GET    /api/organizations
POST   /api/organizations
GET    /api/organizations/{organization_id}/members
POST   /api/organizations/{organization_id}/members
PUT    /api/organizations/{organization_id}/members/{user_id}
DELETE /api/organizations/{organization_id}/members/{user_id}
POST   /api/organizations/{organization_id}/claim-workspace-projects
```

当前成员添加方式要求对方已经完成注册。系统暂未发送邮件邀请，也不会生成可公开传播的邀请链接。

## 项目作用域

项目接口现在支持两种作用域。

### 匿名浏览器工作区

请求只携带：

```text
X-Workspace-Key: <browser-secret>
```

项目只对当前浏览器密钥可见。

### 组织空间

请求携带：

```text
X-Workspace-Key: <browser-secret>
X-Organization-Id: <organization-id>
Cookie: zhilink_session=<HttpOnly session>
```

写请求还必须携带：

```text
X-CSRF-Token: <csrf-token>
```

后端先确认用户是组织成员，再根据角色判断项目操作是否允许。组织项目不依赖某一台浏览器的匿名密钥，因此成员可以从不同设备登录后访问同一组织项目。

## 匿名项目迁移

组织所有者或管理员可以把当前浏览器尚未绑定组织的匿名项目迁移到当前组织：

```text
POST /api/organizations/{organization_id}/claim-workspace-projects
```

迁移行为：

- 只迁移当前 `X-Workspace-Key` 下尚未绑定组织的项目；
- 项目和全部版本历史保留原 ID 与内容；
- 迁移后项目只通过组织成员权限访问；
- 原匿名工作区不再能读取、编辑或删除这些项目；
- 重复迁移不会创建重复项目。

## 数据表

新增：

- `users`
- `organizations`
- `organization_memberships`
- `auth_sessions`
- `organization_projects`

项目本体和版本历史仍保存在：

- `projects`
- `project_versions`

`organization_projects` 作为项目与组织之间的归属表，因此无需破坏已有匿名项目表结构。

## 当前边界

本阶段尚未实现：

- 邮箱验证；
- 忘记密码和密码重置；
- 邮件邀请和邀请链接；
- 多因素认证；
- 企业单点登录；
- 用户自行修改密码或注销账号；
- 操作审计日志；
- Alembic 数据库迁移脚本。

因此公开 Demo 不应鼓励用户复用重要生产密码。正式上线前至少需要补齐邮箱验证、密码重置、审计日志、数据库迁移和密钥管理。

## 测试

```bash
PYTHONPATH=. pytest -q tests/test_auth_rbac.py
node --check frontend/assets/account-access.js
python -m py_compile \
  backend/auth_store.py \
  backend/auth_schemas.py \
  backend/auth_routes.py \
  backend/project_routes.py
```

覆盖范围：

- 注册、登录、退出和会话读取；
- 密码非明文存储；
- HttpOnly 会话 Cookie；
- CSRF 缺失和错误令牌拒绝；
- 所有者、管理员、编辑者和只读成员权限；
- 最后一名所有者保护；
- 组织间项目隔离；
- 匿名项目迁移；
- 迁移后匿名访问失效；
- 组织项目和版本历史访问。
