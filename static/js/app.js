'use strict';
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const dinheiro = value => Number(value ?? 0).toLocaleString('pt-BR', {style:'currency', currency:'BRL'});
const data = value => new Date(value).toLocaleString('pt-BR', {dateStyle:'short', timeStyle:'short'});
const localInput = value => { const d = new Date(value); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0,16); };
const vazio = texto => `<div class="empty">${esc(texto)}</div>`;
let estado = null, assinatura = '', atualizando = null, atualizarDepois = false, preferenciasDirty = false;
let stream = null, cameraTimer = null, toastTimer = null;

function avisar(mensagem, erro=false) {
  const toast = $('#toast');
  clearTimeout(toastTimer);
  toast.textContent = mensagem;
  toast.classList.toggle('error', erro);
  toast.hidden = false;
  toastTimer = setTimeout(() => { toast.hidden = true; }, 6500);
}

async function api(url, method='GET', body) {
  const options = {method, headers:{Accept:'application/json'}};
  if (body !== undefined) { options.headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(body); }
  const response = await fetch(url, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.erro || 'Não foi possível concluir a operação.');
  return result;
}

async function executar(button, tarefa) {
  if (button?.disabled || button?.getAttribute('aria-busy') === 'true') return;
  if (button) button.setAttribute('aria-busy', 'true');
  try { await tarefa(); }
  catch (erro) { avisar(erro.message || 'Não foi possível conectar à livraria.', true); }
  finally { if (button?.isConnected) button.removeAttribute('aria-busy'); }
}

function atualizar() {
  if (atualizando) { atualizarDepois = true; return atualizando; }
  atualizando = (async () => {
    do {
      atualizarDepois = false;
      try {
        const novo = await api('/api/estado');
        const novaAssinatura = JSON.stringify(novo);
        if (novaAssinatura !== assinatura) {
          estado = novo; assinatura = novaAssinatura; renderizar();
        }
        $('#connection-status').hidden = true;
      } catch (erro) {
        $('#connection-status').hidden = false;
      }
    } while (atualizarDepois);
  })().finally(() => { atualizando = null; });
  return atualizando;
}

