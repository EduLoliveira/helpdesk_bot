/**
 * =================================================================
 * SCRIPT UNIFICADO DO CHATBOT DE CHAMADOS - CORRIGIDO E COMPLETO
 * Sistema de atualização automática a cada 25 segundos (CONTÍNUO)
 * CORREÇÃO: Indicador de novas mensagens FUNCIONANDO PERFEITAMENTE
 * CORREÇÃO: Sistema de IDs consistente para evitar falsos positivos
 * =================================================================
 */

// --- Variáveis Globais ---
let chamadoAtual = null;
let sequenciaAtiva = false;
let chatModalInstance = null;
let carregandoMensagens = false;
let ultimaMensagemId = null;
let intervaloAtualizacao = null;
let indicadorNovasMensagens = false;
let modalAberto = false;
let ultimaMensagemVisualizadaId = null;

// --- Inicializador Principal ---
document.addEventListener('DOMContentLoaded', function () {
    console.log('🚀 Inicializando sistema de chat...');
    
    // ✅ CORREÇÃO: Garantir que os estilos CSS sejam injetados primeiro
    injetarEstilosChat();
    
    // ✅ CORREÇÃO: Garantir que o container do indicador exista
    garantirContainerIndicador();
    
    // ✅ NOVO: Inicializar sistema de controle de visualização
    inicializarSistemaVisualizacao();
    
    // Essencial: Abortar se o modal do chat não existir
    const chatModalEl = document.getElementById('chatModal');
    if (!chatModalEl) {
        console.warn('Elemento #chatModal não encontrado. Chat desativado.');
        return;
    }
    
    // ✅ CORREÇÃO: Inicializar modal Bootstrap corretamente
    try {
        chatModalInstance = new bootstrap.Modal(chatModalEl);
        console.log('✅ Modal do chat inicializado com sucesso');
    } catch (error) {
        console.error('❌ Erro ao inicializar modal:', error);
        return;
    }

    // Carregar chamado salvo em todas as páginas
    carregarChamadoSalvo();

    // --- Listeners do Chat (Comuns a todas as páginas) ---
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

    // ✅ CORREÇÃO: Listener para quando o modal é aberto - corrigido
    chatModalEl.addEventListener('shown.bs.modal', function () {
        console.log('📱 Modal do chat aberto');
        modalAberto = true;
        
        // ✅ CORREÇÃO: Forçar redimensionamento do layout
        setTimeout(() => {
            ajustarLayoutChat();
            scrollParaFinal();
        }, 100);
        
        if (messageInput) {
            messageInput.focus();
        }

        if (chamadoAtual && !sequenciaAtiva) {
            iniciarSequenciaBot();
        }
        
        // ✅ CORREÇÃO: Atualizar visualização quando o modal abre
        atualizarUltimaVisualizacao();
        
        // ✅ CORREÇÃO: Remover indicador quando o usuário abre o chat
        removerIndicadorNovasMensagens();
        
        // Verificar mensagens imediatamente
        if (chamadoAtual) {
            setTimeout(() => {
                verificarNovasMensagensInteligente();
            }, 1000);
        }
    });

    // ✅ CORREÇÃO: Listener para quando o modal é fechado - corrigido
    chatModalEl.addEventListener('hidden.bs.modal', function () {
        console.log('📱 Modal do chat fechado');
        modalAberto = false;
        
        console.log('🔄 Atualização automática continua rodando em segundo plano');
        
        // ✅ CORREÇÃO: Atualizar última visualização quando fecha
        atualizarUltimaVisualizacao();
        
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
            chatModalInstance.show();
        });
    }

    // --- Listener Específico do Formulário (Página Principal) ---
    const chamadoForm = document.getElementById('chamadoForm');
    if (chamadoForm) {
        chamadoForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            await enviarChamado();
        });
    }
    
    // ✅ CORREÇÃO: Observar scroll do chat para detectar quando usuário vê mensagens
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.addEventListener('scroll', function() {
            const isNearBottom = chatMessages.scrollHeight - chatMessages.scrollTop - chatMessages.clientHeight < 100;
            if (isNearBottom && modalAberto) {
                atualizarUltimaVisualizacao();
            }
        });
    }
    
    // ✅ CORREÇÃO: Observar redimensionamento da janela para ajustar layout
    window.addEventListener('resize', function() {
        if (modalAberto) {
            ajustarLayoutChat();
        }
    });
    
    // Iniciar atualização automática SEMPRE que houver um chamado ativo
    if (chamadoAtual) {
        console.log('📞 Chamado ativo encontrado, iniciando atualização automática...');
        iniciarAtualizacaoAutomatica();
    }
});

