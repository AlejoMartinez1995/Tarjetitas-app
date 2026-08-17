// Tarjetitas 2.0 - Interactive Showcase & Playground Controller

document.addEventListener('DOMContentLoaded', () => {
  initClock();
  initUnlockEffect();
  initPlayground();
});

// Real-Time Lock Screen Clock
function initClock() {
  const timeEl = document.getElementById('lockTime');
  const dateEl = document.getElementById('lockDate');
  
  function updateTime() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    if (timeEl) timeEl.textContent = `${hours}:${minutes}`;
    
    const options = { weekday: 'long', month: 'long', day: 'numeric' };
    const dateStr = now.toLocaleDateString('es-AR', options);
    if (dateEl) dateEl.textContent = dateStr.charAt(0).toUpperCase() + dateStr.slice(1);
  }
  
  updateTime();
  setInterval(updateTime, 1000);
}

// Dribbble-style Phone Unlock Transition
function initUnlockEffect() {
  const phoneMockup = document.getElementById('phoneMockup');
  const phoneContainer = document.getElementById('phoneContainer');
  const lockScreen = document.getElementById('lockScreen');
  const heroContent = document.getElementById('heroContent');
  const pulseBtn = document.getElementById('lockPulseBtn');

  function unlock() {
    if (lockScreen.classList.contains('unlocked')) return;
    
    lockScreen.classList.add('unlocked');
    phoneContainer.classList.remove('locked-state');
    heroContent.classList.add('unlocked');

    setTimeout(() => {
      document.getElementById('heroSection').scrollIntoView({ behavior: 'smooth' });
    }, 400);
  }

  if (phoneMockup) phoneMockup.addEventListener('click', unlock);
  if (pulseBtn) pulseBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    unlock();
  });
}

// Interactive Live Playground State & Logic
const INITIAL_GASTOS = [
  { detalle: "Supermercado", monto: 180000, cuotas: 1, responsable: "Alejo", tarjeta: "VISA", mes: "Agosto" },
  { detalle: "Horno Eléctrico", monto: 250000, cuotas: 3, responsable: "Alejo", tarjeta: "VISA", mes: "Agosto" },
  { detalle: "Zapatillas", monto: 120000, cuotas: 6, responsable: "Lu", tarjeta: "VISA", mes: "Agosto" }
];

let gastosState = [...INITIAL_GASTOS];

function initPlayground() {
  renderSheetsTable();
  renderCharts();

  // Form submission in Playground Emulator
  const form = document.getElementById('sandboxForm');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      
      const detalle = document.getElementById('sbDetalle').value.trim();
      const monto = parseFloat(document.getElementById('sbMonto').value);
      const cuotas = parseInt(document.getElementById('sbCuotas').value) || 1;
      const tarjeta = document.getElementById('sbTarjeta').value;
      const responsable = document.getElementById('sbResponsable').value;
      const mes = document.getElementById('sbMes').value;

      if (!detalle || isNaN(monto) || monto <= 0) {
        showToast('❌ Ingrese un detalle y monto válidos', 'error');
        return;
      }

      const nuevoGasto = { detalle, monto, cuotas, responsable, tarjeta, mes, isNew: true };
      gastosState.push(nuevoGasto);

      // Render updated table & charts live
      renderSheetsTable();
      renderCharts();
      
      // Reset form fields
      document.getElementById('sbDetalle').value = '';
      document.getElementById('sbMonto').value = '';
      document.getElementById('sbCuotas').value = '1';

      showToast(`⚡ Gasto "${detalle}" cargado! Gráfico de torta & cuotas recalculados.`);
    });
  }

  // Gemini AI Assistant Simulation
  const btnAI = document.getElementById('sbBtnAI');
  if (btnAI) {
    btnAI.addEventListener('click', runAISimulation);
  }

  // Reset Demo Button
  const btnReset = document.getElementById('btnResetDemo');
  if (btnReset) {
    btnReset.addEventListener('click', resetDemo);
  }
}

function renderSheetsTable() {
  const tbody = document.getElementById('sheetsTbody');
  if (!tbody) return;

  tbody.innerHTML = '';
  let totalVisa = 0;

  gastosState.forEach((g, index) => {
    totalVisa += g.monto;
    const tr = document.createElement('tr');
    if (g.isNew) tr.classList.add('row-new');
    
    tr.innerHTML = `
      <td>${index + 1}</td>
      <td><strong>${g.detalle}</strong></td>
      <td>$ ${g.monto.toLocaleString('es-AR', { minimumFractionDigits: 2 })}</td>
      <td>${g.cuotas} c.</td>
      <td><span style="color: ${g.responsable === 'Alejo' ? 'var(--coral)' : 'var(--lavender)'}; font-weight: 700;">${g.responsable}</span></td>
      <td>${g.tarjeta}</td>
      <td>${g.mes}</td>
    `;
    tbody.appendChild(tr);
  });

  // Dynamic Subtotal / Total Row
  const totalTr = document.createElement('tr');
  totalTr.classList.add('total-row');
  totalTr.innerHTML = `
    <td colspan="2">TOTAL VISA (Fórmula Dynamic Batch)</td>
    <td colspan="5">$ ${totalVisa.toLocaleString('es-AR', { minimumFractionDigits: 2 })}</td>
  `;
  tbody.appendChild(totalTr);
}

// Render Dashboard Charts (SVG Pie Chart + Installment Bar Chart)
function renderCharts() {
  renderPieChart();
  renderBarChart();
}

