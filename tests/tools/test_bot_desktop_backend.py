"""Computer-tab streamer selection: voxl by default, VNC as automatic fallback."""

from tools.bot_desktop.backend import (
    FALLBACK_NOTICE,
    VNC,
    VNC_UNAVAILABLE_NOTICE,
    VOXL,
    VOXL_FAILED_NOTICE,
    VOXL_MISSING_NOTICE,
    configured_backend,
    select_stream_backend,
)


def test_configured_backend_defaults_to_voxl_and_rejects_unknown_values():
    assert configured_backend({}) == VOXL
    assert configured_backend({"screen_backend": "vnc"}) == VNC
    assert configured_backend({"screen_backend": "selkies"}) == VOXL
    assert configured_backend({"screen_backend": "VNC"}) == VNC


def test_user_who_pins_vnc_never_falls_back_to_a_notice():
    backend, notice = select_stream_backend(
        "vnc", voxl_available=True, voxl_running=False, vnc_available=True)
    assert backend == VNC and notice is None


def test_voxl_is_used_when_it_is_up():
    backend, notice = select_stream_backend(
        "voxl", voxl_available=True, voxl_running=True, vnc_available=True)
    assert backend == VOXL and notice is None


def test_missing_voxl_falls_back_to_vnc_with_a_notice():
    backend, notice = select_stream_backend(
        "voxl", voxl_available=False, voxl_running=False, vnc_available=True)
    assert backend == VNC
    assert notice == VOXL_MISSING_NOTICE
    assert "VNC" in notice


def test_failed_voxl_start_falls_back_to_vnc_with_a_failed_notice():
    backend, notice = select_stream_backend(
        "voxl", voxl_available=True, voxl_running=False, vnc_available=True, voxl_failed=True)
    assert backend == VNC
    assert notice == VOXL_FAILED_NOTICE
    assert notice != FALLBACK_NOTICE


def test_vnc_unavailable_when_user_asked_for_vnc_and_voxl_is_also_down():
    backend, notice = select_stream_backend(
        "vnc", voxl_available=False, voxl_running=False, vnc_available=False)
    assert backend == VNC and notice == VNC_UNAVAILABLE_NOTICE
