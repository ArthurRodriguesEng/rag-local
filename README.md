# rag-local

RAG local em Python para ingerir documentos, gerar embeddings com Ollama,
armazenar vetores no PostgreSQL com pgvector e, depois, responder perguntas
com busca vetorial e LLM local.

## Stack

- Python
- SQLAlchemy
- PostgreSQL com pgvector
- Docker Compose
- Ollama
- Modelo de embedding: `bge-m3`
- Modelo de chat: `llama3.2:3b`
- Modelo de chat balanceado: `qwen2.5:7b-instruct`

## Requisitos para GPU NVIDIA

O serviço do Ollama no Docker Compose está configurado com `runtime: nvidia`.
Para usar aceleração por GPU, o host precisa ter:

- driver NVIDIA instalado;
- NVIDIA Container Toolkit instalado;
- Docker com o runtime NVIDIA configurado.

Sem esses requisitos, o serviço `ollama` pode falhar ao subir. Para validar o
acesso à GPU pelo Docker, teste um container CUDA compatível com sua instalação
ou acompanhe o uso da GPU no host com:

```bash
nvidia-smi
```

## Passo atual: chatbot RAG interno

O objetivo desta etapa é transformar arquivos locais em uma base de
conhecimento consultável por chat. O sistema ingere documentos, busca trechos
relevantes, monta um prompt com contexto, preserva histórico de conversa quando
necessário e mostra as fontes usadas na resposta.

Diagrama do fluxo: `docs/fluxo-rag-local.excalidraw`.

Fluxo:

```text
arquivo -> DocumentLoader -> RecursiveTextChunker -> EmbeddingService
        -> DocumentRepository -> ChunkRepository -> commit
```

O `IngestionService` é a camada que coordena esse pipeline:

1. Recebe o caminho do arquivo.
2. Extrai o texto com `DocumentLoader`.
3. Divide o texto com `RecursiveTextChunker`.
4. Cria um registro em `documents`.
5. Gera um embedding para cada chunk.
6. Cria os registros em `chunks`.
7. Faz `commit` somente no final.
8. Faz `rollback` se qualquer etapa falhar.

Esse controle de transação evita salvar um documento pela metade. Se a geração
de embedding falhar no meio do processo, nada daquele documento é persistido.

Depois da ingestão, o `ChunkRepository.search_similar()` recebe o embedding de
uma pergunta e ordena os chunks pela distância cosseno do pgvector:

```text
pergunta -> EmbeddingService -> ChunkRepository.search_similar()
         -> chunks mais relevantes
```

Com os chunks encontrados, o `RagService` monta um prompt com contexto e chama
o `ChatService`, que usa o modelo `llama3.2:3b` no Ollama:

```text
pergunta -> histórico -> embedding -> busca vetorial -> contexto
         -> modelo de chat -> resposta com fontes
```

## Arquitetura do código

O projeto segue uma separação simples de responsabilidades para facilitar
manutenção e reaproveitamento em outros RAGs:

```text
app/main.py              -> cria a aplicação FastAPI e registra rotas
app/api/                 -> camada HTTP: rotas, router principal e dependências
app/schemas/             -> contratos Pydantic de entrada e saída da API
app/services/            -> regras de aplicação: ingestão, RAG, chat, embeddings
app/repositories/        -> acesso ao banco com SQLAlchemy
app/models/              -> models ORM e estrutura das tabelas
app/config/              -> settings, conexão com banco e perfis de execução
app/cli.py               -> interface de terminal usando os mesmos services
```

Regra prática: endpoints HTTP não devem conter regra de negócio pesada. Eles
validam entrada, abrem sessão, chamam services e retornam schemas. A lógica de
RAG deve continuar em `services`, e o acesso ao PostgreSQL deve continuar em
`repositories`.

## Como usar pela CLI

Ative a virtualenv do projeto:

```bash
source .venv/bin/activate
```

Suba a infraestrutura:

```bash
docker compose up -d
```

O Docker Compose também sobe um serviço auxiliar que baixa automaticamente os
modelos usados pelo projeto no Ollama:

- `bge-m3`
- `llama3.2:3b`
- `qwen2.5:7b-instruct`

Acompanhe o download inicial com:

```bash
docker compose logs -f ollama-model-loader
```

