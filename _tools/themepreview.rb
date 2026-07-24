# encoding: UTF-8
# Build a local preview of a lesson page (header, callouts, tables, search box)
# so light/dark can be checked without deploying.  ruby _tools/themepreview.rb <outdir>
require "kramdown"

SITE = File.expand_path("..", __dir__)
OUT  = ARGV[0]
Dir.mkdir(OUT) unless Dir.exist?(OUT)

# a lesson that exercises every callout type + tables
path = Dir[File.join(SITE, "_posts", "*peace-in-the-world-2.md")].first
raw   = File.read(path, encoding: "UTF-8")
fm    = raw[/\A---(.*?)---/m, 1]
title = fm[/title:\s*"([^"]*)"/, 1]
sub   = fm[/subtitle:\s*"([^"]*)"/, 1]
body  = Kramdown::Document.new(raw.sub(/\A---.*?---\n/m, "")).to_html

css = File.read(File.join(SITE, "assets/css/style.css"), encoding: "UTF-8")
js  = File.read(File.join(SITE, "assets/js/theme.js"),   encoding: "UTF-8")

html = <<~HTML
  <!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <script>
  (function(){var t;try{t=localStorage.getItem('theme');}catch(e){}
   if(t!=='light'&&t!=='dark'){t=(window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light';}
   document.documentElement.setAttribute('data-theme',t);})();
  </script>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>#{css}</style></head><body>
  <header class="site-header">
    <a class="brand" href="#">
      <img class="brand-lockup brand-lockup-light" src="assets/img/logo-lockup.svg" alt="Daily Lesson Notes" width="196" height="40">
      <img class="brand-lockup brand-lockup-dark" src="assets/img/logo-lockup-on-dark.svg" alt="" aria-hidden="true" width="196" height="40">
    </a>
    <nav class="site-nav">
      <a href="#">All lessons</a><a href="#">Subscribe</a>
      <button id="theme-toggle" class="theme-toggle" type="button" aria-label="Switch theme" title="Light / dark">
        <svg class="icon-moon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/></svg>
        <svg class="icon-sun" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="12" cy="12" r="4.2" fill="currentColor"/><g stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M12 2.4v2.4M12 19.2v2.4M4.4 12H2M22 12h-2.4M6.3 6.3 4.6 4.6M19.4 19.4l-1.7-1.7M17.7 6.3l1.7-1.7M4.6 19.4l1.7-1.7"/></g></svg>
      </button>
    </nav>
  </header>
  <main class="container">
    <div class="search"><input id="q" type="search" placeholder="Search lessons…  (press /)"></div>
    <ul class="lesson-list"><li class="lesson-item"><a href="#"><time>26 Jun 2026</time>
      <span class="lesson-item-title">#{title}</span>
      <span class="lesson-item-sub">#{sub}</span>
      <span class="lesson-item-snippet">… a <mark>search</mark> highlight looks like this …</span></a></li></ul>
    <article class="lesson">
      <p class="lesson-date"><a class="back" href="#">← All lessons</a><time>Friday, 26 June 2026</time></p>
      <h1 class="lesson-title">#{title}</h1><p class="lesson-subtitle">#{sub}</p>
      <div class="lesson-body">#{body}</div>
    </article>
  </main>
  <footer class="site-footer"><p>Daily Lessons · One lesson a day.</p>
  <p class="site-footer-credit">Lessons from <a href="#">kabbalahmedia.info</a> · <a href="#">Subscribe</a> · <a href="#">RSS</a></p></footer>
  <script>#{js}</script></body></html>
HTML

File.write(File.join(OUT, "index.html"), html)
puts "wrote preview -> #{OUT}/index.html"
