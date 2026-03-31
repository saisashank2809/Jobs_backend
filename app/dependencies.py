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
    import logging
    import importlib
    logger = logging.getLogger(__name__)
    registry = {}
    
    # Load each scraper independently so one failure doesn't break everything
    scrapers_to_load = [
        ("deloitte", "app.scraper.deloitte_adapter", "DeloitteAdapter"),
        ("pwc", "app.scraper.pwc_adapter", "PwCAdapter"),
        ("kpmg", "app.scraper.kpmg_adapter", "KPMGAdapter"),
        ("ey", "app.scraper.ey_adapter", "EYAdapter"),
        ("generic", "app.scraper.generic_adapter", "GenericAdapter"),
    ]
    
    for key, module_path, class_name in scrapers_to_load:
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            registry[key] = cls
        except (ImportError, AttributeError, ModuleNotFoundError) as e:
            logger.warning("Scraper '%s' could not be loaded: %s", key, e)
            
    if not registry:
        logger.error("CRITICAL: No scrapers could be loaded!")
        
    return registry

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
    ai: AIPort = Depends(get_ai_service),
) -> UserService:
    """Injects all ports into user domain service."""
    return UserService(db=db, doc_parser=doc, embeddings=emb, storage=storage, ai=ai)


from app.services.job_service import JobService  # type: ignore


def get_job_service(db: DatabasePort = Depends(get_db)) -> JobService:
    """Injects DB adapter into job service."""
    return JobService(db=db)


from app.services.telegram_channel_service import TelegramChannelService  # type: ignore


def get_telegram_channel_service() -> TelegramChannelService:
    """Injects the Telegram channel broadcast service."""
    return TelegramChannelService()


from app.services.ingestion_service import IngestionService  # type: ignore


def get_ingestion_service(
    db: DatabasePort = Depends(get_db),
    ai: AIPort = Depends(get_ai_service),
    emb: EmbeddingPort = Depends(get_embedding_service),
    telegram: TelegramChannelService = Depends(get_telegram_channel_service),
) -> IngestionService:
    """Injects all ports and TelegramChannelService into IngestionService."""
    return IngestionService(db=db, ai=ai, embeddings=emb, telegram=telegram)
