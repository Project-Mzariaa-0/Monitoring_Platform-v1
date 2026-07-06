'use client'

import * as React from 'react'

interface SealRingProps {
  value: number
  size?: number
  strokeWidth?: number
  label?: string
  color?: string
  className?: string
  animateOnMount?: boolean
}

export function SealRing({
  value,
  size = 56,
  strokeWidth = 5,
  label,
  color,
  className,
  animateOnMount = true,
}: SealRingProps) {
  const [mounted, setMounted] = React.useState(animateOnMount)
  const clamped = Math.max(0, Math.min(100, value))
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (clamped / 100) * circumference

  const strokeColor =
    color ?? (clamped >= 80 ? 'var(--accent)' : clamped >= 50 ? 'var(--warning)' : 'var(--danger)')

  const textColor = 'var(--text-primary)'
  const trackColor = 'var(--border)'

  return (
    <div
      className={`seal-ring-container ${className ?? ''}`}
      style={{
        width: size,
        height: size + (label ? 20 : 0),
        animation: mounted ? 'spring-scale 500ms cubic-bezier(0.34, 1.56, 0.64, 1) both' : 'none',
      }}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={trackColor}
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: 'stroke-dashoffset 600ms cubic-bezier(0.34, 1.56, 0.64, 1)' }}
        />
        <text
          x="50%"
          y="50%"
          dominantBaseline="central"
          textAnchor="middle"
          fill={textColor}
          className="seal-ring-value"
          style={{ fontSize: size * 0.26 }}
        >
          {clamped}
        </text>
      </svg>
      {label && <span className="seal-ring-label">{label}</span>}
    </div>
  )
}
