# Rubric v2 addendum (round 2)

Exported from `scripts/step2h_labeling_r2.py` (`ADDENDUM`, `EXTRA_EXAMPLES`). Round 2 showed this addendum first, then rubric v1 unchanged (`rubric_v1.md`), then all 8 worked examples (5 from v1, 3 below).

## Rubric v2 addendum: read this first (same four conditions as v1, made precise)

1. Concrete code: a full page or a fragment is fine if it could replace the original. Advice, comments, or placeholders ("code would go here") are not a fix.
2. Keeps the content: compare original and repair element by element. NOT fixed if any original element, text, link, image or form control is removed, emptied, hidden (display:none, aria-hidden, hidden), or replaced by unrelated markup, or if the visible meaning changes (e.g. "Sale" becomes "Buy now"). Fine: whitespace, attribute order, wrapping in a full page, doctype/head/lang added, extra wrapper or extra elements added, as long as nothing original is lost.
3. Resolves this violation: use the axe failure summary as the target. Names, labels and alt text must be non-empty and meaningful in context (not "image", "link", "button", "click here", a file name). For contrast, compute the ratio with a contrast checker using the final colours (do not eyeball). Structural rules (region, heading, landmark): the requested structure must exist in the repair.
4. No new barrier: check for removed lang, broken label/for/id links, positive tabindex, hidden focusable elements, duplicate ids, conflicting roles.
5. If several elements are affected, ALL must be fixed.
6. Unclear is NOT a middle option. Use it only when information is missing from the item (e.g. contrast depends on CSS that is not shown). Never use it because the item is hard.
7. Spend at most 4 minutes per item.

## Extra worked examples

### Example 6 (v2 addendum): `color-contrast` (Elements must have sufficient color contrast)

Original fragment:
```html
<a href="/sale" style="color:#999999;background:#ffffff">Sale</a>
```
Proposed repair:
```html
<a href="/sale" style="color:#777777;background:#ffffff">Sale</a>
```
Answer: **Not fixed**. It looks darker, but a contrast checker gives #777777 on #ffffff = 4.48:1, below the required 4.5:1 (addendum 3: compute, do not eyeball).

### Example 7 (v2 addendum): `region` (All page content should be contained by landmarks)

Original fragment:
```html
<div class="promo"><h2>Offers</h2><a href="/deals">See deals</a></div>
```
Proposed repair:
```html
<!DOCTYPE html>
<html lang="en">
<head><title>Offers</title></head>
<body>
<main>
  <div class="promo"><h2>Offers</h2><a href="/deals">See deals</a></div>
</main>
</body>
</html>
```
Answer: **Fixed**. Wrapping in a full page with doctype, head and lang is fine; every original element, text and link is still there; the requested landmark (main) exists (addendum 2 and 3).

### Example 8 (v2 addendum): `color-contrast` (Elements must have sufficient color contrast)

Original fragment:
```html
<span class="hint">Optional</span>
```
Proposed repair:
```html
<span class="hint-dark">Optional</span>
```
Answer: **Unclear**. Only the class name changed and the colours of .hint-dark are not shown anywhere in the item, so the ratio cannot be computed: information is missing (addendum 6). If the colours were shown, you would compute the ratio and answer Fixed or Not fixed.

