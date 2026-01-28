import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Plus,
  Settings,
  Play,
  Clock,
  CheckCircle,
  FileText,
  Film,
  Upload,
  MoreVertical,
  Trash2,
  Lightbulb,
  MessageSquare
} from 'lucide-react'
import { useChannelStore } from '../stores/channelStore'
import { useProjectStore, type Project, type ProjectStatus } from '../stores/projectStore'

const STATUS_CONFIG: Record<ProjectStatus, { label: string; color: string; icon: any }> = {
  idea: { label: '아이디어', color: 'blue', icon: Lightbulb },
  script: { label: '스크립트', color: 'purple', icon: FileText },
  media: { label: '미디어 생성', color: 'cyan', icon: Play },
  editor: { label: '편집', color: 'orange', icon: Film },
  review: { label: '검토', color: 'yellow', icon: Clock },
  publish: { label: '발행', color: 'green', icon: Upload },
  completed: { label: '완료', color: 'emerald', icon: CheckCircle }
}

export function ChannelDetailPage() {
  const { channelId } = useParams()
  const navigate = useNavigate()
  const { getChannel } = useChannelStore()
  const { getProjectsByChannel, createProject, deleteProject } = useProjectStore()
  const [menuOpen, setMenuOpen] = useState<string | null>(null)

  const channel = channelId ? getChannel(channelId) : undefined
  const projects = channelId ? getProjectsByChannel(channelId) : []

  if (!channel) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">채널을 찾을 수 없습니다</h2>
          <Link to="/channels" className="text-emerald-400 hover:underline">
            채널 목록으로
          </Link>
        </div>
      </div>
    )
  }

  const handleNewProject = () => {
    const projectId = createProject(channel.id)
    navigate(`/projects/${projectId}`)
  }

  const handleDeleteProject = (id: string) => {
    if (confirm('프로젝트를 삭제하시겠습니까?')) {
      deleteProject(id)
    }
    setMenuOpen(null)
  }

  // Group projects by status
  const projectsByStatus = projects.reduce((acc, project) => {
    if (!acc[project.status]) acc[project.status] = []
    acc[project.status].push(project)
    return acc
  }, {} as Record<ProjectStatus, Project[]>)

  return (
    <div className="h-full overflow-auto">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-zinc-900/95 backdrop-blur border-b border-zinc-800">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center gap-4 mb-4">
            <Link
              to="/channels"
              className="p-2 hover:bg-zinc-800 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex-1">
              <h1 className="text-xl font-bold">{channel.name}</h1>
              <p className="text-sm text-zinc-400">{channel.category}</p>
            </div>
            <Link
              to={`/channels/${channel.id}/setup`}
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
            >
              <Settings className="w-4 h-4" />
              채널 설정
            </Link>
            <button
              onClick={handleNewProject}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition-colors"
            >
              <Plus className="w-5 h-5" />
              새 프로젝트
            </button>
          </div>

          {!channel.setupCompleted && (
            <div className="flex items-center gap-3 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
              <Settings className="w-5 h-5 text-yellow-400" />
              <span className="text-sm text-yellow-200">
                채널 설정을 완료하면 더 정확한 콘텐츠를 생성할 수 있습니다
              </span>
              <Link
                to={`/channels/${channel.id}/setup`}
                className="ml-auto text-sm text-yellow-400 hover:underline"
              >
                설정하기 →
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-6 py-6">
        {projects.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-20 h-20 bg-zinc-800 rounded-full flex items-center justify-center mx-auto mb-4">
              <Film className="w-10 h-10 text-zinc-600" />
            </div>
            <h2 className="text-xl font-semibold mb-2">프로젝트가 없습니다</h2>
            <p className="text-zinc-400 mb-6">새 영상 프로젝트를 시작해보세요</p>
            <button
              onClick={handleNewProject}
              className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition-colors"
            >
              <MessageSquare className="w-5 h-5" />
              아이디어 구상하기
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Kanban-style view */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {(Object.keys(STATUS_CONFIG) as ProjectStatus[]).map(status => {
                const statusProjects = projectsByStatus[status] || []
                const config = STATUS_CONFIG[status]
                const Icon = config.icon

                return (
                  <div key={status} className="bg-zinc-800/30 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-4">
                      <Icon className={`w-4 h-4 text-${config.color}-400`} />
                      <span className="font-medium text-sm">{config.label}</span>
                      <span className="ml-auto text-xs text-zinc-500 bg-zinc-700 px-2 py-0.5 rounded-full">
                        {statusProjects.length}
                      </span>
                    </div>

                    <div className="space-y-2">
                      {statusProjects.map(project => (
                        <ProjectCard
                          key={project.id}
                          project={project}
                          menuOpen={menuOpen === project.id}
                          onMenuToggle={() => setMenuOpen(menuOpen === project.id ? null : project.id)}
                          onDelete={() => handleDeleteProject(project.id)}
                        />
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

interface ProjectCardProps {
  project: Project
  menuOpen: boolean
  onMenuToggle: () => void
  onDelete: () => void
}

function ProjectCard({ project, menuOpen, onMenuToggle, onDelete }: ProjectCardProps) {

  return (
    <div className="bg-zinc-800/50 border border-zinc-700/50 rounded-lg p-3 hover:border-zinc-600 transition-colors group relative">
      <Link to={`/projects/${project.id}`}>
        <h4 className="font-medium text-sm mb-1 group-hover:text-emerald-400 transition-colors pr-6">
          {project.title}
        </h4>
        {project.idea?.hook && (
          <p className="text-xs text-zinc-500 line-clamp-2">{project.idea.hook}</p>
        )}
      </Link>

      <button
        onClick={(e) => { e.preventDefault(); onMenuToggle() }}
        className="absolute top-2 right-2 p-1 hover:bg-zinc-700 rounded opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <MoreVertical className="w-3.5 h-3.5" />
      </button>

      {menuOpen && (
        <div className="absolute right-2 top-8 w-28 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl py-1 z-10">
          <button
            onClick={onDelete}
            className="flex items-center gap-2 px-3 py-1.5 hover:bg-zinc-700 text-xs text-red-400 w-full"
          >
            <Trash2 className="w-3.5 h-3.5" />
            삭제
          </button>
        </div>
      )}
    </div>
  )
}
