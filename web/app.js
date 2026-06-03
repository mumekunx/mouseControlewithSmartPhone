// スマホ側のロジック：WebSocket 接続・トラックパッド操作・キーボード入力

// ===== WebSocket 接続（ペアリングトークン必須・自動再接続つき）=====
let ws = null;

// QR/URL に含まれる接続キー（?token=...）。これが無いと操作できない。
const TOKEN = new URLSearchParams(location.search).get('token');

function setStatusText(s) {
  document.querySelectorAll('.status-text').forEach(t => { t.textContent = s; });
}

function connect() {
  if (!TOKEN) return; // トークンが無ければ接続しない
  ws = new WebSocket(`ws://${location.host}/ws?token=${encodeURIComponent(TOKEN)}`);
  ws.onopen = () => { setConnected(true); sendSensitivity(); }; // 接続できたら現在の感度をPCに同期
  ws.onclose = (e) => {
    setConnected(false);
    if (e.code === 1008) { // トークン不正：再接続しても無駄なので止める
      setStatusText('接続キーが無効です（PCのQRから開き直してください）');
      return;
    }
    setTimeout(connect, 2000); // それ以外は2秒後に再接続
  };
  ws.onerror = () => { try { ws.close(); } catch (e) {} };
}

function send(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(obj));
  }
}

function setConnected(ok) {
  document.querySelectorAll('.status-dot').forEach(d => d.classList.toggle('connected', ok));
  setStatusText(ok ? '接続中' : '再接続中…');
}

if (TOKEN) {
  connect();
} else {
  // QR を使わず直接開いた等。操作できないことを UI で知らせる。
  setStatusText('接続キーがありません（PCに表示された QR から開いてください）');
}

// ===== 画面（モード）切替 =====
const screenControl = document.getElementById('screen-control');
const screenKeyboard = document.getElementById('screen-keyboard');
const kbInput = document.getElementById('kb-input');

document.getElementById('btn-open-keyboard').addEventListener('click', () => {
  screenControl.classList.remove('active');
  screenKeyboard.classList.add('active');
  resetMirror();   // 入力欄とPC対応を初期化してから
  kbInput.focus(); // ソフトキーボードを出す
});
document.getElementById('btn-back').addEventListener('click', () => {
  screenKeyboard.classList.remove('active');
  screenControl.classList.add('active');
  resetMirror();   // 途中のバッファを残さない
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

// 2本指ピンチ（拡大縮小）用の状態
const ZOOM_STEP_PX = 28;   // 指間距離がこの分だけ変わるごとに1段ズーム
let pinchLastDist = 0;     // 直前フレームの指間距離
let pinchAccum = 0;        // ズーム1段に満たない距離変化の貯金

// 長押しドラッグ用の状態
const LONG_PRESS_MS = 450;   // この時間ほぼ動かさず保持したらドラッグ開始
const MOVE_CANCEL_PX = 10;   // これ以上動いたら「長押し」ではなく通常移動とみなす
let pressTimer = null;       // 長押し判定タイマー
let isDragging = false;      // 左ボタンを押しっぱなし（ドラッグ中）か

function clearPressTimer() {
  if (pressTimer) { clearTimeout(pressTimer); pressTimer = null; }
}

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
    // 2本指の重心（スクロール用）と指間距離（ピンチズーム用）を記録
    scrollLastX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
    scrollLastY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
    pinchLastDist = Math.hypot(
      e.touches[0].clientX - e.touches[1].clientX,
      e.touches[0].clientY - e.touches[1].clientY);
    pinchAccum = 0;
  }
  // 1本指で置いたら長押しタイマー開始（保持し続けたらドラッグ開始）
  clearPressTimer();
  if (e.touches.length === 1) {
    pressTimer = setTimeout(() => {
      pressTimer = null;
      isDragging = true;
      send({ type: 'down' });                       // 左ボタンを押しっぱなしにする
      if (navigator.vibrate) navigator.vibrate(30);  // 触覚フィードバック
      trackpad.classList.add('dragging');            // 視覚フィードバック
    }, LONG_PRESS_MS);
  }
}, { passive: false });

trackpad.addEventListener('touchmove', (e) => {
  e.preventDefault();
  maxTouches = Math.max(maxTouches, e.touches.length);

  if (isDragging) {
    // ドラッグ中：1本指の移動でそのままドラッグ（ボタンは押下済み）
    const t = e.touches[0];
    accDx += t.clientX - lastX;
    accDy += t.clientY - lastY;
    lastX = t.clientX; lastY = t.clientY;
    scheduleMove();
    return;
  }

  if (e.touches.length >= 2) {
    // 2本指。長押し判定は中止。
    clearPressTimer();
    const cx = (e.touches[0].clientX + e.touches[1].clientX) / 2;
    const cy = (e.touches[0].clientY + e.touches[1].clientY) / 2;
    const dist = Math.hypot(
      e.touches[0].clientX - e.touches[1].clientX,
      e.touches[0].clientY - e.touches[1].clientY);

    const dDist = dist - pinchLastDist;                   // 指間距離の変化（＝ピンチ量）
    const centroidMove = Math.hypot(cx - scrollLastX, cy - scrollLastY); // 重心の移動（＝パン量）
    pinchLastDist = dist;

    if (Math.abs(dDist) > centroidMove) {
      // ピンチ優勢のフレーム → 拡大縮小。距離変化を貯めて、しきい値ごとに1段送る。
      pinchAccum += dDist;
      while (pinchAccum >= ZOOM_STEP_PX)  { send({ type: 'zoom', dir: 'in'  }); pinchAccum -= ZOOM_STEP_PX; }
      while (pinchAccum <= -ZOOM_STEP_PX) { send({ type: 'zoom', dir: 'out' }); pinchAccum += ZOOM_STEP_PX; }
    } else {
      // パン優勢のフレーム → スクロール（指を下へ動かすと下方向になるよう dy 反転）
      send({ type: 'scroll', dx: cx - scrollLastX, dy: -(cy - scrollLastY) });
    }
    scrollLastX = cx; scrollLastY = cy;
  } else {
    // 1本指 → カーソル移動（差分を貯めて rAF で間引き送信）
    const t = e.touches[0];
    // 一定以上動いたら「長押し」ではなく通常移動とみなしてタイマー中止
    if (Math.hypot(t.clientX - startX, t.clientY - startY) > MOVE_CANCEL_PX) clearPressTimer();
    accDx += t.clientX - lastX;
    accDy += t.clientY - lastY;
    lastX = t.clientX; lastY = t.clientY;
    scheduleMove();
  }
}, { passive: false });

