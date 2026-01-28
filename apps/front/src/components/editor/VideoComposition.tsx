import React from 'react'
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  Sequence,
  Audio,
  Img,
  interpolate,
  spring
} from 'remotion'

// Types
export type TrackType = 'video' | 'overlay' | 'audio' | 'bgm' | 'sfx' | 'subtitle'

export type ImageAnimation =
  | 'none'
  | 'ken-burns-in' | 'ken-burns-out'
  | 'pan-left' | 'pan-right' | 'pan-up' | 'pan-down'
  | 'zoom-in' | 'zoom-out'
  | 'fade-in' | 'fade-out'
  | 'slide-in-left' | 'slide-in-right'

export type SubtitleAnimation =
  | 'none'
  | 'typewriter'
  | 'fade-in-up'
  | 'bounce'
  | 'scale'

export interface ImageClipContent {
  type: 'image'
  src: string
  animation: ImageAnimation
}

export interface AudioClipContent {
  type: 'audio'
  src: string
  volume: number
  fadeIn?: number
  fadeOut?: number
}

export interface SubtitleStyle {
  font: string
  size: number
  color: string
  position: 'top' | 'center' | 'bottom'
}

export interface SubtitleClipContent {
  type: 'subtitle'
  text: string
  style: SubtitleStyle
  animation: SubtitleAnimation
}

export type ClipContent = ImageClipContent | AudioClipContent | SubtitleClipContent

export interface TimelineClip {
  id: string
  startFrame: number
  endFrame: number
  content: ClipContent
}

export interface Track {
  id: string
  type: TrackType
  name: string
  clips: TimelineClip[]
  muted: boolean
}

interface VideoCompositionProps {
  tracks: Track[]
}

// Main Composition
export const VideoComposition: React.FC<VideoCompositionProps> = ({ tracks }) => {
  const trackOrder: TrackType[] = ['video', 'overlay', 'subtitle']
  const audioTypes: TrackType[] = ['audio', 'bgm', 'sfx']

  const visualTracks = tracks.filter(t => trackOrder.includes(t.type))
  const audioTracks = tracks.filter(t => audioTypes.includes(t.type))

  visualTracks.sort((a, b) => trackOrder.indexOf(a.type) - trackOrder.indexOf(b.type))

  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>
      {visualTracks.map(track => (
        <TrackRenderer key={track.id} track={track} />
      ))}
      {audioTracks.map(track => (
        <AudioTrackRenderer key={track.id} track={track} />
      ))}
    </AbsoluteFill>
  )
}

// Track Renderer
const TrackRenderer: React.FC<{ track: Track }> = ({ track }) => {
  if (track.muted) return null

  return (
    <>
      {track.clips.map(clip => (
        <Sequence
          key={clip.id}
          from={clip.startFrame}
          durationInFrames={clip.endFrame - clip.startFrame}
        >
          <ClipRenderer clip={clip} />
        </Sequence>
      ))}
    </>
  )
}

// Audio Track Renderer
const AudioTrackRenderer: React.FC<{ track: Track }> = ({ track }) => {
  if (track.muted) return null

  return (
    <>
      {track.clips.map(clip => {
        if (clip.content.type !== 'audio') return null

        return (
          <Sequence
            key={clip.id}
            from={clip.startFrame}
            durationInFrames={clip.endFrame - clip.startFrame}
          >
            <AudioClipRenderer content={clip.content} />
          </Sequence>
        )
      })}
    </>
  )
}

// Clip Renderer
const ClipRenderer: React.FC<{ clip: TimelineClip }> = ({ clip }) => {
  switch (clip.content.type) {
    case 'image':
      return <ImageClipRenderer content={clip.content} />
    case 'subtitle':
      return <SubtitleClipRenderer content={clip.content} />
    case 'audio':
      return <AudioClipRenderer content={clip.content} />
    default:
      return null
  }
}

