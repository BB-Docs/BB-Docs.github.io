# Daily Lessons

A Jekyll site published with GitHub Pages at **https://bb-docs.github.io/**.

## Adding a lesson (the only thing you do day to day)

1. In the `_posts/` folder, create a file named `YYYY-MM-DD-short-title.md`
   (e.g. `2026-06-28-discipline.md`).
2. Start it with this header:

   ```
   ---
   title: "Your lesson title"
   subtitle: "Optional one-line summary"
   date: 2026-06-28
   ---
   ```

3. Write the lesson body below in Markdown.
4. Commit and push to `main`. GitHub rebuilds the site in ~1 minute.

Images go in `assets/` and are linked like `![caption](/assets/name.png)`.

## Structure

| Path | What it is |
|------|------------|
| `_posts/` | One Markdown file per lesson |
| `_layouts/` | Page templates (`lesson.html`, `default.html`) |
| `index.html` | Home page that lists all lessons |
| `assets/css/style.css` | Styling |
| `_config.yml` | Site title, tagline, settings |

To change the site title or tagline, edit `_config.yml`.
