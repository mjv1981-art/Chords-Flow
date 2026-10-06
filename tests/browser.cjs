const { test } = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const { mkdirSync } = require('node:fs');
mkdirSync('.cache/test-artifacts', {recursive:true});

const origin = process.env.TEST_ORIGIN || 'http://127.0.0.1:5173';
const video = 'https://www.youtube.com/watch?v=rsotlzr9wNw';
const fixture = {title:'Controlled audio fixture',composer:'Test',key:'Dm',tempo:60,time_signature:'4/4',
  right_hand:[{note:'D4',time:0,duration:4},{note:'F4',time:4,duration:2},{note:'A4',time:6,duration:2}],
  harmony:[{chord:'Dm',time:0,duration:8}],source_url:video,arrangement_kind:'melody'};

async function launch() {
  return chromium.launch({executablePath:process.env.CHROMIUM_PATH || '/usr/bin/chromium',
    headless:true,args:['--no-sandbox','--autoplay-policy=no-user-gesture-required']});
}
test('YouTube-only input reports missing server key without claiming success', async () => {
  const browser = await launch();
  try {
    const page = await browser.newPage();
    await page.route('**/api/health',r=>r.fulfill({json:{status:'ok',transcription_configured:false,ffmpeg_available:true}}));
    await page.route('**/api/transcriptions',r=>r.fulfill({status:503,json:{detail:'Добавьте GEMINI_API_KEY в настройках сервера.'}}));
    await page.goto(origin);
    assert.equal(await page.getByRole('tab').count(),0);
    await page.getByLabel('Ссылка на YouTube').fill(video);
    await page.getByRole('button',{name:'Получить мелодию и аккорды'}).click();
    await page.getByRole('alert').waitFor();
    assert.match(await page.getByRole('alert').innerText(),/GEMINI_API_KEY/);
    assert.equal(await page.locator('canvas').count(),0);
  } finally { await browser.close(); }
});
test('controlled transcription plays both hands, toggles Am, seeks, and restores original', async () => {
  const browser = await launch();
  try {
    const page = await browser.newPage({viewport:{width:1440,height:900}});
    const errors = [];
    page.on('pageerror',e=>errors.push(e.message));
    await page.addInitScript(() => {
      window.__oscillatorStarts = 0;
      const create = AudioContext.prototype.createOscillator;
      AudioContext.prototype.createOscillator = function() {
        const oscillator = create.call(this);
        const start = oscillator.start.bind(oscillator);
        oscillator.start = (...args) => { window.__oscillatorStarts++; return start(...args); };
        return oscillator;
      };
    });
    await page.route('**/api/health',r=>r.fulfill({json:{status:'ok',transcription_configured:true,ffmpeg_available:true}}));
    await page.route('**/api/transcriptions',r=>r.fulfill({status:202,json:{id:'controlled'}}));
    await page.route('**/api/transcriptions/controlled',r=>r.fulfill({json:{status:'complete',song:fixture}}));
    await page.goto(origin);
    await page.getByLabel('Ссылка на YouTube').fill(video);
    await page.getByRole('button',{name:'Получить мелодию и аккорды'}).click();
    await page.getByRole('heading',{name:fixture.title}).waitFor();
    assert.equal(await page.locator('canvas').count(),1);
    await page.getByRole('button',{name:'Воспроизвести',exact:true}).click();
    await page.waitForFunction(() => document.querySelector('button[title="D4"]')?.className.includes('scale-110'));
    await page.waitForFunction(() => document.querySelector('button[title="D"]')?.className.includes('scale-110'));
    assert.ok(await page.evaluate(()=>window.__oscillatorStarts) >= 6);
    await page.getByRole('switch',{name:'Транспонировать в ля минор'}).click();
    assert.equal(await page.getByRole('button',{name:'Воспроизвести',exact:true}).count(),1);
    await page.getByRole('button',{name:'Воспроизвести',exact:true}).click();
    await page.waitForFunction(() => document.querySelector('button[title="A3"]')?.className.includes('scale-110'));
    await page.waitForFunction(() => document.querySelector('button[title="A"]')?.className.includes('scale-110'));
    await page.screenshot({path:'.cache/test-artifacts/bayanflow-player.png'});
    await page.getByRole('button',{name:'Пауза',exact:true}).click();
    await page.getByRole('button',{name:'Вперёд на четыре доли'}).click();
    await page.getByRole('button',{name:'Воспроизвести',exact:true}).click();
    await page.waitForFunction(() => document.querySelector('button[title="C4"]')?.className.includes('scale-110'));
    await page.getByRole('button',{name:'Стоп',exact:true}).click();
    await page.getByRole('switch',{name:'Транспонировать в ля минор'}).click();
    await page.getByRole('button',{name:'Воспроизвести',exact:true}).click();
    await page.waitForFunction(() => document.querySelector('button[title="D4"]')?.className.includes('scale-110'));
    await page.getByRole('button',{name:'Сохранить',exact:true}).click();
    const saved = await page.evaluate(()=>JSON.parse(localStorage.getItem('bayanflow-songs')));
    assert.equal(saved[0].key,'Dm');
    assert.equal(saved[0].right_hand[0].note,'D4');
    await page.reload();
    await page.getByRole('button').filter({hasText:fixture.title}).click();
    await page.getByRole('heading',{name:fixture.title}).waitFor();
    assert.deepEqual(errors,[]);
  } finally { await browser.close(); }
});

