import { createBrowserRouter, Navigate } from 'react-router-dom'

import { AppLayout } from '../components/layout/AppLayout'
import { KnowledgeChatPage } from '../pages/KnowledgeChatPage'
import { MemoryManagementPage } from '../pages/MemoryManagementPage'
import { MemoryUploadPage } from '../pages/MemoryUploadPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/memories" replace /> },
      { path: 'memories', element: <MemoryManagementPage /> },
      { path: 'upload', element: <MemoryUploadPage /> },
      { path: 'chat', element: <KnowledgeChatPage /> },
    ],
  },
])
