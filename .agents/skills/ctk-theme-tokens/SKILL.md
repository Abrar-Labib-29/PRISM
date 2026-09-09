---
name: ctk-theme-tokens
description: CustomTkinter theme tokens, dual-mode color tuples, and type scale from the iValue PRISM brand system
---

# CustomTkinter Theme Tokens

## Color Architecture (§8.1.2)

All colors are `(light_mode_hex, dark_mode_hex)` tuples for CustomTkinter dual-mode rendering.

### Core Palette
```python
THEME = {
    # Backgrounds
    "bg_canvas":        ("#F1F5F9", "#0B1120"),
    "bg_sidebar":       ("#E2E8F0", "#0F172A"),
    "bg_card_base":     ("#FFFFFF", "#131F37"),
    "bg_card_elevated": ("#F8FAFC", "#1E293B"),
    "bg_input":         ("#FFFFFF", "#0D1527"),
    
    # Borders
    "border_subtle":    ("#CBD5E1", "#1E293B"),
    "border_strong":    ("#94A3B8", "#334155"),
    "border_accent":    ("#0284C7", "#38BDF8"),
    
    # Text
    "text_primary":     ("#0F172A", "#F8FAFC"),
    "text_secondary":   ("#475569", "#94A3B8"),
    "text_muted":       ("#64748B", "#64748B"),
    
    # Brand
    "brand_purple":     ("#4C1D95", "#7C3AED"),
    "brand_accent":     ("#0284C7", "#0EA5E9"),
    "accent_hover":     ("#0369A1", "#38BDF8"),
}
```

### Semantic Status Tokens
```python
STATUS = {
    "success":  ("#059669", "#10B981"),  # HIGH fit, Ollama online
    "warning":  ("#D97706", "#F59E0B"),  # MED fit, warnings
    "error":    ("#DC2626", "#EF4444"),  # LOW fit, offline, errors
    "info":     ("#0284C7", "#38BDF8"),  # Informational toasts
}

# Background tints (10% opacity)
STATUS_BG = {
    "success":  ("#0596691A", "#0596691A"),
    "warning":  ("#D977061A", "#D977061A"),
    "error":    ("#DC26261A", "#DC26261A"),
    "info":     ("#0284C71A", "#0284C71A"),
}
```

## Typography System (§8.1.3)

```python
# Font families
FONT_PRIMARY = "Segoe UI"
FONT_MONO = "Cascadia Mono"

# Type scale: (family, size_pt, weight)
TYPE_SCALE = {
    "display":      (FONT_PRIMARY, 24, "bold"),
    "h1":           (FONT_PRIMARY, 18, "bold"),
    "h2":           (FONT_PRIMARY, 15, "bold"),      # semi-bold unavailable, use bold
    "h3":           (FONT_PRIMARY, 13, "bold"),
    "body_large":   (FONT_PRIMARY, 12, "normal"),
    "body_regular": (FONT_PRIMARY, 11, "normal"),
    "body_small":   (FONT_PRIMARY, 10, "normal"),
    "caption":      (FONT_PRIMARY, 9,  "normal"),
    "overline":     (FONT_PRIMARY, 9,  "bold"),      # 8.5pt rounds to 9
    "mono":         (FONT_MONO,    11, "normal"),
}
```

> **Note:** CustomTkinter does not support CSS font-weight values (500/600). Map Semi-Bold (600) → `"bold"` and Medium (500) → `"normal"` for CTkFont.

## Spacing Scale (§8.1.4)

```python
SPACING = {
    "xs":   4,   # icon-label gap, chip inner margin
    "sm":   8,   # button padding, tag chip gap, border radii
    "md":   12,  # card vertical gap, form field margins
    "lg":   16,  # card internal padding, button horizontal padding
    "xl":   24,  # main content outer padding, sidebar section spacing
    "2xl":  32,  # major section gap
    "3xl":  48,  # splash screen margins
}
```

## Layout Constants (§8.1.4, §8.1.6)

```python
LAYOUT = {
    "sidebar_width":      280,
    "min_width":          1024,
    "min_height":         640,
    "default_width":      1280,
    "default_height":     820,
    "max_content_width":  1180,
    "card_radius":        12,
    "input_radius":       8,
    "button_height_sm":   32,
    "button_height_md":   36,
    "button_height_lg":   42,
}
```

## Usage in CustomTkinter Widgets

### Applying Colors
```python
import customtkinter

# Buttons use dual-mode tuples directly
btn = customtkinter.CTkButton(
    parent,
    fg_color=THEME["brand_accent"],
    hover_color=THEME["accent_hover"],
    text_color=("#040814", "#040814"),  # dark text on accent
    font=customtkinter.CTkFont(*TYPE_SCALE["h3"]),
    height=LAYOUT["button_height_lg"],
    corner_radius=LAYOUT["input_radius"],
)

# Cards
card = customtkinter.CTkFrame(
    parent,
    fg_color=THEME["bg_card_base"],
    border_color=THEME["border_subtle"],
    border_width=1,
    corner_radius=LAYOUT["card_radius"],
)
```

### Theme Switching (§8.1.13)
```python
# Located at bottom of sidebar
theme_switcher = customtkinter.CTkSegmentedButton(
    sidebar, values=["Dark", "Light", "System"],
    command=lambda v: customtkinter.set_appearance_mode(v.lower())
)
# Persists choice to config.json
```

## WCAG 2.1 AA Contrast Verification (§8.1.2)

| Combination | Ratio | Result |
|---|---|---|
| text_primary on bg_card_base (Dark) | 14.2:1 | ✅ AAA |
| text_primary on bg_card_base (Light) | 16.1:1 | ✅ AAA |
| text_secondary on bg_card_base (Dark) | 5.8:1 | ✅ AA |
| brand_accent button text (Dark) | 8.4:1 | ✅ AAA |

## Micro-Interactions (§8.1.10)

```python
# Button press scale effect (skip if reduced-motion)
def animate_press(widget, reduced_motion=False):
    if reduced_motion:
        return
    # Scale to 97% for 80ms then restore
    original_width = widget.winfo_width()
    widget.configure(width=int(original_width * 0.97))
    widget.after(80, lambda: widget.configure(width=original_width))
```

> Always check `check_reduced_motion()` from `system_info.py` before applying animations.
