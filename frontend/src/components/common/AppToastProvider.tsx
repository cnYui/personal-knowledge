import { Alert, Snackbar } from '@mui/material'
import { createContext, PropsWithChildren, useCallback, useContext, useMemo, useState } from 'react'

type ToastSeverity = 'success' | 'info' | 'warning' | 'error'

interface ToastState {
  open: boolean
  message: string
  severity: ToastSeverity
}

interface AppToastContextValue {
  showToast: (input: { message: string; severity?: ToastSeverity }) => void
}

const AppToastContext = createContext<AppToastContextValue | null>(null)

export function AppToastProvider({ children }: PropsWithChildren) {
  const [toast, setToast] = useState<ToastState>({
    open: false,
    message: '',
    severity: 'info',
  })

  const showToast = useCallback(({ message, severity = 'info' }: { message: string; severity?: ToastSeverity }) => {
    setToast({
      open: true,
      message,
      severity,
    })
  }, [])

  const value = useMemo(() => ({ showToast }), [showToast])

  return (
    <AppToastContext.Provider value={value}>
      {children}
      <Snackbar
        open={toast.open}
        autoHideDuration={4200}
        onClose={() => setToast((prev) => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <Alert
          severity={toast.severity}
          variant="filled"
          onClose={() => setToast((prev) => ({ ...prev, open: false }))}
          sx={{ width: '100%', alignItems: 'center' }}
        >
          {toast.message}
        </Alert>
      </Snackbar>
    </AppToastContext.Provider>
  )
}

export function useAppToast() {
  const context = useContext(AppToastContext)
  if (!context) {
    throw new Error('useAppToast must be used within AppToastProvider')
  }
  return context
}
