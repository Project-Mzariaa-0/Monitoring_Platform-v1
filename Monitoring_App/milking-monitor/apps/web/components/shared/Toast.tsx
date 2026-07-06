'use client';

import React, { useEffect } from 'react';
import styles from './Toast.module.css';

type ToastType = 'success' | 'warning' | 'danger' | 'info';

export interface ToastMessage {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
}

interface ToastProps extends ToastMessage {
  onDismiss: (id: string) => void;
}

const typeConfig: Record<ToastType, { icon: string; label: string }> = {
  success: { icon: '✓', label: 'Success' },
  warning: { icon: '⚠', label: 'Warning' },
  danger: { icon: '✕', label: 'Error' },
  info: { icon: 'ⓘ', label: 'Info' },
};

export function Toast({ id, message, type, duration = 4000, onDismiss }: ToastProps) {
  useEffect(() => {
    if (duration === 0) return;

    const timer = setTimeout(() => {
      onDismiss(id);
    }, duration);

    return () => clearTimeout(timer);
  }, [id, duration, onDismiss]);

  const config = typeConfig[type];

  return (
    <div className={`${styles.toast} ${styles[`toast-${type}`]}`} role="alert">
      <div className={styles.toastIcon}>{config.icon}</div>
      <div className={styles.toastContent}>
        <p className={styles.toastMessage}>{message}</p>
      </div>
      <button
        className={styles.toastClose}
        onClick={() => onDismiss(id)}
        aria-label="Dismiss notification"
      >
        ✕
      </button>
    </div>
  );
}

export function ToastContainer({
  toasts,
  onDismiss,
}: {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}) {
  return (
    <div className={styles.toastContainer}>
      {toasts.map((toast) => (
        <Toast key={toast.id} {...toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

// Context for managing toasts globally
export const ToastContext = React.createContext<{
  addToast: (message: string, type: ToastType, duration?: number) => string;
  removeToast: (id: string) => void;
} | null>(null);

export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastMessage[]>([]);

  const addToast = (message: string, type: ToastType = 'info', duration = 4000) => {
    const id = `toast-${Date.now()}-${Math.random()}`;
    const newToast: ToastMessage = { id, message, type, duration };

    setToasts((prev) => [...prev, newToast]);
    return id;
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </ToastContext.Provider>
  );
}