// Image Clip Renderer with Animations
const ImageClipRenderer: React.FC<{ content: ImageClipContent }> = ({ content }) => {
  const frame = useCurrentFrame()
  const { durationInFrames } = useVideoConfig()

  let transform = ''
  let opacity = 1

  switch (content.animation) {
    case 'ken-burns-in': {
      const scale = interpolate(frame, [0, durationInFrames], [1, 1.2], { extrapolateRight: 'clamp' })
      transform = `scale(${scale})`
      break
    }
    case 'ken-burns-out': {
      const scale = interpolate(frame, [0, durationInFrames], [1.2, 1], { extrapolateRight: 'clamp' })
      transform = `scale(${scale})`
      break
    }
    case 'zoom-in': {
      const scale = interpolate(frame, [0, durationInFrames], [1, 1.3], { extrapolateRight: 'clamp' })
      transform = `scale(${scale})`
      break
    }
    case 'zoom-out': {
      const scale = interpolate(frame, [0, durationInFrames], [1.3, 1], { extrapolateRight: 'clamp' })
      transform = `scale(${scale})`
      break
    }
    case 'pan-left': {
      const x = interpolate(frame, [0, durationInFrames], [0, -100], { extrapolateRight: 'clamp' })
      transform = `translateX(${x}px) scale(1.1)`
      break
    }
    case 'pan-right': {
      const x = interpolate(frame, [0, durationInFrames], [0, 100], { extrapolateRight: 'clamp' })
      transform = `translateX(${x}px) scale(1.1)`
      break
    }
    case 'fade-in': {
      opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' })
      break
    }
    case 'fade-out': {
      opacity = interpolate(frame, [durationInFrames - 15, durationInFrames], [1, 0], { extrapolateLeft: 'clamp' })
      break
    }
    case 'slide-in-left': {
      const x = interpolate(frame, [0, 15], [-100, 0], { extrapolateRight: 'clamp' })
      transform = `translateX(${x}%)`
      break
    }
    case 'slide-in-right': {
      const x = interpolate(frame, [0, 15], [100, 0], { extrapolateRight: 'clamp' })
      transform = `translateX(${x}%)`
      break
    }
  }

  return (
    <AbsoluteFill style={{ opacity }}>
      <Img
        src={content.src}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform
        }}
      />
    </AbsoluteFill>
  )
}

// Subtitle Clip Renderer with Animations
const SubtitleClipRenderer: React.FC<{ content: SubtitleClipContent }> = ({ content }) => {
  const frame = useCurrentFrame()
  const { fps } = useVideoConfig()

  const { style, text, animation } = content

  let animatedStyle: React.CSSProperties = {}
  let displayText = text

  switch (animation) {
    case 'typewriter': {
      const charsToShow = Math.floor(frame / 2)
      displayText = text.slice(0, charsToShow)
      break
    }
    case 'fade-in-up': {
      const progress = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' })
      const y = interpolate(progress, [0, 1], [20, 0])
      animatedStyle = {
        opacity: progress,
        transform: `translateY(${y}px)`
      }
      break
    }
    case 'bounce': {
      const scale = spring({
        frame,
        fps,
        config: { damping: 10, stiffness: 100, mass: 0.5 }
      })
      animatedStyle = { transform: `scale(${scale})` }
      break
    }
    case 'scale': {
      const scaleVal = interpolate(frame, [0, 10], [0.8, 1], { extrapolateRight: 'clamp' })
      const opacityVal = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: 'clamp' })
      animatedStyle = { transform: `scale(${scaleVal})`, opacity: opacityVal }
      break
    }
  }

  const positionStyle: React.CSSProperties = {
    top: style.position === 'top' ? '10%' : undefined,
    bottom: style.position === 'bottom' ? '10%' : undefined,
    ...(style.position === 'center' && {
      top: '50%',
      transform: `translateY(-50%) ${animatedStyle.transform || ''}`
    })
  }

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        ...positionStyle
      }}
    >
      <div
        style={{
          fontFamily: style.font || 'Pretendard, sans-serif',
          fontSize: style.size || 48,
          color: style.color || '#ffffff',
          textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
          padding: '10px 20px',
          textAlign: 'center',
          maxWidth: '80%',
          ...animatedStyle
        }}
      >
        {displayText}
      </div>
    </AbsoluteFill>
  )
}

// Audio Clip Renderer with Volume & Fade
const AudioClipRenderer: React.FC<{ content: AudioClipContent }> = ({ content }) => {
  const frame = useCurrentFrame()
  const { durationInFrames } = useVideoConfig()

  let volume = content.volume

  if (content.fadeIn && frame < content.fadeIn) {
    volume *= interpolate(frame, [0, content.fadeIn], [0, 1])
  }

  if (content.fadeOut && frame > durationInFrames - content.fadeOut) {
    volume *= interpolate(
      frame,
      [durationInFrames - content.fadeOut, durationInFrames],
      [1, 0]
    )
  }

  return <Audio src={content.src} volume={volume} />
}

export default VideoComposition
