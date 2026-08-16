"""
FastAPI backend for the Next.js frontend.

Run locally:
  uvicorn api_server:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

from collections.abc import AsyncIterator
import logging
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from src.api_helpers import (
    build_chat_prompt,
    feedback_record_to_response,
    normalize_content_type,
    safe_download_filename,
    sources_to_dicts,
    uploaded_files_to_dicts,
    validate_choice,
)
from src.campaign_service import (
    CampaignRepository,
    CampaignRequest,
    generate_campaign,
    regenerate_asset,
)
from src.repurpose_service import (
    RepurposeRepository,
    RepurposeRequest as RepurposeServiceRequest,
    repurpose_content,
    regenerate_output as regenerate_repurpose_output,
)
from src.repurpose_prompt_templates import VALID_FORMATS as VALID_REPURPOSE_FORMATS
from src.brand_intelligence import (
    BrandConsistencyScore,
    SupabaseBrandRepository,
    assemble_brand_block,
    build_brand_profile_payload,
    retrieve_brand_context,
    score_brand_consistency,
)
from src.content_artifacts import compare_uniqueness, make_docx_bytes
from src.generation_service import (
    GenerateContentRequest,
    UploadedFileRef,
    generate_content,
    save_uploads,
)
from src.feedback_repository import FeedbackRecord, get_feedback_repository
from src.logging_config import configure_logging
from src.llm_integration import ContentGenerator, ContentGeneratorError
from src.rag_ingestion import (
    SUPPORTED_MIME_TYPES,
    KnowledgeSourceInput,
    RagIngestionError,
    RagIngestionService,
    search_knowledge_chunks,
)
from src.security import (
    InMemoryRateLimiter,
    client_ip,
    get_security_settings,
    require_backend_api_key,
    validate_allowed_mime,
    validate_content_length,
    validate_text_length,
    validate_upload_bytes,
    validate_upload_count,
    validate_uuid,
)
from src.supabase_client import SupabaseConfigurationError, get_supabase_admin_client

load_dotenv()
configure_logging()
logger = logging.getLogger(__name__)
security_settings = get_security_settings()
rate_limiter = InMemoryRateLimiter(
    max_requests=security_settings.rate_limit_requests,
    window_seconds=security_settings.rate_limit_window_seconds,
)

app = FastAPI(title="AI Content Studio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=security_settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    try:
        validate_content_length(request, security_settings)
        require_backend_api_key(request, security_settings)
        rate_limiter.check(client_ip(request))
    except HTTPException as error:
        return JSONResponse(status_code=error.status_code, content={"detail": error.detail})
    return await call_next(request)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled API error path=%s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Unexpected backend error. Check server logs with the request timestamp."})


class UploadedFileBody(BaseModel):
    id: str
    name: str
    size: int
    contentType: str
    url: Optional[str] = None


class GenerateBody(BaseModel):
    content_type: Optional[str] = Field(default=None, alias="contentType")
    topic: str = Field(min_length=2, max_length=500)
    audience: str = Field(default="Target Audience", max_length=200)
    language: str = "english"
    tone: str = Field(default="Professional", max_length=80)
    length: str = "Medium"
    knowledge_base: str = Field(default="hybrid", alias="knowledgeBase")
    files: list[UploadedFileBody] = Field(default_factory=list)
    feedback: str = Field(default="", max_length=4_000)
    previousContent: str = Field(default="", max_length=30_000)
    brand_profile_id: Optional[str] = Field(default=None, alias="brandProfileId")


class FeedbackBody(BaseModel):
    generationId: str
    status: str
    comment: str = ""
    request: dict[str, Any] = Field(default_factory=dict)
    response: dict[str, Any] = Field(default_factory=dict)


class ContentArtifactBody(BaseModel):
    content: str = Field(min_length=1, max_length=80_000)
    topic: str = Field(default="Content", max_length=200)


class ChatMessage(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=8_000)


class ChatBody(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list, max_length=12)


class LlmGenerateBody(BaseModel):
    system: str = Field(default="", max_length=20_000)
    prompt: str = Field(min_length=1, max_length=80_000)


class GeneratedOutputCreateBody(BaseModel):
    organization_id: str = Field(alias="organizationId")
    client_id: str = Field(alias="clientId")
    project_id: str = Field(alias="projectId")
    title: Optional[str] = Field(default=None, max_length=240)
    prompt: Optional[str] = Field(default=None, max_length=120_000)
    content: str = Field(min_length=1, max_length=120_000)
    content_type: str = Field(alias="contentType")
    channel: Optional[str] = None
    language: str = "english"
    status: str = "draft"
    model: Optional[str] = None
    word_count: Optional[int] = Field(default=None, alias="wordCount")
    retrieved_chunk_ids: list[str] = Field(default_factory=list, alias="retrievedChunkIds")
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


VALID_SOURCE_TYPES = {"blog_post", "transcript", "webinar_notes", "article", "social_post", "document", "other"}


class RepurposeBody(BaseModel):
    organization_id: str = Field(alias="organizationId")
    client_id: str = Field(alias="clientId")
    project_id: str = Field(alias="projectId")
    source_text: str = Field(alias="sourceText", min_length=20, max_length=80_000)
    source_title: str = Field(default="", alias="sourceTitle", max_length=200)
    source_type: str = Field(default="article", alias="sourceType")
    target_formats: list[str] = Field(alias="targetFormats", min_length=1, max_length=7)
    language: str = "english"
    preserve_tone: bool = Field(default=True, alias="preserveTone")
    brand_profile_id: Optional[str] = Field(default=None, alias="brandProfileId")
    created_by: Optional[str] = Field(default=None, alias="createdBy")

    model_config = {"populate_by_name": True}


class RepurposeRegenerateBody(BaseModel):
    format: str
    extraction_raw: dict[str, Any] = Field(alias="extractionRaw")
    language: str = "english"
    brand_profile_id: Optional[str] = Field(default=None, alias="brandProfileId")

    model_config = {"populate_by_name": True}


VALID_CAMPAIGN_CHANNELS = {"linkedin", "instagram", "email", "blog", "ads"}
VALID_CAMPAIGN_TONES = {"Academic", "Formal", "Professional", "Friendly", "Conversational"}


class CampaignGenerateBody(BaseModel):
    organization_id: str = Field(alias="organizationId")
    client_id: str = Field(alias="clientId")
    project_id: str = Field(alias="projectId")
    goal: str = Field(min_length=3, max_length=700)
    offer: str = Field(max_length=500)
    audience: str = Field(max_length=300)
    channels: list[str] = Field(min_length=1, max_length=5)
    start_date: str = Field(alias="startDate", max_length=40)
    end_date: str = Field(alias="endDate", max_length=40)
    language: str = "english"
    tone: str = "Professional"
    kb_source: str = Field(default="hybrid", alias="kbSource")
    brand_profile_id: Optional[str] = Field(default=None, alias="brandProfileId")
    created_by: Optional[str] = Field(default=None, alias="createdBy")
    extra_context: str = Field(default="", alias="extraContext", max_length=8_000)

    model_config = {"populate_by_name": True}


class CampaignAssetRegenerateBody(BaseModel):
    channel: str
    concept_raw: dict[str, Any] = Field(alias="conceptRaw")
    language: str = "english"
    brand_profile_id: Optional[str] = Field(default=None, alias="brandProfileId")
    extra_context: str = Field(default="", alias="extraContext")

    model_config = {"populate_by_name": True}


class BrandProfileCreateBody(BaseModel):
    organization_id: str = Field(alias="organizationId")
    client_id: str = Field(alias="clientId")
    project_id: Optional[str] = Field(default=None, alias="projectId")
    name: str = "Default Brand Profile"
    positioning: Optional[str] = None
    voice: Optional[str] = None
    tone_guidelines: Optional[str] = Field(default=None, alias="toneGuidelines")
    audience_summary: Optional[str] = Field(default=None, alias="audienceSummary")
    value_proposition: Optional[str] = Field(default=None, alias="valueProposition")
    approved_terms: list[str] = Field(default_factory=list, alias="approvedTerms")
    banned_terms: list[str] = Field(default_factory=list, alias="bannedTerms")
    compliance_notes: Optional[str] = Field(default=None, alias="complianceNotes")
    brand_values: list[str] = Field(default_factory=list, alias="brandValues")
    example_good: list[str] = Field(default_factory=list, alias="exampleGood")
    example_bad: list[str] = Field(default_factory=list, alias="exampleBad")
    is_default: bool = Field(default=False, alias="isDefault")
    created_by: Optional[str] = Field(default=None, alias="createdBy")
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class BrandProfileUpdateBody(BaseModel):
    name: Optional[str] = None
    positioning: Optional[str] = None
    voice: Optional[str] = None
    tone_guidelines: Optional[str] = Field(default=None, alias="toneGuidelines")
    audience_summary: Optional[str] = Field(default=None, alias="audienceSummary")
    value_proposition: Optional[str] = Field(default=None, alias="valueProposition")
    approved_terms: Optional[list[str]] = Field(default=None, alias="approvedTerms")
    banned_terms: Optional[list[str]] = Field(default=None, alias="bannedTerms")
    compliance_notes: Optional[str] = Field(default=None, alias="complianceNotes")
    brand_values: Optional[list[str]] = Field(default=None, alias="brandValues")
    example_good: Optional[list[str]] = Field(default=None, alias="exampleGood")
    example_bad: Optional[list[str]] = Field(default=None, alias="exampleBad")
    is_default: Optional[bool] = Field(default=None, alias="isDefault")
    metadata: Optional[dict[str, Any]] = None

    model_config = {"populate_by_name": True}


class BrandScoreBody(BaseModel):
    content: str
    brand_profile_id: str = Field(alias="brandProfileId")
    topic: str = ""

    model_config = {"populate_by_name": True}


class KnowledgeTextBody(BaseModel):
    organization_id: str = Field(alias="organizationId")
    client_id: str = Field(alias="clientId")
    project_id: Optional[str] = Field(default=None, alias="projectId")
    title: str = Field(min_length=2, max_length=240)
    text: str = Field(min_length=20, max_length=150_000)
    source_kind: str = Field(default="other", alias="sourceKind")
    content_type: Optional[str] = Field(default=None, alias="contentType")
    language: Optional[str] = None
    channel: Optional[str] = None
    tags: list[str] = Field(default_factory=list, max_length=20)
    metadata: dict[str, Any] = Field(default_factory=dict)
    uploaded_by: Optional[str] = Field(default=None, alias="uploadedBy")


class KnowledgeSearchBody(BaseModel):
    query: str = Field(min_length=2, max_length=2_000)
    client_id: Optional[str] = Field(default=None, alias="clientId")
    project_id: Optional[str] = Field(default=None, alias="projectId")
    content_type: Optional[str] = Field(default=None, alias="contentType")
    language: Optional[str] = None
    channel: Optional[str] = None
    match_count: int = Field(default=8, alias="matchCount", ge=1, le=20)
    match_threshold: float = Field(default=0.72, alias="matchThreshold", ge=0.0, le=1.0)


class BrandProfileBody(BaseModel):
    organization_id: str = Field(alias="organizationId")
    client_id: str = Field(alias="clientId")
    project_id: Optional[str] = Field(default=None, alias="projectId")
    name: str = "Default brand profile"
    positioning: str = ""
    voice: str = ""
    tone_guidelines: str = Field(default="", alias="toneGuidelines")
    audience_summary: str = Field(default="", alias="audienceSummary")
    approved_terms: list[str] = Field(default_factory=list, alias="approvedTerms")
    banned_terms: list[str] = Field(default_factory=list, alias="bannedTerms")
    compliance_notes: str = Field(default="", alias="complianceNotes")
    brand_values: list[str] = Field(default_factory=list, alias="brandValues")


SOURCE_KINDS = {"brand", "product", "audience", "market", "competitor", "campaign", "policy", "other"}
RAG_CONTENT_TYPES = {"blog", "social", "email", "newsletter", "ad", "landing_page", "program", "other"}
CHANNELS = {"website", "linkedin", "instagram", "facebook", "x", "email", "newsletter", "ads", "blog", "other"}


def _request_from_body(body: GenerateBody) -> GenerateContentRequest:
    logger.info("Validating generate request for topic='%s'", body.topic)
    try:
        validate_text_length(body.topic, "topic", max_chars=500, min_chars=2)
        content_type = validate_choice(
            normalize_content_type(body.content_type),
            {"blog", "social", "program", "newsletter"},
            "contentType",
        )
        language = validate_choice(body.language, {"english", "german"}, "language")
        knowledge_base = validate_choice(body.knowledge_base, {"hybrid", "primary", "secondary"}, "knowledgeBase")
        length = validate_choice(body.length, {"Short", "Medium", "Long"}, "length")
    except ValueError as error:
        logger.error("Generate request validation failed: %s", error)
        raise HTTPException(status_code=400, detail=str(error)) from error

    logger.info(
        "Generate request validated: content_type=%s language=%s knowledge_base=%s length=%s",
        content_type,
        language,
        knowledge_base,
        length,
    )
    return GenerateContentRequest(
        contentType=content_type,  # type: ignore[arg-type]
        topic=body.topic,
        audience=body.audience,
        language=language,  # type: ignore[arg-type]
        tone=body.tone,
        length=length,  # type: ignore[arg-type]
        knowledgeBase=knowledge_base,  # type: ignore[arg-type]
        files=[
            UploadedFileRef(
                id=file.id,
                name=file.name,
                size=file.size,
                contentType=file.contentType,
                url=file.url,
            )
            for file in body.files
        ],
        feedback=body.feedback,
        previousContent=body.previousContent,
        brand_profile_id=body.brand_profile_id,
    )


def _normalize_optional_choice(value: str | None, allowed: set[str], field_name: str) -> str | None:
    if value is None or value == "":
        return None
    return validate_choice(value, allowed, field_name)


def _knowledge_source_from_text_body(body: KnowledgeTextBody) -> KnowledgeSourceInput:
    validate_uuid(body.organization_id, "organizationId")
    validate_uuid(body.client_id, "clientId")
    validate_uuid(body.project_id, "projectId", required=False)
    validate_uuid(body.uploaded_by, "uploadedBy", required=False)
    validate_text_length(body.text, "text", max_chars=150_000, min_chars=20)
    return KnowledgeSourceInput(
        organization_id=body.organization_id,
        client_id=body.client_id,
        project_id=body.project_id,
        title=body.title,
        text=body.text,
        source_kind=validate_choice(body.source_kind, SOURCE_KINDS, "sourceKind"),  # type: ignore[arg-type]
        content_type=_normalize_optional_choice(body.content_type, RAG_CONTENT_TYPES, "contentType"),  # type: ignore[arg-type]
        language=body.language,
        channel=_normalize_optional_choice(body.channel, CHANNELS, "channel"),  # type: ignore[arg-type]
        tags=body.tags,
        metadata=body.metadata,
        uploaded_by=body.uploaded_by,
    )


def _ingestion_response(result: Any) -> dict[str, Any]:
    return {
        "documentId": result.document_id,
        "duplicate": result.duplicate,
        "contentHash": result.content_hash,
        "chunkCount": result.chunk_count,
        "embeddingCount": result.embedding_count,
        "status": result.status,
        "message": result.message,
    }


@app.get("/health")
def health() -> dict[str, str]:
    logger.debug("Health check requested")
    return {"status": "ok"}


@app.post("/generate")
def generate(body: GenerateBody) -> dict[str, Any]:
    logger.info("Received /generate request topic='%s'", body.topic)
    try:
        request = _request_from_body(body)
        result = generate_content(request)
        logger.info(
            "Generated content successfully topic='%s' sources=%s content_chars=%s",
            request.topic,
            len(result.sources),
            len(result.content),
        )
        return {
            "content": result.content,
            "sources": sources_to_dicts(result.sources),
            "brief": result.brief,
        }
    except HTTPException:
        raise
    except ContentGeneratorError as error:
        logger.error("Generation API error for topic='%s': %s", body.topic, error)
        raise HTTPException(status_code=502, detail=str(error)) from error
    except (FileNotFoundError, NotADirectoryError, ValueError) as error:
        logger.error("Generation request failed for topic='%s': %s", body.topic, error)
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Unexpected generation error for topic='%s'", body.topic)
        raise HTTPException(status_code=500, detail="Unexpected backend error. Check server logs.") from error


@app.post("/upload")
async def upload(files: list[UploadFile] = File(default=[])) -> dict[str, list[dict[str, Any]]]:
    logger.info("Received /upload request files=%s", len(files))
    validate_upload_count(len(files), security_settings)
    stored_files: list[tuple[str, bytes, str]] = []
    for file in files:
        content = await file.read()
        filename = file.filename or "upload"
        validate_upload_bytes(content, filename, security_settings)
        validate_allowed_mime(file.content_type, filename, SUPPORTED_MIME_TYPES)
        logger.info("Read uploaded file name='%s' bytes=%s type='%s'", file.filename, len(content), file.content_type)
        stored_files.append((filename, content, file.content_type or ""))

    uploaded = save_uploads(stored_files)
    logger.info("Upload request completed files=%s", len(uploaded))
    return {"files": uploaded_files_to_dicts(uploaded)}


@app.post("/knowledge/ingest-text")
def ingest_knowledge_text(body: KnowledgeTextBody) -> dict[str, Any]:
    logger.info("Received /knowledge/ingest-text title='%s' client_id=%s", body.title, body.client_id)
    try:
        source = _knowledge_source_from_text_body(body)
        result = RagIngestionService().ingest(source)
        return _ingestion_response(result)
    except (ValueError, RagIngestionError) as error:
        logger.error("Knowledge text ingestion failed: %s", error)
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Unexpected knowledge text ingestion error")
        raise HTTPException(status_code=500, detail="Unexpected ingestion error. Check server logs.") from error


@app.post("/knowledge/ingest-file")
async def ingest_knowledge_file(
    organization_id: str = Form(alias="organizationId"),
    client_id: str = Form(alias="clientId"),
    project_id: Optional[str] = Form(default=None, alias="projectId"),
    title: str = Form(),
    source_kind: str = Form(default="other", alias="sourceKind"),
    content_type: Optional[str] = Form(default=None, alias="contentType"),
    language: Optional[str] = Form(default=None),
    channel: Optional[str] = Form(default=None),
    tags: str = Form(default=""),
    uploaded_by: Optional[str] = Form(default=None, alias="uploadedBy"),
    file: UploadFile = File(),
) -> dict[str, Any]:
    logger.info("Received /knowledge/ingest-file title='%s' filename='%s' client_id=%s", title, file.filename, client_id)
    try:
        validate_uuid(organization_id, "organizationId")
        validate_uuid(client_id, "clientId")
        validate_uuid(project_id, "projectId", required=False)
        validate_uuid(uploaded_by, "uploadedBy", required=False)
        validate_text_length(title, "title", max_chars=240, min_chars=2)
        file_bytes = await file.read()
        filename = file.filename or "upload"
        validate_upload_bytes(file_bytes, filename, security_settings)
        validate_allowed_mime(file.content_type, filename, SUPPORTED_MIME_TYPES)
        source = KnowledgeSourceInput(
            organization_id=organization_id,
            client_id=client_id,
            project_id=project_id,
            title=title,
            file_bytes=file_bytes,
            filename=filename,
            mime_type=file.content_type,
            source_kind=validate_choice(source_kind, SOURCE_KINDS, "sourceKind"),  # type: ignore[arg-type]
            content_type=_normalize_optional_choice(content_type, RAG_CONTENT_TYPES, "contentType"),  # type: ignore[arg-type]
            language=language,
            channel=_normalize_optional_choice(channel, CHANNELS, "channel"),  # type: ignore[arg-type]
            tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
            uploaded_by=uploaded_by,
        )
        result = RagIngestionService().ingest(source)
        return _ingestion_response(result)
    except (ValueError, RagIngestionError) as error:
        logger.error("Knowledge file ingestion failed: %s", error)
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Unexpected knowledge file ingestion error")
        raise HTTPException(status_code=500, detail="Unexpected ingestion error. Check server logs.") from error


@app.post("/knowledge/search")
def search_knowledge(body: KnowledgeSearchBody) -> dict[str, Any]:
    logger.info("Received /knowledge/search client_id=%s project_id=%s query_chars=%s", body.client_id, body.project_id, len(body.query))
    try:
        validate_uuid(body.client_id, "clientId")
        validate_uuid(body.project_id, "projectId", required=False)
        matches = search_knowledge_chunks(
            query=body.query,
            client_id=body.client_id,
            project_id=body.project_id,
            content_type=_normalize_optional_choice(body.content_type, RAG_CONTENT_TYPES, "contentType"),
            language=body.language,
            channel=_normalize_optional_choice(body.channel, CHANNELS, "channel"),
            match_count=body.match_count,
            match_threshold=body.match_threshold,
        )
        return {"matches": matches, "count": len(matches)}
    except (ValueError, RagIngestionError) as error:
        logger.error("Knowledge search failed: %s", error)
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Unexpected knowledge search error")
        raise HTTPException(status_code=500, detail="Unexpected search error. Check server logs.") from error


@app.get("/brand-profile")
def get_brand_profile(clientId: str, projectId: Optional[str] = None) -> dict[str, Any]:
    logger.info("Received /brand-profile GET client_id=%s project_id=%s", clientId, projectId)
    try:
        validate_uuid(clientId, "clientId")
        validate_uuid(projectId, "projectId", required=False)
        db = get_supabase_admin_client()
        query = db.table("brand_profiles").select("*").eq("client_id", clientId).order("updated_at", desc=True).limit(1)
        if projectId:
            query = query.eq("project_id", projectId)
        profile = query.execute().data
        return {"profile": profile[0] if profile else None}
    except SupabaseConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        logger.exception("Brand profile fetch failed")
        raise HTTPException(status_code=500, detail="Brand profile fetch failed. Check server logs.") from error


@app.post("/brand-profile")
def save_brand_profile(body: BrandProfileBody) -> dict[str, Any]:
    logger.info("Received /brand-profile POST client_id=%s project_id=%s", body.client_id, body.project_id)
    try:
        validate_uuid(body.organization_id, "organizationId")
        validate_uuid(body.client_id, "clientId")
        validate_uuid(body.project_id, "projectId", required=False)
        db = get_supabase_admin_client()
        existing_query = db.table("brand_profiles").select("id").eq("client_id", body.client_id).limit(1)
        if body.project_id:
            existing_query = existing_query.eq("project_id", body.project_id)
        existing = existing_query.execute().data
        payload = {
            "organization_id": body.organization_id,
            "client_id": body.client_id,
            "project_id": body.project_id,
            "name": body.name,
            "positioning": body.positioning,
            "voice": body.voice,
            "tone_guidelines": body.tone_guidelines,
            "audience_summary": body.audience_summary,
            "approved_terms": body.approved_terms,
            "banned_terms": body.banned_terms,
            "compliance_notes": body.compliance_notes,
            "brand_values": body.brand_values,
            "is_default": True,
        }
        if existing:
            profile = db.table("brand_profiles").update(payload).eq("id", existing[0]["id"]).execute().data[0]
        else:
            profile = db.table("brand_profiles").insert(payload).execute().data[0]
        return {"profile": profile}
    except SupabaseConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        logger.exception("Brand profile save failed")
        raise HTTPException(status_code=500, detail="Brand profile save failed. Check server logs.") from error


@app.get("/generated-outputs")
def list_generated_outputs(
    clientId: str,
    projectId: Optional[str] = None,
    limit: int = 50,
) -> dict[str, Any]:
    logger.info("Received /generated-outputs GET client_id=%s project_id=%s", clientId, projectId)
    try:
        validate_uuid(clientId, "clientId")
        validate_uuid(projectId, "projectId", required=False)
        db = get_supabase_admin_client()
        query = (
            db.table("generated_outputs")
            .select("*")
            .eq("client_id", clientId)
            .order("created_at", desc=True)
            .limit(min(max(limit, 1), 100))
        )
        if projectId:
            query = query.eq("project_id", projectId)
        outputs = query.execute().data or []
        return {"outputs": outputs, "count": len(outputs)}
    except SupabaseConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        logger.exception("Generated outputs fetch failed")
        raise HTTPException(status_code=500, detail="Generated outputs fetch failed. Check server logs.") from error


@app.post("/generated-outputs")
def create_generated_output(body: GeneratedOutputCreateBody) -> dict[str, Any]:
    logger.info(
        "Received /generated-outputs POST client_id=%s project_id=%s content_type=%s framework=%s",
        body.client_id,
        body.project_id,
        body.content_type,
        body.metadata.get("framework"),
    )
    try:
        validate_uuid(body.organization_id, "organizationId")
        validate_uuid(body.client_id, "clientId")
        validate_uuid(body.project_id, "projectId")
        for chunk_id in body.retrieved_chunk_ids:
            validate_uuid(chunk_id, "retrievedChunkIds[]")

        payload = {
            "organization_id": body.organization_id,
            "client_id": body.client_id,
            "project_id": body.project_id,
            "title": body.title,
            "prompt": body.prompt,
            "content": body.content,
            "content_type": normalize_content_type(body.content_type),
            "channel": body.channel,
            "language": body.language,
            "status": body.status,
            "model": body.model,
            "word_count": body.word_count or len(body.content.split()),
            "retrieved_chunk_ids": body.retrieved_chunk_ids,
            "metadata": body.metadata,
        }
        db = get_supabase_admin_client()
        response = db.table("generated_outputs").insert(payload).execute()
        row = response.data[0] if response.data else payload
        logger.info("Generated output saved id=%s framework=%s", row.get("id"), body.metadata.get("framework"))
        return {"output": row}
    except HTTPException:
        raise
    except SupabaseConfigurationError as error:
        logger.error("Generated output persistence unavailable: %s", error)
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        logger.exception("Generated output persistence failed client_id=%s", body.client_id)
        raise HTTPException(status_code=500, detail="Generated output persistence failed. Check server logs.") from error


@app.post("/feedback")
def feedback(body: FeedbackBody) -> dict[str, Any]:
    logger.info("Received /feedback request generation_id=%s status=%s", body.generationId, body.status)
    try:
        status = validate_choice(body.status, {"approved", "needs_revision"}, "feedback status")
    except ValueError as error:
        logger.error("Feedback validation failed generation_id=%s: %s", body.generationId, error)
        raise HTTPException(status_code=400, detail=str(error)) from error

    record = FeedbackRecord(
        generation_id=body.generationId,
        status=status,  # type: ignore[arg-type]
        comment=body.comment,
        request=body.request,
        response=body.response,
    )
    saved = get_feedback_repository().save(record)
    logger.info("Feedback saved id=%s generation_id=%s status=%s", saved.id, saved.generation_id, saved.status)
    return feedback_record_to_response(saved)


@app.post("/repurpose")
def repurpose(body: RepurposeBody) -> dict[str, Any]:
    logger.info(
        "Received /repurpose client_id=%s source_type=%s formats=%s chars=%s",
        body.client_id, body.source_type, body.target_formats, len(body.source_text),
    )
    bad = set(body.target_formats) - VALID_REPURPOSE_FORMATS
    if bad:
        raise HTTPException(status_code=400, detail=f"Unknown formats: {bad}. Valid: {sorted(VALID_REPURPOSE_FORMATS)}")
    if body.source_type not in VALID_SOURCE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown source_type '{body.source_type}'.")

    try:
        validate_uuid(body.organization_id, "organizationId")
        validate_uuid(body.client_id, "clientId")
        validate_uuid(body.project_id, "projectId")
        req = RepurposeServiceRequest(
            organization_id=body.organization_id,
            client_id=body.client_id,
            project_id=body.project_id,
            source_text=body.source_text,
            source_title=body.source_title,
            source_type=body.source_type,
            target_formats=body.target_formats,
            language=body.language,
            preserve_tone=body.preserve_tone,
            brand_profile_id=body.brand_profile_id,
            created_by=body.created_by,
        )
        result = repurpose_content(req)
        logger.info(
            "/repurpose complete source_id=%s outputs=%s",
            result.source_id, len(result.outputs),
        )
        return {
            "sourceId": result.source_id,
            "createdAt": result.created_at,
            "extraction": {
                "title": result.extraction.title,
                "coreArgument": result.extraction.core_argument,
                "keyPoints": result.extraction.key_points,
                "facts": result.extraction.facts,
                "quotes": result.extraction.quotes,
                "tone": result.extraction.tone,
                "audienceSignals": result.extraction.audience_signals,
                "oneSentenceSummary": result.extraction.one_sentence_summary,
                "raw": result.extraction.raw,
            },
            "outputs": [
                {
                    "outputId": o.output_id,
                    "format": o.format,
                    "label": o.label,
                    "contentType": o.content_type,
                    "channel": o.channel,
                    "content": o.content,
                    "wordCount": o.word_count,
                    "status": o.status,
                }
                for o in result.outputs
            ],
        }
    except ValueError as error:
        logger.error("Repurpose validation failed: %s", error)
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ContentGeneratorError as error:
        logger.error("Repurpose LLM error: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error
    except Exception as error:
        logger.exception("Repurpose unexpected error")
        raise HTTPException(status_code=500, detail="Unexpected repurpose error. Check server logs.") from error


@app.get("/repurpose/{source_id}")
def get_repurpose_result(source_id: str) -> dict[str, Any]:
    logger.info("Received /repurpose/%s GET", source_id)
    try:
        validate_uuid(source_id, "source_id")
        repo = RepurposeRepository()
        data = repo.get_source_with_outputs(source_id)
        if not data:
            raise HTTPException(status_code=404, detail=f"Repurpose source '{source_id}' not found.")
        return data
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Repurpose fetch failed source_id=%s", source_id)
        raise HTTPException(status_code=500, detail="Fetch failed. Check server logs.") from error


@app.post("/repurpose/{source_id}/outputs/{output_id}/regenerate")
def repurpose_regenerate(
    source_id: str,
    output_id: str,
    body: RepurposeRegenerateBody,
) -> dict[str, Any]:
    logger.info(
        "Received /repurpose/%s/outputs/%s/regenerate format=%s",
        source_id, output_id, body.format,
    )
    if body.format not in VALID_REPURPOSE_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unknown format '{body.format}'.")
    try:
        validate_uuid(source_id, "source_id")
        validate_uuid(output_id, "output_id")
        output = regenerate_repurpose_output(
            source_id=source_id,
            output_id=output_id,
            fmt=body.format,
            extraction_raw=body.extraction_raw,
            language=body.language,
            brand_profile_id=body.brand_profile_id,
        )
        return {
            "outputId": output.output_id,
            "format": output.format,
            "label": output.label,
            "content": output.content,
            "wordCount": output.word_count,
            "status": output.status,
        }
    except ContentGeneratorError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except Exception as error:
        logger.exception("Repurpose regeneration failed output_id=%s", output_id)
        raise HTTPException(status_code=500, detail="Regeneration failed. Check server logs.") from error


@app.post("/repurpose/extract-file")
async def repurpose_extract_file(file: UploadFile = File()) -> dict[str, Any]:
    """Extract plain text from an uploaded PDF, DOCX, TXT, or Markdown file."""
    logger.info("Received /repurpose/extract-file filename='%s'", file.filename)
    try:
        from src.rag_ingestion import extract_text_from_source, KnowledgeSourceInput
        file_bytes = await file.read()
        filename = file.filename or "upload"
        validate_upload_bytes(file_bytes, filename, security_settings)
        validate_allowed_mime(file.content_type, filename, SUPPORTED_MIME_TYPES)
        source = KnowledgeSourceInput(
            organization_id="00000000-0000-0000-0000-000000000000",
            client_id="00000000-0000-0000-0000-000000000000",
            project_id=None,
            title=filename,
            file_bytes=file_bytes,
            filename=filename,
            mime_type=file.content_type,
        )
        text = extract_text_from_source(source)
        return {"text": text, "filename": file.filename, "charCount": len(text)}
    except Exception as error:
        logger.exception("File extraction failed")
        raise HTTPException(status_code=400, detail=f"Could not extract text: {error}") from error


@app.post("/campaigns/generate")
def campaign_generate(body: CampaignGenerateBody) -> dict[str, Any]:
    logger.info(
        "Received /campaigns/generate client_id=%s goal='%s' channels=%s",
        body.client_id, body.goal, body.channels,
    )
    bad_channels = set(body.channels) - VALID_CAMPAIGN_CHANNELS
    if bad_channels:
        raise HTTPException(status_code=400, detail=f"Unknown channels: {bad_channels}. Valid: {VALID_CAMPAIGN_CHANNELS}")

    try:
        validate_uuid(body.organization_id, "organizationId")
        validate_uuid(body.client_id, "clientId")
        validate_uuid(body.project_id, "projectId")
        req = CampaignRequest(
            organization_id=body.organization_id,
            client_id=body.client_id,
            project_id=body.project_id,
            goal=body.goal,
            offer=body.offer,
            audience=body.audience,
            channels=body.channels,
            start_date=body.start_date,
            end_date=body.end_date,
            language=body.language,
            tone=body.tone,
            kb_source=body.kb_source,
            brand_profile_id=body.brand_profile_id,
            created_by=body.created_by,
            extra_context=body.extra_context,
        )
        result = generate_campaign(req)
        logger.info(
            "Campaign generated campaign_id=%s name='%s' assets=%s",
            result.campaign_id, result.concept.name, len(result.assets),
        )
        return {
            "campaignId": result.campaign_id,
            "createdAt": result.created_at,
            "concept": {
                "name": result.concept.name,
                "conceptSummary": result.concept.concept_summary,
                "coreMessage": result.concept.core_message,
                "audienceAngle": result.concept.audience_angle,
                "channelStrategy": result.concept.channel_strategy,
                "contentIdeas": result.concept.raw.get("content_ideas", []),
                "ctaSuggestions": result.concept.cta_suggestions,
                "calendarDraft": result.concept.raw.get("calendar_draft", []),
            },
            "assets": [
                {
                    "assetId": a.asset_id,
                    "campaignItemId": a.campaign_item_id,
                    "channel": a.channel,
                    "label": a.label,
                    "contentType": a.content_type,
                    "content": a.content,
                    "status": a.status,
                }
                for a in result.assets
            ],
        }
    except ValueError as error:
        logger.error("Campaign generate validation failed: %s", error)
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ContentGeneratorError as error:
        logger.error("Campaign generate LLM error: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error
    except Exception as error:
        logger.exception("Campaign generate unexpected error")
        raise HTTPException(status_code=500, detail="Unexpected campaign error. Check server logs.") from error


@app.get("/campaigns")
def list_campaigns(
    clientId: str,
    projectId: Optional[str] = None,
) -> dict[str, Any]:
    logger.info("Received /campaigns GET client_id=%s", clientId)
    try:
        validate_uuid(clientId, "clientId")
        validate_uuid(projectId, "projectId", required=False)
        repo = CampaignRepository()
        campaigns = repo.list_campaigns(clientId, projectId)
        return {"campaigns": campaigns, "count": len(campaigns)}
    except Exception as error:
        logger.exception("Campaign list failed")
        raise HTTPException(status_code=500, detail="Campaign list failed. Check server logs.") from error


@app.get("/campaigns/{campaign_id}")
def get_campaign(campaign_id: str) -> dict[str, Any]:
    logger.info("Received /campaigns/%s GET", campaign_id)
    try:
        validate_uuid(campaign_id, "campaign_id")
        repo = CampaignRepository()
        campaign = repo.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found.")
        assets = repo.get_campaign_assets(campaign_id)
        return {"campaign": campaign, "assets": assets}
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Campaign fetch failed campaign_id=%s", campaign_id)
        raise HTTPException(status_code=500, detail="Campaign fetch failed. Check server logs.") from error


@app.post("/campaigns/{campaign_id}/assets/{asset_id}/regenerate")
def regenerate_campaign_asset(
    campaign_id: str,
    asset_id: str,
    body: CampaignAssetRegenerateBody,
) -> dict[str, Any]:
    logger.info(
        "Received /campaigns/%s/assets/%s/regenerate channel=%s",
        campaign_id, asset_id, body.channel,
    )
    if body.channel not in VALID_CAMPAIGN_CHANNELS:
        raise HTTPException(status_code=400, detail=f"Unknown channel '{body.channel}'.")
    try:
        validate_uuid(campaign_id, "campaign_id")
        validate_uuid(asset_id, "asset_id")
        asset = regenerate_asset(
            campaign_id=campaign_id,
            asset_id=asset_id,
            channel=body.channel,
            concept_raw=body.concept_raw,
            language=body.language,
            brand_profile_id=body.brand_profile_id,
            extra_context=body.extra_context,
        )
        return {
            "assetId": asset.asset_id,
            "channel": asset.channel,
            "label": asset.label,
            "content": asset.content,
            "status": asset.status,
        }
    except ContentGeneratorError as error:
        logger.error("Asset regeneration LLM error: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error
    except Exception as error:
        logger.exception("Asset regeneration failed asset_id=%s", asset_id)
        raise HTTPException(status_code=500, detail="Regeneration failed. Check server logs.") from error


@app.post("/brand/profiles")
def create_brand_profile(body: BrandProfileCreateBody) -> dict[str, Any]:
    logger.info("Received /brand/profiles POST client_id=%s name='%s'", body.client_id, body.name)
    try:
        validate_uuid(body.organization_id, "organizationId")
        validate_uuid(body.client_id, "clientId")
        validate_uuid(body.project_id, "projectId", required=False)
        validate_uuid(body.created_by, "createdBy", required=False)
        repo = SupabaseBrandRepository()
        payload = build_brand_profile_payload(
            organization_id=body.organization_id,
            client_id=body.client_id,
            project_id=body.project_id,
            name=body.name,
            positioning=body.positioning,
            voice=body.voice,
            tone_guidelines=body.tone_guidelines,
            audience_summary=body.audience_summary,
            value_proposition=body.value_proposition,
            approved_terms=body.approved_terms,
            banned_terms=body.banned_terms,
            compliance_notes=body.compliance_notes,
            brand_values=body.brand_values,
            example_good=body.example_good,
            example_bad=body.example_bad,
            is_default=body.is_default,
            created_by=body.created_by,
            metadata=body.metadata,
        )
        row = repo.create_profile(payload)
        logger.info("Brand profile created id=%s", row["id"])
        return row
    except Exception as error:
        logger.exception("Brand profile creation failed")
        raise HTTPException(status_code=500, detail="Brand profile creation failed. Check server logs.") from error


@app.get("/brand/profiles")
def list_brand_profiles(
    clientId: str,
    projectId: Optional[str] = None,
) -> dict[str, Any]:
    logger.info("Received /brand/profiles GET client_id=%s project_id=%s", clientId, projectId)
    try:
        repo = SupabaseBrandRepository()
        profiles = repo.list_profiles(clientId, projectId)
        return {"profiles": profiles, "count": len(profiles)}
    except Exception as error:
        logger.exception("Brand profile list failed")
        raise HTTPException(status_code=500, detail="Brand profile list failed. Check server logs.") from error


@app.get("/brand/profiles/{profile_id}")
def get_brand_profile(profile_id: str) -> dict[str, Any]:
    logger.info("Received /brand/profiles/%s GET", profile_id)
    try:
        validate_uuid(profile_id, "profile_id")
        repo = SupabaseBrandRepository()
        row = repo.get_profile(profile_id)
        if not row:
            raise HTTPException(status_code=404, detail=f"Brand profile '{profile_id}' not found.")
        return row
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Brand profile fetch failed profile_id=%s", profile_id)
        raise HTTPException(status_code=500, detail="Brand profile fetch failed. Check server logs.") from error


@app.put("/brand/profiles/{profile_id}")
def update_brand_profile(profile_id: str, body: BrandProfileUpdateBody) -> dict[str, Any]:
    logger.info("Received /brand/profiles/%s PUT", profile_id)
    try:
        validate_uuid(profile_id, "profile_id")
        repo = SupabaseBrandRepository()
        # Build payload from non-None fields only
        payload: dict[str, Any] = {}
        alias_map = {
            "tone_guidelines": "tone_guidelines",
            "audience_summary": "audience_summary",
            "value_proposition": "value_proposition",
            "approved_terms": "approved_terms",
            "banned_terms": "banned_terms",
            "compliance_notes": "compliance_notes",
            "brand_values": "brand_values",
            "example_good": "example_good",
            "example_bad": "example_bad",
            "is_default": "is_default",
        }
        for attr in ["name", "positioning", "voice", "metadata", *alias_map.keys()]:
            val = getattr(body, attr, None)
            if val is not None:
                payload[attr] = val

        if not payload:
            raise HTTPException(status_code=400, detail="No fields to update.")

        row = repo.update_profile(profile_id, payload)
        logger.info("Brand profile updated id=%s", profile_id)
        return row
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Brand profile update failed profile_id=%s", profile_id)
        raise HTTPException(status_code=500, detail="Brand profile update failed. Check server logs.") from error


@app.post("/brand/score")
def brand_score(body: BrandScoreBody) -> dict[str, Any]:
    logger.info("Received /brand/score request profile_id=%s content_chars=%s", body.brand_profile_id, len(body.content))
    try:
        ctx = retrieve_brand_context(topic=body.topic, profile_id=body.brand_profile_id)
        if ctx is None:
            raise HTTPException(status_code=404, detail=f"Brand profile '{body.brand_profile_id}' not found.")
        score: BrandConsistencyScore = score_brand_consistency(body.content, ctx)
        logger.info(
            "/brand/score completed profile_id=%s overall=%.1f verdict=%s",
            body.brand_profile_id, score.overall_score, score.verdict,
        )
        return {
            "overallScore": score.overall_score,
            "voiceScore": score.voice_score,
            "terminologyScore": score.terminology_score,
            "audienceScore": score.audience_score,
            "violations": score.violations,
            "suggestions": score.suggestions,
            "verdict": score.verdict,
        }
    except HTTPException:
        raise
    except ContentGeneratorError as error:
        logger.error("Brand scoring generation error: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error
    except Exception as error:
        logger.exception("Brand scoring unexpected error")
        raise HTTPException(status_code=500, detail="Unexpected scoring error. Check server logs.") from error


@app.post("/compare")
def compare(body: ContentArtifactBody) -> dict[str, Any]:
    logger.info("Received /compare request topic='%s' content_chars=%s", body.topic, len(body.content))
    comparison = compare_uniqueness(body.content)
    logger.info(
        "Comparison completed topic='%s' unique_terms=%s compared_words=%s",
        body.topic,
        comparison.unique_term_count,
        comparison.compared_word_count,
    )
    return {
        "baseline": comparison.baseline,
        "uniqueTerms": comparison.unique_terms,
        "uniqueTermCount": comparison.unique_term_count,
        "comparedWordCount": comparison.compared_word_count,
    }


@app.post("/export/docx")
def export_docx(body: ContentArtifactBody) -> Response:
    logger.info("Received /export/docx request topic='%s' content_chars=%s", body.topic, len(body.content))
    try:
        docx_bytes = make_docx_bytes(body.content, body.topic)
    except ModuleNotFoundError as error:
        logger.error("DOCX export unavailable: python-docx is not installed")
        raise HTTPException(
            status_code=503,
            detail="DOCX export requires python-docx. Install dependencies with pip install -r requirements.txt.",
        ) from error

    safe_filename = safe_download_filename(body.topic)
    logger.info("DOCX export completed filename=%s.docx bytes=%s", safe_filename, len(docx_bytes))
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}.docx"'},
    )


@app.post("/chat")
def chat(body: ChatBody) -> dict[str, str]:
    logger.info("Received /chat request messages=%s", len(body.messages))
    try:
        generator = ContentGenerator()
        content = generator.generate_content(build_chat_prompt(body.messages))
        logger.info("/chat completed response_chars=%s", len(content))
        return {"content": content}
    except ValueError as error:
        logger.error("Chat validation failed: %s", error)
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ContentGeneratorError as error:
        logger.error("Chat generation failed: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/llm/generate")
def llm_generate(body: LlmGenerateBody) -> dict[str, str]:
    logger.info("Received /llm/generate system_chars=%s prompt_chars=%s", len(body.system), len(body.prompt))
    try:
        generator = ContentGenerator()
        prompt = f"{body.system.strip()}\n\n{body.prompt.strip()}".strip()
        content = generator.generate_content(prompt)
        logger.info("/llm/generate completed response_chars=%s", len(content))
        return {"content": content}
    except ValueError as error:
        logger.error("LLM generation validation failed: %s", error)
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ContentGeneratorError as error:
        logger.error("LLM generation failed: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/chat/stream")
async def chat_stream(body: ChatBody) -> StreamingResponse:
    logger.info("Received /chat/stream request messages=%s", len(body.messages))
    try:
        generator = ContentGenerator()
        content = generator.generate_content(build_chat_prompt(body.messages))
        logger.info("/chat/stream generated response_chars=%s", len(content))
    except ValueError as error:
        logger.error("Chat stream validation failed: %s", error)
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ContentGeneratorError as error:
        logger.error("Chat stream generation failed: %s", error)
        raise HTTPException(status_code=502, detail=str(error)) from error

    async def stream() -> AsyncIterator[str]:
        for token in content.split(" "):
            yield token + " "

    return StreamingResponse(stream(), media_type="text/plain; charset=utf-8")
