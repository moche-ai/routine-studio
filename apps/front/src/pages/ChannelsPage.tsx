import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Plus, Settings, FolderKanban, MoreVertical, Trash2, MessageSquare } from 'lucide-react'
import { useChannelStore, type Channel } from '../stores/channelStore'
import { useProjectStore } from '../stores/projectStore'

export function ChannelsPage() {
  const navigate = useNavigate()
  const { channels, deleteChannel } = useChannelStore()
  const { getProjectsByChannel } = useProjectStore()
  const [menuOpen, setMenuOpen] = useState<string | null>(null)

  const handleNewChannel = () => {
    navigate('/channels/new')
  }

  const handleDelete = (id: string) => {
    if (confirm('채널을 삭제하시겠습니까? 관련 프로젝트도 모두 삭제됩니다.')) {
      deleteChannel(id)
    }
    setMenuOpen(null)
  }

  return (
    <div className="h-full overflow-auto p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold">채널 관리</h1>
            <p className="text-zinc-400 mt-1">유튜브 채널을 기획하고 관리하세요</p>
          </div>
          <button
            onClick={handleNewChannel}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition-colors"
          >
            <Plus className="w-5 h-5" />
            새 채널 기획
          </button>
        </div>

        {/* Channel Grid */}
        {channels.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-20 h-20 bg-zinc-800 rounded-full flex items-center justify-center mx-auto mb-4">
              <FolderKanban className="w-10 h-10 text-zinc-600" />
            </div>
            <h2 className="text-xl font-semibold mb-2">아직 채널이 없습니다</h2>
            <p className="text-zinc-400 mb-6">AI와 대화하며 첫 번째 채널을 기획해보세요</p>
            <button
              onClick={handleNewChannel}
              className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-medium transition-colors"
            >
              <MessageSquare className="w-5 h-5" />
              채널 기획 시작
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {channels.map(channel => {
              const projects = getProjectsByChannel(channel.id)
              return (
                <ChannelCard
                  key={channel.id}
                  channel={channel}
                  projectCount={projects.length}
                  menuOpen={menuOpen === channel.id}
                  onMenuToggle={() => setMenuOpen(menuOpen === channel.id ? null : channel.id)}
                  onDelete={() => handleDelete(channel.id)}
                />
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

interface ChannelCardProps {
  channel: Channel
  projectCount: number
  menuOpen: boolean
  onMenuToggle: () => void
  onDelete: () => void
}

function ChannelCard({ channel, projectCount, menuOpen, onMenuToggle, onDelete }: ChannelCardProps) {
  return (
    <div className="bg-zinc-800/50 border border-zinc-700/50 rounded-xl overflow-hidden hover:border-zinc-600 transition-colors group">
      {/* Thumbnail */}
      <div className="aspect-video bg-gradient-to-br from-zinc-700 to-zinc-800 relative">
        {channel.thumbnailUrl ? (
          <img src={channel.thumbnailUrl} alt={channel.name} className="w-full h-full object-cover" />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-4xl font-bold text-zinc-600">
              {channel.name.charAt(0).toUpperCase()}
            </span>
          </div>
        )}

        {/* Setup Badge */}
        {!channel.setupCompleted && (
          <div className="absolute top-2 left-2 px-2 py-1 bg-yellow-500/20 text-yellow-400 text-xs rounded-full">
            설정 필요
          </div>
        )}

        {/* Menu */}
        <div className="absolute top-2 right-2">
          <button
            onClick={(e) => { e.preventDefault(); onMenuToggle() }}
            className="p-1.5 bg-black/50 hover:bg-black/70 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <MoreVertical className="w-4 h-4" />
          </button>

          {menuOpen && (
            <div className="absolute right-0 mt-1 w-36 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl py-1 z-10">
              <Link
                to={`/channels/${channel.id}/setup`}
                className="flex items-center gap-2 px-3 py-2 hover:bg-zinc-700 text-sm"
              >
                <Settings className="w-4 h-4" />
                채널 설정
              </Link>
              <button
                onClick={onDelete}
                className="flex items-center gap-2 px-3 py-2 hover:bg-zinc-700 text-sm text-red-400 w-full"
              >
                <Trash2 className="w-4 h-4" />
                삭제
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <Link to={`/channels/${channel.id}`} className="block p-4">
        <h3 className="font-semibold text-lg mb-1 group-hover:text-emerald-400 transition-colors">
          {channel.name}
        </h3>
        <p className="text-sm text-zinc-400 line-clamp-2 mb-3">
          {channel.description || '설명 없음'}
        </p>
        <div className="flex items-center gap-4 text-xs text-zinc-500">
          <span className="flex items-center gap-1">
            <FolderKanban className="w-3.5 h-3.5" />
            프로젝트 {projectCount}개
          </span>
          <span>{channel.category || '카테고리 없음'}</span>
        </div>
      </Link>
    </div>
  )
}