// ✅ CORREÇÃO: Função para injetar estilos CSS críticos
function injetarEstilosChat() {
    if (!document.querySelector('#chat-critical-styles')) {
        const style = document.createElement('style');
        style.id = 'chat-critical-styles';
        style.textContent = `
            /* ✅ ESTILOS CRÍTICOS PARA O LAYOUT DO CHAT */
            .chat-modal .modal-dialog {
                max-width: 420px;
                margin: 1.75rem auto;
                height: calc(100vh - 3.5rem);
            }
            .chat-modal .modal-content {
                border-radius: 16px;
                border: none;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
                height: 100%;
                display: flex;
                flex-direction: column;
                min-height: 0;
            }
            .chat-modal .modal-body {
                padding: 0;
                display: flex;
                flex-direction: column;
                flex: 1;
                min-height: 0;
                overflow: hidden;
            }
            .chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 1.25rem;
                background: #ffffff;
                display: flex;
                flex-direction: column;
                min-height: 0;
            }
            .chat-input-section {
                flex-shrink: 0;
                padding: 1rem 1.5rem;
                border-top: 1px solid #e5e7eb;
                background: #f8f9fa;
            }
            
            /* ✅ CORREÇÃO: Garantir que mensagens fiquem corretas */
            .message {
                margin-bottom: 1.25rem;
                max-width: 85%;
            }
            .message-usuario {
                align-self: flex-end;
                align-items: flex-end;
            }
            .message-bot {
                align-self: flex-start;
                align-items: flex-start;
            }
            
            /* ✅ CORREÇÃO CRÍTICA: CONTAINER E INDICADOR FUNCIONAIS */
            .chat-indicator-container {
                position: fixed;
                bottom: 30px;
                right: 30px;
                z-index: 1050;
                width: 60px;
                height: 60px;
            }
            
            #novasMensagensIndicador {
                position: absolute;
                top: 0px;
                right: 0px;
                width: 20px;
                height: 20px;
                border: 3px solid white;
                background-color: #dc3545;
                border-radius: 50%;
                z-index: 1051;
            }
            
            .pulse-animation {
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0% {
                    transform: scale(0.95);
                    box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7);
                }
                70% {
                    transform: scale(1.1);
                    box-shadow: 0 0 0 12px rgba(220, 53, 69, 0);
                }
                100% {
                    transform: scale(0.95);
                    box-shadow: 0 0 0 0 rgba(220, 53, 69, 0);
                }
            }
            
            /* ✅ CORREÇÃO: Botão flutuante dentro do container */
            .chat-floating-btn {
                position: relative !important;
                width: 100% !important;
                height: 100% !important;
                background-color: #10b981 !important;
                border-radius: 50% !important;
                border: none !important;
                box-shadow: 0 8px 25px rgba(16, 185, 129, 0.3) !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                color: white !important;
                font-size: 28px !important;
                transition: all 0.3s ease !important;
            }
            
            .chat-floating-btn:hover {
                transform: scale(1.1);
                box-shadow: 0 12px 30px rgba(16, 185, 129, 0.4);
            }
            
            /* ✅ CORREÇÃO: Estado inicial do chat */
            .chat-initial-state {
                display: none;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                text-align: center;
                padding: 2rem;
                color: #6b7280;
                height: 100%;
            }
            .chat-messages:empty + .chat-initial-state {
                display: flex;
            }
        `;
        document.head.appendChild(style);
        console.log('✅ Estilos críticos do chat injetados');
    }
}

