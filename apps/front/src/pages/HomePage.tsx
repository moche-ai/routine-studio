import { Link } from 'react-router-dom'
import { FolderKanban, Plus } from 'lucide-react'
import { useChannelStore } from '../stores/channelStore'
import { useProjectStore } from '../stores/projectStore'

export function HomePage() {
  const { channels } = useChannelStore()
  const { projects } = useProjectStore()

  const recentChannels = channels.slice(0, 6)
  const completedProjects = projects.filter(p => p.status === 'completed').length

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Routine Studio</h1>
        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="p-4 bg-zinc-800/50 rounded-xl text-center">
            <div className="text-3xl font-bold text-white">{channels.length}</div>
            <div className="text-sm text-zinc-500">채널</div>
          </div>
          <div className="p-4 bg-zinc-800/50 rounded-xl text-center">
            <div className="text-3xl font-bold text-white">{projects.length}</div>
            <div className="text-sm text-zinc-500">프로젝트</div>
          </div>
          <div className="p-4 bg-zinc-800/50 rounded-xl text-center">
            <div className="text-3xl font-bold text-white">{completedProjects}</div>
            <div className="text-sm text-zinc-500">완료된 영상</div>
          </div>
          <div className="p-4 bg-zinc-800/50 rounded-xl text-center">
            <div className="h-9 flex items-center justify-center"><span className="w-3 h-3 bg-emerald-400 rounded-full animate-pulse"></span></div>
            <div className="text-sm text-zinc-500">API 상태</div>
          </div>
        </div>

        {/* Channels */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">채널</h2>
          <Link
            to="/channels/new"
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            새 채널
          </Link>
        </div>

        {channels.length === 0 ? (
          <div className="text-center py-16 bg-zinc-800/30 rounded-xl">
            <FolderKanban className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">첫 채널을 만들어보세요</h3>
            <p className="text-zinc-500 mb-4">AI와 대화하며 유튜브 채널을 기획할 수 있습니다</p>
            <Link
              to="/channels/new"
              className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium transition-colors"
            >
              <Plus className="w-4 h-4" />
              채널 기획 시작
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recentChannels.map(channel => (
              <Link
                key={channel.id}
                to={`/channels/${channel.id}`}
                className="p-4 bg-zinc-800/50 hover:bg-zinc-700/50 rounded-xl transition-colors group"
              >
                <div className="w-10 h-10 bg-zinc-700 rounded-lg flex items-center justify-center mb-3">
                  <span className="text-lg font-bold text-zinc-300">{channel.name.charAt(0)}</span>
                </div>
                <h3 className="font-semibold group-hover:text-emerald-400 transition-colors">
                  {channel.name}
                </h3>
                <p className="text-sm text-zinc-500 mt-1">{channel.category || '카테고리 없음'}</p>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
