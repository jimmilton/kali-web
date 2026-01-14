'use client';

import { useState, useCallback, useEffect } from 'react';
import { useProjectStore } from '@/stores/project-store';
import { projectsApi, Project, CreateProjectInput } from '@/lib/api';

export function useProjects() {
  const {
    projects,
    isLoading,
    error,
    pagination,
    fetchProjects,
    createProject,
    updateProject,
    deleteProject,
    clearError,
  } = useProjectStore();

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  return {
    projects,
    isLoading,
    error,
    pagination,
    refetch: fetchProjects,
    createProject,
    updateProject,
    deleteProject,
    clearError,
  };
}

export function useProject(projectId: string | null) {
  const {
    currentProject,
    currentProjectStats,
    isLoading,
    error,
    fetchProject,
    fetchProjectStats,
    setCurrentProject,
  } = useProjectStore();

  useEffect(() => {
    if (projectId) {
      fetchProject(projectId);
      fetchProjectStats(projectId);
    } else {
      setCurrentProject(null);
    }
  }, [projectId, fetchProject, fetchProjectStats, setCurrentProject]);

  return {
    project: currentProject,
    stats: currentProjectStats,
    isLoading,
    error,
    refetch: () => {
      if (projectId) {
        fetchProject(projectId);
        fetchProjectStats(projectId);
      }
    },
  };
}

export function useProjectMembers(projectId: string) {
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addMember = useCallback(
    async (userId: string, role: string) => {
      setIsLoading(true);
      setError(null);
      try {
        await projectsApi.addMember(projectId, userId, role);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to add member');
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [projectId]
  );

  const removeMember = useCallback(
    async (userId: string) => {
      setIsLoading(true);
      setError(null);
      try {
        await projectsApi.removeMember(projectId, userId);
        setMembers((prev) => prev.filter((m) => m.user_id !== userId));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to remove member');
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [projectId]
  );

  return { members, isLoading, error, addMember, removeMember };
}

interface ProjectMember {
  user_id: string;
  project_id: string;
  role: string;
  user?: {
    id: string;
    username: string;
    email: string;
  };
}

export function useRecentProjects(limit = 5) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchRecent = async () => {
      try {
        const response = await projectsApi.list({ page_size: limit });
        setProjects(response.items);
      } catch {
        // Silently fail for recent projects
      } finally {
        setIsLoading(false);
      }
    };
    fetchRecent();
  }, [limit]);

  return { projects, isLoading };
}

export function useProjectScope(projectId: string | null) {
  const { currentProject, updateProject } = useProjectStore();

  const updateScope = useCallback(
    async (scope: { domains?: string[]; ips?: string[]; exclude?: string[] }) => {
      if (!projectId) return;
      await updateProject(projectId, { scope });
    },
    [projectId, updateProject]
  );

  return {
    scope: currentProject?.scope || { domains: [], ips: [], exclude: [] },
    updateScope,
  };
}
