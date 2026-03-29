import { CircularProgress, Stack, Typography } from '@mui/material'

export function LoadingState({ label }: { label: string }) {
  return (
    <Stack alignItems="center" justifyContent="center" spacing={2} sx={{ py: 8 }}>
      <CircularProgress />
      <Typography color="text.secondary">{label}</Typography>
    </Stack>
  )
}
