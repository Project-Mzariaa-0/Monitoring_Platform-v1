import * as React from 'react'

type StatusVariant = 'success' | 'warning' | 'danger' | 'neutral'

interface StatusTagProps {
  children: React.ReactNode
  variant?: StatusVariant
  className?: string
}

export function StatusTag({ children, variant = 'neutral', className }: StatusTagProps) {
  return (
    <span className={`status-tag status-${variant} ${className ?? ''}`}>
      {children}
    </span>
  )
}
