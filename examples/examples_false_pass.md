# Examples of false passes (round 2)

These are five checker-passing AccessGuru-final repairs whose round-2 human consensus is `not_fixed`. For each one, axe-core 4.4.1 no longer reports the target rule, but both labellers judged that the repair does not truly fix the violation under the rubric.

**Selection rule (fixed in advance).**
1. Take the 44 round-2 items with consensus `not_fixed`, sorted by item id.
2. Shuffle them with Python `random.Random(20261103).shuffle`.
3. Walk the shuffled list in order and keep an item unless its model already has 2. Stop at 5.

The rule picked R2-083, R2-056, R2-117, R2-107 and R2-063, in that order. That is 2 Mistral, 2 Qwen and 1 GPT-4, all Syntax. No item was skipped for any reason other than the per-model cap.

**How to read them.**
- Lines are copied verbatim, but long fragments are **trimmed**. `[… trimmed …]` marks every cut.
- Neither labeller wrote a note on these items. The one-sentence reason is the authors' reading of the rubric (v1 + v2 addendum), written after the fact. It is not the labellers' own words.
- The full texts are in the AccessGuru repository and are pinned by `response_sha256` in `data/sample_round2.csv`.

---

## 1. R2-083 · Mistral · rule `link-name` (Ensures links have discernible text)

Original (dataset row 114):
```html
<a aria-expanded="false" aria-haspopup="true" class="dropdown-toggle" data-toggle="dropdown" href="#" id="drop1" role="button"> <i class="fa fa-globe text-muted"></i> <span class="caret"></span> </a>
```
Repair:
```html
<div class="dropdown">
  <button class="btn btn-default dropdown-toggle" id="drop1" data-toggle="dropdown">
    Globe Link (Dropdown Menu)
  </button>
  <ul class="dropdown-menu" role="menu">
    <!-- The dropdown items are assumed to be present in the original HTML and will not be altered in this example -->
  </ul>
</div>
```
**Why it fails the rubric:** the original link is replaced by a new button. Its name, "Globe Link (Dropdown Menu)", describes the icon rather than what the control does. The repair also drops the original `aria-expanded`/`aria-haspopup` state and the icon and caret elements. So the name is not meaningful, and the original content is not kept (addendum 2 and 3).

## 2. R2-056 · Qwen · rule `image-alt` (Ensures `<img>` elements have alternate text or a role of none or presentation)

Original (dataset row 172; 15 images):
```html
<img src="https://www.usagm.gov/wp-content/themes/bbgRedesign/img/logo_usagm--watermark.png">, [… trimmed: 10 more logo images …]
<img src="data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==">, [… trimmed: 2 more identical spacer images, 1 logo image …]
```
Repair:
```html
<img src="https://www.usagm.gov/wp-content/themes/bbgRedesign/img/logo_usagm--watermark.png" alt="USAGM Logo">
[… trimmed: 10 more logo images …]
<img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAEAOw==" alt="Transparent Image">
[… trimmed: 2 more identical spacer images, 1 logo image …]
```
**Why it fails the rubric:** the three 1×1 spacer GIFs get `alt="Transparent Image"`. That name is not meaningful; a decorative spacer needs `alt=""`. Their image data was also silently changed (compare the base64 strings). So not every affected element is correctly fixed, and the original content is not kept (addendum 2, 3 and 5).

## 3. R2-117 · Mistral · rule `image-alt` (Ensures `<img>` elements have alternate text or a role of none or presentation)

Original (dataset row 176; 4 images):
```html
<img decoding="async" draggable="false" height="600" sizes="100vw" src="https://cdn-images.dzcdn.net/images/misc/8b67c242cb79b3cf3b93b098a49b7a3f/0x1900-000000-80-0-0.png" width="332" loading="lazy">, [… trimmed: 3 more images from the same CDN …]
```
Repair (complete):
```html
<img src="image1.jpg" alt="A description for image1">
<img src="image2.png" alt="A description for image2">
<img src="image3.gif" alt="A description for image3">
```
**Why it fails the rubric:** the four real images are replaced by three made-up file names with placeholder alt text. So the original content is lost, and the alt text describes nothing (addendum 1, 2 and 3).

## 4. R2-107 · Qwen · rule `region` (Ensures all page content is contained by landmarks)

Original (dataset row 57; the affected elements, listed by the dataset):
```html
<section id="hero" class="home-hero">, <p>
                        Search Investigation and Recommendation Data (CAROL Query Tool)
                    </p>, [… trimmed: 2 more paragraphs …], <h1>
                    Who We Are and What We Do
                </h1>, [… trimmed: 1 div, 2 sections, 1 div (start tags only) …]
```
Repair:
```html
<div role="region" id="hero" class="home-hero">
    <h1>
        Who We Are and What We Do
    </h1>
    <p>
        Search Investigation and Recommendation Data (CAROL Query Tool)
    </p>
    [… trimmed: 2 more paragraphs …]
    <section id="news" role="region">
        <!-- Content -->
    </section>
    [… trimmed: 3 more wrappers with role="region" and "<!-- Content -->" …]
</div>
```
**Why it fails the rubric:** every wrapper gets `role="region"`, but none has an accessible name. An unnamed region is not a landmark, so the requested landmark structure does not really exist. The heading is also moved ahead of the paragraphs, and the inner content is replaced by `<!-- Content -->` comments (addendum 1, 2 and 3).

## 5. R2-063 · GPT-4 · rule `aria-allowed-role` (Ensures role attribute has an appropriate value for the element)

Original (dataset row 195; 4 checkboxes):
```html
<input type="checkbox" id="vector-main-menu-dropdown-checkbox" role="button" aria-haspopup="true" data-event-name="ui.dropdown-vector-main-menu-dropdown" class="vector-dropdown-checkbox " aria-label="Main menu">, [… trimmed: 3 more checkboxes …]
```
Repair:
```html
<!-- Corrected Code for Main Menu Dropdown Trigger -->
<button id="vector-main-menu-dropdown-button" aria-haspopup="true" aria-expanded="false" aria-controls="vector-main-menu-dropdown" aria-label="Main menu" class="vector-dropdown-checkbox ">Main menu</button>

<!-- Corresponding section for dropdown content -->
<div id="vector-main-menu-dropdown" style="display: none;">
   <!-- Dropdown menu content goes here -->
</div>
[… trimmed: the same pattern for the other 3 controls …]
```
**Why it fails the rubric:** the checkboxes become buttons, but the repair changes their ids and drops the `data-event-name` hooks. That can break whatever referred to the original ids. It also adds hidden placeholder containers ("Dropdown menu content goes here") in place of concrete code (addendum 1 and 4).

---

## Attribution

The original fragments, rule ids and rule descriptions come from the **AccessGuru dataset** by Fathallah et al., licensed under **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/). The repairs are the published GPT-4, Mistral and Qwen outputs in the AccessGuru repository (https://github.com/NadeenAhmad/AccessGuruLLM, commit `bf45666aa281af7cca23aaabd9bfe3bd802b9036`).

**Changes made here:**
- the fragments are trimmed as marked;
- the repairs are trimmed as marked, and their code fences are removed;
- nothing else is edited.

Please cite Fathallah et al. when you reuse these examples.
