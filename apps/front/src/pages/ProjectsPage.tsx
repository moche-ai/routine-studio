import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Play, Pause, Check, Clock, FolderOpen, MoreVertical, Trash2 } from 'lucide-react'

interface Project {
  id: string
  title: string
  channelId: string
  channelName: string
  status: 'planning' | 'script' | 'editor' | 'publish' | 'completed'
  thumbnail?: string
  createdAt: string
  updatedAt: string
}

const STATUS_CONFIG = {
  planning: { label: '기획', color: 'yellow', icon: Clock },
  script: { label: '스크립트', color: 'blue', icon: Play },
  editor: { label: '편집', color: 'purple', icon: Pause },
  publish: { label: '발행', color: 'emerald', icon: Check },
  completed: { label: '완료', color: 'zinc', icon: Check },
}

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // TODO: Fetch from API
    setProjects([
      {
        id: '1',
        title: '2024 투자 전략 총정리',
        channelId: 'ch1',
        channelName: '투자의 정석',
        status: 'editor',
        createdAt: '2024-01-25T10:00:00Z',
        updatedAt: '2024-01-27T15:30:00Z',
      },
      {
        id: '2',
        title: '아침 루틴으로 인생 바꾸기',
        channelId: 'ch2',
        channelName: '자기계발 마스터',
        status: 'script',
        createdAt: '2024-01-26T09:00:00Z',
        updatedAt: '2024-01-27T12:00:00Z',
      },
    ])
    setLoading(false)
  }, [])

  const handleDelete = (projectId: string) => {
    if (confirm('프로젝트를 삭제하시겠습니까?')) {
      setProjects(projects.filter(p => p.id !== projectId))
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-zinc-800 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">프로젝트</h1>
          <p className="text-zinc-400 text-sm mt-1">영상 제작 프로젝트 관리</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition-colors">
          <Plus className="w-5 h-5" />
          새 프로젝트
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full" />
          </div>
        ) : projects.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-zinc-500">
            <FolderOpen className="w-16 h-16 mb-4 text-zinc-600" />
            <p className="text-lg mb-2">프로젝트가 없습니다</p>
            <p className="text-sm">새 프로젝트를 만들어 시작하세요</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map(project => {
              const statusConfig = STATUS_CONFIG[project.status]
              const StatusIcon = statusConfig.icon

              return (
                <div
                  key={project.id}
                  className="bg-zinc-800/50 rounded-xl overflow-hidden hover:bg-zinc-800 transition-colors group"
                >
                  {/* Thumbnail */}
                  <div className="aspect-video bg-zinc-900 relative">
                    {project.thumbnail ? (
                      <img src={project.thumbnail} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Play className="w-12 h-12 text-zinc-700" />
                      </div>
                    )}
                    <div className={`absolute top-2 right-2 px-2 py-1 rounded text-xs font-medium bg-${statusConfig.color}-500/20 text-${statusConfig.color}-400 flex items-center gap-1`}>
                      <StatusIcon className="w-3 h-3" />
                      {statusConfig.label}
                    </div>
                  </div>

                  {/* Info */}
                  <div className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold truncate">{project.title}</h3>
                        <p className="text-sm text-zinc-400 mt-1">{project.channelName}</p>
                      </div>
                      <div className="relative">
                        <button className="p-1 text-zinc-500 hover:text-white rounded opacity-0 group-hover:opacity-100 transition-opacity">
                          <MoreVertical className="w-5 h-5" />
                        </button>
                      </div>
                    </div>

                    <div className="mt-4 flex items-center justify-between">
                      <span className="text-xs text-zinc-500">
                        {new Date(project.updatedAt).toLocaleDateString('ko-KR')}
                      </span>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleDelete(project.id)}
                          className="p-1.5 text-zinc-500 hover:text-red-400 rounded hover:bg-zinc-700 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                        <Link
                          to={`/projects/${project.id}`}
                          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded text-sm font-medium transition-colors"
                        >
                          열기
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
