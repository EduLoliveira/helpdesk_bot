from django import forms
from .models import Chamado, Departamento, ConfirmacaoResolucao

class ChamadoForm(forms.ModelForm):
    class Meta:
        model = Chamado
        fields = ['titulo', 'descricao', 'nome_solicitante', 'departamento', 'modalidade_presencial']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descreva brevemente o problema...'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Descreva o que aconteceu, quando começou, o que você já tentou fazer...'
            }),
            'nome_solicitante': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome completo'
            }),
            'departamento': forms.Select(attrs={
                'class': 'form-select'
            }),
            'modalidade_presencial': forms.RadioSelect(choices=[(True, 'Presencial'), (False, 'Home Office')])
        }
        labels = {
            'modalidade_presencial': 'Onde você está?'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['departamento'].empty_label = "Selecione o departamento"

class ConfirmacaoResolucaoForm(forms.ModelForm):
    class Meta:
        model = ConfirmacaoResolucao
        fields = ['satisfacao', 'comentario']
        widgets = {
            'satisfacao': forms.RadioSelect(),
            'comentario': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Deixe um comentário sobre o atendimento...'
            })
        }