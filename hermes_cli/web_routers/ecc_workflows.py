"""Dashboard routes for the ECC workflow pack (marketplace Install / Update / Remove)."""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter

from hermes_cli.web_routers._common import (
    _config_profile_scope,
    http_failure,
    spawn_profile_action,
)
from hermes_cli.web_server_gateway import _ACTION_LOG_FILES

router = APIRouter()


def _ecc_action_name(verb: str) -> str:
    name = f"ecc-workflows-{verb}"
    _ACTION_LOG_FILES.setdefault(name, f"action-{name}.log")
    return name


@router.get("/api/workflows/ecc")
async def ecc_workflow_status(profile: Optional[str] = None):
    """Install-state for the scoped Dragon data folder (no npx)."""

    def _run():
        from hermes_cli.ecc_workflows import read_status

        with _config_profile_scope(profile):
            return read_status().to_dict()

    with http_failure("ECC workflow status failed", 502, "Couldn't read ECC Workflows status"):
        return await asyncio.to_thread(_run)


@router.post("/api/workflows/ecc/install")
async def ecc_workflow_install(profile: Optional[str] = None):
    return spawn_profile_action(
        profile,
        ["ecc", "install"],
        _ecc_action_name("install"),
        log_msg="Failed to spawn ECC workflow install",
        prefix="Failed to install ECC Workflows",
    )


@router.post("/api/workflows/ecc/update")
async def ecc_workflow_update(profile: Optional[str] = None):
    return spawn_profile_action(
        profile,
        ["ecc", "update"],
        _ecc_action_name("update"),
        log_msg="Failed to spawn ECC workflow update",
        prefix="Failed to update ECC Workflows",
    )


@router.post("/api/workflows/ecc/uninstall")
async def ecc_workflow_uninstall(profile: Optional[str] = None):
    return spawn_profile_action(
        profile,
        ["ecc", "remove"],
        _ecc_action_name("uninstall"),
        log_msg="Failed to spawn ECC workflow remove",
        prefix="Failed to remove ECC Workflows",
    )


@router.post("/api/workflows/ecc/remove")
async def ecc_workflow_remove(profile: Optional[str] = None):
    """Alias of uninstall — marketplace copy says Remove."""
    return await ecc_workflow_uninstall(profile=profile)
