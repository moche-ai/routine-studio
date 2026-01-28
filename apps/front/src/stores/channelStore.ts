import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface ChannelSettings {
  style?: {
    tone: string
    format: string
  }
  tts?: {
    voice: string
    speed: number
  }
  image?: {
    style: string
    checkpoint: string
  }
  thumbnail?: {
    template: string
    colors: string[]
  }
  branding?: {
    logo: string
    colors: string[]
  }
  subtitle?: {
    font: string
    size: number
    color: string
  }
}

export interface Channel {
  id: string
  name: string
  description: string
  category: string
  targetAudience: string
  thumbnailUrl?: string
  settings: ChannelSettings
  setupCompleted: boolean
  createdAt: Date
  updatedAt: Date
}

interface ChannelState {
  channels: Channel[]
  currentChannelId: string | null

  getChannel: (id: string) => Channel | undefined
  getCurrentChannel: () => Channel | undefined
  createChannel: (data: Partial<Channel>) => string
  updateChannel: (id: string, data: Partial<Channel>) => void
  deleteChannel: (id: string) => void
  selectChannel: (id: string | null) => void
}

const generateId = (): string => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

export const useChannelStore = create<ChannelState>()(
  persist(
    (set, get) => ({
      channels: [],
      currentChannelId: null,

      getChannel: (id: string) => {
        return get().channels.find(c => c.id === id)
      },

      getCurrentChannel: () => {
        const state = get()
        return state.channels.find(c => c.id === state.currentChannelId)
      },

      createChannel: (data: Partial<Channel>) => {
        const id = generateId()
        const newChannel: Channel = {
          id,
          name: data.name || '새 채널',
          description: data.description || '',
          category: data.category || '',
          targetAudience: data.targetAudience || '',
          thumbnailUrl: data.thumbnailUrl,
          settings: data.settings || {},
          setupCompleted: false,
          createdAt: new Date(),
          updatedAt: new Date()
        }

        set(state => ({
          channels: [...state.channels, newChannel],
          currentChannelId: id
        }))

        return id
      },

      updateChannel: (id: string, data: Partial<Channel>) => {
        set(state => ({
          channels: state.channels.map(c =>
            c.id === id
              ? { ...c, ...data, updatedAt: new Date() }
              : c
          )
        }))
      },

      deleteChannel: (id: string) => {
        set(state => ({
          channels: state.channels.filter(c => c.id !== id),
          currentChannelId: state.currentChannelId === id ? null : state.currentChannelId
        }))
      },

      selectChannel: (id: string | null) => {
        set({ currentChannelId: id })
      }
    }),
    {
      name: 'routine-channels-storage'
    }
  )
)
