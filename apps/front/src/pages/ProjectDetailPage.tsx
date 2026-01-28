import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  Lightbulb,
  FileText,
  Film,
  Upload,
  Check,
  ChevronRight,
  ArrowLeft,
  Play,
  RefreshCw
} from 'lucide-react'

const WORKFLOW_STEPS = [
  { id: 'planning', label: '기획', icon: Lightbulb, description: '주제 선정 및 키워드 분석' },
  { id: 'script', label: '스크립트', icon: FileText, description: '대본 작성 및 편집' },
  { id: 'editor', label: '편집', icon: Film, description: 'TTS/이미지 생성, 타임라인 편집' },
  { id: 'publish', label: '발행', icon: Upload, description: '렌더링 및 유튜브 업로드' },
]

interface ProjectData {
  id: string
  title: string
  topic: string
  keywords: string[]
  script?: {
    sections: { title: string; content: string }[]
  }
  media?: {
    images: string[]
    audio: string[]
  }
  status: string
}

export function ProjectDetailPage() {
  const { projectId } = useParams()
  const [currentStep, setCurrentStep] = useState(0)
  const [project, setProject] = useState<ProjectData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // TODO: Fetch from API
    setTimeout(() => {
      setProject({
        id: projectId!,
        title: '2024 투자 전략 총정리',
        topic: '2024년 하반기 투자 전략',
        keywords: ['투자', '주식', '2024', '전략'],
        script: {
          sections: [
            { title: '인트로', content: '안녕하세요, 오늘은 2024년 하반기 투자 전략에 대해 이야기해보겠습니다.' },
            { title: '본문 1', content: '첫 번째로 살펴볼 것은 글로벌 경제 동향입니다.' },
            { title: '본문 2', content: '두 번째는 국내 시장 분석입니다.' },
            { title: '아웃트로', content: '오늘 영상이 도움이 되셨다면 구독과 좋아요 부탁드립니다.' },
          ]
        },
        status: 'script'
      })
      setLoading(false)
      setCurrentStep(1) // script step
    }, 500)
  }, [projectId])

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  if (!project) {
    return (
      <div className="h-full flex items-center justify-center text-zinc-500">
        프로젝트를 찾을 수 없습니다
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-zinc-800">
        <div className="flex items-center gap-4 mb-4">
          <Link to="/projects" className="p-2 hover:bg-zinc-800 rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-xl font-semibold">{project.title}</h1>
            <p className="text-sm text-zinc-400">{project.topic}</p>
          </div>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center">
          {WORKFLOW_STEPS.map((step, idx) => {
            const isCompleted = idx < currentStep
            const isCurrent = idx === currentStep
            const StepIcon = step.icon

            return (
              <div key={step.id} className="flex items-center">
                <button
                  onClick={() => setCurrentStep(idx)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors
                    ${isCurrent
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : isCompleted
                        ? 'text-zinc-300 hover:bg-zinc-800'
                        : 'text-zinc-500 hover:bg-zinc-800'
                    }
                  `}
                >
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center
                    ${isCompleted
                      ? 'bg-emerald-500 text-white'
                      : isCurrent
                        ? 'bg-emerald-500/30 text-emerald-400'
                        : 'bg-zinc-700'
                    }
                  `}>
                    {isCompleted ? (
                      <Check className="w-4 h-4" />
                    ) : (
                      <StepIcon className="w-3 h-3" />
                    )}
                  </div>
                  <span className="hidden sm:inline">{step.label}</span>
                </button>
                {idx < WORKFLOW_STEPS.length - 1 && (
                  <ChevronRight className="w-5 h-5 text-zinc-600 mx-1" />
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {currentStep === 0 && <PlanningStep project={project} />}
        {currentStep === 1 && <ScriptStep project={project} />}
        {currentStep === 2 && <EditorStep project={project} />}
        {currentStep === 3 && <PublishStep project={project} />}
      </div>
    </div>
  )
}

function PlanningStep({ project }: { project: ProjectData }) {
  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <label className="block text-sm font-medium mb-2">영상 주제</label>
          <input
            type="text"
            defaultValue={project.topic}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-3 focus:border-emerald-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">키워드</label>
          <div className="flex flex-wrap gap-2">
            {project.keywords.map(keyword => (
              <span key={keyword} className="px-3 py-1 bg-zinc-800 rounded-full text-sm">
                {keyword}
              </span>
            ))}
            <button className="px-3 py-1 border border-dashed border-zinc-700 rounded-full text-sm text-zinc-500 hover:border-zinc-500">
              + 추가
            </button>
          </div>
        </div>

        <div className="pt-4">
          <button className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition-colors flex items-center justify-center gap-2">
            <RefreshCw className="w-5 h-5" />
            AI로 기획 생성
          </button>
        </div>
      </div>
    </div>
  )
}

function ScriptStep({ project }: { project: ProjectData }) {
  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto space-y-4">
        {project.script?.sections.map((section, idx) => (
          <div key={idx} className="bg-zinc-800/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium">{section.title}</span>
              <span className="text-xs text-zinc-500">섹션 {idx + 1}</span>
            </div>
            <textarea
              defaultValue={section.content}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-sm focus:border-emerald-500 focus:outline-none resize-none"
              rows={3}
            />
          </div>
        ))}

        <div className="flex items-center gap-2 pt-4">
          <button className="flex-1 py-3 bg-zinc-700 hover:bg-zinc-600 rounded-lg font-medium transition-colors">
            + 섹션 추가
          </button>
          <button className="flex-1 py-3 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition-colors flex items-center justify-center gap-2">
            <RefreshCw className="w-5 h-5" />
            AI로 스크립트 생성
          </button>
        </div>
      </div>
    </div>
  )
}

function EditorStep({ project: _project }: { project: ProjectData }) {
  const { projectId } = useParams()

  return (
    <div className="h-full flex flex-col items-center justify-center p-6">
      <Film className="w-16 h-16 text-zinc-600 mb-4" />
      <h2 className="text-xl font-semibold mb-2">비디오 에디터</h2>
      <p className="text-zinc-400 mb-6 text-center">
        TTS 생성, 이미지 생성, 타임라인 편집을 진행합니다
      </p>
      <div className="flex items-center gap-4">
        <button className="px-6 py-3 bg-zinc-700 hover:bg-zinc-600 rounded-lg font-medium transition-colors flex items-center gap-2">
          <RefreshCw className="w-5 h-5" />
          미디어 자동 생성
        </button>
        <Link
          to={`/projects/${projectId}/editor`}
          className="px-6 py-3 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition-colors flex items-center gap-2"
        >
          <Play className="w-5 h-5" />
          에디터 열기
        </Link>
      </div>
    </div>
  )
}

function PublishStep({ project: _project }: { project: ProjectData }) {
  return (
    <div className="h-full flex flex-col items-center justify-center p-6">
      <Upload className="w-16 h-16 text-zinc-600 mb-4" />
      <h2 className="text-xl font-semibold mb-2">영상 발행</h2>
      <p className="text-zinc-400 mb-6 text-center">
        영상을 렌더링하고 유튜브에 업로드합니다
      </p>
      <div className="flex items-center gap-4">
        <button className="px-6 py-3 bg-zinc-700 hover:bg-zinc-600 rounded-lg font-medium transition-colors">
          렌더링 시작
        </button>
        <button className="px-6 py-3 bg-red-600 hover:bg-red-500 rounded-lg font-medium transition-colors flex items-center gap-2">
          <Play className="w-5 h-5" />
          YouTube 업로드
        </button>
      </div>
    </div>
  )
}
