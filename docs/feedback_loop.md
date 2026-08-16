# Feedback Loop

## Current Implementation

The app now supports a production-style feedback loop without requiring a database.

Flow:

1. A user generates content from the Next.js frontend.
2. The response receives a `generationId`.
3. The user can mark the draft as `Approved` or `Needs revision`.
4. The user can add reviewer comments.
5. Feedback is submitted through `POST /api/feedback`.
6. The Next.js route proxies the payload to the Python backend `POST /feedback`.
7. The backend stores each feedback event as one JSON line in:

```txt
feedback/generation_feedback.jsonl
```

Each record includes:

- feedback ID
- generation ID
- status
- reviewer comment
- original request
- generated response
- timestamp

## Regeneration With Feedback

When the user clicks `Regenerate with feedback`, the frontend sends the original request again with:

- `feedback`
- `previousContent`

The Python generation service injects this into the prompt as revision context. This gives the model the previous draft and the reviewer instruction, while still grounding the new draft in the selected brand knowledge base.

## Architecture Boundary

Feedback persistence is isolated behind:

```txt
src/feedback_repository.py
```

Current class:

```txt
FileFeedbackRepository
```

The API uses:

```txt
get_feedback_repository()
```

This keeps the FastAPI route independent from the storage backend.

## To Be: Supabase Migration

For production, replace `FileFeedbackRepository` with a `SupabaseFeedbackRepository` that implements the same `save(record)` method.

Recommended Supabase tables:

```txt
generations
- id
- topic
- content_type
- audience
- language
- tone
- length
- knowledge_base
- content
- metadata jsonb
- created_at

generation_feedback
- id
- generation_id
- status
- comment
- request jsonb
- response jsonb
- reviewer_id nullable
- created_at
```

The frontend and API route should not need to change when moving to Supabase. Only the repository factory should change from file storage to database storage.

## Future Enhancements

- Add reviewer identity when authentication exists.
- Add an approval workflow: draft, in review, needs revision, approved, published.
- Store final edited copy separately from raw AI output.
- Add analytics for common revision reasons.
- Use approved examples as few-shot prompt references.
