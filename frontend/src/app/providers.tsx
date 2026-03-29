import { CssBaseline, ThemeProvider, createTheme } from '@mui/material'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PropsWithChildren, useState } from 'react'

export function AppProviders({ children }: PropsWithChildren) {
  const [queryClient] = useState(() => new QueryClient())
  const [theme] = useState(() =>
    createTheme({
      palette: {
        mode: 'light',
        primary: { main: '#1976d2' },
        background: { default: '#f5f7fb' },
      },
      shape: { borderRadius: 12 },
    }),
  )

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  )
}
