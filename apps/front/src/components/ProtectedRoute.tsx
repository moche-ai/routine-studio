import { useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation()
  const { user, token, checkAuth } = useAuthStore()
  const [isChecking, setIsChecking] = useState(true)

  useEffect(() => {
    const verify = async () => {
      if (token) {
        await checkAuth()
      }
      setIsChecking(false)
    }
    verify()
  }, [token, checkAuth])

  // 토큰 검증 중
  if (isChecking) {
    return (
      <div className="min-h-screen bg-zinc-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-emerald-500 animate-spin mx-auto mb-4" />
          <p className="text-zinc-400">인증 확인 중...</p>
        </div>
      </div>
    )
  }

  // 인증되지 않음 - 로그인 페이지로 리다이렉트
  if (!user || !token) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // 인증됨 - 자식 컴포넌트 렌더링
  return <>{children}</>
}
