/**
 * =================================================================
 * SISTEMA DE CHAT UNIFICADO - NOTIFICAÇÕES PARA COLABORADORES E SUPORTE
 * VERSÃO COMPATÍVEL COM initial.html E todos_chamados.html
 * =================================================================
 */

// ✅ CONFIGURAÇÕES DE INTERVALO ATUALIZADAS - CORREÇÃO CRÍTICA
const INTERVALOS = {
    CHAT_SEGUNDO_PLANO: 2 * 60 * 1000,      // 2 minutos (ÚNICO INTERVALO PRINCIPAL)
    REFRESH_DADOS: 5 * 60 * 1000,           // 5 minutos (apenas para dados gerais)
    VERIFICACAO_MENSAGENS: 30 * 1000,       // 30 segundos para verificações rápidas de mensagens
    TIMEOUT_CONEXAO: 10 * 1000              // 10 segundos para timeout
};

// --- Variáveis Globais ---
let chamadoAtual = null;
let sequenciaAtiva = false;
let chatModalInstance = null;
let carregandoMensagens = false;
let ultimaMensagemId = null;
let intervaloAtualizacao = null;
let intervaloVerificacaoAutomatica = null;
let indicadorNovasMensagens = false;
let modalAberto = false;
let ultimaMensagemVisualizadaId = null;
let sistemaInicializado = false;
let tipoUsuario = null;

// ✅ CORREÇÃO: Função para mostrar indicador de novas mensagens
function mostrarIndicadorNovasMensagens() {
    console.log('🔄 Mostrando indicador de novas mensagens...');
    
    const indicador = document.getElementById('novasMensagensIndicador');
    
    if (indicador && !modalAberto) {
        indicador.style.display = 'block';
        indicador.style.visibility = 'visible';
        indicador.style.opacity = '1';
        
        indicador.classList.add('pulse-animation');
        
        indicadorNovasMensagens = true;
        
        console.log('🔴 Botão pulsante de novas mensagens MOSTRADO visualmente');
        
        void indicador.offsetWidth;
    } else {
        console.log('❌ Não foi possível mostrar o indicador:', {
            indicadorExiste: !!indicador,
            modalAberto: modalAberto
        });
    }
}

// ✅ FUNÇÃO: Mostrar indicador de digitação
function mostrarIndicadorDigitacao() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message message-bot';
        typingDiv.id = 'typingIndicator';
        typingDiv.innerHTML = `
            <div class="message-content">
                <div class="message-header">BOT_HYPER</div>
                <div class="message-text">
                    <span class="typing-dots">
                        <span>.</span>
                        <span>.</span>
                        <span>.</span>
                    </span>
                </div>
                <div class="message-time">${new Date().toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})}</div>
            </div>
        `;
        chatMessages.appendChild(typingDiv);
        scrollParaFinal();
    }
}

