'use client';

import { useQuery } from '@tanstack/react-query';
import { toolsApi, Tool } from '@/lib/api';

export function useTools(params?: { category?: string }) {
  return useQuery({
    queryKey: ['tools', params],
    queryFn: () => toolsApi.list(params),
  });
}

export function useTool(slug: string) {
  return useQuery({
    queryKey: ['tool', slug],
    queryFn: () => toolsApi.get(slug),
    enabled: !!slug,
  });
}
