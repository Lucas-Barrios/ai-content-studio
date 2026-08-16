"use client";

import { useEffect, useMemo, useState } from "react";
import { defaultRequest } from "@/lib/constants";
import type { GenerateRequest, GenerateResponse, HistoryItem, UploadedFile } from "@/lib/types";

const historyKey = "brand-content-history";

export function useContentSession() {
  const [request, setRequest] = useState<GenerateRequest>(defaultRequest);
  const [response, setResponse] = useState<GenerateResponse | null>(null);
  const [responseRequest, setResponseRequest] = useState<GenerateRequest | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);

  useEffect(() => {
    const raw = window.localStorage.getItem(historyKey);
    if (!raw) return;
    try {
      setHistory(JSON.parse(raw) as HistoryItem[]);
    } catch {
      window.localStorage.removeItem(historyKey);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(historyKey, JSON.stringify(history.slice(0, 10)));
  }, [history]);

  const updateRequest = <K extends keyof GenerateRequest>(key: K, value: GenerateRequest[K]) => {
    setRequest((current) => ({ ...current, [key]: value }));
  };

  const addFiles = (files: UploadedFile[]) => {
    setRequest((current) => ({ ...current, files: [...(current.files ?? []), ...files] }));
  };

  const removeFile = (id: string) => {
    setRequest((current) => ({ ...current, files: (current.files ?? []).filter((file) => file.id !== id) }));
  };

  const commitResponse = (nextResponse: GenerateResponse) => {
    const committedRequest = { ...request };
    setResponse(nextResponse);
    setResponseRequest(committedRequest);
    setHistory((current) => [
      {
        id: crypto.randomUUID(),
        request: committedRequest,
        response: nextResponse
      },
      ...current
    ]);
  };

  const activeSuggestionContext = useMemo(() => request.contentType, [request.contentType]);

  return {
    request,
    response,
    responseRequest,
    history,
    activeSuggestionContext,
    setRequest,
    updateRequest,
    addFiles,
    removeFile,
    commitResponse
  };
}
