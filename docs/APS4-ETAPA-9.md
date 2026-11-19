# APS 4 — Etapa 9: documentação e entrega

Preparação local: 18/11/2026. Conexão do repositório próprio autorizada em 19/11/2026.

## Alterações

- README revisado: identificação da APS 4, instalação em outra pasta, chave externa, administrador local, cadastro/login, uso do Bearer no Swagger, permissões, exemplos JSON, erros HTTP, estrutura atual e reprodução dos testes.
- Corrigidas referências herdadas a 52 testes, estrutura sem usuário/security, pacote APS 3 e repositório anterior como se fossem a entrega atual.
- `requirements.txt` conferido com as dependências usadas; hash Argon2/pwdlib, PyJWT, python-dotenv, FastAPI, Pydantic e SQLAlchemy estão fixados. Testes usam requirements-dev.txt.
- Empacotador adaptado para `APS-4-Desenvolvimento-backend.zip`, incluindo security e `.env.example`, código, testes, documentação e evidências APS4.
- Ambientes virtuais, Git, bancos, temporários, arquivos de configuração reais e históricos APS 3 ficam fora do ZIP. A lista permitida é explícita; arquivos sensíveis, chave local e possíveis JWTs são recusados antes da geração.
- ZIP acompanhado de manifesto SHA-256 por arquivo, dentro e fora do pacote, e checksum do ZIP.
- O repositório esperado `Luizgsch/APS-4-Desenvolvimento-backend` retornou 404 no conector GitHub. A pesquisa de repositórios acessíveis mostrou somente APS 2 e APS 3 para esse nome de projeto. Não se conclui que não possa existir um repositório privado inacessível ou com outro nome.
- Em 19/11/2026, o usuário informou e autorizou conectar `https://github.com/Luizgsch/APS-4-Desenvolvimento_backend.git`. O repositório público foi confirmado vazio e com permissão de escrita. O endereço usa sublinhado antes de backend, diferente do nome pesquisado inicialmente. Nenhum push para APS 3 foi realizado.

## Conferência da seção 14

| Requisito mínimo | Evidência |
| --- | --- |
| FastAPI | main.py e controllers; chamadas HTTP reais |
| Continuidade da APS 3 | testes de CRUD, vagas, concorrência, cascatas e 12 cenários de negócio |
| SQLite e SQLAlchemy | database.py, modelos e testes de persistência/reinicialização |
| Cadastro de usuários | POST /usuarios; resposta pública e validações |
| Hash seguro | pwdlib/Argon2id, verificação do arquivo SQLite temporário |
| Autenticação por e-mail e senha | POST /auth/login, sucesso e falhas genéricas |
| Geração/validação JWT | security/tokens.py e testes adversariais |
| Prazo de validade | exp em UTC, duração configurável, expirado rejeitado |
| Rotas protegidas | dependência Bearer centralizada, 401 para token ausente/inválido |
| Dois perfis | usuario/administrador; autorização pelo perfil atual do banco |
| Usuário autenticado | GET /auth/me sem senha/hash e sem confiar em id livre |
| Chave segura | variável de ambiente/.env ignorado, sem fallback e exemplo fictício |
| Erros HTTP | 401, 403, 404, 409, 422 e erros genéricos de infraestrutura |
| Validação Pydantic | schemas separados, extras rejeitados no cadastro/login |
| Relatórios preservados | ocupação, categorias e cursos, com permissões administrativas |
| Separação de responsabilidades | controller, model, schema, service, security e database |
| Swagger | OpenAPI com BearerJWT e fluxo visual 401/200/401 observado |
| Código organizado | módulos pequenos, regras de negócio e segurança fora das rotas |

**Limite de método:** os 12 cenários completos foram executados por HTTP real. A operação visual do Swagger cobriu aplicação/remoção de Bearer e /auth/me; não se afirma que os 12 cenários foram repetidos individualmente na interface. A verificação do hash foi feita diretamente no banco temporário, sem criar uma rota que o exponha.

## Conferência da seção 15

1. Código-fonte atualizado: incluído no pacote APS4.
2. requirements.txt: incluído; requirements-dev.txt permite reproduzir testes.
3. README: descrição, instalação/execução, estrutura, chave, rotas, cadastro/tokens, perfis/permissões, JSON e testes documentados.
4. Repositório próprio definido: [Luizgsch/APS-4-Desenvolvimento_backend](https://github.com/Luizgsch/APS-4-Desenvolvimento_backend). A publicação deve ser conferida comparando o commit local e o remoto e verificando README, código e requisitos.

Nenhuma chave real é incluída no pacote ou nos arquivos versionáveis. A publicação não é considerada concluída enquanto não houver verificação do destino e da versão remota.

## Validação do pacote

A validação em ambiente novo está registrada em `docs/evidencias/aps4-etapa9/`. Uma cópia extraída do ZIP recebeu sua própria `.venv`, criada do zero, e instalou requirements-dev.txt. Resultados observados:

- Instalação limpa concluída; `pip check` sem dependências quebradas.
- **112 testes aprovados** na cópia extraída, sem reutilizar a venv original.
- **12 cenários de segurança** e **12 cenários de continuidade** aprovados por HTTP real na cópia, com reinicialização e bancos/chaves temporários.
- Empacotador executado com sucesso na cópia, mesmo sem `.env` real.
- Controles negativos: um arquivo de evidência com chave de teste foi recusado; outro com JWT de teste também foi recusado. Valores não apareceram na saída dos erros. Fixtures removidas após o teste.
- Os comandos de teste não criaram `.env` ou eventos.db na raiz da cópia; só usaram bancos temporários.
- Código e requisitos na cópia mantiveram seus hashes do manifesto. A instalação não exige um banco fornecido nem credenciais predefinidas.
- Auditoria local confirmou ausência da chave real no Git e no ZIP, links locais válidos no README e preservação da APS 3 e de ambos os bancos reais.

Arquivos de evidência: `testes-copia.txt`, `seguranca-copia.txt`, `regressao-copia.txt`, `instalacao-limpa.txt`, `dependencias.txt`, `versoes.txt`, `empacotador-copia.txt`, `validacao.json` e `auditoria-local.json`.

O pacote final é regenerado após inserir as evidências. A comparação dos hashes de código, schemas, configuração de exemplo e dependências garante que a regeneração documental não altera os arquivos executáveis testados.

## Uso do pacote

```powershell
# Na pasta original, para gerar novamente:
.\.venv\Scripts\python.exe scripts\preparar_entrega.py
```

Entregáveis em `output/`: ZIP da APS 4, `.sha256` e `MANIFESTO.json`. Em outra pasta, extraia o ZIP, crie `.venv`, instale os requisitos e gere sua própria chave seguindo o README. O pacote não contém contas nem banco pronto.

## Entrega externa e limites

- Destino autorizado: `Luizgsch/APS-4-Desenvolvimento_backend`, na branch main. O remoto da pasta APS4 passa a apontar somente para esse destino.
- Se for exigida repetição individual de todos os cenários na interface Swagger, esse procedimento ainda não está documentado como executado; as evidências atuais distinguem HTTP automatizado e fluxo visual Bearer.
- APS 3 e bancos existentes devem continuar preservados. A preparação de 18/11 não havia feito commit ou push; a publicação foi autorizada em 19/11.

A seção 15 pede código-fonte, requirements.txt, README e link do repositório atualizado. O repositório contém os três primeiros itens; enviar seu link disponibiliza esse conjunto. O PDF não exige expressamente anexar ZIP separado. Campos ou orientações adicionais da plataforma de entrega devem ser observados pelo aluno.
