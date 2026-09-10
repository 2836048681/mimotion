# 服务器部署约定

- 应用目录：`/opt/mimotion`
- 运行用户：`mimotion`
- 私有数据：`/var/lib/mimotion`
- 环境文件：`/etc/mimotion/mimotion.env`
- Web：仅监听 `127.0.0.1:8501`
- 公网入口：Cloudflare Tunnel，域名 `mimotion.ricksanchez12301.me`
- 定时器：每分钟检查一次北京时间随机计划，避免与 GitHub Actions 同时调度

环境文件必须包含：

```dotenv
MIMOTION_DATA_DIR=/var/lib/mimotion
MIMOTION_TOKEN_FILE=/var/lib/mimotion/encrypted_tokens.data
MIMOTION_MASTER_KEY=<32-byte-key-as-hex>
MIMOTION_TOKEN_AES_KEY=<16-character-key>
MIMOTION_ALLOWED_EMAILS=<Cloudflare-Access-email>
```

如未配置 Cloudflare Access，可临时使用 `MIMOTION_ADMIN_PASSWORD_SHA256`，值为访问密码的 SHA-256；不要保存明文密码。
