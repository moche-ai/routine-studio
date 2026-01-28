import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import {
  Home,
  FolderKanban,
  ChevronLeft,
  ChevronRight,
  LogOut,
  User,
  Plus,
  MessageSquare,
  Youtube,
  Trash2
} from 'lucide-react'
import { useState } from 'react'
import { useAuthStore } from '../stores/authStore'
import { useChannelStore } from '../stores/channelStore'
import { useChatStore } from '../stores/chatStore'

const navItems = [
  { path: '/', icon: Home, label: '홈' },
]

export function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const { channels, deleteChannel } = useChannelStore()
  const { conversations, currentConversationId, createConversation, selectConversation, deleteConversation } = useChatStore()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const handleNewChat = () => {
    const id = createConversation()
    selectConversation(id)
    navigate('/channels/new')
  }

  const handleSelectSession = (convId: string) => {
    selectConversation(convId)
    navigate('/channels/new')
  }

  const handleDeleteSession = async (e: React.MouseEvent, convId: string) => {
    e.stopPropagation()
    await deleteConversation(convId)
  }

  const handleDeleteChannel = (e: React.MouseEvent, channelId: string) => {
    e.stopPropagation()
    deleteChannel(channelId)
  }

  const formatDate = (date: Date | string) => {
    const d = date instanceof Date ? date : new Date(date)
    const now = new Date()
    const diff = now.getTime() - d.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))

    if (days === 0) {
      return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
    } else if (days === 1) {
      return '어제'
    } else if (days < 7) {
      return `${days}일 전`
    } else {
      return d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
    }
  }

  // 채널 페이지인지 확인
  const isChannelPage = location.pathname.startsWith('/channels')

  return (
    <div className="flex h-screen bg-zinc-900 text-white">
      {/* Sidebar */}
      <aside className={`${collapsed ? 'w-16' : 'w-64'} border-r border-zinc-800 flex flex-col transition-all duration-200 flex-shrink-0`}>
        {/* Logo */}
        <div className="p-4 border-b border-zinc-800 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden">
            <img src="/logo.png" alt="Logo" className="w-8 h-8" />
          </div>
          {!collapsed && (
            <span className="font-semibold text-lg">Routine Studio</span>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-2">
          {/* Basic Nav Items */}
          {navItems.map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) => `
                flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 transition-colors
                ${isActive
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : 'text-zinc-400 hover:bg-zinc-800 hover:text-white'
                }
              `}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          ))}

          {/* Channels Link */}
          <NavLink
            to="/channels"
            className={({ isActive }) => `
              flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 transition-colors
              ${isActive || isChannelPage
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'text-zinc-400 hover:bg-zinc-800 hover:text-white'
              }
            `}
          >
            <FolderKanban className="w-5 h-5 flex-shrink-0" />
            {!collapsed && <span>채널</span>}
          </NavLink>

          {/* Channel & Session Sections (visible when on channel pages or not collapsed) */}
          {!collapsed && isChannelPage && (
            <>
              {/* Section 1: Created Channels */}
              <div className="mt-4 mb-2">
                <div className="flex items-center justify-between px-3 mb-2">
                  <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">내 채널</span>
                </div>
                <div className="space-y-1">
                  {channels.length === 0 ? (
                    <div className="px-3 py-2 text-xs text-zinc-600">
                      아직 채널이 없습니다
                    </div>
                  ) : (
                    channels.map((channel) => (
                      <NavLink
                        key={channel.id}
                        to={`/channels/${channel.id}`}
                        className={({ isActive }) => `
                          group flex items-center gap-2 px-3 py-2 rounded-lg transition-colors
                          ${isActive
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : 'text-zinc-300 hover:bg-zinc-800'
                          }
                        `}
                      >
                        <div className="w-6 h-6 bg-zinc-700 rounded-full flex items-center justify-center flex-shrink-0">
                          {channel.thumbnailUrl ? (
                            <img src={channel.thumbnailUrl} alt="" className="w-full h-full rounded-full object-cover" />
                          ) : (
                            <Youtube className="w-3.5 h-3.5 text-zinc-400" />
                          )}
                        </div>
                        <span className="text-sm truncate flex-1">{channel.name}</span>
                        <button
                          onClick={(e) => handleDeleteChannel(e, channel.id)}
                          className="p-1 opacity-0 group-hover:opacity-100 hover:bg-zinc-700 rounded transition-all"
                        >
                          <Trash2 className="w-3 h-3 text-zinc-500 hover:text-red-400" />
                        </button>
                      </NavLink>
                    ))
                  )}
                </div>
              </div>

              {/* Section 2: Chat Sessions (blurry/faded look) */}
              <div className="mt-4 mb-2">
                <div className="flex items-center justify-between px-3 mb-2">
                  <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">채널 기획</span>
                  <button
                    onClick={handleNewChat}
                    className="p-1 hover:bg-zinc-700 rounded transition-colors"
                    title="새 대화"
                  >
                    <Plus className="w-3.5 h-3.5 text-zinc-500 hover:text-emerald-400" />
                  </button>
                </div>
                <div className="space-y-1">
                  {conversations.length === 0 ? (
                    <button
                      onClick={handleNewChat}
                      className="w-full flex items-center gap-2 px-3 py-2 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50 rounded-lg transition-colors"
                    >
                      <Plus className="w-4 h-4" />
                      <span className="text-sm">새 채널 기획 시작</span>
                    </button>
                  ) : (
                    conversations.map((conv) => (
                      <button
                        key={conv.id}
                        onClick={() => handleSelectSession(conv.id)}
                        className={`
                          group w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-all text-left
                          ${currentConversationId === conv.id
                            ? 'bg-zinc-800 text-zinc-200'
                            : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50 opacity-60 hover:opacity-100'
                          }
                        `}
                      >
                        <MessageSquare className={`w-4 h-4 flex-shrink-0 ${
                          currentConversationId === conv.id ? 'text-emerald-400' : 'text-zinc-600'
                        }`} />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm truncate">{conv.title}</div>
                          <div className="text-xs text-zinc-600 truncate">
                            {formatDate(conv.updatedAt)}
                            {conv.messages.length > 0 && ` · ${conv.messages.length}개`}
                          </div>
                        </div>
                        <button
                          onClick={(e) => handleDeleteSession(e, conv.id)}
                          className="p-1 opacity-0 group-hover:opacity-100 hover:bg-zinc-700 rounded transition-all"
                        >
                          <Trash2 className="w-3 h-3 text-zinc-500 hover:text-red-400" />
                        </button>
                      </button>
                    ))
                  )}
                </div>
              </div>
            </>
          )}
        </nav>

        {/* User Menu */}
        <div className="relative border-t border-zinc-800">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="w-full p-3 flex items-center gap-3 hover:bg-zinc-800 transition-colors"
          >
            <div className="w-8 h-8 bg-zinc-700 rounded-full flex items-center justify-center flex-shrink-0">
              <User className="w-4 h-4 text-zinc-300" />
            </div>
            {!collapsed && (
              <div className="flex-1 text-left overflow-hidden">
                <div className="text-sm font-medium truncate">{user?.name || user?.username || 'User'}</div>
                <div className="text-xs text-zinc-500 truncate">@{user?.username}</div>
              </div>
            )}
          </button>

          {/* Dropdown */}
          {showUserMenu && (
            <div className="absolute bottom-full left-0 w-full p-2 bg-zinc-800 border border-zinc-700 rounded-lg shadow-lg mb-1">
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-zinc-700 rounded-lg transition-colors"
              >
                <LogOut className="w-4 h-4" />
                {!collapsed && '로그아웃'}
              </button>
            </div>
          )}
        </div>

        {/* Collapse Button */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-4 border-t border-zinc-800 text-zinc-500 hover:text-white transition-colors flex items-center justify-center"
        >
          {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
        </button>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}