trackpad.addEventListener('touchend', (e) => {
  e.preventDefault();
  clearPressTimer();

  if (isDragging) {
    // ドラッグ中に全部の指が離れたらボタンを離す（ドロップ）
    if (e.touches.length === 0) {
      send({ type: 'up' });
      isDragging = false;
      trackpad.classList.remove('dragging');
    }
    return; // ドラッグ後はクリック扱いにしない
  }

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

// ===== キーボード入力（入力欄の実値をライブミラー）=====
// 入力欄(kbInput)の「実際の値」を唯一の正とし、input イベントごとに
// 前回PCへ反映済みとの前方一致差分だけ送る（{type:'compose', back, add}）。
// これで日本語の変換中・濁点・削除・英数をすべて1経路で扱え、値が同じなら
// 差分ゼロ＝二重送信が原理的に起きない（冪等）。iOS Safari の composition/keydown
// 二重発火や、確定ごとのクリア由来のバグ（濁点で旧文字が残る等）を根本回避する。
let mirroredCP = [];   // PCに反映済みの「入力欄の値」（コードポイント配列）

function resetMirror() {
  // 入力欄をクリアし、PC側との対応もリセット（PC上の確定済み文字は残す）
  kbInput.value = '';
  mirroredCP = [];
}

// 入力欄の現在値を、前回反映済み mirroredCP との差分にしてPCへ送る。
function syncFromInput() {
  const cur = Array.from(kbInput.value);          // コードポイント単位（絵文字=1要素）
  let i = 0;
  const n = Math.min(mirroredCP.length, cur.length);
  while (i < n && mirroredCP[i] === cur[i]) i++;  // 共通プレフィックスの長さ
  const back = mirroredCP.length - i;             // PC側で消す文字数
  const add = cur.slice(i).join('');              // PC側で足す文字
  if (back > 0 || add.length > 0) {
    send({ type: 'compose', back, add });
    if (add) appendDisplay(add);
  }
  mirroredCP = cur;
}

// 文字入力・変換・削除はすべて input で拾う（変換中 isComposing でもライブ反映）。
kbInput.addEventListener('input', syncFromInput);
// compositionend 後の最終状態も念のため同期（端末差の保険）。
kbInput.addEventListener('compositionend', syncFromInput);

// 特殊キーは入力欄の値に出ない（または出したくない）ので keydown で個別に送る。
kbInput.addEventListener('keydown', (e) => {
  if (e.isComposing) return; // 変換中（Enterでの変換確定など）はIMEに任せる

  if (e.key === 'Enter') {
    send({ type: 'key', key: 'enter' });
    appendDisplay('⏎');
    e.preventDefault();
    resetMirror();            // 1行送信＝区切り。バッファをリセットして次へ
  } else if (e.key === 'Backspace') {
    // 入力欄に文字があるときは input(削除) が差分を送るので、ここでは何もしない。
    // 空のときだけ PC 側の既存文字を1つ消す。
    if (kbInput.value.length === 0) {
      send({ type: 'key', key: 'backspace' });
      e.preventDefault();
    }
  } else if (e.key === 'Tab') {
    send({ type: 'key', key: 'tab' }); appendDisplay('⇥'); e.preventDefault();
  } else if (e.key === 'Escape') {
    send({ type: 'key', key: 'esc' }); e.preventDefault();
  }
});

const kbDisplay = document.getElementById('kb-display');
function appendDisplay(s) {
  // 直近に送った内容を確認用に表示（末尾60文字まで）
  kbDisplay.textContent = (kbDisplay.textContent + s).slice(-60);
}

// ===== カーソル感度（DPI）：ステータスバーのセレクト（iOS Safari ではロール選択になる）=====
const sensSelect = document.getElementById('sens-select');

function sendSensitivity() {
  // 接続時・変更時に現在の感度を PC に送る
  if (sensSelect) send({ type: 'sensitivity', value: Number(sensSelect.value) });
}

if (sensSelect) {
  // 0.5〜3.0 を 0.1 刻みで選択肢生成（×0.5 …のように表示）
  for (let v = 0.5; v <= 3.0001; v += 0.1) {
    const val = v.toFixed(1);
    const opt = document.createElement('option');
    opt.value = val;
    opt.textContent = '×' + val;
    sensSelect.appendChild(opt);
  }
  // 前回値を復元（localStorage）。無ければ既定 1.5。
  const saved = localStorage.getItem('sensitivity');
  sensSelect.value = (saved !== null && saved !== '') ? Number(saved).toFixed(1) : '1.5';

  sensSelect.addEventListener('change', () => {
    localStorage.setItem('sensitivity', sensSelect.value);
    sendSensitivity();
  });
}
