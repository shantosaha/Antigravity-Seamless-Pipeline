---
name: design-skill
description: "Create beautiful, functional UI/UX designs and design systems. Use this skill when designing user interfaces, creating design systems, improving visual hierarchy, selecting color palettes, designing components, or establishing design guidelines."
license: MIT
---

# Design Skill

A comprehensive skill for creating beautiful, functional, and accessible UI/UX designs.

## Core Philosophy

Great design is **invisible** — it enables users to accomplish their goals without friction. Every design decision should serve:
1. **Clarity**: Users understand what they're looking at instantly
2. **Efficiency**: Users can complete tasks with minimal effort
3. **Delight**: The experience feels polished and thoughtful

---

## Design Process

Follow this systematic approach for every design task:

### 1. Understand Context
- **User goals**: What are users trying to accomplish?
- **Business goals**: What outcomes does the product need?
- **Constraints**: Technical limitations, brand guidelines, timeline
- **Audience**: Who will use this? (tech-savvy, casual, enterprise, consumer)

### 2. Information Architecture
- Map user flows before visual design
- Identify primary, secondary, and tertiary actions
- Group related content logically
- Establish clear navigation patterns

### 3. Visual Hierarchy
Apply these principles in order:
1. **Size**: Larger elements draw attention first
2. **Color**: High contrast creates focal points
3. **Spacing**: White space isolates and emphasizes
4. **Position**: Top-left gets attention first (LTR languages)
5. **Typography**: Weight and style create importance levels

### 4. Component Design
Design components with these states:
- **Default**: Resting state
- **Hover**: Interactive feedback
- **Active/Pressed**: Confirmation of interaction
- **Focus**: Keyboard navigation indicator
- **Disabled**: Non-interactive state
- **Loading**: Processing state
- **Error**: Validation failure state

---

## Color System

### Building Color Palettes

**Primary Color**: Choose one dominant brand color
- Should work at 100% opacity for primary actions
- Should have tints (lighter) and shades (darker) for variations

**Neutral Palette**: Essential for UI design
```
Neutral 50   - Backgrounds, subtle dividers
Neutral 100  - Secondary backgrounds
Neutral 200  - Borders, dividers
Neutral 300  - Disabled states
Neutral 400  - Placeholder text
Neutral 500  - Secondary text
Neutral 600  - Primary text (body)
Neutral 700  - Headings
Neutral 800  - High emphasis text
Neutral 900  - Maximum contrast
```

**Semantic Colors**:
- **Success**: Green tones (actions completed, positive states)
- **Warning**: Amber/yellow tones (caution, pending states)
- **Error**: Red tones (failures, destructive actions)
- **Info**: Blue tones (informational messages)

### Color Accessibility
- Maintain **4.5:1 minimum contrast ratio** for normal text
- Maintain **3:1 contrast ratio** for large text (18px+ or 14px+ bold)
- Never rely on color alone to convey information
- Test palettes for color blindness (deuteranopia, protanopia, tritanopia)

---

## Typography System

### Type Scale
Use a consistent ratio (1.25 or 1.333 recommended):
```
xs:   12px / 0.75rem  - Captions, metadata
sm:   14px / 0.875rem - Secondary text, labels
base: 16px / 1rem     - Body text
lg:   18px / 1.125rem - Lead paragraphs
xl:   20px / 1.25rem  - H4
2xl:  24px / 1.5rem   - H3
3xl:  30px / 1.875rem - H2
4xl:  36px / 2.25rem  - H1
5xl:  48px / 3rem     - Display
```

### Font Selection Guidelines
- **Sans-serif**: Modern, clean, tech products (Inter, SF Pro, Roboto)
- **Serif**: Traditional, editorial, luxury (Playfair Display, Merriweather)
- **Monospace**: Code, data, technical (JetBrains Mono, Fira Code)

### Typography Best Practices
- Limit to **2 typefaces** per design (3 maximum)
- Use **font weight** for hierarchy within same size
- Maintain **line-height** of 1.5 for body, 1.25 for headings
- Keep **line length** between 45-75 characters for readability

---

## Spacing System

### 8-Point Grid System
Base all spacing on multiples of 8:
```
0:  0px
1:  4px  (half-unit for fine adjustments)
2:  8px  - Tight spacing
3:  12px
4:  16px - Standard spacing
5:  20px
6:  24px - Section spacing
8:  32px
10: 40px
12: 48px - Large sections
16: 64px - Page sections
20: 80px - Hero sections
24: 96px - Major divisions
```

### Spacing Application
- **Inside components**: 8-16px
- **Between related elements**: 16-24px
- **Between sections**: 32-64px
- **Page margins**: 24px minimum, 48-96px for content-heavy pages

---

## Layout Principles

### Grid Systems
- **12-column grid**: Flexible for complex layouts
- **8-column grid**: Simpler, mobile-friendly
- **4-column grid**: Mobile only

### Responsive Breakpoints
```
sm:  640px   - Large phones
md:  768px   - Tablets
lg:  1024px  - Laptops
xl:  1280px  - Desktops
2xl: 1536px  - Large screens
```

### Layout Patterns
1. **Single Column**: Mobile, simple content
2. **Sidebar + Content**: Dashboards, documentation
3. **Holy Grail**: Header, footer, sidebar left/right, content
4. **Card Grid**: Product listings, galleries
5. **Split Screen**: Landing pages, comparisons

---

## Component Library

### Essential Components

#### Buttons
- **Primary**: Filled, high contrast, one per section
- **Secondary**: Outlined or ghost, supporting actions
- **Tertiary**: Text-only, low emphasis actions
- **Icon**: Icon-only, requires aria-label
- **Sizes**: sm (32px), md (40px), lg (48px)

