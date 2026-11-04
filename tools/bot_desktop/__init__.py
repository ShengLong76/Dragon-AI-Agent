"""Bot Desktop: per-profile headless Xfce desktop, viewed from Dragon AI Desktop.

``runtime`` owns the Xvnc/Xfce process and the published env; ``voxl`` streams H.264 through the
gateway (VNC/RFB is the automatic fallback); ``lease`` owns who may drive the screen (agent vs.
human); ``rfb_filter`` / ``voxl_filter`` are the byte-level input gates the WebSocket bridges apply.
"""