function trocarAba(aba) {
  document.querySelectorAll('[data-panel]').forEach(panel => { panel.hidden = panel.dataset.panel !== aba; });
  document.querySelectorAll('nav [data-tab]').forEach(button => {
    if (button.dataset.tab === aba) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
}

function capa(livro) {
  const indices = {'1984':0, bichos:1, hobbit:2, reino:3, esgotado:4};
  return `<div class="cover palette-${indices[livro.id] ?? 1}">${livro.lancamento ? '<span class="new-label">NOVIDADE</span>' : ''}<span class="author">${esc(livro.autor)}</span><span class="title">${esc(livro.titulo)}</span><span class="edition">Entrelinhas · ${esc(livro.genero)}</span></div>`;
}

function renderizarCatalogo() {
  if (!estado) return;
  const q = $('#busca').value.trim().toLocaleLowerCase('pt-BR');
  const genero = $('#genero').value;
  const livros = estado.livros.filter(l => (!q || l.titulo.toLocaleLowerCase('pt-BR').includes(q) || l.autor.toLocaleLowerCase('pt-BR').includes(q)) && (!genero || l.genero === genero) && (!$('#lancamentos').checked || l.lancamento));
  $('#catalog-count').textContent = `${livros.length} ${livros.length === 1 ? 'livro encontrado' : 'livros encontrados'}`;
  $('#catalogo-livros').setAttribute('aria-busy', 'false');
  const desejos = new Set(estado.desejos.map(l => l.id));
  $('#catalogo-livros').innerHTML = livros.length ? livros.map(l => `
    <article class="book-card">
      <button class="cover-button" data-action="detalhes" data-id="${esc(l.id)}" aria-label="Ver detalhes de ${esc(l.titulo)}">${capa(l)}</button>
      <div class="book-info"><span class="genre">${esc(l.genero)}</span><h3>${esc(l.titulo)}</h3><div class="subtle">${esc(l.autor)}</div>
      <div class="book-bottom"><span class="price">${dinheiro(l.preco)}</span><span class="stock ${l.estoque ? '' : 'zero'}">${l.estoque ? `${l.estoque} em estoque` : 'Esgotado'}</span></div>
      <div class="book-actions"><button class="btn secondary" data-action="${l.estoque ? 'reservar' : 'acompanhar'}" data-id="${esc(l.id)}">${l.estoque ? 'Reservar' : 'Avise-me'}</button><button class="wish-button ${desejos.has(l.id) ? 'saved' : ''}" data-action="desejo" data-id="${esc(l.id)}" aria-label="Guardar ${esc(l.titulo)} na lista de desejos" aria-pressed="${desejos.has(l.id)}">${desejos.has(l.id) ? '♥' : '♡'}</button></div></div>
    </article>`).join('') : vazio('Nenhum livro encontrado. Tente outro título, autor ou gênero.');
}

function renderizarVisita() {
  $('#reservas').innerHTML = estado.reservas.length ? `<div class="list">${estado.reservas.map(r => `<article class="list-item"><div class="row"><h3>${esc(r.titulo)}</h3><span class="status ${esc(r.status)}">${esc(r.status)}</span></div><p class="subtle">Retirada até ${esc(data(r.prazo))}${r.embrulho ? ' · Presente com embrulho especial' : ''}</p>${r.status !== 'cancelada' ? `<div class="row"><button class="btn link" data-action="prazo" data-id="${esc(r.id)}">Alterar prazo</button><button class="btn secondary" data-action="cancelar" data-id="${esc(r.id)}">Cancelar reserva</button></div>` : ''}</article>`).join('')}</div>` : vazio('Sua próxima leitura ainda não está reservada. Escolha um livro no catálogo.');
  $('#loja-info').innerHTML = `<p><span class="label">Funcionamento</span><br><strong>${esc(estado.loja.horario)}</strong></p><p><span class="label">Lotação atual</span><br><strong>${estado.loja.lotacao} pessoas na loja</strong></p>`;
  $('#fila-posicao').textContent = estado.fila.posicao ? `Sua posição na fila: ${estado.fila.posicao}.` : 'Entre na fila ao chegar à loja.';
  $('#fila-button').disabled = Boolean(estado.fila.posicao);
  const selecionado = $('#agendamento-horario').value;
  $('#agendamento-horario').innerHTML = `<option value="">${estado.horarios.length ? 'Escolha um horário' : 'Nenhum horário disponível'}</option>` + estado.horarios.map(h => `<option value="${esc(h.id)}">${esc(h.livreiro)} · ${esc(data(h.quando))}</option>`).join('');
  if (estado.horarios.some(h => h.id === selecionado)) $('#agendamento-horario').value = selecionado;
  $('#agendamento-form button').disabled = !estado.horarios.length;
  $('#agendamentos').innerHTML = estado.agendamentos.map(a => `<div class="list-item"><strong>${esc(a.livreiro)}</strong><div class="subtle">Agendado para ${esc(data(a.quando))}</div></div>`).join('');
}

function renderizarComunidade() {
  $('#eventos').innerHTML = estado.eventos.length ? estado.eventos.map(e => `<article class="list-item"><span class="label">${esc(data(e.quando))}</span><h3>${esc(e.titulo)}</h3><p class="subtle">${esc(e.local)}${e.vagas !== null ? ` · ${e.vagas} vagas disponíveis` : ''}</p><button class="btn ${e.inscrito ? 'secondary' : ''}" data-action="inscrever" data-id="${esc(e.id)}" ${e.inscrito || e.vagas === 0 || new Date(e.quando) <= new Date() ? 'disabled' : ''}>${e.inscrito ? 'Inscrição confirmada ✓' : (e.vagas === 0 ? 'Sem vagas' : 'Quero participar')}</button></article>`).join('') : vazio('A loja ainda não divulgou novos eventos.');
  const rascunhos = new Map([...document.querySelectorAll('.opiniao-form')].map(f => [f.dataset.id, f.elements.texto.value]));
  $('#clubes').innerHTML = estado.clubes.length ? estado.clubes.map(c => `<article class="list-item"><h3>${esc(c.nome)}</h3><p class="subtle">${c.membros} ${c.membros === 1 ? 'participante' : 'participantes'} · Um espaço para trocar leituras.</p>${c.participando ? '<span class="status">Você participa deste clube</span>' : `<button class="btn secondary" data-action="clube" data-id="${esc(c.id)}">Participar do clube</button>`}${c.opinioes.map(o => `<div class="opinion"><span class="label">Leitor ${esc(o.cliente.slice(0,8))}</span><p>${esc(o.texto)}</p></div>`).join('')}${c.participando ? `<form class="opiniao-form" data-id="${esc(c.id)}" style="margin-top:18px"><div class="field"><label for="opiniao-${esc(c.id)}">Compartilhe sua opinião</label><textarea id="opiniao-${esc(c.id)}" name="texto" required placeholder="O que essa leitura deixou com você?">${esc(rascunhos.get(c.id) || '')}</textarea></div><button class="btn" type="submit">Publicar opinião</button></form>` : ''}</article>`).join('') : vazio('Os clubes de leitura aparecerão aqui.');
}

function renderizarPerfil(generos) {
  const f = estado.fidelidade;
  $('#fidelidade').innerHTML = `<div class="loyalty-card"><div class="brand">entrelinhas</div><span class="label" style="color:#ced7c3">Seu saldo de fidelidade</span><strong>${f.saldo} <span style="font:14px system-ui">pontos</span></strong><div class="number">${esc(f.cartao.numero)}</div></div>`;
  $('#cupons').innerHTML = f.cupons.length ? f.cupons.map(c => `<div class="coupon"><strong>${esc(c.codigo)}</strong><div class="subtle">${esc(c.termos)}</div></div>`).join('') : vazio('Seus cupons da loja aparecerão aqui.');
  $('#historico').innerHTML = estado.historico.length ? estado.historico.map(c => `<article class="list-item"><h3>${esc(c.livro.titulo)}</h3><p class="subtle">Compra na loja física · ${esc(data(c.data))}</p><span class="status">${c.pontos} pontos recebidos</span>${c.expira_em ? `<p class="subtle">Validade dos pontos: ${esc(data(c.expira_em))}</p>` : ''}</article>`).join('') : vazio('Você ainda não tem compras físicas registradas.');
  $('#desejos').innerHTML = estado.desejos.length ? estado.desejos.map(l => `<article class="list-item row"><div><h3>${esc(l.titulo)}</h3><span class="subtle">${esc(l.autor)}</span></div><button class="btn secondary" data-action="detalhes" data-id="${esc(l.id)}">Ver livro</button></article>`).join('') : vazio('Toque no coração de um livro para guardá-lo aqui.');
  if (!preferenciasDirty) {
    const temas = {estoque:'Reposição de livros', reservas:'Minhas reservas', fidelidade:'Pontos e cupons', eventos:'Eventos e encontros'};
    $('#preferencias-opcoes').innerHTML = `<fieldset><legend>Gêneros favoritos</legend><div class="form-options">${generos.map(g => `<label class="check"><input type="checkbox" name="generos" value="${esc(g)}" ${estado.cliente.generos.some(s => s.toLocaleLowerCase('pt-BR') === g.toLocaleLowerCase('pt-BR')) ? 'checked' : ''}>${esc(g)}</label>`).join('')}</div></fieldset><fieldset><legend>Quero receber avisos sobre</legend><div class="form-options">${Object.entries(temas).map(([valor, nome]) => `<label class="check"><input type="checkbox" name="temas" value="${valor}" ${estado.cliente.temas_notificacao === null || estado.cliente.temas_notificacao.includes(valor) ? 'checked' : ''}>${nome}</label>`).join('')}</div></fieldset>`;
  }
}

function renderizar() {
  $('#hero-hours').textContent = estado.loja.horario;
  $('#hero-occupancy').textContent = `${estado.loja.lotacao} pessoas na loja agora`;
  const generos = [...new Set(estado.livros.map(l => l.genero))].sort();
  const generoAtual = $('#genero').value;
  $('#genero').innerHTML = '<option value="">Todos os gêneros</option>' + generos.map(g => `<option value="${esc(g)}">${esc(g)}</option>`).join('');
  $('#genero').value = generoAtual;
  renderizarCatalogo(); renderizarVisita(); renderizarComunidade(); renderizarPerfil(generos);
  $('#recomendacoes').innerHTML = estado.recomendacoes.length ? `<div class="suggestions">${estado.recomendacoes.map(l => `<button class="suggestion" data-action="detalhes" data-id="${esc(l.id)}"><strong>${esc(l.titulo)}</strong><span class="subtle">${esc(l.autor)} · ${esc(l.genero)}</span></button>`).join('')}</div>` : vazio('Escolha seus gêneros em Meu perfil para descobrir novas leituras.');
  const count = $('#notification-count'); count.textContent = estado.notificacoes.length; count.hidden = !estado.notificacoes.length;
  $('#notificacoes').innerHTML = estado.notificacoes.length ? [...estado.notificacoes].reverse().map(n => `<article class="list-item"><span class="label">${esc(n.tema)} · ${esc(data(n.data))}</span><p style="margin:8px 0 0">${esc(n.mensagem)}</p></article>`).join('') : vazio('Nenhuma notificação por enquanto.');
}

async function abrirLivro(id) {
  const l = await api(`/api/livros/${encodeURIComponent(id)}`);
  $('#book-details').innerHTML = `<div class="dialog-heading"><div><div class="eyebrow">${esc(l.genero)}</div><h2 id="book-title">${esc(l.titulo)}</h2></div><button class="close" data-close aria-label="Fechar">×</button></div><p class="subtle">${esc(l.autor)}</p><p>${esc(l.sinopse || 'Sinopse não informada.')}</p><div class="details-grid"><div><span class="label">Preço na loja</span><strong>${dinheiro(l.preco)}</strong></div><div><span class="label">Disponibilidade</span><strong>${l.estoque} exemplares</strong></div><div><span class="label">Seção</span><strong>${esc(l.secao || 'Não informada')}</strong></div><div><span class="label">Prateleira</span><strong>${esc(l.prateleira || 'Não informada')}</strong></div></div><h3>Quem leu, conta</h3>${l.avaliacoes?.length ? l.avaliacoes.map(a => `<div class="opinion"><span class="label">${esc(a.cliente)}</span><p>${esc(a.texto)}</p></div>`).join('') : '<p class="subtle">Este livro ainda não tem avaliações.</p>'}<div class="details-actions"><button class="btn" data-action="${l.estoque ? 'reservar' : 'acompanhar'}" data-id="${esc(l.id)}">${l.estoque ? 'Reservar para retirada' : 'Avise-me quando chegar'}</button><button class="btn secondary" data-action="desejo" data-id="${esc(l.id)}">♡ Guardar</button></div>`;
  $('#book-dialog').showModal();
}

function abrirReserva(id) {
  if (!estado) return;
  const livro = estado.livros.find(l => l.id === id);
  $('#book-dialog').close();
  $('#reserve-form').reset();
  $('#reserve-form').elements.livro_id.value = id;
  $('#reserve-book').textContent = `${livro.titulo} · ${livro.autor}`;
  $('#reserve-deadline').min = localInput(new Date());
  $('#reserve-dialog').showModal();
}

function pararCamera() {
  clearTimeout(cameraTimer); cameraTimer = null;
  if (stream) stream.getTracks().forEach(track => track.stop());
  stream = null; $('#camera').srcObject = null; $('#camera').hidden = true;
}

async function iniciarCamera() {
  const status = $('#camera-status');
  if (!('BarcodeDetector' in window) || !navigator.mediaDevices?.getUserMedia) {
    status.textContent = 'A câmera não pode ler códigos neste navegador. Informe o número abaixo ou use um leitor USB.';
    return;
  }
  pararCamera();
  try {
    const detector = new BarcodeDetector({formats:['ean_13','ean_8','code_128','upc_a']});
    stream = await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}}});
    if (!$('#scan-dialog').open) { pararCamera(); return; }
    const video = $('#camera'); video.srcObject = stream; video.hidden = false;
    await video.play(); status.textContent = 'Aponte para o código de barras do livro.';
    const detectar = async () => {
      if (!stream) return;
      try {
        const codigos = await detector.detect(video);
        if (codigos.length) {
          const l = await api(`/api/codigo/${encodeURIComponent(codigos[0].rawValue)}`);
          $('#scan-dialog').close(); await abrirLivro(l.id); return;
        }
      } catch (erro) { status.textContent = 'Ainda não encontramos o livro. Tente novamente ou informe o código.'; }
      if (stream) cameraTimer = setTimeout(detectar, 450);
    };
    detectar();
  } catch (erro) { pararCamera(); status.textContent = 'Não foi possível acessar a câmera. Você pode informar o código abaixo.'; }
}

