import AutoStoriesIcon from '@mui/icons-material/AutoStories'
import ChatIcon from '@mui/icons-material/Chat'
import AccountTreeIcon from '@mui/icons-material/AccountTree'
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft'
import ChevronRightIcon from '@mui/icons-material/ChevronRight'
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import { Box, IconButton, List, ListItemButton, ListItemIcon, ListItemText, Tooltip, Typography } from '@mui/material'
import { NavLink } from 'react-router-dom'

const items = [
  { to: '/memories', label: '记忆管理', icon: <AutoStoriesIcon /> },
  { to: '/upload', label: '记忆上传', icon: <UploadFileIcon /> },
  { to: '/chat', label: '知识对话', icon: <ChatIcon /> },
  { to: '/graph', label: '知识图谱', icon: <AccountTreeIcon /> },
  { to: '/settings', label: '设置', icon: <SettingsOutlinedIcon /> },
]

export function SideNav({
  collapsed,
  onToggle,
}: {
  collapsed: boolean
  onToggle: () => void
}) {
  const railWidth = 84
  const expandedWidth = 258

  return (
    <Box
      sx={{
        width: collapsed ? railWidth : expandedWidth,
        height: '100vh',
        flexShrink: 0,
        overflow: 'hidden',
        bgcolor: 'rgba(247, 245, 238, 0.95)',
        backgroundImage: 'linear-gradient(180deg, rgba(247,245,238,0.98) 0%, rgba(240,236,226,0.94) 100%)',
        color: '#141413',
        borderRight: '1px solid rgba(176, 174, 165, 0.3)',
        transition: 'width 240ms ease, border-color 240ms ease',
        borderColor: 'rgba(176, 174, 165, 0.3)',
      }}
    >
      <Box
        sx={{
          width: collapsed ? railWidth : expandedWidth,
          height: '100%',
          px: collapsed ? 1 : 2.25,
          py: 2.5,
          overflowY: 'auto',
        }}
      >
        <Box
          sx={{
            mb: 3.5,
            px: collapsed ? 0 : 0.75,
            py: 1.25,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'space-between',
          }}
        >
          {collapsed ? null : (
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
          )}
          <IconButton
            aria-label={collapsed ? '展开侧边栏' : '收起侧边栏'}
            onClick={onToggle}
            sx={{
              borderRadius: 0.75,
              border: '1px solid rgba(176, 174, 165, 0.24)',
              bgcolor: 'rgba(255, 253, 248, 0.82)',
              '&:hover': {
                bgcolor: 'rgba(255, 253, 248, 0.96)',
              },
            }}
          >
            {collapsed ? <ChevronRightIcon /> : <ChevronLeftIcon />}
          </IconButton>
        </Box>
        <List>
          {items.map((item) => (
            <Tooltip key={item.to} title={collapsed ? item.label : ''} placement="right" arrow>
              <ListItemButton
                component={NavLink}
                to={item.to}
                sx={{
                  borderRadius: 0.75,
                  mb: 0.75,
                  color: '#3f3b35',
                  px: collapsed ? 1 : 1.5,
                  py: 1.1,
                  minHeight: 52,
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  border: '1px solid transparent',
                  transition: 'all 0.18s ease',
                  '&:hover': {
                    bgcolor: 'rgba(232, 230, 220, 0.52)',
                  },
                  '&.active': {
                    bgcolor: 'rgba(232, 230, 220, 0.7)',
                    borderColor: 'rgba(176, 174, 165, 0.4)',
                    color: '#141413',
                  },
                }}
              >
                <ListItemIcon
                  sx={{
                    color: 'inherit',
                    minWidth: collapsed ? 'auto' : 38,
                    justifyContent: 'center',
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                {collapsed ? null : (
                  <ListItemText
                    primary={item.label}
                    primaryTypographyProps={{
                      fontWeight: 600,
                      fontFamily: 'Poppins, Arial, sans-serif',
                    }}
                  />
                )}
              </ListItemButton>
            </Tooltip>
          ))}
        </List>
      </Box>
    </Box>
  )
}
