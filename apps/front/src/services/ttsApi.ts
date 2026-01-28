const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

// ============================================================================
// Type Definitions
// ============================================================================

export interface InstructExample {
  label: string
  value: string
  description: string
}

export interface InstructExamples {
  emotions: InstructExample[]
  speed_range: {
    min: number
    max: number
    default: number
    step: number
  }
  pitch_range: {
    min: number
    max: number
    default: number
    step: number
  }
}

export interface TTSResult {
  audio_base64: string
  duration: number
  voice_name: string
  text: string
}

export interface VoiceSample {
  voice_id: string
  filename: string
  prompt_text: string
  index: number
}

export interface SamplesResponse {
  samples: VoiceSample[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface SampleAudioResponse {
  voice_id: string
  filename: string
  prompt_text: string
  audio_base64: string
}

export interface YouTubeExtractResponse {
  audio_base64: string
  duration: number
  video_id: string
  ref_text: string
  quality_score: number
}

// ============================================================================
// API Functions
// ============================================================================

export const ttsApi = {
  /**
   * 감정/스타일 예시 목록 조회
   */
  async getInstructExamples(): Promise<InstructExamples> {
    const response = await fetch(API_BASE + "/api/tts/instruct-examples")

    if (!response.ok) {
      throw new Error("Failed to fetch instruct examples: " + response.status)
    }

    return response.json()
  },

  /**
   * TTS 미리듣기 생성
   */
  async generatePreview(
    text: string,
    speaker?: string,
    speed?: number,
    pitch?: number,
    instruct?: string
  ): Promise<TTSResult> {
    const response = await fetch(API_BASE + "/api/tts/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        speaker,
        speed,
        pitch,
        instruct
      })
    })

    if (!response.ok) {
      throw new Error("Failed to generate preview: " + response.status)
    }

    return response.json()
  },

  /**
   * 음성 샘플 목록 조회 (페이지네이션)
   */
  async getVoiceSamples(page: number = 1, perPage: number = 10): Promise<SamplesResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: perPage.toString()
    })

    const response = await fetch(API_BASE + "/api/tts/samples?" + params.toString())

    if (!response.ok) {
      throw new Error("Failed to fetch voice samples: " + response.status)
    }

    return response.json()
  },

  /**
   * 특정 샘플 오디오 조회
   */
  async getSampleAudio(voiceId: string): Promise<SampleAudioResponse> {
    const response = await fetch(API_BASE + "/api/tts/sample/" + voiceId)

    if (!response.ok) {
      throw new Error("Failed to fetch sample audio: " + response.status)
    }

    return response.json()
  },

  /**
   * YouTube 오디오 추출
   */
  async extractYouTubeAudio(
    url: string,
    startTime: string,
    endTime: string
  ): Promise<YouTubeExtractResponse> {
    const response = await fetch(API_BASE + "/api/tts/extract-youtube", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url,
        start_time: startTime,
        end_time: endTime
      })
    })

    if (!response.ok) {
      throw new Error("Failed to extract YouTube audio: " + response.status)
    }

    return response.json()
  },

  /**
   * 음성 클로닝 미리듣기
   */
  async cloneVoicePreview(
    text: string,
    refAudioBase64: string,
    refText?: string
  ): Promise<TTSResult> {
    const response = await fetch(API_BASE + "/api/tts/clone-preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        ref_audio_base64: refAudioBase64,
        ref_text: refText
      })
    })

    if (!response.ok) {
      throw new Error("Failed to generate clone preview: " + response.status)
    }

    return response.json()
  }
}
