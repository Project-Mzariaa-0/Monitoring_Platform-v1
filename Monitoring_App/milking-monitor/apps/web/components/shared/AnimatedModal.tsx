'use client';

import React, { useEffect, useRef } from 'react';
import styles from './AnimatedModal.module.css';

interface AnimatedModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: 'small' | 'medium' | 'large';
  className?: string;
}

export function AnimatedModal({
  isOpen,
  onClose,
  title,
  children,
  footer,
  size = 'medium',
  className = '',
}: AnimatedModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      previousFocusRef.current = document.activeElement as HTMLElement;
      dialog.showModal();
      dialog.classList.add(styles.open);
      // Prevent body scroll
      document.body.style.overflow = 'hidden';
    } else {
      dialog.classList.remove(styles.open);
      dialog.close();
      document.body.style.overflow = '';
      previousFocusRef.current?.focus();
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === dialogRef.current) {
      onClose();
    }
  };

  return (
    <dialog
      ref={dialogRef}
      className={`${styles.modal} ${styles[`modal-${size}`]} ${className}`}
      onClick={handleBackdropClick}
    >
      <div className={styles.modalContent}>
        {title && (
          <div className={styles.modalHeader}>
            <h2 className={styles.modalTitle}>{title}</h2>
            <button
              className={styles.modalClose}
              onClick={onClose}
              aria-label="Close modal"
            >
              ✕
            </button>
          </div>
        )}
        <div className={styles.modalBody}>{children}</div>
        {footer && <div className={styles.modalFooter}>{footer}</div>}
      </div>
    </dialog>
  );
}
