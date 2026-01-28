import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogIn, UserPlus, Loader2, AlertCircle, Youtube } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'

export function LoginPage() {
  const navigate = useNavigate()
  const { login, register, isLoading, error, clearError } = useAuthStore()
  
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [validationError, setValidationError] = useState('')

  const validate = () => {
    if (username.length < 3 || username.length > 15) {
      setValidationError('아이디는 3~15자로 입력해주세요')
      return false
    }
    if (password.length < 3 || password.length > 15) {
      setValidationError('비밀번호는 3~15자로 입력해주세요')
      return false
    }
    setValidationError('')
    return true
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    
    if (!validate()) return
    
    let success = false
    if (mode === 'login') {
      success = await login(username, password)
    } else {
      success = await register(username, password, name || undefined)
    }
    
    if (success) {
      navigate('/')
    }
  }

  const toggleMode = () => {
    setMode(mode === 'login' ? 'register' : 'login')
    clearError()
    setValidationError('')
  }

  const displayError = validationError || error

  return (
    <div className="min-h-screen bg-zinc-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-emerald-600 rounded-2xl mb-4">
            <Youtube className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Routine Studio</h1>
          <p className="text-zinc-500 mt-1">YouTube 콘텐츠 자동화 플랫폼</p>
        </div>

        {/* Form */}
        <div className="bg-zinc-800/50 rounded-2xl p-6">
          <h2 className="text-xl font-semibold text-white mb-6 text-center">
            {mode === 'login' ? '로그인' : '회원가입'}
          </h2>

          {displayError && (
            <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm mb-4">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{displayError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-1.5">
                  이름 (선택)
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="홍길동"
                  className="w-full px-4 py-3 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors"
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-1.5">
                아이디
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="아이디"
                required
                minLength={3}
                maxLength={15}
                className="w-full px-4 py-3 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-1.5">
                비밀번호
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="비밀번호"
                required
                minLength={3}
                maxLength={15}
                className="w-full px-4 py-3 bg-zinc-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500 transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/50 disabled:cursor-not-allowed rounded-lg text-white font-medium transition-colors"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : mode === 'login' ? (
                <>
                  <LogIn className="w-5 h-5" />
                  로그인
                </>
              ) : (
                <>
                  <UserPlus className="w-5 h-5" />
                  가입하기
                </>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={toggleMode}
              className="text-sm text-zinc-400 hover:text-emerald-400 transition-colors"
            >
              {mode === 'login' ? (
                <>계정이 없으신가요? <span className="text-emerald-400">회원가입</span></>
              ) : (
                <>이미 계정이 있으신가요? <span className="text-emerald-400">로그인</span></>
              )}
            </button>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-zinc-600 text-sm mt-6">
          © 2026 Routine Studio. All rights reserved.
        </p>
      </div>
    </div>
  )
}
