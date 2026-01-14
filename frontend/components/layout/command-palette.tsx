'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import {
  LayoutDashboard,
  FolderKanban,
  Wrench,
  Terminal,
  Workflow,
  Settings,
  Plus,
  Search,
  Moon,
  Sun,
  LogOut,
} from 'lucide-react';
import { useUIStore } from '@/stores/ui-store';
import { useAuthStore } from '@/stores/auth-store';
import { useTheme } from 'next-themes';

interface CommandItem {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  shortcut?: string;
  action: () => void;
}

export function CommandPalette() {
  const router = useRouter();
  const { commandPaletteOpen, closeCommandPalette } = useUIStore();
  const { logout } = useAuthStore();
  const { theme, setTheme } = useTheme();
  const [search, setSearch] = useState('');

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        useUIStore.getState().toggleCommandPalette();
      }
    };

    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  const runCommand = useCallback(
    (command: () => void) => {
      closeCommandPalette();
      command();
    },
    [closeCommandPalette]
  );

  const navigationItems: CommandItem[] = [
    {
      icon: LayoutDashboard,
      label: 'Dashboard',
      shortcut: 'G D',
      action: () => router.push('/dashboard'),
    },
    {
      icon: FolderKanban,
      label: 'Projects',
      shortcut: 'G P',
      action: () => router.push('/projects'),
    },
    {
      icon: Wrench,
      label: 'Tools',
      shortcut: 'G T',
      action: () => router.push('/tools'),
    },
    {
      icon: Terminal,
      label: 'Jobs',
      shortcut: 'G J',
      action: () => router.push('/jobs'),
    },
    {
      icon: Workflow,
      label: 'Workflows',
      shortcut: 'G W',
      action: () => router.push('/workflows'),
    },
    {
      icon: Settings,
      label: 'Settings',
      shortcut: 'G S',
      action: () => router.push('/settings'),
    },
  ];

  const actionItems: CommandItem[] = [
    {
      icon: Plus,
      label: 'New Project',
      shortcut: '⇧⌘P',
      action: () => router.push('/projects/new'),
    },
    {
      icon: Search,
      label: 'Search...',
      shortcut: '/',
      action: () => router.push('/search'),
    },
    {
      icon: theme === 'dark' ? Sun : Moon,
      label: `Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`,
      shortcut: '⇧⌘D',
      action: () => setTheme(theme === 'dark' ? 'light' : 'dark'),
    },
    {
      icon: LogOut,
      label: 'Log Out',
      action: async () => {
        await logout();
        router.push('/login');
      },
    },
  ];

  return (
    <CommandDialog open={commandPaletteOpen} onOpenChange={closeCommandPalette}>
      <CommandInput
        placeholder="Type a command or search..."
        value={search}
        onValueChange={setSearch}
      />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Navigation">
          {navigationItems.map((item) => (
            <CommandItem
              key={item.label}
              onSelect={() => runCommand(item.action)}
            >
              <item.icon className="mr-2 h-4 w-4" />
              <span>{item.label}</span>
              {item.shortcut && (
                <span className="ml-auto text-xs text-muted-foreground">
                  {item.shortcut}
                </span>
              )}
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Actions">
          {actionItems.map((item) => (
            <CommandItem
              key={item.label}
              onSelect={() => runCommand(item.action)}
            >
              <item.icon className="mr-2 h-4 w-4" />
              <span>{item.label}</span>
              {item.shortcut && (
                <span className="ml-auto text-xs text-muted-foreground">
                  {item.shortcut}
                </span>
              )}
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
