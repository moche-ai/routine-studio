import { useState } from "react"
import { MessageSquare, Tv, Palette, Lightbulb, FileText, CheckCircle, Plus, ChevronLeft, ChevronRight, Trash2, Loader2 } from "lucide-react"

interface Conversation {
  id: string
  title: string
  step: string
  updatedAt: Date
}

interface Props {
  conversations: Conversation[]
  currentId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void | Promise<void>
  collapsed: boolean
  onToggle: () => void
}

const STEP_ICONS: Record<string, React.ReactNode> = {
  idle: <MessageSquare className="w-5 h-5" />,
  channel_name: <Tv className="w-5 h-5" />,
  character: <Palette className="w-5 h-5" />,
  video_ideas: <Lightbulb className="w-5 h-5" />,
  script: <FileText className="w-5 h-5" />,
  completed: <CheckCircle className="w-5 h-5 text-emerald-400" />
}

export function Sidebar({ conversations, currentId, onSelect, onNew, onDelete, collapsed, onToggle }: Props) {
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    if (deleteConfirm === id) {
      setDeleting(id)
      try {
        await onDelete(id)
      } finally {
        setDeleting(null)
        setDeleteConfirm(null)
      }
    } else {
      setDeleteConfirm(id)
      setTimeout(() => setDeleteConfirm(null), 3000)
    }
  }

  const isCollapsed = collapsed
  const isCurrentId = (id: string) => currentId === id
  const isDeleteConfirm = (id: string) => deleteConfirm === id
  const isDeleting = (id: string) => deleting === id

  return (
    <div className={`flex flex-col h-full bg-zinc-950 border-r border-zinc-800 transition-all duration-300 ${isCollapsed ? "w-16" : "w-64"}`}>
      <div className="flex items-center justify-between p-3 border-b border-zinc-800">
        {!isCollapsed && (
          <h2 className="font-semibold text-sm text-zinc-300">대화 목록</h2>
        )}
        <button
          onClick={onToggle}
          className="p-2 hover:bg-zinc-800 rounded-lg transition-colors text-zinc-400 hover:text-white"
          title={isCollapsed ? "펼치기" : "접기"}
        >
          {isCollapsed ? (
            <ChevronRight className="w-5 h-5" />
          ) : (
            <ChevronLeft className="w-5 h-5" />
          )}
        </button>
      </div>

      <div className="p-2">
        <button
          onClick={onNew}
          className={`w-full flex items-center gap-2 p-3 bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors ${isCollapsed ? "justify-center" : ""}`}
        >
          <Plus className="w-5 h-5" />
          {!isCollapsed && <span className="text-sm font-medium">새 대화</span>}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {conversations.length === 0 ? (
          !isCollapsed && (
            <p className="text-xs text-zinc-500 text-center py-4">
              대화 기록이 없습니다
            </p>
          )
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`group flex items-center rounded-lg transition-colors ${
                isCurrentId(conv.id)
                  ? "bg-emerald-600/20 border border-emerald-500/50 text-white"
                  : "hover:bg-zinc-800/50 text-zinc-400 hover:text-white"
              }`}
            >
              <button
                onClick={() => onSelect(conv.id)}
                className={`flex items-center gap-3 p-3 text-left min-w-0 ${isCollapsed ? "justify-center flex-1" : "flex-1"}`}
                title={conv.title}
              >
                <span className={`flex-shrink-0 ${isCurrentId(conv.id) ? "text-emerald-400" : ""}`}>
                  {STEP_ICONS[conv.step] || <MessageSquare className="w-5 h-5" />}
                </span>
                {!isCollapsed && (
                  <div className="min-w-0 flex-1 overflow-hidden">
                    <p className="text-sm font-medium truncate">{conv.title}</p>
                    <p className={`text-xs ${isCurrentId(conv.id) ? "text-emerald-400/70" : "text-zinc-500"}`}>
                      {new Date(conv.updatedAt).toLocaleDateString("ko-KR")}
                    </p>
                  </div>
                )}
              </button>
              {!isCollapsed && (
                <div className="flex-shrink-0 w-10 flex items-center justify-center">
                  <button
                    onClick={(e) => handleDelete(e, conv.id)}
                    disabled={isDeleting(conv.id)}
                    className={`p-1.5 rounded transition-all ${
                      isDeleting(conv.id)
                        ? "bg-zinc-600 text-zinc-400"
                        : isDeleteConfirm(conv.id)
                        ? "bg-red-600 text-white"
                        : "opacity-0 group-hover:opacity-100 hover:bg-zinc-700 text-zinc-400 hover:text-red-400"
                    }`}
                    title={isDeleteConfirm(conv.id) ? "다시 클릭하여 삭제" : "삭제"}
                  >
                    {isDeleting(conv.id) ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {!isCollapsed && (
        <div className="p-3 border-t border-zinc-800">
          <p className="text-xs text-zinc-600 text-center">
            Routine Studio v2
          </p>
        </div>
      )}
    </div>
  )
}
