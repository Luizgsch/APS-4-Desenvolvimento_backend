# APS 4 — Etapa 1: diagnóstico e preparação

Data: 18/11/2026. Somente a etapa 1 foi executada. Autenticação não foi implementada.

## Referências e limites

O PDF `C:\Users\luizg\Downloads\06-Temporarios\APS 4.pdf` foi lido integralmente: 12 páginas, seções 1 a 16. Ele define os requisitos acadêmicos. O texto fornecido pelo usuário define o trabalho em nove etapas e autoriza somente diagnóstico e preparação nesta execução.

Destino confirmado: `D:\Projetos\APS-4-Desenvolvimento-backend`.
Base inspecionada, sem alterações: `D:\Projetos\APS-3-Desenvolvimento-backend`.
Não foram encontrados arquivos AGENTS.md no destino ou nas pastas ancestrais verificadas; foram seguidas as instruções globais fornecidas na conversa.

## Estado encontrado e alterações

- Código Python, testes, scripts, dependências e banco da APS 4 coincidiam com os da APS 3 por SHA-256.
- A `.venv/pyvenv.cfg` ainda registrava criação na APS 3. O ambiente copiado foi preservado em `.venv-copiada-aps3/`; uma nova `.venv` foi criada no destino com CPython 3.13.15.
- Dependências existentes foram instaladas por `requirements-dev.txt`, que inclui `requirements.txt`. Nenhuma dependência de autenticação foi adicionada.
- `.vscode/settings.json` já selecionava `${workspaceFolder}\\.venv\\Scripts\\python.exe`; não precisou de alteração.
- README atualizado para identificar a APS 4, o destino e o estado real da etapa. Documentação histórica da APS 3 foi mantida.
- Evidências atuais foram gravadas em `docs/evidencias/aps4-etapa1/`, sem sobrescrever as evidências históricas.
- Nenhuma rota, entidade, regra de negócio ou banco foi alterado. Ambos os bancos existentes continham zero eventos, participantes e inscrições; nenhum banco foi apagado.

## Mapeamento dos requisitos

| Seções do PDF | Estado observado |
| --- | --- |
| 1 e 2 — contexto e objetivo | Continuidade confirmada; FastAPI, Pydantic, SQLite e SQLAlchemy presentes. Objetivo de segurança permanece pendente. |
| 3 e 3.1 — usuários | Ausentes: entidade, tabela, schemas e POST /usuarios. Participante existente não equivale a usuário autenticado. |
| 4 — hash | Ausente; biblioteca e serviço serão preparados nas etapas seguintes. |
| 5 e 6 — login e JWT | Ausentes: login, assinatura, expiração, validação e configuração da chave. |
| 7 e 8 — proteção e perfis | Rotas atuais são públicas; não há Bearer, dependências de identidade ou autorização por perfil. |
| 9 — identidade | GET /auth/me ausente. |
| 10 — continuidade | CRUD, inscrições, integridade, persistência e três relatórios aprovados na validação da base. Nova regressão será necessária após integrar segurança. |
| 11 — erros | Base possui validações Pydantic, 404, 409 e tratamento genérico de falhas SQLAlchemy. Erros 401/403 de autenticação e autorização ainda pendentes. |
| 12 — arquitetura | Controller, model, schema, service e database separados. Módulo security e recursos de usuário/autenticação serão adicionados nas etapas correspondentes. |
| 13 — testes | Base validada por testes automatizados e HTTP real. Os 12 cenários de segurança da APS 4 e demonstração pelo Swagger permanecem pendentes. |
| 14 e 15 — conclusão e entrega | Base executável; documentação final, segurança e repositório próprio ainda pendentes. APS 4 não está concluída. |

O professor exige a separação de responsabilidades; a árvore de arquivos da seção 12 é sugestão adaptável. Recriar a venv e separar evidências são decisões de preparação. Argon2/pwdlib e PyJWT são sugestões do PDF, ainda não instaladas. Procedimento local de criação de administrador será decisão de implementação, sem execução nesta etapa.

## Validação e resultados

- `python -m pip check`: nenhuma dependência quebrada.
- `python -X utf8 -m unittest discover -s tests -v`: **52 testes aprovados**. Cobrem CRUD, schemas, persistência após reabrir conexões/aplicação, duplicidades, referências inválidas, capacidade, concorrência, cascatas e relatórios.
- Script herdado `scripts/validar_cenarios.py`: **12 cenários da APS 3 aprovados**, por HTTP real com Uvicorn e reinicialização de processo. Não confundir com os 12 cenários de autenticação exigidos na seção 13 da APS 4.
- `/`, `/docs` e `/openapi.json` responderam por HTTP. A resposta de `/docs` não comprova interação visual com Swagger; Bearer ainda não existe.
- Bancos reais consultados em modo somente leitura: `PRAGMA integrity_check = ok`, `foreign_key_check = []` em ambas as pastas.
- Testes e cenários utilizam bancos temporários. A evidência de preservação registra hashes dos arquivos da base e dos bancos.

Uma primeira tentativa de testes ocorreu antes do término da instalação e falhou por ausência temporária de FastAPI. Após a instalação concluir, a execução completa passou; não foi necessária correção no código.

Evidências: `testes.txt`, `dependencias.txt`, `cenarios.json` e `preservacao.json` em `docs/evidencias/aps4-etapa1/`.

## Execução preparada

Na raiz da APS 4:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Swagger: http://127.0.0.1:8000/docs. Os servidores temporários usados na validação foram encerrados.

Para repetir os testes sem modificar dados existentes:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
```

O script herdado pode ser executado diretamente, mas sua saída padrão sobrescreve `docs/evidencias/etapa8.json`, que pertence ao histórico da APS 3. Nesta etapa, ele foi importado e seu destino OUTPUT foi redirecionado para `docs/evidencias/aps4-etapa1/cenarios.json`.

## Pendências e limitações

1. Nenhum impedimento funcional encontrado para iniciar a etapa 2. Segurança aguarda autorização da próxima etapa.
2. `origin` ainda aponta a `https://github.com/Luizgsch/APS-3-Desenvolvimento-backend.git`. Não houve push nem mudança de remoto. Será necessário definir o repositório da APS 4 antes da entrega.
3. README e documentos herdados ainda contêm referências históricas à APS 3. A documentação completa de autenticação será produzida na etapa 9.
4. Demonstração visual no Swagger, inclusive Bearer, continua pendente. Validação desta etapa foi automatizada e por HTTP.
5. A configuração SQLite atual depende de Python >= 3.12; ambiente validado: Windows x64, Python 3.13.15.

Etapa 2 não iniciada.
