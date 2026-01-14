'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workflowsApi, Workflow, CreateWorkflowInput, WorkflowRun } from '@/lib/api';
import { toast } from 'sonner';

export function useWorkflows(params?: { projectId?: string }) {
  return useQuery({
    queryKey: ['workflows', params],
    queryFn: () =>
      workflowsApi.list({
        project_id: params?.projectId,
      }),
  });
}

export function useWorkflow(id: string) {
  return useQuery({
    queryKey: ['workflow', id],
    queryFn: () => workflowsApi.get(id),
    enabled: !!id,
  });
}

export function useWorkflowRuns(workflowId: string) {
  return useQuery({
    queryKey: ['workflow-runs', workflowId],
    queryFn: () => workflowsApi.getRuns(workflowId),
    enabled: !!workflowId,
  });
}

export function useCreateWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateWorkflowInput) => workflowsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      toast.success('Workflow created successfully');
    },
    onError: (error: { detail?: string }) => {
      toast.error(error.detail || 'Failed to create workflow');
    },
  });
}

export function useUpdateWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CreateWorkflowInput> }) =>
      workflowsApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      queryClient.invalidateQueries({ queryKey: ['workflow', id] });
      toast.success('Workflow saved successfully');
    },
    onError: (error: { detail?: string }) => {
      toast.error(error.detail || 'Failed to save workflow');
    },
  });
}

export function useDeleteWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => workflowsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      toast.success('Workflow deleted');
    },
    onError: (error: { detail?: string }) => {
      toast.error(error.detail || 'Failed to delete workflow');
    },
  });
}

export function useRunWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ workflowId, projectId }: { workflowId: string; projectId: string }) =>
      workflowsApi.run(workflowId, projectId),
    onSuccess: (_, { workflowId }) => {
      queryClient.invalidateQueries({ queryKey: ['workflow-runs', workflowId] });
      toast.success('Workflow started');
    },
    onError: (error: { detail?: string }) => {
      toast.error(error.detail || 'Failed to start workflow');
    },
  });
}
