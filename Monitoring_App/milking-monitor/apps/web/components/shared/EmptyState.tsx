'use client';

import React from 'react';
import Link from 'next/link';
import styles from './EmptyState.module.css';

interface EmptyStateProps {
  icon?: React.ReactNode;
  headline: string;
  description?: string;
  action?: {
    label: string;
    href?: string;
    onClick?: () => void;
  };
  className?: string;
}

export function EmptyState({
  icon,
  headline,
  description,
  action,
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`${styles.emptyState} ${className}`}>
      {icon && <div className={styles.emptyIcon}>{icon}</div>}
      <h3 className={styles.emptyHeadline}>{headline}</h3>
      {description && <p className={styles.emptyDescription}>{description}</p>}
      {action && (
        <>
          {action.href ? (
            <Link href={action.href} className={styles.emptyAction}>
              {action.label}
            </Link>
          ) : (
            <button className={styles.emptyAction} onClick={action.onClick}>
              {action.label}
            </button>
          )}
        </>
      )}
    </div>
  );
}
