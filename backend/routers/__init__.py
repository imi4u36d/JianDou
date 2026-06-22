"""HTTP API routers — one module per resource.

Each router module exposes a ``router`` attribute (``APIRouter`` instance)
that is registered by the application factory in ``backend.main``.

Submodules
----------
admin              Admin-dashboard endpoints.
auth               Authentication (login, logout, invite, activate).
credits            Credit-balance and consumption endpoints.
generation         AI-generation run endpoints.
health             Health-check and readiness probes.
material_assets    Material-asset management endpoints.
material_center    Material-centre (asset browser) endpoints.
runtime_config     Runtime configuration (model lists, etc.).
tasks              Task CRUD and lifecycle endpoints.
uploads            File-upload endpoints.
workflows          Multi-stage creative workflow endpoints.
"""
