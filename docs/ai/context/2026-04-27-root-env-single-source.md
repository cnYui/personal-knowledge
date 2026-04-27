# 根目录环境变量作为唯一配置源

日期：2026-04-27

## 背景

项目曾同时存在根目录 `.env`、`backend/.env`、`backend/.env.example` 等配置入口。设置页保存模型配置时写入 `backend/.env`，Docker Compose 则读取根目录 `.env`，导致同一字段出现不同值。

实际问题已经出现：

- 根目录 `.env` 中 `KNOWLEDGE_BUILD_REASONING_EFFORT=xhigh`
- `backend/.env` 中 `KNOWLEDGE_BUILD_REASONING_EFFORT=medium`
- 当前运行时和 Docker 重建后的行为可能不一致

## 决策

根目录 `.env` 是唯一运行时配置源。

保留：

- `.env`
- `.env.example`

废弃：

- `backend/.env`
- `backend/.env.example`
- `frontend/.env` 作为长期配置源

## 实现原则

- 后端本地运行默认读取项目根目录 `.env`
- Docker 后端通过 `PKB_ENV_FILE=/workspace/.env` 读取同一份根目录 `.env`
- 设置页模型配置更新写回根目录 `.env`
- `DATABASE_URL` 和 `NEO4J_URI` 在宿主机直跑时使用 `.env` 中的 `localhost` 地址
- Docker 容器内的 `DATABASE_URL` 和 `NEO4J_URI` 由 Compose 注入容器网络地址，避免容器内访问 `localhost` 指向自身

## 取舍

模型 API 配置必须只有一份真实来源，因为设置页会热更新这些字段。

数据库和 Neo4j 地址存在宿主机与容器网络差异，因此 Docker Compose 可以对容器进程注入运行地址，但这不改变用户可编辑配置的唯一来源。

## 后续约束

新增环境变量时只更新根目录 `.env.example`。

不要再新增 `backend/.env.example` 或让后端写回 `backend/.env`。
