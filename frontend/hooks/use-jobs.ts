'use client';

import { useState, useCallback, useEffect } from 'react';
import { jobsApi, Job, CreateJobInput, PaginatedResponse, JobOutput } from '@/lib/api';
import { useLiveJobStatus } from './use-socket';

interface UseJobsOptions {
  projectId?: string;
  status?: string;
  page?: number;
  pageSize?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function useJobs(options: UseJobsOptions = {}) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState({
    total: 0,
    page: 1,
    pageSize: 25,
    pages: 0,
  });

  const fetchJobs = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (options.projectId) params.project_id = options.projectId;
      if (options.status) params.status = options.status;
      if (options.page) params.page = String(options.page);
      if (options.pageSize) params.page_size = String(options.pageSize);

      const response: PaginatedResponse<Job> = await jobsApi.list(params);
      setJobs(response.items);
      setPagination({
        total: response.total,
        page: response.page,
        pageSize: response.page_size,
        pages: response.pages,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch jobs');
    } finally {
      setIsLoading(false);
    }
  }, [options.projectId, options.status, options.page, options.pageSize]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  useEffect(() => {
    if (!options.autoRefresh) return;
    const interval = setInterval(fetchJobs, options.refreshInterval || 5000);
    return () => clearInterval(interval);
  }, [options.autoRefresh, options.refreshInterval, fetchJobs]);

  return { jobs, isLoading, error, pagination, refetch: fetchJobs };
}

export function useJob(jobId: string | null) {
  const [job, setJob] = useState<Job | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { status: liveStatus } = useLiveJobStatus(jobId, job?.status);

  const fetchJob = useCallback(async () => {
    if (!jobId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await jobsApi.get(jobId);
      setJob(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch job');
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchJob();
  }, [fetchJob]);

  const jobWithLiveStatus = job
    ? { ...job, status: liveStatus as Job['status'] }
    : null;

  return { job: jobWithLiveStatus, isLoading, error, refetch: fetchJob };
}

export function useJobOutput(jobId: string | null) {
  const [outputs, setOutputs] = useState<JobOutput[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchOutput = useCallback(async () => {
    if (!jobId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await jobsApi.getOutput(jobId);
      setOutputs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch output');
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchOutput();
  }, [fetchOutput]);

  return { outputs, isLoading, error, refetch: fetchOutput };
}

export function useCreateJob() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createJob = useCallback(async (data: CreateJobInput): Promise<Job | null> => {
    setIsLoading(true);
    setError(null);
    try {
      const job = await jobsApi.create(data);
      return job;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create job';
      setError(message);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { createJob, isLoading, error };
}

export function useJobActions(jobId: string) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cancel = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      await jobsApi.cancel(jobId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel job');
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  const retry = useCallback(async (): Promise<Job | null> => {
    setIsLoading(true);
    setError(null);
    try {
      const job = await jobsApi.retry(jobId);
      return job;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retry job');
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  return { cancel, retry, isLoading, error };
}