// ✅ FUNÇÃO: Remover indicador de digitação
function removerIndicadorDigitacao() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// ✅ CORREÇÃO: Função unificada para verificar notificações (2 minutos)
async function verificarNotificacoesAutomaticas() {
    if (!chamadoAtual) {
        return;
    }
    
    try {
        console.log('🔔 Verificando notificações automáticas (2min)...');
        
        const response = await fetch('/api/verificar-notificacoes/', {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (response.ok) {
            const result = await response.json();
            
            if (result.success) {
                console.log(`📊 Notificações: ${result.total_nao_lidas} não lidas (tipo: ${result.tipo_usuario})`);
                
                // ✅ CORREÇÃO: Mostrar indicador apenas se há notificações não lidas
                if (result.total_nao_lidas > 0 && !modalAberto) {
                    console.log('🔴 Mostrando indicador de notificações não lidas');
                    mostrarIndicadorNovasMensagens();
                }
                
                return result;
            }
        }
    } catch (error) {
        console.error('❌ Erro ao verificar notificações automáticas:', error);
    }
    return null;
}

// ✅ CORREÇÃO CRÍTICA: Sistema de verificações automáticas UNIFICADO (2 minutos)
function iniciarVerificacoesAutomaticas() {
    console.log('⏰ Iniciando sistema de verificações automáticas (2min)...');
    
    pararVerificacoesAutomaticas();
    
    // ✅ CORREÇÃO: ÚNICO intervalo de 2 minutos para tudo
    intervaloVerificacaoAutomatica = setInterval(async () => {
        if (chamadoAtual && !modalAberto) {
            await verificarNotificacoesAutomaticas();
            await verificarNovasMensagensInteligente();
        }
    }, INTERVALOS.CHAT_SEGUNDO_PLANO); // 2 minutos
    
    console.log('✅ Verificações automáticas iniciadas (2 minutos)');
}

// ✅ FUNÇÃO: Parar verificações automáticas
function pararVerificacoesAutomaticas() {
    if (intervaloVerificacaoAutomatica) {
        clearInterval(intervaloVerificacaoAutomatica);
        intervaloVerificacaoAutomatica = null;
        console.log('⏹️ Verificações automáticas paradas');
    }
}

// ✅ FUNÇÃO: Sistema de sincronização entre abas/páginas
function inicializarSincronizacaoEntreAbas() {
    console.log('🔄 Inicializando sincronização entre abas/páginas...');
    
    // Sincronizar quando o storage muda (outra aba/página)
    window.addEventListener('storage', function(e) {
        console.log('📦 Evento de storage detectado:', e.key);
        
        if (e.key === 'chamadoAtual' && e.newValue) {
            console.log('🔄 Sincronizando chamado atual entre abas...');
            try {
                const novoChamado = JSON.parse(e.newValue);
                if (novoChamado && novoChamado.chamado_id !== chamadoAtual?.chamado_id) {
                    chamadoAtual = novoChamado;
                    console.log('✅ Chamado sincronizado:', chamadoAtual?.chamado_legivel);
                    
                    // Reiniciar sistema de atualização
                    reiniciarSistemaAtualizacao();
                }
            } catch (error) {
                console.error('❌ Erro ao sincronizar chamado:', error);
            }
        }
        
        if (e.key === 'ultimaVisualizacao' && e.newValue) {
            console.log('🔄 Sincronizando estado de visualização...');
            try {
                const novoEstado = JSON.parse(e.newValue);
                if (novoEstado && novoEstado.ultimaMensagemId !== ultimaMensagemVisualizadaId) {
                    ultimaMensagemVisualizadaId = novoEstado.ultimaMensagemId;
                    console.log('✅ Estado de visualização sincronizado:', ultimaMensagemVisualizadaId);
                }
            } catch (error) {
                console.error('❌ Erro ao sincronizar estado de visualização:', error);
            }
        }
        
        if (e.key === 'indicadorNovasMensagens') {
            console.log('🔄 Sincronizando indicador de mensagens...');
            const deveMostrar = e.newValue === 'true';
            
            if (deveMostrar && !indicadorNovasMensagens && !modalAberto) {
                console.log('🔴 Mostrando indicador sincronizado');
                mostrarIndicadorNovasMensagens();
            }
        }

        if (e.key === 'tipoUsuario' && e.newValue) {
            console.log('🔄 Sincronizando tipo de usuário...');
            tipoUsuario = e.newValue;
            console.log('✅ Tipo de usuário sincronizado:', tipoUsuario);
        }
    });
}

// ✅ FUNÇÃO: Reiniciar sistema de atualização quando necessário
function reiniciarSistemaAtualizacao() {
    console.log('🔄 Reiniciando sistema de atualização...');
    
    // Parar sistema atual
    pararAtualizacaoAutomatica();
    pararVerificacoesAutomaticas();
    
    // Recarregar estado atual
    carregarEstadoAtual();
    
    // Reiniciar verificações
    if (chamadoAtual) {
        iniciarAtualizacaoAutomatica();
        iniciarVerificacoesAutomaticas();
        
        // Verificar mensagens pendentes imediatamente
        setTimeout(() => {
            verificarNovasMensagensInteligente();
        }, 1000);
    }
}

// ✅ FUNÇÃO MELHORADA: Carregar estado atual de forma mais robusta
function carregarEstadoAtual() {
    console.log('📂 Carregando estado atual do sistema...');
    
    try {
        // Carregar chamado atual
        const chamadoSalvo = localStorage.getItem('chamadoAtual');
        if (chamadoSalvo) {
            chamadoAtual = JSON.parse(chamadoSalvo);
            console.log('✅ Chamado carregado:', chamadoAtual?.chamado_legivel);
        }
        
        // Carregar estado de visualização
        const estadoSalvo = localStorage.getItem('ultimaVisualizacao');
        if (estadoSalvo) {
            const estado = JSON.parse(estadoSalvo);
            ultimaMensagemVisualizadaId = estado.ultimaMensagemId;
            console.log('✅ Estado de visualização carregado:', ultimaMensagemVisualizadaId);
        }
        
        // Carregar estado do indicador
        const indicadorSalvo = localStorage.getItem('indicadorNovasMensagens');
        indicadorNovasMensagens = indicadorSalvo === 'true';
        console.log('✅ Estado do indicador carregado:', indicadorNovasMensagens);
        
        // ✅ NOVO: Carregar tipo de usuário
        const tipoUsuarioSalvo = localStorage.getItem('tipoUsuario');
        if (tipoUsuarioSalvo) {
            tipoUsuario = tipoUsuarioSalvo;
            console.log('✅ Tipo de usuário carregado:', tipoUsuario);
        }
        
        // Se há indicador ativo, mostrar visualmente
        if (indicadorNovasMensagens && !modalAberto) {
            console.log('🔴 Restaurando indicador visual do estado salvo...');
            setTimeout(() => {
                mostrarIndicadorNovasMensagens();
            }, 500);
        }
        
    } catch (error) {
        console.error('❌ Erro ao carregar estado atual:', error);
        resetarEstadoSistema();
    }
}

// ✅ FUNÇÃO: Resetar estado do sistema
function resetarEstadoSistema() {
    console.log('🔄 Resetando estado do sistema...');
    
    chamadoAtual = null;
    ultimaMensagemVisualizadaId = null;
    indicadorNovasMensagens = false;
    tipoUsuario = null;
    
    localStorage.removeItem('chamadoAtual');
    localStorage.removeItem('ultimaVisualizacao');
    localStorage.removeItem('indicadorNovasMensagens');
    localStorage.removeItem('tipoUsuario');
    
    // ✅ CORREÇÃO: Não remover indicador visual aqui
    pararAtualizacaoAutomatica();
    pararVerificacoesAutomaticas();
}

// ✅ FUNÇÃO MELHORADA: Salvar estado com sincronização
function salvarEstadoSistema() {
    try {
        // Salvar chamado atual
        if (chamadoAtual) {
            localStorage.setItem('chamadoAtual', JSON.stringify(chamadoAtual));
        }
        
        // Salvar estado de visualização
        const estadoVisualizacao = {
            ultimaMensagemId: ultimaMensagemVisualizadaId,
            timestamp: Date.now(),
            chamadoId: chamadoAtual ? chamadoAtual.chamado_id : null
        };
        localStorage.setItem('ultimaVisualizacao', JSON.stringify(estadoVisualizacao));
        
        // Salvar estado do indicador
        localStorage.setItem('indicadorNovasMensagens', indicadorNovasMensagens.toString());
        
        // ✅ NOVO: Salvar tipo de usuário
        if (tipoUsuario) {
            localStorage.setItem('tipoUsuario', tipoUsuario);
        }
        
        console.log('💾 Estado do sistema salvo com sucesso');
        
    } catch (error) {
        console.error('❌ Erro ao salvar estado do sistema:', error);
    }
}

// ✅ CORREÇÃO: Função para garantir que chamadoAtual sempre tenha valor válido
function garantirChamadoAtual() {
    if (!chamadoAtual) {
        try {
            const chamadoSalvo = localStorage.getItem('chamadoAtual');
            if (chamadoSalvo) {
                chamadoAtual = JSON.parse(chamadoSalvo);
                console.log('🔄 ChamadoAtual recuperado do localStorage:', chamadoAtual?.chamado_legivel);
            }
        } catch (error) {
            console.error('❌ Erro ao recuperar chamadoAtual:', error);
        }
    }
    return chamadoAtual;
}

// ✅ FUNÇÃO: Iniciar atualização automática ATUALIZADA
function iniciarAtualizacaoAutomatica() {
    console.log('🔄 Iniciando atualização automática...');
    
    // Parar intervalo anterior se existir
    pararAtualizacaoAutomatica();
    
    // ✅ ATUALIZADO: Verificar a cada 5 minutos (apenas para dados gerais)
    intervaloAtualizacao = setInterval(() => {
        if (chamadoAtual && !modalAberto) {
            console.log('🔄 Atualização de dados gerais (5min)');
        }
    }, INTERVALOS.REFRESH_DADOS);
    
    console.log('✅ Atualização automática iniciada (5 minutos)');
}

// ✅ FUNÇÃO: Parar atualização automática
function pararAtualizacaoAutomatica() {
    if (intervaloAtualizacao) {
        clearInterval(intervaloAtualizacao);
        intervaloAtualizacao = null;
        console.log('⏹️ Atualização automática parada');
    }
}

// ✅ FUNÇÃO: Atualizar última visualização
function atualizarUltimaVisualizacao() {
    if (!chamadoAtual) return;
    
    // Buscar a última mensagem no DOM
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    const mensagens = chatMessages.querySelectorAll('[data-message-id]');
    if (mensagens.length > 0) {
        const ultimaMensagem = mensagens[mensagens.length - 1];
        const messageId = ultimaMensagem.getAttribute('data-message-id');
        
        if (messageId && messageId !== ultimaMensagemVisualizadaId) {
            ultimaMensagemVisualizadaId = messageId;
            salvarEstadoSistema();
            console.log('👀 Última mensagem visualizada atualizada:', messageId);
        }
    }
}

// ✅ FUNÇÃO: Detectar mudanças de página
function detectarMudancasDePagina() {
    // Observar mudanças no DOM que podem indicar navegação SPA
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                // Verificar se elementos críticos foram adicionados/removidos
                const chatModalEl = document.getElementById('chatModal');
                if (!chatModalEl && chatModalInstance) {
                    console.log('🔄 Página mudou, reiniciando sistema...');
                    reiniciarSistemaAtualizacao();
                }
            }
        });
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}

