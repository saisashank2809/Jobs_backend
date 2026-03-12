"""
Dependency Injection container.

Wires abstract ports → concrete adapters. To swap a provider
(e.g., OpenAI → Ollama), change the adapter instantiation here.
Nothing else in the codebase changes  (Open/Closed Principle).
"""

from functools import lru_cache

from fastapi import Depends  # type: ignore
from supabase import create_client  # type: ignore

from app.adapters.document_adapter import DocumentAdapter  # type: ignore
from app.adapters.openai_adapter import OpenAIAdapter  # type: ignore
from app.adapters.openai_embedding import OpenAIEmbeddingAdapter  # type: ignore
from app.adapters.supabase_adapter import SupabaseAdapter  # type: ignore
from app.adapters.supabase_storage_adapter import SupabaseStorageAdapter  # type: ignore
from app.config import settings  # type: ignore
from app.ports.ai_port import AIPort  # type: ignore
from app.ports.database_port import DatabasePort  # type: ignore
from app.ports.document_port import DocumentPort  # type: ignore
from app.ports.embedding_port import EmbeddingPort  # type: ignore
from app.ports.storage_port import StoragePort  # type: ignore


# ── Singletons (cached) ──────────────────────────────────────


@lru_cache(maxsize=1)
def _get_supabase_client():
    # Use service role key — bypasses RLS for server-side operations
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


@lru_cache(maxsize=1)
def _get_openai_adapter() -> OpenAIAdapter:
    return OpenAIAdapter(api_key=settings.openai_api_key)


@lru_cache(maxsize=1)
def _get_embedding_adapter() -> OpenAIEmbeddingAdapter:
    return OpenAIEmbeddingAdapter(api_key=settings.openai_api_key)


@lru_cache(maxsize=1)
def _get_supabase_adapter() -> SupabaseAdapter:
    return SupabaseAdapter(client=_get_supabase_client())


@lru_cache(maxsize=1)
def _get_storage_adapter() -> SupabaseStorageAdapter:
    return SupabaseStorageAdapter(client=_get_supabase_client())


@lru_cache(maxsize=1)
def _get_document_adapter() -> DocumentAdapter:
    return DocumentAdapter()


# ── FastAPI Dependencies (return abstract types) ──────────────


def get_ai_service() -> AIPort:
    """Inject the AI adapter."""
    return _get_openai_adapter()


def get_embedding_service() -> EmbeddingPort:
    """Inject the embedding adapter."""
    return _get_embedding_adapter()


def get_db() -> DatabasePort:
    """Inject the database adapter."""
    return _get_supabase_adapter()


def get_storage() -> StoragePort:
    """Inject the file storage adapter."""
    return _get_storage_adapter()


def get_document_parser() -> DocumentPort:
    """Inject the document text extractor (PDF + DOCX)."""
    return _get_document_adapter()


# ── Scraper Registry ──────────────────────────────────────────

from app.scraper.scraper_port import ScraperPort  # type: ignore # noqa: E402

def _get_registry() -> dict[str, type]:
    try:
        from app.scraper.deloitte_adapter import DeloitteAdapter  # type: ignore
        from app.scraper.pwc_adapter import PwCAdapter  # type: ignore
        from app.scraper.kpmg_adapter import KPMGAdapter  # type: ignore
        from app.scraper.ey_adapter import EYAdapter  # type: ignore
        from app.scraper.generic_adapter import GenericAdapter  # type: ignore
        return {
            "deloitte": DeloitteAdapter,
            "pwc": PwCAdapter,
            "kpmg": KPMGAdapter,
            "ey": EYAdapter,
            "generic": GenericAdapter,
        }
    except ImportError as e:
        import logging
        logging.getLogger(__name__).warning("Scrapers could not be loaded due to import error: %s", e)
        return {}

def get_scraper(source_name: str) -> ScraperPort:
    """Resolve a source name to its scraper adapter instance."""
    registry = _get_registry()
    cls = registry.get(source_name.lower())
    if not cls:
        raise ValueError(
            f"Unknown source or scrapers disabled: {source_name}. "
            f"Available: {', '.join(registry.keys())}"
        )
    return cls()

def get_all_scrapers() -> list[ScraperPort]:
    """Returns a list of all registered scraper instances."""
    registry = _get_registry()
    return [cls() for cls in registry.values()]


# ── Domain Services ───────────────────────────────────────────

from app.services.matching_service import MatchingService  # type: ignore # noqa: E402


def get_matching_service(
    db: DatabasePort = Depends(get_db), ai: AIPort = Depends(get_ai_service)
) -> MatchingService:
    """Injects DB and AI adapters into the matching domain service."""
    return MatchingService(db=db, ai=ai)


from app.services.analytics_service import AnalyticsService  # type: ignore

def get_analytics_service(db: DatabasePort = Depends(get_db)) -> AnalyticsService:
    """Injects DB adapter into analytics service."""
    return AnalyticsService(db=db)


from app.services.user_service import UserService  # type: ignore

def get_user_service(
    db: DatabasePort = Depends(get_db),
    doc: DocumentPort = Depends(get_document_parser),
    emb: EmbeddingPort = Depends(get_embedding_service),
    storage: StoragePort = Depends(get_storage),
) -> UserService:
    """Injects all ports into user domain service."""
    return UserService(db=db, doc_parser=doc, embeddings=emb, storage=storage)
