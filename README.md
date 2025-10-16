# Leroy Merlin RH LLM Toolkit

Esta biblioteca fornece uma solução ponta-a-ponta para classificar, extrair e agregar documentos de Recursos Humanos da Leroy Merlin utilizando o OpenAI Responses API. O fluxo proposto replica exatamente os prompts exigidos para as fases de extração/classificação e geração do CSV final.

## Funcionalidades

- **Classificação e extração** com `gpt-4o` (ou outro modelo definido) respeitando o schema fornecido.
- **Fallback automático** para `o3-mini` (ou modelo configurado) quando `confidence < 0.70` ou quando o documento necessita de revisão.
- **Agregação** dos resultados em CSV com ordem e cabeçalhos exigidos, seja via Python ou via LLM com prompt dedicado.
- **CLI** baseada em [Typer](https://typer.tiangolo.com/) para facilitar automações locais ou pipelines.

## Instalação

```bash
pip install -e .
```

Opcionalmente exporte a variável `OPENAI_API_KEY` ou crie um ficheiro `.env` com essa chave antes de executar os comandos.

## Preparação dos dados

Monte um ficheiro JSON de entrada com um objeto por documento:

```json
[
  {
    "ordinal": 12,
    "filename": "0248A936.pdf",
    "file_id": "file-xxxxxxxxxxx",
    "instrucoes": "Classifique o documento num dos tipos listados..."
  }
]
```

Os tipos de documento válidos (`leroy_doctypes`) devem ser fornecidos através da opção `--document-type` no comando da CLI. Basta repetir a opção para cada valor. Exemplo:

```bash
lm-rh-llm classify payload.json \
  --document-type CONTRATO_TRABALHO \
  --document-type RECIBO_VENCIMENTO \
  --document-type IRS \
  --document-type NIB \
  --document-type FICHA_ADMISSAO \
  --document-type RGPD \
  --document-type CC \
  --document-type OUTROS \
  --output resultados.json
```

O ficheiro `resultados.json` conterá o schema completo devolvido pelo modelo e o campo adicional `model` indicando qual motor produziu a resposta (principal ou fallback).

## Agregação para CSV

Para gerar o CSV final a partir dos resultados validados:

```bash
lm-rh-llm aggregate resultados.json --output final.csv
```

O comando acima utiliza a implementação determinística em Python. Caso deseje produzir o CSV via LLM empregando o prompt do agregador:

```bash
lm-rh-llm aggregate resultados.json --use-llm --model gpt-4o-mini --output final.csv
```

## Componentes Principais

- `lm_rh_llm/prompts.py`: concentra as mensagens de sistema e auxiliares para montar as mensagens do Responses API.
- `lm_rh_llm/classifier.py`: integra com o Responses API, controla fallback automático e normaliza a saída para o schema exigido.
- `lm_rh_llm/aggregator.py`: oferece as duas estratégias para geração do CSV.
- `lm_rh_llm/cli.py`: interface de linha de comando (Typer) para orquestrar a solução E2E.

## Teste Rápido com JSON Mock

Sem aceder aos modelos, é possível simular a agregação local criando um ficheiro `resultados.json` manualmente:

```json
[
  {
    "ordinal": 1,
    "filename": "0248A936.pdf",
    "document_type": "CONTRATO_TRABALHO",
    "document_date": "2018-07-12",
    "employee_name": "Renato Filipe Henriques Ferreira",
    "confidence": 0.92,
    "needs_review": false,
    "notes": ""
  }
]
```

Em seguida execute:

```bash
lm-rh-llm aggregate resultados.json
```

Resultado esperado:

```
ordem;ficheiro;tipo_documento;data_documento;nome_colaborador;confidencia;needs_review;notas
1;0248A936.pdf;CONTRATO_TRABALHO;2018-07-12;Renato Filipe Henriques Ferreira;0.92;false;
```

## Licença

Distribuído sob a licença MIT.
