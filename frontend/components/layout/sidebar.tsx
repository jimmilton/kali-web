'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  FolderKanban,
  Wrench,
  Terminal,
  Workflow,
  FileText,
  Settings,
  ChevronLeft,
  Shield,
  Bug,
  Key,
  Server,
  Network,
  Search,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useUIStore } from '@/stores/ui-store';
import { useProjectStore } from '@/stores/project-store';

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}

const mainNavItems: NavItem[] = [
  { title: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { title: 'Projects', href: '/projects', icon: FolderKanban },
  { title: 'Tools', href: '/tools', icon: Wrench },
  { title: 'Jobs', href: '/jobs', icon: Terminal },
  { title: 'Workflows', href: '/workflows', icon: Workflow },
  { title: 'Search', href: '/search', icon: Search },
];

const projectNavItems: NavItem[] = [
  { title: 'Overview', href: '', icon: LayoutDashboard },
  { title: 'Assets', href: '/assets', icon: Server },
  { title: 'Graph', href: '/graph', icon: Network },
  { title: 'Scans', href: '/scans', icon: Shield },
  { title: 'Vulnerabilities', href: '/vulnerabilities', icon: Bug },
  { title: 'Credentials', href: '/credentials', icon: Key },
  { title: 'Reports', href: '/reports', icon: FileText },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebarCollapsed } = useUIStore();
  const { currentProject } = useProjectStore();

  const isProjectPage = pathname.startsWith('/projects/') && pathname.split('/').length > 2;
  const projectId = isProjectPage ? pathname.split('/')[2] : null;

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 h-screen border-r bg-card transition-all duration-300',
        sidebarCollapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between border-b px-4">
        {!sidebarCollapsed && (
          <Link href="/dashboard" className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-primary" />
            <span className="font-bold">kwebbie</span>
          </Link>
        )}
        {sidebarCollapsed && (
          <Link href="/dashboard" className="mx-auto">
            <Shield className="h-6 w-6 text-primary" />
          </Link>
        )}
        <Button
          variant="ghost"
          size="icon"
          className={cn('h-8 w-8', sidebarCollapsed && 'hidden')}
          onClick={toggleSidebarCollapsed}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 p-2">
        {/* Main Navigation */}
        <div className="mb-2">
          {!sidebarCollapsed && (
            <span className="px-3 text-xs font-semibold uppercase text-muted-foreground">
              Navigation
            </span>
          )}
        </div>
        {mainNavItems.map((item) => (
          <NavLink
            key={item.href}
            item={item}
            isActive={pathname === item.href || pathname.startsWith(item.href + '/')}
            collapsed={sidebarCollapsed}
          />
        ))}

        {/* Project Navigation */}
        {isProjectPage && projectId && (
          <>
            <div className="my-4 border-t" />
            {!sidebarCollapsed && (
              <div className="mb-2">
                <span className="px-3 text-xs font-semibold uppercase text-muted-foreground">
                  {currentProject?.name || 'Project'}
                </span>
              </div>
            )}
            {projectNavItems.map((item) => {
              const href = `/projects/${projectId}${item.href}`;
              const isActive = item.href === ''
                ? pathname === `/projects/${projectId}`
                : pathname.startsWith(href);
              return (
                <NavLink
                  key={item.href || 'overview'}
                  item={{ ...item, href }}
                  isActive={isActive}
                  collapsed={sidebarCollapsed}
                />
              );
            })}
          </>
        )}
      </nav>

      {/* Bottom section */}
      <div className="absolute bottom-0 left-0 right-0 border-t p-2">
        <NavLink
          item={{ title: 'Settings', href: '/settings', icon: Settings }}
          isActive={pathname.startsWith('/settings')}
          collapsed={sidebarCollapsed}
        />
        {sidebarCollapsed && (
          <Button
            variant="ghost"
            size="icon"
            className="mt-2 w-full"
            onClick={toggleSidebarCollapsed}
          >
            <ChevronLeft className="h-4 w-4 rotate-180" />
          </Button>
        )}
      </div>
    </aside>
  );
}

interface NavLinkProps {
  item: NavItem;
  isActive: boolean;
  collapsed: boolean;
}

function NavLink({ item, isActive, collapsed }: NavLinkProps) {
  const Icon = item.icon;

  return (
    <Link
      href={item.href}
      className={cn(
        'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
        isActive
          ? 'bg-primary text-primary-foreground'
          : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
        collapsed && 'justify-center px-2'
      )}
      title={collapsed ? item.title : undefined}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed && (
        <>
          <span className="flex-1">{item.title}</span>
          {item.badge !== undefined && item.badge > 0 && (
            <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-destructive px-1.5 text-xs font-medium text-destructive-foreground">
              {item.badge}
            </span>
          )}
        </>
      )}
    </Link>
  );
}
