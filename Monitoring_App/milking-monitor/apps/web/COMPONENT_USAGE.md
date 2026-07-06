# Enhanced Component Usage Guide

This document outlines all the newly enhanced and created components for the UI/UX redesign of the Milking Monitor Platform.

## Overview of Enhancements

### 1. **Animation System** (`globals.css`)
All new animation keyframes are defined in the global CSS and respect `prefers-reduced-motion` for accessibility.

#### Available Animations:
- `shimmer` - Animated gradient loading effect (2s duration)
- `slide-in-right` - Notification/toast slide-in from right
- `slide-in-bottom` - Modal/dropdown slide-up animation
- `scale-in` - Modal/card entrance with scale (0.95 → 1)
- `bounce-in` - Button press feedback with bounce
- `pulse-soft` - Gentle pulse for active states
- `spring-scale` - SealRing entrance with spring easing
- `reveal-up` - Data table row reveal animation
- `fade-in-backdrop` - Backdrop fade-in for modals

### 2. **Enhanced Interactive States**

#### Button Hover Effects
All buttons now have:
- Subtle lift effect: `transform: translateY(-2px)`
- Enhanced shadow on hover
- Smooth transition: 150ms cubic-bezier(0.4, 0, 0.2, 1)
- Disabled state handling with reduced opacity

**Example:**
```tsx
<button className="button button-primary">
  Click me
</button>
```

#### Data Row Interactive Feedback
- Hover background color change: `rgba(31, 77, 58, 0.02)`
- Left padding shift on hover for visual feedback
- Border color emphasis
- Smooth 150ms transition

#### Icon Button Scale Effect
- Scale up on hover: `scale(1.08)`
- Subtle shadow on hover
- Scale down on active: `scale(0.96)`

### 3. **SkeletonLoader Component**

A versatile skeleton loading component with animated shimmer effect.

**Import:**
```tsx
import { SkeletonLoader } from '@/components/shared/SkeletonLoader';
```

**Types:**
- `card` - Full card skeleton (default)
- `row` - Table row skeleton with multiple items
- `circle` - Circular skeleton (avatars, icons)
- `bar` - Horizontal bar skeleton
- `text` - Multiple text lines skeleton

**Usage Examples:**

```tsx
// Card skeleton
<SkeletonLoader type="card" height={120} />

// Multiple table rows with stagger animation
<SkeletonLoader type="row" count={5} />

// Avatar/circle
<SkeletonLoader type="circle" width={48} height={48} />

// Progress bar
<SkeletonLoader type="bar" width="100%" height={8} />

// Text paragraphs
<SkeletonLoader type="text" count={3} />
```

**Props:**
- `type?: 'card' | 'row' | 'circle' | 'bar' | 'text'` - Skeleton type
- `width?: string | number` - Custom width (default: 100%)
- `height?: string | number` - Custom height (default: 120px)
- `count?: number` - Number of items to show (for row/text types)
- `className?: string` - Additional CSS classes

**Features:**
- Animated shimmer gradient
- Staggered animations for multiple items
- Respects `prefers-reduced-motion`
- Matches design system colors

---

### 4. **Toast/Notification System**

A context-based toast notification system for global alerts.

**Setup in your root layout:**

```tsx
import { ToastProvider } from '@/components/shared/Toast';

export default function RootLayout({ children }) {
  return (
    <ToastProvider>
      {children}
    </ToastProvider>
  );
}
```

**Usage in Components:**

```tsx
'use client';

import { useToast } from '@/components/shared/Toast';

export function MyComponent() {
  const { addToast } = useToast();

  const handleSuccess = () => {
    addToast('Operation completed successfully!', 'success', 4000);
  };

  const handleError = () => {
    addToast('Something went wrong', 'danger', 5000);
  };

  return (
    <>
      <button onClick={handleSuccess}>Show Success</button>
      <button onClick={handleError}>Show Error</button>
    </>
  );
}
```

**Toast Types:**
- `success` - Green/success colored toast
- `warning` - Orange/warning colored toast
- `danger` - Red/error colored toast
- `info` - Blue/info colored toast

**Method Signature:**
```tsx
addToast(
  message: string,
  type: 'success' | 'warning' | 'danger' | 'info',
  duration?: number // milliseconds (default: 4000)
): string // returns toast ID
```

