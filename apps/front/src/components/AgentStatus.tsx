import { useEffect, useState } from 'react'
import { Check, X, CheckCircle, Circle, Loader2 } from 'lucide-react'

interface StatusStep {
  id: string
  label: string
  status: 'pending' | 'running' | 'completed' | 'error'
  detail?: string
  duration?: number
}

interface Props {
  currentStep: string
  isLoading: boolean
}

const WORKFLOW_STEPS: StatusStep[] = [
  { id: 'channel_name', label: '채널명 생성', status: 'pending', detail: 'LLM으로 채널명 후보 생성' },
  { id: 'benchmarking', label: '벤치마킹', status: 'pending', detail: '채널 벤치마킹 분석' },
  { id: 'character', label: '캐릭터 생성', status: 'pending', detail: 'ComfyUI로 이미지 생성' },
  { id: 'tts_settings', label: '음성 설정', status: 'pending', detail: 'TTS 음성 설정' },
  { id: 'logo', label: '브랜딩', status: 'pending', detail: '로고/배너/워터마크 생성' },
]

export function AgentStatus({ currentStep, isLoading }: Props) {
  const [steps, setSteps] = useState<StatusStep[]>(WORKFLOW_STEPS)
  const [elapsedTime, setElapsedTime] = useState(0)
  const [currentAction, setCurrentAction] = useState('')

  useEffect(() => {
    setSteps(prev => prev.map(step => {
      const stepIdx = WORKFLOW_STEPS.findIndex(s => s.id === step.id)
      const currentIdx = WORKFLOW_STEPS.findIndex(s => s.id === currentStep)

      if (stepIdx < currentIdx) {
        return { ...step, status: 'completed' as const }
      } else if (step.id === currentStep && isLoading) {
        return { ...step, status: 'running' as const }
      } else if (step.id === currentStep && !isLoading) {
        return { ...step, status: 'completed' as const }
      }
      return { ...step, status: 'pending' as const }
    }))
  }, [currentStep, isLoading])

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>
    if (isLoading) {
      setElapsedTime(0)
      interval = setInterval(() => {
        setElapsedTime(prev => prev + 100)
      }, 100)
    }
    return () => clearInterval(interval)
  }, [isLoading])

  useEffect(() => {
    if (!isLoading) {
      setCurrentAction('')
      return
    }

    const actions = {
      channel_name: [
        '요청 분석 중...',
        '채널 컨셉 파악 중...',
        'LLM에 프롬프트 전송 중...',
        '채널명 후보 생성 중...',
        '결과 정리 중...'
      ],
      benchmarking: [
        '채널 분석 준비 중...',
        '유사 채널 검색 중...',
        '벤치마킹 데이터 수집 중...',
        '분석 리포트 생성 중...',
        '결과 정리 중...'
      ],
      character: [
        '캐릭터 설정 분석 중...',
        '이미지 프롬프트 생성 중...',
        'ComfyUI 워크플로우 준비 중...',
        '이미지 생성 중... (약 30초 소요)',
        '이미지 후처리 중...'
      ],
      tts_settings: [
        '음성 옵션 준비 중...',
        '샘플 음성 로딩 중...',
        'TTS 설정 중...',
        '미리듣기 생성 중...',
        '결과 정리 중...'
      ],
      logo: [
        '브랜딩 옵션 준비 중...',
        '로고 생성 중...',
        '배너 생성 중...',
        '워터마크 생성 중...',
        '결과 정리 중...'
      ]
    }

    const stepActions = actions[currentStep as keyof typeof actions] || ['처리 중...']
    let idx = 0

    const interval = setInterval(() => {
      idx = Math.min(idx + 1, stepActions.length - 1)
      setCurrentAction(stepActions[idx])
    }, 2000)

    setCurrentAction(stepActions[0])

    return () => clearInterval(interval)
  }, [isLoading, currentStep])

  if (currentStep === 'idle') return null

  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000)
    const tenths = Math.floor((ms % 1000) / 100)
    return `${seconds}.${tenths}s`
  }

  return (
    <div className="bg-zinc-800/50 border border-zinc-700 rounded-xl p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-zinc-300">워크플로우 진행 상태</span>
          {isLoading && (
            <span className="px-2 py-0.5 text-xs bg-emerald-500/20 text-emerald-400 rounded-full">
              진행 중
            </span>
          )}
        </div>
        {isLoading && (
          <span className="text-xs text-zinc-500 font-mono">{formatTime(elapsedTime)}</span>
        )}
      </div>

      <div className="space-y-2">
        {steps.map((step, idx) => (
          <div key={step.id} className="flex items-center gap-3">
            <div className="w-5 h-5 flex items-center justify-center">
              {step.status === 'completed' && (
                <Check className="w-5 h-5 text-emerald-500" />
              )}
              {step.status === 'running' && (
                <Loader2 className="w-4 h-4 text-emerald-500 animate-spin" />
              )}
              {step.status === 'pending' && (
                <Circle className="w-4 h-4 text-zinc-600" />
              )}
              {step.status === 'error' && (
                <X className="w-5 h-5 text-red-500" />
              )}
            </div>

            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className={`text-sm ${
                  step.status === 'completed' ? 'text-zinc-400' :
                  step.status === 'running' ? 'text-white font-medium' :
                  'text-zinc-500'
                }`}>
                  {idx + 1}. {step.label}
                </span>
                {step.status === 'running' && (
                  <span className="text-xs text-emerald-400 animate-pulse">
                    {currentAction}
                  </span>
                )}
              </div>
              {step.status === 'running' && (
                <div className="mt-1 h-1 bg-zinc-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full transition-all duration-300"
                    style={{
                      width: `${Math.min((elapsedTime / 10000) * 100, 95)}%`,
                      animation: 'pulse 2s infinite'
                    }}
                  />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {currentStep === 'completed' && (
        <div className="mt-3 pt-3 border-t border-zinc-700 flex items-center gap-2 text-emerald-400">
          <CheckCircle className="w-5 h-5" />
          <span className="text-sm font-medium">모든 기획 단계 완료!</span>
        </div>
      )}
    </div>
  )
}
