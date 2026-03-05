# ruff: noqa: B008

from components.vault_service.main import VaultService
from fastapi import Depends, FastAPI, HTTPException

from .models import (
    DocumentResponse,
    FileListResponse,
    QueryRequest,
    QueryResponse,
    ReindexResponse,
)


def create_app(service: VaultService) -> FastAPI:
    """
    Creates and configures the FastAPI application, registering all routes.
    This function returns the app object but does not run it.

    Args:
        service: The fully initialized VaultService instance.

    Returns:
        The configured FastAPI app instance.
    """
    app = FastAPI(title="Vault API")

    # Dependency provider to make the service available to endpoints
    def get_service() -> VaultService:
        return service

    # Register all API routes
    @app.get(
        "/files",
        response_model=FileListResponse,
        tags=["documents"],
        operation_id="list_files",
    )
    def list_files(svc: VaultService = Depends(get_service)) -> FileListResponse:
        """List all indexed files in the vault.

        Returns absolute file paths of every document currently in the vector
        store index, along with a total count.
        """
        files = svc.list_all_files()
        return FileListResponse(files=files, total_count=len(files))

    @app.get(
        "/document",
        response_model=DocumentResponse,
        tags=["documents"],
        operation_id="get_document",
    )
    def get_document(
        file_path: str, svc: VaultService = Depends(get_service)
    ) -> DocumentResponse:
        """Retrieve the full content of an indexed document.

        Pass the absolute file_path (as returned by list_files or
        search_documents) to get the complete raw text of that document.
        """
        try:
            content = svc.get_document_content(file_path)
            return DocumentResponse(content=content, file_path=file_path)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail="Document not found") from e

    @app.post(
        "/query",
        response_model=QueryResponse,
        tags=["search"],
        operation_id="search_documents",
    )
    async def search(
        request: QueryRequest, svc: VaultService = Depends(get_service)
    ) -> QueryResponse:
        """Semantic search across indexed vault documents.

        Finds the most relevant text chunks for a natural-language query
        using vector similarity. Returns ranked results with source file
        paths, relevance scores, and character offsets for locating the
        match within the original document.

        Use the optional filter parameter to narrow results by folder or
        tags. The folder_prefix filter is especially useful for targeting
        specific areas of the vault (e.g. "System/Rules", "_Private/Transcripts").
        """
        results = await svc.search_chunks(
            request.query, request.limit, where=request.filter
        )
        return QueryResponse(sources=results)

    @app.post(
        "/reindex",
        response_model=ReindexResponse,
        tags=["admin"],
        operation_id="reindex_vault",
    )
    async def reindex(svc: VaultService = Depends(get_service)) -> ReindexResponse:
        """Trigger a re-index of the vault.

        Scans the vault for new, changed, or deleted files and updates the
        vector store accordingly. Only changed files are re-processed.
        """
        result = await svc.reindex_vault()
        return ReindexResponse(**result)

    return app