**Features:**
- Auto-dismiss after duration
- Manual close button
- Slide-in animation from bottom-right
- Stacks multiple toasts
- Accessible with proper ARIA roles
- Responsive on mobile

---

### 5. **EmptyState Component**

A branded empty state component for when data is unavailable.

**Import:**
```tsx
import { EmptyState } from '@/components/shared/EmptyState';
```

**Usage:**

```tsx
// Simple empty state
<EmptyState
  icon="📋"
  headline="No sessions yet"
  description="Create your first session to get started"
/>

// With CTA button
<EmptyState
  icon="🐄"
  headline="No milking sessions"
  description="Start a new session to begin monitoring"
  action={{
    label: 'Start Session',
    href: '/sessions/new'
  }}
/>

// With onClick handler
<EmptyState
  icon="⚠️"
  headline="No data available"
  description="Try adjusting your filters"
  action={{
    label: 'Reset Filters',
    onClick: () => resetFilters()
  }}
/>
```

**Props:**
- `icon?: React.ReactNode` - Icon/emoji (any React node)
- `headline: string` - Main heading (required)
- `description?: string` - Supporting text
- `action?: { label: string; href?: string; onClick?: () => void }` - CTA button
- `className?: string` - Additional CSS classes

**Features:**
- Staggered entrance animation
- Spring scale icon animation
- Customizable icon (emoji, SVG, custom component)
- Responsive design
- Respects motion preferences

---

### 6. **AnimatedModal Component**

A modern modal with smooth entrance/exit animations and focus management.

**Import:**
```tsx
import { AnimatedModal } from '@/components/shared/AnimatedModal';
```

**Usage:**

```tsx
'use client';

import { useState } from 'react';
import { AnimatedModal } from '@/components/shared/AnimatedModal';

export function ModalExample() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button onClick={() => setIsOpen(true)}>Open Modal</button>

      <AnimatedModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Confirm Action"
        size="medium"
      >
        <p>Are you sure you want to proceed?</p>
      </AnimatedModal>
    </>
  );
}
```

**Props:**
- `isOpen: boolean` - Control modal visibility
- `onClose: () => void` - Callback when closing
- `title?: string` - Modal title
- `children: React.ReactNode` - Modal body content
- `footer?: React.ReactNode` - Footer action buttons
- `size?: 'small' | 'medium' | 'large'` - Modal width (default: 'medium')
- `className?: string` - Additional CSS classes

**Sizes:**
- `small` - 400px max width
- `medium` - 600px max width (default)
- `large` - 800px max width

**Example with Footer:**

```tsx
<AnimatedModal
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
  title="Save Changes?"
  size="medium"
  footer={
    <div style={{ display: 'flex', gap: '12px' }}>
      <button className="button button-secondary" onClick={() => setIsOpen(false)}>
        Cancel
      </button>
      <button className="button button-primary" onClick={handleSave}>
        Save
      </button>
    </div>
  }
>
  <p>You have unsaved changes. Do you want to save before leaving?</p>
</AnimatedModal>
```

**Features:**
- Scale-in animation with spring easing
- Backdrop fade-in
- Focus trap (auto-focus body on open)
- Keyboard support (Escape to close)
- Click-outside to close
- Prevents body scroll
- Auto-restores previous focus on close
- Smooth animations

---

### 7. **SearchBar Component**

An enhanced search input with keyboard navigation and suggestion dropdown.

**Import:**
```tsx
import { SearchBar } from '@/components/layout/SearchBar';
```

**Basic Usage:**

```tsx
<SearchBar
  placeholder="Search sessions..."
  onSearch={(query) => console.log('Search:', query)}
/>
```

**With Suggestions:**

```tsx
const sessions = ['Session A', 'Session B', 'Session C'];

<SearchBar
  placeholder="Search sessions..."
  suggestions={sessions}
  onSearch={(query) => handleSearch(query)}
  onSuggestionSelect={(suggestion) => handleSelectSuggestion(suggestion)}
/>
```

**Props:**
- `placeholder?: string` - Input placeholder (default: 'Search...')
- `onSearch?: (query: string) => void` - Called on search/enter
- `suggestions?: string[]` - Array of suggestions
- `onSuggestionSelect?: (suggestion: string) => void` - Called when suggestion selected

