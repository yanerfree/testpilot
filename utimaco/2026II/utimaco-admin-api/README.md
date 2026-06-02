# 华为云密码机二期 — 接口自动化测试

基于 pytest + Excel 数据驱动的接口测试框架，覆盖 CHSM Admin API 全部 44 个接口。

## 目录结构

```
├── config/config.yaml       # 环境配置（地址、算法、路径）
├── cert/                    # 签名密钥文件（PEM 格式）
├── data/
│   ├── test_data.xlsx       # 测试数据 Excel（含多个 sheet）
│   ├── keys.json            # 公钥测试数据（testdata 中 ${keys.xxx} 引用）
│   └── 设计笔记.md          # 设计决策与踩坑记录
├── common/                  # 公共模块
│   ├── excel_handler.py     # Excel 数据加载 & 变量替换
│   ├── http_client.py       # HTTP 客户端（自动签名）
│   ├── signer.py            # RSA/SM2 签名
│   ├── assertions.py        # 断言引擎
│   ├── scenario_runner.py   # 场景编排（多步骤 + 变量传递）
│   ├── result_collector.py  # 测试结果收集
│   └── issue_collector.py   # 失败问题收集
├── testcases/
│   └── test_chsm_api.py    # 测试入口
├── tools/
│   ├── chsm_mock.py         # Mock Server（dry-run 验证用）
│   ├── gen_trusted_guest.py # 生成 trusted/guest sheet 数据
│   ├── gen_pk.py            # 生成 pk_rsa/pk_sm2 sheet 数据
│   ├── gen_section8_9.py    # 生成 section8_9 sheet 数据
│   ├── gen_test_cases.py    # 生成测试用例 Excel
│   └── backfill_results.py  # 结果回填到测试用例 Excel
├── run.py                   # 一键运行 + 生成 Allure 报告
├── requirements.txt         # Python 依赖
└── pytest.ini               # pytest 配置
```

## 环境准备

### 1. Python 依赖

```bash
pip install -r requirements.txt
```

### 2. Allure CLI（生成 HTML 报告）

```bash
# 方式一：npm 安装（需要 Node.js）
npm install -g allure-commandline

# 需要 Java 运行时
sudo apt-get install default-jre-headless   # Debian/Ubuntu
```

### 3. 签名密钥

将 RSA 和 SM2 的密钥对放到 `cert/` 目录：

```
cert/
├── rsa_private_key.pem
├── rsa_public_key.pem
├── sm2_private_key.pem
└── sm2_public_key.pem
```

## 配置

编辑 `config/config.yaml`：

```yaml
# 切换签名算法
auth:
  algorithm: "RSAWithSHA256"   # 或 "SM2WithSM3"

# 切换目标环境
environments:
  dev:
    base_url: "https://172.16.2.112:7443"
  test:
    base_url: "https://172.16.2.112:7443"

current_env: "test"   # 当前使用的环境
```

### Excel config sheet

`data/test_data.xlsx` 的 `config` sheet 存放测试数据中的环境变量，测试数据通过 `${env.xxx}` 语法引用：

| key | value | 说明 |
|-----|-------|------|
| vsmHost | https://192.168.1.50:7443 | Section 9 租户密评 VSM 地址 |
| fileServerHost | http://10.10.1.100:8080 | Section 8 FileServer 地址 |
| callbackUrl | http://10.10.1.207:8000/callback | 异步回调地址 |
| ... | ... | 其他参数见 config sheet |

**部署到新环境时，修改这两处即可：**
1. `config.yaml` 的 `base_url`
2. Excel `config` sheet 的各地址值

## 运行测试

### 一键运行（推荐）

```bash
python run.py
```

运行完自动生成 Allure 报告并在浏览器中打开。

不想自动打开报告：

```bash
python run.py --no-open
```

### 透传 pytest 参数

```bash
# 按关键字筛选
python run.py -k "CHSM_INFO"

# 只跑冒烟测试
python run.py -m smoke
```

### 直接用 pytest

```bash
pytest testcases/test_chsm_api.py -v
```

## 测试数据 Sheet 说明

`data/test_data.xlsx` 包含以下 sheet：

| Sheet | 内容 | 行数 | 认证 |
|-------|------|------|------|
| testdata | 示例数据（默认运行） | 4 | — |
| pk_rsa | 7.3 公钥管理（RSA 算法） | 37 | guest/trusted |
| pk_sm2 | 7.3 公钥管理（SM2 算法） | 37 | guest/trusted |
| trusted | 7.1 CHSM + 7.2 VSM 管理 | 176 | trusted |
| guest | 无需认证的状态查询接口 | 12 | 无 |
| section8_9 | 8 FileServer + 9 租户密评 | 57 | mixed |
| config | 环境变量配置 | 14 | — |

### 切换 sheet

修改 `testcases/test_chsm_api.py` 第 27 行的 `sheet_name` 参数：

```python
ALL_DATA = handler.get_test_cases(sheet_name="trusted", process_data=True)
```

### 双算法覆盖

trusted/guest sheet 不区分算法，切换 `config.yaml` 中的 `auth.algorithm` 跑两遍即可：

1. `algorithm: "RSAWithSHA256"` → 运行一遍
2. `algorithm: "SM2WithSM3"` → 运行一遍

pk_rsa / pk_sm2 各自对应算法，需配合切换。

## Mock Server（dry-run）

在没有真实密码机环境时，可以用 mock server 验证框架流程：

```bash
# 终端1：启动 mock
python tools/chsm_mock.py

# 终端2：修改配置后运行
# 1. config.yaml → base_url 改为 http://127.0.0.1:9443
# 2. Excel config sheet → vsmHost 改为 http://127.0.0.1:9443
# 3. 运行测试
python run.py
```

注意：mock 是 HTTP 协议，配置地址必须用 `http://` 而非 `https://`。

## 测试结果

- **Allure 报告**: `reports/allure-report/`（浏览器打开 index.html）
- **测试结果 JSON**: `output/test_results.json`（全量 pass/fail/error）
- **失败问题 JSON**: `output/issues.json`（只收集失败项）
- **结果回填**: `python tools/backfill_results.py` 将结果写回测试用例 Excel
