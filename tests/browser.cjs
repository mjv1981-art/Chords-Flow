const { test } = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const { mkdirSync, readFileSync } = require('node:fs');
mkdirSync('.cache/test-artifacts', {recursive:true});

const origin = process.env.TEST_ORIGIN || 'http://127.0.0.1:5173';
const video = 'https://www.youtube.com/watch?v=rsotlzr9wNw';
const fixture = {title:'Controlled MIDI fixture',composer:'Test',key:'Dm',tempo:60,time_signature:'4/4',
  right_hand:[{note:'D4',time:0,duration:4},{note:'F4',time:4,duration:2},{note:'A4',time:6,duration:2}],
  harmony:[{chord:'Dm',time:0,duration:8}],source_url:video,arrangement_kind:'melody'};

async function launch() {
  return chromium.launch({executablePath:process.env.CHROMIUM_PATH || '/usr/bin/chromium',
    headless:true,args:['--no-sandbox','--autoplay-policy=no-user-gesture-required']});
}
function lookupResult(song=fixture, changes={}) {
  return {video:{url:video,title:'Nightwish — '+song.title,author:'YouTube channel',metadata_available:true},
    query:song.title,needs_name:false,manual_name:false,library_count:2,search_links:[],
    matches:[{id:'controlled',title:song.title,artist:song.composer,description:'Existing MIDI arrangement',
      source_url:'https://github.com/dirkncl/midiArchive',source_name:'MIDI Archive'}],...changes};
}

test('unknown song offers source searches without inventing a playable melody', async () => {
  const browser=await launch();
  try {
    const page=await browser.newPage();
    await page.route('**/api/song-lookup',r=>r.fulfill({json:lookupResult(fixture,{matches:[],search_links:[
      {label:'MIDI',url:'https://www.google.com/search?q=unknown+MIDI'}]})}));
    await page.goto(origin);
    await page.getByLabel('Ссылка на YouTube').fill(video);
    await page.getByRole('button',{name:'Определить песню'}).click();
    await page.getByText('Для этой песни готовой аранжировки пока нет.',{exact:false}).waitFor();
    assert.equal(await page.getByRole('link',{name:'Найти midi'}).count(),1);
    assert.equal(await page.locator('canvas').count(),0);
    assert.equal(await page.getByRole('button',{name:/Да, открыть/}).count(),0);
  } finally { await browser.close(); }
});
test('confirmed library arrangement plays both hands, toggles Am, seeks, and restores original', async () => {
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
    await page.route('**/api/song-lookup',r=>r.fulfill({json:lookupResult()}));
    await page.route('**/api/library-song',r=>r.fulfill({json:{song:fixture}}));
    await page.goto(origin);
    await page.getByLabel('Ссылка на YouTube').fill(video);
    await page.getByRole('button',{name:'Определить песню'}).click();
    await page.getByRole('button',{name:'Да, открыть '+fixture.title}).waitFor();
    assert.equal(await page.locator('canvas').count(),0);
    await page.getByRole('button',{name:'Да, открыть '+fixture.title}).click();
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

test('blocked YouTube metadata can be replaced with a user-confirmed song name', async () => {
  const browser=await launch();
  try {
    const page=await browser.newPage();
    const requests=[];
    await page.route('**/api/song-lookup',route=> {
      const request=route.request().postDataJSON(); requests.push(request);
      return route.fulfill({json:lookupResult(fixture,request.query ? {manual_name:true} :
        {matches:[],needs_name:true,query:'',video:{url:video,title:'',author:'',metadata_available:false}})});
    });
    await page.route('**/api/library-song',r=>r.fulfill({json:{song:fixture}}));
    await page.goto(origin);
    await page.getByLabel('Ссылка на YouTube').fill(video);
    await page.getByRole('button',{name:'Определить песню'}).click();
    await page.getByText('YouTube не вернул название.',{exact:false}).waitFor();
    await page.getByLabel('Песня и исполнитель').fill('Nightwish — Sleeping Sun');
    await page.getByRole('button',{name:'Найти аранжировку'}).click();
    await page.getByRole('button',{name:'Да, открыть '+fixture.title}).click();
    await page.getByRole('heading',{name:fixture.title}).waitFor();
    assert.equal(requests[1].query,'Nightwish — Sleeping Sun');
  } finally { await browser.close(); }
});

for (const songId of ['nightwish-sleeping-sun','nightwish-come-cover-me']) {
  test(`real imported ${songId} arrangement plays both hands and supports Am`,async()=> {
    const song=JSON.parse(readFileSync('server/library/'+songId+'.json','utf8'));
    const browser=await launch();
    try {
      const page=await browser.newPage({viewport:{width:1440,height:900}});
      const errors=[]; page.on('pageerror',error=>errors.push(error.message));
      await page.route('**/api/song-lookup',r=>r.fulfill({json:lookupResult(song)}));
      await page.route('**/api/library-song',r=>r.fulfill({json:{song}}));
      await page.goto(origin);
      await page.getByLabel('Ссылка на YouTube').fill(video);
      await page.getByRole('button',{name:'Определить песню'}).click();
      await page.getByRole('button',{name:'Да, открыть '+song.title}).click();
      await page.getByRole('heading',{name:song.title}).waitFor();
      await page.getByRole('button',{name:'Воспроизвести',exact:true}).click();
      await page.waitForFunction(note=>document.querySelector(`button[title="${note}"]`)?.className.includes('scale-110'),song.right_hand[0].note);
      await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(button=>
        button.title && !/\d$/.test(button.title) && button.className.includes('scale-110')));
      await page.getByRole('switch',{name:'Транспонировать в ля минор'}).click();
      await page.getByText('Am · B-гриф',{exact:true}).waitFor();
      await page.getByRole('button',{name:'Воспроизвести',exact:true}).click();
      await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(button=>
        /\d$/.test(button.title) && button.className.includes('scale-110')));
      assert.deepEqual(errors,[]);
    } finally { await browser.close(); }
  });
}
