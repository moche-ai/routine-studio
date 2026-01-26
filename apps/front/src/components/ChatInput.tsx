import { useState, useRef, type KeyboardEvent } from "react"
import { ImagePlus, Send, X } from "lucide-react"

interface Props {
  onSend: (content: string, images: string[]) => void
  disabled?: boolean
}

export function ChatInput({ onSend, disabled }: Props) {
  const [text, setText] = useState("")
  const [images, setImages] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return

    Array.from(files).forEach(file => {
      const reader = new FileReader()
      reader.onload = (e) => {
        const base64 = e.target?.result as string
        setImages(prev => [...prev, base64])
      }
      reader.readAsDataURL(file)
    })
    
    e.target.value = ""
  }

  const removeImage = (index: number) => {
    setImages(prev => prev.filter((_, i) => i !== index))
  }

  const handleSend = () => {
    if (!text.trim() && images.length === 0) return
    onSend(text, images)
    setText("")
    setImages([])
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t border-zinc-800 p-4">
      {/* 이미지 프리뷰 */}
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {images.map((img, idx) => (
            <div key={idx} className="relative">
              <img src={img} alt="" className="w-20 h-20 object-cover rounded-lg" />
              <button
                onClick={() => removeImage(idx)}
                className="absolute -top-2 -right-2 bg-red-500 rounded-full p-1 hover:bg-red-600"
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-end gap-2">
        {/* 이미지 첨부 버튼 */}
        <button
          onClick={() => fileInputRef.current?.click()}
          className="p-3 bg-zinc-800 rounded-xl hover:bg-zinc-700 transition"
          disabled={disabled}
        >
          <ImagePlus size={20} />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={handleImageSelect}
          className="hidden"
        />

        {/* 텍스트 입력 */}
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="메시지를 입력하세요..."
          disabled={disabled}
          rows={1}
          className="flex-1 bg-zinc-800 rounded-xl px-4 py-3 resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
        />

        {/* 전송 버튼 */}
        <button
          onClick={handleSend}
          disabled={disabled || (!text.trim() && images.length === 0)}
          className="p-3 bg-emerald-600 rounded-xl hover:bg-emerald-500 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send size={20} />
        </button>
      </div>
    </div>
  )
}
