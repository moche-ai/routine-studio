import { useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  Check,
  ChevronRight,
  Palette,
  Mic,
  Image,
  FileImage,
  Crown,
  User,
  FileText,
  Type
} from 'lucide-react'

const SETUP_STEPS = [
  { id: 'style', label: '스타일', icon: Palette, required: true, description: '스크립트 말투와 형식 설정' },
  { id: 'tts', label: 'TTS', icon: Mic, required: true, description: '음성 설정 (목소리, 속도, 톤)' },
  { id: 'image', label: '영상 이미지', icon: Image, required: true, description: '영상에 사용할 이미지 스타일' },
  { id: 'thumbnail', label: '썸네일', icon: FileImage, required: true, description: '썸네일 디자인 스타일' },
  { id: 'branding', label: '채널 로고', icon: Crown, required: true, description: '로고 및 브랜딩 설정' },
  { id: 'character', label: '캐릭터', icon: User, required: false, description: '캐릭터 설정 (선택사항)' },
  { id: 'script', label: '스크립트', icon: FileText, required: true, description: '영상 구조 템플릿' },
  { id: 'subtitle', label: '자막', icon: Type, required: true, description: '자막 스타일 설정' },
]

interface StepConfig {
  style?: {
    tone: string
    format: string
    examples: string[]
  }
  tts?: {
    voice: string
    speed: number
    pitch: number
  }
  image?: {
    style: string
    checkpoint: string
    lora?: string
  }
  thumbnail?: {
    template: string
    colors: string[]
    font: string
  }
  branding?: {
    logo: string
    colors: string[]
    watermark: boolean
  }
  character?: {
    name: string
    image: string
    description: string
  }
  script?: {
    structure: string[]
    hooks: string[]
    cta: string
  }
  subtitle?: {
    font: string
    size: number
    color: string
    position: string
  }
}

