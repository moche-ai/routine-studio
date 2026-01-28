import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { MainLayout } from './layouts/MainLayout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { LoginPage } from './pages/LoginPage'
import { HomePage } from './pages/HomePage'
import { ChannelsPage } from './pages/ChannelsPage'
import { ChannelChatPage } from './pages/ChannelChatPage'
import { ChannelDetailPage } from './pages/ChannelDetailPage'
import { ChannelSetupPage } from './pages/ChannelSetupPage'
import { ProjectDetailPage } from './pages/ProjectDetailPage'
import { VideoEditorPage } from './pages/VideoEditorPage'

const router = createBrowserRouter([
  // 로그인 (인증 불필요)
  {
    path: '/login',
    element: <LoginPage />
  },
  // 메인 앱 (인증 필요)
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <HomePage /> },
      // 채널 관리
      { path: 'channels', element: <ChannelsPage /> },
      { path: 'channels/new', element: <ChannelChatPage /> },
      { path: 'channels/:channelId', element: <ChannelDetailPage /> },
      { path: 'channels/:channelId/setup', element: <ChannelSetupPage /> },
      // 프로젝트 (채널 내)
      { path: 'projects/:projectId', element: <ProjectDetailPage /> },
      { path: 'projects/:projectId/editor', element: <VideoEditorPage /> },
    ]
  }
])

export function Router() {
  return <RouterProvider router={router} />
}
