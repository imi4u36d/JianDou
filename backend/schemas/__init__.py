"""Pydantic request/response schemas — one module per resource.

Each schema module defines the Pydantic models used for FastAPI
request validation and OpenAPI response documentation.

Submodules
----------
admin       Admin-dashboard DTOs.
auth        Authentication request/response models.
common      Shared pagination, error, and metadata schemas.
credit      Credit-account and transaction DTOs.
generation  Generation-run request/response models.
material    Material-asset DTOs.
task        Task request/response models.
upload      File-upload DTOs.
workflow    Workflow request/response models.
"""
