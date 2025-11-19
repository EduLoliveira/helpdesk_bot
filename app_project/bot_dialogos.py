# bot_dialogos.py - ATUALIZADO
from django.utils import timezone
from .models import Chamado, Notificacao

class BibliotecaDialogosBot:
    """
    Biblioteca centralizada para todos os diálogos do bot
    Simula uma biblioteca de mensagens e respostas inteligentes
    """
    
    @staticmethod
    def get_saudacao_inicial(nome_solicitante):
        """Retorna apenas a saudação inicial"""
        return {
            'mensagem': f"👋 Olá, {nome_solicitante}!",
            'acao_bot': 'saudacao'
        }

    @staticmethod
    def get_sequencia_inicial_completa(chamado, nome_solicitante, departamento, modalidade_presencial):
        """Retorna a sequência completa inicial de mensagens"""
        return [
            {
                'mensagem': f"👋 Olá, {nome_solicitante}!",
                'acao_bot': 'saudacao'
            },
            {
                'mensagem': f"✅ Recebi seu chamado do departamento de {departamento.nome}.",
                'acao_bot': 'confirmacao'
            },
            {
                'mensagem': f"📋 **Confirmação do Chamado:**<br>🏠 Localização: {'Presencial' if modalidade_presencial else 'Home Office'}<br>📝 Problema: \"{chamado.titulo}\"<br>🆔 ID: {chamado.id_legivel}",
                'acao_bot': 'confirmacao'
            },
            {
                'mensagem': f"🔍 Analisando e classificando o problema...",
                'acao_bot': 'classificacao'
            },
            {
                'mensagem': f"📋 **Classificação:** {chamado.get_urgencia_display()}<br>📊 **Status:** {chamado.get_status_display()}",
                'acao_bot': 'classificacao'
            },
            {
                'mensagem': f"⏱️ **Tempo estimado de atendimento:** até 10 minutos",
                'acao_bot': 'tempo_estimado',
            },
            {
                'mensagem': "💬 Enquanto isso, se precisar de mais alguma coisa, é só me avisar!",
                'acao_bot': 'tempo_estimado',
            }
        ]
    
    @staticmethod
    def get_notificacao_novo_chamado(chamado):
        """Gera notificação para usuários de suporte sobre novo chamado"""
        return {
            'mensagem': f"🚨 **NOVO CHAMADO CRIADO**<br>📝 {chamado.titulo}<br>👤 {chamado.nome_solicitante}<br>🏢 {chamado.departamento.nome}<br>🆔 {chamado.id_legivel}",
            'acao_bot': 'notificacao_novo_chamado',
            'notificacao': True,
            'broadcast': True  # Indica que deve ser enviado para todos os suportes
        }
    
    @staticmethod
    def get_verificacao_tempo():
        """Verificação após 10 minutos"""
        return {
            'mensagem': "⏰ **Verificação automática:** Já se passaram 10 minutos. O suporte já atendeu seu chamado? Se sim, por favor confirme se foi resolvido.",
            'acao_bot': 'verificacao_tempo'
        }
    
    @staticmethod
    def get_verificacao_urgente():
        """Verificação urgente após 15 minutos"""
        return {
            'mensagem': "🚨 **Verificação urgente:** Já se passaram 15 minutos. Caso o suporte já tenha atendido, por favor confirme a resolução para finalizarmos o chamado.",
            'acao_bot': 'verificacao_urgente'
        }
    
    @staticmethod
    def get_finalizacao_suporte():
        """Confirmação de finalização pelo suporte"""
        return {
            'mensagem': "✅ **Chamado finalizado!** O suporte confirmou que o atendimento foi concluído com sucesso.",
            'acao_bot': 'finalizacao'
        }
    
    @staticmethod
    def get_finalizacao_usuario():
        """Confirmação de finalização pelo usuário"""
        return {
            'mensagem': "🎉 **Excelente!** Chamado finalizado com sucesso. Obrigado por confirmar a resolução!",
            'acao_bot': 'finalizacao_usuario'
        }
    
    @staticmethod
    def get_resposta_inteligente(mensagem, chamado, usuario):
        """
        Sistema inteligente de respostas baseado em contexto
        ATUALIZADO: Agora recebe o usuário para verificar tipo
        """
        # Verificar se o chamado já está resolvido
        if chamado.status == 'resolvido':
            return {
                'mensagem': "✅ **Este chamado já foi finalizado!** Se precisar de mais ajuda, por favor abra um novo chamado.",
                'acao_bot': 'chamado_finalizado',
                'intencao_detectada': 'chamado_finalizado'
            }
        
        mensagem_lower = mensagem.lower()
        
        # Dicionário de intenções e respostas
        intencoes_respostas = {
            'resolucao_confirmada': {
                'palavras_chave': ['resolvido', 'concluído', 'finalizado', 'problema solucionado', 'já resolvi', 'funcionando'],
                'resposta': "🎉 **Perfeito!** Marquei seu chamado como RESOLVIDO. Obrigado por confirmar! Se tiver mais alguma necessidade, estarei aqui para ajudar.",
                'acao': 'marcar_resolvido'
            },
            'agradecimento': {
                'palavras_chave': ['obrigado', 'obrigada', 'agradeço', 'valeu', 'agradecido', 'agradecida'],
                'resposta': "😊 De nada! Estou aqui para ajudar. Se tiver mais alguma dúvida, é só perguntar.",
                'acao': None
            },
            'prazo': {
                'palavras_chave': ['prazo', 'tempo', 'quando', 'quanto tempo', 'demora', 'prazos'],
                'resposta': f"⏰ Baseado na urgência **{chamado.get_urgencia_display()}** do seu chamado, nosso tempo médio de resposta é de 10-20 minutos. Nossa equipe está trabalhando para resolvê-lo o mais rápido possível!",
                'acao': None
            },
            'status': {
                'palavras_chave': ['status', 'andamento', 'atualização', 'situação', 'andando'],
                'resposta': f"📊 **Status Atual:** {chamado.get_status_display()}<br>🚨 **Urgência:** {chamado.get_urgencia_display()}<br>⏱️ **Tempo decorrido:** {chamado.tempo_decorrido}",
                'acao': None
            },
            'contato': {
                'palavras_chave': ['contato', 'telefone', 'email', 'falar', 'contatar', 'ligar'],
                'resposta': "📞 Você pode entrar em contato com nosso suporte pelo:<br>• 📧 Email: suporte@empresa.com<br>• 📞 Telefone: (11) 9999-9999<br>• 💬 Este chat mesmo!",
                'acao': None
            },
            'urgencia': {
                'palavras_chave': ['urgente', 'urgência', 'rápido', 'prioridade', 'emergência', 'emergencia'],
                'resposta': "🚨 Entendi que é urgente! Estou notificando nossa equipe sobre a prioridade. Em breve teremos novidades.",
                'acao': None
            },
            'departamento_errado': {
                'palavras_chave': ['departamento errado', 'departamento incorreto', 'setor errado', 'mudei departamento'],
                'resposta': "🔄 Entendi que o departamento está incorreto. Vou encaminhar para o departamento correto. Qual seria o departamento adequado para seu chamado?",
                'acao': None
            },
            'cancelamento': {
                'palavras_chave': ['não é mais necessario', 'não preciso mais', 'cancelar', 'resolvido sozinho', 'já resolvi'],
                'resposta': "✅ **Entendido!** Cancelei seu chamado e marquei como resolvido. Se precisar de ajuda novamente, é só abrir um novo chamado!",
                'acao': 'marcar_resolvido'
            },
            'saudacao': {
                'palavras_chave': ['oi', 'olá', 'ola', 'bom dia', 'boa tarde', 'boa noite'],
                'resposta': "👋 Olá! Em que posso ajudá-lo hoje?",
                'acao': None
            },
            'despedida': {
                'palavras_chave': ['tchau', 'adeus', 'até logo', 'flw', 'vlw'],
                'resposta': "👋 Até logo! Estarei aqui se precisar de mais alguma coisa.",
                'acao': None
            },
            'ajuda': {
                'palavras_chave': ['help', 'ajuda', 'socorro', 'auxílio'],
                'resposta': "🆘 Estou aqui para ajudar! Pode me contar qual é o problema ou dúvida que você está tendo?",
                'acao': None
            }
        }
        
        # Buscar a intenção correspondente
        for intencao, dados in intencoes_respostas.items():
            for palavra in dados['palavras_chave']:
                if palavra in mensagem_lower:
                    # Executar ação se houver
                    if dados['acao'] == 'marcar_resolvido':
                        chamado.status = 'resolvido'
                        chamado.data_resolucao = timezone.now()
                        chamado.save()
                    
                    return {
                        'mensagem': dados['resposta'],
                        'acao_bot': 'resposta_inteligente',
                        'intencao_detectada': intencao
                    }
        
        # Resposta personalizada baseada no tipo de usuário
        if usuario.tipo_usuario == 'suporte':
            resposta_padrao = "🤖 Entendi sua mensagem! Como membro do suporte, você pode atualizar o status do chamado ou interagir com o usuário para resolver o problema."
        else:
            resposta_padrao = "🤖 Entendi sua mensagem! Nossa equipe de suporte já foi notificada e em breve dará sequência ao seu chamado. Enquanto isso, posso ajudar com alguma informação específica?"
        
        return {
            'mensagem': resposta_padrao,
            'acao_bot': 'resposta_padrao',
            'intencao_detectada': 'nao_identificada'
        }

# Instância global para fácil acesso
bot_dialogos = BibliotecaDialogosBot()