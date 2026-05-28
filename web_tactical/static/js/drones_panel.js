// drones_panel.js — LogiDrone-UCC v5.1
// Correccion: refresca frente de cola tras despacho/completar entrega
'use strict';

const DC = {
    bg:      '#07111F',
    surf:    '#0B1929',
    surf2:   '#0F2035',
    border:  '#1A3A5C',
    cyan:    '#00E5FF',
    blue:    '#3B82F6',
    green:   '#00FF9C',
    yellow:  '#FFC857',
    red:     '#FF4D6D',
    red2:    '#FF0040',
    orange:  '#FF8C00',
    muted:   '#4A6A8A',
    white:   '#E8F4FF',
};

function batColor(pct) {
    if (pct <= 20) return DC.red;
    if (pct <= 40) return DC.orange;
    if (pct <= 60) return DC.yellow;
    return DC.green;
}

function estadoColor(d) {
    if (d.necesita_mant) return DC.red;
    const map = {
        en_vuelo:      DC.cyan,
        en_espera:     DC.blue,
        bateria_baja:  DC.orange,
        mantenimiento: DC.red,
    };
    return map[d.estado] || DC.muted;
}

// ── Alerta banner ─────────────────────────────────────────────────────────────

function renderAlertasMant(drones) {
    const container = document.getElementById('drones-alertas');
    if (!container) return;

    const criticos = drones.filter(d => d.necesita_mant);
    if (!criticos.length) {
        container.innerHTML = '';
        container.style.display = 'none';
        return;
    }

    container.style.display = 'block';
    container.innerHTML = `
    <div style="
      background:#1A0008;border:1px solid ${DC.red2};border-radius:6px;
      padding:12px 16px;margin-bottom:16px">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
        <span style="font-size:18px">⚠</span>
        <strong style="color:${DC.red2};font-family:monospace;font-size:13px;letter-spacing:.08em">
          ${criticos.length} DRON${criticos.length > 1 ? 'ES' : ''} REQUIERE${criticos.length > 1 ? 'N' : ''} MANTENIMIENTO
        </strong>
        <span style="color:${DC.muted};font-size:10px;margin-left:auto">BATERÍA ≤ 20% → MANTENIMIENTO OBLIGATORIO</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:6px">
        ${criticos.map(d => `
          <div style="
            display:flex;align-items:center;gap:12px;
            background:#200510;padding:8px 12px;border-radius:4px;
            border-left:3px solid ${DC.red2}">
            <div style="flex:1">
              <div style="color:${DC.white};font-family:monospace;font-size:12px;font-weight:bold">
                ${d.id}  ·  ${d.modelo}
              </div>
              <div style="color:${DC.red};font-size:11px;margin-top:2px">
                ${d.razon_mant || 'Requiere mantenimiento'}
              </div>
            </div>
            <div style="text-align:right">
              <div style="color:${batColor(d.bateria)};font-family:monospace;font-size:13px;font-weight:bold">
                ${d.bateria}%
              </div>
              <div style="background:${DC.border};border-radius:2px;width:80px;height:4px;margin-top:4px">
                <div style="background:${batColor(d.bateria)};height:4px;border-radius:2px;width:${d.bateria}%"></div>
              </div>
            </div>
            <button
              onclick="abrirFormMant('${d.id}')"
              style="
                background:${DC.red2};color:#fff;border:none;
                font-family:monospace;font-size:11px;font-weight:bold;
                padding:5px 10px;border-radius:4px;cursor:pointer;
                white-space:nowrap">
              ATENDER →
            </button>
          </div>
        `).join('')}
      </div>
    </div>`;
}

// ── Cards de drones ───────────────────────────────────────────────────────────

