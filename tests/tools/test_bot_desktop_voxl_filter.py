"""Lease-gated voxl client frames: watchers may ack, holders may type."""

from tools.bot_desktop.voxl_filter import VoxlClientFilter, allow_client_binary, allow_client_text


def test_watch_only_commands_pass_without_the_lease():
    assert allow_client_text("a", False)
    assert allow_client_text("kf", False)
    assert allow_client_text("po,1", False)
    assert not allow_client_text("k,a,1", False)
    assert not allow_client_text("c,hello", False)
    assert allow_client_text("k,a,1", True)


def test_binary_frames_are_input_and_dropped_for_watchers():
    assert not allow_client_binary(b"\x00\x01", False)
    assert allow_client_binary(b"\x00\x01", True)
    assert not allow_client_binary(b"", True)


def test_filter_object_returns_none_for_dropped_frames():
    filt = VoxlClientFilter(lambda: False)
    assert filt.text("v") == "v"
    assert filt.text("m,10,10") is None
    assert filt.binary(b"xx") is None
    holder = VoxlClientFilter(lambda: True)
    assert holder.text("m,10,10") == "m,10,10"
    assert holder.binary(b"xx") == b"xx"
