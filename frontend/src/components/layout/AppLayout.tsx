import { Box } from '@mui/material'
import { Outlet } from 'react-router-dom'

import { SideNav } from './SideNav'
import { TopBar } from './TopBar'

export function AppLayout() {
  return (
    <Box sx={{ display: 'flex', height: '100vh', bgcolor: 'background.default', overflow: 'hidden' }}>
      <SideNav />
      <Box sx={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <TopBar />
        <Box component="main" sx={{ p: 3, flex: 1, minHeight: 0, overflow: 'hidden' }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  )
}