function renderCardsDrones(drones) {
    const grid = document.getElementById('drones-cards-grid');
    if (!grid) return;

    if (!drones.length) {
        grid.innerHTML = `<p style="color:${DC.muted};font-family:monospace;font-size:12px">Sin drones en la flota.</p>`;
        return;
    }

    grid.innerHTML = drones.map(d => {
        const mant   = d.necesita_mant;
        const col    = estadoColor(d);
        const bc     = batColor(d.bateria);
        const estTxt = mant ? 'MANTENIMIENTO' : (d.estado || '').replace(/_/g, ' ').toUpperCase();

        return `
      <div style="
        background:${DC.surf};border-radius:6px;padding:0;overflow:hidden;
        border:1px solid ${mant ? DC.red2 : DC.border};
        ${mant ? `box-shadow:0 0 12px rgba(255,0,64,.2)` : ''}">
        <div style="background:${col};height:2px"></div>
        <div style="padding:12px 14px">
          ${mant ? `<div style="color:${DC.red2};font-family:monospace;font-size:10px;font-weight:bold;margin-bottom:6px">
            ⚠ MANTENIMIENTO REQUERIDO</div>` : ''}
          <div style="display:flex;align-items:center;gap:8px">
            <span style="color:${DC.white};font-family:monospace;font-size:16px;font-weight:bold">${d.id}</span>
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${col}"></span>
          </div>
          <div style="color:${DC.muted};font-size:11px;font-family:monospace">${d.modelo}</div>
          <div style="color:${col};font-family:monospace;font-size:11px;font-weight:bold;margin:4px 0 8px">${estTxt}</div>
          <div style="color:${DC.muted};font-size:10px;font-family:monospace;margin-bottom:8px">
            Cap: ${d.capacidad_kg} kg  ·  Vel: ${Math.round(d.velocidad_kmh)} km/h
          </div>
          <div style="color:${bc};font-family:monospace;font-size:11px;font-weight:${d.bateria <= 20 ? 'bold' : 'normal'}">
            BATERÍA: ${d.bateria}%${d.bateria <= 20 ? ' ⚠ CRÍTICA' : ''}
          </div>
          <div style="background:${DC.border};border-radius:2px;height:5px;margin:4px 0 10px">
            <div style="background:${bc};height:5px;border-radius:2px;width:${d.bateria}%"></div>
          </div>
          <div style="border-top:1px solid ${DC.border};padding-top:8px;color:${DC.muted};font-size:10px;font-family:monospace">
            ${(d.ultimo_mant || 'Sin registros').slice(0, 40)}
          </div>
          <div style="display:flex;gap:6px;margin-top:10px;flex-wrap:wrap">
            ${mant ? `
              <button onclick="abrirFormMant('${d.id}')"
                style="flex:1;background:${DC.red};color:#07111F;border:none;font-family:monospace;
                       font-size:10px;font-weight:bold;padding:5px;border-radius:3px;cursor:pointer">
                ◈ REGISTRAR MANT.
              </button>
              <button onclick="recargarDron('${d.id}')"
                style="flex:1;background:transparent;color:${DC.yellow};border:1px solid ${DC.yellow};
                       font-family:monospace;font-size:10px;padding:5px;border-radius:3px;cursor:pointer">
                ⚡ RECARGAR
              </button>
            ` : `
              <button onclick="abrirFormMant('${d.id}')"
                style="flex:1;background:transparent;color:${DC.cyan};border:1px solid ${DC.border};
                       font-family:monospace;font-size:10px;padding:5px;border-radius:3px;cursor:pointer">
                ◈ MANT.
              </button>
              <button onclick="recargarDron('${d.id}')"
                style="flex:1;background:transparent;color:${DC.yellow};border:1px solid ${DC.border};
                       font-family:monospace;font-size:10px;padding:5px;border-radius:3px;cursor:pointer">
                ⚡ RECARGAR
              </button>
            `}
            <button onclick="retirarDron('${d.id}')"
              style="background:transparent;color:${DC.muted};border:1px solid ${DC.border};
                     font-family:monospace;font-size:10px;padding:5px 8px;border-radius:3px;cursor:pointer"
              title="Retirar dron de la flota">✖</button>
          </div>
        </div>
      </div>`;
    }).join('');
}

// ── Actualizar pantallas de drones (versión completa) ─────────────────────────