// ✅ FUNÇÃO MELHORADA: Inicialização principal
document.addEventListener('DOMContentLoaded', function () {
    console.log('🚀 Inicializando sistema de chat (NOTIFICAÇÕES PARA TODOS)...');
    console.log('📅 Intervalos configurados:', {
        'Chat em segundo plano': `${INTERVALOS.CHAT_SEGUNDO_PLANO/1000}s`,
        'Refresh de dados': `${INTERVALOS.REFRESH_DADOS/1000}s`,
        'Verificação mensagens': `${INTERVALOS.VERIFICACAO_MENSAGENS/1000}s`
    });
    
    // Prevenir múltiplas inicializações
    if (sistemaInicializado) {
        console.log('⚠️ Sistema já inicializado, ignorando...');
        return;
    }
    
    sistemaInicializado = true;
    
    inicializarSincronizacaoEntreAbas();
    carregarEstadoAtual();
    
    const chatModalEl = document.getElementById('chatModal');
    if (!chatModalEl) {
        console.warn('Elemento #chatModal não encontrado. Chat desativado.');
        return;
    }
    
    try {
        chatModalInstance = new bootstrap.Modal(chatModalEl);
        console.log('✅ Modal do chat inicializado com sucesso');
    } catch (error) {
        console.error('❌ Erro ao inicializar modal:', error);
        return;
    }

    // ✅ CORREÇÃO: Carregar chamado salvo de forma assíncrona
    setTimeout(() => {
        carregarChamadoSalvo().then(() => {
            console.log('✅ Carregamento inicial completo');
            
            // ✅ CORREÇÃO: Iniciar sistema apenas se há chamado ativo
            if (chamadoAtual) {
                console.log('📞 Chamado ativo encontrado, iniciando sistema...');
                iniciarAtualizacaoAutomatica();
                iniciarVerificacoesAutomaticas();
                
                // Verificar mensagens pendentes imediatamente
                setTimeout(() => {
                    verificarNovasMensagensInteligente();
                }, 2000);
            }
        });
    }, 100);

    // --- Listeners do Chat ---
    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) {
        sendBtn.addEventListener('click', enviarMensagemChat);
    }

    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                enviarMensagemChat();
            }
        });
    }

    // ✅ CORREÇÃO MELHORADA: Listener para quando o modal é aberto
    chatModalEl.addEventListener('shown.bs.modal', function () {
        console.log('📱 Modal do chat aberto');
        modalAberto = true;
        
        carregarEstadoAtual();
        
        setTimeout(() => {
            scrollParaFinal();
        }, 100);
        
        if (messageInput) {
            messageInput.focus();
        }

        // ✅ CORREÇÃO CRÍTICA: Remover indicador visual ao abrir o modal
        console.log('📱 Modal aberto - removendo indicador visual');
        const indicador = document.getElementById('novasMensagensIndicador');
        if (indicador) {
            indicador.style.display = 'none';
            indicador.classList.remove('pulse-animation');
            indicadorNovasMensagens = false;
            salvarEstadoSistema();
            console.log('🟢 Botão pulsante REMOVIDO (chat visualizado)');
        }
        
        atualizarUltimaVisualizacao();
        
        if (chamadoAtual) {
            setTimeout(() => {
                verificarNotificacoesAutomaticas();
            }, 1000);
        }
        
        if (chamadoAtual && !sequenciaAtiva) {
            setTimeout(() => {
                iniciarSequenciaBot();
            }, 1500);
        }
        
        if (chamadoAtual) {
            setTimeout(() => {
                carregarMensagensChamado(chamadoAtual.chamado_id);
                verificarNovasMensagensInteligente();
            }, 500);
        }
    });

    chatModalEl.addEventListener('hidden.bs.modal', function () {
        console.log('📱 Modal do chat fechado');
        modalAberto = false;
        
        atualizarUltimaVisualizacao();
        salvarEstadoSistema();
        
        console.log('🔄 Atualização automática continua rodando em segundo plano');
        
        if (chamadoAtual) {
            setTimeout(() => {
                verificarNovasMensagensInteligente();
            }, 1000);
        }
    });

    const floatingBtn = document.getElementById('chatFloatingBtn');
    if (floatingBtn) {
        floatingBtn.addEventListener('click', function () {
            console.log('🔄 Abrindo modal do chat via botão flutuante');
            carregarEstadoAtual();
            
            if (chamadoAtual) {
                console.log('✅ Chamado ativo encontrado, abrindo chat...');
                chatModalInstance.show();
            } else {
                console.log('ℹ️ Nenhum chamado ativo, mas abrindo chat para visualização...');
                chatModalInstance.show();
                
                const chatMessages = document.getElementById('chatMessages');
                const initialState = document.querySelector('.chat-initial-state');
                
                if (chatMessages) {
                    chatMessages.innerHTML = '';
                }
                
                if (initialState) {
                    initialState.style.display = 'flex';
                    initialState.innerHTML = `
                        <i class="bi bi-chat-square-text"></i>
                        <h5>Nenhum chamado ativo</h5>
                        <p>Crie um novo chamado para iniciar uma conversa com o suporte.</p>
                    `;
                }
            }
        });
    }

    const chamadoForm = document.getElementById('chamadoForm');
    if (chamadoForm) {
        chamadoForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            await enviarChamado();
        });
    }
    
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.addEventListener('scroll', function() {
            const isNearBottom = chatMessages.scrollHeight - chatMessages.scrollTop - chatMessages.clientHeight < 100;
            if (isNearBottom && modalAberto) {
                atualizarUltimaVisualizacao();
            }
        });
    }
    
    // ✅ CORREÇÃO: Verificar mensagens rapidamente (30s) mas notificações apenas a cada 2min
    setInterval(() => {
        if (chamadoAtual && !modalAberto) {
            verificarNovasMensagensInteligente();
        }
    }, INTERVALOS.VERIFICACAO_MENSAGENS);
    
    window.addEventListener('beforeunload', function() {
        console.log('💾 Salvando estado antes de descarregar página...');
        salvarEstadoSistema();
    });
    
    detectarMudancasDePagina();
});

