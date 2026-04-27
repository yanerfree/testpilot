| 用例ID | 标题 | 模块 | 测试类型 | 优先级 | 前置条件 | 测试步骤 | 预期结果 |
|--------|------|------|---------|--------|---------|---------|---------|
| TC-REG-001 | 验证正确信息注册成功 | 用户注册 | 功能测试 | P0 | 邮箱 test@example.com 未被注册 | 1. 发送 POST /api/auth/register，body: {"username":"testuser","email":"test@example.com","password":"Abc123456"} | 1. 状态码 201 2. 返回 JSON 包含 id（数字）、username="testuser"、email="test@example.com" 3. 不返回 password 字段 |
| TC-REG-002 | 验证缺少 username 字段返回 400 | 用户注册 | 参数校验 | P1 | 无 | 1. 发送 POST /api/auth/register，body: {"email":"test@example.com","password":"Abc123456"} | 1. 状态码 400 2. 返回错误信息提示 username 必填 |
| TC-REG-003 | 验证缺少 email 字段返回 400 | 用户注册 | 参数校验 | P1 | 无 | 1. 发送 POST /api/auth/register，body: {"username":"testuser","password":"Abc123456"} | 1. 状态码 400 2. 返回错误信息提示 email 必填 |
| TC-REG-004 | 验证缺少 password 字段返回 400 | 用户注册 | 参数校验 | P1 | 无 | 1. 发送 POST /api/auth/register，body: {"username":"testuser","email":"test@example.com"} | 1. 状态码 400 2. 返回错误信息提示 password 必填 |
| TC-REG-005 | 验证空请求体返回 400 | 用户注册 | 参数校验 | P2 | 无 | 1. 发送 POST /api/auth/register，body: {} | 1. 状态码 400 |
| TC-REG-006 | 验证邮箱格式不正确返回 400 | 用户注册 | 参数校验 | P2 | 无 | 1. 发送 POST /api/auth/register，body: {"username":"testuser","email":"not-an-email","password":"Abc123456"} | 1. 状态码 400 2. 返回错误信息提示邮箱格式不正确 |
| TC-REG-007 | 验证密码不足 8 位返回 400 | 用户注册 | 参数校验 | P2 | 无 | 1. 发送 POST /api/auth/register，body: {"username":"testuser","email":"test@example.com","password":"Ab1"} | 1. 状态码 400 2. 返回错误信息提示密码至少 8 位 |
| TC-REG-008 | 验证密码缺少大写字母返回 400 | 用户注册 | 参数校验 | P2 | 无 | 1. 发送 POST /api/auth/register，body: {"username":"testuser","email":"test@example.com","password":"abc123456"} | 1. 状态码 400 2. 返回错误信息提示密码需包含大小写和数字 |
| TC-REG-009 | 验证密码缺少数字返回 400 | 用户注册 | 参数校验 | P2 | 无 | 1. 发送 POST /api/auth/register，body: {"username":"testuser","email":"test@example.com","password":"Abcdefghi"} | 1. 状态码 400 2. 返回错误信息提示密码需包含大小写和数字 |
| TC-REG-010 | 验证邮箱已被注册返回 409 | 用户注册 | 业务规则 | P1 | 已存在用户 email=test@example.com | 1. 发送 POST /api/auth/register，body: {"username":"another","email":"test@example.com","password":"Abc123456"} | 1. 状态码 409 2. 返回错误信息提示邮箱已被注册 |
| TC-REG-011 | 验证 username 为空字符串返回 400 | 用户注册 | 边界条件 | P2 | 无 | 1. 发送 POST /api/auth/register，body: {"username":"","email":"test@example.com","password":"Abc123456"} | 1. 状态码 400 |
| TC-REG-012 | 验证 email 为空字符串返回 400 | 用户注册 | 边界条件 | P2 | 无 | 1. 发送 POST /api/auth/register，body: {"username":"testuser","email":"","password":"Abc123456"} | 1. 状态码 400 |
| TC-LOG-001 | 验证正确邮箱密码登录成功 | 用户登录 | 功能测试 | P0 | 已注册用户 email=test@example.com, password=Abc123456 | 1. 发送 POST /api/auth/login，body: {"email":"test@example.com","password":"Abc123456"} | 1. 状态码 200 2. 返回 JSON 包含 token（string 类型，非空） 3. 返回 user 对象包含 id、username、email |
| TC-LOG-002 | 验证密码错误返回 401 | 用户登录 | 异常场景 | P1 | 已注册用户 email=test@example.com | 1. 发送 POST /api/auth/login，body: {"email":"test@example.com","password":"WrongPass123"} | 1. 状态码 401 2. 返回错误信息"邮箱或密码错误" |
| TC-LOG-003 | 验证邮箱不存在返回 401 | 用户登录 | 异常场景 | P1 | 无 | 1. 发送 POST /api/auth/login，body: {"email":"noexist@example.com","password":"Abc123456"} | 1. 状态码 401 2. 返回错误信息"邮箱或密码错误"（不泄露邮箱是否存在） |
| TC-LOG-004 | 验证缺少 email 字段返回 400 | 用户登录 | 参数校验 | P1 | 无 | 1. 发送 POST /api/auth/login，body: {"password":"Abc123456"} | 1. 状态码 400 2. 返回错误信息提示 email 必填 |
| TC-LOG-005 | 验证缺少 password 字段返回 400 | 用户登录 | 参数校验 | P1 | 无 | 1. 发送 POST /api/auth/login，body: {"email":"test@example.com"} | 1. 状态码 400 2. 返回错误信息提示 password 必填 |
| TC-LOG-006 | 验证空请求体返回 400 | 用户登录 | 参数校验 | P2 | 无 | 1. 发送 POST /api/auth/login，body: {} | 1. 状态码 400 |
| TC-ME-001 | 验证携带有效 token 获取用户信息 | 用户信息 | 功能测试 | P0 | 已注册并登录，获取有效 token | 1. 发送 GET /api/auth/me，Header: Authorization: Bearer {valid_token} | 1. 状态码 200 2. 返回 JSON 包含 id、username、email、createdAt 4 个字段 3. createdAt 为合法时间格式 |
| TC-ME-002 | 验证不携带 token 返回 401 | 用户信息 | 异常场景 | P1 | 无 | 1. 发送 GET /api/auth/me，不设置 Authorization Header | 1. 状态码 401 |
| TC-ME-003 | 验证 token 无效返回 401 | 用户信息 | 异常场景 | P1 | 无 | 1. 发送 GET /api/auth/me，Header: Authorization: Bearer invalid_token_abc | 1. 状态码 401 |
| TC-ME-004 | 验证 token 过期返回 401 | 用户信息 | 异常场景 | P2 | 已获取过期 token | 1. 发送 GET /api/auth/me，Header: Authorization: Bearer {expired_token} | 1. 状态码 401 2. 返回错误信息提示 token 已过期 |
| TC-ME-005 | 验证 Authorization 缺少 Bearer 前缀返回 401 | 用户信息 | 边界条件 | P2 | 已获取有效 token | 1. 发送 GET /api/auth/me，Header: Authorization: {valid_token} | 1. 状态码 401 |
| TC-PWD-001 | 验证修改密码成功 | 修改密码 | 功能测试 | P0 | 已注册并登录，当前密码 Abc123456，获取有效 token | 1. 发送 PUT /api/auth/password，Header: Authorization: Bearer {valid_token}，body: {"oldPassword":"Abc123456","newPassword":"Xyz789012"} | 1. 状态码 200 2. 使用新密码 Xyz789012 可以登录成功 3. 使用旧密码 Abc123456 登录返回 401 |
| TC-PWD-002 | 验证旧密码错误返回 401 | 修改密码 | 异常场景 | P1 | 已注册并登录，获取有效 token | 1. 发送 PUT /api/auth/password，Header: Authorization: Bearer {valid_token}，body: {"oldPassword":"WrongOld123","newPassword":"Xyz789012"} | 1. 状态码 401 2. 返回错误信息提示旧密码错误 3. 原密码未被修改 |
| TC-PWD-003 | 验证未认证返回 401 | 修改密码 | 异常场景 | P1 | 无 | 1. 发送 PUT /api/auth/password，不设置 Authorization Header，body: {"oldPassword":"Abc123456","newPassword":"Xyz789012"} | 1. 状态码 401 |
| TC-PWD-004 | 验证新密码不足 8 位返回 400 | 修改密码 | 参数校验 | P2 | 已注册并登录，获取有效 token | 1. 发送 PUT /api/auth/password，Header: Authorization: Bearer {valid_token}，body: {"oldPassword":"Abc123456","newPassword":"Xy7"} | 1. 状态码 400 2. 返回错误信息提示密码至少 8 位 |
| TC-PWD-005 | 验证新密码缺少大写字母返回 400 | 修改密码 | 参数校验 | P2 | 已注册并登录，获取有效 token | 1. 发送 PUT /api/auth/password，Header: Authorization: Bearer {valid_token}，body: {"oldPassword":"Abc123456","newPassword":"xyz789012"} | 1. 状态码 400 |
| TC-PWD-006 | 验证新密码缺少数字返回 400 | 修改密码 | 参数校验 | P2 | 已注册并登录，获取有效 token | 1. 发送 PUT /api/auth/password，Header: Authorization: Bearer {valid_token}，body: {"oldPassword":"Abc123456","newPassword":"Xyzabcdef"} | 1. 状态码 400 |
| TC-PWD-007 | 验证缺少 oldPassword 字段返回 400 | 修改密码 | 参数校验 | P2 | 已注册并登录，获取有效 token | 1. 发送 PUT /api/auth/password，Header: Authorization: Bearer {valid_token}，body: {"newPassword":"Xyz789012"} | 1. 状态码 400 |
| TC-PWD-008 | 验证缺少 newPassword 字段返回 400 | 修改密码 | 参数校验 | P2 | 已注册并登录，获取有效 token | 1. 发送 PUT /api/auth/password，Header: Authorization: Bearer {valid_token}，body: {"oldPassword":"Abc123456"} | 1. 状态码 400 |
| TC-PWD-009 | 验证新旧密码相同返回 400 | 修改密码 | 业务规则 | P2 | 已注册并登录，当前密码 Abc123456，获取有效 token | 1. 发送 PUT /api/auth/password，Header: Authorization: Bearer {valid_token}，body: {"oldPassword":"Abc123456","newPassword":"Abc123456"} | 1. 状态码 400 2. 返回错误信息提示新密码不能与旧密码相同 |
