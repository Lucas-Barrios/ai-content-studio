"use client";

import { FolderKanban } from "lucide-react";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { EmptyState } from "@/components/workspace/empty-state";
import { EditableContentCard } from "@/components/workspace/editable-content-card";
import { PageHeader } from "@/components/workspace/page-header";
import { listGeneratedOutputs } from "@/lib/api-client";
import { useWorkspace } from "@/lib/hooks/use-workspace";
import type { GeneratedOutputRecord, HistoryItem } from "@/lib/types";

export default function AssetsPage() {
  const { workspace } = useWorkspace();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [outputs, setOutputs] = useState<GeneratedOutputRecord[]>([]);

  useEffect(() => {
    const raw = window.localStorage.getItem("brand-content-history");
    if (!raw) return;
    try {
      setHistory(JSON.parse(raw) as HistoryItem[]);
    } catch {
      setHistory([]);
    }
  }, []);

  useEffect(() => {
    listGeneratedOutputs(workspace.clientId, workspace.projectId)
      .then((data) => setOutputs(data.outputs))
      .catch(() => setOutputs([]));
  }, [workspace.clientId, workspace.projectId]);

  return (
    <AppShell>
      <div className="mx-auto max-w-7xl space-y-6">
        <PageHeader
          eyebrow="Generated Assets Library"
          title="Review and edit generated content"
          description="Generated assets from the current browser session appear here. The database schema is ready for moving this library to `generated_outputs`."
          icon={FolderKanban}
          badge="Editable cards"
        />
        {outputs.length ? (
          <div className="grid gap-4 xl:grid-cols-2">
            {outputs.map((output) => (
              <EditableContentCard
                key={output.id}
                eyebrow={`${output.content_type}${output.channel ? ` / ${output.channel}` : ""}`}
                title={output.title || "Untitled asset"}
                content={output.content}
                status={output.status}
              />
            ))}
          </div>
        ) : history.length ? (
          <div className="grid gap-4 xl:grid-cols-2">
            {history.map((item) => (
              <EditableContentCard
                key={item.id}
                eyebrow={item.request.contentType}
                title={item.request.topic || "Untitled asset"}
                content={item.response.content}
                status="draft"
              />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={FolderKanban}
            title="No generated assets in this session"
            description="Run the generator, campaign builder, or repurposer to create editable assets. Persisted asset history should come from the generated_outputs API next."
          />
        )}
      </div>
    </AppShell>
  );
}
