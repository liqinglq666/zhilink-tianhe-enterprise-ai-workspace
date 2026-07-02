# 部署说明

## 本地运行

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

浏览器打开：

```text
http://127.0.0.1:8000
```

## Docker 私有化部署

```bash
docker compose up -d --build
```

访问：

```text
http://localhost:8000
```

当前 Dockerfile 已包含非 root 用户与健康检查，适合演示、园区服务器和企业内网试点。

## Render / Railway

启动命令：

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

环境变量建议：

```text
MAX_BODY_BYTES=1500000
CORS_ALLOW_ORIGINS=*
```

如果平台不支持 `$PORT`，可改为固定 8000。

## Nginx 反向代理示例

```nginx
server {
    listen 80;
    server_name your-domain.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

正式环境建议配 HTTPS。

## 政企落地建议

- 优先采用 Docker 私有化部署至园区服务器、企业内网或政企云。
- API Key 由使用单位自行配置，或由用户在页面临时输入。
- 合同、客户、会员、会议等敏感文本建议脱敏输入。
- 后端默认不写数据库；如果后续加入留存功能，应增加用户授权、脱敏、权限和审计。
- 正式上线前增加登录、角色权限、操作日志、政策库更新机制、服务商资源库和人工复核流程。
- 如接入单位自有大模型网关，可在页面选择“自定义兼容接口”，填写内网 Base URL 与模型名称。
