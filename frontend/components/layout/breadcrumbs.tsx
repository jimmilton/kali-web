'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronRight, Home } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useProjectStore } from '@/stores/project-store';

interface BreadcrumbItem {
  label: string;
  href?: string;
}

const routeLabels: Record<string, string> = {
  dashboard: 'Dashboard',
  projects: 'Projects',
  tools: 'Tools',
  jobs: 'Jobs',
  workflows: 'Workflows',
  settings: 'Settings',
  assets: 'Assets',
  scans: 'Scans',
  vulnerabilities: 'Vulnerabilities',
  credentials: 'Credentials',
  reports: 'Reports',
  new: 'New',
  profile: 'Profile',
  team: 'Team',
  integrations: 'Integrations',
};

export function Breadcrumbs() {
  const pathname = usePathname();
  const { currentProject } = useProjectStore();

  const segments = pathname.split('/').filter(Boolean);

  const breadcrumbs: BreadcrumbItem[] = [];

  let currentPath = '';
  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i];
    currentPath += `/${segment}`;

    // Check if this is a project ID (UUID format)
    if (segments[i - 1] === 'projects' && segment.match(/^[0-9a-f-]{36}$/i)) {
      breadcrumbs.push({
        label: currentProject?.name || 'Project',
        href: currentPath,
      });
    } else if (routeLabels[segment]) {
      breadcrumbs.push({
        label: routeLabels[segment],
        href: i === segments.length - 1 ? undefined : currentPath,
      });
    } else if (!segment.match(/^[0-9a-f-]{36}$/i)) {
      // Skip UUIDs that aren't project IDs
      breadcrumbs.push({
        label: segment.charAt(0).toUpperCase() + segment.slice(1),
        href: i === segments.length - 1 ? undefined : currentPath,
      });
    }
  }

  if (breadcrumbs.length === 0) {
    return null;
  }

  return (
    <nav className="flex items-center space-x-1 text-sm text-muted-foreground">
      <Link
        href="/dashboard"
        className="flex items-center hover:text-foreground transition-colors"
      >
        <Home className="h-4 w-4" />
      </Link>
      {breadcrumbs.map((crumb, index) => (
        <div key={index} className="flex items-center">
          <ChevronRight className="h-4 w-4 mx-1" />
          {crumb.href ? (
            <Link
              href={crumb.href}
              className="hover:text-foreground transition-colors"
            >
              {crumb.label}
            </Link>
          ) : (
            <span className="text-foreground font-medium">{crumb.label}</span>
          )}
        </div>
      ))}
    </nav>
  );
}

interface PageHeaderProps {
  title: string;
  description?: string;
  children?: React.ReactNode;
}

export function PageHeader({ title, description, children }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div>
        <Breadcrumbs />
        <h1 className="mt-2 text-2xl font-bold tracking-tight">{title}</h1>
        {description && (
          <p className="text-muted-foreground">{description}</p>
        )}
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  );
}
