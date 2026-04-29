## 背景

- 当前 chat 小分支在完成测试和构建后，worktree 会反复出现以下本地产物：
  - `.codex-runtime/` 日志目录
  - `backend/test-*.db` 临时数据库
  - `frontend/*.tsbuildinfo` TypeScript 增量构建缓存
- 这些文件不属于交付物，但会持续污染 `git status`，导致手动提交流程很难判断是否还有真实未提交改动。

## 决策

- `.codex-runtime/` 和 `backend/test-*.db` 统一加入忽略规则。
- `frontend/tsconfig.tsbuildinfo` 与 `frontend/tsconfig.node.tsbuildinfo` 已经在 `.gitignore` 中声明，应从版本控制中移除，避免每次构建后再次产生脏改动。

## 原因

- 这些文件都由本地运行、测试或构建生成，不应该参与评审和提交。
- 继续把 `tsbuildinfo` 保留为 tracked 文件，会让“测试通过”与“工作区干净”互相冲突，属于仓库层面的错误边界。

## 验证方式

- 清理索引中的 `frontend/*.tsbuildinfo`
- 删除已生成的本地产物
- 再次执行 `git status --short`，确认只剩真实代码改动
