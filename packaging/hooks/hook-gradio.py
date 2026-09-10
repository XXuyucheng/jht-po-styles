# Gradio reads its own .py sources at runtime (component_meta / blocks_events).
# PyInstaller's default .pyc-in-PYZ collection makes the UI return 500.
module_collection_mode = {
    "gradio": "py",
}
