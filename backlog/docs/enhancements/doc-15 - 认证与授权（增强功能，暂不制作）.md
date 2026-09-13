---
id: doc-15
title: 认证与授权（增强功能，暂不制作）
type: other
created_date: '2026-09-13 12:51'
updated_date: '2026-09-13 12:51'
---
# 认证与授权（增强功能，暂不制作）

> 状态：**暂不制作**（增强功能） | 关联：doc-14（WebUI 信息架构）、doc-12（REST API Key）
> 定位说明：本项目为**个人金融数据平台**（非生产）。首期 WebUI 仅本机（`127.0.0.1`）访问、无账号体系；当出现**远程访问 / 多用户 / 对外开放 REST / 审计合规**需求时，按下述方案实施。

## 1. 触发条件（何时启用）

- 需要远程访问 WebUI 或多设备使用；
- 需要多用户与角色隔离（viewer / operator / admin）；
- 对外提供 REST/SDK（他人消费）或需要操作审计留痕。

## 2. 方案概要（四层）

1. **身份与角色**：本地账号为基线，OIDC 可选适配（不引入重 IAM、不实现 IdP）；
2. **会话（BFF）**：浏览器只持会话 Cookie；WebUI 服务端以服务账号调 REST；
3. **权限执行**：固定三角色 + 页面/操作两级校验（后端为准）；
4. **审计**：管理动作与登录事件统一审计（用户归因）。

## 3. 数据模型（PG `meta` schema）

| 表 | 内容 |
|---|---|
| `meta.users` | `user_id / username / password_hash(Argon2id) / status / created_at / last_login` |
| `meta.user_roles` | `user_id / role`（viewer / operator / admin；可选受控 `audit` 查看权） |
| `meta.sessions` | 服务端会话：`session_id / user_id / created_at / expires_at / idle_expires / ip / ua / revoked_at` |
| `meta.idp_identities` | OIDC 预留：`(provider, subject, email) → user_id` |
| `meta.audit_log` | 登录/登出/失败/角色变更/高风险操作（与 REST 审计同流） |

## 4. 会话与安全基线

- 会话 Cookie：`HttpOnly + Secure + SameSite`，配 CSRF 头；浏览器**永不接触 API Key**；
- **会话权威存 PG**（Redis 仅可选加速）——安全状态不入缓存（doc-10 §3.4）；
- Argon2id 密码哈希；登录限速 + 失败锁定；会话 TTL / 闲置超时 / 管理员可撤销；
- 引导管理员：部署时一次性 secret 或 CLI（`platform-admin create-user`）创建，**首登强制改密、不落镜像**。

## 5. SSO（OIDC，预留）

- 配置 `auth.mode: local | oidc | local+oidc`；
- OIDC 走 **Authorization Code + PKCE**；校验 `iss / aud / nonce / 签名`；
- `groups` claim → 角色映射（配置表）；JIT 创建用户；SSO 用户默认禁用本地密码登录；
- 对接企业已有 IdP；无 IdP 时保持 local（轻量 IdP 由用户自行添加，不作为平台内置依赖）。

## 6. WebUI → REST 调用（BFF 模式）

- WebUI 服务端以**服务账号 API Key（admin scope）**调用 REST；用户权限在服务端按角色执行；
- **审计以 user_id 归因**（不是 Key 主体）；服务账号 Key 仅服务端注入、可轮换、不落镜像；
- 备选：每用户短期 token（REST 侧可做用户级审计，但 Key 数量膨胀）——默认不采用。

## 7. 与 REST API Key 的关系

- doc-12 的 API Key（`read / export / admin`）**不变**，面向外部程序消费；
- 本文档只负责"人"的身份、会话与WebUI权限，两者不复用。

## 8. 实施清单（未来启用时）

1. 表结构与迁移（`meta` schema）；2. CLI 用户管理；3. 登录页与会话管理（刷新/登出）；4. 角色矩阵与前端隐藏 + 后端校验；5. 审计检索页；6. OIDC 适配与组映射；7. 测试（会话固定/CSRF/暴力破解/越权）。
