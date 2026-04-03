import { CssBaseline, ThemeProvider, createTheme } from '@mui/material'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { PropsWithChildren, useState } from 'react'

import { AppToastProvider } from '../components/common/AppToastProvider'

export function AppProviders({ children }: PropsWithChildren) {
  const [queryClient] = useState(() => new QueryClient())
  const [theme] = useState(() =>
    createTheme({
      palette: {
        mode: 'light',
        primary: { main: '#141413', contrastText: '#faf9f5' },
        secondary: { main: '#d97757' },
        background: { default: '#faf9f5', paper: '#fffdf8' },
        text: {
          primary: '#141413',
          secondary: '#6f6a61',
        },
        divider: 'rgba(176, 174, 165, 0.35)',
      },
      shape: { borderRadius: 6 },
      typography: {
        fontFamily: 'Lora, Georgia, serif',
        h4: {
          fontFamily: 'Poppins, Arial, sans-serif',
          fontWeight: 700,
          letterSpacing: '-0.045em',
          fontSize: '3.25rem',
          lineHeight: 1.02,
        },
        h5: {
          fontFamily: 'Poppins, Arial, sans-serif',
          fontWeight: 700,
          letterSpacing: '-0.035em',
          fontSize: '2.4rem',
          lineHeight: 1.08,
        },
        h6: {
          fontFamily: 'Poppins, Arial, sans-serif',
          fontWeight: 700,
          letterSpacing: '-0.02em',
        },
        subtitle1: {
          fontFamily: 'Poppins, Arial, sans-serif',
          fontWeight: 600,
        },
        subtitle2: {
          fontFamily: 'Poppins, Arial, sans-serif',
          fontWeight: 600,
        },
        button: {
          fontFamily: 'Poppins, Arial, sans-serif',
          fontWeight: 600,
          textTransform: 'none',
          letterSpacing: '-0.01em',
        },
        caption: {
          fontFamily: 'Poppins, Arial, sans-serif',
          letterSpacing: '0.01em',
        },
      },
      components: {
        MuiCssBaseline: {
          styleOverrides: {
            ':root': {
              colorScheme: 'light',
            },
            body: {
              backgroundColor: '#faf9f5',
              color: '#141413',
              backgroundImage:
                'radial-gradient(circle at top left, rgba(232, 230, 220, 0.75), transparent 34%), linear-gradient(180deg, #faf9f5 0%, #f4f1e8 100%)',
            },
            '::selection': {
              backgroundColor: 'rgba(217, 119, 87, 0.2)',
            },
          },
        },
        MuiPaper: {
          styleOverrides: {
            root: {
              backgroundImage: 'none',
              borderColor: 'rgba(176, 174, 165, 0.28)',
            },
          },
        },
        MuiButton: {
          defaultProps: {
            disableElevation: true,
          },
          styleOverrides: {
            root: {
              borderRadius: 6,
              paddingInline: 20,
              paddingBlock: 10,
            },
            contained: {
              backgroundColor: '#141413',
              color: '#faf9f5',
              boxShadow: '0 12px 28px rgba(20, 20, 19, 0.12)',
              '&:hover': {
                backgroundColor: '#20201e',
                boxShadow: '0 16px 30px rgba(20, 20, 19, 0.16)',
              },
            },
            outlined: {
              borderColor: 'rgba(176, 174, 165, 0.45)',
              color: '#141413',
              backgroundColor: 'rgba(255, 253, 248, 0.72)',
              '&:hover': {
                borderColor: 'rgba(20, 20, 19, 0.32)',
                backgroundColor: 'rgba(232, 230, 220, 0.4)',
              },
            },
          },
        },
        MuiChip: {
          styleOverrides: {
            root: {
              borderRadius: 4,
              fontFamily: 'Poppins, Arial, sans-serif',
              fontWeight: 600,
              backgroundColor: 'rgba(232, 230, 220, 0.68)',
              color: '#59544c',
            },
          },
        },
        MuiAlert: {
          styleOverrides: {
            root: {
              borderRadius: 4,
              border: '1px solid rgba(176, 174, 165, 0.24)',
            },
          },
        },
        MuiTextField: {
          defaultProps: {
            variant: 'outlined',
          },
        },
        MuiOutlinedInput: {
          styleOverrides: {
            root: {
              borderRadius: 6,
              backgroundColor: 'rgba(255, 253, 248, 0.88)',
              transition: 'border-color 160ms ease, box-shadow 160ms ease, background-color 160ms ease',
              '&:hover': {
                backgroundColor: 'rgba(255, 253, 248, 0.96)',
              },
              '&.Mui-focused': {
                boxShadow: '0 0 0 4px rgba(217, 119, 87, 0.08)',
              },
            },
            notchedOutline: {
              borderColor: 'rgba(176, 174, 165, 0.36)',
            },
          },
        },
        MuiAccordion: {
          styleOverrides: {
            root: {
              boxShadow: 'none',
            },
          },
        },
        MuiIconButton: {
          styleOverrides: {
            root: {
              color: '#59544c',
            },
          },
        },
      },
    }),
  )

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <AppToastProvider>
          <CssBaseline />
          {children}
        </AppToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
