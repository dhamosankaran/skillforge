// Utility formatting functions for SkillForge

export function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return dateStr
  }
}

export function getGradeColor(grade: string): string {
  if (grade.startsWith('A')) return '#00ffc8'
  if (grade.startsWith('B')) return '#3fb950'
  if (grade.startsWith('C')) return '#f0a500'
  if (grade.startsWith('D')) return '#d29922'
  return '#f85149'
}

export function getScoreColor(score: number): string {
  if (score >= 80) return '#00ffc8'
  if (score >= 60) return '#f0a500'
  return '#f85149'
}

export function getScoreLabel(score: number): string {
  if (score >= 80) return 'Strong Match'
  if (score >= 60) return 'Moderate Match'
  if (score >= 40) return 'Weak Match'
  return 'Poor Match'
}

export function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'critical':
      return '#f85149'
    case 'warning':
      return '#d29922'
    case 'info':
      return '#8b949e'
    default:
      return '#8b949e'
  }
}

export function getSeverityBg(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'rgba(248, 81, 73, 0.1)'
    case 'warning':
      return 'rgba(210, 153, 34, 0.1)'
    case 'info':
      return 'rgba(139, 148, 158, 0.1)'
    default:
      return 'rgba(139, 148, 158, 0.1)'
  }
}

export function getImportanceColor(importance: string): string {
  switch (importance) {
    case 'critical':
      return '#f85149'
    case 'recommended':
      return '#d29922'
    case 'nice-to-have':
      return '#484f58'
    default:
      return '#484f58'
  }
}

export function getImportanceBg(importance: string): string {
  switch (importance) {
    case 'critical':
      return 'rgba(248, 81, 73, 0.12)'
    case 'recommended':
      return 'rgba(210, 153, 34, 0.12)'
    case 'nice-to-have':
      return 'rgba(72, 79, 88, 0.3)'
    default:
      return 'rgba(72, 79, 88, 0.3)'
  }
}

export function getStatusColor(status: string): string {
  switch (status) {
    case 'Applied':
      return '#8b949e'
    case 'Interview':
      return '#00ffc8'
    case 'Offer':
      return '#3fb950'
    case 'Rejected':
      return '#f85149'
    default:
      return '#8b949e'
  }
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength - 3) + '...'
}

export function getBulletScoreColor(score: number): string {
  if (score >= 8) return '#00ffc8'
  if (score >= 5) return '#f0a500'
  return '#f85149'
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
