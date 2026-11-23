export function el(tag, attrs={}, children=[]) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key,value]) => {
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2).toLowerCase(), value);
    else node.setAttribute(key,value);
  });
  children.filter(child => child !== null && child !== undefined && child !== false).forEach(child => node.append(child instanceof Node ? child : document.createTextNode(child)));
  return node;
}
export function table(headers, rows, empty='暂无记录') {
  const wrap = el('div',{class:'table-wrap'});
  const t = el('table');
  t.append(el('thead',{},[el('tr',{},headers.map(h=>el('th',{text:h})))]));
  const body = el('tbody');
  if (!rows.length) body.append(el('tr',{},[el('td',{colSpan:headers.length,class:'empty',text:empty})]));
  rows.forEach(row=>body.append(el('tr',{},row.map(cell=>el('td',{text:String(cell ?? '—')})))));
  t.append(body); wrap.append(t); return wrap;
}
export function toast(message, kind='info') { const box = el('div',{class:`toast ${kind}`,text:message}); document.body.append(box); setTimeout(()=>box.remove(),3200); }
export function badge(text, kind='neutral'){ return el('span',{class:`badge ${kind}`,text}); }
