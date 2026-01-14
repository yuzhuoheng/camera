# Nginx MinIO 反向代理配置示例

server {
    listen 443 ssl;
    server_name hos-studio.supcon.com;

    # SSL 证书配置 (请替换为实际路径)
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;

    # 其他 SSL 参数...

    # MinIO 文件访问代理
    # 匹配 /camera-server-photos/ 开头的请求
    location /camera-server-photos/ {
        # 转发到 MinIO 服务端口 (假设宿主机端口为 31110)
        # 如果 Nginx 和 MinIO 在同一 Docker 网络，可以使用 http://minio:9000
        proxy_pass http://127.0.0.1:31110/camera-server-photos/;
        
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 支持大文件上传/下载
        client_max_body_size 20M;
    }
}
