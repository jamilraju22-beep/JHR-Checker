const $ = (s) => document.querySelector(s);
const drop = $('#drop'), input = $('#image'), preview = $('#preview'), form = $('#form'), results = $('#results'), summary = $('#summary'), download = $('#download');
let report;
drop.addEventListener('click', () => input.click());
drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('drag'); });
drop.addEventListener('dragleave', () => drop.classList.remove('drag'));
drop.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('drag'); input.files = e.dataTransfer.files; showFile(); });
input.addEventListener('change', showFile);
function showFile() { const file=input.files[0]; if(!file)return; preview.src=URL.createObjectURL(file); preview.hidden=false; $('#file-name').textContent=file.name; }
form.addEventListener('submit', async e => { e.preventDefault(); const file=input.files[0]; if(!file)return alert('Choose an image first.'); results.innerHTML='<div class="loading">Analyzing image…</div>'; const fd=new FormData(); fd.append('image',file); try { const r=await fetch('/api/check',{method:'POST',body:fd}); if(!r.ok) throw new Error((await r.json()).detail||'Analysis failed'); report=await r.json(); render(report); } catch(err) { results.innerHTML=`<div class="error">${err.message}</div>`; } });
function render(r) { const labels={pass:'PASS',warn:'REVIEW',fail:'FAIL'}; summary.className=`summary ${r.overall}`; summary.innerHTML=`<strong>${labels[r.overall]}</strong><span>${r.width} × ${r.height} · ${r.megapixels} MP · ${r.file_size_mb} MB</span>`; results.innerHTML=r.checks.map(c=>`<article class="check ${c.status}"><div class="dot"></div><div><h3>${c.name.replaceAll('_',' ')}</h3><p>${c.message}</p>${c.auto_fixable?'<small>Potentially fixable</small>':''}</div><b>${labels[c.status]}</b></article>`).join(''); download.hidden=false; }
download.addEventListener('click',()=>{const blob=new Blob([JSON.stringify(report,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='jhr-stock-report.json';a.click();});
