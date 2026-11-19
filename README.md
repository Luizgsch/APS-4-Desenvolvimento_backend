# APS 4 - API de Eventos Acadêmicos

[Repositório no GitHub](https://github.com/Luizgsch/APS-4-Desenvolvimento_backend)

Continuação da APS 3: API RESTful com FastAPI, persistência SQLite/SQLAlchemy ORM,
autenticação por e-mail e senha, tokens JWT e controle de acesso por perfis.
Eventos, participantes, inscrições e os três relatórios dinâmicos foram preservados.
Senhas são armazenadas como hash Argon2id, e os dados permanecem no banco após
reiniciar a aplicação. Este projeto é independente da pasta da APS 3.

## Requisitos e instalação

Ambiente de referência: **CPython 3.13.15, Windows x64**. O código requer Python
3.12 ou superior por usar `sqlite3.Connection.autocommit`; outras versões e
sistemas não foram validados. SQLite já acompanha o Python. Dependências diretas
e transitivas estão fixadas em `requirements.txt`; testes usam `requirements-dev.txt`.

Clone o repositório e abra um terminal na raiz, onde fica `main.py`:

```powershell
git clone https://github.com/Luizgsch/APS-4-Desenvolvimento_backend.git
cd APS-4-Desenvolvimento_backend
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Se já baixou ou extraiu o código, abra o terminal nessa pasta e comece pela criação
da `.venv`. Não copie um ambiente virtual de outra pasta. Se já houver `.venv`,
preserve o existente antes de recriá-lo. Os comandos usam o executável diretamente,
sem exigir ativação nem mudança na política do PowerShell.

## Configuração de segurança

Antes de usar o login, crie `.env` na raiz do projeto com uma chave exclusiva.
O comando abaixo gera o arquivo sem imprimir o segredo nem sobrescrever um existente:

```powershell
.\.venv\Scripts\python.exe -c "from pathlib import Path; import secrets; p=Path('.env'); f=p.open('x', encoding='utf-8'); f.write('JWT_SECRET_KEY='+secrets.token_urlsafe(48)+'\nACCESS_TOKEN_EXPIRE_MINUTES=30\n'); f.close()"
```

Como alternativa, copie `.env.example` para `.env` e substitua o valor fictício
por uma chave aleatória de pelo menos 32 bytes. Não use o exemplo como chave real.
Se `.env` já existir, preserve sua configuração.

O algoritmo permitido é **HS256**, fixado no servidor. Tokens duram **30 minutos**
por padrão; `ACCESS_TOKEN_EXPIRE_MINUTES` aceita outro inteiro positivo.
Variáveis do processo têm prioridade sobre `.env`, inclusive quando vazias.
O arquivo é lido pelo caminho do projeto, sem interpolação de valores.

Não há chave padrão de emergência: chave ausente, vazia, curta ou igual ao exemplo
impede a emissão de tokens. Trocar a chave invalida tokens anteriores.
`.env`, suas variantes, `.key` e `.pem` ficam fora do Git; somente `.env.example`
é versionável. Nenhuma chave real acompanha o pacote de código.

## Execução

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- OpenAPI: http://127.0.0.1:8000/openapi.json

Use Ctrl+C para encerrar. No Swagger, expanda a operação, clique em **Try it out**,
preencha os campos e clique em **Execute**. Para operações protegidas, obtenha um
token e aplique a autorização Bearer conforme as instruções abaixo.

## Estrutura e responsabilidades

```text
main.py                        aplicação, lifespan, routers e handlers de falhas
database.py                    engine, Base, fábrica e sessões SQLite
controller/                    rotas e códigos HTTP
model/                         Evento, Participante, Inscricao e Usuario
schema/                        entradas e respostas Pydantic
service/                       regras, transações, cadastro, login e agregações
security/                      configuração, hash, JWT e dependências de acesso
tests/                         testes com bancos e chaves temporários
scripts/criar_administrador.py  criação controlada de administrador local
scripts/validar_seguranca.py    12 cenários de segurança da APS 4 por HTTP
scripts/validar_cenarios.py     12 cenários de continuidade da APS 3 por HTTP
scripts/demonstrar_swagger.py   servidor descartável para teste visual
scripts/preparar_entrega.py     pacote ZIP e manifesto de arquivos
docs/                          registros das etapas e evidências
requirements.txt               dependências de execução fixadas
requirements-dev.txt           dependências de testes fixadas
.env.example                   exemplo de configuração sem segredo real
```

O `lifespan` importa os modelos e cria tabelas ausentes por `Base.metadata.create_all()`.
Os controllers recebem a sessão de negócio por `Depends(get_db)`. Os serviços
confirmam operações com commit; falhas provocam rollback e as sessões são fechadas.
O pool é liberado no encerramento. Não há armazenamento em listas.

Hash e JWT ficam em `security/`, separados das rotas. A autenticação consulta a
identidade em uma sessão curta, encerrada antes da transação de negócio para não
manter uma leitura SQLite aberta antes dos bloqueios de escrita.

## Banco, entidades e integridade

`eventos.db` é criado automaticamente **na raiz deste projeto**, com caminho
absoluto derivado de `database.py`, independentemente do diretório do terminal.
O banco e seus arquivos auxiliares não fazem parte do ZIP nem do Git.

| Tabela | Campos |
| --- | --- |
| eventos | id, titulo, descricao, data, horario, local, capacidade, categoria |
| participantes | id, nome, email, curso |
| inscricoes | id, evento_id, participante_id, data_inscricao |
| usuarios | id, nome, email, senha_hash, perfil |

Evento e Participante possuem relações de um para muitos com Inscricao. As chaves
estrangeiras são obrigatórias e verificadas em cada conexão SQLite. Excluir um
evento ou participante remove suas inscrições em cascata, preservando a outra
entidade. Excluir um participante libera suas vagas.

Usuário e Participante são entidades independentes. Não existe vínculo automático
por id ou e-mail. O token identifica o usuário autenticado; o identificador de
participante na inscrição seleciona a entidade de negócio.

O banco impede e-mails repetidos em cada recurso, inscrições repetidas para o
mesmo par, capacidade não positiva e perfis diferentes de `usuario` e `administrador`.
E-mails de usuário são normalizados para minúsculas; a comparação NOCASE do SQLite
sem distinção de caixa é limitada a ASCII. Não há normalização adicional de
categorias ou cursos. Pydantic valida e-mails, datas, horários e campos obrigatórios.
Textos de eventos e participantes são aparados e não podem ficar vazios.

IDs são gerados na inserção. `data_inscricao` usa a data local do servidor, gerada
pelo ORM. PUT exige todos os campos de cadastro e mantém o ID original. O cliente
não escolhe ID nem data da inscrição.

Inscrições verificam evento, participante, duplicidade e vagas, nessa ordem.
O PUT de evento rejeita capacidade menor que a quantidade de inscritos. Um bloqueio
de escrita SQLite obtido antes da leitura serializa inscrições e alterações de
capacidade, protegendo a última vaga. Bloqueios prolongados podem causar erro 500.
Escritas arbitrárias fora da API não são cobertas pela regra de vagas dos serviços.

`create_all()` cria tabelas ausentes, mas não migra estruturas antigas. Alembic não
é utilizado. Não remova `eventos.db` se precisar preservar registros. Para backup
simples, encerre a aplicação antes de copiar o banco e guarde a cópia fora do pacote.

## Cadastro, login e autenticação

O cadastro público `POST /usuarios` recebe nome, email e senha. Retorna **201** com
id, nome, email e perfil `usuario`, sem senha ou hash. Campos extras como perfil,
id e senha_hash são rejeitados com 422; o primeiro cadastro não vira administrador.

Nome deve ter de 1 a 120 caracteres após remover espaços externos. E-mail deve ser
válido e único. Senha deve ter **8 a 128 caracteres** e não pode conter somente
espaços. Espaços de uma senha válida são preservados. Esses limites são decisões
da equipe; o PDF exige critérios definidos, sem estabelecer um comprimento exato.

`pwdlib` gera e verifica o hash Argon2id, com salt aleatório. Somente o hash é
persistido. `POST /auth/login` recebe JSON com email e senha; login válido retorna
access_token e token_type `bearer`. E-mail inexistente e senha incorreta retornam
o mesmo 401, sem indicar qual credencial falhou.

O JWT contém apenas `sub` (id textual do usuário), `iat` e `exp` em UTC. PyJWT valida
assinatura, algoritmo permitido e expiração. Claims obrigatórias, datas inteiras e
id positivo também são conferidos. Tokens adulterados, expirados, sem assinatura
ou com algoritmo diferente são rejeitados. Senha, hash e perfil não são incluídos.
Não há renovação de tokens, recuperação de senha ou login externo, dispensados pelo PDF.

Rotas protegidas recebem `Authorization: Bearer SEU_ACCESS_TOKEN`.
`GET /auth/me` retorna os dados públicos do usuário identificado pelo token.
Parâmetros como usuario_id não selecionam a identidade. O usuário e o perfil atual
são consultados no banco em cada requisição; tokens de usuários removidos são
recusados. Claims extras, corpo, query e cabeçalhos livres não concedem privilégios.

### Administrador inicial

Execute no terminal local, na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe scripts\criar_administrador.py
```

O comando mostra o banco de destino e solicita nome, e-mail, senha oculta e
confirmação. Usa as mesmas validações e o serviço de hash do cadastro público.
Se o terminal não permitir ocultar a senha, cancela a operação. Não recebe senha
por argumento ou variável de ambiente e não contém senha administrativa fixa.

Cria uma nova conta com perfil `administrador`; e-mail existente é recusado, sem
promover a conta ou trocar sua senha. Não há endpoint de promoção. O acesso ao
terminal e ao SQLite deve ficar com quem administra a instalação. Nenhuma conta
real é criada automaticamente nos testes ou fornecida com o projeto.

### Bearer no Swagger

1. Cadastre um usuário ou crie o administrador pelo comando local.
2. Execute `POST /auth/login` com JSON e copie o valor de access_token.
3. Clique em **Authorize**, esquema **BearerJWT**, e cole somente o token, sem o prefixo Bearer.
4. Aplique a credencial, feche a janela e execute `/auth/me` ou outra rota com cadeado.
5. Use **Remove authorization/Logout** e repita a operação para verificar o retorno 401.

## Perfis e permissões

O administrador pode gerenciar eventos e participantes, consultar inscritos e
relatórios e realizar inscrições. O usuário comum pode consultar eventos,
participantes e inscritos, realizar inscrições e consultar suas próprias
informações em `/auth/me`. As permissões são verificadas no servidor pelo perfil
atual do banco, inclusive quando o token foi emitido antes de uma mudança de perfil.

As regras mínimas do PDF restringem alterações de eventos aos administradores e
permitem inscrições por autenticados. As decisões adicionais da equipe são:

- Eventos permanecem com consulta pública.
- Participantes e inscritos exigem autenticação; ambos os perfis podem consultar
  nome, e-mail e curso de todos os participantes cadastrados.
- Cadastro, atualização e exclusão de participantes ficam com administradores.
- Relatórios consolidados ficam com administradores.

Como usuário e participante são independentes, autenticados podem inscrever
qualquer participante já cadastrado, conforme essa política acadêmica. Não se
presume que o participante selecionado seja o titular do token.

## Rotas e respostas

| Método | Rota | Acesso | Sucesso |
| --- | --- | --- | --- |
| GET | / | Público | 200, mensagem de funcionamento |
| POST | /usuarios | Público | 201, usuário comum criado |
| POST | /auth/login | Público | 200, token de acesso |
| GET | /auth/me | Autenticado | 200, dados do próprio usuário |
| POST | /eventos | Administrador | 201, evento criado |
| GET | /eventos | Público | 200, lista ordenada por ID |
| GET | /eventos/{id} | Público | 200, evento |
| PUT | /eventos/{id} | Administrador | 200, evento atualizado |
| DELETE | /eventos/{id} | Administrador | 204, sem corpo |
| POST | /participantes | Administrador | 201, participante criado |
| GET | /participantes | Autenticado | 200, lista ordenada por ID |
| GET | /participantes/{id} | Autenticado | 200, participante |
| PUT | /participantes/{id} | Administrador | 200, participante atualizado |
| DELETE | /participantes/{id} | Administrador | 204, sem corpo |
| POST | /eventos/{evento_id}/inscricoes/{participante_id} | Autenticado | 201, inscrição com ID e data |
| GET | /eventos/{evento_id}/inscricoes | Autenticado | 200, participantes na ordem das inscrições |
| GET | /relatorios/eventos/ocupacao | Administrador | 200, ocupação por evento |
| GET | /relatorios/eventos/categorias | Administrador | 200, totais por categoria |
| GET | /relatorios/participantes/cursos | Administrador | 200, totais por curso |

Autenticado significa usuário comum ou administrador com token válido. `/docs` e
`/openapi.json` são públicos. Listagens sem registros retornam `[]`. Use caminhos
sem barra final; `/eventos/` continua funcionando por redirecionamento HTTP 307.

Erros usam `{"detail": ...}`: **401** para credenciais inválidas, token ausente,
inválido, expirado ou de usuário inexistente; **403** para autenticado sem permissão;
**404** para entidade inexistente; **409** para e-mail repetido, inscrição duplicada,
falta de vagas ou redução indevida de capacidade; **422** para entrada inválida;
**500** para falhas de persistência; **503** para configuração de autenticação inválida.
Mensagens não incluem senha, hash, SQL ou parâmetros internos. No cadastro e no
login, erros de validação usam uma mensagem fixa, sem repetir o corpo enviado.

## Exemplo de uso

No Swagger, envie `POST /usuarios`:

```json
{
  "nome": "Aluno Exemplo",
  "email": "aluno@example.com",
  "senha": "Minha senha de exemplo 123"
}
```

Exemplo de resposta, com ID definido pela execução:

```json
{"id": 1, "nome": "Aluno Exemplo", "email": "aluno@example.com", "perfil": "usuario"}
```

Depois envie `POST /auth/login` com as mesmas credenciais:

```json
{"email": "aluno@example.com", "senha": "Minha senha de exemplo 123"}
```

A resposta contém o token que deve ser aplicado em **Authorize**:

```json
{"access_token": "JWT_RETORNADO_PELA_API", "token_type": "bearer"}
```

`GET /auth/me` retorna id, nome, email e perfil, sem senha ou hash. Para cadastrar
eventos e participantes, faça login com a conta administrativa criada pelo comando
local e aplique esse token. Envie `POST /eventos`:

```json
{
  "titulo": "Workshop de Python",
  "descricao": "Introdução ao desenvolvimento com Python",
  "data": "2026-12-01",
  "horario": "19:00",
  "local": "Auditório",
  "capacidade": 2,
  "categoria": "Workshop"
}
```

Ainda como administrador, envie `POST /participantes`:

```json
{"nome": "Participante de exemplo", "email": "participante@example.com", "curso": "Computacao"}
```

Use os IDs retornados em `POST /eventos/{evento_id}/inscricoes/{participante_id}`,
sem corpo JSON, com token de qualquer perfil autenticado. Exemplo de resposta
(ID e data dependem da execução):

```json
{"evento_id": 1, "participante_id": 1, "id": 1, "data_inscricao": "2026-11-19"}
```

Consulte `GET /eventos/1/inscricoes` usando o ID real. Repetir a inscrição retorna
409 com `{"detail": "Participante já está inscrito neste evento."}`.

## Relatórios dinâmicos

As três rotas exigem administrador e retornam JSON calculado no SQLite via
SQLAlchemy: uma consulta da identidade e uma consulta consolidada por relatório,
sem listas de resultados fixas e sem cache dos totais.

- **Ocupação:** evento_id, titulo, capacidade, total_inscritos, vagas_disponiveis
  e percentual_ocupacao. Inclui eventos sem inscrições; ordena por ID. Percentual
  igual a `inscritos * 100 / capacidade`, arredondado para duas casas e protegido
  contra divisão por zero.
- **Categorias:** categoria, total_eventos, capacidade_total e total_inscricoes.
  Agrega inscrições antes do join para somar cada capacidade uma vez, inclusive
  quando dois eventos têm capacidade igual. Inclui categorias sem inscrições.
- **Cursos:** curso, total_participantes e total_inscricoes. Conta participantes
  distintos, mesmo com várias inscrições, e inclui participantes sem inscrições.
  Categorias e cursos são ordenados pelo texto cadastrado.

No exemplo anterior, com um evento de capacidade 2 e uma inscrição, a ocupação é:

```json
[{"evento_id": 1, "titulo": "Workshop de Python", "capacidade": 2, "total_inscritos": 1, "vagas_disponiveis": 1, "percentual_ocupacao": 50.0}]
```

Nesse mesmo exemplo, categorias e cursos retornam, respectivamente:

```json
[{"categoria": "Workshop", "total_eventos": 1, "capacidade_total": 2, "total_inscricoes": 1}]
```

```json
[{"curso": "Computacao", "total_participantes": 1, "total_inscricoes": 1}]
```

Alterar capacidade/categoria/curso, criar inscrição ou excluir registros atualiza
as próximas consultas. Se não houver registros da entidade principal, retorna `[]`.

## Testes e evidências

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 scripts\validar_seguranca.py
.\.venv\Scripts\python.exe -X utf8 scripts\validar_cenarios.py
```

A suíte possui **112 testes**: infraestrutura, modelos, schemas, CRUD, falhas de
persistência, concorrência, relatórios, cadastro/hash, administrador, login/JWT,
Bearer e autorização. Usa bancos e chaves temporários, preservando os dados reais.
O transporte é httpx2, compatível com o TestClient instalado.

`validar_seguranca.py` demonstra os **12 cenários da APS 4** por HTTP real, incluindo
token inválido e expirado separadamente. Registra 41 requisições em
`docs/evidencias/aps4-etapa8/cenarios-seguranca.json`, ocultando senhas, hashes e tokens.
`validar_cenarios.py` mantém os **12 cenários de continuidade da APS 3**, com
55 requisições em `docs/evidencias/aps4-regressao.json`. Ambos reiniciam o servidor
com o mesmo banco temporário para conferir persistência. Uma nova execução
substitui a evidência correspondente. A auditoria direta do SQLite ocorre somente
nos testes; a aplicação usa ORM.

Veja a matriz e os resultados em [docs/APS4-ETAPA-8.md](docs/APS4-ETAPA-8.md).
O fluxo Bearer foi operado visualmente no Swagger: 401 sem token, 200 após
autorizar e 401 após remover a autorização. Os 12 cenários completos foram
executados por HTTP, não individualmente pela interface Swagger.

Para repetir o fluxo visual sem usar o banco real:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\demonstrar_swagger.py
```

Abra a URL exibida e use as credenciais descartáveis de
`tmp/aps4-swagger/sessao.json`, ignorado pelo Git. Ao terminar, em outro terminal:

```powershell
New-Item -ItemType File -Force tmp/aps4-swagger/parar
```

O servidor encerra, o banco temporário é removido e o arquivo de credenciais é
apagado. Não copie essas fixtures para `.env` nem use esse ambiente para dados reais.

## Pacote de entrega

```powershell
.\.venv\Scripts\python.exe scripts\preparar_entrega.py
```

Gera `output/APS-4-Desenvolvimento-backend.zip`, manifesto com SHA-256 por arquivo
e checksum do pacote. Inclui código, security, `.env.example`, documentação e
evidências APS4, testes e dependências. Exclui ambientes virtuais, Git, bancos,
caches, temporários, `.env` real e históricos da APS 3. O empacotador recusa a
chave local e possíveis tokens JWT antes de gerar o ZIP.

Extraia em outra pasta, crie uma nova `.venv` e siga a instalação. O manifesto
permite conferir os arquivos. A cópia extraída foi validada em ambiente criado
do zero, com os 112 testes e os dois conjuntos de 12 cenários aprovados.

O repositório desta entrega é
[Luizgsch/APS-4-Desenvolvimento_backend](https://github.com/Luizgsch/APS-4-Desenvolvimento_backend).
A APS 3 permanece em sua pasta e repositório separados. Os registros
`docs/APS4-ETAPA-1.md` a `docs/APS4-ETAPA-9.md` descrevem a evolução desta versão;
os históricos `docs/ETAPA-*.md` pertencem à APS 3 e não integram o ZIP APS4.

O GitHub hospeda o código e este README. Uma URL de API em execução depende de
um serviço de hospedagem Python com armazenamento persistente para `eventos.db`;
GitHub Pages não executa esta API FastAPI.