test('a full-length score stays within canvas limits at high pixel density', async () => {
  const browser = await launch();
  try {
    const page = await browser.newPage({viewport:{width:1440,height:900},deviceScaleFactor:2});
    const longSong = {...fixture, right_hand:[{note:'D4',time:0,duration:1},{note:'F4',time:1800,duration:1}],
      left_hand:[{note:'D-bass',time:0,duration:1}],id:'long-fixture'};
    await page.addInitScript(song=>localStorage.setItem('bayanflow-songs',JSON.stringify([song])),longSong);
    await page.goto(origin);
    await page.getByRole('button').filter({hasText:fixture.title}).click();
    await page.locator('canvas').waitFor();
    const width = await page.locator('canvas').evaluate(c=>c.width);
    assert.ok(width > 0 && width < 8192);
    const slider = page.getByRole('slider');
    await slider.focus();
    await page.keyboard.press('End');
    await page.waitForFunction(()=>parseFloat(document.querySelector('canvas').style.left)>50000);
    assert.ok(await page.locator('canvas').evaluate(c=>c.width) < 8192);
  } finally { await browser.close(); }
});

for (const status of ['processing', 'partial']) {
  test(`a ready fragment remains playable when transcription is ${status}`, async () => {
    const browser = await launch();
    try {
      const page = await browser.newPage({viewport:{width:1440,height:900}});
      const notice = 'Готовая часть 0:30 из 2:00. Остальная часть ещё обрабатывается.';
      const partial = {...fixture, transcription_partial:true, processed_seconds:30,
        total_seconds:120, lyrics_notice:notice, transcription_warning:notice};
      await page.route('**/api/health',r=>r.fulfill({json:{status:'ok',transcription_configured:true,ffmpeg_available:false}}));
      await page.route('**/api/transcriptions',r=>r.fulfill({status:202,json:{id:'partial-check'}}));
      await page.route('**/api/transcriptions/partial-check',r=>r.fulfill({json:{status,song:partial,progress:'Ready',error:notice}}));
      await page.goto(origin);
      await page.getByLabel('Ссылка на YouTube').fill(video);
      await page.getByRole('button',{name:'Получить мелодию и аккорды'}).click();
      await page.getByRole('button',{name:'Открыть готовую часть (0:30)'}).waitFor();
      assert.equal(await page.getByText('Распознавание пока не настроено на сервере.',{exact:false}).count(),0);
      if (status === 'partial') assert.match(await page.getByRole('alert').innerText(),/Готовая часть/);
      await page.getByRole('button',{name:'Открыть готовую часть (0:30)'}).click();
      await page.getByRole('heading',{name:fixture.title}).waitFor();
      assert.equal(await page.getByText(notice,{exact:true}).count(),1);
      await page.getByRole('button',{name:'Воспроизвести',exact:true}).click();
      await page.waitForFunction(() => document.querySelector('button[title="D4"]')?.className.includes('scale-110'));
    } finally { await browser.close(); }
  });
}
