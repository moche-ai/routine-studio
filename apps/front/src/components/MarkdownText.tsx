import React from 'react'

interface MarkdownTextProps {
  content: string
  className?: string
}

export function MarkdownText({ content, className = '' }: MarkdownTextProps) {
  const renderLine = (line: string, lineIndex: number) => {
    // 리스트 아이템 처리 (- 로 시작)
    const isListItem = line.trim().startsWith('- ')
    const lineContent = isListItem ? line.trim().slice(2) : line

    // **bold** 처리
    const parts = lineContent.split(/(\*\*[^*]+\*\*)/)
    const renderedParts = parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} className="text-emerald-300 font-semibold">
            {part.slice(2, -2)}
          </strong>
        )
      }
      return <React.Fragment key={i}>{part}</React.Fragment>
    })

    if (isListItem) {
      return (
        <div key={lineIndex} className="flex items-start gap-2 my-1">
          <span className="text-emerald-400 mt-1">•</span>
          <span>{renderedParts}</span>
        </div>
      )
    }

    return (
      <div key={lineIndex} className="my-1">
        {renderedParts}
      </div>
    )
  }

  const lines = content.split('\n')

  return (
    <div className={className}>
      {lines.map((line, i) => renderLine(line, i))}
    </div>
  )
}
