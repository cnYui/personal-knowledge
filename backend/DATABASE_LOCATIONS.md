# 数据库存储位置说明

## SQLite 数据库 (记忆数据)

### 位置
```
D:\CodeWorkSpace\personal-knowledge-base\backend\app.db
```

### 配置
- **配置文件**: `app/core/config.py`
- **连接字符串**: `sqlite:///./app.db`
- **相对路径**: `./app.db` (相对于 backend 目录)

### 存储内容
- 记忆表 (memory)
  - id, title, title_status, content, group_id
  - created_at, updated_at
  - graph_status, graph_episode_uuid, graph_added_at, graph_error
- 图片表 (memory_image)
  - id, memory_id, original_file_name, stored_path
  - ocr_text, image_description

### 文件大小
- 当前大小: 40 KB (空数据库)
- 会随着数据增长而增大

### 备份方式
```bash
# 备份数据库
cp backend/app.db backend/app.db.backup

# 恢复数据库
cp backend/app.db.backup backend/app.db
```

---

## Neo4j 图数据库 (知识图谱)

### 位置
**Docker Volume**: `personal-knowledge-base_neo4j_data`

**实际路径** (Windows):
```
C:\ProgramData\Docker\volumes\personal-knowledge-base_neo4j_data\_data
```

### 配置
- **连接 URI**: `bolt://localhost:7687`
- **用户名**: `neo4j`
- **密码**: `password`
- **HTTP 端口**: 7474 (Neo4j Browser)
- **Bolt 端口**: 7687 (应用连接)

### 存储内容
- Episodic 节点 (记忆片段)
- Entity 节点 (实体)
- RELATES_TO 关系 (实体关系)
- 全文索引

### 查看数据
1. 打开浏览器访问: http://localhost:7474
2. 登录: neo4j / password
3. 运行 Cypher 查询:
   ```cypher
   MATCH (n) RETURN n LIMIT 25
   ```

### 备份方式
```bash
# 导出 volume
docker run --rm -v personal-knowledge-base_neo4j_data:/data -v $(pwd):/backup alpine tar czf /backup/neo4j_backup.tar.gz /data

# 恢复 volume
docker run --rm -v personal-knowledge-base_neo4j_data:/data -v $(pwd):/backup alpine tar xzf /backup/neo4j_backup.tar.gz -C /
```

---

## 上传文件存储

### 位置
```
D:\CodeWorkSpace\personal-knowledge-base\backend\uploads\images\
```

### 配置
- **配置文件**: `app/core/config.py`
- **配置项**: `upload_dir = "backend/uploads/images"`

### 存储内容
- 用户上传的图片文件
- 文件名格式: `{timestamp}_{original_filename}`

### 备份方式
```bash
# 备份上传文件
cp -r backend/uploads backend/uploads.backup

# 恢复上传文件
cp -r backend/uploads.backup backend/uploads
```

---

## 完整备份策略

### 1. 备份所有数据
```bash
# 创建备份目录
mkdir -p backups/$(date +%Y%m%d)

# 备份 SQLite
cp backend/app.db backups/$(date +%Y%m%d)/app.db

# 备份上传文件
cp -r backend/uploads backups/$(date +%Y%m%d)/uploads

# 备份 Neo4j (需要 Docker)
docker exec pkb-neo4j neo4j-admin database dump neo4j --to-path=/backups
docker cp pkb-neo4j:/backups/neo4j.dump backups/$(date +%Y%m%d)/
```

### 2. 恢复所有数据
```bash
# 恢复 SQLite
cp backups/20260329/app.db backend/app.db

# 恢复上传文件
cp -r backups/20260329/uploads backend/uploads

# 恢复 Neo4j
docker cp backups/20260329/neo4j.dump pkb-neo4j:/backups/
docker exec pkb-neo4j neo4j-admin database load neo4j --from-path=/backups
```

---

## 清空数据

### 使用脚本清空
```bash
cd backend
python clear_database.py
```

### 手动清空
```bash
# 删除 SQLite 数据库
rm backend/app.db

# 删除上传文件
rm -rf backend/uploads/images/*

# 清空 Neo4j
docker-compose down -v
docker-compose up -d
```

---

## 数据迁移

### 从开发环境到生产环境
1. 备份开发环境数据
2. 复制 `app.db` 到生产服务器
3. 复制 `uploads/` 目录到生产服务器
4. 导出/导入 Neo4j 数据

### 注意事项
- SQLite 数据库文件可以直接复制
- Neo4j 需要使用 dump/load 命令
- 上传文件需要保持目录结构
- 确保文件权限正确

---

**更新时间**: 2026-03-29  
**数据库版本**: SQLite 3, Neo4j 5.26.0