// ✅ FUNÇÃO MELHORADA: Verificação de novas mensagens - INTERVALOS ATUALIZADOS
async function verificarNovasMensagensInteligente() {
    carregarEstadoAtual();
    
    if (!chamadoAtual) {
        console.log('❌ Nenhum chamado ativo para verificar mensagens');
        return;
    }
    
    try {
        const url = `/chamado/${chamadoAtual.chamado_id}/verificar-mensagens-inteligente/?ultima_visualizada_id=${ultimaMensagemVisualizadaId || ''}`;
        
        console.log(`🔍 Verificando novas mensagens inteligente: ${url}`);
        
        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            console.log(`📊 Resultado da verificação: ${result.total_novas} novas, última ID: ${result.ultima_visualizada_id}`);
            
            if (result.chamado_status === 'resolvido') {
                console.log('✅ Chamado resolvido, removendo indicador e desativando sistema...');
                // ✅ CORREÇÃO: Remover indicador visual apenas se estiver visível
                const indicador = document.getElementById('novasMensagensIndicador');
                if (indicador && indicador.style.display !== 'none') {
                    indicador.style.display = 'none';
                    indicador.classList.remove('pulse-animation');
                    console.log('🟢 Botão pulsante REMOVIDO (chamado resolvido)');
                }
                desativarChat();
                resetarEstadoSistema();
                return;
            }
            
            const haMensagensNaoVisualizadas = result.total_novas > 0;
            
            if (haMensagensNaoVisualizadas) {
                console.log(`✅ ${result.total_novas} nova(s) mensagem(ns) não visualizada(s) encontrada(s)`);
                
                if (!modalAberto) {
                    ultimaMensagemVisualizadaId = result.ultima_visualizada_id;
                    indicadorNovasMensagens = true;
                    salvarEstadoSistema();
                    
                    console.log(`🔴 Mostrando indicador: modalAberto=${modalAberto}, mensagensNaoVisualizadas=${haMensagensNaoVisualizadas}`);
                    
                    mostrarIndicadorNovasMensagens();
                }
                
                if (modalAberto) {
                    result.novas_mensagens.forEach(msg => {
                        adicionarMensagemDOM(msg.mensagem, msg.remetente, msg.hora, msg.id);
                    });
                    scrollParaFinal();
                    atualizarUltimaVisualizacao();
                }
            } else {
                console.log('✅ Nenhuma nova mensagem não visualizada encontrada');
                
                if (result.ultima_visualizada_id && result.ultima_visualizada_id !== ultimaMensagemVisualizadaId) {
                    console.log(`🔄 Atualizando ID de referência: ${ultimaMensagemVisualizadaId} -> ${result.ultima_visualizada_id}`);
                    ultimaMensagemVisualizadaId = result.ultima_visualizada_id;
                    salvarEstadoSistema();
                }
            }
        } else {
            console.error('❌ Erro na resposta da API:', result.message);
        }
    } catch (error) {
        console.error('❌ Erro ao verificar novas mensagens inteligente:', error);
    }
}

