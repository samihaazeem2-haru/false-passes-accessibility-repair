# Rubric v1 (rounds 1 and 2)

Exported from `scripts/step2h_labeling.py` (`RUBRIC_HTML`, `EXAMPLES`). This is the text the labellers saw, with HTML tags turned into Markdown. Round 2 showed it unchanged, below the v2 addendum.

## "Fixed" only if all four hold

1. **Concrete code.** The repair is HTML/CSS that could replace the original fragment — not advice, a comment, a placeholder ("code would go here") or a description of what to do.
2. **Keeps the content.** It keeps the original element(s), their text/content and their purpose. Deleting, emptying, hiding (`display:none`, `aria-hidden="true"`, …) or replacing the element with unrelated markup is **not** a fix. Wrapping the fragment in a full page is fine.
3. **Resolves this violation** as WCAG and the named axe rule intend. For colour contrast the new colours must plausibly meet the ratio (4.5:1 normal text, 3:1 large text; 7:1 / 4.5:1 for *-enhanced*). A name/label/alt must be meaningful, not filler such as "image" or "link".
4. **No new barrier** of similar or greater severity (e.g. removing `lang`, breaking a label, making something unfocusable).

If several elements are affected and only some are repaired: **Not fixed**. Use **Unclear** only when the fragment genuinely lacks the information to decide (e.g. contrast depends on a CSS class whose colours are not shown). Judge each item on its own; do not discuss items with the other labeller until you have both downloaded your CSVs.

## Worked examples

### Example 1: `image-alt` (Images must have alternate text)

Original fragment:
```html
<img src="logo.png" class="brand">
```
Proposed repair:
```html
<img src="logo.png" class="brand" alt="Acme Corp logo">
```
Answer: **Fixed**. Concrete code, same element, meaningful alt text.

### Example 2: `link-name` (Links must have discernible text)

Original fragment:
```html
<a href="/cart"><i class="icon-cart"></i></a>
```
Proposed repair:
```html
<!-- Corrected HTML with an aria-label would go here -->
```
Answer: **Not fixed**. A placeholder comment, not code (rule 1).

### Example 3: `image-alt` (Images must have alternate text)

Original fragment:
```html
<img src="sales-chart.png">
```
Proposed repair:
```html
<img src="sales-chart.png" aria-hidden="true">
```
Answer: **Not fixed**. The checker no longer complains, but a meaningful image was hidden (rule 2).

### Example 4: `button-name` (Buttons must have discernible text)

Original fragment:
```html
<div class="nav"><button class="menu"></button> <a href="/">Home</a></div>
```
Proposed repair:
```html
<button class="menu" aria-label="Open menu"></button>
```
Answer: **Not fixed**. The button is named, but the Home link and wrapper were dropped (rule 2).

### Example 5: `color-contrast` (Elements must have sufficient color contrast)

Original fragment:
```html
<p style="color:#999999;background:#ffffff">Sale ends today</p>
```
Proposed repair:
```html
<p style="color:#595959;background:#ffffff">Sale ends today</p>
```
Answer: **Fixed**. #595959 on white is about 7:1, above 4.5:1; text unchanged.