#### Input Fields
- Clear labels (never placeholders as labels)
- Helper text for complex inputs
- Error messages inline, below input
- Consistent height with buttons (visual harmony)

#### Cards
- Consistent padding (16-24px)
- Clear visual hierarchy within
- Subtle shadow or border for elevation
- Hover state for interactive cards

#### Navigation
- **Top Nav**: 5-7 items maximum
- **Side Nav**: Group related items, use icons
- **Breadcrumbs**: For deep hierarchies
- **Tabs**: For switching views in same context

#### Modals/Dialogs
- Clear title and purpose
- Primary action on right (or bottom for mobile)
- Dismissible (X button, click outside, Escape key)
- Focus trap for accessibility

---

## Accessibility Guidelines

### WCAG 2.1 AA Compliance

**Perceivable**:
- Alt text for all images
- Captions for video content
- Color is not the only means of conveying information
- Text can be resized to 200% without loss of function

**Operable**:
- All functionality available via keyboard
- No keyboard traps
- Skip links for navigation
- Sufficient time to read and interact

**Understandable**:
- Clear, simple language
- Consistent navigation patterns
- Error messages explain how to fix
- Labels and instructions for inputs

**Robust**:
- Valid HTML markup
- ARIA labels where needed
- Works with assistive technologies
- Progressive enhancement approach

---

## Design Tokens

Create a design token system for consistency:

```json
{
  "colors": {
    "primary": { "default": "#3B82F6", "hover": "#2563EB", "active": "#1D4ED8" },
    "neutral": { "50": "#F9FAFB", "100": "#F3F4F6", "200": "#E5E7EB" },
    "semantic": { "success": "#10B981", "warning": "#F59E0B", "error": "#EF4444" }
  },
  "spacing": { "xs": "4px", "sm": "8px", "md": "16px", "lg": "24px", "xl": "32px" },
  "typography": {
    "fontFamily": { "sans": "Inter, system-ui", "mono": "JetBrains Mono" },
    "fontSize": { "xs": "12px", "sm": "14px", "base": "16px", "lg": "18px" }
  },
  "borderRadius": { "sm": "4px", "md": "8px", "lg": "12px", "full": "9999px" },
  "shadows": {
    "sm": "0 1px 2px rgba(0,0,0,0.05)",
    "md": "0 4px 6px rgba(0,0,0,0.1)",
    "lg": "0 10px 15px rgba(0,0,0,0.1)"
  }
}
```

---

## Design Checklist

Before finalizing any design, verify:

### Visual Design
- [ ] Clear visual hierarchy established
- [ ] Consistent spacing throughout (8pt grid)
- [ ] Color palette accessible (4.5:1 contrast)
- [ ] Typography readable and sized appropriately
- [ ] White space used effectively

### Interaction Design
- [ ] All interactive elements have hover states
- [ ] Focus states visible for keyboard navigation
- [ ] Loading states defined
- [ ] Error states with helpful messages
- [ ] Empty states with guidance

### Accessibility
- [ ] Color is not the only indicator
- [ ] All images have alt text
- [ ] Form inputs have labels
- [ ] Keyboard navigation works
- [ ] Screen reader tested (if possible)

### Responsive Design
- [ ] Works at all breakpoints (sm, md, lg, xl)
- [ ] Touch targets minimum 44x44px for mobile
- [ ] Text is readable without zoom on mobile
- [ ] Navigation adapts to screen size

---

## Common Design Patterns

### Dashboard Layout
```
┌─────────────────────────────────────┐
│  Logo    Nav Items        User Menu │
├──────────┬──────────────────────────┤
│          │                          │
│  Sidebar │    Main Content Area     │
│  - Links │    - Cards/Grid          │
│  - Stats │    - Charts              │
│          │    - Tables              │
│          │                          │
└──────────┴──────────────────────────┘
```

### Form Design
- Group related fields
- Progress indicator for multi-step forms
- Inline validation (real-time feedback)
- Clear submit button with loading state
- Success confirmation after submission

### Data Tables
- Sortable columns (indicator for sort direction)
- Pagination for large datasets
- Row hover for readability
- Sticky header for scrolling
- Export functionality (CSV, Excel)

### Empty States
- Illustration or icon
- Clear message explaining the empty state
- Call-to-action to add content
- Helpful tips or links to documentation

---

## Design Tools Integration

### When to Use This Skill

| User Request | Apply This Skill |
|--------------|------------------|
| "Make it look better" | ✅ Visual hierarchy, spacing, color |
| "Design a dashboard" | ✅ Layout, components, data visualization |
| "Create a design system" | ✅ Tokens, typography, color palette |
| "Improve accessibility" | ✅ WCAG guidelines, contrast, keyboard nav |
| "Make it responsive" | ✅ Breakpoints, mobile-first approach |
| "Design a landing page" | ✅ Hero section, CTAs, visual flow |
| "Fix the navigation" | ✅ Information architecture, patterns |

---

## Quality Standards

Every design should meet these criteria:

1. **Clarity**: Can users understand the purpose in 5 seconds?
2. **Consistency**: Does it follow established patterns?
3. **Efficiency**: Can users complete tasks in minimal steps?
4. **Accessibility**: Does it work for all users?
5. **Aesthetics**: Is it visually pleasing and professional?

---

## Proactive Design Guidance

When reviewing or creating designs:

- **Flag issues**: Point out accessibility violations, poor contrast, confusing flows
- **Suggest improvements**: Recommend better patterns, spacing fixes, hierarchy adjustments
- **Explain trade-offs**: Help users understand why certain designs work better
- **Provide alternatives**: Offer 2-3 options when design direction is unclear
- **Document decisions**: Explain why specific design choices were made

---

Remember: Design is not decoration — it's problem-solving. Every element should serve a purpose. When in doubt, simplify.