// ✅ CORREÇÃO: Garantir que o container existe
function garantirContainerIndicador() {
    let container = document.querySelector('.chat-indicator-container');
    
    if (!container) {
        console.log('🔄 Container do indicador não encontrado, criando...');
        container = criarContainerIndicador();
    }
    
    return container;
}

// ✅ CORREÇÃO: Função para criar container se não existir
function criarContainerIndicador() {
    const container = document.createElement('div');
    container.className = 'chat-indicator-container';
    
    // Encontrar o botão flutuante
    const floatingBtn = document.getElementById('chatFloatingBtn');
    if (floatingBtn) {
        // Se o botão já existe, movê-lo para o container
        if (floatingBtn.parentNode) {
            floatingBtn.parentNode.insertBefore(container, floatingBtn);
        }
        container.appendChild(floatingBtn);
    } else {
        // Se não tem botão, criar um
        const newFloatingBtn = document.createElement('button');
        newFloatingBtn.className = 'chat-floating-btn';
        newFloatingBtn.id = 'chatFloatingBtn';
        newFloatingBtn.innerHTML = '<i class="bi bi-chat-dots-fill"></i>';
        newFloatingBtn.addEventListener('click', function() {
            if (chatModalInstance) chatModalInstance.show();
        });
        container.appendChild(newFloatingBtn);
    }
    
    document.body.appendChild(container);
    console.log('✅ Container do indicador criado');
    
    return container;
}

// ✅ CORREÇÃO DEFINITIVA: Função mostrarIndicadorNovasMensagens
function mostrarIndicadorNovasMensagens() {
    console.log('🟡 Tentando mostrar indicador de novas mensagens...');
    
    // Remover indicador existente primeiro
    removerIndicadorNovasMensagens();
    
    // ✅ CORREÇÃO: Usar o container correto
    const container = document.querySelector('.chat-indicator-container');
    if (!container) {
        console.log('❌ Container do indicador não encontrado, criando...');
        criarContainerIndicador();
        return;
    }
    
    // ✅ CORREÇÃO: Criar indicador com estilos corretos
    const indicador = document.createElement('div');
    indicador.id = 'novasMensagensIndicador';
    indicador.className = 'pulse-animation';
    indicador.title = 'Novas mensagens';
    
    // Aplicar estilos inline para garantir visibilidade
    indicador.style.cssText = `
        position: absolute;
        top: -2px;
        right: -2px;
        width: 20px;
        height: 20px;
        border: 3px solid white;
        background-color: #dc3545;
        border-radius: 50%;
        z-index: 1051;
    `;
    
    // Adicionar ao container
    container.appendChild(indicador);
    
    indicadorNovasMensagens = true;
    
    console.log('🔴✅ Indicador de nova mensagem exibido COM SUCESSO');
}

// ✅ CORREÇÃO: Função removerIndicadorNovasMensagens
function removerIndicadorNovasMensagens() {
    const indicador = document.getElementById('novasMensagensIndicador');
    
    if (indicador && indicador.parentNode) {
        indicador.parentNode.removeChild(indicador);
        console.log('✅ Indicador de novas mensagens removido');
    }
    
    indicadorNovasMensagens = false;
}

// ✅ NOVO: Função para ajustar layout do chat
function ajustarLayoutChat() {
    const chatMessages = document.getElementById('chatMessages');
    const modalBody = document.querySelector('.chat-modal .modal-body');
    
    if (chatMessages && modalBody) {
        // ✅ CORREÇÃO: Forçar recálculo do layout
        chatMessages.style.height = 'auto';
        setTimeout(() => {
            const availableHeight = modalBody.clientHeight - 
                                 document.querySelector('.chat-input-section').clientHeight;
            chatMessages.style.height = availableHeight + 'px';
            chatMessages.style.minHeight = '200px';
            scrollParaFinal();
        }, 50);
    }
}

