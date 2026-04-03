import { Box } from '@mui/material'
import { Outlet } from 'react-router-dom'

import { SideNav } from './SideNav'
import { TopBar } from './TopBar'

export function AppLayout() {
  return (
    <Box
      sx={{
        display: 'flex',
        height: '100vh',
        bgcolor: '#faf9f5',
        backgroundImage:
          'radial-gradient(circle at top left, rgba(232, 230, 220, 0.78), transparent 30%), linear-gradient(180deg, #faf9f5 0%, #f3efe4 100%)',
        overflow: 'hidden',
      }}
    >
      <SideNav />
      <Box sx={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <TopBar />
        <Box component="main" sx={{ px: { xs: 2, md: 4 }, py: { xs: 2, md: 3 }, flex: 1, minHeight: 0, overflow: 'hidden' }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  )
}