function actualizarPantallasDronesCompleto() {
    fetch('/api/drones').then(r => r.json()).then(data => {
        const drones = data.drones || [];

        renderAlertasMant(drones);
        renderCardsDrones(drones);

        const tabla = document.getElementById('tabla-drones-full');
        if (tabla) {
            tabla.innerHTML = `<tr>
          <th>ID</th><th>Modelo</th><th>Estado</th>
          <th>Batería</th><th>Cap.(kg)</th><th>Vel.(km/h)</th><th>Alerta</th>
        </tr>`;
            const select = document.getElementById('ctrl-dron-id');
            if (select) select.innerHTML = '';

            drones.forEach(d => {
                const mant   = d.necesita_mant;
                const bc     = batColor(d.bateria);
                const estTxt = mant ? 'MANTENIMIENTO' : d.estado.toUpperCase();
                const col    = mant ? DC.red : DC.blue;

                tabla.innerHTML += `<tr style="${mant ? `background:rgba(255,0,64,.05)` : ''}">
              <td style="font-family:monospace;font-weight:bold">${d.id}</td>
              <td style="color:${DC.muted}">${d.modelo}</td>
              <td style="color:${col};font-weight:bold">${estTxt}</td>
              <td style="color:${bc};font-weight:bold">${d.bateria}%</td>
              <td>${d.capacidad_kg}</td>
              <td>${Math.round(d.velocidad_kmh)}</td>
              <td style="color:${mant ? DC.red2 : DC.green};font-size:11px">
                ${mant ? `⚠ ${d.razon_mant}` : '✔ OK'}
              </td>
            </tr>`;

                if (select) {
                    select.innerHTML += `<option value="${d.id}" ${mant ? 'disabled style="color:#666"' : ''}>
                ${d.id} - ${d.estado}${mant ? ' ⚠' : ''}
              </option>`;
                }
            });
        }

        const selViaje = document.getElementById('select-dron-viaje');
        if (selViaje) {
            selViaje.innerHTML = '<option value="">-- Seleccione un Dron Operativo --</option>';
            drones.forEach(d => {
                if (d.estado === 'en_espera' && !d.necesita_mant) {
                    selViaje.innerHTML += `<option value="${d.id}">${d.id} (${d.bateria}%)</option>`;
                }
            });
        }
    }).catch(e => console.error('[DRONES]', e));
}

// Alias para compatibilidad con map.js
window.actualizarPantallasDronesCompleto = actualizarPantallasDronesCompleto;
// Sobreescribir la versión simple de map.js con la versión completa
window.actualizarPantallasDrones = actualizarPantallasDronesCompleto;

// ── Formulario de mantenimiento (modal) ───────────────────────────────────────

function abrirFormMant(idDron) {
    document.getElementById('modal-mant')?.remove();

    const overlay = document.createElement('div');
    overlay.id = 'modal-mant';
    overlay.style.cssText = `
    position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9999;
    display:flex;align-items:center;justify-content:center`;

    overlay.innerHTML = `
    <div style="
      background:${DC.surf};border:1px solid ${DC.cyan};border-radius:8px;
      width:420px;max-width:95vw;overflow:hidden">
      <div style="background:${DC.surf};border-bottom:1px solid ${DC.border};
                  padding:14px 18px;display:flex;align-items:center;gap:10px">
        <span style="color:${DC.cyan};font-family:monospace;font-size:13px;font-weight:bold">
          ◈  REGISTRAR MANTENIMIENTO — ${idDron}
        </span>
        <button onclick="document.getElementById('modal-mant').remove()"
          style="margin-left:auto;background:transparent;border:none;color:${DC.muted};
                 font-size:18px;cursor:pointer;line-height:1">×</button>
      </div>
      <div style="padding:20px">
        <div id="mant-alerta-bat" style="display:none;
          background:#1A0008;border:1px solid ${DC.red2};border-radius:4px;
          padding:8px 12px;margin-bottom:14px;color:${DC.red2};
          font-family:monospace;font-size:11px;font-weight:bold"></div>

        ${campo_modal('mant-op',  'OPERACIÓN',    'Ej: Cambio de batería')}
        ${campo_modal('mant-tec', 'TÉCNICO',      'Ej: Carlos M.')}
        ${campo_modal('mant-obs', 'OBSERVACIÓN',  'Ej: Batería agotada en vuelo')}

        <div style="display:flex;gap:8px;margin-top:16px">
          <button onclick="enviarMantenimiento('${idDron}')"
            style="flex:2;background:${DC.cyan};color:${DC.bg};border:none;
                   font-family:monospace;font-size:12px;font-weight:bold;
                   padding:10px;border-radius:4px;cursor:pointer">
            ◈ APILAR MANTENIMIENTO
          </button>
          <button onclick="document.getElementById('modal-mant').remove()"
            style="flex:1;background:transparent;color:${DC.muted};
                   border:1px solid ${DC.border};font-family:monospace;font-size:11px;
                   padding:10px;border-radius:4px;cursor:pointer">
            Cancelar
          </button>
        </div>
      </div>
    </div>`;

    document.body.appendChild(overlay);

    fetch(`/api/drones`).then(r => r.json()).then(data => {
        const d = (data.drones || []).find(x => x.id === idDron);
        if (d && d.necesita_mant) {
            const alerta = document.getElementById('mant-alerta-bat');
            if (alerta) {
                alerta.style.display = 'block';
                alerta.textContent = `⚠ ${d.razon_mant || 'Requiere mantenimiento'}`;
            }
        }
    });
}