// ✅ CORREÇÃO CRÍTICA: Sistema de Controle de Visualização com IDs Consistentes
function inicializarSistemaVisualizacao() {
    console.log('🔧 Inicializando sistema de controle de visualização...');
    
    // Carregar estado salvo do localStorage
    try {
        const estadoSalvo = localStorage.getItem('ultimaVisualizacao');
        if (estadoSalvo) {
            const estado = JSON.parse(estadoSalvo);
            ultimaMensagemVisualizadaId = estado.ultimaMensagemId;
            console.log('✅ Estado de visualização carregado:', estado);
        }
    } catch (e) {
        console.error('❌ Erro ao carregar estado de visualização:', e);
    }
}

function salvarEstadoVisualizacao() {
    try {
        const estado = {
            ultimaMensagemId: ultimaMensagemVisualizadaId,
            timestamp: Date.now(),
            chamadoId: chamadoAtual ? chamadoAtual.chamado_id : null
        };
        localStorage.setItem('ultimaVisualizacao', JSON.stringify(estado));
    } catch (e) {
        console.error('❌ Erro ao salvar estado de visualização:', e);
    }
}

function atualizarUltimaVisualizacao() {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages || !chamadoAtual) return;
    
    const mensagens = chatMessages.querySelectorAll('.message');
    if (mensagens.length > 0) {
        const ultimaMensagem = mensagens[mensagens.length - 1];
        // ✅ CORREÇÃO CRÍTICA: Usar ID real da mensagem do servidor, não timestamp
        const novoId = ultimaMensagem.getAttribute('data-message-id');
        
        if (novoId && novoId !== ultimaMensagemVisualizadaId) {
            ultimaMensagemVisualizadaId = novoId;
            salvarEstadoVisualizacao();
            console.log('👀 Última mensagem visualizada atualizada:', novoId);
        }
    }
}

// --- Sistema de Atualização Automática CORRIGIDO ---

function iniciarAtualizacaoAutomatica() {
    if (!chamadoAtual) {
        console.log('❌ Nenhum chamado ativo para iniciar atualização do CHAT');
        return;
    }
    
    // Parar qualquer intervalo existente ANTES de criar novo
    if (intervaloAtualizacao) {
        clearInterval(intervaloAtualizacao);
        console.log('🔄 Reiniciando sistema de atualização do chat...');
    }
    
    console.log('💬 Iniciando sistema de atualização automática do CHAT (25s)...');
    
    // Verificar novas mensagens a cada 25 segundos
    intervaloAtualizacao = setInterval(async () => {
        console.log('⏰ Verificando novas mensagens do chat...');
        await verificarNovasMensagensInteligente();
    }, 25000); // 25 segundos
    
    // Verificar imediatamente ao iniciar
    setTimeout(() => {
        verificarNovasMensagensInteligente();
    }, 2000);
}

function pararAtualizacaoAutomatica() {
    if (intervaloAtualizacao) {
        clearInterval(intervaloAtualizacao);
        intervaloAtualizacao = null;
        console.log('⏹️ Sistema de atualização automática parado');
    }
}

