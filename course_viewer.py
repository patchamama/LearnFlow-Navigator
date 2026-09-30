#!/usr/bin/env python3
"""Local course reader for a folder of exported HTML chapters.

Run from the folder containing the exported pages:
    python3 course_viewer.py
Then open http://localhost:8765
"""
from pathlib import Path
import argparse
import functools
import json
import re
import sqlite3
import struct
import sys
import threading
import urllib.request
import urllib.error
import webbrowser
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR
GENERATED_NAMES = {"index.html", f"{ROOT.name}.html"}


def set_root(folder: Path):
    """Point the builder/server at a different course folder (creating it if needed)."""
    global ROOT, GENERATED_NAMES
    folder.mkdir(parents=True, exist_ok=True)
    ROOT = folder
    GENERATED_NAMES = {"index.html", f"{ROOT.name}.html"}


def ensure_chapter_tools_asset():
    """Copy the chapter-sidebar helper into ROOT when it targets a folder other than this script's own."""
    src = SCRIPT_DIR / "course-reader-chapter-tools.js"
    dest = ROOT / "course-reader-chapter-tools.js"
    if src.resolve() != dest.resolve() and src.exists() and not dest.exists():
        dest.write_bytes(src.read_bytes())


def prompt_for_folder(current: Path) -> Path:
    """Ask which folder to use when none was given and the current one has no course content."""
    try:
        entered = input(
            f"No course chapters found in '{current}'.\n"
            f"Enter a folder to use instead (e.g. examples), or press Enter to keep this one: "
        ).strip()
    except (EOFError, KeyboardInterrupt):
        return current
    return Path(entered).expanduser().resolve() if entered else current


def chapter_title(filename: str) -> str:
    """Turn an exported filename into a concise chapter label."""
    name = Path(filename).stem
    name = re.sub(r"\s*_\s*Rise 360$", "", name, flags=re.I)
    name = re.sub(r"\s*-\s*ELO 25 Flows Development\s*-\s*Handout \(DE\)", "", name, flags=re.I)
    name = re.sub(r"^\d+\s+", "", name)
    return name.strip() or Path(filename).stem


