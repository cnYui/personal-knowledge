import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { CircularProgress, Stack } from '@mui/material'

import { AppLayout } from '../components/layout/AppLayout'

const KnowledgeChatPage = lazy(() =>
  import('../pages/KnowledgeChatPage').then((module) => ({ default: module.KnowledgeChatPage })),
)
const KnowledgeGraphPage = lazy(() =>
  import('../pages/KnowledgeGraphPage').then((module) => ({ default: module.KnowledgeGraphPage })),
)
const MemoryManagementPage = lazy(() =>
  import('../pages/MemoryManagementPage').then((module) => ({ default: module.MemoryManagementPage })),
)
const MemoryUploadPage = lazy(() =>
  import('../pages/MemoryUploadPage').then((module) => ({ default: module.MemoryUploadPage })),
)
const SettingsPage = lazy(() =>
  import('../pages/SettingsPage').then((module) => ({ default: module.SettingsPage })),
)
const DailyReviewPage = lazy(() =>
  import('../pages/DailyReviewPage').then((module) => ({ default: module.DailyReviewPage })),
)

function PageFallback() {
  return (
    <Stack alignItems="center" justifyContent="center" sx={{ minHeight: 240 }}>
      <CircularProgress />
    </Stack>
  )
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/memories" replace /> },
      {
        path: 'memories',
        element: (
          <Suspense fallback={<PageFallback />}>
            <MemoryManagementPage />
          </Suspense>
        ),
      },
      {
        path: 'upload',
        element: (
          <Suspense fallback={<PageFallback />}>
            <MemoryUploadPage />
          </Suspense>
        ),
      },
      {
        path: 'chat',
        element: (
          <Suspense fallback={<PageFallback />}>
            <KnowledgeChatPage />
          </Suspense>
        ),
      },
      {
        path: 'graph',
        element: (
          <Suspense fallback={<PageFallback />}>
            <KnowledgeGraphPage />
          </Suspense>
        ),
      },
      {
        path: 'daily-review',
        element: (
          <Suspense fallback={<PageFallback />}>
            <DailyReviewPage />
          </Suspense>
        ),
      },
      {
        path: 'settings',
        element: (
          <Suspense fallback={<PageFallback />}>
            <SettingsPage />
          </Suspense>
        ),
      },
    ],
  },
])
