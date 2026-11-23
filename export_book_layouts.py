"""Regenerate scorer-generated reference lines for browser wrapping differences.

Uses the shared paginator, packaged pinned-font subsets and local Chromium.
Run: python export_book_layouts.py
"""
from pathlib import Path
import hashlib
import json
import re
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
FONT_DIR = ROOT / 'assets' / 'fonts'

EXPORT_JS = r'''async ({rows,chains})=>{
  const versions={},failures=[];
  const measure=document.createElement('div');
  measure.className='lp-copy';
  Object.assign(measure.style,{position:'absolute',left:'-100000px',top:'0',width:'365px',visibility:'hidden'});
  document.body.append(measure);
  let pageCount=0,lineCount=0,paragraphCount=0;
  const nonspace=s=>s.replace(/\s/g,'');
  const normalize=s=>s.replace(/[ \t\r\n\f]+/g,' ').replace(/^ +| +$/g,'');
  try {
    for(const row of rows){
      const family=chains[row.lang].map(f=>JSON.stringify(f)).join(',');
      const layout=await LangPrintRenderer.paginate({text:row.text,lang:row.lang,fontFamily:family});
      if(Math.abs(layout.occupied_pages-row.occupied_pages)>1e-10)throw new Error(`Stored score mismatch ${row.idx}/${row.lang}`);
      measure.style.fontFamily=family;measure.lang=row.lang;measure.dir=row.lang==='ar'?'rtl':'ltr';
      const exported=[];
      for(const fragment of layout.pages){
        measure.replaceChildren();
        const ps=fragment.paragraphs.map(text=>{const p=document.createElement('p');p.textContent=normalize(text);measure.append(p);return p;});
        const resultParagraphs=[];
        for(const p of ps){
          const text=p.textContent,node=p.firstChild;
          const boundaries=[0];
          for(const segment of new Intl.Segmenter(row.lang,{granularity:'grapheme'}).segment(text))boundaries.push(segment.index+segment.segment.length);
          const range=document.createRange(),lines=[];
          let start=0;
          while(start<boundaries.length-1){
            while(start<boundaries.length-1&&/^ +$/.test(text.slice(boundaries[start],boundaries[start+1])))start++;
            if(start>=boundaries.length-1)break;
            range.setStart(node,boundaries[start]);range.setEnd(node,boundaries[start+1]);
            const firstRects=[...range.getClientRects()].filter(r=>r.width>0.01);
            const firstTop=firstRects.length?Math.min(...firstRects.map(r=>r.top)):range.getBoundingClientRect().top;
            // Em boxes from fallback fonts have slightly different ascents on
            // the same visual row; half a line distinguishes rows safely.
            const limit=firstTop+layout.lineHeight*0.5;
            let lo=start+1,hi=boundaries.length-1;
            while(lo<hi){
              const mid=Math.ceil((lo+hi)/2);
              range.setStart(node,boundaries[start]);range.setEnd(node,boundaries[mid]);
              const rects=[...range.getClientRects()].filter(r=>r.width>0.01);
              const fits=rects.every(r=>r.top<=limit);
              if(fits)lo=mid;else hi=mid-1;
            }
            const line=text.slice(boundaries[start],boundaries[lo]).replace(/ +$/g,'');
            if(!line)throw new Error(`Empty line ${row.idx}/${row.lang}`);
            lines.push(line);start=lo;
          }
          const expected=Math.round(p.getBoundingClientRect().height/layout.lineHeight);
          if(lines.length!==expected)throw new Error(`Line extraction mismatch ${row.idx}/${row.lang}: ${lines.length} vs ${expected}; ${JSON.stringify(lines)}`);
          if(nonspace(lines.join(''))!==nonspace(text))throw new Error(`Paragraph text mismatch ${row.idx}/${row.lang}`);
          resultParagraphs.push({lines});paragraphCount++;
        }
        const extractedLines=resultParagraphs.reduce((n,p)=>n+p.lines.length,0);
        if(extractedLines!==fragment.lines)throw new Error(`Page line mismatch ${row.idx}/${row.lang}`);
        // Prove that explicit line breaks preserve reference page height.
        for(let i=0;i<ps.length;i++){
          ps[i].style.whiteSpace='pre';ps[i].textContent=resultParagraphs[i].lines.join('\n');
        }
        const preLines=Math.round(measure.getBoundingClientRect().height/layout.lineHeight);
        if(preLines!==fragment.lines||measure.scrollWidth>measure.clientWidth+1){
          const detail=[];
          for(let i=0;i<ps.length;i++){
            let offset=0;const range=document.createRange();
            for(const line of resultParagraphs[i].lines){range.setStart(ps[i].firstChild,offset);range.setEnd(ps[i].firstChild,offset+line.length);detail.push({line,width:range.getBoundingClientRect().width,indent:offset===0?getComputedStyle(ps[i]).textIndent:'0'});offset+=line.length+1;}
          }
          throw new Error(`Canonical layout overflow ${row.idx}/${row.lang}: ${preLines}/${fragment.lines}, width ${measure.scrollWidth}: ${JSON.stringify(detail)}`);
        }
        exported.push({lines:fragment.lines,paragraphs:resultParagraphs});
        pageCount++;lineCount+=fragment.lines;
      }
      if(nonspace(exported.flatMap(p=>p.paragraphs.flatMap(p=>p.lines)).join(''))!==nonspace(row.text))throw new Error(`Source text mismatch ${row.idx}/${row.lang}`);
      (versions[row.lang]??={})[String(row.idx)]={occupied_pages:row.occupied_pages,pages:exported};
    }
    return {versions,report:{records:rows.length,pages:pageCount,lines:lineCount,paragraphs:paragraphCount,failures}};
  } finally {measure.remove();}
}'''

