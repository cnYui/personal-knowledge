import { AppBar, Box, Toolbar, Typography } from '@mui/material'

export function TopBar() {
  return (
    <AppBar position="static" color="transparent" elevation={0} sx={{ borderBottom: '1px solid #e5e7eb', bgcolor: '#fff' }}>
      <Toolbar>
        <Box>
          <Typography variant="h6" color="text.primary">
            个人知识库
          </Typography>
          <Typography variant="body2" color="text.secondary">
            管理你的学习记忆、上传资料并和知识库对话
          </Typography>
        </Box>
      </Toolbar>
    </AppBar>
  )
}