function campo_modal(id, label, placeholder) {
    return `
    <div style="margin-bottom:12px">
      <label style="color:${DC.muted};font-family:monospace;font-size:10px;font-weight:bold;
                    display:block;margin-bottom:4px;letter-spacing:.08em">${label}</label>
      <input id="${id}" type="text" placeholder="${placeholder}"
        style="width:100%;background:${DC.surf2};color:${DC.white};border:1px solid ${DC.border};
               padding:8px 10px;font-family:monospace;font-size:12px;border-radius:4px;
               outline:none;box-sizing:border-box"
        onfocus="this.style.borderColor='${DC.cyan}'"
        onblur="this.style.borderColor='${DC.border}'">
    </div>`;
}

function enviarMantenimiento(idDron) {
    const op  = document.getElementById('mant-op')?.value.trim();
    const tec = document.getElementById('mant-tec')?.value.trim();
    const obs = document.getElementById('mant-obs')?.value.trim();

    if (!op || !tec) {
        mostrarToast('⚠ Completa Operación y Técnico', 'error');
        return;
    }

    fetch(`/api/drones/${idDron}/mantenimiento`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ operacion: op, tecnico: tec, observacion: obs || '' })
    }).then(r => r.json()).then(data => {
        document.getElementById('modal-mant')?.remove();
        mostrarToast(data.message, 'success');
        if (data.necesita_mant) {
            mostrarToast(`⚡ ${idDron} aún necesita recarga de batería`, 'warning');
        }
        actualizarPantallasDronesCompleto();
    }).catch(e => {
        console.error('[MANT]', e);
        mostrarToast('Error de red', 'error');
    });
}

// ── Agregar dron ──────────────────────────────────────────────────────────────

