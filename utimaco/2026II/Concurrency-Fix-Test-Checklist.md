# 并发问题修复 — 涉及接口清单（测试用）

> **日期**：2026-06-04
> **对应提交**：`93fb7c9` fix: 异步生命周期操作 per-device 并发互斥 + 配置 UPSERT + 文件锁

---

## 修复概述

本次修复覆盖 6 项并发竞态问题，按严重程度分级：

| # | 级别 | 修复项 | 简述 |
|---|------|--------|------|
| 1 | CRITICAL | DeviceOperationLockRegistry 两级锁 | 异步操作 dispatch 前获取设备锁，防止同设备并发操作冲突 |
| 2 | HIGH | UpgradeInProgressGuard 执行时二次检查 | 堵住 RetryScheduler 重试绕过入队检查的漏洞 |
| 3 | HIGH | 配置 saveOrUpdate 改用 UPSERT | 消除首次写入 UNIQUE 约束冲突导致的 500 错误 |
| 4 | MEDIUM | resolv.conf 文件读写加锁 | 防止并发读写 DNS 配置文件导致内容损坏 |
| 5 | MEDIUM | ExportImagesLockRegistry TTL 超时释放 | 防止导出锁因异常未释放导致永久阻塞 |
| 6 | LOW | 容量检查竞态标注 | persistNew 容量检查非原子（已标注，暂不修复） |

---

## 锁模型说明

```
┌──────────────────────────────────────────────────┐
│           DeviceOperationLockRegistry             │
│                                                  │
│   全局 write lock（互斥所有操作）                  │
│   ├── CHSM 全部异步操作（影响所有 VSM slot）       │
│   └── VSM upgrade（遍历全部 VSM endpoint）         │
│                                                  │
│   全局 read lock + per-vsmId lock（同 vsmId 互斥） │
│   ├── VSM start / stop / restart / reset          │
│   └── VSM export / import                         │
│                                                  │
│   无锁                                            │
│   ├── VSM create / destroy（存根）                 │
│   └── 测试 fixture                                │
└──────────────────────────────────────────────────┘
```

**互斥规则**：
- CHSM 操作进行中 → 所有 VSM 操作被阻塞
- VSM upgrade 进行中 → 所有其他操作被阻塞
- 同一 vsmId 的 VSM 操作互斥，不同 vsmId 可并行
- 锁获取失败 → 任务标记 FAILED，由 RetryScheduler 下轮重试

---

## 一、异步生命周期接口（修复项 #1 #2）

### CHSM 异步操作 — 全局 write lock

| # | 接口路径 | 方法 | oprType | 锁类型 | 测试要点 |
|---|---------|------|---------|--------|---------|
| 1 | `/api/1.0/chsm/image` | POST | `export` | 全局 write | 导出期间其他 CHSM/VSM 操作应被阻塞 |
| 2 | `/api/1.0/chsm/image` | POST | `import` | 全局 write | 导入期间其他 CHSM/VSM 操作应被阻塞 |
| 3 | `/api/1.0/chsm` | POST | `upgradeCHSM` | 全局 write | 升级期间所有操作应被阻塞；UpgradeInProgressGuard 双重检查 |
| 4 | `/api/1.0/chsm` | POST | `restartCHSM` | 全局 write | 重启期间其他操作应被阻塞 |
| 5 | `/api/1.0/chsm` | POST | `backupCHSM` | 全局 write | 备份期间其他操作应被阻塞 |
| 6 | `/api/1.0/chsm` | POST | `restoreCHSM` | 全局 write | 恢复期间所有操作应被阻塞；UpgradeInProgressGuard 双重检查 |

### VSM 异步操作 — 全局 write lock

| # | 接口路径 | 方法 | oprType | 锁类型 | 测试要点 |
|---|---------|------|---------|--------|---------|
| 7 | `/api/1.0/vsm` | POST | `upgrade` | 全局 write | 升级期间所有 CHSM/VSM 操作应被阻塞；UpgradeInProgressGuard 双重检查 |

### VSM 异步操作 — per-vsmId read lock

| # | 接口路径 | 方法 | oprType | 锁类型 | 测试要点 |
|---|---------|------|---------|--------|---------|
| 8 | `/api/1.0/vsm` | POST | `start` | per-vsmId | 同 vsmId 操作互斥；不同 vsmId 可并行 |
| 9 | `/api/1.0/vsm` | POST | `stop` | per-vsmId | 同上 |
| 10 | `/api/1.0/vsm` | POST | `restart` | per-vsmId | 同上 |
| 11 | `/api/1.0/vsm` | POST | `reset` | per-vsmId | 同上 |
| 12 | `/api/1.0/vsm/image` | POST | `export` | per-vsmId | 同 vsmId 互斥 + ExportImagesLockRegistry TTL |
| 13 | `/api/1.0/vsm/image` | POST | `import` | per-vsmId | 同 vsmId 互斥 + ExportImagesLockRegistry TTL |

### VSM 异步操作 — 无锁（存根）

| # | 接口路径 | 方法 | oprType | 锁类型 | 备注 |
|---|---------|------|---------|--------|------|
| 14 | `/api/1.0/vsm` | POST | `create` | 无 | 存根接口，无实际操作 |
| 15 | `/api/1.0/vsm` | POST | `destroy` | 无 | 存根接口，无实际操作 |

---

## 二、配置写入接口（修复项 #3）

改用 SQLite `INSERT ... ON CONFLICT DO UPDATE` (UPSERT)，消除并发首次写入时 UNIQUE 约束冲突 500。

### CHSM 配置 — ChsmConfigRepository UPSERT

