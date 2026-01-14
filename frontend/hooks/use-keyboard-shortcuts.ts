'use client';

import { useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useUIStore } from '@/stores/ui-store';

// Vim-style "g" followed by letter navigation
const goShortcuts: Record<string, { path: string; description: string }> = {
  d: { path: '/dashboard', description: 'Go to Dashboard' },
  p: { path: '/projects', description: 'Go to Projects' },
  t: { path: '/tools', description: 'Go to Tools' },
  j: { path: '/jobs', description: 'Go to Jobs' },
  w: { path: '/workflows', description: 'Go to Workflows' },
  s: { path: '/settings', description: 'Go to Settings' },
};

export function useKeyboardShortcuts() {
  const router = useRouter();
  const { toggleCommandPalette } = useUIStore();

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Ignore if typing in an input
      const target = event.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      // Command palette (Cmd/Ctrl + K)
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault();
        toggleCommandPalette();
        return;
      }

      // Toggle theme (Cmd/Ctrl + Shift + D)
      if ((event.metaKey || event.ctrlKey) && event.shiftKey && event.key === 'd') {
        event.preventDefault();
        const currentTheme = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
        document.documentElement.classList.toggle('dark', currentTheme === 'light');
        return;
      }

      // Quick search (/)
      if (event.key === '/' && !event.metaKey && !event.ctrlKey) {
        event.preventDefault();
        router.push('/search');
        return;
      }

      // New project (Cmd/Ctrl + Shift + P)
      if ((event.metaKey || event.ctrlKey) && event.shiftKey && event.key === 'p') {
        event.preventDefault();
        router.push('/projects/new');
        return;
      }

      // Escape - close modals/sheets
      if (event.key === 'Escape') {
        // This is handled by individual components
        return;
      }
    },
    [router, toggleCommandPalette]
  );

  useEffect(() => {
    let goPressed = false;
    let goTimeout: NodeJS.Timeout;

    const handleGoShortcuts = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      if (event.key === 'g' && !event.metaKey && !event.ctrlKey) {
        goPressed = true;
        goTimeout = setTimeout(() => {
          goPressed = false;
        }, 1000);
        return;
      }

      if (goPressed && goShortcuts[event.key]) {
        event.preventDefault();
        goPressed = false;
        clearTimeout(goTimeout);
        router.push(goShortcuts[event.key].path);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keydown', handleGoShortcuts);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keydown', handleGoShortcuts);
      clearTimeout(goTimeout);
    };
  }, [handleKeyDown, router]);
}

export function getShortcutsList() {
  return [
    { keys: ['⌘', 'K'], description: 'Open command palette' },
    { keys: ['⌘', '⇧', 'P'], description: 'Create new project' },
    { keys: ['⌘', '⇧', 'D'], description: 'Toggle dark mode' },
    { keys: ['/'], description: 'Quick search' },
    { keys: ['G', 'D'], description: 'Go to Dashboard' },
    { keys: ['G', 'P'], description: 'Go to Projects' },
    { keys: ['G', 'T'], description: 'Go to Tools' },
    { keys: ['G', 'J'], description: 'Go to Jobs' },
    { keys: ['G', 'W'], description: 'Go to Workflows' },
    { keys: ['G', 'S'], description: 'Go to Settings' },
    { keys: ['Esc'], description: 'Close dialogs/sheets' },
  ];
}
