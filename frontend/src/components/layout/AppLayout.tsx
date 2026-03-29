import { Box } from '@mui/material'
import { Outlet } from 'react-router-dom'

import { SideNav } from './SideNav'
import { TopBar } from './TopBar'

export function AppLayout() {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <SideNav />
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <TopBar />
        <Box component="main" sx={{ p: 3, flex: 1 }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  )
}
