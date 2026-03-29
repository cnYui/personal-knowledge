import { Stack, Typography } from '@mui/material'
import { ReactNode } from 'react'

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', md: 'center' }} spacing={2}>
      <Stack spacing={0.5}>
        <Typography variant="h4" fontWeight={700}>
          {title}
        </Typography>
        {description ? <Typography color="text.secondary">{description}</Typography> : null}
      </Stack>
      {actions}
    </Stack>
  )
}
