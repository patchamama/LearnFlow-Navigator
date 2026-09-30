(() => { const KEY='course-reader-sidebar-hidden', ROOT='course-reader-sidebar-hidden'; const hidden=()=>localStorage.getItem(KEY)==='1';
function style(){let s=document.getElementById('course-reader-sidebar-style');if(!s){s=document.createElement('style');s.id='course-reader-sidebar-style';document.head.append(s)}s.textContent=`.course-reader-sidebar-hidden .nav-sidebar,.course-reader-sidebar-hidden .nav-sidebar__content,.course-reader-sidebar-hidden [class*="nav-sidebar"]{display:none!important}.course-reader-sidebar-hidden .course-navigation__sidebar--nav-open .page-wrap{margin-inline-start:0!important}.course-reader-sidebar-hidden .navButtonsFull,.course-reader-sidebar-hidden main{width:100%!important;max-width:none!important;margin-left:0!important}`}
function wire(){let links=[...document.querySelectorAll('.nav-sidebar a[href],[class*="nav-sidebar"] a[href]')];links.forEach((a,i)=>{a.href='#';a.onclick=e=>{e.preventDefault();parent.postMessage({courseReaderNavigateIndex:i},'*')}});document.addEventListener('click',e=>{let b=e.target.closest?.('button.nav-control__button[aria-controls="nav-content-sidebar"]');if(b){e.preventDefault();e.stopPropagation();parent.postMessage({courseReaderAction:'toggleSidebarHidden'},'*')}},true)}
function hide(){style();document.documentElement.classList.add(ROOT);document.querySelectorAll('.nav-sidebar,[class*="nav-sidebar"]').forEach(n=>{if(n.parentElement)n.parentElement.style.setProperty('display','none','important')});wire()}
function set(h){localStorage.setItem(KEY,h?'1':'0');if(h){hide();[300,1200,2400].forEach(ms=>setTimeout(()=>hidden()&&hide(),ms))}else if(document.documentElement.classList.contains(ROOT))location.reload()}
window.addEventListener('message',e=>{if(e.data?.courseReaderAction==='setSidebarHidden')set(!!e.data.hidden)});wire();if(hidden())hide();})();
(() => {
function esc(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
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
function styleTag(){
  let s=document.getElementById('course-reader-code-style');
  if(!s){s=document.createElement('style');s.id='course-reader-code-style';document.head.append(s);
    s.textContent='.tok-kw{color:#a626a4;font-weight:600}.tok-str{color:#50a14f}.tok-com{color:#a0a1a7;font-style:italic}.tok-num{color:#986801}.tok-tag{color:#e45649}.tok-attr{color:#986801}@media (prefers-color-scheme: dark){.tok-kw{color:#c678dd}.tok-str{color:#98c379}.tok-com{color:#7f848e}.tok-num{color:#d19a66}.tok-tag{color:#e06c75}.tok-attr{color:#e5c07b}}';
  }
}
function highlightAll(){
  let blocks=document.querySelectorAll('pre code[class*="language-"]:not([data-hl]), pre[data-lang] code:not([data-hl])');
  if(!blocks.length)return;
  styleTag();
  blocks.forEach(code=>{
    let pre=code.closest('pre');
    let lang=((pre&&pre.dataset.lang)||(code.className.match(/language-(\w+)/)||[])[1]||'').toLowerCase();
    code.innerHTML=highlightCode(code.textContent,lang);
    code.setAttribute('data-hl','1');
  });
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',highlightAll);else highlightAll();
})();
