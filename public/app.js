const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let adminData;
let user, data, page='dashboard', queue=[], position=0, result=null;
const icons=['◈','◎','♡','⌁','⌘'];
const descriptions=['How we encode, store and retrieve.','How other people shape our behaviour.','The bonds that shape relationships.','The biology behind our behaviour.','How psychologists investigate ideas.'];
async function api(path, body){const r=await fetch('/api/'+path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const d=await r.json();if(!r.ok)throw Error(d.error||'Something went wrong.');return d;}
function toast(s){$('#toast').textContent=s;$('#toast').classList.add('show');setTimeout(()=>$('#toast').classList.remove('show'),4000);}
async function refresh(){data=await api('data');if(user.role==='admin')adminData=await api('admin');}
function topicStats(topic){const qs=data.questions.filter(q=>q.topic===topic);const latest=qs.map(q=>data.attempts.find(a=>a.question_id===q.id)).filter(Boolean);return {count:latest.length,score:latest.length?Math.round(latest.reduce((n,a)=>n+a.score,0)/latest.length*100):0,total:qs.length};}
function status(s){return !s.count?'Not assessed':s.score<50?'Needs revision':s.score<80?'Developing':'Looking stronger';}
function topics(){return [...new Set(data.questions.map(q=>q.topic))];}
function nav(){return `<aside><a class="brand" href="#" data-page="dashboard"><span class="logo">r.</span> recall<span class="brand-dot">✦</span></a><div class="side-label">YOUR STUDY SPACE</div><nav>${[['dashboard','◫','Overview'],['practice','◈','Practice'],['portfolio','▥','My portfolio'],['history','◷','History']].map(([id,icon,label])=>`<button data-page="${id}" class="nav ${page===id?'active':''}"><span>${icon}</span>${label}</button>`).join('')}</nav><div class="side-note"><span>✧</span><b>A little recall.<br>A lot of progress.</b><p>Start with what you remember. Build from there.</p></div><div class="profile"><span class="avatar">${esc(user.name[0].toUpperCase())}</span><div><b>${esc(user.name)}</b><small>Psychology student</small></div><button id="logout" aria-label="Log out" title="Log out">↗</button></div></aside>`;}
function shell(content){$('#app').innerHTML=nav()+`<main><header><span>YOUR LEARNING, IN FOCUS</span><span class="local-pill">● Local study space</span></header>${content}<footer>Built for active recall · Broad A-level Psychology concepts · Progress is provisional</footer></main>`;document.querySelectorAll('[data-page]').forEach(b=>b.onclick=e=>{e.preventDefault();page=b.dataset.page;render();});$('#logout').onclick=async()=>{await api('logout',{});user=null;auth();};document.querySelectorAll('[data-topic]').forEach(b=>b.onclick=()=>start(b.dataset.topic));if(page==='dashboard'||page==='portfolio')showLearningPlan();}
function cards(){return `<div class="topic-grid">${topics().map((t,i)=>{let s=topicStats(t);return `<button class="topic-card" data-topic="${esc(t)}"><div class="card-top"><span class="topic-icon color-${i}">${icons[i]}</span><span class="arrow">↗</span></div><h3>${t}</h3><p>${descriptions[i]}</p><div class="progress"><i style="width:${s.count/s.total*100}%"></i></div><div class="card-foot"><span>${s.count} / ${s.total} questions explored</span><b>${status(s)}</b></div></button>`;}).join('')}</div>`;}
function render(){result=null;if(user.role==='admin'){adminDashboard();return;}if(page==='practice'){shell(`<div class="heading"><span class="eyebrow">MAKE IT STICK</span><h1>What will you recall today?</h1><p>Choose a topic. Three short questions. Answer from memory, then reflect.</p></div>${cards()}<div class="info">✧ Put your notes aside. It’s okay to leave a gap — that’s how you find your next step.</div>`);return;}
if(page==='portfolio'){portfolio();return;}if(page==='history'){history();return;}
const assessed=data.questions.filter(q=>data.attempts.some(a=>a.question_id===q.id)).length;
const weak=topics().filter(t=>topicStats(t).count).sort((a,b)=>topicStats(a).score-topicStats(b).score);
shell(`<div class="heading"><span class="eyebrow">A FRESH CHANCE TO LEARN</span><h1>Your next breakthrough<br>starts with recall<span class="teal">.</span></h1><p>Welcome${data.attempts.length?' back':''}, ${esc(user.name.split(' ')[0])}. Let’s turn what you remember into a clearer revision plan.</p></div><section class="hero"><div><span class="eyebrow">SMALL SESSIONS. CLEARER THINKING.</span><h2>Find your gaps.<br>Build your confidence.</h2><p>A few questions today. A better idea of<br>what to focus on tomorrow.</p><button class="primary light" data-topic="${esc(weak[0]||'Memory')}">Start a retrieval session <span>↗</span></button><small>3 questions · Go at your own pace</small></div><div class="orbit" aria-hidden="true"><div class="orbit-ring ring1"></div><div class="orbit-ring ring2"></div><div class="orbit-ring ring3"></div><div class="orbit-center">✦</div><span class="orbit-tag tag1">Retrieve</span><span class="orbit-tag tag2">Reflect</span><span class="orbit-tag tag3">Remember</span></div></section><div class="stats"><article><span>Questions explored</span><strong>${assessed}<small> / ${data.questions.length}</small></strong><p>Every answer is a starting point</p></article><article><span>Retrieval attempts</span><strong>${data.attempts.length}</strong><p>Your practice, recorded over time</p></article><article><span>Your next focus</span><strong class="focus-text">${weak[0]||'Start exploring'}</strong><p>${weak.length?'Based on your latest answer points':'Take a session to find your gaps'}</p></article></div><div class="section-title"><h2>Explore your topics</h2><span>Board-independent foundations</span></div>${cards()}`);}
function start(topic){queue=data.questions.filter(q=>q.topic===topic);position=0;page='practice';question();}
function question(){result=null;const q=queue[position];shell(`<div class="session-top"><button class="text-button" id="exit">← Back to topics</button><span>${q.topic} <b> ${position+1} / ${queue.length}</b></span></div><div class="session-progress"><i style="width:${position/queue.length*100}%"></i></div><section class="question-panel"><span class="eyebrow">RETRIEVE · ${q.subtopic.toUpperCase()}</span><h1>${q.prompt}</h1><p>Close your notes and explain it in your own words.</p><form id="answer-form"><label for="answer">Your answer</label><textarea id="answer" maxlength="5000" placeholder="Start with what you remember…" rows="7"></textarea><fieldset><legend>How confident do you feel?</legend><div class="confidence">${['Not sure yet','Somewhat sure','Confident'].map((v,i)=>`<label><input type="radio" name="confidence" value="${i+1}" ${i===1?'checked':''}><span>${v}</span></label>`).join('')}</div></fieldset><div class="form-actions"><button class="text-button" type="button" id="skip">I don’t know yet</button><button class="primary" type="submit">Check my answer →</button></div></form></section>`);$('#exit').onclick=()=>{page='practice';render();};$('#skip').onclick=()=>submitAnswer('');$('#answer-form').onsubmit=e=>{e.preventDefault();if(!$('#answer').value.trim())return toast('Write an answer, or choose “I don’t know yet”.');submitAnswer($('#answer').value);};}
async function submitAnswer(answer){const confidence=Number(document.querySelector('input[name=confidence]:checked').value);document.querySelectorAll('.form-actions button').forEach(b=>b.disabled=true);try{result=await api('answer',{question_id:queue[position].id,answer,confidence});await refresh();feedback(answer);}catch(e){toast(e.message);document.querySelectorAll('.form-actions button').forEach(b=>b.disabled=false);}}
function feedback(answer) {
    const r = result;
    const q = queue[position];
    shell(`<div class="heading"><span class="eyebrow">REFLECT · ${q.topic.toUpperCase()}</span>
        <h1>Think through the missing pieces.</h1><p>Your answer is saved. Use a hint to prepare your next attempt.</p></div>
        <section class="feedback-panel"><h3>${q.prompt}</h3><blockquote>${esc(answer || 'I don’t know yet.')}</blockquote>
        <div class="info">Each point checks a relationship between ideas. These rule-based marks are provisional and can miss valid paraphrases. ${r.needs_review ? 'Your answer is queued for teacher review.' : 'No answer was submitted.'}</div>
        <h3>Point-by-point feedback</h3>
        ${r.hints.map((hint, i) => `<div class="rubric-point"><span class="badge ${r.matched[i] ? '' : 'amber'}">Point ${i + 1} · ${r.matched[i] ? 'Evidence found' : 'Not yet demonstrated'}</span>
            ${r.matched[i] ? `<p>Your evidence: “${esc(r.evidence[i])}”</p>` : `<p class="hint">${esc(hint)}</p>`}</div>`).join('')}
        <p class="muted">Your teacher has the final say. Weak questions are scheduled for a fresh attempt in three days.</p>
        <div class="form-actions"><button class="text-button" id="retry-hint">Try this question again</button>
        <button class="primary" id="next">${position + 1 === queue.length ? 'Finish & view portfolio' : 'Continue'} →</button></div></section>`);
    $('#retry-hint').onclick = () => question();
    $('#next').onclick = () => {
        position++;
        if (position < queue.length) question();
        else { page = 'portfolio'; render(); toast('Practice saved. Your next steps are ready.'); }
    };
}
function portfolio(){shell(`<div class="heading"><span class="eyebrow">SEE THE BIGGER PICTURE</span><h1>Your knowledge, taking shape.</h1><p>A living record of what you’ve recalled, and where to go next.</p></div><div class="info">Scores show answer points in your latest attempt per question. Same-day repeats are practice, and untested questions remain unknown. Revisit later to check retention.</div><div class="portfolio-list">${topics().map((t,i)=>{const s=topicStats(t);return `<section class="portfolio-card"><div class="section-title"><div class="topic-heading"><span class="topic-icon color-${i}">${icons[i]}</span><div><h2>${t}</h2><span class="badge ${s.count&&s.score<50?'amber':''}">${status(s)}</span></div></div><button class="secondary" data-topic="${t}">Practise topic ↗</button></div>${data.questions.filter(q=>q.topic===t).map(q=>{const aa=data.attempts.filter(a=>a.question_id===q.id);const a=aa[0];return `<div class="subtopic"><div><b>${q.subtopic}</b><small>${a?`${aa.length} attempt${aa.length===1?'':'s'} · ${new Date(a.created*1000).toLocaleDateString()} · ${markLabel(a)}`:'Ready for your first attempt'}</small></div><div class="mini-progress"><i style="width:${a?a.score*100:0}%"></i></div><strong>${a?Math.round(a.score*100)+'%':'—'}</strong></div>`;}).join('')}</section>`;}).join('')}</div>`);}
function history(){shell(`<div class="heading"><span class="eyebrow">EVERY ATTEMPT COUNTS</span><h1>Your practice history.</h1><p>Look back at your answers and see how your thinking changes.</p></div>${data.attempts.length?`<div class="history-list">${data.attempts.map(a=>{const q=data.questions.find(q=>q.id===a.question_id);return `<details><summary><div><span class="eyebrow">${q.topic}</span><h3>${q.subtopic}</h3><small>${new Date(a.created*1000).toLocaleString()} · ${markLabel(a)}</small></div><strong>${Math.round(a.score*100)}% <span>⌄</span></strong></summary><div class="history-answer"><b>${q.prompt}</b><p>${esc(a.answer||'I don’t know yet.')}</p>${teacherFeedback(a)}<small>Confidence before feedback: ${['','Not sure yet','Somewhat sure','Confident'][a.confidence]}</small></div></details>`;}).join('')}</div>`:`<div class="empty"><span>◷</span><h2>Your first attempt starts the story.</h2><p>Try a short retrieval session to start your history.</p><button class="primary" data-topic="Memory">Start with Memory →</button></div>`}`);}
function auth(register=false){$('#app').innerHTML=`<div class="auth-layout"><section class="auth-brand"><a class="brand"><span class="logo">r.</span> recall</a><div><span class="eyebrow">YOUR PSYCHOLOGY STUDY SPACE</span><h1>Less rereading.<br>More remembering<span>✦</span></h1><p>Find the gaps. Connect the ideas.<br>Make your next revision session count.</p><div class="auth-steps"><span>01 &nbsp; Retrieve</span><span>02 &nbsp; Reflect</span><span>03 &nbsp; Grow</span></div></div><small>Built around broad A-level Psychology foundations.</small></section><section class="auth-form"><div class="auth-box"><span class="eyebrow">A LITTLE PRACTICE GOES A LONG WAY</span><h2>${register?'Make room for progress.':'Welcome to your study space.'}</h2><p>${register?'Create your account to keep your learning in one place.':'Log in to pick up where you left off.'}</p><form id="auth-form">${register?'<label for="name">Your name</label><input id="name" autocomplete="given-name" maxlength="60" required placeholder="Alex">':''}<label for="email">Email address</label><input id="email" type="email" autocomplete="username" required placeholder="you@example.com"><label for="password">Password</label><input id="password" type="password" autocomplete="${register?'new-password':'current-password'}" minlength="${register?10:1}" maxlength="128" required placeholder="At least 10 characters"><p class="error" id="auth-error" role="alert"></p><button class="primary" type="submit">${register?'Create account':'Log in'} <span>→</span></button></form><p class="auth-switch">${register?'Already have an account?':'New here?'} <button id="switch">${register?'Log in':'Create an account'}</button></p><small class="local-note">● Saved to your account on this server. Use an email you can remember; email verification is not enabled.</small></div></section></div>`;$('#switch').onclick=()=>auth(!register);$('#auth-form').onsubmit=async e=>{e.preventDefault();const b=$('#auth-form button');b.disabled=true;try{await api(register?'register':'login',{name:$('#name')?.value,email:$('#email').value,password:$('#password').value});user=await api('me');await refresh();page='dashboard';render();}catch(e){$('#auth-error').textContent=e.message;b.disabled=false;}};}
(async()=>{try{user=await api('me');if(user){await refresh();render();}else auth();}catch(e){$('#app').textContent='Unable to connect to the local server. Refresh to retry.';}})();

function studentSummary(student) {
    const attempts = adminData.attempts.filter(a => a.user_id === student.id);
    const latest = new Map();
    attempts.forEach(a => {
        if (!latest.has(a.question_id)) latest.set(a.question_id, a);
    });
    const mean = rows => rows.length ? Math.round(rows.reduce((sum, a) => sum + a.score, 0) / rows.length * 100) : null;
    const current = mean([...latest.values()]);
    return {attempts, latest, current, change: student.learning.change};
}

function adminDashboard() {
    const students = adminData.students;
    const active = students.filter(s => studentSummary(s).attempts.length).length;
    $('#app').innerHTML = `
        <aside>
            <a class="brand"><span class="logo">r.</span> recall</a>
            <div class="side-label">ADMIN WORKSPACE</div>
            <nav><button class="nav active">◫ &nbsp; Student overview</button></nav>
            <div class="side-note"><span>✧</span><b>See the progress.<br>Support the next step.</b><p>Explore each student’s learning evidence.</p></div>
            <div class="profile"><span class="avatar">A</span><div><b>Admin</b><small>Administrator</small></div><button id="logout" aria-label="Log out" title="Log out">↗</button></div>
        </aside>
        <main>
            <header><span>YOUR CLASS, IN FOCUS</span><span class="local-pill">● Admin access</span></header>
            <div class="heading"><span class="eyebrow">LEARNING AT A GLANCE</span><h1>Every student. Every step.</h1><p>See who is practising, where understanding is growing and which topics need attention.</p></div>
            <div class="stats">
                <article><span>Registered students</span><strong>${students.length}</strong><p>All student accounts</p></article>
                <article><span>Students practising</span><strong>${active}</strong><p>At least one recorded answer</p></article>
                <article><span>Retrieval attempts</span><strong>${adminData.attempts.length}</strong><p>Across all students and topics</p></article>
            </div>
            <div class="info">Scores reflect latest answer-point coverage on attempted questions. Teacher-reviewed marks are labelled. Change compares first and latest attempts at least three days apart on the same questions, in percentage points. A dash means no spaced comparison yet. These are provisional learning indicators.</div>
            <div class="section-title"><h2>Student progress</h2><button class="secondary" id="refresh-admin">Refresh results ↻</button></div>
            <label for="student-search">Find a student</label><input id="student-search" type="search" placeholder="Search by name or email">
            <div id="student-list"></div><div id="teacher-review"></div>
            <footer>Admin overview · Unassessed questions are excluded from scores</footer>
        </main>`;
    $('#logout').onclick = async () => {
        try { await api('logout', {}); user = null; adminData = null; auth(); }
        catch (e) { toast(e.message); }
    };
    $('#refresh-admin').onclick = async () => {
        try { await refresh(); adminDashboard(); toast('Student results updated.'); }
        catch (e) { toast(e.message); }
    };
    $('#student-search').oninput = () => renderStudents($('#student-search').value);
    renderStudents('');
    renderReviewQueue();
}

function renderStudents(query) {
    const students = adminData.students.filter(s => `${s.name} ${s.email}`.toLowerCase().includes(query.toLowerCase()));
    $('#student-list').innerHTML = students.length ? students.map(student => {
        const summary = studentSummary(student);
        const change = summary.change === null ? '—' : `${summary.change > 0 ? '+' : ''}${summary.change} pp`;
        const topicRows = topics().map(topic => {
            const questions = data.questions.filter(q => q.topic === topic);
            const answers = questions.map(q => summary.latest.get(q.id)).filter(Boolean);
            const score = answers.length ? Math.round(answers.reduce((n, a) => n + a.score, 0) / answers.length * 100) : null;
            return `<div class="subtopic"><div><b>${topic}</b><small>${answers.length} / ${questions.length} questions explored · ${status({count:answers.length, score})}</small></div><div class="mini-progress"><i style="width:${score || 0}%"></i></div><strong>${score === null ? '—' : score + '%'}</strong></div>`;
        }).join('');
        const historyRows = summary.attempts.map(a => {
            const question = data.questions.find(q => q.id === a.question_id);
            return `<details><summary><div><span class="eyebrow">${question.topic}</span><h3>${question.subtopic}</h3><small>${new Date(a.created * 1000).toLocaleString()} · ${markLabel(a)}</small></div><strong>${Math.round(a.score * 100)}%</strong></summary><div class="history-answer"><b>${question.prompt}</b><p>${esc(a.answer || 'I don’t know yet.')}</p>${teacherFeedback(a)}<small>Confidence: ${['', 'Not sure yet', 'Somewhat sure', 'Confident'][a.confidence]}</small></div></details>`;
        }).join('');
        return `<details class="student-card"><summary><div><h3>${esc(student.name)}</h3><small>${esc(student.email)}</small></div><div class="student-metrics"><span><b>${summary.current === null ? '—' : summary.current + '%'}</b><small>Latest score</small></span><span><b>${summary.latest.size} / ${data.questions.length}</b><small>Explored</small></span><span><b>${change}</b><small>Spaced change</small></span><span class="arrow">⌄</span></div></summary><div class="student-detail"><p>${summary.attempts.length} retrieval attempts · Last active ${summary.attempts.length ? new Date(summary.attempts[0].created * 1000).toLocaleString() : '—'}</p><div class="info">${student.learning.inactive ? 'Follow up · No activity in the last seven days (or no answers yet). ' : ''}${student.learning.calibration.filter(c => c.kind === 'Overconfident').length} confidence/score mismatches indicating possible overconfidence · ${student.learning.schedule.filter(r => r.overdue).length} re-attempts due.</div><h3>Topic breakdown</h3>${topicRows}<h3>Answer history</h3><div class="history-list">${historyRows || '<p>No practice recorded yet.</p>'}</div></div></details>`;
    }).join('') : '<div class="empty"><h2>No students to show yet.</h2><p>Student accounts appear here after registration. Try another search if you have filtered the list.</p></div>';
}

function markLabel(attempt) {
    if (attempt.teacher_id) return 'Teacher reviewed';
    if (attempt.marking_version === 'rubric-v2') return 'Rubric check · provisional';
    return attempt.reviewed ? 'Legacy self-review' : 'Legacy keyword check';
}

function teacherFeedback(attempt) {
    return attempt.teacher_note ? `<div class="info"><b>Teacher feedback</b><p>${esc(attempt.teacher_note)}</p></div>` : '';
}

function showLearningPlan() {
    const learning = data.learning;
    if (!learning) return;
    const panel = document.createElement('section');
    panel.className = 'learning-plan';
    const due = learning.schedule.filter(item => item.overdue);
    panel.innerHTML = `<div class="section-title"><div><span class="eyebrow">CLOSE THE LEARNING LOOP</span><h2>Your next steps</h2></div><span>${due.length} re-attempts due</span></div>
        <p class="muted">Weak questions are scheduled three days after the latest attempt. Your teacher’s marks update these priorities.</p>
        ${learning.schedule.length ? learning.schedule.map(item => `<div class="retest-row"><div><b>${esc(item.subtopic)}</b><small>${esc(item.topic)} · ${item.overdue ? 'Ready to revisit' : 'Revisit ' + new Date(item.due * 1000).toLocaleDateString()} · ${Math.round(item.score * 100)}% provisional unless teacher reviewed</small></div><button class="secondary" data-retest="${item.question_id}">${item.overdue ? 'Re-attempt' : 'Practise early'} ↗</button></div>`).join('') : '<p>Complete some retrieval practice to build your next-step plan.</p>'}
        <details class="learning-details"><summary>Confidence and accuracy</summary><p class="muted">Confidence ratings are mapped to 25%, 60% and 90%. Gaps of at least 30 percentage points are highlighted. This is a guide for reflection.</p>
        ${learning.calibration.length ? learning.calibration.map(c => `<div class="retest-row"><div><b>${esc(c.subtopic)}</b><small>${c.kind} · ${['', 'Not sure yet', 'Somewhat sure', 'Confident'][c.confidence]} before answering · ${Math.round(c.score * 100)}% answer points${c.provisional ? ' · provisional mark' : ''}</small></div></div>`).join('') : '<p>No large confidence/score mismatches found in your latest answers.</p>'}</details>
        <details class="learning-details"><summary>Progress after spaced practice</summary>
        ${learning.comparisons.length ? learning.comparisons.map(c => `<div class="retest-row"><div><b>${esc(c.subtopic)}</b><small>First ${Math.round(c.first * 100)}% → latest spaced ${Math.round(c.latest * 100)}%${c.provisional ? ' · provisional marks' : ' · teacher reviewed'}</small></div><strong>${c.change > 0 ? '+' : ''}${c.change} pp</strong></div>`).join('') : '<p>No spaced comparison yet. Return after three days and try a question again. Same-day practice is kept in your history.</p>'}</details>`;
    const heading = document.querySelector('main .heading');
    heading.insertAdjacentElement('afterend', panel);
    panel.querySelectorAll('[data-retest]').forEach(button => {
        button.onclick = () => {
            queue = [data.questions.find(q => q.id === Number(button.dataset.retest))];
            position = 0;
            page = 'practice';
            question();
        };
    });
}

function renderReviewQueue() {
    const pending = adminData.attempts.filter(a => a.needs_review);
    const container = $('#teacher-review');
    container.innerHTML = `<div class="section-title"><h2>Teacher review queue</h2><span>${pending.length} awaiting review</span></div>
        <p class="muted">Conservative automated checks may miss paraphrases or accept an incorrect relationship. Confirm each original practice-rubric point. Legacy results retain their original marks until you review them.</p>
        ${pending.length ? pending.map(attempt => {
            const student = adminData.students.find(s => s.id === attempt.user_id);
            const question = data.questions.find(q => q.id === attempt.question_id);
            const rubric = adminData.rubrics[attempt.question_id];
            const matched = JSON.parse(attempt.matched);
            return `<details class="student-card"><summary><div><h3>${esc(student.name)} · ${question.subtopic}</h3><small>${markLabel(attempt)} · ${new Date(attempt.created * 1000).toLocaleString()}</small></div><span class="badge amber">Review required</span></summary>
                <form class="teacher-form student-detail" data-attempt="${attempt.id}" data-revision="${attempt.revision}"><h3>${question.prompt}</h3><blockquote>${esc(attempt.answer || 'No answer submitted.')}</blockquote>
                ${rubric.points.map((point, i) => `<label class="point"><input type="checkbox" name="point" ${matched[i] ? 'checked' : ''}><span>${esc(point)}</span></label>`).join('')}
                <label for="note-${attempt.id}">Teacher feedback and reason for this mark</label><textarea id="note-${attempt.id}" name="note" required maxlength="2000" rows="3" placeholder="Explain what was demonstrated and what to revisit."></textarea>
                <button class="primary" type="submit">Save teacher mark</button><p class="error" role="alert"></p></form></details>`;
        }).join('') : '<div class="info">All submitted answers have been reviewed.</div>'}`;
    container.querySelectorAll('form').forEach(form => {
        form.onsubmit = async event => {
            event.preventDefault();
            const button = form.querySelector('button');
            button.disabled = true;
            try {
                await api('teacher-review', {
                    id: Number(form.dataset.attempt), revision: Number(form.dataset.revision),
                    matched: [...form.querySelectorAll('[name=point]')].map(input => input.checked),
                    note: form.querySelector('[name=note]').value
                });
                await refresh();
                adminDashboard();
                toast('Teacher mark saved. Scores and priorities updated.');
            } catch (error) {
                form.querySelector('.error').textContent = error.message;
                button.disabled = false;
            }
        };
    });
}
