import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ProjectStatus = 'idea' | 'script' | 'media' | 'editor' | 'review' | 'publish' | 'completed'

export interface ProjectIdea {
  title: string
  hook: string
  outline: string[]
  keywords: string[]
}

export interface ProjectScript {
  intro: string
  body: string[]
  outro: string
  cta: string
  estimatedDuration: number
}

export interface Project {
  id: string
  channelId: string
  title: string
  status: ProjectStatus
  idea?: ProjectIdea
  script?: ProjectScript
  thumbnailUrl?: string
  videoUrl?: string
  createdAt: Date
  updatedAt: Date
}

interface ProjectState {
  projects: Project[]

  getProject: (id: string) => Project | undefined
  getProjectsByChannel: (channelId: string) => Project[]
  createProject: (channelId: string, data?: Partial<Project>) => string
  updateProject: (id: string, data: Partial<Project>) => void
  deleteProject: (id: string) => void
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

export const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
      projects: [],

      getProject: (id: string) => {
        return get().projects.find(p => p.id === id)
      },

      getProjectsByChannel: (channelId: string) => {
        return get().projects.filter(p => p.channelId === channelId)
      },

      createProject: (channelId: string, data?: Partial<Project>) => {
        const id = generateId()
        const newProject: Project = {
          id,
          channelId,
          title: data?.title || '새 프로젝트',
          status: 'idea',
          idea: data?.idea,
          script: data?.script,
          createdAt: new Date(),
          updatedAt: new Date()
        }

        set(state => ({
          projects: [...state.projects, newProject]
        }))

        return id
      },

      updateProject: (id: string, data: Partial<Project>) => {
        set(state => ({
          projects: state.projects.map(p =>
            p.id === id
              ? { ...p, ...data, updatedAt: new Date() }
              : p
          )
        }))
      },

      deleteProject: (id: string) => {
        set(state => ({
          projects: state.projects.filter(p => p.id !== id)
        }))
      }
    }),
    {
      name: 'routine-projects-storage'
    }
  )
)
