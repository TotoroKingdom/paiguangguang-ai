# PostgreSQL 17

这些文件在服务器上的目标目录是 `/home/postgres`。

## 1. 上传

在本地 PowerShell 执行：

```powershell
scp -r "C:\AI\my-website-ui\paiguangguang\deploy\postgres" root@服务器IP:/home/
```

## 2. 配置并启动

在服务器执行：

```bash
cd /home/postgres
cp postgres.env.example postgres.env
openssl rand -base64 32
vi postgres.env
mkdir -p data
chmod 600 postgres.env
docker compose config
docker compose up -d
docker compose ps
```

将 `openssl` 输出的随机密码填入 `POSTGRES_PASSWORD`。

数据库只监听服务器的 `127.0.0.1:5432`，不要在云安全组或
CentOS 防火墙中开放公网端口 `5432`。

## 3. 本地连接

首次使用时配置专用 SSH 密钥。这个过程只需要输入一次服务器密码：

```powershell
.\setup-postgres-ssh-key.ps1
```

以后直接运行以下脚本，并保持窗口开启：

```powershell
.\start-postgres-tunnel.ps1
```

如果当前 PowerShell 禁止执行本地脚本，可以仅为本次进程放行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup-postgres-ssh-key.ps1
.\start-postgres-tunnel.ps1
```

Navicat 和本机直接运行的项目使用：

```text
主机：127.0.0.1
端口：15432
数据库：paiguangguang
用户名：pgadmin
密码：postgres.env 中的 POSTGRES_PASSWORD
SSL：关闭
```

SQLAlchemy/psycopg 连接串：

```text
postgresql+psycopg://pgadmin:密码@127.0.0.1:15432/paiguangguang
```

本地 Docker 容器中的项目将主机改为 `host.docker.internal`：

```text
postgresql+psycopg://pgadmin:密码@host.docker.internal:15432/paiguangguang
```

## 4. 为其他项目创建数据库

```bash
docker exec -it postgres17 psql -U pgadmin -d postgres
```

在 PostgreSQL 中执行：

CREATE ROLE paiguangguang
WITH LOGIN
PASSWORD 'postgres@paiguangguang';

CREATE DATABASE knowledge_rag_agent
WITH OWNER paiguangguang
ENCODING 'UTF8';

REVOKE ALL ON DATABASE knowledge_rag_agent FROM PUBLIC;
GRANT CONNECT ON DATABASE knowledge_rag_agent TO paiguangguang;

CREATE DATABASE feishu_agent
WITH OWNER paiguangguang
ENCODING 'UTF8';

REVOKE ALL ON DATABASE feishu_agent FROM PUBLIC;
GRANT CONNECT ON DATABASE feishu_agent TO paiguangguang;


其他项目连接串：

```text
postgresql://other_project_user:密码@127.0.0.1:15432/other_project
```

初始化 `paiguangguang` 的表结构时，在本地 SSH 隧道已连接的情况下执行项目现有的 Alembic migration。