def main():
    html_path = ROOT / 'index.html'
    html = html_path.read_text()
    match = re.search(r'<script id="book-data" type="application/json">(.*?)</script>', html, re.S)
    if not match:
        raise RuntimeError('The static book data was not found.')
    book = json.loads(match.group(1))
    raw = (ROOT / 'data/results.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != book['sourceSha256']:
        raise RuntimeError('The corpus changed; update the embedded book data before regenerating references.')
    requested = {(lang, passage['idx']) for passage in book['passages']
                 for lang, version in passage['versions'].items() if 'referenceLayout' in version}
    rows = [row for row in json.loads(raw) if (row['lang'], row['idx']) in requested]
    inventory = json.loads((FONT_DIR / 'font-inventory.json').read_text())
    fonts = [{'family': f['family'], 'url': 'https://langprint.invalid/' + f['file']} for f in inventory['fonts']]
    files = {f['url']: FONT_DIR / Path(f['url']).name for f in fonts}
    for font in inventory['fonts']:
        if hashlib.sha256((FONT_DIR / font['file']).read_bytes()).hexdigest() != font['sha256']:
            raise RuntimeError('A packaged font does not match its inventory.')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(viewport={'width': 930, 'height': 624}, locale='en-US', device_scale_factor=1, offline=True)
            def serve(route):
                file = files.get(route.request.url)
                if file:
                    route.fulfill(path=file, content_type='font/woff', headers={'Access-Control-Allow-Origin': '*'})
                else:
                    route.abort()
            context.route('**/*', serve)
            page = context.new_page()
            page.set_content('<!doctype html><meta charset="utf-8"><style>body{margin:0}</style>')
            page.add_script_tag(content=(ROOT / 'renderer.js').read_text())
            page.evaluate("""async fonts => {
                for (const font of fonts) {
                    const face = new FontFace(font.family, `url("${font.url}")`, {weight: '400'});
                    document.fonts.add(await face.load());
                }
                await document.fonts.ready;
            }""", fonts)
            result = page.evaluate(EXPORT_JS, {'rows': rows, 'chains': inventory['font_family_chains']})
            for passage in book['passages']:
                for lang, version in passage['versions'].items():
                    reference = result['versions'].get(lang, {}).get(str(passage['idx']))
                    if reference:
                        version['referenceLayout'] = reference
            payload = json.dumps(book, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
            updated = html[:match.start(1)] + payload + html[match.end(1):]
            if html_path.read_text() != html:
                raise RuntimeError('The HTML changed during generation; no data was overwritten.')
            html_path.write_text(updated)
            result['report'].update(source_sha256=book['sourceSha256'], chromium_version=browser.version)
            (ROOT / 'data/book-reference-report.json').write_text(json.dumps(result['report'], ensure_ascii=False, indent=2) + '\n')
            print(f"Regenerated {len(rows)} reference layouts.")
        finally:
            browser.close()

if __name__ == '__main__':
    main()