// --- Funções de Gerenciamento do LocalStorage ---

async function carregarChamadoSalvo() {
    try {
        const chamadoSalvo = localStorage.getItem('chamadoAtual');
        if (chamadoSalvo) {
            const chamadoData = JSON.parse(chamadoSalvo);
            console.log('📂 Tentando carregar chamado salvo:', chamadoData.chamado_legivel);
            
            const response = await fetch(`/chamado/${chamadoData.chamado_id}/carregar-mensagens/`);
            
            if (!response.ok) {
                throw new Error('Chamado não encontrado no servidor');
            }
            
            const result = await response.json();

            if (result.success) {
                if (result.status.toLowerCase().includes('resolvido')) {
                    console.log('✅ Chamado resolvido, limpando estado...');
                    resetarEstadoSistema();
                    mostrarFeedbackPersistente(chamadoData.chamado_legivel, 'Resolvido (Chat finalizado)');
                } else {
                    chamadoAtual = chamadoData;
                    console.log('✅ Chamado carregado do localStorage:', chamadoAtual.chamado_legivel);

                    const estadoSalvo = localStorage.getItem('ultimaVisualizacao');
                    if (estadoSalvo) {
                        const estado = JSON.parse(estadoSalvo);
                        if (estado.chamadoId === chamadoAtual.chamado_id) {
                            ultimaMensagemVisualizadaId = estado.ultimaMensagemId;
                            console.log('✅ Estado de visualização carregado para este chamado:', ultimaMensagemVisualizadaId);
                        } else {
                            console.log('🔄 Estado de visualização pertence a outro chamado, resetando...');
                            ultimaMensagemVisualizadaId = null;
                            salvarEstadoSistema();
                        }
                    }

                    mostrarFeedbackPersistente(chamadoAtual.chamado_legivel, result.status);

                    const initialState = document.querySelector('.chat-initial-state');
                    if (initialState) {
                        initialState.style.display = 'none';
                    }
                    
                    setTimeout(() => {
                        verificarNovasMensagensInteligente();
                    }, 2000);
                }
            } else {
                console.log('❌ Chamado inválido no servidor, limpando estado...');
                resetarEstadoSistema();
            }
        } else {
            console.log('📂 Nenhum chamado salvo encontrado no localStorage');
        }
    } catch (error) {
        console.error('❌ Erro ao carregar chamado salvo:', error);
        resetarEstadoSistema();
    }
}

function salvarChamadoNoStorage(chamado) {
    try {
        localStorage.setItem('chamadoAtual', JSON.stringify(chamado));
        console.log('💾 Chamado salvo no localStorage:', chamado.chamado_legivel);
    } catch (error) {
        console.error('❌ Erro ao salvar chamado no localStorage:', error);
    }
}

