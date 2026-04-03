import { AppBar, Box, Toolbar, Typography } from '@mui/material'
import { useLocation } from 'react-router-dom'

const PAGE_META: Record<string, { title: string; description: string }> = {
  '/memories': {
    title: '记忆管理',
    description: '浏览、搜索和维护已经写入系统的知识记忆，并决定哪些内容继续进入知识图谱。',
  },
  '/upload': {
    title: '记忆上传',
    description: '先整理提示词，再上传文本和图片，让知识库更稳定地理解你的资料。',
  },
  '/chat': {
    title: '知识对话',
    description: '和知识库自然交流，系统会优先检索证据，再给出可解释的回答。',
  },
  '/graph': {
    title: '知识图谱',
    description: '查看记忆之间的关联结构，理解实体、关系和上下文在图谱中的连接方式。',
  },
  '/settings': {
    title: '设置',
    description: '统一管理对话模型与知识库构建模型的 API Key。保存后会写回 .env，并立即热更新当前后端服务。',
  },
}

export function TopBar({ centered = false }: { centered?: boolean }) {
  const location = useLocation()
  const pageMeta = PAGE_META[location.pathname] ?? PAGE_META['/memories']

  return (
    <AppBar
      position="sticky"
      color="transparent"
      elevation={0}
      sx={{
        top: 0,
        zIndex: (theme) => theme.zIndex.drawer + 1,
        borderBottom: '1px solid rgba(176, 174, 165, 0.24)',
        bgcolor: 'rgba(250, 249, 245, 0.88)',
        backdropFilter: 'blur(10px)',
      }}
    >
      <Toolbar
        sx={{
          minHeight: 120,
          px: { xs: 2, md: 4 },
          justifyContent: centered ? 'center' : 'flex-start',
          transition: 'all 240ms ease',
        }}
      >
        <Box
          sx={{
            px: 0.25,
            pt: 2,
            pb: 1,
            width: '100%',
            maxWidth: centered ? 1340 : 'none',
            transition: 'max-width 240ms ease',
          }}
        >
          <Typography
            variant="h5"
            color="text.primary"
            sx={{ fontWeight: 700, letterSpacing: '-0.04em', lineHeight: 1.02 }}
          >
            {pageMeta.title}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.65, maxWidth: 760, lineHeight: 1.65 }}>
            {pageMeta.description}
          </Typography>
        </Box>
      </Toolbar>
    </AppBar>
  )
}
