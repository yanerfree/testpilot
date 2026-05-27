# cert/ 证书与密钥存放说明

本目录存放接口签名认证所需的密钥文件。框架支持两种签名算法，
对应两组密钥文件，格式要求不同。

---

## 文件清单

```
cert/
├── rsa_private_key.pem    # RSA 私钥 (用于签名)
├── rsa_public_key.pem     # RSA 公钥 (用于计算指纹)
├── sm2_private_key.pem    # SM2 私钥 (用于签名)
└── sm2_public_key.pem     # SM2 公钥 (用于计算指纹)
```

文件路径在 `config/config.yaml` 中配置：

```yaml
auth:
  rsa:
    private_key_path: "cert/rsa_private_key.pem"
    public_key_path:  "cert/rsa_public_key.pem"
  sm2:
    private_key_path: "cert/sm2_private_key.pem"
    public_key_path:  "cert/sm2_public_key.pem"
```

> 如果密钥文件不存在，框架会使用 `common/signer.py` 底部内置的测试密钥。
> 内置 RSA 密钥与一期相同，内置 SM2 密钥为国密规范示例密钥，仅用于开发调试。

---

## RSA 密钥格式 (PEM)

标准 PKCS#8 PEM 格式，与一期 `cert/` 目录下的格式一致。

### rsa_private_key.pem

```
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFA......
(PKCS#8 DER 的 BASE64 编码，每行 64 字符)
......
-----END PRIVATE KEY-----
```

### rsa_public_key.pem

```
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOC......
(SubjectPublicKeyInfo DER 的 BASE64 编码，每行 64 字符)
......
-----END PUBLIC KEY-----
```

**加载逻辑**：框架自动去掉 `-----BEGIN/END ...-----` 行，
合并中间的 BASE64 字符串作为密钥数据。

**生成方式**（如需重新生成）：

```bash
# 生成 2048 位 RSA 私钥
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out rsa_private_key.pem

# 导出公钥
openssl pkey -in rsa_private_key.pem -pubout -out rsa_public_key.pem
```

**指纹计算规则**：取公钥 PEM 中去掉头尾后的纯 BASE64 字符串，
对其 UTF-8 字节做 SHA-256 哈希，结果再 BASE64 编码。
与一期 `SHA256withRSA.py` 中 `generate_fingerprint()` 逻辑一致。

---

## SM2 密钥格式 (HEX 文本)

SM2 密钥使用十六进制 (HEX) 纯文本格式，不带 PEM 头尾。
文件扩展名仍用 `.pem` 只是沿用命名习惯，实际内容为纯文本。

### sm2_private_key.pem

文件内容为一行 64 个十六进制字符（256 bit 私钥）：

```
3945208F7B2144B13F36E38AC6D39F95889393692860B51A42FB81EF4DF7C5B8
```

### sm2_public_key.pem

文件内容为一行 128 个十六进制字符（512 bit = 256 bit X + 256 bit Y）：

```
09F9DF311E5421A150DD7D161E4BC5C672179FAD1833FC076BB08FF356F35020CCEA490CE26775A52DC6EA718CC1AA600AED05FBF35E084A6632F6072DA9AD13
```

> 注意：不带 `04` 前缀（非压缩点标识），只有 X 和 Y 坐标拼接。

**加载逻辑**：框架直接读取文件全部内容，去除首尾空白，作为 HEX 字符串使用。

**指纹计算规则**：对公钥 HEX 字符串的字节做 SM3 哈希，结果再 BASE64 编码。

**生成方式**（如需重新生成）：

```bash
# 使用 gmssl Python 库生成
python3 -c "
from gmssl import sm2
import secrets

# 生成私钥 (256 bit)
private_key = secrets.token_hex(32).upper()
print(f'私钥: {private_key}')

# 通过椭圆曲线计算公钥
# 注意: gmssl 库的 sm2.CryptSM2 需要已知密钥对
# 实际项目中建议使用密码机或专业工具生成
"
```

实际项目中 SM2 密钥通常由密码机或华为云平台生成提供，
获取后将私钥和公钥分别存入上述两个文件即可。

---

## 如何切换签名算法

修改 `config/config.yaml`：

```yaml
auth:
  enabled: true
  algorithm: "RSAWithSHA256"    # 改为 "SM2WithSM3" 即切换
```

切换后所有 trusted 接口的请求头将自动使用对应算法签名。

---

## 如何验证密钥是否正确

```bash
cd /home/dreamer/utimaco/2026II/utimaco-admin-api
python3 demo_sign.py
```

输出会展示两种算法的签名结果和指纹。
将 RSA 指纹与一期对比、将 SM2 指纹与密码机侧配置对比，确认一致即可。
