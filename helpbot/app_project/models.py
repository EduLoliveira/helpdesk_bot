from django.db import models
import uuid
import random
import string
from django.utils import timezone

class Usuario(models.Model):
    id_usuario = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_suporte = models.IntegerField(verbose_name='Código Suporte')
    username = models.CharField(max_length=20, unique=True, verbose_name='Username')
    TIPO_CHOICES = [
        ('suporte', 'Suporte'),
        ('colaborador', 'Colaborador'),
    ]
    tipo_usuario = models.CharField(max_length=15, choices=TIPO_CHOICES, default='colaborador', verbose_name='Tipo de Usuário')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    

class Departamento(models.Model):
    id_departamento = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=100, verbose_name='Nome do Departamento')
    descricao = models.TextField(blank=True, null=True, verbose_name='Descrição')
    
    def __str__(self):
        return self.nome

class Chamado(models.Model):
    URGENCIA_CHOICES = [
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('urgente', 'Urgente'),
    ]
    
    STATUS_CHOICES = [
        ('em_andamento', 'Em Andamento'),
        ('resolvido', 'Resolvido'),
    ]
    
    id_chamado = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titulo = models.CharField(max_length=200, verbose_name='Título do Problema')
    descricao = models.TextField(verbose_name='Descrição Detalhada')
    nome_solicitante = models.CharField(max_length=100, verbose_name='Nome do Solicitante', blank=True)
    
    # Departamento como ForeignKey
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE, verbose_name='Departamento')
    
    # Modalidade: Presencial (True) / Home Office (False)
    modalidade_presencial = models.BooleanField(default=True, verbose_name='Modalidade Presencial')
    
    # Urgência determinada automaticamente
    urgencia = models.CharField(
        max_length=10, 
        choices=URGENCIA_CHOICES, 
        default='media',
        verbose_name='Nível de Urgência'
    )
    
    # Status do chamado
    status = models.CharField(
        max_length=15, 
        choices=STATUS_CHOICES, 
        default='em_andamento',
        verbose_name='Status do Chamado'
    )
    
    # Usuário que criou o chamado (opcional)
    usuario = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='Usuário Solicitante'
    )
    
    # ✅ CAMPOS PARA SUPORTE
    visualizado_suporte = models.BooleanField(default=False, verbose_name='Visualizado pelo Suporte')
    controle_chat_suporte = models.BooleanField(default=False, verbose_name='Controle do Chat pelo Suporte')
    suporte_responsavel = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='chamados_atendidos',
        verbose_name='Suporte Responsável'
    )
    
    # Datas importantes
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    data_resolucao = models.DateTimeField(null=True, blank=True, verbose_name='Data de Resolução')
    
    # ID legível para exibição
    id_legivel = models.CharField(max_length=20, unique=True, blank=True, verbose_name='ID Legível')
    
    def save(self, *args, **kwargs):
        # ✅ CORREÇÃO: Garantir que nome_solicitante seja preenchido
        if not self.nome_solicitante and self.usuario:
            self.nome_solicitante = self.usuario.username
        
        # Gerar ID legível se não existir
        if not self.id_legivel:
            self.id_legivel = self.gerar_id_legivel()
        
        # Determinar urgência automaticamente baseada no título
        if not self.pk:  # Apenas na criação
            self.urgencia = self.determinar_urgencia()
        
        # Registrar data de resolução se o status mudou para resolvido
        if self.pk:
            try:
                original = Chamado.objects.get(pk=self.pk)
                if original.status != 'resolvido' and self.status == 'resolvido':
                    self.data_resolucao = timezone.now()
            except Chamado.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
    
    def gerar_id_legivel(self):
        """Gera ID legível único"""
        while True:
            # ✅ CORREÇÃO: ID mais curto e garantia de unicidade
            novo_id = f"TKT-{random.randint(10000, 99999)}"
            if not Chamado.objects.filter(id_legivel=novo_id).exists():
                return novo_id
    
    def determinar_urgencia(self):
        """Determina urgência automaticamente baseada no título"""
        titulo_lower = self.titulo.lower()
        descricao_lower = self.descricao.lower()
        texto_completo = f"{titulo_lower} {descricao_lower}"
        
        # ✅ CORREÇÃO: Palavras-chave mais abrangentes
        urgent_keywords = [
            'urgente', 'crítico', 'critico', 'emergência', 'emergencia', 
            'parado', 'fora do ar', 'queda', 'não funciona', 'nao funciona',
            'quebrado', 'prioridade', 'impeditivo', 'bloqueado', 'crash',
            'erro crítico', 'sistema down', 'indisponível', 'paralisado'
        ]
        
        low_keywords = [
            'dúvida', 'duvida', 'consulta', 'informação', 'informacao',
            'sugestão', 'sugestao', 'melhoria', 'questionamento', 
            'orientação', 'orientacao', 'curiosidade', 'dica'
        ]
        
        for keyword in urgent_keywords:
            if keyword in texto_completo:
                return 'urgente'
        
        for keyword in low_keywords:
            if keyword in texto_completo:
                return 'baixa'
        
        return 'media'
    
    def get_nome_exibicao(self):
        """✅ MÉTODO: Obter nome do solicitante"""
        if self.nome_solicitante:
            return self.nome_solicitante
        elif self.usuario:
            return self.usuario.username
        return "Solicitante"
    
    def get_modalidade_display(self):
        return "Presencial" if self.modalidade_presencial else "Home Office"
    
    def get_urgencia_display(self):
        for choice in self.URGENCIA_CHOICES:
            if choice[0] == self.urgencia:
                return choice[1]
        return self.urgencia
    
    def get_status_display(self):
        for choice in self.STATUS_CHOICES:
            if choice[0] == self.status:
                return choice[1]
        return self.status
    
    @property
    def tempo_decorrido(self):
        diferenca = timezone.now() - self.criado_em
        dias = diferenca.days
        horas = diferenca.seconds // 3600
        minutos = (diferenca.seconds % 3600) // 60
        
        if dias > 0:
            return f"{dias}d {horas}h"
        elif horas > 0:
            return f"{horas}h {minutos}min"
        else:
            return f"{minutos}min"
    
    def __str__(self):
        return f"{self.id_legivel} - {self.titulo}"
    
    class Meta:
        ordering = ['-criado_em']