| # | 接口路径 | 方法 | 说明 | 测试要点 |
|---|---------|------|------|---------|
| 16 | `/api/1.0/chsm/network` | POST | 配置 CHSM 网络 | 并发写入同 key 不应 500 |
| 17 | `/api/1.0/chsm/ntp` | POST | 配置 NTP | 同上 |
| 18 | `/api/1.0/chsm/imageuploader` | POST | 配置镜像上传地址 | 同上 |
| 19 | `/api/1.0/chsm/loguploader` | POST | 配置日志上传地址 | 同上 |
| 20 | `/api/1.0/chsm/alarmaddress` | POST | 配置告警地址 | 同上 |
| 21 | `/api/1.0/chsm/cloudtoken` | POST | 配置 CloudToken | 同上 |
| 22 | `/api/1.0/chsm/moocaddress` | POST | 配置 MO 对接地址 | 同上 |

### VSM 配置 — VsmConfigRepository UPSERT

| # | 接口路径 | 方法 | 说明 | 测试要点 |
|---|---------|------|------|---------|
| 23 | `/api/1.0/vsm/{vsmId}/network` | POST | 配置 VSM 网络 | 并发写入同 vsmId 同 key 不应 500 |
| 24 | `/api/1.0/vsm/{vsmId}/mac` | POST | 配置 VSM MAC | 同上 |
| 25 | `/api/1.0/vsm/{vsmId}/vlan` | POST | 配置 VSM VLAN | 同上 |
| 26 | `/api/1.0/vsm/{vsmId}/network` | DELETE | 删除 VSM 网络配置 | 同上 |

### VSM 租户令牌 — VsmTenantTokenRepository UPSERT

| # | 接口路径 | 方法 | 说明 | 测试要点 |
|---|---------|------|------|---------|
| 27 | `/api/1.0/vsm/{vsmId}/token` | POST | 配置租户令牌 | 并发写入同 vsmId 不应 500 |

---

## 三、镜像导出导入接口（修复项 #5）

ExportImagesLockRegistry 增加 TTL 超时释放，防止 StreamingResponseBody 异常导致锁永久泄漏。

| # | 接口路径 | 方法 | 说明 | 测试要点 |
|---|---------|------|------|---------|
| 28 | `/platformServlet?method=exportBackupKeys` | POST | 租户密评导出备份密钥 | 导出超时后锁应自动释放，不阻塞后续导入 |
| 29 | `/platformServlet?method=importBackupKeys` | POST | 租户密评导入备份密钥 | 同上 |

---

## 四、DNS 配置接口（修复项 #4）

resolv.conf 文件读写加 ReentrantLock，防止并发读写导致内容损坏。

| # | 接口路径 | 方法 | 说明 | 测试要点 |
|---|---------|------|------|---------|
| 30 | `/api/1.0/chsm/network` | POST | 配置网络（含 DNS） | 并发配置网络不应导致 resolv.conf 内容损坏 |

---

## 五、不受影响的接口（仅供确认）

以下接口为只读查询或 guest 端点，本次修复**不涉及**：

| 接口路径 | 方法 | 说明 |
|---------|------|------|
| `/api/1.0/chsm/allstatus` | GET | CHSM 全量状态查询 |
| `/api/1.0/chsm/debuginfo` | GET | 调试信息查询 |
| `/api/1.0/chsm/authpk` | GET | 获取公钥指纹 |
| `/api/1.0/vsm/status` | GET | VSM 状态查询 |
| `/api/1.0/vsm` | POST (oprType=`getinfo`) | VSM 信息查询 |
| `/api/1.0/vsm` | POST (oprType=`getDeviceInfo`) | VSM 设备信息查询 |
| `/authServlet?method=getAuthPKFingerprints` | GET | 租户公钥指纹查询 |
| `/platformServlet?method=getStatus` | POST | 租户 VSM 状态查询 |

---

## 测试场景建议

### 场景 A：全局锁互斥（CHSM 操作 vs VSM 操作）

1. 发起 CHSM export（接口 #1）
2. 在 export 执行期间，发起 VSM start（接口 #8）
3. **预期**：VSM start 任务标记 FAILED，等待 RetryScheduler 下轮重试

### 场景 B：per-vsmId 互斥（同 VSM 并发操作）

1. 对 vsmId=A 发起 VSM start（接口 #8）
2. 在 start 执行期间，对同一 vsmId=A 发起 VSM restart（接口 #10）
3. **预期**：restart 被阻塞，标记 FAILED，下轮重试
4. 对 vsmId=B 发起 VSM start → **预期**：正常执行，不受 vsmId=A 影响

### 场景 C：VSM upgrade 全局互斥

1. 发起 VSM upgrade（接口 #7）
2. 在 upgrade 执行期间，发起任意 CHSM 或 VSM 操作
3. **预期**：所有操作被阻塞

### 场景 D：UpgradeInProgressGuard 二次检查

1. 模拟一个 upgrade 任务因异常进入 FAILED 状态后被 RetryScheduler 重新入队
2. 在此期间手动发起另一个 upgrade
3. **预期**：runAsync dispatch 前的二次 guard.check() 拦截，返回 409

### 场景 E：配置 UPSERT 幂等

1. 对同一配置项（如 CHSM network）并发发起 2 个 POST 请求
2. **预期**：两个请求都应成功（200），不应出现 500 UNIQUE 约束冲突

### 场景 F：导出锁 TTL 超时释放

1. 发起 exportBackupKeys（接口 #28）
2. 模拟导出过程异常中断（如连接断开）
3. 等待 TTL 超时后，发起 importBackupKeys（接口 #29）
4. **预期**：导入不被死锁阻塞，正常执行
