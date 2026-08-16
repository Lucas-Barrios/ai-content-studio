"use client";

import { useState } from "react";
import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ChatPanel } from "@/components/content/chat-panel";
import { HistoryPanel } from "@/components/content/history-panel";
import { InputPanel } from "@/components/content/input-panel";
import { ResultsPanel } from "@/components/content/results-panel";
import { generateContent, submitFeedback, uploadFiles } from "@/lib/api-client";
import { useContentSession } from "@/lib/hooks/use-content-session";
import { useWorkspace } from "@/lib/hooks/use-workspace";
import type { FeedbackStatus } from "@/lib/types";

export function ContentWorkbench() {
  const session = useContentSession();
  const { workspace } = useWorkspace();
  const [isGenerating, setIsGenerating] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const response = await generateContent({
        ...session.request,
        organizationId: workspace.organizationId,
        clientId: workspace.clientId,
        projectId: workspace.projectId
      });
      session.commitResponse(response);
    } catch (nextError) {
      const message = nextError instanceof Error ? nextError.message : "Generation failed.";
      setError(message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSubmitFeedback = async (status: FeedbackStatus, comment: string) => {
    if (!session.response) return;
    await submitFeedback({
      generationId: session.response.metadata.generationId,
      status,
      comment,
      request: session.responseRequest ?? session.request,
      response: session.response
    });
  };

  const handleRegenerateWithFeedback = async (comment: string) => {
    if (!session.response || !comment.trim()) return;

    setIsGenerating(true);
    setError(null);
    try {
      const response = await generateContent({
        ...(session.responseRequest ?? session.request),
        organizationId: workspace.organizationId,
        clientId: workspace.clientId,
        projectId: workspace.projectId,
        feedback: comment,
        previousContent: session.response.content
      });
      session.commitResponse(response);
    } catch (nextError) {
      const message = nextError instanceof Error ? nextError.message : "Regeneration failed.";
      setError(message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleFilesSelected = async (files: File[]) => {
    if (!files.length) return;
    setIsUploading(true);
    setError(null);
    try {
      const uploaded = await uploadFiles(files);
      session.addFiles(uploaded);
    } catch (nextError) {
      const message = nextError instanceof Error ? nextError.message : "File upload failed.";
      setError(message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="mx-auto max-w-[1440px] space-y-5">
      <Card className="overflow-hidden border-primary/15 bg-white shadow-soft">
        <CardContent className="grid gap-4 p-5 lg:grid-cols-[1fr_auto] lg:items-center">
          <div>
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge>AI powered</Badge>
              <Badge variant="outline">Multi channel</Badge>
              <Badge variant="outline">Brand consistency</Badge>
            </div>
            <h2 className="text-balance text-2xl font-semibold tracking-tight md:text-3xl">
              AI Content Studio
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              Choose a content type, add your topic, and the system uses the selected brand&apos;s knowledge-base sources to create
              clear, on-brand marketing content.
            </p>
          </div>
          <div className="flex items-center justify-start lg:justify-end">
            <span className="rounded-md border px-3 py-1.5 text-sm font-semibold tracking-tight text-foreground/80">
              AI Content Studio
            </span>
          </div>
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Action needed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div id="generator" className="grid scroll-mt-24 gap-4 xl:grid-cols-[440px_minmax(0,1fr)] xl:items-start">
        <InputPanel
          request={session.request}
          isLoading={isGenerating || isUploading}
          onChange={session.updateRequest}
          onSubmit={handleGenerate}
          onFilesSelected={handleFilesSelected}
          onFileRemove={session.removeFile}
        />
        <ResultsPanel
          response={session.response}
          isLoading={isGenerating}
          error={error}
          onFeedbackSubmit={handleSubmitFeedback}
          onRegenerateWithFeedback={handleRegenerateWithFeedback}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section id="history" className="scroll-mt-24">
          <HistoryPanel history={session.history} />
        </section>
        <section id="chat" className="scroll-mt-24">
          <ChatPanel />
        </section>
      </div>
    </div>
  );
}
