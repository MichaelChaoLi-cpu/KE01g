// Deterministic editable SVG previews. Graphical-abstract PPTX remains pending.
import fs from 'node:fs';
import path from 'node:path';
const out=path.resolve('data/exp/revision-comment-4');fs.mkdirSync(out,{recursive:true});
const C={ink:'#223746',muted:'#546875',blue:'#335F7D',teal:'#237D81',amber:'#AD7022',line:'#9AABB5',pale:'#EFF5F7'};
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;');
function canvas(w,h){return [`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9" fill="${C.line}"/></marker></defs><rect width="100%" height="100%" fill="white"/><g font-family="Arial, Helvetica, sans-serif" fill="${C.ink}">`];}
function text(a,x,y,s,size=22,weight=400,color=C.ink,anchor='start'){a.push(`<text x="${x}" y="${y}" font-size="${size}" font-weight="${weight}" fill="${color}" text-anchor="${anchor}">${esc(s)}</text>`);}
function lines(a,x,y,ss,size=20,color=C.muted,gap=29){ss.forEach((s,i)=>text(a,x,y+i*gap,s,size,400,color));}
function line(a,d,dash=false){a.push(`<path d="${d}" fill="none" stroke="${C.line}" stroke-width="2.5" ${dash?'stroke-dasharray="7 6"':''} marker-end="url(#arrow)"/>`);}
function box(a,x,y,w,h,title,ss,color=C.blue){a.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="5" fill="white" stroke="${color}" stroke-width="1.8"/><path d="M${x+1} ${y+2}H${x+w-1}" stroke="${color}" stroke-width="5"/>`);text(a,x+20,y+36,title,23,700,color);lines(a,x+20,y+67,ss,20,C.muted,28);}
function save(a,n){fs.writeFileSync(path.join(out,n),a.join('\n')+'</g></svg>');}
let a=canvas(1500,880);
a.push('<g transform="translate(0,-100)">');
// One shared input band replaces the intersecting input-distribution arrows.
a.push(`<rect x="55" y="125" width="1390" height="150" rx="5" fill="${C.pale}" stroke="#CCD9E0"/>`);
text(a,75,163,'Emergency records',23,700,C.blue);
lines(a,75,199,['Occupancy and locations','Water and reported deployments'],20);
text(a,550,163,'Population evidence',23,700,C.blue);
lines(a,550,199,['Age–sex census mesh','Disability and long-term-care totals'],20);
text(a,1025,163,'Planning assumptions',23,700,C.blue);
lines(a,1025,199,['Toilet benchmarks and overlap','Support scopes and mobility'],20);
for(const x of [275,750,1225]) line(a,`M${x} 275V325`);
box(a,55,325,440,165,'Municipality screening',['11 municipalities','Benchmark and equity-demand scenarios','Compare functional-support scopes'],C.blue);
box(a,530,325,440,165,'Shelter demand scenarios',['53 matched shelters','Calibration and residential catchments','Synthetic shares × observed occupancy'],C.teal);
box(a,1005,325,440,165,'Requirements and pressure',['Sitewise vs pooled rounding: 53 sites','Operational screen: Yatsushiro only','Reported units, water and occupancy'],C.amber);
line(a,'M275 490V550');
line(a,'M750 490V550');
line(a,'M1225 490V550');
box(a,55,550,440,165,'Municipality verification order',['Rank equity-sensitive demand','Check stability across support scopes','Identify where to collect more evidence'],C.blue);
box(a,530,550,440,165,'Shelter verification shortlist',['Rank across overlap scenarios','Select smallest worst-scenario ranks','Assess scenario sensitivity'],C.teal);
box(a,1005,550,440,165,'Conditional rebalancing',['Mobility bounds and recipient priority','Nearest eligible donors','Nominal road-distance sensitivity'],C.amber);
// A single short side connector carries demand VALUES, not shortlist ranks.
line(a,'M970 465H986V620H1005');
text(a,1025,754,'Priority uses operational tiers and demand values',18,400,C.muted);
line(a,'M1225 770V812');
box(a,1005,812,440,142,'Conditional service packages',['Residual shortfall and unit additions','Women–men designation','Separate accessible parity screen'],C.amber);
a.push('</g>');
save(a,'Figure_methodological_flowchart_review.svg');

a=canvas(1593.6,637.2);
text(a,48,62,'Equity-sensitive shelter sanitation planning',38,700);
a.push(`<path d="M48 87H1544" stroke="${C.blue}" stroke-width="3"/>`);
text(a,48,135,'INCOMPLETE RECORDS',18,700,C.blue);
text(a,48,185,'11 municipalities',29,700);
text(a,48,224,'53 matched shelters',29,700);
lines(a,48,279,['Observed occupancy','+ residential composition','+ administrative support data'],23,C.muted,34);
text(a,48,409,'Female and functional-',23,700,C.teal);
text(a,48,441,'support demand scenarios',23,700,C.teal);
line(a,'M355 319H407');
text(a,440,135,'LOCAL REQUIREMENTS',18,700,C.teal);
text(a,440,169,'Kumamoto',23,700);
text(a,440,199,'Prolonged-stay benchmark units',19,400,C.muted);
// Native vector bars represent exact source-table data, not illustrations.
for(const [x,v,label,color] of [[472,14,'Pooled',C.blue],[620,23,'Sitewise',C.teal]]){
const h=v*7.4;a.push(`<rect x="${x}" y="${410-h}" width="92" height="${h}" fill="${color}"/>`);text(a,x+46,397-h,String(v),32,700,color,'middle');text(a,x+46,443,label,21,400,C.ink,'middle');}
text(a,440,491,'14 to 23 units',27,700,C.teal);
text(a,440,521,'Separate rounding at each shelter',19,400,C.muted);
text(a,800,135,'CONDITIONAL TRANSFERS',18,700,C.amber);
text(a,800,169,'Yatsushiro',23,700);
text(a,800,199,'Residual temporary-toilet-only shortfall',18,400,C.muted);
for(const [x,v,labels,color] of [[817,31,['No','movement'],C.blue],[937,26,['Empty-site','donors'],C.teal],[1057,0,['Full surplus','mobility'],C.amber]]){
const h=v*4.6;a.push(`<rect x="${x}" y="${410-Math.max(2,h)}" width="76" height="${Math.max(2,h)}" fill="${color}"/>`);text(a,x+38,396-h,String(v),32,700,color,'middle');labels.forEach((s,i)=>text(a,x+38,439+i*24,s,18,400,C.ink,'middle'));}
text(a,800,505,'Zero is a scenario bound',24,700,C.amber);
text(a,800,534,'Usable service still requires verification',18,400,C.muted);
line(a,'M1161 319H1202');
text(a,1230,135,'BEFORE DEPLOYMENT',18,700,C.blue);
lines(a,1230,190,['Prioritize female and','functional-support needs'],24,C.teal,34);
lines(a,1230,295,['Check donor usability','and local need','Verify access and','recipient service conditions'],22,C.muted,33);
a.push(`<path d="M48 570H1544" stroke="#DCE5E9" stroke-width="1.5"/>`);
text(a,797,610,'Reported surplus alone does not establish usable service',27,700,C.ink,'middle');
save(a,'Graphical_abstract_review.svg');
console.log(out);