// ✅ CORREÇÃO CRÍTICA: Função de verificação com controle de estado melhorado
async function verificarNovasMensagensInteligente() {
    if (!chamadoAtual) {
        console.log('❌ Nenhum chamado ativo para verificar mensagens');
        return;
    }
    
    try {
        // ✅ CORREÇÃO: Usar sempre o ID da última mensagem VISUALIZADA
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
            
            // ✅ CORREÇÃO CRÍTICA: Só considerar como "novas" se realmente houver mensagens não visualizadas
            const haMensagensNaoVisualizadas = result.total_novas > 0 && 
                result.ultima_visualizada_id !== ultimaMensagemVisualizadaId;
            
            if (haMensagensNaoVisualizadas) {
                console.log(`✅ ${result.total_novas} nova(s) mensagem(ns) não visualizada(s) encontrada(s)`);
                
                // ✅ CORREÇÃO: Atualizar última mensagem visualizada APENAS se não estiver no modal
                if (!modalAberto) {
                    ultimaMensagemVisualizadaId = result.ultima_visualizada_id;
                    salvarEstadoVisualizacao();
                }
                
                // Adicionar novas mensagens ao chat (se o modal estiver aberto)
                if (modalAberto) {
                    result.novas_mensagens.forEach(msg => {
                        adicionarMensagemDOM(msg.mensagem, msg.remetente, msg.hora, msg.id);
                    });
                    scrollParaFinal();
                    
                    // ✅ CORREÇÃO: Atualizar visualização automaticamente quando modal está aberto
                    atualizarUltimaVisualizacao();
                }
                
                // ✅ CORREÇÃO CRÍTICA: Mostrar indicador apenas se modal fechado E há mensagens realmente novas
                if (!modalAberto && haMensagensNaoVisualizadas) {
                    console.log(`🔴 Mostrando indicador: modalAberto=${modalAberto}, mensagensNaoVisualizadas=${haMensagensNaoVisualizadas}`);
                    mostrarIndicadorNovasMensagens();
                }
            } else {
                console.log('✅ Nenhuma nova mensagem não visualizada encontrada');
                
                // ✅ CORREÇÃO IMPORTANTE: Atualizar o ID da última mensagem visualizada mesmo quando não há novas
                // Isso evita falsos positivos quando a página é recarregada
                if (result.ultima_visualizada_id && result.ultima_visualizada_id !== ultimaMensagemVisualizadaId) {
                    console.log(`🔄 Atualizando ID de referência: ${ultimaMensagemVisualizadaId} -> ${result.ultima_visualizada_id}`);
                    ultimaMensagemVisualizadaId = result.ultima_visualizada_id;
                    salvarEstadoVisualizacao();
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
            const result = await response.json();

            if (result.success) {
                if (result.status.toLowerCase().includes('resolvido')) {
                    localStorage.removeItem('chamadoAtual');
                    localStorage.removeItem('ultimaVisualizacao');
                    console.log('✅ Chamado resolvido, removendo do localStorage');
                } else {
                    chamadoAtual = chamadoData;
                    console.log('✅ Chamado carregado do localStorage:', chamadoAtual.chamado_legivel);

                    // ✅ CORREÇÃO: Verificar se o estado salvo pertence ao mesmo chamado
                    const estadoSalvo = localStorage.getItem('ultimaVisualizacao');
                    if (estadoSalvo) {
                        const estado = JSON.parse(estadoSalvo);
                        if (estado.chamadoId === chamadoAtual.chamado_id) {
                            ultimaMensagemVisualizadaId = estado.ultimaMensagemId;
                            console.log('✅ Estado de visualização carregado para este chamado:', ultimaMensagemVisualizadaId);
                        } else {
                            console.log('🔄 Estado de visualização pertence a outro chamado, resetando...');
                            ultimaMensagemVisualizadaId = null;
                        }
                    }

                    // Tenta mostrar o feedback persistente (só funciona na página principal)
                    mostrarFeedbackPersistente(chamadoAtual.chamado_legivel, result.status);

                    // Preparar o chat
                    const initialState = document.querySelector('.chat-initial-state');
                    if (initialState) {
                        initialState.style.display = 'none';
                    }
                    await carregarMensagensChamado(chamadoAtual.chamado_id);
                    
                    // Iniciar atualização automática para chamado carregado
                    iniciarAtualizacaoAutomatica();
                }
            } else {
                localStorage.removeItem('chamadoAtual');
                localStorage.removeItem('ultimaVisualizacao');
                console.log('❌ Chamado não encontrado no servidor, removendo do localStorage');
            }
        } else {
            console.log('📂 Nenhum chamado salvo encontrado no localStorage');
            // ✅ CORREÇÃO: Limpar estado de visualização se não há chamado
            localStorage.removeItem('ultimaVisualizacao');
        }
    } catch (error) {
        console.error('❌ Erro ao carregar chamado salvo:', error);
        localStorage.removeItem('chamadoAtual');
        localStorage.removeItem('ultimaVisualizacao');
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
        console.log('🗑️ Chamado e estado de visualização removidos do localStorage');
    } catch (error) {
        console.error('❌ Erro ao remover dados do localStorage:', error);
    }
}

// --- Funções Específicas do Formulário (Página Principal) ---

async function enviarChamado() {
    const submitBtn = document.getElementById('submitBtn');
    const chamadoForm = document.getElementById('chamadoForm');
    
    // Abortar se os elementos do formulário não existem
    if (!submitBtn || !chamadoForm) {
        console.error('❌ Elementos do formulário não encontrados');
        return;
    }

    // Pegar a URL do atributo data-url
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

            // ✅ CORREÇÃO: Resetar estado de visualização para novo chamado
            ultimaMensagemVisualizadaId = null;
            salvarEstadoVisualizacao();

            // Limpar estado inicial do chat
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

            // Iniciar sistema de atualização automática
            iniciarAtualizacaoAutomatica();

            setTimeout(() => {
                iniciarSequenciaBot();
            }, 1000);
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

// --- Funções do Chat (Comuns) ---

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

            // ✅ CORREÇÃO: Usar IDs reais do servidor, não gerar dinamicamente
            result.mensagens.forEach(msg => {
                // ✅ CORREÇÃO CRÍTICA: Usar o ID real da mensagem do servidor
                const messageId = msg.id || `msg_${Date.now()}`;
                adicionarMensagemDOM(msg.mensagem, msg.remetente, msg.hora, messageId);
            });

            // ✅ CORREÇÃO: Atualizar última mensagem ID com dados reais do servidor
            if (result.mensagens.length > 0) {
                const ultimaMsg = result.mensagens[result.mensagens.length - 1];
                const ultimaMsgId = ultimaMsg.id || `msg_${Date.now()}`;
                
                // ✅ Só atualizar visualização se for a primeira carga ou se não houver estado salvo
                if (!ultimaMensagemVisualizadaId) {
                    ultimaMensagemVisualizadaId = ultimaMsgId;
                    salvarEstadoVisualizacao();
                    console.log(`📝 Última mensagem ID inicializada: ${ultimaMensagemVisualizadaId}`);
                }
                
                ultimaMensagemId = ultimaMsgId;
            }

            if (result.status.toLowerCase().includes('resolvido')) {
                console.log('✅ Chamado resolvido, desativando chat...');
                desativarChat();
                removerChamadoDoStorage();
                pararAtualizacaoAutomatica();
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
            
            const maxMensagensBot = 8;

            if (mensagensExistentes >= maxMensagensBot) {
                console.log(`✅ Todas as ${maxMensagensBot} mensagens já foram exibidas`);
                sequenciaAtiva = false;
                return;
            }

            for (let i = mensagensExistentes; i < maxMensagensBot; i++) {
                if (i > mensagensExistentes) {
                    console.log(`⏳ Aguardando 2 segundos antes da mensagem ${i + 1}...`);
                    await new Promise(resolve => setTimeout(resolve, 2000));
                }

                const proximaResponse = await fetch(`/chamado/${chamadoAtual.chamado_id}/proxima-mensagem/`);
                const proximaResult = await proximaResponse.json();

                if (proximaResult.success && !proximaResult.completo) {
                    console.log(`➕ Adicionando mensagem ${i + 1} de ${maxMensagensBot}`);
                    await carregarMensagensChamado(chamadoAtual.chamado_id);
                } else {
                    console.log('✅ Sequência completa ou erro ao buscar mensagem');
                    break;
                }
            }
        }
    } catch (error) {
        console.error('❌ Erro na sequência do bot:', error);
    } finally {
        sequenciaAtiva = false;
        console.log('🏁 Sequência do bot finalizada');
    }
}

