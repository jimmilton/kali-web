'use client';

import { ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick?: () => void;
    href?: string;
  };
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <Card className={cn('border-dashed', className)}>
      <CardContent className="flex flex-col items-center justify-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">{icon}</div>
        <CardTitle className="text-lg mb-2">{title}</CardTitle>
        <CardDescription className="text-center max-w-sm mb-6">
          {description}
        </CardDescription>
        {action && (
          action.href ? (
            <Button asChild>
              <a href={action.href}>{action.label}</a>
            </Button>
          ) : (
            <Button onClick={action.onClick}>{action.label}</Button>
          )
        )}
      </CardContent>
    </Card>
  );
}

interface EmptyStateInlineProps {
  icon: ReactNode;
  message: string;
  className?: string;
}

export function EmptyStateInline({ icon, message, className }: EmptyStateInlineProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-8 text-muted-foreground',
        className
      )}
    >
      <div className="mb-2 text-muted-foreground/50">{icon}</div>
      <p className="text-sm">{message}</p>
    </div>
  );
}
