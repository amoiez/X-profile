// TanStack Query hooks.
"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api, type CreateAnalysisInput, type CreateImportedAnalysisInput } from "./api";

export function useCreateAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateAnalysisInput) => api.createAnalysis(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["analyses"] }),
  });
}

export function useCreateImportedAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateImportedAnalysisInput) => api.createImportedAnalysis(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["analyses"] }),
  });
}

export function useJob(id: string, enabled: boolean) {
  return useQuery({
    queryKey: ["job", id],
    queryFn: () => api.getJob(id),
    enabled,
  });
}

export function useProgress(id: string, enabled: boolean) {
  return useQuery({
    queryKey: ["progress", id],
    queryFn: () => api.getProgress(id),
    enabled,
    // Poll while the job is still running.
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 1500;
    },
  });
}

export function useResults(id: string, enabled: boolean) {
  return useQuery({
    queryKey: ["results", id],
    queryFn: () => api.getResults(id),
    enabled,
    retry: false,
  });
}

export function useHistory(page: number, pageSize = 20) {
  return useQuery({
    queryKey: ["analyses", page, pageSize],
    queryFn: () => api.listAnalyses(page, pageSize),
  });
}

export function useDeleteAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteAnalysis(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["analyses"] }),
  });
}

export function useRefreshAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.refreshAnalysis(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["analyses"] }),
  });
}
