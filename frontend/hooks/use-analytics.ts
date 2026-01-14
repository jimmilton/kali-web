'use client';

import { useQuery } from '@tanstack/react-query';
import { analyticsApi, AnalyticsDashboard } from '@/lib/api';

export function useAnalytics(params?: { projectId?: string; days?: number }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['analytics', 'dashboard', params?.projectId, params?.days],
    queryFn: () => analyticsApi.getDashboard({
      project_id: params?.projectId,
      days: params?.days,
    }),
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // Refetch every minute
  });

  return {
    analytics: data,
    isLoading,
    error,
    refetch,
  };
}

export function useVulnerabilityStats(projectId?: string) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'vulnerability-stats', projectId],
    queryFn: () => analyticsApi.getVulnerabilityStats(projectId),
    staleTime: 30000,
  });

  return {
    stats: data,
    isLoading,
    error,
  };
}

export function useAssetStats(projectId?: string) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'asset-stats', projectId],
    queryFn: () => analyticsApi.getAssetStats(projectId),
    staleTime: 30000,
  });

  return {
    stats: data,
    isLoading,
    error,
  };
}

export function useJobStats(params?: { projectId?: string; days?: number }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics', 'job-stats', params?.projectId, params?.days],
    queryFn: () => analyticsApi.getJobStats({
      project_id: params?.projectId,
      days: params?.days,
    }),
    staleTime: 30000,
  });

  return {
    stats: data,
    isLoading,
    error,
  };
}
