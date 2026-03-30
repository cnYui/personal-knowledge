import AutoStoriesIcon from '@mui/icons-material/AutoStories'
import ChatIcon from '@mui/icons-material/Chat'
import AccountTreeIcon from '@mui/icons-material/AccountTree'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import { Box, List, ListItemButton, ListItemIcon, ListItemText, Typography } from '@mui/material'
import { NavLink } from 'react-router-dom'

const items = [
  { to: '/memories', label: '记忆管理', icon: <AutoStoriesIcon /> },
  { to: '/upload', label: '记忆上传', icon: <UploadFileIcon /> },
  { to: '/chat', label: '知识对话', icon: <ChatIcon /> },
  { to: '/graph', label: '知识图谱', icon: <AccountTreeIcon /> },
]

export function SideNav() {
  return (
    <Box
      sx={{
        width: 240,
        height: '100vh',
        flexShrink: 0,
        overflowY: 'auto',
        bgcolor: '#111827',
        color: '#fff',
        px: 2,
        py: 3,
      }}
    >
      <Typography variant="h6" sx={{ mb: 3, fontWeight: 700 }}>
        Knowledge Base
      </Typography>
      <List>
        {items.map((item) => (
          <ListItemButton
            key={item.to}
            component={NavLink}
            to={item.to}
            sx={{ borderRadius: 2, mb: 1, color: '#fff', '&.active': { bgcolor: 'rgba(255,255,255,0.12)' } }}
          >
            <ListItemIcon sx={{ color: 'inherit', minWidth: 36 }}>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
    </Box>
  )
}
