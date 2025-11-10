# frontend/nginx.conf
server {
    listen 80;
    
    # 静态文件的根目录
    root /usr/share/nginx/html;
    index index.html;

    # --- 1. 代理 API 请求 ---
    # 匹配 /api/..., /api/groups/1, ...
    location /api {
        proxy_pass http://backend:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # --- 2. 托管 Vue.js 静态资源 ---
    # 匹配 /assets/index-xxx.js, /assets/index-xxx.css
    location /assets {
        try_files $uri =404;
    }
    
    # 匹配 /favicon.ico
    location = /favicon.ico {
        try_files $uri =404;
    }

    # --- 3. 托管 Vue.js 的“根”页面 (后台) ---
    # [安全] 只精确匹配 / (根目录)
    # [安全] 以及 /all-domains 和 /group (后台的 Vue 路由)
    location ~ ^/(all-domains|group|$) {
        try_files $uri $uri/ /index.html;
    }

    # --- 4. [关键] 捕获所有其他请求 (即 /go, /aB3xZ7 等) ---
    # 所有不匹配 1, 2, 3 的请求都会被这里捕获
    # 并被转发到 Flask 后端进行跳转
    location / {
        proxy_pass http://backend:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}