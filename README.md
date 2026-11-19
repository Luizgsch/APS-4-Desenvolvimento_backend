# APS 4 - API de Eventos Acadêmicos

## Estado da APS 4

Cadastro com Argon2, criação local de administrador, login JWT,
autenticação Bearer, /auth/me e autorização por perfil implementados.
A base funcional da APS 3 está preservada. Testes consolidados e Bearer no Swagger
verificados; documentação e pacote locais preparados na etapa 9.

Repositório da entrega: [Luizgsch/APS-4-Desenvolvimento_backend](https://github.com/Luizgsch/APS-4-Desenvolvimento_backend).
Destino local: `D:\Projetos\APS-4-Desenvolvimento-backend`.
Consulte [o diagnóstico](docs/APS4-ETAPA-1.md) e
[a configuração de segurança](docs/APS4-ETAPA-2.md).
O cadastro está descrito no [relatório da etapa 3](docs/APS4-ETAPA-3.md).
O procedimento administrativo está no [relatório da etapa 4](docs/APS4-ETAPA-4.md).
O login e os tokens estão no [relatório da etapa 5](docs/APS4-ETAPA-5.md).
A proteção das rotas está no [relatório da etapa 6](docs/APS4-ETAPA-6.md).
As permissões estão no [relatório da etapa 7](docs/APS4-ETAPA-7.md).
Os testes consolidados estão no [relatório da etapa 8](docs/APS4-ETAPA-8.md).
A conferência da entrega está no [relatório da etapa 9](docs/APS4-ETAPA-9.md).
Os registros `docs/ETAPA-*.md` e as evidências anteriores são históricos da APS 3.

## Requisitos e instalação

Ambiente de referência: **CPython 3.13.15, Windows x64**. O código requer Python
3.12 ou superior por usar `sqlite3.Connection.autocommit`; outras versões e
sistemas não foram validados. SQLite já acompanha o Python. Dependências diretas
e transitivas estão fixadas em `requirements.txt`; testes usam `requirements-dev.txt`.

Extraia o ZIP ou baixe o código e abra um terminal na raiz, onde fica `main.py`:

```powershell
# Abra o terminal na pasta onde extraiu o pacote, contendo main.py.
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Não copie um ambiente virtual de outra pasta. Se já houver `.venv`, use um
ambiente novo ou preserve o existente antes de recriá-lo. Os comandos usam o
executável diretamente, sem exigir ativação nem mudança na política do PowerShell.

## Configuração de segurança (etapa 2)

Instale as dependências por `requirements.txt` ou, para testes, `requirements-dev.txt`.
`security/config.py` define o algoritmo permitido **HS256**, fixado no servidor,
e a duração padrão de **30 minutos** para tokens.

A configuração local usa `.env` na raiz. A preparação criou esse arquivo somente
se ausente, sem exibir a chave. Em outra instalação, gere o arquivo sem sobrescrever
uma configuração existente nem imprimir o segredo:

```powershell
.\.venv\Scripts\python.exe -c "from pathlib import Path; import secrets; p=Path('.env'); f=p.open('x', encoding='utf-8'); f.write('JWT_SECRET_KEY='+secrets.token_urlsafe(48)+'\nACCESS_TOKEN_EXPIRE_MINUTES=30\n'); f.close()"
```

Como alternativa, copie `.env.example` para `.env` e substitua o valor fictício
por uma chave aleatória exclusiva de pelo menos 32 bytes. Não use o exemplo como chave.
`JWT_SECRET_KEY` e `ACCESS_TOKEN_EXPIRE_MINUTES` também podem vir das variáveis
do processo. Essas variáveis têm prioridade sobre `.env`, inclusive se vazias.
A duração deve ser um inteiro positivo. A chave é obrigatória, sem valor padrão;
ausência, chave vazia, curta ou igual ao exemplo provocam erro.

A leitura usa o caminho do projeto e não interpola variáveis no arquivo.
`.env`, suas variantes, arquivos `.key` e `.pem` são ignorados pelo Git;
somente `.env.example`, sem segredo real, é versionável. Não compartilhe a chave.
Trocar a chave invalida tokens assinados com a chave anterior.

O serviço JWT chama `load_security_settings()` na emissão e na validação.
As bibliotecas são `pwdlib[argon2]`, `PyJWT` e `python-dotenv`.
Configuração inválida impede a emissão; não há chave padrão de emergência.

## Execução

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- OpenAPI: http://127.0.0.1:8000/openapi.json

Use Ctrl+C para encerrar. No Swagger, expanda a operação, clique em **Try it out**,
preencha os campos e clique em **Execute**. Guarde os IDs retornados para consultar,
alterar, excluir ou inscrever participantes.

## Cadastro público de usuários (etapa 3)

`POST /usuarios` recebe JSON e retorna **201**, com `id`, `nome`, `email` e
`perfil`. Todo cadastro público recebe `perfil: "usuario"`.

```json
{
  "nome": "Aluno Exemplo",
  "email": "aluno@example.com",
  "senha": "Minha senha de exemplo 123"
}
```

Nome: de 1 a 120 caracteres após remover espaços externos. E-mail válido,
normalizado para minúsculas e único na tabela de usuários, inclusive no banco.
Senha: de 8 a 128 caracteres, sem aceitar somente espaços. Espaços da senha
são preservados. Esses limites são decisões da equipe; o PDF exige critérios
mínimos definidos e documentados, sem determinar um comprimento específico.

São aceitos somente `nome`, `email` e `senha`. Qualquer campo extra, incluindo
`perfil`, `id` e `senha_hash`, retorna **422**. Dados ausentes, inválidos ou JSON
malformado também retornam **422**, com mensagem fixa, sem repetir valores enviados.
E-mail duplicado retorna **409**. Falhas de banco retornam mensagem genérica **500**.
Nenhuma dessas respostas devolve senha ou hash.

O banco recebe somente o hash Argon2id gerado pelo `pwdlib`, com salt aleatório.
`security/passwords.py` centraliza geração e verificação pela biblioteca.
`model/usuario.py`, `schema/usuario_schema.py`, `service/usuario_service.py` e
`controller/usuario_controller.py` separam persistência, validação, regras e HTTP.
Usuário e participante são entidades independentes; o cadastro não cria participante.
A tabela `usuarios` é criada por `create_all()` ao iniciar a API, sem apagar as demais.

Para testar, inicie a API e use `POST /usuarios` em `/docs`, ou envie o JSON acima
por um cliente HTTP. Os testes automatizados usam bancos temporários; o fluxo
Bearer também foi verificado visualmente no Swagger. O login é descrito abaixo.

## Criação controlada de administrador (etapa 4)

Quem administra a instalação, com acesso ao terminal e ao banco local, pode criar
uma nova conta administrativa. Esse acesso local é a fronteira de confiança do
procedimento; ele não deve ser disponibilizado por uma rota HTTP.

Na raiz da APS 4, execute:

```powershell
.\.venv\Scripts\python.exe scripts\criar_administrador.py
```

O comando mostra o caminho do banco de destino e solicita nome, e-mail, senha e
confirmação. A senha não aparece durante a digitação; use um terminal interativo.
Se o terminal não permitir ocultá-la, o comando cancela o procedimento. Não há
opção de senha por argumento, variável de ambiente ou valor fixo no código.
Para consultar a ajuda: `python scripts/criar_administrador.py --help` usando
o Python da `.venv`.

As validações são as mesmas do cadastro: nome de 1 a 120 caracteres, e-mail válido
e senha de 8 a 128 caracteres, não composta somente por espaços. A confirmação
deve coincidir exatamente. O serviço reutiliza o hash Argon2 de `security/passwords.py`.

O comando cria as tabelas ausentes sem apagar as existentes e grava uma nova conta
com perfil `administrador`. E-mail já cadastrado é recusado, inclusive em variações
de maiúsculas: o comando não promove, não troca senha e não altera contas existentes.
Escolha outro e-mail caso já exista uma conta comum com o endereço desejado.
O cadastro público continua criando somente `usuario`, inclusive o primeiro cadastro.
Não há endpoint de promoção e o banco aceita apenas `usuario` ou `administrador`.

Após gravar, o comando confirma id, e-mail e perfil, sem senha ou hash.
Códigos de saída: `0` sucesso/ajuda, `1` conflito ou falha de banco, `2` dados
inválidos ou terminal inadequado, `130` cancelamento antes da gravação.
Os testes usam somente credenciais e bancos temporários; nenhuma conta
administrativa real foi criada automaticamente na preparação desta etapa.
O login e as regras de autorização são descritos abaixo.

## Login e JWT (etapa 5)

Com `.env` configurado e a API iniciada, use `POST /auth/login`, com JSON:

```json
{
  "email": "aluno@example.com",
  "senha": "Minha senha de exemplo 123"
}
```

Use as credenciais de uma conta previamente cadastrada. O login retorna **200**:

```json
{
  "access_token": "JWT_ASSINADO_RETORNADO_PELA_API",
  "token_type": "bearer"
}
```

E-mail inexistente e senha incorreta retornam o mesmo **401**, com
`{"detail": "E-mail ou senha inválidos."}`. E-mail inválido, campos ausentes,
campos extras e JSON malformado retornam **422**, sem repetir os dados enviados.
Senha vazia ou incorreta, dentro de um corpo válido, retorna 401. O limite de
128 caracteres também se aplica ao login. Espaços da senha são preservados.
Erros de banco retornam 500 genérico; configuração JWT inválida retorna 503
genérico, sem token nem segredo. A resposta com token usa `Cache-Control: no-store`.

O JWT contém somente `sub` (id do usuário como texto), `iat` (emissão UTC) e
`exp` (expiração UTC). Não contém senha, hash ou perfil. O algoritmo permitido
é HS256 e a duração vem da configuração, com padrão de 30 minutos.
`security/tokens.py` centraliza emissão e validação por PyJWT: assinatura,
algoritmo fixado no servidor, claims obrigatórias, datas e id inteiro positivo.
Tokens expirados, adulterados, sem assinatura ou com outro algoritmo são rejeitados.

`security/dependencies.py` integra `validar_token()` às rotas protegidas e consulta
o usuário no banco em cada requisição. Não há renovação, recuperação de senha
nem login externo.

## Autenticação e usuário atual (etapa 6)

Envie `Authorization: Bearer SEU_ACCESS_TOKEN` nas rotas protegidas.
`GET /auth/me` retorna somente id, nome, e-mail e perfil do usuário identificado
pelo token validado. Parâmetros como `usuario_id` enviados pelo cliente não
selecionam a identidade. Nome e perfil vêm do banco, não de claims adicionais.
Token de usuário inexistente ou excluído é recusado.

| Rotas | Acesso atual, após etapa 7 |
| --- | --- |
| POST /usuarios e POST /auth/login | Público |
| GET /, /docs e /openapi.json | Público |
| GET /eventos e GET /eventos/{id} | Público |
| GET /participantes e GET /participantes/{id} | Usuário ou administrador autenticado |
| GET /eventos/{evento_id}/inscricoes | Usuário ou administrador autenticado |
| POST /eventos, PUT e DELETE /eventos/{id} | Somente administrador |
| POST /participantes, PUT e DELETE /participantes/{id} | Somente administrador |
| POST /eventos/{evento_id}/inscricoes/{participante_id} | Usuário autenticado |
| GET /relatorios/eventos/ocupacao, /relatorios/eventos/categorias e /relatorios/participantes/cursos | Somente administrador |
| GET /auth/me | Usuário autenticado |

Token ausente, inválido, adulterado, expirado ou de usuário inexistente retorna
**401**, com mensagem genérica e cabeçalho `WWW-Authenticate: Bearer`.
Problemas de configuração retornam 503; falhas de banco retornam 500 genérico.
A autenticação fica centralizada em `get_usuario_atual()`. A consulta da identidade
usa uma sessão curta, encerrada antes da transação de negócio; isso evita manter
uma leitura SQLite aberta antes das operações de escrita.

No Swagger (`/docs`):

1. Cadastre uma conta por `POST /usuarios`, ou use uma conta existente.
2. Execute `POST /auth/login` com JSON e copie apenas o valor de `access_token`.
3. Clique em **Authorize**, selecione **BearerJWT** e cole somente o token, sem
   escrever `Bearer` antes. O Swagger adiciona o prefixo no cabeçalho.
4. Execute `GET /auth/me` e as operações com cadeado. Use **Remove authorization/Logout** para remover
   o token do Swagger e verificar o retorno 401 nas rotas protegidas.

O esquema HTTP Bearer e os requisitos das operações são verificados no OpenAPI.
Na etapa 8, o Swagger foi operado no navegador: /auth/me retornou 401 sem token,
200 após Authorize e 401 após remover a autorização. O token usado era descartável.

## Autorização por perfil (etapa 7)

`get_administrador()` reutiliza a identidade consultada no banco. Somente o
perfil atual `administrador` pode criar, alterar ou excluir eventos. Usuário
autenticado sem permissão recebe **403**, com mensagem genérica; token ausente
ou inválido continua recebendo **401**. Claims, query, corpo e cabeçalhos livres
informando `perfil=administrador` não concedem privilégios. Alterações de perfil
no banco são consideradas na próxima requisição, sem exigir novo login.

O PDF exige restrição administrativa de eventos, inscrições por autenticados,
consulta de eventos e acesso do administrador aos participantes, inscritos e
relatórios. As regras adicionais escolhidas pela equipe são:

- Participantes e listas de inscritos exigem autenticação; usuários comuns e
  administradores podem consultar todos os participantes cadastrados, incluindo
  nome, e-mail e curso. Esses dados não são públicos para visitantes anônimos.
- Cadastro, alteração e exclusão de participantes ficam com administradores.
- Relatórios consolidados ficam com administradores.
- Consultas de eventos continuam públicas; `/auth/me` mostra somente o próprio usuário.

Usuário e participante são entidades independentes. Não há associação por id
ou e-mail nem uma regra de "participante próprio". A inscrição é uma operação
autenticada para um participante já cadastrado, identificado na rota. Usuário
comum pode inscrever qualquer participante cadastrado, conforme essa política
acadêmica; o administrador mantém o cadastro dos participantes. Nenhum vínculo
novo foi criado para presumir que o titular do token é o participante inscrito.
Duplicidade, capacidade, integridade e cascatas permanecem em vigor.

O script de regressão cria um administrador apenas no banco temporário pelo
mesmo serviço local da etapa 4; não usa cadastro público para obter privilégios.
Não há endpoint de promoção de perfil.

## Testes consolidados da APS 4 (etapa 8)

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 scripts\validar_seguranca.py
.\.venv\Scripts\python.exe -X utf8 scripts\validar_cenarios.py
```

A suíte tem 112 testes. `validar_seguranca.py` demonstra os 12 cenários da seção 13
por HTTP real, incluindo tokens inválidos e expirados, hash, 401/403, administrador,
identidade, persistência após reiniciar e continuidade dos relatórios. As evidências
ocultam senhas, hashes e tokens e ficam em `docs/evidencias/aps4-etapa8/`.
`validar_cenarios.py` mantém os 12 cenários de negócio da APS 3 e salva, por padrão,
`docs/evidencias/aps4-regressao.json`. Ambos utilizam bancos e chaves temporários.

Para repetir a demonstração visual sem utilizar dados reais:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\demonstrar_swagger.py
```

Abra a URL local exibida. O arquivo `tmp/aps4-swagger/sessao.json`, ignorado pelo
Git, contém credenciais e token exclusivamente descartáveis dessa demonstração.
Use esse token em Authorize e teste /auth/me; remova a autorização e confira 401.
Para encerrar pelo outro terminal, crie `tmp/aps4-swagger/parar`; o servidor fecha,
o banco temporário é removido e o arquivo com credenciais é apagado.
Não use esse ambiente para armazenar dados reais nem copie suas fixtures para `.env`.

## Base herdada da APS 3

Continuação da APS 2: API RESTful com FastAPI, persistência SQLite/SQLAlchemy ORM
e três relatórios dinâmicos. Eventos, participantes e inscrições permanecem no
banco após reiniciar a aplicação. A evolução ocorre na pasta da APS 4;
as pastas da APS 2 e da APS 3 são preservadas.

## Estrutura e responsabilidades

```text
main.py                       aplicação, lifespan, routers e handler de falhas
database.py                   engine, Base, fábrica e dependência de sessões
controller/                   rotas e códigos HTTP
model/                        Evento, Participante, Inscricao e Usuario do SQLAlchemy
schema/                       entradas e respostas Pydantic
service/                      regras, transações, CRUD e agregações
security/                     hash, configuração, JWT e dependências de acesso
tests/                        testes com bancos temporários
scripts/validar_cenarios.py    12 cenários por HTTP com reinicialização real
scripts/validar_seguranca.py   12 cenários da APS 4, com credenciais ocultadas
scripts/criar_administrador.py procedimento administrativo local
scripts/demonstrar_swagger.py  servidor descartável para teste visual
scripts/preparar_entrega.py    pacote ZIP e manifesto de arquivos
docs/                         registros das etapas e evidências
requirements.txt              dependências de execução fixadas
requirements-dev.txt          dependências de testes fixadas
.env.example                  exemplo público sem segredo real
```

O `lifespan` importa os modelos e cria as tabelas por `Base.metadata.create_all()`.
Os controllers recebem uma sessão por requisição usando `Depends(get_db)`.
Os serviços confirmam operações com commit; exceções provocam rollback e a sessão
sempre é fechada. O pool é liberado no encerramento. Não há armazenamento em listas.

## Banco, entidades e integridade

`eventos.db` é criado automaticamente **na raiz deste projeto**, com caminho
absoluto derivado de `database.py`, independentemente do diretório do terminal.
O banco e seus arquivos auxiliares não fazem parte do ZIP nem do Git.

| Tabela | Campos |
|---|---|
| eventos | id, titulo, descricao, data, horario, local, capacidade, categoria |
| participantes | id, nome, email, curso |
| inscricoes | id, evento_id, participante_id, data_inscricao |
| usuarios | id, nome, email, senha_hash, perfil |

Evento e Participante possuem relações de um para muitos com Inscricao. As duas
chaves estrangeiras são obrigatórias e verificadas em cada conexão SQLite.
Excluir um evento ou participante remove suas inscrições em cascata, preservando
a outra entidade. Excluir um participante libera suas vagas.

O banco impede e-mails repetidos, inscrições repetidas para o mesmo par e
capacidade não positiva e perfis diferentes de usuario/administrador. E-mails usam NOCASE do SQLite, cuja comparação sem
distinção de caixa é limitada a ASCII. Não há normalização adicional de categorias
ou cursos. Pydantic valida e-mail, datas, horários, capacidade positiva e campos
obrigatórios; textos são aparados e não podem ficar vazios.

IDs são gerados na inserção. `data_inscricao` usa a data local do servidor,
gerada pelo ORM. PUT exige todos os campos de cadastro e mantém o ID original.
O cliente não escolhe ID nem data da inscrição.

Inscrições verificam evento, participante, duplicidade e vagas, nessa ordem.
O PUT de evento rejeita capacidade menor que a quantidade de inscritos.
Um bloqueio de escrita SQLite obtido antes da leitura serializa inscrições e
alterações de capacidade na mesma transação, protegendo a última vaga. Bloqueios
prolongados podem causar erro de acesso 500. A regra de vagas depende dos serviços;
escritas arbitrárias feitas fora da API não são cobertas por essa regra.

`create_all()` cria tabelas ausentes, mas não migra estruturas antigas. Alembic
não é utilizado. Não remova `eventos.db` se precisar preservar registros. Para
backup simples, encerre a aplicação antes de copiar o banco e guarde a cópia
fora do pacote de código.

## Rotas e respostas

| Método | Rota | Sucesso |
|---|---|---|
| GET | / | 200, mensagem de funcionamento |
| POST | /eventos | 201, evento criado |
| GET | /eventos | 200, lista ordenada por ID |
| GET | /eventos/{id} | 200, evento |
| PUT | /eventos/{id} | 200, evento atualizado |
| DELETE | /eventos/{id} | 204, sem corpo |
| POST | /participantes | 201, participante criado |
| GET | /participantes | 200, lista ordenada por ID |
| GET | /participantes/{id} | 200, participante |
| PUT | /participantes/{id} | 200, participante atualizado |
| DELETE | /participantes/{id} | 204, sem corpo |
| POST | /eventos/{evento_id}/inscricoes/{participante_id} | 201, inscrição com ID e data |
| GET | /eventos/{evento_id}/inscricoes | 200, participantes na ordem das inscrições |
| GET | /relatorios/eventos/ocupacao | 200, ocupação por evento |
| GET | /relatorios/eventos/categorias | 200, totais por categoria |
| GET | /relatorios/participantes/cursos | 200, totais por curso |

Listagens sem registros retornam `[]`. Use os caminhos sem barra final;
`/eventos/` continua funcionando por redirecionamento HTTP 307.

Erros usam `{"detail": ...}`: 401 para credenciais ausentes ou inválidas; 403 para
autenticado sem permissão; 404 para entidade inexistente; 409 para e-mail
repetido, inscrição duplicada, falta de vagas ou redução indevida de capacidade;
422 para entrada inválida; 500 para falhas de persistência, sem SQL ou caminhos
internos na resposta; 503 para configuração de autenticação inválida.
Manter o próprio e-mail em uma atualização de participante é permitido.

## Exemplo de uso

No Swagger, faça login como administrador, aplique o Bearer e envie `POST /eventos`:

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
{"evento_id": 1, "participante_id": 1, "id": 1, "data_inscricao": "2026-11-17"}
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
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 scripts\validar_cenarios.py
```

A suíte possui 112 testes: infraestrutura, modelos, schemas, CRUD, falhas de
persistência, concorrência, relatórios, cadastro/hash, administrador, login/JWT,
Bearer e autorização. Usa bancos e chaves temporários, preservando os dados
reais. O transporte é httpx2, compatível com o TestClient instalado.

O demonstrador executa os 12 cenários por HTTP real, em dois processos Uvicorn
sucessivos sobre o mesmo banco temporário. Registra 55 requisições e respostas JSON
em `docs/evidencias/aps4-regressao.json`. Uma nova execução
substitui essa evidência. A auditoria direta do arquivo SQLite existe somente
nos testes; a aplicação usa ORM.

Veja a matriz e o roteiro em [docs/APS4-ETAPA-8.md](docs/APS4-ETAPA-8.md).
Os 12 cenários de segurança foram demonstrados por HTTP real, incluindo senha
como hash, login, duplicidade, token inválido e expirado, 401/403, administrador,
/auth/me e persistência. O fluxo Bearer foi operado visualmente no Swagger
(401/200/401), com registros em `docs/evidencias/aps4-etapa8/`. Os 12 cenários
completos não foram executados individualmente pela interface Swagger.

## Pacote de entrega

```powershell
.\.venv\Scripts\python.exe scripts\preparar_entrega.py
```

Gera ZIP, manifesto com SHA-256 por arquivo e checksum do pacote em `output/`.
Inclui código, security, `.env.example`, documentação e evidências APS4, testes e
dependências. Exclui ambientes virtuais, Git, bancos, caches, temporários, `.env`
real e históricos da APS 3. O empacotador recusa a chave local e possíveis JWTs.
Extraia em outra pasta,
crie uma nova `.venv` e siga a instalação. O manifesto permite conferir os arquivos.

**Repositório da APS 4:** [Luizgsch/APS-4-Desenvolvimento_backend](https://github.com/Luizgsch/APS-4-Desenvolvimento_backend).
O endereço utiliza sublinhado antes de backend, conforme informado pelo usuário.
As APS anteriores permanecem separadas. Os registros `docs/APS4-ETAPA-*.md` descrevem a evolução desta versão.
Os históricos `docs/ETAPA-*.md` pertencem à APS 3 e não integram o pacote APS4.

O GitHub hospeda o código e este README. Uma URL de API em execução depende de
um serviço de hospedagem Python com armazenamento persistente para eventos.db;
GitHub Pages não executa esta API FastAPI.
