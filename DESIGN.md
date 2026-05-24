# Design System: Rautrex Quant Finance Platform

## 1. Visual Theme & Atmosphere
Rautrex is designed as a high-performance financial analytics platform that balances institutional precision with modern interface clarity. The design system supports a dual-personality approach, ensuring that data density remains readable while providing a premium, tactile experience.

*   **Dark Theme (Bloomberg Terminal x Linear):** A high-contrast, low-fatigue environment for professional traders. It uses a deep obsidian base with vibrant cyan accents to highlight critical data and "active" states. The atmosphere is dense, utilitarian, and focused.
*   **Light Theme (Notion x Carta x Brex):** A clean, paper-like interface that prioritizes readability and structural elegance. It uses soft off-white surfaces and subtle grey borders to create a spacious, professional environment suitable for research and reporting.

## 2. Color Palette & Roles
The system is built entirely on CSS variables. Hardcoded hex values are strictly prohibited in components.

### Light Theme (Notion/Carta/Brex Aesthetic)
*   **Base Background (`--bg-base` / #FAFAF8):** Warm Architectural Off-White. The canvas for the entire application, providing a premium, non-clinical feel.
*   **Surface Background (`--bg-surface` / #FFFFFF):** Pure Paper White. Used for primary content cards and data panels to create elevation against the beige base.
*   **Elevated Background (`--bg-elevated` / #F9F7F4):** Warm Secondary Cream. Used for secondary UI elements like inset sections or secondary metric rows.
*   **Sidebar Background (`--sidebar-bg` / #F5F3EF):** Tactile Warm Beige. Slightly deeper than the base to define the navigation structure.
*   **Navbar Background (`--navbar-bg` / #FDFCFA):** Luminous Warm White. Provides a clean top anchor for the interface.
*   **Default Border (`--border` / #E8E6E0):** Linen Grey. Subtle separation.
*   **Strong Border (`--border-strong` / #D4D0C8):** Concrete Grey. Used for structural definition.

### Dark Theme (Bloomberg/Linear Aesthetic)
*   **Base Background (`--bg-base` / #0A0E1A):** Midnight Navy-Black. Deep, immersive base.
*   **Surface Background (`--bg-surface` / #0D1526):** Deep Sea Blue. Used for the main interactive panels.
*   **Elevated Background (`--bg-elevated` / #111827):** Stealth Grey. For floating elements and secondary layers.
*   **Default Border (`--border` / #1E2A3A):** Cold Iron. Minimalist separation.
*   **Strong Border (`--border-strong` / #2A3A4A):** Gunmetal Blue. Defined borders for inputs and containers.
*   **Primary Text (`--text-primary` / #F0F4F8):** Cloud White. High-readability text on dark backgrounds.
*   **Secondary Text (`--text-secondary` / #8B9BB4):** Steel Blue. For metadata and secondary info.
*   **Muted Text (`--text-muted` / #4A5568):** Charcoal Dusk. For placeholder text and non-essential labels.
*   **Accent Teal (`--accent-teal` / #00D4FF):** Neon Electric Cyan. High-visibility brand color for terminal-like focus.
*   **Positive State (`--positive` / #10B981):** Emerald Glow. Vibrant green for data-heavy gains.
*   **Negative State (`--negative` / #EF4444):** Ruby Pulse. Stark red for immediate attention to losses.
*   **Sidebar Background (`--sidebar-bg` / #080C18):** Slightly darker than the base to create depth and focus on the main workspace.

## 3. Typography Rules
Typography is used to distinguish between interactive UI and quantitative data.
*   **UI Sans (Inter):** Used for all navigation, labels, body text, and general interface elements. Prioritizes legibility at small sizes.
*   **Data Mono (Geist Mono):** Used exclusively for tickers, price values, percentages, timestamps, and any mathematical data. This ensures numbers align vertically in tables and charts.
*   **Scale:** Headers use tight letter-spacing and semi-bold weights, while body text maintains standard tracking for flow.

## 4. Component Stylings
*   **Buttons:**
    *   Primary: Filled with `--accent-teal`, text using `--bg-base` (light) or `--text-primary` (dark).
    *   Ghost/Outline: Using `--border-strong` and `--text-secondary`.
    *   Shape: 6px (`0.375rem`) rounded corners for a modern, slightly technical feel.
*   **Cards & Containers:**
    *   Background: `--bg-surface`.
    *   Border: `1px` solid `--border`.
    *   Elevation: In Light theme, use a whisper-soft diffused shadow (`0 2px 4px rgba(0,0,0,0.02)`). In Dark theme, elevation is defined by color change (`--bg-elevated`) rather than shadows.
*   **Inputs & Forms:**
    *   Stroke: `1px` solid `--border-strong`.
    *   Background: `--bg-base` for subtle depth.
    *   Focus State: Border color shifts to `--accent-teal` with a soft glow ring.

## 5. Layout Principles
*   **Data Density:** Maintain a "Comfortable" density. Use `1.5rem` (24px) for page margins and `1rem` (16px) for internal component spacing.
*   **Grid Alignment:** All analytics panels are snapped to a logical 12-column grid.
*   **Theming Strategy:** Switching between themes is handled by toggling a `.dark` class on the `<html>` or `<body>` element, which swaps the CSS variable values.