APP = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Course Reader</title><style>
:root{--bg:#f5f7fb;--card:#fff;--soft:#edf2fa;--text:#15233b;--muted:#69758a;--line:#d9e1ed;--accent:#3867f4;--accentSoft:#e9efff;--ok:#16a36a;--shadow:0 16px 45px #16254020;color-scheme:light}:root.dark{--bg:#101827;--card:#192438;--soft:#243248;--text:#edf4ff;--muted:#adbbd0;--line:#33445f;--accent:#8eabff;--accentSoft:#293d6d;--ok:#4ed596;--shadow:0 16px 45px #0008;color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 Inter,system-ui,sans-serif}.app{height:100vh;display:grid;grid-template-columns:330px 7px 1fr}.app.panelCollapsed{grid-template-columns:1fr!important}.app.panelCollapsed .side,.app.panelCollapsed .resizer{display:none}.app.panelCollapsed main{grid-column:1/-1;width:100%}.resizer{cursor:col-resize;background:transparent;position:relative;z-index:6}.resizer:hover,.resizer.dragging{background:var(--accent)}.side{min-width:0;background:var(--card);border-right:1px solid var(--line);display:flex;flex-direction:column}.side.collapsed{display:none}.app:has(.side.collapsed){grid-template-columns:1fr}.brand{padding:20px;border-bottom:1px solid var(--line)}.eyebrow{font-size:10px;font-weight:850;letter-spacing:.13em;text-transform:uppercase;color:var(--accent)}h1{font-size:19px;margin:3px 0 12px}.bar{height:7px;border-radius:7px;background:var(--soft);overflow:hidden}.bar i{display:block;height:100%;background:var(--accent);width:0}.copy{font-size:12px;color:var(--muted);margin:7px 0 0}.tabs{display:flex;padding:8px 10px 0;gap:5px}.tab{flex:1;border:0;border-bottom:2px solid transparent;padding:8px;background:transparent;color:var(--muted);font-weight:750;cursor:pointer}.tab.active{color:var(--accent);border-color:var(--accent)}.pane{display:none;overflow:auto;min-height:0}.pane.active{display:block;flex:1}.chapters,.assets{list-style:none;padding:10px;margin:0}.chapter{width:100%;display:grid;grid-template-columns:29px 1fr;gap:10px;border:0;background:none;color:var(--text);text-align:left;padding:8px 7px;cursor:pointer;border-radius:9px;position:relative}.chapter:hover,.chapter.active{background:var(--accentSoft)}.chapter:not(:last-child) .node:after{content:"";position:absolute;top:25px;bottom:-17px;left:13px;width:2px;background:var(--line)}.node{position:relative;width:25px;height:25px;display:grid;place-items:center;border:1.5px solid var(--line);border-radius:50%;font-size:11px;font-weight:800;color:var(--muted);z-index:1;background:var(--card)}.chapter.active .node{color:var(--accent);border-color:var(--accent)}.chapter.read .node{background:var(--ok);border-color:var(--ok);color:#fff}.chapter-title{font-weight:700}.chapter small{color:var(--muted);display:block}.module{border:1px solid var(--line);border-radius:10px;margin:8px;overflow:hidden}.module summary{padding:9px;cursor:pointer;font-weight:750;background:var(--soft)}.module .chapters{padding:4px 8px}.filegroup{margin:8px;border:1px solid var(--line);border-radius:9px;overflow:hidden}.filegroup summary{padding:8px;cursor:pointer;font-weight:700}.file{display:block;padding:6px 9px 6px 25px;color:var(--muted);font-size:12px;text-decoration:none;overflow-wrap:anywhere}.file:hover{color:var(--accent);background:var(--accentSoft)}.hint{padding:10px;color:var(--muted);font-size:12px}.foot{padding:13px 20px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}main{min-width:0;display:grid;grid-template-rows:auto 1fr}.top{display:flex;align-items:center;gap:8px;padding:12px 18px;background:var(--card);border-bottom:1px solid var(--line)}.current{flex:1;min-width:0}.current b{display:block;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.current span{font-size:12px;color:var(--muted)}.notesButton{white-space:nowrap;padding:7px!important}.btn{border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--text);min-height:35px;padding:7px 10px;font-weight:700;cursor:pointer}.btn:hover,.btn.active{color:var(--accent);border-color:var(--accent);background:var(--accentSoft)}.collapse{font-size:18px;width:37px;padding:0}.search{position:relative;display:none}.search.live{display:flex;gap:4px}.search input{width:220px;border:1px solid var(--line);border-radius:7px;padding:7px;background:var(--bg);color:var(--text)}.results{position:absolute;top:42px;right:0;width:min(540px,70vw);max-height:55vh;overflow:auto;background:var(--card);border:1px solid var(--line);box-shadow:var(--shadow);border-radius:9px;padding:8px;z-index:7}.result{display:block;width:100%;text-align:left;border:0;background:none;color:var(--text);padding:9px;cursor:pointer;border-bottom:1px solid var(--line)}.result:hover{background:var(--accentSoft)}.result small{color:var(--muted);display:block}.reader{min-height:0;position:relative;background:var(--soft);display:flex;justify-content:center;overflow:auto}.reader iframe{flex:0 0 var(--content-width,100%);max-width:100%;font-family:var(--reader-font,system-ui);font-size:var(--reader-size,14px)}.reader.reader-white{background:#fff}.reader.reader-caramel{background:#d8b27a}.reader.reader-black{background:#000}.reader.reader-dark{background:#101827}.chapterNav{position:absolute;right:20px;bottom:18px;z-index:4;display:flex;gap:8px;filter:drop-shadow(0 4px 9px #0004)}iframe{width:100%;height:100%;border:0;background:#fff}.notesButton{position:static;z-index:5;border:0;border-radius:22px;background:var(--accent);color:white;padding:12px 16px;font-weight:800;box-shadow:var(--shadow);cursor:pointer}.badge{background:#fff;color:var(--accent);border-radius:20px;padding:1px 6px;margin-left:5px}.searchModal{position:fixed;inset:0;z-index:20;background:#0007;display:none;place-items:start center;padding-top:12vh}.searchModal.open{display:grid}.searchDialog{width:min(680px,calc(100vw - 30px));background:var(--card);border-radius:12px;padding:16px;box-shadow:var(--shadow)}.searchDialog>div:first-child{display:flex;justify-content:space-between;align-items:center;font-size:17px}.searchDialog input{width:100%;margin:12px 0 8px;padding:10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--text)}.searchBoxResults{max-height:45vh;overflow:auto;margin-top:9px}.settingsPanel{position:fixed;z-index:8;right:20px;top:65px;width:min(420px,calc(100vw - 40px));max-height:calc(100vh - 80px);overflow:auto;padding:15px;background:var(--card);border:1px solid var(--line);border-radius:13px;box-shadow:var(--shadow);display:none}.settingsPanel.open{display:grid;gap:9px}.settingsPanel label{display:grid;gap:3px;font-size:12px;font-weight:700}.settingsPanel input,.settingsPanel select,.settingsPanel textarea{width:100%;border:1px solid var(--line);border-radius:7px;padding:8px;background:var(--bg);color:var(--text)}.settingsPanel textarea{min-height:90px}.settingsPanel article{white-space:pre-wrap;font-size:13px}.notes{position:fixed;z-index:8;right:20px;bottom:74px;width:min(460px,calc(100vw - 40px));height:min(580px,calc(100vh - 100px));padding:15px;background:var(--card);border:1px solid var(--line);border-radius:13px;box-shadow:var(--shadow);display:none;flex-direction:column}.notes.open{display:flex}.notes.max{inset:15px;width:auto;height:auto;bottom:15px}.notesHead,.tools,.notesFoot{display:flex;align-items:center;gap:7px}.notesHead b{font-size:16px;flex:1}.tools{margin:10px 0}.tools .btn{min-height:30px;padding:5px 8px;font-size:12px}.editor,.preview{flex:1;min-height:0;width:100%;border:1px solid var(--line);border-radius:8px;padding:10px;background:var(--bg);color:var(--text);font:13px/1.5 ui-monospace,monospace;resize:none}.preview{display:none;overflow:auto;font-family:inherit;white-space:normal}.preview h1,.preview h2,.preview h3{margin:.5em 0}.preview code{background:var(--soft);padding:1px 4px}.preview blockquote{border-left:3px solid var(--accent);margin:9px 0;padding:6px 10px;background:var(--accentSoft)}.notesFoot{justify-content:space-between;margin-top:9px;font-size:12px;color:var(--muted)}.help{position:absolute;right:14px;top:55px;width:300px;background:var(--card);border:1px solid var(--line);box-shadow:var(--shadow);padding:12px;border-radius:9px;display:none;z-index:9;font-size:12px}.help.open{display:block}.help pre{white-space:pre-wrap;background:var(--soft);padding:7px;border-radius:5px}@media(max-width:780px){.app{grid-template-columns:1fr;grid-template-rows:220px 1fr}.resizer{display:none}.side{border-right:0;border-bottom:1px solid var(--line)}.side.collapsed{display:none}.app:has(.side.collapsed){grid-template-rows:1fr}.foot{display:none}.top{padding:8px}.btn.nav{font-size:0;width:36px;padding:0}.btn.nav::first-letter{font-size:15px}.notes{right:10px;width:calc(100vw - 20px)}.notesButton{right:10px}}</style></head><body><div class="app"><aside class="side" id="side"><div class="brand"><div class="eyebrow">Learning space</div><h1>Course reader</h1><div class="bar"><i id="progress"></i></div><p class="copy" id="progressCopy"></p></div><div class="tabs"><button class="tab active" data-pane="chapterPane">Chapters</button><button class="tab" data-pane="filePane">Course files</button></div><section class="pane active" id="chapterPane"><div id="chapterList"></div></section><section class="pane" id="filePane"><div id="fileList"></div></section><div class="foot">Progress and notes are stored privately in this browser.</div></aside><div class="resizer" id="resizer" title="Drag to resize course panel"></div><main><header class="top"><button class="btn collapse" id="collapse" title="Collapse course panel">☰</button><div class="current"><b id="title">Loading…</b><span id="meta"></span></div><button class="btn nav" id="first">↤ First</button><button class="btn nav" id="prev">← Previous</button><button class="btn nav" id="next">Next →</button><button class="btn nav" id="last">Last ↦</button><button class="btn" id="searchToggle" title="Search course">⌕</button><button class="notesButton" id="notesOpen">✎ Notes <span class="badge" id="badge">0</span></button><div class="search" id="search"><input id="searchInput" placeholder="Search course…" aria-label="Search course"><button class="btn" id="searchGo">Search</button><div class="results" id="results" hidden></div></div><button class="btn" id="hideInner" title="Hide/show navigation inside current chapter">Hide sidebar</button><button class="btn" id="settings" title="AI settings">⚙</button><button class="btn" id="theme" title="Switch color theme">☾</button></header><div class="reader"><iframe id="frame"></iframe><div class="chapterNav" id="chapterNav"><button class="btn" id="bottomPrev">← Previous</button><button class="btn" id="bottomNext">Next →</button></div></div></main></div><section class="searchModal" id="searchModal" role="dialog" aria-label="Course search"><div class="searchDialog"><div><b>Search course</b><button class="btn" id="searchClose">×</button></div><input id="modalSearchInput" placeholder="Enter a term or question…"><label id="aiSearchOption"><input type="checkbox" id="aiSearch"> Answer with AI and course RAG</label><button class="btn" id="modalSearchGo">Search</button><div class="searchBoxResults" id="searchBoxResults"></div></div></section><section class="settingsPanel" id="settingsPanel"><b>AI course assistant</b><label>Provider <select id="provider"><option value="ollama">Ollama (local)</option><option value="openai">OpenAI</option><option value="anthropic">Anthropic</option></select></label><label>API key <input id="apiKey" type="password" placeholder="Stored in browser unless saved below"></label><label><input id="saveBackend" type="checkbox"> Save this configuration and API key in the local backend</label><label>Model <select id="model"></select></label><label>Course language <input id="courseLanguage" value="German" placeholder="e.g. German"></label><hr><b>Reader appearance</b><label><input id="readerRaw" type="checkbox"> Show chapters unmodified (ignore the options below)</label><label>Background <select id="readerBg"><option value="white">White</option><option value="caramel">Caramel</option><option value="black">Black</option></select></label><label>Content width <select id="contentWidth"><option value="100%">Full</option><option value="75%">75%</option><option value="50%">50%</option></select></label><label>Font <select id="readerFont"><option value="system-ui">System</option><option value="Arial">Arial</option><option value="Georgia">Georgia</option><option value="Verdana">Verdana</option></select></label><label>Font size <select id="readerSize"><option value="14px">14 px</option><option value="16px">16 px</option><option value="18px">18 px</option><option value="20px">20 px</option></select></label><button class="btn" id="loadModels">Test & load models</button><hr><textarea id="question" placeholder="Ask about this course…"></textarea><button class="btn" id="ask">Ask with course context</button><article id="answer"></article></section><section class="notes" id="notes"><div class="notesHead"><b>Notes & tasks</b><button class="btn" id="maximize" title="Maximize notes">⛶</button><button class="btn" id="notesClose">×</button></div><div class="tools"><button class="btn" id="editMode">Edit</button><button class="btn" id="previewMode">Preview</button><button class="btn" id="addTask">☐ Task</button><button class="btn" id="addCallout">💡 Callout</button><button class="btn" id="import">Import</button><button class="btn" id="export">Export .md</button><button class="btn" id="helpBtn" title="Markdown examples">?</button></div><aside class="help" id="help"><b>Markdown quick help</b><pre># Heading
**bold** and *italic*
- [ ] Open task
- [x] Done task
> [!NOTE]
> Useful information
> [!TIP]
> Helpful suggestion</pre></aside><textarea class="editor" id="editor" placeholder="Write Markdown notes…"></textarea><article class="preview" id="preview"></article><div class="notesFoot"><span id="taskText">0 open tasks</span><span>Saved automatically</span></div><input id="importFile" type="file" accept=".md,text/markdown,text/plain" hidden></section><script>
const data=__DATA__,key='course-reader-v2',$=id=>document.getElementById(id);let activeChapterDoc=null,sidebarHidden=localStorage.getItem('course-reader-sidebar-hidden')!=='0',skipPositionRestore=false;localStorage.setItem('course-reader-sidebar-hidden',sidebarHidden?'1':'0');function syncSidebarButton(){ $('hideInner').textContent=sidebarHidden?'Show sidebar':'Hide sidebar';$('hideInner').classList.toggle('active',sidebarHidden) }function applySidebarState(){ if(sidebarHidden)$('frame').contentWindow?.postMessage({courseReaderAction:'setSidebarHidden',hidden:true},'*') }let state=JSON.parse(localStorage.getItem(key)||'{"read":[],"notes":"","theme":"light"}'),current=Math.max(0,Number(localStorage.getItem('course-reader-current')||0));const chapters=data.chapters;const positions=JSON.parse(localStorage.getItem('course-reader-positions')||'{}');const aiKey='course-reader-ai-v1';let ai=JSON.parse(localStorage.getItem(aiKey)||'{"provider":"ollama","apiKey":"","model":"","language":"German","bg":"white","width":"100%","font":"system-ui","size":"14px","raw":false}');
function esc(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}function save(){localStorage.setItem(key,JSON.stringify(state))}function taskCount(){return(state.notes.match(/- \[ \]/g)||[]).length}function updateNotes(sync=true){let n=taskCount();$('badge').textContent=n;$('taskText').textContent=`${n} open task${n==1?'':'s'}`;if(sync)$('editor').value=state.notes}function renderMD(md){let h=esc(md).replace(/^### (.*)$/gm,'<h3>$1</h3>').replace(/^## (.*)$/gm,'<h2>$1</h2>').replace(/^# (.*)$/gm,'<h1>$1</h1>').replace(/^&gt; \[!(TIP|NOTE|WARNING|IMPORTANT)\]\n((?:&gt; .*\n?)*)/gm,(_,t,b)=>`<blockquote><b>${t}</b><br>${b.replace(/^&gt; ?/gm,'')}</blockquote>`).replace(/^- \[ \] (.*)$/gm,'☐ $1').replace(/^- \[x\] (.*)$/gmi,'☑ $1').replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/`(.+?)`/g,'<code>$1</code>').replace(/\n/g,'<br>');return h}function setTheme(){document.documentElement.classList.toggle('dark',state.theme==='dark');$('theme').textContent=state.theme==='dark'?'☀':'☾';applyAppearance()}
function chapterHTML(items){let r=new Set(state.read);return `<ol class="chapters">${items.map(c=>`<li><button class="chapter ${c.id===current?'active':''} ${r.has(c.path)?'read':''}" data-id="${c.id}"><span class="node">${r.has(c.path)?'✓':c.order}</span><span><span class="chapter-title">${c.title}</span><small>${r.has(c.path)?'Completed':'Chapter '+c.order}</small></span></button></li>`).join('')}</ol>`}function render(){let root=chapters.filter(x=>!x.module),mods=data.modules;$('chapterList').innerHTML=chapterHTML(root)+mods.map(m=>`<details class="module" open><summary>▣ ${m.name} <small>(${m.chapters.length} chapters)</small>${chapterHTML(m.chapters)}</details>`).join('')||'<p class="hint">No chapters found.</p>';$('chapterList').querySelectorAll('.chapter').forEach(b=>b.onclick=()=>openChapter(+b.dataset.id));$('fileList').innerHTML=fileGroups(data.courseFiles,'Course files')+mods.map(m=>fileGroups(m.files,`Files · ${m.name}`)).join('')||'<p class="hint">No course files found.</p>';let done=new Set(state.read).size;$('progress').style.width=`${chapters.length?done/chapters.length*100:0}%`;$('progressCopy').textContent=`${done} of ${chapters.length} chapters completed`;$('title').textContent=chapters[current]?.title||'No chapters found';$('meta').textContent=chapters.length?`Chapter ${current+1} of ${chapters.length}`:'';$('first').disabled=!chapters.length||current===0;$('prev').disabled=!chapters.length||current===0;$('next').disabled=!chapters.length||current===chapters.length-1;$('last').disabled=!chapters.length||current===chapters.length-1;$('bottomPrev').disabled=!chapters.length||current===0;$('bottomNext').disabled=!chapters.length||current===chapters.length-1}function fileGroups(groups,label){return `<details class="filegroup" open><summary>📁 ${label}</summary>${groups.map(g=>`<details class="filegroup"><summary>📂 ${g.name}</summary>${g.files.map(f=>`<a class="file" href="${f.path}" target="_blank">${f.name}</a>`).join('')}</details>`).join('')}</details>`}
function openChapter(i,opts){if(!chapters.length)return;current=Math.max(0,Math.min(i,chapters.length-1));skipPositionRestore=!!(opts&&opts.skipRestore);localStorage.setItem('course-reader-current',current);let path=chapters[current].path;if(/\.md$/i.test(path)){$('frame').removeAttribute('src');fetch(path).then(r=>r.text()).then(md=>{$('frame').srcdoc=renderMarkdownPage(md,chapters[current].title)}).catch(()=>{$('frame').srcdoc='<p>Could not load '+esc(path)+'</p>'})}else{$('frame').removeAttribute('srcdoc');$('frame').src=path}render()}function complete(){let c=chapters[current];if(c&&!state.read.includes(c.path)){state.read.push(c.path);save();render()}}$('frame').addEventListener('load',()=>{applyAppearance();setTimeout(()=>{syncSidebarButton();applySidebarState()},500);setTimeout(()=>{try{let d=$('frame').contentDocument;activeChapterDoc=d;let w=$('frame').contentWindow,check=()=>{let e=d.scrollingElement;if(e&&e.scrollTop+e.clientHeight>=e.scrollHeight-8)complete()};let savePosition=()=>{let y=w.scrollY||w.pageYOffset||d.scrollingElement?.scrollTop||d.documentElement?.scrollTop||d.body?.scrollTop||0;positions[chapters[current].path]=y;localStorage.setItem('course-reader-positions',JSON.stringify(positions));check()};w.addEventListener('scroll',savePosition,{passive:true});d.addEventListener('scroll',savePosition,{passive:true,capture:true});w.addEventListener('beforeunload',savePosition);let saved=skipPositionRestore?0:positions[chapters[current].path];skipPositionRestore=false;if(saved)setTimeout(()=>{w.scrollTo(0,saved);d.scrollingElement&&(d.scrollingElement.scrollTop=saved)},900);check();let installNav=()=>{if(d.querySelector('.nav-sidebar__content,[class*="nav-sidebar"]'))$('hideInner').classList.add('available');applyAppearance();};installNav();setTimeout(installNav,1200);let end=d.createElement('div');end.innerHTML='<button data-course-nav="prev">← Previous</button><button data-course-nav="next">Next →</button>';end.style.cssText='position:fixed;bottom:14px;right:18px;z-index:999999;display:flex;gap:8px';end.querySelectorAll('button').forEach(b=>b.style.cssText='padding:9px 13px;border:0;border-radius:7px;background:#3867f4;color:white;font:600 14px sans-serif;cursor:pointer');end.onclick=e=>{let x=e.target.dataset.courseNav;if(x)parent.postMessage({courseNav:x},'*')};d.body.append(end)}catch(e){}},300)});window.addEventListener('message',e=>{if(e.data?.courseNav==='next')openChapter(current+1);if(e.data?.courseNav==='prev')openChapter(current-1);if(Number.isInteger(e.data?.courseReaderNavigateIndex))openChapter(e.data.courseReaderNavigateIndex);if(e.data?.courseReaderAction==='toggleSidebarHidden')$('hideInner').click();if(e.data?.courseReaderSidebar!==undefined){let hidden=e.data.courseReaderSidebar;sidebarHidden=hidden;localStorage.setItem('course-reader-sidebar-hidden',hidden?'1':'0');$('hideInner').dataset.hidden=hidden?'true':'false';$('hideInner').classList.toggle('active',hidden);$('hideInner').textContent=hidden?'Show sidebar':'Hide sidebar'};});
async function search(){let q=$('modalSearchInput').value.trim();if(!q)return;let box=$('searchBoxResults');box.textContent='Searching…';try{if($('aiSearch').checked&&ai.model){try{let d=await fetchJSON('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...ai,question:q})});box.textContent=d.answer||d.error}catch(e){box.textContent='AI assistant needs the local backend (run start.sh/start.bat).'}return}let results;try{results=(await fetchJSON('/api/search?q='+encodeURIComponent(q))).results}catch(e){results=await clientSearch(q)}box.innerHTML=results.length?results.map(x=>`<button class="result" data-path="${x.path}"><b>${x.title}</b><small>${x.snippet}</small></button>`).join(''):'No matching course content.';box.querySelectorAll('.result').forEach(b=>b.onclick=()=>{let i=chapters.findIndex(c=>c.path===b.dataset.path);if(i>=0)openChapter(i,{skipRestore:true});$('searchModal').classList.remove('open')})}catch(e){box.textContent='Search failed: '+e.message}}$('searchToggle').onclick=()=>{let configured=Boolean(ai.model);$('aiSearchOption').hidden=!configured;$('aiSearch').checked=configured;$('searchModal').classList.add('open');$('modalSearchInput').focus()};$('searchClose').onclick=()=>$('searchModal').classList.remove('open');$('modalSearchGo').onclick=search;$('modalSearchInput').onkeydown=e=>{if(e.key==='Enter')search()};document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{document.querySelectorAll('.tab,.pane').forEach(x=>x.classList.remove('active'));t.classList.add('active');$(t.dataset.pane).classList.add('active')});$('hideInner').onclick=()=>{sidebarHidden=!sidebarHidden;localStorage.setItem('course-reader-sidebar-hidden',sidebarHidden?'1':'0');syncSidebarButton();$('frame').contentWindow?.postMessage({courseReaderAction:'setSidebarHidden',hidden:sidebarHidden},'*')};const app=document.querySelector('.app'),resize=$('resizer');$('collapse').onclick=()=>{app.classList.toggle('panelCollapsed');$('collapse').textContent=app.classList.contains('panelCollapsed')?'☰':'×'};let resizing=false;resize.onpointerdown=e=>{resizing=true;resize.classList.add('dragging');resize.setPointerCapture(e.pointerId)};resize.onpointermove=e=>{if(resizing){let width=Math.max(220,Math.min(620,e.clientX));app.style.gridTemplateColumns=`${width}px 7px 1fr`;localStorage.setItem('course-panel-width',width)}};resize.onpointerup=()=>{resizing=false;resize.classList.remove('dragging')};let savedWidth=localStorage.getItem('course-panel-width');if(savedWidth)app.style.gridTemplateColumns=`${savedWidth}px 7px 1fr`;$('bottomPrev').onclick=()=>openChapter(current-1);$('bottomNext').onclick=()=>openChapter(current+1);$('first').onclick=()=>openChapter(0);$('prev').onclick=()=>openChapter(current-1);$('next').onclick=()=>openChapter(current+1);$('last').onclick=()=>openChapter(chapters.length-1);$('theme').onclick=()=>{state.theme=state.theme==='dark'?'light':'dark';save();setTheme()};$('notesOpen').onclick=()=>$('notes').classList.add('open');$('notesClose').onclick=()=>$('notes').classList.remove('open');$('maximize').onclick=()=>$('notes').classList.toggle('max');$('editMode').onclick=()=>{$('editor').style.display='block';$('preview').style.display='none'};$('previewMode').onclick=()=>{$('preview').innerHTML=renderMD(state.notes);$('editor').style.display='none';$('preview').style.display='block'};$('editor').oninput=()=>{state.notes=$('editor').value;save();updateNotes(false)};function insert(x){let e=$('editor'),p=e.selectionStart;e.setRangeText(x,p,e.selectionEnd,'end');e.focus();state.notes=e.value;save();updateNotes(false)}$('addTask').onclick=()=>insert('- [ ] ');$('addCallout').onclick=()=>insert('> [!NOTE]\n> ');$('helpBtn').onclick=()=>$('help').classList.toggle('open');$('export').onclick=()=>{let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([state.notes],{type:'text/markdown'}));a.download='course-notes.md';a.click();URL.revokeObjectURL(a.href)};$('import').onclick=()=>$('importFile').click();$('importFile').onchange=e=>{let f=e.target.files[0];if(f){let r=new FileReader;r.onload=()=>{state.notes=r.result;save();updateNotes()};r.readAsText(f)}};document.onkeydown=e=>{if(e.altKey&&e.key==='ArrowRight')openChapter(current+1);if(e.altKey&&e.key==='ArrowLeft')openChapter(current-1)};const PALETTES={white:{bg:'#fff',text:'#15233b',muted:'#5b6b85',card:'#f5f7fb',line:'#d9e1ed',link:'#3867f4',kw:'#a626a4',str:'#50a14f',com:'#a0a1a7',num:'#986801',tag:'#e45649',attr:'#986801',scheme:'light'},caramel:{bg:'#d8b27a',text:'#2b1d0e',muted:'#5a4327',card:'#e6c793',line:'#b98f56',link:'#7a3b00',kw:'#7b1fa2',str:'#2e6b1f',com:'#6d5a3c',num:'#8a4b00',tag:'#b3261e',attr:'#8a4b00',scheme:'light'},black:{bg:'#000',text:'#e7edf7',muted:'#95a3bd',card:'#111a2e',line:'#233052',link:'#8eabff',kw:'#c678dd',str:'#98c379',com:'#7f848e',num:'#d19a66',tag:'#e06c75',attr:'#e5c07b',scheme:'dark'},dark:{bg:'#101827',text:'#edf4ff',muted:'#adbbd0',card:'#192438',line:'#33445f',link:'#8eabff',kw:'#c678dd',str:'#98c379',com:'#7f848e',num:'#d19a66',tag:'#e06c75',attr:'#e5c07b',scheme:'dark'}};function readerPalette(){let k=ai.bg||'white';if(state.theme==='dark'&&k==='white')k='dark';return [k,PALETTES[k]||PALETTES.white]}function applyAppearance(){let r=document.querySelector('.reader');['readerBg','contentWidth','readerFont','readerSize'].forEach(id=>$(id).disabled=!!ai.raw);if(ai.raw){r.classList.remove('reader-white','reader-caramel','reader-black','reader-dark');['--content-width','--reader-font','--reader-size'].forEach(v=>r.style.removeProperty(v));try{$('frame').contentDocument.getElementById('readerAppearance')?.remove()}catch(e){}return}let [k,p]=readerPalette();r.classList.remove('reader-white','reader-caramel','reader-black','reader-dark');r.classList.add('reader-'+k);r.style.setProperty('--content-width',ai.width||'100%');r.style.setProperty('--reader-font',ai.font||'system-ui');r.style.setProperty('--reader-size',ai.size||'14px');try{let d=$('frame').contentDocument;if(!d||!d.head)return;let st=d.getElementById('readerAppearance')||d.head.appendChild(d.createElement('style')),T='p,li,h1,h2,h3,h4,h5,h6,td,th,blockquote,label,dt,dd,figcaption,a',f=ai.font||'system-ui',z=ai.size||'14px';st.id='readerAppearance';st.textContent=`:root{--bg:${p.bg}!important;--text:${p.text}!important;--muted:${p.muted}!important;--card:${p.card}!important;--line:${p.line}!important;--accent:${p.link}!important;color-scheme:${p.scheme}!important}html,body{background:${p.bg}!important;color:${p.text}!important;font-family:${f}!important;font-size:${z}!important}body :where(main,section,article,header,footer,aside,div){background-color:transparent!important}body :where(${T}){color:${p.text}!important;font-family:${f}!important}body :where(p,li,td,th,blockquote,label,dt,dd){font-size:${z}!important}body a{color:${p.link}!important}pre,pre.code-block{background:${p.card}!important;border-color:${p.line}!important}.tok-kw{color:${p.kw}!important}.tok-str{color:${p.str}!important}.tok-com{color:${p.com}!important}.tok-num{color:${p.num}!important}.tok-tag{color:${p.tag}!important}.tok-attr{color:${p.attr}!important}`}catch(e){}}function saveAI(){ai={provider:$('provider').value,apiKey:$('apiKey').value,model:$('model').value,language:$('courseLanguage').value,bg:$('readerBg').value,width:$('contentWidth').value,font:$('readerFont').value,size:$('readerSize').value,raw:$('readerRaw').checked};localStorage.setItem(aiKey,JSON.stringify(ai));if($('saveBackend').checked)fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(ai)})}function fillAI(){ $('provider').value=ai.provider;$('apiKey').value=ai.apiKey;$('courseLanguage').value=ai.language;$('readerBg').value=ai.bg||'white';$('contentWidth').value=ai.width||'100%';$('readerFont').value=ai.font||'system-ui';$('readerSize').value=ai.size||'14px';$('readerRaw').checked=!!ai.raw;applyAppearance()}$('settings').onclick=async()=>{$('settingsPanel').classList.toggle('open');fillAI();try{let d=await fetchJSON('/api/settings');if(d.provider){ai=d;fillAI();$('saveBackend').checked=true}}catch(e){}};$('loadModels').onclick=async()=>{saveAI();$('model').innerHTML='<option>Loading…</option>';try{let d=await fetchJSON('/api/models',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(ai)});if(d.error)throw Error(d.error);$('model').innerHTML=d.models.map(x=>`<option>${x}</option>`).join('');if(ai.model)$('model').value=ai.model;$('answer').textContent='Connection successful.'}catch(e){$('answer').textContent=(e.message==='backend-unavailable'?'This needs the local backend (run start.sh/start.bat).':'Connection failed: '+e.message)}};['readerRaw','readerBg','contentWidth','readerFont','readerSize'].forEach(id=>$(id).onchange=()=>{saveAI();applyAppearance()});$('ask').onclick=async()=>{saveAI();let q=$('question').value.trim();if(!q)return;$('answer').textContent='Thinking with course context…';try{let d=await fetchJSON('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...ai,question:q})});$('answer').textContent=d.answer||d.error}catch(e){$('answer').textContent=(e.message==='backend-unavailable'?'This needs the local backend (run start.sh/start.bat).':'Request failed: '+e.message)}};setTheme();updateNotes();applyAppearance();syncSidebarButton();render();openChapter(current);
const CODE_KEYWORDS={python:"False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield".split(' '),php:"abstract and array as break callable case catch class clone const continue declare default do echo else elseif empty enddeclare endfor endforeach endif endswitch endwhile enum extends final finally fn for foreach function global goto if implements include include_once instanceof insteadof interface isset list match namespace new or print private protected public readonly require require_once return static switch throw trait try unset use var while xor yield".split(' '),java:"abstract assert boolean break byte case catch char class const continue default do double else enum extends final finally float for goto if implements import instanceof int interface long native new package private protected public record return sealed short static strictfp super switch synchronized this throw throws transient try var void volatile while yield permits".split(' '),go:"break default func interface select case defer go map struct chan else goto package switch const fallthrough if range type continue for import return var".split(' '),javascript:"break case catch class const continue debugger default delete do else export extends finally for function if import in instanceof let new return super switch this throw try typeof var void while with yield async await static get set of".split(' '),bash:"if then else elif fi for while do done case esac function in select until time".split(' ')};
CODE_KEYWORDS.py=CODE_KEYWORDS.python;CODE_KEYWORDS.js=CODE_KEYWORDS.javascript;CODE_KEYWORDS.sh=CODE_KEYWORDS.bash;
function highlightGeneric(code,lang){
  let kws=new Set(CODE_KEYWORDS[lang]||[]);
  let escaped=esc(code);
  let tokenRe=/(\/\/[^\n]*|#[^\n]*|\/\*[\s\S]*?\*\/)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`)|(\b\d+\.?\d*\b)|(\b[A-Za-z_]\w*\b)/g;
  return escaped.replace(tokenRe,(m,com,str,num,word)=>{
    if(com)return `<span class="tok-com">${com}</span>`;
    if(str)return `<span class="tok-str">${str}</span>`;
    if(num)return `<span class="tok-num">${num}</span>`;
    if(word)return kws.has(word)?`<span class="tok-kw">${word}</span>`:word;
    return m;
  });
}
function highlightMarkup(code){
  let escaped=esc(code);
  return escaped.replace(/(&lt;!--[\s\S]*?--&gt;)|(&lt;\/?[a-zA-Z][\w:-]*)((?:\s+[\w:-]+(?:=(?:"[^"]*"|'[^']*'))?)*)(\s*\/?&gt;)/g,(m,comment,open,attrs,close)=>{
    if(comment)return `<span class="tok-com">${comment}</span>`;
    let attrHl=attrs.replace(/([\w:-]+)(=)("[^"]*"|'[^']*')?/g,(am,name,eq,val)=>val?`<span class="tok-attr">${name}</span>${eq}<span class="tok-str">${val}</span>`:`<span class="tok-attr">${name}</span>`);
    return `<span class="tok-tag">${open}</span>${attrHl}<span class="tok-tag">${close}</span>`;
  });
}
function highlightJson(code){
  let escaped=esc(code);
  return escaped.replace(/("(?:[^"\\]|\\.)*")(\s*:)?|(\b(?:true|false|null)\b)|(-?\b\d+\.?\d*(?:[eE][+-]?\d+)?\b)/g,(m,str,colon,lit,num)=>{
    if(str)return colon?`<span class="tok-attr">${str}</span>${colon}`:`<span class="tok-str">${str}</span>`;
    if(lit)return `<span class="tok-kw">${lit}</span>`;
    if(num)return `<span class="tok-num">${num}</span>`;
    return m;
  });
}
function highlightCode(code,lang){
  let l=(lang||'').toLowerCase();
  if(l==='xml'||l==='html')return highlightMarkup(code);
  if(l==='json')return highlightJson(code);
  if(CODE_KEYWORDS[l])return highlightGeneric(code,l);
  return esc(code);
}
function renderMarkdownBody(md){
  let lines=md.replace(/\r\n/g,'\n').split('\n'),html='',i=0,listStack=null;
  function closeList(){if(listStack){html+=`</${listStack}>`;listStack=null}}
  function inline(s){
    s=esc(s);
    s=s.replace(/`([^`]+)`/g,(m,c)=>`<code>${c}</code>`);
    s=s.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
    s=s.replace(/\*([^*]+)\*/g,'<em>$1</em>');
    s=s.replace(/\[([^\]]+)\]\(([^)]+)\)/g,(m,t,u)=>`<a href="${u}" target="_blank" rel="noopener">${t}</a>`);
    return s;
  }
  while(i<lines.length){
    let line=lines[i];
    let fence=line.match(/^```\s*([\w+-]*)\s*$/);
    if(fence){
      closeList();
      let lang=fence[1],codeLines=[];
      i++;
      while(i<lines.length&&!/^```\s*$/.test(lines[i])){codeLines.push(lines[i]);i++}
      i++;
      let code=codeLines.join('\n');
      html+=`<pre class="code-block"${lang?` data-lang="${lang}"`:''}><code>${highlightCode(code,lang)}</code></pre>`;
      continue;
    }
    let h=line.match(/^(#{1,4})\s+(.*)$/);
    if(h){closeList();html+=`<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`;i++;continue}
    let bq=line.match(/^>\s?(.*)$/);
    if(bq){closeList();html+=`<blockquote>${inline(bq[1])}</blockquote>`;i++;continue}
    let ul=line.match(/^[-*]\s+(.*)$/);
    if(ul){if(listStack!=='ul'){closeList();html+='<ul>';listStack='ul'}html+=`<li>${inline(ul[1])}</li>`;i++;continue}
    let ol=line.match(/^\d+\.\s+(.*)$/);
    if(ol){if(listStack!=='ol'){closeList();html+='<ol>';listStack='ol'}html+=`<li>${inline(ol[1])}</li>`;i++;continue}
    if(line.trim()===''){closeList();i++;continue}
    closeList();
    html+=`<p>${inline(line)}</p>`;
    i++;
  }
  closeList();
  return html;
}
function renderMarkdownPage(md,title){
  let body=renderMarkdownBody(md);
  return `<!doctype html><html><head><meta charset="utf-8"><title>${esc(title||'')}</title><style>
:root{--bg:#fff;--text:#15233b;--muted:#5b6b85;--line:#d9e1ed;--card:#f5f7fb;--accent:#3867f4;--tok-kw:#a626a4;--tok-str:#50a14f;--tok-com:#a0a1a7;--tok-num:#986801;--tok-tag:#e45649;--tok-attr:#986801}
@media (prefers-color-scheme: dark){:root{--bg:#0b1120;--text:#e7edf7;--muted:#95a3bd;--line:#233052;--card:#111a2e;--accent:#5b8cff;--tok-kw:#c678dd;--tok-str:#98c379;--tok-com:#7f848e;--tok-num:#d19a66;--tok-tag:#e06c75;--tok-attr:#e5c07b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;padding:40px 20px}
article{max-width:760px;margin:0 auto}h1,h2,h3,h4{margin-top:1.4em}a{color:var(--accent)}
code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.9em;background:var(--card);padding:.1em .35em;border-radius:4px}
pre.code-block{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;overflow-x:auto}
pre.code-block code{background:none;padding:0;font-size:14px;line-height:1.5}
blockquote{border-left:3px solid var(--accent);margin:1em 0;padding:.4em 1em;color:var(--muted);background:var(--card);border-radius:0 8px 8px 0}
.tok-kw{color:var(--tok-kw);font-weight:600}.tok-str{color:var(--tok-str)}.tok-com{color:var(--tok-com);font-style:italic}.tok-num{color:var(--tok-num)}.tok-tag{color:var(--tok-tag)}.tok-attr{color:var(--tok-attr)}
</style></head><body><article>${body}</article></body></html>`;
}
async function fetchJSON(url,opts){
  let r=await fetch(url,opts);
  let ct=r.headers.get('content-type')||'';
  if(!r.ok||!ct.includes('json'))throw new Error('backend-unavailable');
  return r.json();
}
let chapterTextCache={};
async function chapterText(path){
  if(chapterTextCache[path]!==undefined)return chapterTextCache[path];
  try{
    let raw=await (await fetch(path)).text();
    let text;
    if(/\.md$/i.test(path)){text=raw}
    else{let doc=new DOMParser().parseFromString(raw,'text/html');text=doc.body?doc.body.textContent:''}
    text=text.replace(/\s+/g,' ').trim();
    chapterTextCache[path]=text;
    return text;
  }catch(e){chapterTextCache[path]='';return ''}
}
async function clientSearch(query,limit=8){
  let needle=query.toLowerCase(),hits=[];
  for(let c of chapters){
    let text=await chapterText(c.path);
    let idx=text.toLowerCase().indexOf(needle);
    if(idx>=0){
      let start=Math.max(0,idx-60),end=Math.min(text.length,idx+needle.length+160);
      hits.push({path:c.path,title:c.title,snippet:(start>0?'…':'')+text.slice(start,end)+(end<text.length?'…':'')});
      if(hits.length>=limit)break;
    }
  }
  return hits;
}
</script></body></html>
'''



def is_module(path: Path) -> bool:
    return path.is_dir() and re.match(r"^\d+", path.name) is not None


def item_title(path: Path) -> str:
    return chapter_title(path.name)


def chapter_source_files(base: Path, *, recursive: bool):
    """Chapter-eligible files: exported HTML plus Markdown, sorted together so numbering interleaves naturally."""
    glob = base.rglob if recursive else base.glob
    return sorted(list(glob("*.html")) + list(glob("*.md")))


def asset_groups(root: Path, *, exclude_html: bool = True):
    """Return files grouped by their immediate/relative course folder."""
    buckets = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name in GENERATED_NAMES:
            continue
        if exclude_html and path.suffix.lower() in (".html", ".md"):
            continue
        relative = path.relative_to(root)
        group = str(relative.parent) if str(relative.parent) != "." else "Files in this folder"
        buckets.setdefault(group, []).append({"name": path.name, "path": path.relative_to(ROOT).as_posix()})
    return [{"name": name, "files": files} for name, files in buckets.items()]



def inject_chapter_tools():
    """Give each exported chapter a same-folder sidebar controller, even outside the viewer iframe."""
    ensure_chapter_tools_asset()
    tag = '<script src="course-reader-chapter-tools.js" data-course-reader-tools="1"></script>'
    for path in ROOT.rglob("*.html"):
        if path.name in GENERATED_NAMES:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            if 'data-course-reader-tools="1"' not in content:
                content = re.sub(r'</head\s*>', tag + '</head>', content, count=1, flags=re.I)
                path.write_text(content, encoding="utf-8")
        except OSError:
            continue

def course_data():
    """Create a static manifest: numeric folders are expandable modules."""
    module_dirs = [p for p in sorted(ROOT.iterdir()) if is_module(p)]
    module_paths = {p.resolve() for p in module_dirs}
    chapter_items = []
    order = 1

    # Top-level lesson exports (HTML or Markdown) are chapters outside a module.
    for path in chapter_source_files(ROOT, recursive=False):
        if path.name in GENERATED_NAMES:
            continue
        chapter_items.append({"id": len(chapter_items), "order": order, "title": item_title(path),
                              "path": path.name, "module": None})
        order += 1

    modules = []
    for module in module_dirs:
        entries = []
        for path in chapter_source_files(module, recursive=True):
            entries.append({"id": len(chapter_items), "order": order, "title": item_title(path),
                            "path": path.relative_to(ROOT).as_posix(), "module": module.name})
            chapter_items.append(entries[-1])
            order += 1
        modules.append({"name": module.name, "chapters": entries, "files": asset_groups(module)})

    global_groups = []
    # Plain text files next to course chapters belong to Course files (Markdown is now rendered as a chapter instead).
    top_files = [{"name": p.name, "path": p.name} for p in sorted(ROOT.iterdir())
                 if p.is_file() and p.suffix.lower() == ".txt"]
    if top_files:
        global_groups.append({"name": "Files in this folder", "files": top_files})
    # Non-module folders appear separately in general Course files.
    for folder in sorted(p for p in ROOT.iterdir()
                         if p.is_dir() and not p.name.startswith(".") and p.name != "__pycache__" and p.resolve() not in module_paths):
        files = asset_groups(folder, exclude_html=False)
        if files:
            global_groups.extend([{"name": f"{folder.name} / {g['name']}", "files": g["files"]} for g in files])
    return {"chapters": chapter_items, "modules": modules, "courseFiles": global_groups}



class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.ignored = 0
    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}: self.ignored += 1
    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self.ignored: self.ignored -= 1
    def handle_data(self, data):
        if not self.ignored and data.strip(): self.parts.append(data.strip())


def source_documents():
    for path in list(ROOT.rglob("*.html")) + list(ROOT.rglob("*.md")):
        if path.name in GENERATED_NAMES:
            continue
        try:
            if path.suffix.lower() == ".md":
                text = re.sub(r"\s+", " ", path.read_text(encoding="utf-8", errors="ignore"))
            else:
                parser = TextExtractor(); parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
                text = re.sub(r"\s+", " ", " ".join(parser.parts))
            if text: yield path, item_title(path), text
        except OSError:
            continue


_SEMANTIC_MODEL = None


def semantic_model():
    """Lazily load and cache the multilingual embedding model (loading it per call made every search slow)."""
    global _SEMANTIC_MODEL
    if _SEMANTIC_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _SEMANTIC_MODEL = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _SEMANTIC_MODEL


def build_search_index():
    """Create local SQLite FTS data; optionally include multilingual embeddings."""
    db = ROOT / "course_index.sqlite"
    temp_db = ROOT / "course_index.build.sqlite"
    temp_db.unlink(missing_ok=True)
    con = sqlite3.connect(temp_db)
    con.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY, path TEXT, title TEXT, body TEXT, vector BLOB)")
    con.execute("CREATE VIRTUAL TABLE search USING fts5(path UNINDEXED, title, body)")
    rows = []
    for path, title, body in source_documents():
        words = body.split()
        for i in range(0, len(words), 420):
            chunk = " ".join(words[i:i + 520])
            if chunk: rows.append((path.relative_to(ROOT).as_posix(), title, chunk))
    con.executemany("INSERT INTO chunks(path,title,body) VALUES(?,?,?)", rows)
    con.execute("INSERT INTO search(rowid,path,title,body) SELECT id,path,title,body FROM chunks")
    # The downloaded multilingual model makes a small local RAG semantic; lexical FTS remains a no-dependency fallback.
    try:
        vectors = semantic_model().encode([r[2] for r in rows], normalize_embeddings=True, show_progress_bar=False)
        con.executemany("UPDATE chunks SET vector=? WHERE id=?", [(struct.pack(f"{len(v)}f", *v), i + 1) for i, v in enumerate(vectors)])
        mode = "semantic"
    except Exception:
        mode = "lexical"
    con.commit(); con.close()
    temp_db.replace(db)
    return {"chunks": len(rows), "mode": mode}


def search_course(query, limit=8):
    """Lexical FTS for precise term matches, plus semantic recall over every chunk for cross-language RAG matching.

    Semantic reranking used to run only over the lexical FTS candidates, so a query sharing no words with the
    course text (e.g. asking in a different language) always came back empty even though embeddings existed
    to answer it. Scoring every chunk's vector against the query fixes that; lexical hits are still kept so
    exact-term queries aren't demoted by imperfect embeddings.
    """
    db = ROOT / "course_index.sqlite"
    if not db.exists(): build_search_index()
    con = sqlite3.connect(db)
    try:
        safe = " ".join(re.findall(r"[\wÀ-ÿ]+", query))
        lexical_ids = [r[0] for r in con.execute(
            "SELECT rowid FROM search WHERE search MATCH ? ORDER BY bm25(search) LIMIT 30", (safe or query,))]
    except sqlite3.OperationalError:
        lexical_ids = [r[0] for r in con.execute("SELECT id FROM chunks WHERE body LIKE ? LIMIT 30", (f"%{query}%",))]

    semantic_ids = []
    try:
        q = semantic_model().encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
        scored = []
        for cid, vector in con.execute("SELECT id, vector FROM chunks WHERE vector IS NOT NULL"):
            v = struct.unpack(f"{len(vector)//4}f", vector)
            scored.append((sum(a * b for a, b in zip(q, v)), cid))
        scored.sort(key=lambda x: x[0], reverse=True)
        semantic_ids = [cid for _, cid in scored[:limit * 3]]
    except Exception:
        pass

    seen, ordered_ids = set(), []
    for cid in semantic_ids + lexical_ids:
        if cid not in seen:
            seen.add(cid); ordered_ids.append(cid)

    rows = {}
    if ordered_ids:
        placeholders = ",".join("?" * len(ordered_ids))
        rows = {r[0]: r for r in con.execute(
            f"SELECT id,path,title,body FROM chunks WHERE id IN ({placeholders})", ordered_ids)}
    con.close()
    return [{"path": rows[cid][1], "title": rows[cid][2],
             "snippet": rows[cid][3][:360] + ("…" if len(rows[cid][3]) > 360 else "")}
            for cid in ordered_ids[:limit] if cid in rows]



def settings_path(): return ROOT / ".course-reader-settings.json"
def load_saved_settings():
    try: return json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return {}
def save_settings(payload):
    safe = {k: payload.get(k, "") for k in ("provider", "apiKey", "model", "language", "bg", "width", "font", "size")}
    settings_path().write_text(json.dumps(safe), encoding="utf-8")
    return safe

def provider_request(url, payload=None, headers=None):
    req = urllib.request.Request(url, data=(json.dumps(payload).encode() if payload is not None else None), headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as response: return json.loads(response.read())


def provider_models(cfg):
    provider, key = cfg.get("provider"), cfg.get("apiKey", "")
    if provider == "ollama": return [m["name"] for m in provider_request("http://localhost:11434/api/tags").get("models", [])]
    if provider == "openai": return [m["id"] for m in provider_request("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"}).get("data", [])]
    if provider == "anthropic": return ["claude-sonnet-4-5", "claude-haiku-4-5"]
    return []


def ask_course(cfg):
    question = cfg.get("question", "").strip(); language = cfg.get("language", "the course language")
    context = search_course(question, 6)
    evidence = "\n\n".join(f"SOURCE: {x['title']} ({x['path']})\n{x['snippet']}" for x in context)
    prompt = f"""You are a precise course assistant. Answer in the language used by the learner's question. The course language is {language}. Use ONLY the supplied course excerpts. If evidence is insufficient, say so. Cite the source title in brackets. Do not invent instructions.\n\nCOURSE EXCERPTS:\n{evidence}\n\nLEARNER QUESTION: {question}"""
    provider, model, key = cfg.get("provider"), cfg.get("model"), cfg.get("apiKey", "")
    if not model: raise ValueError("Choose a model in Settings first.")
    if provider == "ollama":
        data = provider_request("http://localhost:11434/api/chat", {"model": model, "stream": False, "messages": [{"role":"user","content":prompt}]})
        return data["message"]["content"]
    if provider == "openai":
        data = provider_request("https://api.openai.com/v1/chat/completions", {"model":model,"messages":[{"role":"user","content":prompt}]}, {"Authorization":f"Bearer {key}","Content-Type":"application/json"})
        return data["choices"][0]["message"]["content"]
    if provider == "anthropic":
        data = provider_request("https://api.anthropic.com/v1/messages", {"model":model,"max_tokens":900,"messages":[{"role":"user","content":prompt}]}, {"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json"})
        return data["content"][0]["text"]
    raise ValueError("Unsupported provider")


class CourseHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", "0")); payload = json.loads(self.rfile.read(size) or "{}")
            if self.path == "/api/models": self.json({"models": provider_models(payload)}); return
            if self.path == "/api/ask": self.json({"answer": ask_course(payload)}); return
            if self.path == "/api/settings": self.json(save_settings(payload)); return
            self.send_error(404)
        except Exception as exc:
            self.json({"error": str(exc)})

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.json({"ok": True}); return
        if parsed.path == "/api/search":
            q = parse_qs(parsed.query).get("q", [""])[0].strip()
            self.json({"results": search_course(q) if q else []}); return
        if parsed.path == "/api/reindex":
            self.json(build_search_index()); return
        if parsed.path == "/api/settings":
            self.json(load_saved_settings()); return
        super().do_GET()
    def json(self, payload):
        data = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)


def bind_server(port, handler, tries=50):
    """Bind the first free port from `port` up; fall back to an OS-assigned one. Binding (not probing) avoids a race."""
    for candidate in [*range(port, port + tries), 0]:
        try:
            return ThreadingHTTPServer(("127.0.0.1", candidate), handler)
        except OSError:
            continue
    raise OSError("No free port available")


def serve(port=8765, page="index.html", open_browser=True):
    build_search_index()
    httpd = bind_server(port, functools.partial(CourseHandler, directory=str(ROOT)))
    url = f"http://localhost:{httpd.server_address[1]}/{quote(page)}"
    print(f"Course Reader + local search: {url}")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    httpd.serve_forever()

def output_path():
    """Never overwrite an existing index; use the folder name as fallback."""
    index = ROOT / "index.html"
    return index if not index.exists() else ROOT / f"{ROOT.name}.html"


def build():
    destination = output_path()
    inject_chapter_tools()
    data = course_data()
    document = APP.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    destination.write_text(document, encoding="utf-8")
    print(f"Created {destination.name}")
    print(f"Embedded {len(data['chapters'])} chapters and {len(data['modules'])} module(s).")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build a standalone local course-reader HTML file")
    parser.add_argument("folder", nargs="?", default=None,
                         help="course folder to build/serve (defaults to this script's own folder; created if missing)")
    parser.add_argument("--force-index", action="store_true", help="replace index.html (normally it is preserved)")
    parser.add_argument("--serve", action="store_true", help="start local backend with course search")
    parser.add_argument("--port", type=int, default=8765, help="preferred port; the next free one is used if it is taken")
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser when serving")
    args = parser.parse_args()
    if args.folder:
        set_root(Path(args.folder).expanduser().resolve())
    elif sys.stdin.isatty():
        preview = course_data()
        if not preview["chapters"] and not preview["modules"]:
            chosen = prompt_for_folder(ROOT)
            if chosen != ROOT:
                set_root(chosen)
    if args.force_index:
        # Explicit opt-in prevents the default safeguard from overwriting index.html.
        inject_chapter_tools()
        target = ROOT / "index.html"
        target.write_text(APP.replace("__DATA__", json.dumps(course_data(), ensure_ascii=False)), encoding="utf-8")
        print(f"Created {target.name}")
        page = target.name
    else:
        page = build().name
    if args.serve:
        serve(args.port, page, not args.no_browser)