export function ChannelSetupPage() {
  const { channelId: _channelId } = useParams()
  const [currentStep, setCurrentStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set())
  const [config, setConfig] = useState<StepConfig>({})

  const step = SETUP_STEPS[currentStep]

  const handleNext = () => {
    setCompletedSteps(prev => new Set([...prev, step.id]))
    if (currentStep < SETUP_STEPS.length - 1) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSave = async () => {
    // TODO: Save to API
    console.log('Saving config:', config)
  }

  return (
    <div className="h-full flex">
      {/* Steps Sidebar */}
      <div className="w-64 border-r border-zinc-800 p-4">
        <h2 className="font-semibold mb-4 px-2">채널 설정</h2>
        <div className="space-y-1">
          {SETUP_STEPS.map((s, idx) => (
            <button
              key={s.id}
              onClick={() => setCurrentStep(idx)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors text-left
                ${idx === currentStep
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : completedSteps.has(s.id)
                    ? 'text-zinc-300 hover:bg-zinc-800'
                    : 'text-zinc-500 hover:bg-zinc-800'
                }
              `}
            >
              <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0
                ${completedSteps.has(s.id)
                  ? 'bg-emerald-500 text-white'
                  : 'bg-zinc-700 text-zinc-400'
                }
              `}>
                {completedSteps.has(s.id) ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <span className="text-xs">{idx + 1}</span>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1">
                  <span className="truncate">{s.label}</span>
                  {!s.required && (
                    <span className="text-xs text-zinc-600">(선택)</span>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>

        {/* Progress */}
        <div className="mt-6 px-2">
          <div className="text-sm text-zinc-500 mb-2">
            진행률: {completedSteps.size}/{SETUP_STEPS.filter(s => s.required).length}
          </div>
          <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-emerald-500 transition-all"
              style={{
                width: `${(completedSteps.size / SETUP_STEPS.filter(s => s.required).length) * 100}%`
              }}
            />
          </div>
        </div>
      </div>

      {/* Step Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center">
              <step.icon className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-xl font-semibold">{step.label}</h1>
              <p className="text-sm text-zinc-400">{step.description}</p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <StepContent
            stepId={step.id}
            config={config}
            onChange={setConfig}
          />
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-zinc-800 flex items-center justify-between">
          <button
            onClick={handlePrev}
            disabled={currentStep === 0}
            className="px-4 py-2 text-zinc-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            이전
          </button>
          <div className="flex items-center gap-2">
            {currentStep === SETUP_STEPS.length - 1 ? (
              <button
                onClick={handleSave}
                className="px-6 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition-colors"
              >
                저장하기
              </button>
            ) : (
              <button
                onClick={handleNext}
                className="px-6 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition-colors flex items-center gap-2"
              >
                다음
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// Step Content Components
function StepContent({
  stepId,
  config,
  onChange
}: {
  stepId: string
  config: StepConfig
  onChange: (config: StepConfig) => void
}) {
  switch (stepId) {
    case 'style':
      return <StyleStep config={config} onChange={onChange} />
    case 'tts':
      return <TTSStep config={config} onChange={onChange} />
    case 'image':
      return <ImageStep config={config} onChange={onChange} />
    case 'character':
      return <CharacterStep config={config} onChange={onChange} />
    default:
      return (
        <div className="text-zinc-500 text-center py-12">
          {stepId} 설정 UI (구현 예정)
        </div>
      )
  }
}

function StyleStep({ config, onChange }: { config: StepConfig; onChange: (c: StepConfig) => void }) {
  const tones = ['친근한', '전문적인', '유머러스', '차분한', '열정적인']
  const formats = ['강의형', '스토리텔링', '리스트형', '대화형', 'Q&A']

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <label className="block text-sm font-medium mb-3">말투 스타일</label>
        <div className="flex flex-wrap gap-2">
          {tones.map(tone => (
            <button
              key={tone}
              onClick={() => onChange({ ...config, style: { ...config.style, tone } as any })}
              className={`px-4 py-2 rounded-lg border transition-colors
                ${config.style?.tone === tone
                  ? 'border-emerald-500 bg-emerald-500/20 text-emerald-400'
                  : 'border-zinc-700 hover:border-zinc-600'
                }
              `}
            >
              {tone}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-3">영상 형식</label>
        <div className="flex flex-wrap gap-2">
          {formats.map(format => (
            <button
              key={format}
              onClick={() => onChange({ ...config, style: { ...config.style, format } as any })}
              className={`px-4 py-2 rounded-lg border transition-colors
                ${config.style?.format === format
                  ? 'border-emerald-500 bg-emerald-500/20 text-emerald-400'
                  : 'border-zinc-700 hover:border-zinc-600'
                }
              `}
            >
              {format}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-3">예시 문장</label>
        <textarea
          className="w-full h-32 bg-zinc-800 border border-zinc-700 rounded-lg p-3 text-sm focus:border-emerald-500 focus:outline-none"
          placeholder="원하는 스타일의 예시 문장을 입력하세요..."
        />
      </div>
    </div>
  )
}

function TTSStep({ config, onChange }: { config: StepConfig; onChange: (c: StepConfig) => void }) {
  const voices = ['여성 1', '여성 2', '남성 1', '남성 2', '아이']

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <label className="block text-sm font-medium mb-3">목소리 선택</label>
        <div className="grid grid-cols-5 gap-2">
          {voices.map(voice => (
            <button
              key={voice}
              onClick={() => onChange({ ...config, tts: { ...config.tts, voice } as any })}
              className={`p-4 rounded-lg border text-center transition-colors
                ${config.tts?.voice === voice
                  ? 'border-emerald-500 bg-emerald-500/20 text-emerald-400'
                  : 'border-zinc-700 hover:border-zinc-600'
                }
              `}
            >
              <Mic className="w-6 h-6 mx-auto mb-2" />
              <span className="text-sm">{voice}</span>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-3">속도: {config.tts?.speed || 1}x</label>
        <input
          type="range"
          min="0.5"
          max="2"
          step="0.1"
          value={config.tts?.speed || 1}
          onChange={e => onChange({ ...config, tts: { ...config.tts, speed: parseFloat(e.target.value) } as any })}
          className="w-full"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-3">피치: {config.tts?.pitch || 0}</label>
        <input
          type="range"
          min="-10"
          max="10"
          step="1"
          value={config.tts?.pitch || 0}
          onChange={e => onChange({ ...config, tts: { ...config.tts, pitch: parseInt(e.target.value) } as any })}
          className="w-full"
        />
      </div>

      <button className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-sm transition-colors">
        미리 듣기
      </button>
    </div>
  )
}

function ImageStep({ config, onChange }: { config: StepConfig; onChange: (c: StepConfig) => void }) {
  const styles = [
    { id: 'cartoon', label: '카툰', desc: 'Family Guy, Simpsons 스타일' },
    { id: 'anime', label: '애니메', desc: '일본 애니메이션 스타일' },
    { id: 'realistic', label: '실사', desc: '실제 사진 스타일' },
    { id: '3d', label: '3D', desc: 'Pixar, 3D 렌더링 스타일' },
    { id: 'illustration', label: '일러스트', desc: '디지털 아트 스타일' },
  ]

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <label className="block text-sm font-medium mb-3">이미지 스타일</label>
        <div className="grid grid-cols-2 gap-3">
          {styles.map(style => (
            <button
              key={style.id}
              onClick={() => onChange({ ...config, image: { ...config.image, style: style.id } as any })}
              className={`p-4 rounded-lg border text-left transition-colors
                ${config.image?.style === style.id
                  ? 'border-emerald-500 bg-emerald-500/20'
                  : 'border-zinc-700 hover:border-zinc-600'
                }
              `}
            >
              <div className="font-medium">{style.label}</div>
              <div className="text-sm text-zinc-400">{style.desc}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

function CharacterStep({ config, onChange }: { config: StepConfig; onChange: (c: StepConfig) => void }) {
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <label className="block text-sm font-medium mb-3">캐릭터 이름</label>
        <input
          type="text"
          value={config.character?.name || ''}
          onChange={e => onChange({ ...config, character: { ...config.character, name: e.target.value } as any })}
          className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 focus:border-emerald-500 focus:outline-none"
          placeholder="캐릭터 이름을 입력하세요"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-3">캐릭터 설명</label>
        <textarea
          value={config.character?.description || ''}
          onChange={e => onChange({ ...config, character: { ...config.character, description: e.target.value } as any })}
          className="w-full h-32 bg-zinc-800 border border-zinc-700 rounded-lg p-3 text-sm focus:border-emerald-500 focus:outline-none"
          placeholder="캐릭터의 외모, 성격 등을 설명하세요..."
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-3">캐릭터 이미지</label>
        <div className="border-2 border-dashed border-zinc-700 rounded-lg p-8 text-center hover:border-zinc-600 cursor-pointer transition-colors">
          <User className="w-12 h-12 mx-auto mb-3 text-zinc-600" />
          <p className="text-zinc-400">클릭하여 이미지 업로드</p>
          <p className="text-sm text-zinc-500 mt-1">또는 드래그 앤 드롭</p>
        </div>
      </div>
    </div>
  )
}