function removerChamadoDoStorage() {
    try {
        localStorage.removeItem('chamadoAtual');
        localStorage.removeItem('ultimaVisualizacao');
        localStorage.removeItem('indicadorNovasMensagens');
        localStorage.removeItem('tipoUsuario');
        console.log('🗑️ Chamado e estado de visualização removidos do localStorage');
    } catch (error) {
        console.error('❌ Erro ao remover dados do localStorage:', error);
    }
}

// --- Funções Específicas do Formulário ---

async function enviarChamado() {
    const submitBtn = document.getElementById('submitBtn');
    const chamadoForm = document.getElementById('chamadoForm');
    
    if (!submitBtn || !chamadoForm) {
        console.error('❌ Elementos do formulário não encontrados');
        return;
    }

    const url = chamadoForm.dataset.url;
    if (!url) {
        console.error('❌ URL de envio não encontrada no atributo data-url do formulário.');
        mostrarErro('Erro de configuração. Contate o administrador.');
        return;
    }

    const originalText = submitBtn.innerHTML;

    try {
        submitBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i> Enviando...';
        submitBtn.classList.add('loading');

        const formData = new FormData(chamadoForm);

        console.log('📤 Enviando novo chamado...');
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            console.log('✅ Chamado criado com sucesso:', result.chamado_legivel);
            limparFormulario();
            mostrarFeedbackSucesso(result.chamado_legivel, result.status);
            chamadoAtual = result;
            salvarChamadoNoStorage(chamadoAtual);

            // ✅ NOVO: Detectar e salvar tipo de usuário
            if (result.tipo_usuario) {
                tipoUsuario = result.tipo_usuario;
                localStorage.setItem('tipoUsuario', tipoUsuario);
                console.log('👤 Tipo de usuário detectado:', tipoUsuario);
            }

            ultimaMensagemVisualizadaId = null;
            salvarEstadoSistema();

            const initialState = document.querySelector('.chat-initial-state');
            if (initialState) {
                initialState.style.display = 'none';
            }
            const chatMessages = document.getElementById('chatMessages');
            if (chatMessages) {
                chatMessages.innerHTML = '';
            }

            await carregarMensagensChamado(result.chamado_id);
            chatModalInstance.show();

            iniciarAtualizacaoAutomatica();
            iniciarVerificacoesAutomaticas();

            setTimeout(() => {
                iniciarSequenciaBot();
            }, 1500);
        } else {
            console.error('❌ Erro ao criar chamado:', result.message);
            mostrarErro(result.message || 'Erro ao criar chamado');
        }

    } catch (error) {
        console.error('❌ Erro de conexão:', error);
        mostrarErro('Erro de conexão. Tente novamente.');
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.classList.remove('loading');
    }
}

// --- Funções do Chat ---

async function carregarMensagensChamado(chamadoId) {
    if (carregandoMensagens) {
        console.log('⏳ Já carregando mensagens, aguarde...');
        return;
    }

    try {
        carregandoMensagens = true;
        console.log(`📥 Carregando mensagens do chamado: ${chamadoId}`);
        
        const response = await fetch(`/chamado/${chamadoId}/carregar-mensagens/`);
        const result = await response.json();

        if (result.success) {
            const chatMessages = document.getElementById('chatMessages');
            if(chatMessages) {
                chatMessages.innerHTML = '';
            }

            result.mensagens.forEach(msg => {
                const messageId = msg.id || `msg_${Date.now()}`;
                adicionarMensagemDOM(msg.mensagem, msg.remetente, msg.hora, messageId);
            });

            if (result.mensagens.length > 0) {
                const ultimaMsg = result.mensagens[result.mensagens.length - 1];
                const ultimaMsgId = ultimaMsg.id || `msg_${Date.now()}`;
                
                if (!ultimaMensagemVisualizadaId) {
                    ultimaMensagemVisualizadaId = ultimaMsgId;
                    salvarEstadoSistema();
                    console.log(`📝 Última mensagem ID inicializada: ${ultimaMensagemVisualizadaId}`);
                }
                
                ultimaMensagemId = ultimaMsgId;
            }

            if (result.status.toLowerCase().includes('resolvido')) {
                console.log('✅ Chamado resolvido, desativando chat...');
                desativarChat();
                // ✅ CORREÇÃO: Remover indicador visual apenas se estiver visível
                const indicador = document.getElementById('novasMensagensIndicador');
                if (indicador && indicador.style.display !== 'none') {
                    indicador.style.display = 'none';
                    indicador.classList.remove('pulse-animation');
                    console.log('🟢 Botão pulsante REMOVIDO (chamado resolvido)');
                }
                removerChamadoDoStorage();
                pararAtualizacaoAutomatica();
                pararVerificacoesAutomaticas();
                
                const chatMessages = document.getElementById('chatMessages');
                if (chatMessages) {
                    const finalizacaoDiv = document.createElement('div');
                    finalizacaoDiv.className = 'message message-bot';
                    finalizacaoDiv.innerHTML = `
                        <div class="message-content">
                            <div class="message-header">BOT_HYPER</div>
                            <div class="message-text">✅ Este chamado foi finalizado. Obrigado por utilizar nosso serviço!</div>
                            <div class="message-time">${new Date().toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})}</div>
                        </div>
                    `;
                    chatMessages.appendChild(finalizacaoDiv);
                    scrollParaFinal();
                }
            }

            scrollParaFinal();
            console.log(`✅ ${result.mensagens.length} mensagens carregadas`);
        } else {
            console.error('❌ Erro ao carregar mensagens:', result.message);
        }
    } catch (error) {
        console.error('❌ Erro ao carregar mensagens:', error);
    } finally {
        carregandoMensagens = false;
    }
}