document.addEventListener('click', event => {
  const close = event.target.closest('[data-close]');
  if (close) { close.closest('dialog').close(); return; }
  const tab = event.target.closest('[data-tab]');
  if (tab) { trocarAba(tab.dataset.tab); return; }
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const {action, id} = button.dataset;
  executar(button, async () => {
    if (action === 'atualizar') { await atualizar(); return; }
    if (action === 'detalhes') { await abrirLivro(id); return; }
    if (action === 'reservar') { abrirReserva(id); return; }
    if (action === 'notificacoes') { $('#notifications-dialog').showModal(); return; }
    if (action === 'escanear') { $('#camera-status').textContent = ''; $('#scan-dialog').showModal(); return; }
    if (action === 'camera') { await iniciarCamera(); return; }
    if (action === 'prazo') {
      const r = estado.reservas.find(r => r.id === id);
      $('#deadline-form').elements.reserva_id.value = id;
      $('#new-deadline').value = localInput(r.prazo); $('#new-deadline').min = localInput(new Date());
      $('#deadline-dialog').showModal(); return;
    }
    const acoes = {
      desejo: ['/api/desejos', {livro_id:id}, 'Livro guardado na sua lista de desejos.'],
      acompanhar: ['/api/avisos-estoque', {livro_id:id}, 'Você receberá um aviso de reposição conforme suas preferências.'],
      cancelar: [`/api/reservas/${encodeURIComponent(id)}/cancelar`, undefined, 'Reserva cancelada.'],
      fila: ['/api/fila', undefined, 'Você entrou na fila virtual.'],
      inscrever: [`/api/eventos/${encodeURIComponent(id)}/inscricoes`, undefined, 'Sua inscrição está confirmada.'],
      clube: [`/api/clubes/${encodeURIComponent(id)}/participar`, undefined, 'Bem-vindo ao clube de leitura!']
    };
    const tarefa = acoes[action];
    if (tarefa) { await api(tarefa[0], 'POST', tarefa[1]); await atualizar(); avisar(tarefa[2]); }
  });
});

