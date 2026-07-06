# Quick Start - Enhanced Components

A quick reference for using the new enhanced UI components in the Milking Monitor Platform.

## 1. Setup (One-Time)

Add ToastProvider to your root layout:

```tsx
// app/layout.tsx
import { ToastProvider } from '@/components/shared/Toast';

export default function RootLayout({ children }) {
  return (
    <ToastProvider>
      {children}
    </ToastProvider>
  );
}
```

## 2. Loading States

Replace spinner/blank states with SkeletonLoader:

```tsx
import { SkeletonLoader } from '@/components/shared/SkeletonLoader';

export function MyDataTable() {
  const { data, isLoading } = useData();

  return isLoading ? (
    <SkeletonLoader type="row" count={5} />
  ) : (
    <Table data={data} />
  );
}
```

**Types:**
- `card` - Single card
- `row` - Table row (best for lists)
- `circle` - Avatar/icon
- `bar` - Progress bar
- `text` - Paragraph text

## 3. User Feedback

Use Toast instead of alerts:

```tsx
'use client';

import { useToast } from '@/components/shared/Toast';

export function MyComponent() {
  const { addToast } = useToast();

  const handleSave = async () => {
    try {
      await saveData();
      addToast('Saved successfully!', 'success');
    } catch (error) {
      addToast('Failed to save', 'danger');
    }
  };

  return <button onClick={handleSave}>Save</button>;
}
```

**Toast Types:** `'success' | 'warning' | 'danger' | 'info'`

## 4. Empty States

Show branded empty state instead of blank screen:

```tsx
import { EmptyState } from '@/components/shared/EmptyState';

export function SessionsList() {
  const { sessions } = useData();

  return sessions.length === 0 ? (
    <EmptyState
      icon="📋"
      headline="No sessions yet"
      description="Create your first session to start monitoring"
      action={{
        label: 'New Session',
        href: '/sessions/new'
      }}
    />
  ) : (
    <Sessions data={sessions} />
  );
}
```

## 5. Modals

Use AnimatedModal for forms and confirmations:

```tsx
'use client';

import { useState } from 'react';
import { AnimatedModal } from '@/components/shared/AnimatedModal';

export function MyModal() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button onClick={() => setOpen(true)}>Edit</button>

      <AnimatedModal
        isOpen={open}
        onClose={() => setOpen(false)}
        title="Edit Session"
        footer={
          <div style={{ display: 'flex', gap: '12px' }}>
            <button className="button button-secondary" onClick={() => setOpen(false)}>
              Cancel
            </button>
            <button className="button button-primary" onClick={handleSave}>
              Save
            </button>
          </div>
        }
      >
        <form>{/* form fields */}</form>
      </AnimatedModal>
    </>
  );
}
```

## 6. Enhanced Search

Replace basic search with SearchBar:

```tsx
import { SearchBar } from '@/components/layout/SearchBar';

export function Header() {
  const sessions = ['Session A', 'Session B', 'Session C'];

  return (
    <SearchBar
      placeholder="Search sessions..."
      suggestions={sessions}
      onSearch={(query) => navigateTo(`/search?q=${query}`)}
      onSuggestionSelect={(session) => navigateTo(`/sessions/${session}`)}
    />
  );
}
```

## 7. Animated SealRing

The SealRing now animates on mount:

```tsx
import { SealRing } from '@/components/ui/seal-ring';

// Default - with animation
<SealRing value={85} label="Compliance" />

// Without animation if needed
<SealRing value={85} label="Compliance" animateOnMount={false} />
```

## Common Patterns

### Pattern 1: Data Loading with Skeleton + Toast

```tsx
'use client';

import { useState, useEffect } from 'react';
import { SkeletonLoader } from '@/components/shared/SkeletonLoader';
import { useToast } from '@/components/shared/Toast';

export function DataDisplay() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const { addToast } = useToast();

  useEffect(() => {
    fetchData()
      .then(setData)
      .catch(() => {
        addToast('Failed to load data', 'danger');
      })
      .finally(() => setLoading(false));
  }, []);

  return loading ? (
    <SkeletonLoader type="row" count={3} />
  ) : (
    <DisplayData data={data} />
  );
}
```

### Pattern 2: Form with Modal + Toast

```tsx
'use client';

import { useState } from 'react';
import { AnimatedModal } from '@/components/shared/AnimatedModal';
import { useToast } from '@/components/shared/Toast';

export function EditForm() {
  const [open, setOpen] = useState(false);
  const { addToast } = useToast();

  const handleSubmit = async (formData) => {
    try {
      await saveData(formData);
      addToast('Saved successfully', 'success');
      setOpen(false);
    } catch (error) {
      addToast('Failed to save', 'danger');
    }
  };

  return (
    <>
      <button onClick={() => setOpen(true)}>Edit</button>

      <AnimatedModal
        isOpen={open}
        onClose={() => setOpen(false)}
        title="Edit Record"
      >
        <Form onSubmit={handleSubmit} />
      </AnimatedModal>
    </>
  );
}
```

### Pattern 3: List with Empty State

```tsx
import { EmptyState } from '@/components/shared/EmptyState';

export function SessionList() {
  const { sessions, isLoading } = useSessions();

  if (isLoading) return <SkeletonLoader type="row" count={5} />;

  return sessions.length === 0 ? (
    <EmptyState
      icon="🐄"
      headline="No sessions recorded"
      description="Start your first milking session"
      action={{
        label: 'Start Session',
        onClick: () => router.push('/new-session')
      }}
    />
  ) : (
    <SessionTable sessions={sessions} />
  );
}
```

## Styling & Customization

All components use CSS modules and respect the design system:

```css
/* Design tokens available */
--canvas        /* Background color */
--surface       /* Card/surface color */
--text-primary  /* Main text */
--text-secondary
--accent        /* Primary green */
--warning       /* Orange */
--danger        /* Red */
--border        /* Border color */
```

To customize component styling, add your own CSS or pass `className`:

```tsx
<SkeletonLoader type="row" count={5} className="my-custom-class" />
<EmptyState className="custom-padding" {...props} />
<AnimatedModal className="dark-modal" {...props} />
```

## Keyboard Shortcuts

### Modal
- `Escape` - Close modal
- `Tab` - Navigate focus within modal

### SearchBar
- `↓` / `↑` - Navigate suggestions
- `Enter` - Select or search
- `Escape` - Close suggestions

### Toast
- Click close button or wait for auto-dismiss

## Performance Tips

1. **Skeleton Loaders** - Use for any async data
2. **Lazy Imports** - Components are tree-shakeable
3. **CSS Modules** - Scoped styling, no conflicts
4. **GPU Animation** - All animations use CSS (not JS)

## Accessibility

All components are accessible:
- ✅ Keyboard navigation
- ✅ Screen reader support
- ✅ Focus management
- ✅ Motion preferences respected
- ✅ ARIA labels

No additional setup needed!

## Troubleshooting

### Toast not showing?
- Did you wrap with `<ToastProvider>`?
- Are you calling `addToast()` in a client component?

### Modal not closing?
- Use `onClose` callback to set state
- Modal closes with Escape key automatically

### Skeleton animation not smooth?
- Check `prefers-reduced-motion` setting
- Animation uses CSS (check DevTools)

### Search suggestions not showing?
- Pass `suggestions` array
- Input must match filter logic
- Check that list items are strings

## Examples

More detailed examples in `COMPONENT_USAGE.md`

---

**Version:** 1.0  
**Last Updated:** 2025-07-06  
**Status:** Production Ready ✅
