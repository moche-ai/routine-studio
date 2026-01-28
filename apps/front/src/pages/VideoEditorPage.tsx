import { useState, useRef, useCallback, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Player, type PlayerRef } from '@remotion/player'
import {
  ArrowLeft,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
  Maximize,
  ZoomIn,
  ZoomOut,
  Plus,
  Trash2,
  Image,
  Mic,
  Type,
  Music,
  Layers,
  Settings,
  Download,
  Save
} from 'lucide-react'
import { VideoComposition, type Track, type TimelineClip, type TrackType } from '../components/editor/VideoComposition'

const TRACK_CONFIG: Record<TrackType, { color: string; label: string; icon: any }> = {
  video: { color: 'purple', label: '영상', icon: Image },
  overlay: { color: 'cyan', label: '오버레이', icon: Layers },
  audio: { color: 'green', label: '오디오', icon: Mic },
  bgm: { color: 'yellow', label: 'BGM', icon: Music },
  sfx: { color: 'red', label: '효과음', icon: Volume2 },
  subtitle: { color: 'pink', label: '자막', icon: Type },
}

const FPS = 30
const DEFAULT_DURATION = 30 * FPS // 30 seconds

export function VideoEditorPage() {
  const { projectId } = useParams()
  const playerRef = useRef<PlayerRef>(null)

  const [isPlaying, setIsPlaying] = useState(false)
  const [currentFrame, setCurrentFrame] = useState(0)
  const [totalFrames, _setTotalFrames] = useState(DEFAULT_DURATION)
  const [zoom, setZoom] = useState(1)
  const [muted, setMuted] = useState(false)
  const [selectedClipId, setSelectedClipId] = useState<string | null>(null)

  const [tracks, setTracks] = useState<Track[]>([
    {
      id: 'video-1',
      type: 'video',
      name: '영상 트랙',
      muted: false,
      clips: [
        {
          id: 'clip-1',
          startFrame: 0,
          endFrame: 150,
          content: {
            type: 'image',
            src: '/placeholder-1.jpg',
            animation: 'ken-burns-in'
          }
        },
        {
          id: 'clip-2',
          startFrame: 150,
          endFrame: 300,
          content: {
            type: 'image',
            src: '/placeholder-2.jpg',
            animation: 'zoom-in'
          }
        }
      ]
    },
    {
      id: 'audio-1',
      type: 'audio',
      name: '음성',
      muted: false,
      clips: [
        {
          id: 'audio-clip-1',
          startFrame: 0,
          endFrame: 300,
          content: {
            type: 'audio',
            src: '/voice.mp3',
            volume: 1,
            fadeIn: 10,
            fadeOut: 10
          }
        }
      ]
    },
    {
      id: 'subtitle-1',
      type: 'subtitle',
      name: '자막',
      muted: false,
      clips: [
        {
          id: 'sub-1',
          startFrame: 0,
          endFrame: 90,
          content: {
            type: 'subtitle',
            text: '안녕하세요, 오늘은 2024년 투자 전략에 대해',
            style: { font: 'Pretendard', size: 48, color: '#ffffff', position: 'bottom' },
            animation: 'fade-in-up'
          }
        },
        {
          id: 'sub-2',
          startFrame: 90,
          endFrame: 180,
          content: {
            type: 'subtitle',
            text: '이야기해보겠습니다.',
            style: { font: 'Pretendard', size: 48, color: '#ffffff', position: 'bottom' },
            animation: 'fade-in-up'
          }
        }
      ]
    }
  ])

  // Player controls
  const togglePlay = useCallback(() => {
    if (playerRef.current) {
      if (isPlaying) {
        playerRef.current.pause()
      } else {
        playerRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }, [isPlaying])

  const seekTo = useCallback((frame: number) => {
    if (playerRef.current) {
      playerRef.current.seekTo(frame)
      setCurrentFrame(frame)
    }
  }, [])


  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return

      switch (e.key) {
        case ' ':
          e.preventDefault()
          togglePlay()
          break
        case 'ArrowLeft':
          seekTo(Math.max(0, currentFrame - (e.shiftKey ? 30 : 1)))
          break
        case 'ArrowRight':
          seekTo(Math.min(totalFrames, currentFrame + (e.shiftKey ? 30 : 1)))
          break
        case 'Delete':
        case 'Backspace':
          if (selectedClipId) {
            deleteClip(selectedClipId)
          }
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [togglePlay, seekTo, currentFrame, totalFrames, selectedClipId])

  const deleteClip = (clipId: string) => {
    setTracks(tracks.map(track => ({
      ...track,
      clips: track.clips.filter(c => c.id !== clipId)
    })))
    setSelectedClipId(null)
  }

  const formatTime = (frames: number) => {
    const seconds = Math.floor(frames / FPS)
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    const remainingFrames = frames % FPS
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}:${remainingFrames.toString().padStart(2, '0')}`
  }

  return (
    <div className="h-full flex flex-col bg-zinc-950">
      {/* Header */}
      <div className="h-12 border-b border-zinc-800 flex items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <Link to={`/projects/${projectId}`} className="p-1.5 hover:bg-zinc-800 rounded transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <span className="font-medium">비디오 에디터</span>
        </div>
        <div className="flex items-center gap-2">
          <button className="p-2 hover:bg-zinc-800 rounded transition-colors">
            <Settings className="w-5 h-5" />
          </button>
          <button className="px-3 py-1.5 bg-zinc-700 hover:bg-zinc-600 rounded text-sm font-medium transition-colors flex items-center gap-2">
            <Save className="w-4 h-4" />
            저장
          </button>
          <button className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded text-sm font-medium transition-colors flex items-center gap-2">
            <Download className="w-4 h-4" />
            렌더링
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Media Library */}
        <div className="w-64 border-r border-zinc-800 flex flex-col">
          <div className="p-3 border-b border-zinc-800">
            <h3 className="text-sm font-medium">미디어 라이브러리</h3>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            <button className="w-full p-3 border border-dashed border-zinc-700 rounded-lg text-center hover:border-zinc-600 transition-colors">
              <Plus className="w-6 h-6 mx-auto mb-1 text-zinc-500" />
              <span className="text-sm text-zinc-400">미디어 추가</span>
            </button>
          </div>
        </div>

        {/* Center - Preview & Timeline */}
        <div className="flex-1 flex flex-col">
          {/* Preview */}
          <div className="flex-1 flex items-center justify-center bg-black p-4">
            <div className="relative w-full max-w-4xl aspect-video bg-zinc-900 rounded-lg overflow-hidden">
              <Player
                ref={playerRef}
                component={VideoComposition}
                inputProps={{ tracks }}
                durationInFrames={totalFrames}
                compositionWidth={1920}
                compositionHeight={1080}
                fps={FPS}
                style={{ width: '100%', height: '100%' }}
                controls={false}
              />
            </div>
          </div>

          {/* Playback Controls */}
          <div className="h-12 border-t border-zinc-800 flex items-center justify-center gap-4 px-4">
            <button
              onClick={() => seekTo(0)}
              className="p-2 hover:bg-zinc-800 rounded transition-colors"
            >
              <SkipBack className="w-5 h-5" />
            </button>
            <button
              onClick={togglePlay}
              className="w-10 h-10 bg-emerald-600 hover:bg-emerald-500 rounded-full flex items-center justify-center transition-colors"
            >
              {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
            </button>
            <button
              onClick={() => seekTo(totalFrames)}
              className="p-2 hover:bg-zinc-800 rounded transition-colors"
            >
              <SkipForward className="w-5 h-5" />
            </button>

            <div className="text-sm font-mono text-zinc-400">
              {formatTime(currentFrame)} / {formatTime(totalFrames)}
            </div>

            <div className="flex-1" />

            <button
              onClick={() => setMuted(!muted)}
              className="p-2 hover:bg-zinc-800 rounded transition-colors"
            >
              {muted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
            </button>
            <button className="p-2 hover:bg-zinc-800 rounded transition-colors">
              <Maximize className="w-5 h-5" />
            </button>
          </div>

          {/* Timeline */}
          <div className="h-64 border-t border-zinc-800 flex flex-col">
            {/* Timeline Header */}
            <div className="h-8 border-b border-zinc-800 flex items-center justify-between px-4">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setZoom(Math.max(0.25, zoom - 0.25))}
                  className="p-1 hover:bg-zinc-800 rounded"
                >
                  <ZoomOut className="w-4 h-4" />
                </button>
                <span className="text-xs text-zinc-500 w-12 text-center">{(zoom * 100).toFixed(0)}%</span>
                <button
                  onClick={() => setZoom(Math.min(3, zoom + 0.25))}
                  className="p-1 hover:bg-zinc-800 rounded"
                >
                  <ZoomIn className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Time Ruler */}
            <div className="h-6 border-b border-zinc-800 relative bg-zinc-900">
              {Array.from({ length: Math.ceil(totalFrames / FPS) + 1 }).map((_, i) => (
                <div
                  key={i}
                  className="absolute top-0 h-full border-l border-zinc-700 text-xs text-zinc-500 pl-1"
                  style={{ left: i * FPS * zoom }}
                >
                  {i}s
                </div>
              ))}
              {/* Playhead */}
              <div
                className="absolute top-0 h-full w-0.5 bg-emerald-500 z-10"
                style={{ left: currentFrame * zoom }}
              />
            </div>

            {/* Tracks */}
            <div className="flex-1 overflow-y-auto">
              {tracks.map(track => {
                const config = TRACK_CONFIG[track.type]
                const TrackIcon = config.icon

                return (
                  <div key={track.id} className="flex border-b border-zinc-800">
                    {/* Track Label */}
                    <div className="w-32 flex-shrink-0 p-2 border-r border-zinc-800 flex items-center gap-2">
                      <TrackIcon className={`w-4 h-4 text-${config.color}-400`} />
                      <span className="text-sm truncate">{track.name}</span>
                    </div>

                    {/* Track Content */}
                    <div className="flex-1 relative h-12 bg-zinc-900/50">
                      {track.clips.map(clip => {
                        const width = (clip.endFrame - clip.startFrame) * zoom
                        const left = clip.startFrame * zoom

                        return (
                          <div
                            key={clip.id}
                            onClick={() => setSelectedClipId(clip.id)}
                            className={`absolute top-1 h-10 rounded cursor-pointer transition-colors
                              bg-${config.color}-500/30 border border-${config.color}-500/50
                              ${selectedClipId === clip.id ? `ring-2 ring-${config.color}-400` : ''}
                              hover:bg-${config.color}-500/40
                            `}
                            style={{ left, width: Math.max(width, 20) }}
                          >
                            <div className="px-2 py-1 text-xs truncate">
                              {clip.content.type === 'subtitle'
                                ? clip.content.text
                                : clip.content.type === 'image'
                                  ? 'Image'
                                  : 'Audio'
                              }
                            </div>
                          </div>
                        )
                      })}

                      {/* Playhead line */}
                      <div
                        className="absolute top-0 h-full w-0.5 bg-emerald-500 pointer-events-none"
                        style={{ left: currentFrame * zoom }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Right Panel - Properties */}
        <div className="w-64 border-l border-zinc-800 flex flex-col">
          <div className="p-3 border-b border-zinc-800">
            <h3 className="text-sm font-medium">속성</h3>
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            {selectedClipId ? (
              <ClipProperties
                tracks={tracks}
                clipId={selectedClipId}
                onUpdate={(updatedTracks) => setTracks(updatedTracks)}
              />
            ) : (
              <div className="text-sm text-zinc-500 text-center py-8">
                클립을 선택하세요
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function ClipProperties({
  tracks,
  clipId,
  onUpdate: _onUpdate
}: {
  tracks: Track[]
  clipId: string
  onUpdate: (tracks: Track[]) => void
}) {
  let selectedClip: TimelineClip | null = null
  let selectedTrack: Track | null = null

  for (const track of tracks) {
    const clip = track.clips.find(c => c.id === clipId)
    if (clip) {
      selectedClip = clip
      selectedTrack = track
      break
    }
  }

  if (!selectedClip || !selectedTrack) return null

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs text-zinc-500 mb-1">타입</label>
        <div className="text-sm">{selectedClip.content.type}</div>
      </div>

      <div>
        <label className="block text-xs text-zinc-500 mb-1">시작 프레임</label>
        <input
          type="number"
          value={selectedClip.startFrame}
          className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-sm"
          readOnly
        />
      </div>

      <div>
        <label className="block text-xs text-zinc-500 mb-1">끝 프레임</label>
        <input
          type="number"
          value={selectedClip.endFrame}
          className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-sm"
          readOnly
        />
      </div>

      {selectedClip.content.type === 'subtitle' && (
        <div>
          <label className="block text-xs text-zinc-500 mb-1">자막 텍스트</label>
          <textarea
            defaultValue={selectedClip.content.text}
            className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-sm resize-none"
            rows={3}
          />
        </div>
      )}

      {selectedClip.content.type === 'image' && (
        <div>
          <label className="block text-xs text-zinc-500 mb-1">애니메이션</label>
          <select
            defaultValue={selectedClip.content.animation}
            className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-sm"
          >
            <option value="none">없음</option>
            <option value="ken-burns-in">Ken Burns (확대)</option>
            <option value="ken-burns-out">Ken Burns (축소)</option>
            <option value="zoom-in">줌 인</option>
            <option value="zoom-out">줌 아웃</option>
            <option value="fade-in">페이드 인</option>
            <option value="pan-left">팬 왼쪽</option>
            <option value="pan-right">팬 오른쪽</option>
          </select>
        </div>
      )}

      {selectedClip.content.type === 'audio' && (
        <>
          <div>
            <label className="block text-xs text-zinc-500 mb-1">볼륨</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              defaultValue={selectedClip.content.volume}
              className="w-full"
            />
          </div>
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="block text-xs text-zinc-500 mb-1">페이드 인</label>
              <input
                type="number"
                defaultValue={selectedClip.content.fadeIn || 0}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-sm"
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs text-zinc-500 mb-1">페이드 아웃</label>
              <input
                type="number"
                defaultValue={selectedClip.content.fadeOut || 0}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-sm"
              />
            </div>
          </div>
        </>
      )}

      <button className="w-full py-2 bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded text-sm transition-colors flex items-center justify-center gap-2">
        <Trash2 className="w-4 h-4" />
        클립 삭제
      </button>
    </div>
  )
}
