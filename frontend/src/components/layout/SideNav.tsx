import AutoStoriesIcon from '@mui/icons-material/AutoStories'
import ChatIcon from '@mui/icons-material/Chat'
import AccountTreeIcon from '@mui/icons-material/AccountTree'
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import { Box, List, ListItemButton, ListItemIcon, ListItemText, Typography } from '@mui/material'
import { NavLink } from 'react-router-dom'

const items = [
  { to: '/memories', label: '记忆管理', icon: <AutoStoriesIcon /> },
  { to: '/upload', label: '记忆上传', icon: <UploadFileIcon /> },
  { to: '/chat', label: '知识对话', icon: <ChatIcon /> },
  { to: '/graph', label: '知识图谱', icon: <AccountTreeIcon /> },
  { to: '/settings', label: '设置', icon: <SettingsOutlinedIcon /> },
]

export function SideNav() {
  return (
    <Box
      sx={{
        width: 258,
        height: '100vh',
        flexShrink: 0,
        overflowY: 'auto',
        bgcolor: 'rgba(247, 245, 238, 0.95)',
        backgroundImage: 'linear-gradient(180deg, rgba(247,245,238,0.98) 0%, rgba(240,236,226,0.94) 100%)',
        color: '#141413',
        px: 2.25,
        py: 2.5,
        borderRight: '1px solid rgba(176, 174, 165, 0.3)',
      }}
    >
      <Box
        sx={{
          mb: 3.5,
          px: 0.75,
          py: 1.25,
        }}
      >
        <Box
          sx={{
            width: 72,
            height: 4,
            borderRadius: 999,
            mb: 1.25,
            background: 'linear-gradient(90deg, #d97757 0%, #6a9bcc 100%)',
            opacity: 0.9,
          }}
        />
        <Typography
          variant="h6"
          sx={{
            fontFamily: 'Poppins, Arial, sans-serif',
            fontWeight: 700,
            lineHeight: 1.15,
            letterSpacing: '-0.03em',
            color: '#141413',
          }}
        >
          个人知识库
        </Typography>
      </Box>
      <List>
        {items.map((item) => (
          <ListItemButton
            key={item.to}
            component={NavLink}
            to={item.to}
            sx={{
              borderRadius: 999,
              mb: 0.75,
              color: '#3f3b35',
              px: 1.5,
              py: 1.1,
              border: '1px solid transparent',
              transition: 'all 0.18s ease',
              '&:hover': {
                bgcolor: 'rgba(106, 155, 204, 0.1)',
                borderColor: 'rgba(106, 155, 204, 0.16)',
              },
              '&.active': {
                bgcolor: 'rgba(217, 119, 87, 0.14)',
                borderColor: 'rgba(217, 119, 87, 0.24)',
                color: '#141413',
                boxShadow: '0 8px 18px rgba(217, 119, 87, 0.08)',
              },
            }}
          >
            <ListItemIcon
              sx={{
                color: 'inherit',
                minWidth: 38,
                '.active &': {
                  color: '#d97757',
                },
              }}
            >
              {item.icon}
            </ListItemIcon>
            <ListItemText
              primary={item.label}
              primaryTypographyProps={{
                fontWeight: 600,
                fontFamily: 'Poppins, Arial, sans-serif',
              }}
            />
          </ListItemButton>
        ))}
      </List>
    </Box>
  )
}