Depois, confirme os modelos instalados:

```bash
docker exec -it rag-ollama ollama list
```

Copie o arquivo de configuração de exemplo, se ainda não existir `.env`:

```bash
cp .env.example .env
```

## Configuração

O projeto foi organizado para ser reaproveitado em outros RAGs mudando
parâmetros no `.env`:

```text
DEBUG                        -> ativa logs detalhados quando true
UPLOAD_DIR                   -> pasta usada pela API para arquivos enviados
RAG_PROFILE                  -> perfil padrão: fast_local, balanced_local ou deep_local
EMBEDDING_MODEL              -> modelo usado para gerar embeddings
EMBEDDING_DIMENSION          -> dimensão do vetor salvo no pgvector
CHAT_MODEL                   -> modelo local do Ollama usado para gerar respostas
CHUNK_SIZE                   -> tamanho máximo de cada chunk
CHUNK_OVERLAP                -> sobreposição entre chunks
RETRIEVAL_LIMIT              -> quantidade padrão de chunks no contexto
RETRIEVAL_CANDIDATE_LIMIT    -> quantidade buscada antes de filtrar contexto
RETRIEVAL_MAX_DISTANCE       -> distância máxima aceita na busca vetorial
RAG_MAX_CONTEXT_CHARS        -> limite de caracteres do contexto no prompt
RAG_MEMORY_LIMIT             -> quantidade de mensagens recentes usadas como memória
RAG_MEMORY_MAX_CHARS         -> limite de caracteres da memória no prompt
RAG_RESPONSE_MODE            -> modo de resposta: concise, analytical ou deep
RAG_PROMPT_PATH              -> arquivo com prompt base do assistente
RAG_SYSTEM_PROMPT            -> instrução base do assistente
RAG_EMPTY_CONTEXT_MESSAGE    -> resposta quando o contexto for insuficiente
EMBEDDING_TIMEOUT_SECONDS    -> timeout da chamada de embedding
CHAT_TIMEOUT_SECONDS         -> timeout da chamada de chat
```

O projeto usa Ollama local para chat e embeddings. O default atual de embedding
é `bge-m3` com `EMBEDDING_DIMENSION=1024`.

Se você mudar `EMBEDDING_MODEL` ou `EMBEDDING_DIMENSION`, precisa recriar a
tabela de chunks e reingerir os documentos. Em desenvolvimento local:

```bash
python -m app.cli reset-db --yes
python -m app.cli ingest documents/manual_python.txt
```

Crie a extensão `vector` e as tabelas:

```bash
python -m app.cli init-db
```

Ingere um documento:

```bash
python -m app.cli ingest documents/manual_python.txt
```

Você também pode sobrescrever parâmetros da ingestão no terminal:

```bash
python -m app.cli ingest documents/manual_python.txt \
  --chunk-size 800 \
  --chunk-overlap 120 \
  --embedding-model bge-m3
```

Resultado esperado:

```text
Documento ingerido com sucesso.
ID: ...
Arquivo: manual_python.txt
Total de chunks: ...
```

Faça uma pergunta:

```bash
python -m app.cli ask "Como Python pode ser usado em projetos de inteligência artificial?"
```

Agora a resposta também mostra as fontes usadas:

```text
Fontes:
- [1] manual_python.txt, trecho 2, distância 0.1821
```

Você também pode sobrescrever parâmetros da pergunta no terminal:

```bash
python -m app.cli ask "Como Python pode ser usado em IA?" \
  --limit 3 \
  --chat-model llama3.2:3b \
  --system-prompt "Você é um assistente técnico. Responda em português, com base apenas no contexto."
```

Liste os perfis disponíveis:

```bash
python -m app.cli profiles
```

Use um perfil específico:

```bash
python -m app.cli ask "Quais são os pontos principais do documento?" \
  --profile balanced_local
```

Controle a profundidade da resposta por comando:

```bash
python -m app.cli ask "Analise os resultados do artigo" \
  --profile fast_local \
  --response-mode deep \
  --limit 4
```

Modos disponíveis:

```text
concise     -> resposta curta e objetiva
analytical  -> resposta explicada, com evidências e insights
deep        -> resposta detalhada, com análise, limitações e implicações
```

