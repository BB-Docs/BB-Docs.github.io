# encoding: UTF-8
require "kramdown"
css = File.read("assets/css/style.css", encoding: "UTF-8")
src = File.read("_posts/2026-06-26-peace-in-the-world.md", encoding: "UTF-8")
fm = src[/\A---(.*?)---/m, 1]
title = fm[/title:\s*"([^"]*)"/, 1]
sub = fm[/subtitle:\s*"([^"]*)"/, 1]
body = src.sub(/\A---.*?---\n/m, "")
html = Kramdown::Document.new(body).to_html
page = <<~HTML
  <!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>#{css}</style></head><body>
  <header class="site-header"><a class="brand" href="#"><span class="brand-mark">📘</span><span class="brand-name">Daily Lessons</span></a><nav class="site-nav"><a href="#">All lessons</a></nav></header>
  <main class="container"><article class="lesson">
  <p class="lesson-date"><a class="back" href="#">← All lessons</a><time>Friday, 26 June 2026</time></p>
  <h1 class="lesson-title">#{title}</h1><p class="lesson-subtitle">#{sub}</p>
  <div class="lesson-body">#{html}</div></article></main>
  <footer class="site-footer"><p>Daily Lessons · One lesson a day.</p></footer></body></html>
HTML
out = ARGV[0]
File.write(out, page)
puts "preview written to #{out}"
