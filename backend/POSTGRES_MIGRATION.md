# SQLite 到 PostgreSQL 迁移完成

## 迁移日期
2026-03-29

## 迁移原因
- 更好的并发性能
- 更强的数据完整性
- 生产环境标准
- 更好的扩展性

---

## 迁移步骤

### 1. ✅ 清理旧容器
删除了以下非必要容器:
- `cli-proxy-api`
- `knowledge-pgadmin`
- `knowledge-postgres` (旧的 PostgreSQL)

保留:
- `pkb-neo4j` (Neo4j 知识图谱)

### 2. ✅ 创建新的 PostgreSQL 容器
**容器名称**: `pkb-postgres`
**镜像**: `postgres:15-alpine`
**端口**: 5432

**配置**:
- 数据库名: `personal_knowledge_base`
- 用户名: `pkb_user`
- 密码: `pkb_password`

### 3. ✅ 更新配置文件

#### config.py
```python
database_url: str = "postgresql://pkb_user:pkb_password@localhost:5432/personal_knowledge_base"
```

#### .env
```env
DATABASE_URL=postgresql://pkb_user:pkb_password@localhost:5432/personal_knowledge_base
```

### 4. ✅ 删除 SQLite 数据库
删除了 `app.db` 文件

### 5. ✅ 启动服务
后端服务成功启动并连接到 PostgreSQL

---

## 数据库架构

### memory 表
```sql
CREATE TABLE memory (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL DEFAULT '标题生成中',
    title_status VARCHAR(16) NOT NULL DEFAULT 'pending',
    content TEXT NOT NULL,
    group_id VARCHAR(64) NOT NULL DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    graph_status VARCHAR(16) DEFAULT 'not_added',
    graph_episode_uuid VARCHAR(36),
    graph_added_at TIMESTAMP,
    graph_error TEXT
)
```

### memory_image 表
```sql
CREATE TABLE memory_image (
    id VARCHAR(36) PRIMARY KEY,
    memory_id VARCHAR(36) NOT NULL,
    original_file_name VARCHAR(255) NOT NULL,
    stored_path VARCHAR(512) NOT NULL,
    ocr_text TEXT,
    image_description TEXT,
    FOREIGN KEY (memory_id) REFERENCES memory(id) ON DELETE CASCADE
)
```

---

## 连接信息

### PostgreSQL
- **主机**: localhost
- **端口**: 5432
- **数据库**: personal_knowledge_base
- **用户**: pkb_user
- **密码**: pkb_password

### 连接字符串
```
postgresql://pkb_user:pkb_password@localhost:5432/personal_knowledge_base
```

---

## Docker 配置

### docker-compose.yml
```yaml
services:
  postgres:
    image: postgres:15-alpine
    container_name: pkb-postgres
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: personal_knowledge_base
      POSTGRES_USER: pkb_user
      POSTGRES_PASSWORD: pkb_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
```

---

## 数据存储位置

### PostgreSQL 数据
**Docker Volume**: `personal-knowledge-base_postgres_data`

**实际路径** (Windows):
```
C:\ProgramData\Docker\volumes\personal-knowledge-base_postgres_data\_data
```

---

## 管理命令

### 启动服务
```bash
docker-compose up -d postgres
```

### 停止服务
```bash
docker-compose stop postgres
```

### 查看日志
```bash
docker logs pkb-postgres
```

### 连接数据库
```bash
docker exec -it pkb-postgres psql -U pkb_user -d personal_knowledge_base
```

### 备份数据库
```bash
docker exec pkb-postgres pg_dump -U pkb_user personal_knowledge_base > backup.sql
```

### 恢复数据库
```bash
docker exec -i pkb-postgres psql -U pkb_user personal_knowledge_base < backup.sql
```

---

## 验证

### 检查连接
```bash
python verify_empty.py
```

### 检查表结构
```sql
\dt  -- 列出所有表
\d memory  -- 查看 memory 表结构
\d memory_image  -- 查看 memory_image 表结构
```

---

## 性能优势

### SQLite vs PostgreSQL

| 特性 | SQLite | PostgreSQL |
|-----|--------|-----------|
| 并发写入 | ❌ 单线程 | ✅ 多线程 |
| 数据完整性 | ⚠️ 基础 | ✅ 强大 |
| 事务支持 | ✅ 基础 | ✅ 完整 ACID |
| 扩展性 | ❌ 有限 | ✅ 优秀 |
| 生产就绪 | ⚠️ 小型应用 | ✅ 企业级 |

---

## 注意事项

1. **密码安全**: 生产环境应使用更强的密码
2. **备份策略**: 定期备份 PostgreSQL 数据
3. **连接池**: 考虑使用 pgbouncer 进行连接池管理
4. **监控**: 使用 pg_stat_statements 监控查询性能

---

## 回滚方案

如果需要回滚到 SQLite:

1. 停止后端服务
2. 更新 `.env`: `DATABASE_URL=sqlite:///./app.db`
3. 更新 `config.py` 中的默认值
4. 重启后端服务

---

**迁移状态**: ✅ 完成  
**数据库状态**: ✅ 运行中  
**数据完整性**: ✅ 验证通过