function renderPieChart() {
  const pieSvg = document.getElementById('pieSvg');
  const pieLegend = document.getElementById('pieLegend');
  if (!pieSvg || !pieLegend) return;

  const totalsByResp = {};
  let grandTotal = 0;

  gastosState.forEach(g => {
    const resp = g.responsable || "Alejo";
    totalsByResp[resp] = (totalsByResp[resp] || 0) + g.monto;
    grandTotal += g.monto;
  });

  const colorsMap = { "Alejo": "#FE7A5C", "Lu": "#7D81F7" };
  const defaultColors = ['#FE7A5C', '#7D81F7', '#FED34A', '#4CAF50'];
  let currentAngle = 0;
  let svgPaths = '';
  let legendHtml = '';

  const respKeys = Object.keys(totalsByResp);
  
  if (grandTotal === 0 || respKeys.length === 0) {
    pieSvg.innerHTML = `<circle cx="80" cy="80" r="60" fill="none" stroke="#282C37" stroke-width="24"/>`;
    pieLegend.innerHTML = `<div style="color: var(--text-muted);">Sin gastos</div>`;
    return;
  }

  respKeys.forEach((resp, i) => {
    const amount = totalsByResp[resp];
    const pct = amount / grandTotal;
    const strokeDasharray = `${pct * 377} 377`;
    const strokeDashoffset = -currentAngle * 377;
    const color = colorsMap[resp] || defaultColors[i % defaultColors.length];

    svgPaths += `<circle cx="80" cy="80" r="60" fill="none" stroke="${color}" stroke-width="24" stroke-dasharray="${strokeDasharray}" stroke-dashoffset="${strokeDashoffset}"/>`;
    
    legendHtml += `
      <div class="legend-item">
        <div class="legend-color" style="background: ${color};"></div>
        <span><strong>${resp}</strong>: ${(pct * 100).toFixed(0)}% ($ ${Math.round(amount).toLocaleString('es-AR')})</span>
      </div>
    `;

    currentAngle += pct;
  });

  pieSvg.innerHTML = svgPaths;
  pieLegend.innerHTML = legendHtml;
}

function renderBarChart() {
  const barWrapper = document.getElementById('barWrapper');
  if (!barWrapper) return;

  const monthNames = ["Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre", "Enero"];
  const monthSums = { "Agosto": 0, "Septiembre": 0, "Octubre": 0, "Noviembre": 0, "Diciembre": 0, "Enero": 0 };

  gastosState.forEach(g => {
    const cuotaMensual = g.monto / (g.cuotas || 1);
    const startIdx = monthNames.indexOf(g.mes) !== -1 ? monthNames.indexOf(g.mes) : 0;
    
    for (let c = 0; c < g.cuotas; c++) {
      const targetMonth = monthNames[(startIdx + c) % monthNames.length];
      monthSums[targetMonth] += cuotaMensual;
    }
  });

  let maxVal = 0;
  monthNames.forEach(m => {
    if (monthSums[m] > maxVal) maxVal = monthSums[m];
  });

  let barsHtml = '';
  monthNames.forEach(m => {
    const val = monthSums[m];
    const pct = maxVal > 0 ? (val / maxVal) * 100 : 0;
    const isPeak = val > 0 && val === maxVal;

    barsHtml += `
      <div class="bar-col">
        <div class="bar-val">${val > 0 ? `$${Math.round(val / 1000)}k` : ''}</div>
        <div class="bar-fill ${isPeak ? 'peak' : ''}" style="height: ${Math.max(pct, 6)}%;"></div>
        <div class="bar-label">${m.slice(0, 3)}</div>
      </div>
    `;
  });

  barWrapper.innerHTML = barsHtml;
}

function runAISimulation() {
  const aiBox = document.getElementById('sbAiResponse');
  if (!aiBox) return;

  aiBox.style.display = 'block';
  aiBox.innerHTML = `
    <div class="mini-ai-title">✨ ASISTENTE FINANCIERO IA</div>
    <div>⏳ Analizando gastos y gráficos con Gemini...</div>
  `;

  setTimeout(() => {
    const total = gastosState.reduce((acc, g) => acc + g.monto, 0);
    const respMap = {};
    gastosState.forEach(g => respMap[g.responsable] = (respMap[g.responsable] || 0) + g.monto);

    const alejoTotal = respMap["Alejo"] || 0;
    const luTotal = respMap["Lu"] || 0;

    let critique = `Llevan acumulados <strong>$${total.toLocaleString('es-AR')}</strong>.<br/>`;
    critique += `🍕 <strong>Alejo:</strong> $${alejoTotal.toLocaleString('es-AR')} | <strong>Lu:</strong> $${luTotal.toLocaleString('es-AR')}.<br/>`;
    
    if (total > 500000) {
      critique += `⚠️ ¡Atención al gráfico de cuotas! Se observa un <strong>mes pico</strong> cargado. Recomiendo no patear más consumos en 6 o 12 cuotas este mes.`;
    } else {
      critique += `✅ La proyección por mes se ve equilibrada. Sin riesgo de sobreendeudamiento.`;
    }

    aiBox.innerHTML = `
      <div class="mini-ai-title">✨ ASISTENTE FINANCIERO IA</div>
      <div>${critique}</div>
    `;
  }, 900);
}

function resetDemo() {
  gastosState = [...INITIAL_GASTOS];
  renderSheetsTable();
  renderCharts();
  const aiBox = document.getElementById('sbAiResponse');
  if (aiBox) aiBox.style.display = 'none';
  showToast('🔄 Demostración y gráficos reiniciados');
}

function showToast(message, type = 'success') {
  let toast = document.getElementById('liveToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'liveToast';
    toast.className = 'toast';
    document.body.appendChild(toast);
  }

  toast.innerHTML = `<span>${message}</span>`;
  toast.classList.add('show');

  setTimeout(() => {
    toast.classList.remove('show');
  }, 3500);
}
