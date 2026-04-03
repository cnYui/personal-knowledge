import { Box } from '@mui/material'
import { useState } from 'react'
import { Outlet } from 'react-router-dom'

import { SideNav } from './SideNav'
import { TopBar } from './TopBar'

const NAV_COLLAPSED_STORAGE_KEY = 'pkb_nav_collapsed'

export function AppLayout() {
  const [navCollapsed, setNavCollapsed] = useState(() => {
    if (typeof window === 'undefined') {
      return false
    }
    return window.localStorage.getItem(NAV_COLLAPSED_STORAGE_KEY) === '1'
  })

  const handleSetCollapsed = (nextValue: boolean) => {
    setNavCollapsed(nextValue)
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(NAV_COLLAPSED_STORAGE_KEY, nextValue ? '1' : '0')
    }
  }

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
      <SideNav collapsed={navCollapsed} onToggle={() => handleSetCollapsed(!navCollapsed)} />
      <Box
        sx={{
          flex: 1,
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          position: 'relative',
          transition: 'padding 240ms ease, width 240ms ease',
        }}
      >
        <TopBar centered={navCollapsed} />
        <Box
          component="main"
          sx={{
            px: { xs: 2, md: 4 },
            py: { xs: 2, md: 3 },
            flex: 1,
            minHeight: 0,
            overflow: 'hidden',
            display: 'flex',
            justifyContent: navCollapsed ? 'center' : 'stretch',
            transition: 'all 240ms ease',
          }}
        >
          <Box
            sx={{
              width: '100%',
              maxWidth: navCollapsed ? 1340 : 'none',
              transition: 'max-width 240ms ease',
            }}
          >
            <Outlet />
          </Box>
        </Box>
      </Box>
    </Box>
  )
}