async function enviarMensagemChat() {
    const messageInput = document.getElementById('messageInput');
    if (!messageInput) {
        console.error('❌ Campo de mensagem não encontrado');
        return;
    }

    if (messageInput.classList.contains('chat-disabled')) {
        console.log('⏸️ Chat desativado, mensagem não enviada');
        return;
    }

    const message = messageInput.value.trim();
    if (!message) {
        console.log('ℹ️ Mensagem vazia, não enviada');
        return;
    }
    
    if (!chamadoAtual) {
        console.error('❌ Nenhum chamado ativo');
        return;
    }

    console.log('📤 Enviando mensagem:', message.substring(0, 50) + '...');
    const horaAtual = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    
    // ✅ CORREÇÃO: Usar ID temporário que será substituído pelo ID real do servidor
    adicionarMensagemDOM(message, 'usuario', horaAtual, `temp_user_${Date.now()}`);
    messageInput.value = '';
    scrollParaFinal();

    try {
        const response = await fetch(`/chamado/${chamadoAtual.chamado_id}/enviar-mensagem/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({ mensagem: message })
        });

        const result = await response.json();

        if (result.success) {
            console.log('✅ Mensagem enviada com sucesso');
            
            if (result.intencao_detectada === 'resolucao_confirmada' || result.resposta.includes('RESOLVIDO')) {
                console.log('✅ Resolução confirmada, desativando chat...');
                desativarChat();
                removerChamadoDoStorage();
                pararAtualizacaoAutomatica();
            }

            const horaResposta = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
            
            // ✅ CORREÇÃO: Usar ID do servidor se disponível
            const messageId = result.message_id || `bot_${Date.now()}`;
            adicionarMensagemDOM(result.resposta, 'bot', horaResposta, messageId);
            scrollParaFinal();
            
            // ✅ CORREÇÃO: Atualizar visualização após envio
            atualizarUltimaVisualizacao();
            
            // Recarregar mensagens para garantir IDs consistentes
            setTimeout(() => {
                carregarMensagensChamado(chamadoAtual.chamado_id);
            }, 1000);
        } else {
            console.error('❌ Erro ao enviar mensagem:', result.message);
        }
    } catch (error) {
        console.error('❌ Erro ao enviar mensagem:', error);
        const horaErro = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
        adicionarMensagemDOM('Desculpe, ocorreu um erro. Tente novamente.', 'bot', horaErro, `error_${Date.now()}`);
        scrollParaFinal();
    }
}

function desativarChat() {
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatStatus = document.getElementById('chatStatus');

    if (messageInput) {
        messageInput.placeholder = "Chat encerrado - Chamado resolvido";
        messageInput.classList.add('chat-disabled');
    }
    if (sendBtn) {
        sendBtn.classList.add('chat-disabled');
    }
    if (chatStatus) {
        chatStatus.textContent = "Finalizado";
        chatStatus.style.backgroundColor = "#6b7280";
    }
    console.log('🔴 Chat desativado - Chamado resolvido');
}

// --- Funções Utilitárias ---

function getCSRFToken() {
    let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfToken) {
        return csrfToken.value;
    }

    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const parts = cookie.trim().split('=');
        if (parts[0] === 'csrftoken') {
            return parts[1];
        }
    }
    
    console.warn('⚠️ CSRF Token não encontrado');
    return '';
}

function limparFormulario() {
    const form = document.getElementById('chamadoForm');
    if (form) {
        form.reset();
        const presencialCheck = document.getElementById('presencial');
        if (presencialCheck) {
            presencialCheck.checked = true;
        }
        console.log('🧹 Formulário limpo');
    }
}

function mostrarFeedbackSucesso(chamadoId, status) {
    const feedbackDiv = document.getElementById('successFeedback');
    const errorDiv = document.getElementById('errorFeedback');
    
    if (!feedbackDiv) {
        console.log('ℹ️ Elemento de feedback de sucesso não encontrado');
        return;
    }

    feedbackDiv.innerHTML = `
    <strong><i class="bi bi-check-circle-fill me-1"></i> Chamado criado com sucesso!</strong>
    <div class="mt-2">
        <strong>ID:</strong> ${chamadoId}<br>
        <strong>Status:</strong> ${status}
    </div>
    `;
    feedbackDiv.style.display = 'block';

    if (errorDiv) {
        errorDiv.style.display = 'none';
    }

    setTimeout(() => {
        feedbackDiv.style.display = 'none';
        console.log('✅ Feedback de sucesso ocultado');
    }, 10000);
}

function mostrarFeedbackPersistente(chamadoId, status) {
    const feedbackDiv = document.getElementById('successFeedback');
    const errorDiv = document.getElementById('errorFeedback');

    if (!feedbackDiv) {
        console.log('ℹ️ Elemento de feedback persistente não encontrado');
        return;
    }

    feedbackDiv.innerHTML = `
    <strong><i class="bi bi-arrow-clockwise me-1"></i> Chamado em andamento</strong>
    <div class="mt-2">
        <strong>ID:</strong> ${chamadoId}<br>
        <strong>Status:</strong> ${status}<br>
        <small class="text-muted">Chamado carregado automaticamente</small>
    </div>
    `;
    feedbackDiv.style.display = 'block';

    if (errorDiv) {
        errorDiv.style.display = 'none';
    }

    setTimeout(() => {
        feedbackDiv.style.display = 'none';
        console.log('✅ Feedback persistente ocultado');
    }, 15000);
}

function mostrarErro(mensagem) {
    const errorDiv = document.getElementById('errorFeedback');
    const feedbackDiv = document.getElementById('successFeedback');
    
    if (!errorDiv) {
        console.log('ℹ️ Elemento de erro não encontrado');
        return;
    }

    errorDiv.innerHTML = `<strong><i class="bi bi-exclamation-triangle-fill me-1"></i> ${mensagem}</strong>`;
    errorDiv.style.display = 'block';

    if (feedbackDiv) {
        feedbackDiv.style.display = 'none';
    }

    setTimeout(() => {
        errorDiv.style.display = 'none';
        console.log('✅ Feedback de erro ocultado');
    }, 8000);
}

function adicionarMensagemDOM(mensagem, remetente, hora, messageId = null) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) {
        console.error('❌ Área de mensagens do chat não encontrada');
        return;
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${remetente} mb-3 d-flex flex-column ${remetente === 'usuario' ? 'align-items-end' : 'align-items-start'}`;
    
    // ✅ CORREÇÃO CRÍTICA: Usar ID consistente fornecido, não gerar dinamicamente
    if (messageId) {
        messageDiv.setAttribute('data-message-id', messageId);
    } else {
        // Fallback apenas se não houver ID
        messageDiv.setAttribute('data-message-id', `msg_${Date.now()}`);
    }

    const remetenteNome = remetente === 'bot' ? 'Bot Hyper' : 'Você';

    messageDiv.innerHTML = `
    <div class="fw-bold small mb-1">${remetenteNome}</div>
    <div class="p-3 rounded-3" style="background-color: ${remetente === 'usuario' ? '#0d6efd' : '#f1f3f5'}; color: ${remetente === 'usuario' ? 'white' : 'black'}; ">
        ${mensagem}
    </div>
    <div class="small text-muted mt-1">${hora}</div>
    `;
    chatMessages.appendChild(messageDiv);

    const initialState = document.querySelector('.chat-initial-state');
    if (initialState) {
        initialState.style.display = 'none';
    }
    
    console.log(`💬 Mensagem adicionada (${remetente}): ${mensagem.substring(0, 30)}... [ID: ${messageDiv.getAttribute('data-message-id')}]`);
}

function scrollParaFinal() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
        console.log('📜 Scroll para o final do chat');
    }
}