async function iniciarSequenciaBot() {
    if (!chamadoAtual || sequenciaAtiva) {
        console.log('⏸️ Sequência do bot já ativa ou nenhum chamado');
        return;
    }

    sequenciaAtiva = true;
    console.log('🤖 Iniciando sequência do bot...');

    try {
        const response = await fetch(`/chamado/${chamadoAtual.chamado_id}/carregar-mensagens/`);
        const result = await response.json();

        if (result.success) {
            if (result.status.toLowerCase().includes('resolvido')) {
                console.log('✅ Chamado já resolvido, cancelando sequência');
                desativarChat();
                sequenciaAtiva = false;
                return;
            }

            const mensagensBot = result.mensagens.filter(msg => msg.remetente === 'bot');
            const mensagensExistentes = mensagensBot.length;
            console.log(`📊 Mensagens do bot existentes: ${mensagensExistentes}`);
            
            const maxMensagensBot = 7;

            if (mensagensExistentes >= maxMensagensBot) {
                console.log(`✅ Todas as ${maxMensagensBot} mensagens já foram exibidas`);
                sequenciaAtiva = false;
                return;
            }

            for (let i = mensagensExistentes; i < maxMensagensBot; i++) {
                if (i > mensagensExistentes) {
                    console.log(`⏳ Aguardando 1.5 segundos antes da mensagem ${i + 1}...`);
                    await new Promise(resolve => setTimeout(resolve, 1500));
                }

                mostrarIndicadorDigitacao();
                await new Promise(resolve => setTimeout(resolve, 800));
                removerIndicadorDigitacao();

                const responseMsg = await fetch(`/chamado/${chamadoAtual.chamado_id}/enviar-mensagem-bot/${i + 1}/`);
                
                if (!responseMsg.ok) {
                    console.log(`⚠️ Mensagem ${i + 1} não disponível, continuando...`);
                    continue;
                }

                const resultMsg = await responseMsg.json();

                if (resultMsg.success) {
                    const messageId = resultMsg.mensagem_id || `msg_${Date.now()}`;
                    adicionarMensagemDOM(resultMsg.mensagem, 'bot', resultMsg.hora, messageId);
                    scrollParaFinal();
                    console.log(`✅ Mensagem ${i + 1} do bot adicionada`);
                } else {
                    console.log(`⚠️ Mensagem ${i + 1} do bot não disponível:`, resultMsg.message);
                }
            }
        } else {
            console.error('❌ Erro ao verificar mensagens existentes:', result.message);
        }
    } catch (error) {
        console.error('❌ Erro na sequência do bot:', error);
    } finally {
        sequenciaAtiva = false;
        console.log('🤖 Sequência do bot finalizada');
    }
}

