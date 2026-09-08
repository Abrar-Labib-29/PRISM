---
name: pyinstaller-splash-bootloader
description: Two-phase PyInstaller splash pattern — C-bootloader static splash + CTk live preloader handoff
---

# PyInstaller Two-Phase Splash Bootloader

## Problem
On 5400 RPM HDDs, PyInstaller's C-bootloader takes 3–8 seconds to decompress and load Python DLLs before the interpreter starts. Users see nothing during this time.

## Solution: Two-Stage Splash Handoff

### Stage 1 — C-Bootloader Static Splash
PyInstaller ≥4.0 supports `--splash` flag. This embeds a static image into the C executable stub, displayed within <1–2 seconds.

**Build command (include this flag):**
```powershell
pyinstaller --splash "assets/branding/boot_splash.png" main.py
```

**Image requirements:**
- File: `assets/branding/boot_splash.png`
- Size: 420×280px
- Content: Dark background (#0B1120), PRISM logo, "Starting iValue PRISM..." text

### Stage 2 — CTk Preloader Handoff
Once Python initializes, `main.py` must close the C-bootloader splash before mounting the CTk splash:

```python
# At the top of main.py, BEFORE creating any Tkinter window:
try:
    import pyi_splash
    pyi_splash.update_text("Initializing PRISM Core Engine...")
    pyi_splash.close()
except ImportError:
    pass  # Not running in packaged PyInstaller environment (dev mode)
```

### Stage 2 — CTk SplashPreloader
After `pyi_splash.close()`, mount `SplashPreloader(customtkinter.CTkToplevel)`:
- 480×340px borderless window, centered, background `#0B1120`
- 96×96px logo, title, subtitle, progress bar
- 4-step initialization checklist updated via `update_step(step, label, elapsed)`
- After all 4 steps green: 300ms cross-fade → destroy → launch main app

### Sequence Diagram
```
User clicks .exe
  → [0–2s]  C-bootloader renders boot_splash.png
  → [2–8s]  Python runtime loads, DLLs unpacked
  → [~8s]   main.py starts, pyi_splash.close() called
  → [8–30s] SplashPreloader shows live checklist
  → [~30s]  All checks pass → cross-fade → PRISMApp visible
```

### Critical Rules
1. **Never skip `pyi_splash.close()`** — if you don't call it, both splashes are visible simultaneously.
2. **Always wrap in `try/except ImportError`** — `pyi_splash` only exists in packaged builds.
3. **Call `pyi_splash.close()` BEFORE creating any Tkinter root** — the C splash owns the display context.
4. **The boot_splash.png is static** — no animations, no text updates (those happen in CTk phase).