document.addEventListener('submit', event => {
  const form = event.target;
  event.preventDefault();
  if (form.id === 'filtros') { renderizarCatalogo(); return; }
  executar(form.querySelector('button[type="submit"]'), async () => {
    const values = new FormData(form);
    if (form.id === 'reserve-form') {
      await api('/api/reservas', 'POST', {livro_id:values.get('livro_id'), prazo:new Date(values.get('prazo')).toISOString(), embrulho:$('#reserve-gift').checked});
      $('#reserve-dialog').close(); trocarAba('visita'); avisar('Livro reservado. Acompanhe a preparação por aqui.');
    } else if (form.id === 'deadline-form') {
      await api(`/api/reservas/${encodeURIComponent(values.get('reserva_id'))}`, 'PATCH', {prazo:new Date(values.get('prazo')).toISOString()});
      $('#deadline-dialog').close(); avisar('Prazo de retirada atualizado.');
    } else if (form.id === 'scan-form') {
      const l = await api(`/api/codigo/${encodeURIComponent(values.get('codigo').trim())}`);
      $('#scan-dialog').close(); await abrirLivro(l.id); return;
    } else if (form.id === 'agendamento-form') {
      await api('/api/agendamentos', 'POST', {horario_id:values.get('horario_id')}); avisar('Atendimento agendado.');
    } else if (form.id === 'preferencias-form') {
      await api('/api/preferencias', 'PATCH', {generos:values.getAll('generos'), temas_notificacao:values.getAll('temas')});
      preferenciasDirty = false; avisar('Suas preferências foram salvas.');
    } else if (form.classList.contains('opiniao-form')) {
      await api(`/api/clubes/${encodeURIComponent(form.dataset.id)}/opinioes`, 'POST', {texto:values.get('texto')});
      form.elements.texto.value = ''; avisar('Opinião publicada.');
    }
    await atualizar();
  });
});

$('#busca').addEventListener('input', renderizarCatalogo);
$('#genero').addEventListener('change', renderizarCatalogo);
$('#lancamentos').addEventListener('change', renderizarCatalogo);
$('#preferencias-form').addEventListener('change', () => { preferenciasDirty = true; });
$('#scan-dialog').addEventListener('close', pararCamera);
window.addEventListener('pagehide', pararCamera);
atualizar();
setInterval(() => { if (!document.hidden) atualizar(); }, 15000);
