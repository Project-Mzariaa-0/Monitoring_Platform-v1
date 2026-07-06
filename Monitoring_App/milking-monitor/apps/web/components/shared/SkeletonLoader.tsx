'use client';

import React from 'react';
import styles from './SkeletonLoader.module.css';

type SkeletonType = 'card' | 'row' | 'circle' | 'bar' | 'text';

interface SkeletonLoaderProps {
  type?: SkeletonType;
  width?: string | number;
  height?: string | number;
  count?: number;
  className?: string;
}

export function SkeletonLoader({
  type = 'card',
  width = '100%',
  height = 120,
  count = 1,
  className = '',
}: SkeletonLoaderProps) {
  const widthStr = typeof width === 'number' ? `${width}px` : width;
  const heightStr = typeof height === 'number' ? `${height}px` : height;

  if (type === 'card') {
    return (
      <div className={`${styles.skeletonCard} ${className}`}>
        <div
          className={styles.shimmer}
          style={{ width: widthStr, height: heightStr }}
        />
      </div>
    );
  }

  if (type === 'row') {
    return (
      <div className={styles.skeletonList}>
        {Array.from({ length: count || 3 }).map((_, i) => (
          <div key={i} className={styles.skeletonRow}>
            <div
              className={styles.shimmer}
              style={{ width: '60px', height: '40px', borderRadius: '8px' }}
            />
            <div style={{ flex: 1 }}>
              <div
                className={styles.shimmer}
                style={{ width: '100%', height: '16px', marginBottom: '8px' }}
              />
              <div
                className={styles.shimmer}
                style={{ width: '60%', height: '14px' }}
              />
            </div>
            <div
              className={styles.shimmer}
              style={{ width: '80px', height: '24px', borderRadius: '999px' }}
            />
          </div>
        ))}
      </div>
    );
  }

  if (type === 'circle') {
    return (
      <div
        className={`${styles.shimmer} ${styles.skeletonCircle}`}
        style={{
          width: widthStr,
          height: heightStr,
          borderRadius: '999px',
        }}
      />
    );
  }

  if (type === 'bar') {
    return (
      <div className={styles.skeletonBar}>
        <div
          className={styles.shimmer}
          style={{ width: widthStr, height: heightStr }}
        />
      </div>
    );
  }

  // text type
  return (
    <div className={styles.skeletonText}>
      {Array.from({ length: count || 2 }).map((_, i) => (
        <div
          key={i}
          className={styles.shimmer}
          style={{
            width: i === (count || 2) - 1 ? '80%' : '100%',
            height: '14px',
            marginBottom: i < (count || 2) - 1 ? '8px' : '0',
          }}
        />
      ))}
    </div>
  );
}
