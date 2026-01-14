import { create } from 'zustand';
import { projectsApi, Project, ProjectStats, CreateProjectInput, PaginatedResponse } from '@/lib/api';

interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  currentProjectStats: ProjectStats | null;
  isLoading: boolean;
  error: string | null;
  pagination: {
    total: number;
    page: number;
    pageSize: number;
    pages: number;
  };

  fetchProjects: (params?: { page?: number; page_size?: number; status?: string }) => Promise<void>;
  fetchProject: (id: string) => Promise<void>;
  fetchProjectStats: (id: string) => Promise<void>;
  createProject: (data: CreateProjectInput) => Promise<Project>;
  updateProject: (id: string, data: Partial<CreateProjectInput>) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  setCurrentProject: (project: Project | null) => void;
  clearError: () => void;
}

export const useProjectStore = create<ProjectState>()((set, get) => ({
  projects: [],
  currentProject: null,
  currentProjectStats: null,
  isLoading: false,
  error: null,
  pagination: {
    total: 0,
    page: 1,
    pageSize: 25,
    pages: 0,
  },

  fetchProjects: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response: PaginatedResponse<Project> = await projectsApi.list(params);
      set({
        projects: response.items,
        pagination: {
          total: response.total,
          page: response.page,
          pageSize: response.page_size,
          pages: response.pages,
        },
        isLoading: false,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch projects';
      set({ error: message, isLoading: false });
    }
  },

  fetchProject: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const project = await projectsApi.get(id);
      set({ currentProject: project, isLoading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch project';
      set({ error: message, isLoading: false });
    }
  },

  fetchProjectStats: async (id: string) => {
    try {
      const stats = await projectsApi.getStats(id);
      set({ currentProjectStats: stats });
    } catch (error) {
      console.error('Failed to fetch project stats:', error);
    }
  },

  createProject: async (data: CreateProjectInput) => {
    set({ isLoading: true, error: null });
    try {
      const project = await projectsApi.create(data);
      set((state) => ({
        projects: [project, ...state.projects],
        isLoading: false,
      }));
      return project;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to create project';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  updateProject: async (id: string, data: Partial<CreateProjectInput>) => {
    set({ isLoading: true, error: null });
    try {
      const project = await projectsApi.update(id, data);
      set((state) => ({
        projects: state.projects.map((p) => (p.id === id ? project : p)),
        currentProject: state.currentProject?.id === id ? project : state.currentProject,
        isLoading: false,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to update project';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  deleteProject: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      await projectsApi.delete(id);
      set((state) => ({
        projects: state.projects.filter((p) => p.id !== id),
        currentProject: state.currentProject?.id === id ? null : state.currentProject,
        isLoading: false,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to delete project';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  setCurrentProject: (project: Project | null) => {
    set({ currentProject: project, currentProjectStats: null });
  },

  clearError: () => set({ error: null }),
}));