class InteracaoChamado(models.Model):
    TIPO_REMETENTE = [
        ('usuario', 'Usuário'),
        ('bot', 'Bot'),
        ('suporte', 'Suporte'),
    ]
    
    ACAO_BOT_CHOICES = [
        ('saudacao', 'Saudação Inicial'),
        ('confirmacao', 'Confirmação do Chamado'),
        ('classificacao', 'Classificação da Urgência'),
        ('status', 'Atualização de Status'),
        ('resposta', 'Resposta Automática'),
        ('verificacao_tempo', 'Verificação de Tempo'),
        ('verificacao_urgente', 'Verificação Urgente'),
        ('finalizacao', 'Finalização'),
        ('notificacao_novo_chamado', 'Notificação Novo Chamado'),
        ('atualizacao_status', 'Atualização de Status'),
        ('mensagem', 'Mensagem'),
        ('inicio', 'Início'),
        ('intermediacao_ativa', 'Intermediação Ativa'),
        ('mensagem_fallback', 'Mensagem Fallback'),
    ]
    
    id_interacao = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name='interacoes')
    remetente = models.CharField(max_length=10, choices=TIPO_REMETENTE, verbose_name='Remetente')
    mensagem = models.TextField(verbose_name='Mensagem')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    visualizada_automatica = models.BooleanField(default=False)
    acao_bot = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name='Ação do Bot',
        choices=ACAO_BOT_CHOICES
    )
    
    # ✅ Suporte responsável pela mensagem
    suporte_responsavel = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='Suporte Responsável'
    )
    
    class Meta:
        ordering = ['criado_em']
        verbose_name = 'Interação do Chamado'
        verbose_name_plural = 'Interações dos Chamados'
    
    def __str__(self):
        return f"{self.chamado.id_legivel} - {self.remetente} - {self.criado_em.strftime('%d/%m/%Y %H:%M')}"

class ConfirmacaoResolucao(models.Model):
    id_confirmacao = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chamado = models.OneToOneField(Chamado, on_delete=models.CASCADE, related_name='confirmacao')
    confirmado_por = models.ForeignKey(Usuario, on_delete=models.CASCADE, verbose_name='Confirmado por')
    data_confirmacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de Confirmação')
    satisfacao = models.IntegerField(
        choices=[(1, '1 - Muito Insatisfeito'), (2, '2'), (3, '3'), (4, '4'), (5, '5 - Muito Satisfeito')],
        verbose_name='Nível de Satisfação'
    )
    comentario = models.TextField(blank=True, null=True, verbose_name='Comentário')
    
    def __str__(self):
        return f"Confirmação - {self.chamado.id_legivel}"

# models.py - ATUALIZE o modelo Notificacao

class Notificacao(models.Model):
    TIPO_CHOICES = [
        ('novo_chamado', 'Novo Chamado'),
        ('atualizacao', 'Atualização'),
        ('mensagem', 'Nova Mensagem'),
        ('novo_chamado_broadcast', 'Novo Chamado (Broadcast)'),  # ✅ ADICIONE
        ('sistema_novo_chamado', 'Sistema - Novo Chamado'),  # ✅ ADICIONE
    ]
    
    id_notificacao = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='notificacoes')
    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name='notificacoes')
    mensagem = models.TextField()
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default='novo_chamado')  # ✅ ATUALIZE max_length
    lida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    
    # ✅ ADICIONE ESTES CAMPOS PARA BROADCAST:
    broadcast = models.BooleanField(default=False, verbose_name="Notificação Broadcast")
    broadcast_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="ID do Broadcast")
    
    class Meta:
        db_table = 'notificacoes'
        ordering = ['-criado_em']
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
    
    def __str__(self):
        return f"Notificação para {self.usuario.username} - {self.get_tipo_display()}"