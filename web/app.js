// スマホ側のロジック：WebSocket 接続・トラックパッド操作・キーボード入力

// ===== WebSocket 接続（自動再接続つき）=====
let ws = null;

function connect() {
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onopen = () => setConnected(true);
  ws.onclose = () => { setConnected(false); setTimeout(connect, 2000); }; // 2秒後に再接続
  ws.onerror = () => { try { ws.close(); } catch (e) {} };
}

function send(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(obj));
  }
}

function setConnected(ok) {
  document.querySelectorAll('.status-dot').forEach(d => d.classList.toggle('connected', ok));
  document.querySelectorAll('.status-text').forEach(t => { t.textContent = ok ? '接続中' : '再接続中…'; });
}

connect();

// ===== 画面（モード）切替 =====
const screenControl = document.getElementById('screen-control');
const screenKeyboard = document.getElementById('screen-keyboard');
const kbInput = document.getElementById('kb-input');

document.getElementById('btn-open-keyboard').addEventListener('click', () => {
  screenControl.classList.remove('active');
  screenKeyboard.classList.add('active');
  kbInput.focus(); // ソフトキーボードを出す
});
document.getElementById('btn-back').addEventListener('click', () => {
  screenKeyboard.classList.remove('active');
  screenControl.classList.add('active');
  kbInput.blur();
});

// ===== クリックボタン =====
document.getElementById('btn-left').addEventListener('click', () => send({ type: 'click', button: 'left', double: false }));
document.getElementById('btn-right').addEventListener('click', () => send({ type: 'click', button: 'right', double: false }));

// ===== トラックパッド =====
const trackpad = document.getElementById('trackpad');
let lastX = 0, lastY = 0;       // 直前のタッチ座標（1本指移動用）
let accDx = 0, accDy = 0;       // 1フレーム分の移動量を貯める
let rafPending = false;
let startX = 0, startY = 0, startTime = 0, maxTouches = 0;
let scrollLastX = 0, scrollLastY = 0;

// 貯めた移動量を1フレームに1回だけ送る（送りすぎを防ぐ＝間引き）
function flushMove() {
  rafPending = false;
  if (accDx !== 0 || accDy !== 0) {
    send({ type: 'move', dx: accDx, dy: accDy });
    accDx = 0; accDy = 0;
  }
}
function scheduleMove() {
  if (!rafPending) {
    rafPending = true;
    requestAnimationFrame(flushMove);
  }
}

trackpad.addEventListener('touchstart', (e) => {
  e.preventDefault();
  const t = e.touches[0];
  lastX = t.clientX; lastY = t.clientY;
  startX = t.clientX; startY = t.clientY;
  startTime = Date.now();
  maxTouches = e.touches.length;
  if (e.touches.length === 2) {
    // 2本指の重心を記録（スクロール用）
    scrollLastX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
    scrollLastY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
  }
}, { passive: false });

trackpad.addEventListener('touchmove', (e) => {
  e.preventDefault();
  maxTouches = Math.max(maxTouches, e.touches.length);

  if (e.touches.length >= 2) {
    // 2本指 → スクロール（重心の移動量）
    const cx = (e.touches[0].clientX + e.touches[1].clientX) / 2;
    const cy = (e.touches[0].clientY + e.touches[1].clientY) / 2;
    const dx = cx - scrollLastX;
    const dy = cy - scrollLastY;
    scrollLastX = cx; scrollLastY = cy;
    // 指を下へ動かすと下方向スクロールになるよう dy の符号を反転
    send({ type: 'scroll', dx: dx, dy: -dy });
  } else {
    // 1本指 → カーソル移動（差分を貯めて rAF で間引き送信）
    const t = e.touches[0];
    accDx += t.clientX - lastX;
    accDy += t.clientY - lastY;
    lastX = t.clientX; lastY = t.clientY;
    scheduleMove();
  }
}, { passive: false });

trackpad.addEventListener('touchend', (e) => {
  e.preventDefault();
  // 短時間・ほぼ動かさずに離した = タップ = クリック
  const elapsed = Date.now() - startTime;
  const dist = Math.hypot(lastX - startX, lastY - startY);
  if (e.touches.length === 0 && elapsed < 200 && dist < 10) {
    if (maxTouches >= 2) send({ type: 'click', button: 'right', double: false });
    else send({ type: 'click', button: 'left', double: false });
  }
}, { passive: false });

// 既定のジェスチャ・コンテキストメニューを抑止
trackpad.addEventListener('contextmenu', (e) => e.preventDefault());
document.addEventListener('gesturestart', (e) => e.preventDefault());

// ===== キーボード入力（リアルタイム送信 + 日本語IME対応）=====
let composing = false; // 変換中かどうか

kbInput.addEventListener('compositionstart', () => { composing = true; });
kbInput.addEventListener('compositionend', (e) => {
  composing = false;
  if (e.data) {
    send({ type: 'text', text: e.data });  // 変換が確定した文字列だけ送る
    appendDisplay(e.data);
  }
  kbInput.value = '';
});

// 特殊キー：JSのキー名 → サーバーへ送るキー名
const SPECIAL = { 'Enter': 'enter', 'Backspace': 'backspace', 'Tab': 'tab', 'Escape': 'esc', ' ': 'space' };

kbInput.addEventListener('keydown', (e) => {
  if (composing) return; // 変換中は何もしない（IME に任せる）

  if (e.key in SPECIAL) {
    send({ type: 'key', key: SPECIAL[e.key] });
    appendDisplay(e.key === ' ' ? '␣' : e.key);
    e.preventDefault();
    kbInput.value = '';
  } else if (e.key.length === 1) {
    // 通常の1文字（英数記号）はそのまま送る
    send({ type: 'text', text: e.key });
    appendDisplay(e.key);
    e.preventDefault();
    kbInput.value = '';
  }
});

const kbDisplay = document.getElementById('kb-display');
function appendDisplay(s) {
  // 直近に送った内容を確認用に表示（末尾60文字まで）
  kbDisplay.textContent = (kbDisplay.textContent + s).slice(-60);
}
