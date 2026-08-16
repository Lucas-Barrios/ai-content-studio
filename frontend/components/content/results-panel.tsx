"use client";

import { CheckCircle2, Copy, Download, FileText, RefreshCw, ThumbsDown } from "lucide-react";
import { useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { downloadMarkdown } from "@/lib/api-client";
import type { FeedbackStatus, GenerateResponse } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

interface ResultsPanelProps {
  response: GenerateResponse | null;
  isLoading: boolean;
  error?: string | null;
  onFeedbackSubmit?: (status: FeedbackStatus, comment: string) => Promise<void>;
  onRegenerateWithFeedback?: (comment: string) => Promise<void>;
}

export function ResultsPanel({
  response,
  isLoading,
  error,
  onFeedbackSubmit,
  onRegenerateWithFeedback
}: ResultsPanelProps) {
  const content = response?.content ?? "";
  const [feedbackStatus, setFeedbackStatus] = useState<FeedbackStatus>("approved");
  const [feedbackComment, setFeedbackComment] = useState("");
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [isSavingFeedback, setIsSavingFeedback] = useState(false);

  const copyContent = async () => {
    if (content) await navigator.clipboard.writeText(content);
  };

  const saveFeedback = async (status: FeedbackStatus) => {
    if (!response || !onFeedbackSubmit) return;
    setIsSavingFeedback(true);
    setFeedbackMessage(null);
    setFeedbackStatus(status);
    try {
      await onFeedbackSubmit(status, feedbackComment);
      setFeedbackMessage(status === "approved" ? "Feedback saved: approved." : "Feedback saved: needs revision.");
    } catch (nextError) {
      const message = nextError instanceof Error ? nextError.message : "Could not save feedback.";
      setFeedbackMessage(message);
    } finally {
      setIsSavingFeedback(false);
    }
  };

  const regenerate = async () => {
    if (!feedbackComment.trim() || !onRegenerateWithFeedback) return;
    await saveFeedback("needs_revision");
    await onRegenerateWithFeedback(feedbackComment);
  };

  return (
    <Card className="min-h-[720px] shadow-soft">
      <CardHeader className="flex flex-row items-start justify-between gap-4 pb-3">
        <div>
          <CardTitle>Output workspace</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">Review generated content, source context, and export-ready copy.</p>
        </div>
        {response && (
          <Badge variant="success">
            {formatNumber(response.metadata.wordCount)} words
          </Badge>
        )}
      </CardHeader>
      <CardContent>
        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertTitle>Generation failed</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <div className="space-y-3 rounded-lg border bg-background p-4">
            <Skeleton className="h-5 w-1/3" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-11/12" />
            <Skeleton className="h-4 w-10/12" />
            <Skeleton className="h-52 w-full" />
          </div>
        ) : (
          <Tabs defaultValue="content" className="w-full">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <TabsList>
                <TabsTrigger value="content">Generated Content</TabsTrigger>
                <TabsTrigger value="sources">Knowledge Base</TabsTrigger>
                <TabsTrigger value="metadata">Summary</TabsTrigger>
              </TabsList>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={copyContent} disabled={!content}>
                  <Copy className="h-4 w-4" />
                  Copy
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!content}
                  onClick={() => downloadMarkdown(content, `content-${response?.metadata.contentType ?? "content"}.md`)}
                >
                  <Download className="h-4 w-4" />
                  Markdown
                </Button>
              </div>
            </div>

            <TabsContent value="content">
              <ScrollArea className="h-[560px] rounded-lg border bg-white">
                <article className="prose prose-neutral max-w-none whitespace-pre-wrap p-5 text-sm leading-7">
                  {content || (
                    <div className="flex h-[500px] flex-col items-center justify-center text-center text-muted-foreground">
                      <FileText className="mb-3 h-8 w-8" />
                      <p className="font-medium text-foreground">No generated content yet</p>
                      <p className="mt-1 max-w-sm text-sm">Complete the input panel and run a generation request.</p>
                    </div>
                  )}
                </article>
              </ScrollArea>

              {response && (
                <div className="mt-4 rounded-lg border bg-muted/30 p-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <p className="text-sm font-semibold">Feedback loop</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Capture reviewer decisions and use comments to regenerate a stronger draft.
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        type="button"
                        variant={feedbackStatus === "approved" ? "default" : "outline"}
                        size="sm"
                        disabled={isSavingFeedback}
                        onClick={() => saveFeedback("approved")}
                      >
                        <CheckCircle2 className="h-4 w-4" />
                        Approve
                      </Button>
                      <Button
                        type="button"
                        variant={feedbackStatus === "needs_revision" ? "default" : "outline"}
                        size="sm"
                        disabled={isSavingFeedback}
                        onClick={() => saveFeedback("needs_revision")}
                      >
                        <ThumbsDown className="h-4 w-4" />
                        Needs revision
                      </Button>
                    </div>
                  </div>
                  <Textarea
                    className="mt-3 min-h-24 bg-white"
                    value={feedbackComment}
                    onChange={(event) => setFeedbackComment(event.target.value)}
                    placeholder="Add reviewer feedback, e.g. make this warmer, add a student proof point, and strengthen the CTA."
                  />
                  <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <p className="text-xs text-muted-foreground">
                      Saved feedback is stored server-side and can be migrated to Supabase later.
                    </p>
                    <Button
                      type="button"
                      size="sm"
                      disabled={!feedbackComment.trim() || isSavingFeedback || isLoading}
                      onClick={regenerate}
                    >
                      <RefreshCw className="h-4 w-4" />
                      Regenerate with feedback
                    </Button>
                  </div>
                  {feedbackMessage && <p className="mt-2 text-sm text-muted-foreground">{feedbackMessage}</p>}
                </div>
              )}
            </TabsContent>

            <TabsContent value="sources">
              <ScrollArea className="h-[560px] rounded-lg border bg-white">
                <div className="space-y-2 p-4">
                  {(response?.sources ?? []).length === 0 ? (
                    <p className="text-sm text-muted-foreground">Source metadata will appear here when returned by the backend.</p>
                  ) : (
                    response?.sources.map((source) => (
                      <div key={`${source.source}-${source.filename}`} className="flex items-center justify-between rounded-md border p-3">
                        <div className="min-w-0">
                          <Badge variant={source.source === "primary" ? "default" : "secondary"}>{source.source}</Badge>
                          <p className="mt-2 truncate text-sm font-medium">{source.filename}</p>
                        </div>
                        <span className="text-sm text-muted-foreground">{formatNumber(source.words)} words</span>
                      </div>
                    ))
                  )}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="metadata">
              <div className="grid gap-3 rounded-lg border bg-white p-4 md:grid-cols-2">
                {response ? (
                  Object.entries(response.metadata).map(([key, value]) => (
                    <div key={key} className="rounded-md bg-muted/45 p-3">
                      <p className="text-xs font-semibold uppercase text-muted-foreground">{key}</p>
                      <p className="mt-1 text-sm font-medium">{String(value)}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">Generation metadata will appear after the first successful response.</p>
                )}
              </div>
            </TabsContent>
          </Tabs>
        )}
      </CardContent>
    </Card>
  );
}
