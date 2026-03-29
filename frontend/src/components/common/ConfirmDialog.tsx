import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Typography } from '@mui/material'

export function ConfirmDialog({
  open,
  title,
  description,
  onClose,
  onConfirm,
}: {
  open: boolean
  title: string
  description: string
  onClose: () => void
  onConfirm: () => void
}) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Typography color="text.secondary">{description}</Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>取消</Button>
        <Button color="error" variant="contained" onClick={onConfirm}>
          确认
        </Button>
      </DialogActions>
    </Dialog>
  )
}
