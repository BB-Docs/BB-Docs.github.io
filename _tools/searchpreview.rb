# encoding: UTF-8
# Build a local, Jekyll-faithful preview of the home page + search into OUT dir.
require "kramdown"

SITE = File.expand_path("..", __dir__)
OUT  = ARGV[0]
Dir.mkdir(OUT) unless Dir.exist?(OUT)

posts = Dir[File.join(SITE, "_posts", "*.md")].map do |path|
  raw = File.read(path, encoding: "UTF-8")
  fm  = raw[/\A---(.*?)---/m, 1] || ""
  body = raw.sub(/\A---.*?---\n/m, "")
  title = fm[/title:\s*"([^"]*)"/, 1] || File.basename(path)
  sub   = fm[/subtitle:\s*"([^"]*)"/, 1] || ""
  date  = fm[/date:\s*(\S+)/, 1] || File.basename(path)[0, 10]
  base  = File.basename(path, ".md")
  y, m, d, slug = base[0, 4], base[5, 2], base[8, 2], base[11..]
  html = Kramdown::Document.new(body).to_html
  text = html.gsub(/<[^>]+>/, " ").gsub(/\s+/, " ").strip
  {
    "title" => title, "subtitle" => sub,
    "date" => Time.new(y.to_i, m.to_i, d.to_i).strftime("%-d %b %Y"),
    "url" => "/lessons/#{y}/#{m}/#{d}/#{slug}/", "content" => text,
    "sortkey" => base
  }
end.sort_by { |p| p["sortkey"] }.reverse

require "json"
File.write(File.join(OUT, "search.json"),
           JSON.generate(posts.map { |p| p.reject { |k, _| k == "sortkey" } }))

items = posts.map do |p|
  %Q{<li class="lesson-item"><a href="#{p['url']}"><time>#{p['date']}</time>} +
    %Q{<span class="lesson-item-title">#{p['title']}</span>} +
    (p['subtitle'].empty? ? "" : %Q{<span class="lesson-item-sub">#{p['subtitle']}</span>}) +
    "</a></li>"
end.join("\n")

css = File.read(File.join(SITE, "assets/css/style.css"), encoding: "UTF-8")
js  = File.read(File.join(SITE, "assets/js/search.js"), encoding: "UTF-8")

html = <<~HTML
  <!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>#{css}</style></head><body>
  <header class="site-header"><a class="brand" href="#"><span class="brand-mark">📘</span><span class="brand-name">Daily Lessons</span></a><nav class="site-nav"><a href="#">All lessons</a></nav></header>
  <main class="container">
  <section class="hero"><h1>Daily Lessons</h1><p class="hero-tagline">One lesson a day.</p></section>
  <div class="search"><input id="q" type="search" placeholder="Search lessons…  (press /)" autocomplete="off" spellcheck="false" data-index="search.json"><p id="search-meta" class="search-meta" hidden></p></div>
  <ul class="lesson-list" id="search-results" hidden></ul>
  <ul class="lesson-list" id="lesson-list">
  #{items}
  </ul></main>
  <script>#{js}</script></body></html>
HTML

File.write(File.join(OUT, "index.html"), html)
puts "wrote #{posts.size} posts to #{OUT}"