async function enviarMensagemChat() {
    garantirChamadoAtual();
    
    if (!chamadoAtual) {
        console.error('❌ Nenhum chamado ativo para enviar mensagem');
        mostrarErro('Crie um chamado primeiro para enviar mensagens');
        return;
    }

    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');

    if (!messageInput || !sendBtn) {
        console.error('❌ Elementos do chat não encontrados');
        return;
    }

    const mensagem = messageInput.value.trim();

    if (!mensagem) {
        console.log('❌ Mensagem vazia, ignorando envio');
        return;
    }

    const originalText = sendBtn.innerHTML;

    try {
        sendBtn.innerHTML = '<i class="bi bi-hourglass-split"></i>';
        sendBtn.disabled = true;
        messageInput.disabled = true;

        const response = await fetch(`/chamado/${chamadoAtual.chamado_id}/enviar-mensagem/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({ mensagem: mensagem })
        });

        const result = await response.json();

        if (result.success) {
            console.log('✅ Mensagem enviada com sucesso');
            messageInput.value = '';
            
            const messageId = result.mensagem_id || `msg_${Date.now()}`;
            adicionarMensagemDOM(mensagem, 'usuario', result.hora, messageId);
            scrollParaFinal();

            atualizarUltimaVisualizacao();
            
            if (result.chamado_resolvido) {
                console.log('✅ Chamado marcado como resolvido após mensagem');
                desativarChat();
                // ✅ CORREÇÃO: Remover indicador visual apenas se estiver visível
                const indicador = document.getElementById('novasMensagensIndicador');
                if (indicador && indicador.style.display !== 'none') {
                    indicador.style.display = 'none';
                    indicador.classList.remove('pulse-animation');
                    console.log('🟢 Botão pulsante REMOVIDO (chamado resolvido)');
                }
            }
        } else {
            console.error('❌ Erro ao enviar mensagem:', result.message);
            mostrarErro(result.message || 'Erro ao enviar mensagem');
        }

    } catch (error) {
        console.error('❌ Erro de conexão:', error);
        mostrarErro('Erro de conexão. Tente novamente.');
    } finally {
        sendBtn.innerHTML = originalText;
        sendBtn.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
    }
}

// ✅ FUNÇÃO MELHORADA: Adicionar mensagem DOM com estilo do template
function adicionarMensagemDOM(mensagem, remetente, hora, messageId) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) {
        console.error('❌ Elemento chatMessages não encontrado');
        return;
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${remetente === 'usuario' ? 'message-usuario' : 'message-bot'}`;
    messageDiv.setAttribute('data-message-id', messageId);

    const horaFormatada = formatarHora(hora);
    const remetenteLabel = remetente === 'usuario' ? 'Você' : 'BOT_HYPER';

    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="message-header">${remetenteLabel}</div>
            <div class="message-text">${mensagem}</div>
            <div class="message-time">${horaFormatada}</div>
        </div>
    `;

    chatMessages.appendChild(messageDiv);

    const initialState = document.querySelector('.chat-initial-state');
    if (initialState) {
        initialState.style.display = 'none';
    }

    scrollParaFinal();
}

function scrollParaFinal() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        setTimeout(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 100);
    }
}

function formatarHora(horaString) {
    if (!horaString) return '';
    
    try {
        const data = new Date(horaString);
        if (isNaN(data.getTime())) {
            return horaString;
        }
        
        return data.toLocaleTimeString('pt-BR', {
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        console.error('❌ Erro ao formatar hora:', error);
        return horaString;
    }
}

function desativarChat() {
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    
    if (messageInput) {
        messageInput.disabled = true;
        messageInput.placeholder = 'Chat finalizado - chamado resolvido';
    }
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.innerHTML = '<i class="bi bi-check-circle"></i>';
    }
    
    pararAtualizacaoAutomatica();
    pararVerificacoesAutomaticas();
    
    console.log('🔒 Chat desativado (chamado resolvido)');
}

// --- Funções de Feedback/UI ---

function mostrarFeedbackSucesso(chamadoLegivel, status) {
    const feedbackDiv = document.getElementById('feedbackChamado');
    if (!feedbackDiv) return;

    feedbackDiv.innerHTML = `
        <div class="alert alert-success d-flex align-items-center" role="alert">
            <i class="bi bi-check-circle-fill me-2"></i>
            <div>
                <strong>Chamado ${chamadoLegivel} criado com sucesso!</strong>
                <div class="small">Status: ${status}</div>
            </div>
        </div>
    `;
    feedbackDiv.style.display = 'block';

    setTimeout(() => {
        feedbackDiv.style.display = 'none';
    }, 10000);
}

function mostrarFeedbackPersistente(chamadoLegivel, status) {
    const feedbackDiv = document.getElementById('feedbackChamado');
    if (!feedbackDiv) return;

    feedbackDiv.innerHTML = `
        <div class="alert alert-info d-flex align-items-center" role="alert">
            <i class="bi bi-info-circle-fill me-2"></i>
            <div>
                <strong>Chamado ${chamadoLegivel}</strong>
                <div class="small">Status: ${status}</div>
            </div>
        </div>
    `;
    feedbackDiv.style.display = 'block';
}

function mostrarErro(mensagem) {
    const feedbackDiv = document.getElementById('feedbackChamado');
    if (!feedbackDiv) {
        console.error('❌ Elemento feedbackChamado não encontrado');
        return;
    }

    feedbackDiv.innerHTML = `
        <div class="alert alert-danger d-flex align-items-center" role="alert">
            <i class="bi bi-exclamation-triangle-fill me-2"></i>
            <div>${mensagem}</div>
        </div>
    `;
    feedbackDiv.style.display = 'block';

    setTimeout(() => {
        feedbackDiv.style.display = 'none';
    }, 10000);
}

function limparFormulario() {
    const chamadoForm = document.getElementById('chamadoForm');
    if (chamadoForm) {
        chamadoForm.reset();
    }
}

// ✅ CORREÇÃO: Exportar funções para uso global
window.mostrarIndicadorNovasMensagens = mostrarIndicadorNovasMensagens;
window.verificarNovasMensagensInteligente = verificarNovasMensagensInteligente;
window.verificarNotificacoesAutomaticas = verificarNotificacoesAutomaticas;
window.iniciarAtualizacaoAutomatica = iniciarAtualizacaoAutomatica;
window.mostrarIndicadorDigitacao = mostrarIndicadorDigitacao;
window.removerIndicadorDigitacao = removerIndicadorDigitacao;
window.reiniciarSistemaAtualizacao = reiniciarSistemaAtualizacao;
window.carregarEstadoAtual = carregarEstadoAtual;
window.resetarEstadoSistema = resetarEstadoSistema;
window.salvarEstadoSistema = salvarEstadoSistema;

console.log('✅ Sistema de Chat - NOTIFICAÇÕES PARA COLABORADORES E SUPORTE!');
console.log('⏰ Chat em segundo plano: 2 minutos (ÚNICO intervalo para notificações)');
console.log('🔄 Refresh de dados: 5 minutos');
console.log('🔔 Verificação mensagens: 30 segundos');
console.log('🔴 Botão pulsante: Só será removido quando o chat for visualizado');
console.log('👥 Suporte: Todas as notificações | Colaboradores: Apenas seus chamados');