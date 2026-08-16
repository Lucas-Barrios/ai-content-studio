"use client";

import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FileUpload } from "@/components/content/file-upload";
import {
  audienceOptions,
  contentTypeOptions,
  knowledgeBaseOptions,
  languageOptions,
  lengthOptions,
  toneOptions,
  topicSuggestions
} from "@/lib/constants";
import type { GenerateRequest, KnowledgeBaseSource, Language, Length, UploadedFile } from "@/lib/types";
import { cn } from "@/lib/utils";

interface InputPanelProps {
  request: GenerateRequest;
  isLoading: boolean;
  onChange: <K extends keyof GenerateRequest>(key: K, value: GenerateRequest[K]) => void;
  onSubmit: () => void;
  onFilesSelected: (files: File[]) => void;
  onFileRemove: (id: string) => void;
}

export function InputPanel({
  request,
  isLoading,
  onChange,
  onSubmit,
  onFilesSelected,
  onFileRemove
}: InputPanelProps) {
  const suggestions = topicSuggestions[request.contentType];
  const selectedContentType = contentTypeOptions.find((option) => option.value === request.contentType);

  return (
    <Card className="h-full shadow-soft">
      <CardHeader className="pb-4">
        <CardTitle>Generate content</CardTitle>
        <CardDescription>
          Generate compliant, industry-appropriate content that meets both company and industry standards.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-2">
          <Label>Content type</Label>
          <div className="grid grid-cols-2 gap-2">
            {contentTypeOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => onChange("contentType", option.value)}
                className={cn(
                  "rounded-md border p-3 text-left transition-colors",
                  request.contentType === option.value
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-background hover:bg-muted"
                )}
              >
                <div className="text-sm font-semibold">{option.label}</div>
                <div className={cn("mt-1 text-xs", request.contentType === option.value ? "text-white/78" : "text-muted-foreground")}>
                  {option.description}
                </div>
              </button>
            ))}
          </div>
          {selectedContentType && <p className="text-xs text-muted-foreground">Selected: {selectedContentType.description}</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="topic">Topic or campaign brief</Label>
          <Input
            id="topic"
            value={request.topic}
            placeholder="e.g. Evidence-based investing"
            onChange={(event) => onChange("topic", event.target.value)}
          />
          <div className="grid grid-cols-2 gap-2">
            {suggestions.map((suggestion) => (
              <Button
                key={suggestion}
                type="button"
                variant="outline"
                size="sm"
                className="justify-start overflow-hidden text-ellipsis"
                onClick={() => onChange("topic", suggestion)}
              >
                {suggestion}
              </Button>
            ))}
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div className="space-y-2">
            <Label>Audience</Label>
            <Select value={request.audience} onValueChange={(value) => onChange("audience", value)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {audienceOptions.map((audience) => (
                  <SelectItem key={audience} value={audience}>
                    {audience}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Language</Label>
            <Select value={request.language} onValueChange={(value) => onChange("language", value as Language)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {languageOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <div className="space-y-2">
            <Label>Knowledge base</Label>
            <Select value={request.knowledgeBase} onValueChange={(value) => onChange("knowledgeBase", value as KnowledgeBaseSource)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {knowledgeBaseOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Length</Label>
            <Select value={request.length} onValueChange={(value) => onChange("length", value as Length)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {lengthOptions.map((length) => (
                  <SelectItem key={length} value={length}>
                    {length}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="space-y-2">
          <Label>Tone</Label>
          <div className="flex flex-wrap gap-2">
            {toneOptions.map((tone) => (
              <Button
                key={tone}
                type="button"
                variant={request.tone === tone ? "default" : "outline"}
                size="sm"
                onClick={() => onChange("tone", tone)}
              >
                {tone}
              </Button>
            ))}
          </div>
        </div>

        <FileUpload
          files={(request.files ?? []) as UploadedFile[]}
          onFilesSelected={onFilesSelected}
          onRemove={onFileRemove}
          disabled={isLoading}
        />

        <Button type="button" className="w-full" size="lg" onClick={onSubmit} disabled={isLoading || !request.topic.trim()}>
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {isLoading ? "Generating..." : "Generate with brand context"}
        </Button>
      </CardContent>
    </Card>
  );
}