function abrirFormNuevoDron() {
    document.getElementById('modal-nuevo-dron')?.remove();

    fetch('/api/drones/modelos').then(r => r.json()).then(data => {
        const modelos = data.modelos || [];

        const overlay = document.createElement('div');
        overlay.id = 'modal-nuevo-dron';
        overlay.style.cssText = `
      position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9999;
      display:flex;align-items:center;justify-content:center`;

        overlay.innerHTML = `
      <div style="
        background:${DC.surf};border:1px solid ${DC.green};border-radius:8px;
        width:400px;max-width:95vw;overflow:hidden">
        <div style="background:${DC.surf};border-bottom:1px solid ${DC.border};
                    padding:14px 18px;display:flex;align-items:center">
          <span style="color:${DC.green};font-family:monospace;font-size:13px;font-weight:bold">
            ＋  INCORPORAR NUEVO DRON
          </span>
          <button onclick="document.getElementById('modal-nuevo-dron').remove()"
            style="margin-left:auto;background:transparent;border:none;
                   color:${DC.muted};font-size:18px;cursor:pointer">×</button>
        </div>
        <div style="padding:20px">
          <label style="color:${DC.muted};font-family:monospace;font-size:10px;font-weight:bold;
                        display:block;margin-bottom:4px;letter-spacing:.08em">MODELO</label>
          <select id="nd-modelo"
            style="width:100%;background:${DC.surf2};color:${DC.white};border:1px solid ${DC.border};
                   padding:9px 10px;font-family:monospace;font-size:12px;border-radius:4px;
                   outline:none;margin-bottom:12px;box-sizing:border-box">
            ${modelos.map(m => `<option value="${m}">${m}</option>`).join('')}
          </select>

          ${campo_modal('nd-cap', 'CAPACIDAD DE CARGA (kg)', '5.0')}
          ${campo_modal('nd-vel', 'VELOCIDAD DE VUELO (km/h)', '80')}

          <div style="background:${DC.surf2};border-radius:4px;padding:10px 12px;
                      margin:14px 0;color:${DC.muted};font-family:monospace;font-size:10px;line-height:1.5">
            El dron recibirá un ID automático correlativo y quedará<br>
            en estado <strong style="color:${DC.blue}">EN ESPERA</strong> con batería al 100%.
          </div>

          <div style="display:flex;gap:8px">
            <button onclick="confirmarNuevoDron()"
              style="flex:2;background:${DC.green};color:${DC.bg};border:none;
                     font-family:monospace;font-size:12px;font-weight:bold;
                     padding:10px;border-radius:4px;cursor:pointer">
              ＋ INCORPORAR A LA FLOTA
            </button>
            <button onclick="document.getElementById('modal-nuevo-dron').remove()"
              style="flex:1;background:transparent;color:${DC.muted};
                     border:1px solid ${DC.border};font-family:monospace;
                     font-size:11px;padding:10px;border-radius:4px;cursor:pointer">
              Cancelar
            </button>
          </div>
        </div>
      </div>`;

        document.body.appendChild(overlay);
        document.getElementById('nd-cap').value = '5.0';
        document.getElementById('nd-vel').value = '80';
    });
}

function confirmarNuevoDron() {
    const modelo = document.getElementById('nd-modelo')?.value;
    const cap    = parseFloat(document.getElementById('nd-cap')?.value);
    const vel    = parseFloat(document.getElementById('nd-vel')?.value);

    if (!modelo || isNaN(cap) || isNaN(vel) || cap <= 0 || vel <= 0) {
        mostrarToast('⚠ Capacidad y velocidad deben ser números positivos', 'error');
        return;
    }

    fetch('/api/drones', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ modelo, capacidad_kg: cap, velocidad_kmh: vel })
    }).then(r => r.json()).then(data => {
        document.getElementById('modal-nuevo-dron')?.remove();
        if (data.status === 'success') {
            mostrarToast(`✔ ${data.message}`, 'success');
            actualizarPantallasDronesCompleto();
        } else {
            mostrarToast(`⚠ ${data.message}`, 'error');
        }
    }).catch(e => {
        console.error('[NUEVO DRON]', e);
        mostrarToast('Error de red', 'error');
    });
}

// ── Recargar / Retirar ────────────────────────────────────────────────────────

function recargarDron(idDron) {
    fetch(`/api/drones/${idDron}/recargar`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            mostrarToast(`⚡ ${data.message || `${idDron} recargado al 100%`}`, 'success');
            actualizarPantallasDronesCompleto();
            // Si la ventana de pedidos está activa, actualizar selector de drones
            if (typeof window.actualizarPantallaPedidos === 'function') {
                window.actualizarPantallaPedidos();
            }
        });
}

function retirarDron(idDron) {
    if (!confirm(`¿Retirar el dron ${idDron} de la flota?\n\nEsta acción no se puede deshacer.`)) return;
    fetch(`/api/drones/${idDron}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                mostrarToast(`✖ ${data.message}`, 'success');
            } else {
                mostrarToast(`⚠ ${data.message}`, 'error');
            }
            actualizarPantallasDronesCompleto();
        });
}

// Exponer funciones globales
window.abrirFormNuevoDron  = abrirFormNuevoDron;
window.confirmarNuevoDron  = confirmarNuevoDron;
window.abrirFormMant       = abrirFormMant;
window.enviarMantenimiento = enviarMantenimiento;
window.recargarDron        = recargarDron;
window.retirarDron         = retirarDron;