Para tornar respostas mais profundas por padrão, altere o `.env`:

```env
RAG_PROFILE=deep_local
```

Inicie um chat interativo com histórico:

```bash
python -m app.cli chat --profile fast_local --response-mode analytical
```

Controle a memória recente do agente por comando:

```bash
python -m app.cli chat \
  --profile balanced_local \
  --memory-limit 8 \
  --memory-max-chars 2400
```

`--memory-limit` define quantas mensagens anteriores são buscadas da conversa.
`--memory-max-chars` limita quantos caracteres dessa memória entram no prompt.

O perfil `fast_local` foi calibrado para máquinas locais mais limitadas:
usa menos chunks e um contexto menor para reduzir a chance do Ollama encerrar
o processo por falta de recurso.

Para salvar uma pergunta isolada em uma conversa:

```bash
python -m app.cli ask "Resuma o documento" --save-conversation
```

Liste documentos cadastrados:

```bash
python -m app.cli documents
```

Para entender melhor o que o sistema está fazendo no terminal, ative:

```env
DEBUG=true
```

Resultado esperado:

```text
Pergunta: Como Python pode ser usado em projetos de inteligência artificial?
Chunks usados: ...

Resposta:
...
```

Limpe todos os documentos e chunks do banco:

```bash
python -m app.cli clear
```

Para limpar sem confirmação interativa:

```bash
python -m app.cli clear --yes
```

## API HTTP

A aplicação também possui uma FastAPI inicial:

```bash
uvicorn app.main:app --reload
```

Endpoints disponíveis:

```text
GET    /health
POST   /documents/upload?filename=arquivo.txt
GET    /documents
DELETE /documents/{document_id}
POST   /chat
```

Upload usando corpo binário:

```bash
curl -X POST "http://localhost:8000/documents/upload?filename=manual.txt" \
  --data-binary @documents/manual_python.txt
```

Chat:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Quais são os pontos principais?",
    "profile": "fast_local",
    "memory_limit": 4,
    "memory_max_chars": 1200
  }'
```

Como foram adicionadas tabelas de conversa e novas colunas em `chunks`, recrie
o banco local antes de usar esta versão se você já tinha dados antigos:

```bash
python -m app.cli reset-db --yes
python -m app.cli ingest documents/manual_python.txt
```

## Scripts didáticos

Os scripts em `scripts/` continuam úteis para estudar cada etapa isolada:

```text
scripts/test_document_loader.py   -> testa extração de texto
scripts/test_recursive_chunker.py -> testa divisão recursiva
scripts/test_ingestion.py         -> testa ingestão completa
scripts/test_vector_search.py     -> testa busca vetorial
scripts/test_rag_chat.py          -> testa RAG completo
```

Prefira rodar scripts a partir da raiz do projeto:

```bash
python -m scripts.test_rag_chat
```

O `scripts/test_rag_chat.py` também aceita execução direta pelo caminho do
arquivo, mas o formato com `-m` é o mais consistente para imports Python.

## Problemas comuns

Se aparecer:

```text
different vector dimensions 768 and 1024
```

o banco ainda tem embeddings antigos. Recrie as tabelas e ingira os documentos
novamente:

```bash
python -m app.cli reset-db --yes
python -m app.cli ingest documents/manual_python.txt
```

Se aparecer:

```text
python-dotenv could not parse statement
```

o `.env` tem alguma linha inválida. Cada configuração precisa estar em uma
única linha no formato `CHAVE=valor`. Prompts longos devem ficar em uma linha
só ou ser movidos futuramente para um arquivo de prompt.

Se o Ollama retornar algo como:

```text
llama-server process has terminated: signal: killed
model runner has unexpectedly stopped
```

o modelo provavelmente foi encerrado por limite de memória/processamento ou
por prompt grande demais. Use o perfil leve ou reduza o contexto:

```bash
python -m app.cli ask "sua pergunta" --profile fast_local --limit 2
python -m app.cli chat --profile fast_local --limit 2
```

## Próximos passos sugeridos

- Adicionar migrations com Alembic para evoluir o banco sem `reset-db`.
- Criar avaliação automática de qualidade das respostas.
- Implementar reranking dos chunks recuperados.
- Adicionar autenticação na API antes de uso em rede interna.
