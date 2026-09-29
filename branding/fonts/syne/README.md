# Syne — empty-state wordmark face

**Family:** Syne  
**License:** SIL Open Font License 1.1 (`OFL.txt`)  
**Authors:** The Syne Project Authors — https://gitlab.com/bonjour-monde/fonderie/syne-typeface

This package does **not** vendor Universal Sans, Gotham, or any proprietary Tesla face, and does not claim to ship them.

The upstream Hermes empty-state wordmark is the **Collapse** display face (`font-family: Collapse` in `apps/desktop/src/styles.css`): a high-contrast bold with thick/thin strokes. That is the red-boxed “DRAGON AI AGENT” lettering.

Syne is a free OFL geometric sans (variable, 400–800). The overlay uses **weight 700** on the wordmark, then the same family on composer and the product chrome it already touches. Files are registered as both `Syne` and `Collapse`, and unpacked `.wordmark` `font-family` is rewritten so UltraDragon does not keep drawing Collapse-Bold.