**Features:**
- Keyboard navigation (arrow keys, enter, escape)
- Filtered suggestions based on input
- Click to select suggestion
- Focus styling with border and shadow
- Slide-up animation for suggestions
- Responsive design
- Accessible with ARIA attributes

**Keyboard Shortcuts:**
- `↓` / `↑` - Navigate suggestions
- `Enter` - Select highlighted suggestion or search
- `Escape` - Close suggestions

---

## Enhanced SealRing Component

The `SealRing` component now has optional mount animations.

**New Props:**
- `animateOnMount?: boolean` - Enable spring animation on mount (default: true)

**Usage:**

```tsx
import { SealRing } from '@/components/ui/seal-ring';

// With animation (default)
<SealRing value={85} label="Compliance" />

// Without animation
<SealRing value={85} label="Compliance" animateOnMount={false} />

// Custom size and spring animation
<SealRing
  value={92}
  size={80}
  label="System Health"
  animateOnMount={true}
  color="var(--success)"
/>
```

**Animation Details:**
- Spring scale entrance: 500ms with cubic-bezier(0.34, 1.56, 0.64, 1)
- Arc fill animates smoothly over 600ms
- Respects prefers-reduced-motion

---

## Global Styling Updates

### Updated CSS Classes

#### Button Hover States
```css
.button-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(31, 77, 58, 0.15);
}
```

#### Data Row Hover
```css
.data-row:hover {
  background: rgba(31, 77, 58, 0.02);
  padding-left: 8px;
}
```

#### Icon Button Interactive
```css
.icon-button:hover {
  transform: scale(1.08);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.icon-button:active {
  transform: scale(0.96);
}
```

#### Focus States
```css
.button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
```

---

## Best Practices

### 1. **Animation Timing**
- Keep transitions at 150ms for micro-interactions
- Use 300-400ms for page/modal transitions
- Avoid animations that interfere with functionality

### 2. **Motion Preferences**
All components automatically respect `prefers-reduced-motion`. No additional setup needed.

### 3. **Loading States**
Always use `SkeletonLoader` instead of spinners or blank spaces:
```tsx
{isLoading ? (
  <SkeletonLoader type="row" count={5} />
) : (
  <DataTable data={data} />
)}
```

### 4. **User Feedback**
Always provide feedback for user actions:
```tsx
const handleSave = async () => {
  try {
    await saveData();
    addToast('Changes saved successfully', 'success');
  } catch (error) {
    addToast('Failed to save changes', 'danger');
  }
};
```

### 5. **Empty States**
Show empty states instead of blank screens:
```tsx
{data.length === 0 ? (
  <EmptyState
    icon="📊"
    headline="No data yet"
    description="Start creating records to see them here"
  />
) : (
  <DataDisplay data={data} />
)}
```

---

## Accessibility

All enhanced components follow WCAG 2.1 guidelines:
- Keyboard navigation fully supported
- Screen reader compatible with proper ARIA roles
- Focus states clearly visible
- Color contrast ratios maintained
- Motion preferences respected
- Touch-friendly sizing (min 44px targets)

---

## Browser Support

All animations use CSS properties supported in modern browsers:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari 14+, Chrome Android)

The animations gracefully degrade in older browsers (elements still appear, just without animation).

---

## Migration Guide

### From Old SkeletonCard to New SkeletonLoader

**Old:**
```tsx
<SkeletonCard count={3} />
```

**New:**
```tsx
<SkeletonLoader type="row" count={3} />
```

### Adding Toasts to Existing Components

1. Wrap your app with `ToastProvider`
2. Import `useToast` in your component
3. Call `addToast()` on user actions

### Replacing Alert() with Toast

**Old:**
```tsx
alert('Operation complete');
```

**New:**
```tsx
const { addToast } = useToast();
addToast('Operation complete', 'success');
```

---

## Performance Tips

- SkeletonLoader animations are GPU-accelerated using CSS
- Toast system batches multiple notifications
- Modal uses native `<dialog>` element
- SearchBar uses debounced filtering
- All components use CSS modules for scoped styling

---

## Support

For issues or questions about these components, refer to the implementation files:
- `app/globals.css` - Animation keyframes
- `components/shared/` - Reusable components
- `components/layout/SearchBar.tsx` - Search component
- `components/ui/seal-ring.tsx` - Enhanced SealRing
