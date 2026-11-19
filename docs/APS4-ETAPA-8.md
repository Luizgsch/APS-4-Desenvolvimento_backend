# APS 4 — Etapa 8: testes e regressão

Data: 18/11/2026. Escopo limitado aos testes e suas evidências. Etapa 9 não iniciada.

## Alterações

- Criado `scripts/validar_seguranca.py`, que executa os 12 cenários da seção 13 por HTTP real com Uvicorn, usando somente banco e chave temporários.
- O script registra requisições, status esperado/observado, respostas, hash verificado e persistência. Senhas, hashes e tokens são ocultados nas evidências; respostas são verificadas contra valores sensíveis conhecidos antes da gravação.
- Criado `scripts/demonstrar_swagger.py` para abrir um servidor local isolado com administrador descartável. A URL usa porta livre e o banco fica em diretório temporário. Credenciais ficam apenas em `tmp/`, ignorado pelo Git, e são removidas ao encerrar.
- Executados os 112 testes existentes e os cenários de regressão de negócio, sem mudanças nas regras da API.
- README atualizado com reprodução dos testes e estado observado do Swagger.

## Cenários da seção 13

Todos aprovados. Evidência detalhada: `docs/evidencias/aps4-etapa8/cenarios-seguranca.json`.

Foram registradas **41 requisições** nesses 12 cenários e **55 requisições** nos 12 cenários adicionais de continuidade. O fluxo visual do Swagger também foi confirmado pelos registros 401/200/401 no servidor. Ao terminar, o servidor descartável foi encerrado e suas fixtures foram removidas.

| Nº | Cenário | Resultado observado |
| --- | --- | --- |
| 1 | Cadastro de usuário | 201; apenas id/nome/email/perfil; extras administrativos e entradas inválidas retornam 422 |
| 2 | Senha armazenada como hash | Arquivo SQLite contém Argon2id, sem coluna de senha; verificação correta passa e incorreta falha |
| 3 | E-mail duplicado | 409, inclusive variação de maiúsculas |
| 4 | Login válido | 200 com access_token e token_type bearer |
| 5 | Login inválido | E-mail inexistente e senha incorreta retornam o mesmo 401 |
| 6 | Rota protegida sem token | 401 com WWW-Authenticate Bearer |
| 7 | Rota protegida com token válido | /auth/me e consulta de participantes retornam 200 |
| 8 | Token inválido ou expirado | Ambos testados separadamente: 401; assinatura incorreta, none, algoritmo alternativo e usuário inexistente também rejeitados |
| 9 | Comum em operação administrativa | Criar evento e consultar relatório retornam 403 |
| 10 | Administrador em operação administrativa | Evento e participante criados com 201; inscrição por usuário comum permitida |
| 11 | /auth/me | 200 com identidade do token; id de query ignorado; sem senha/hash |
| 12 | Funcionalidades e relatórios da APS 3 | Após reiniciar: usuários/evento/inscrição persistidos; três relatórios corretos; atualização, exclusão, cascata, duplicidade e capacidade conferidos |

Requisitos adicionais do usuário também verificados: perfil administrativo no corpo rejeitado, ausência de valores de senha/hash em erros de validação, banco isolado, persistência após reinicializar e funcionamento do Bearer no Swagger.

## Suíte e regressão

- **112 testes aprovados**, abrangendo cadastro, hash, configuração, JWT, autenticação, autorização, comando administrativo, CRUD, concorrência, vagas, duplicidade, cascatas e relatórios.
- `pip check`: sem dependências quebradas.
- Os **12 cenários de continuidade** do script herdado foram repetidos com administrador temporário e login HTTP. São cenários de negócio diferentes dos 12 cenários de segurança acima.
- A integridade do SQLite temporário foi conferida: integrity_check ok e foreign_key_check vazio.
- Nenhum teste utiliza os bancos de trabalho. Hashes da APS 3 e dos dois bancos reais são comparados com a base da etapa 1.
- `git diff --check` passou. Ambos os bancos existentes também passaram nas verificações de integridade em modo somente leitura e mantiveram seus hashes anteriores.

## Swagger: resultado visual observado

O acesso integrado ao navegador estava indisponível (`The browser access host is unavailable`), mas o navegador Brave pôde ser controlado pela interface nativa. Isso é uma limitação da ferramenta de acesso ao navegador, não uma falha da API. Nenhuma configuração de segurança do navegador foi alterada.

Foi usada a skill computer-use para operar `/docs` do servidor descartável:

1. Expandido GET /auth/me, Try it out e Execute sem autorização: **401**, mensagem genérica e WWW-Authenticate Bearer.
2. Aberto Authorize, token temporário inserido sem prefixo e Apply credentials: esquema **BearerJWT (http, Bearer)** mostrou **Authorized**, com valor mascarado.
3. Execute em /auth/me: **200**, contendo somente id, nome, email e perfil do administrador de teste; o Swagger enviou Authorization Bearer.
4. Remove authorization e Close; nova execução de /auth/me: **401**.

Evidências: `swagger-visual.json` registra o que foi observado; `swagger-http.txt` contém as três requisições correspondentes no log do servidor. As capturas da interface foram inspecionadas durante a execução, sem exportar tokens para os arquivos de entrega.

O fluxo Bearer foi operado visualmente. Os 12 cenários completos foram demonstrados pelo script HTTP, não individualmente pela interface Swagger. A verificação de hash ocorreu diretamente no arquivo SQLite temporário, pois esse dado não deve estar acessível em uma resposta pública.

## Requisitos e decisões

- **Seções 7, 10, 11 e 13:** testes de autenticação, continuidade, respostas e cenários mínimos demonstrados; comportamento da interface Swagger verificado.
- Executar os cenários em servidor real com banco/chave temporários, ocultar segredos nos registros e criar um launcher descartável são decisões de implementação para tornar as evidências reproduzíveis sem alterar os dados existentes.
- A validação técnica desta etapa não substitui o fechamento documental e a conferência completa de entrega da etapa 9.

## Reprodução

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 scripts\validar_seguranca.py
.\.venv\Scripts\python.exe -X utf8 scripts\validar_cenarios.py
.\.venv\Scripts\python.exe -X utf8 scripts\demonstrar_swagger.py
```

O último comando permanece ativo para interação manual. Abra a URL exibida e use somente as credenciais descartáveis de `tmp/aps4-swagger/sessao.json`. Ao terminar, em outro terminal:

```powershell
New-Item -ItemType File -Force tmp/aps4-swagger/parar
```

## Pendências e limitações

- Os 12 cenários foram registrados por HTTP; a operação visual do Swagger cobriu autorização, consulta autenticada e remoção da autorização.
- Etapa 9: revisão integral do README, requirements e entrega, adaptação do empacotador, conferência dos requisitos mínimos e definição/publicação no repositório próprio.
- Não houve criação de contas reais, alteração de dados existentes, commit ou push nesta etapa.

Etapa 9 não iniciada.
