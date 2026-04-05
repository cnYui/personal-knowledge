import { SxProps, Theme } from '@mui/material'

export const unifiedCardSx: SxProps<Theme> = {
  borderRadius: 0.9,
  border: '1px solid',
  borderColor: 'divider',
  boxShadow: '0 16px 34px rgba(20, 20, 19, 0.05)',
  backgroundColor: '#fffdf8',
  backgroundImage: 'none',
}

export const unifiedCardHoverSx: SxProps<Theme> = {
  transition: 'transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease, background-color 180ms ease',
  '&:hover': {
    transform: 'translateY(-2px)',
    boxShadow: '0 18px 34px rgba(20, 20, 19, 0.08)',
    borderColor: 'rgba(20, 20, 19, 0.28)',
    backgroundColor: '#fffdf8',
  },
}

export const unifiedCardMutedBackground = '#fffdf8'