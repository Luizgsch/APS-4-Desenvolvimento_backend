# APS 4 — Etapa 5: login e JWT

Data: 18/11/2026. Somente etapa 5. A proteção HTTP das rotas pertence à etapa 6.

## Alterações

- Criados `schema/auth_schema.py`, `controller/auth_controller.py`, `service/auth_service.py` e `security/tokens.py`, mantendo as responsabilidades separadas.
- `POST /auth/login` recebe JSON com email e senha. E-mail é validado e normalizado como no cadastro; senha mantém espaços e usa SecretStr.
- A senha é verificada pelo serviço já existente de pwdlib/Argon2. Uma verificação com hash fictício, aleatório e não persistido também ocorre quando o e-mail não existe, evitando o retorno antecipado sem Argon2. Não se afirma tempo constante para a requisição inteira.
- Sucesso retorna 200 com somente access_token e token_type `bearer`. Cabeçalhos `Cache-Control: no-store` e `Pragma: no-cache` evitam orientar cache da resposta.
- E-mail inexistente e senha incorreta retornam 401 com a mesma mensagem genérica e `WWW-Authenticate: Bearer`. Erros de formato retornam 422 sem eco do corpo. Falhas SQLAlchemy continuam com 500 genérico. Configuração JWT inválida retorna 503 genérico, sem revelar a chave.
- Tokens HS256 contêm somente sub, iat e exp. A chave vem da configuração externa da etapa 2; a duração padrão continua sendo 30 minutos.
- `validar_token()` exige assinatura válida, algoritmo HS256 permitido explicitamente pelo servidor e presença de sub/iat/exp. A biblioteca verifica expiração e emissão; o serviço exige datas inteiras, exp posterior a iat e sub representando id inteiro positivo compatível com SQLite.
- Nenhum perfil é incluído como autoridade no token. Nenhuma senha ou hash é incluída no token ou nas respostas.
- README atualizado com login, resposta e limites da integração atual. Nenhuma dependência foi adicionada.

## Requisitos e decisões

- **Seção 5:** login por e-mail/senha, verificação pela biblioteca, resposta bearer e 401 genérico para credenciais incorretas.
- **Seção 6:** emissão e validação JWT, assinatura, segredo externo, algoritmo permitido, validade e rejeição de tokens inválidos/adulterados/expirados.
- **Seção 11:** respostas HTTP consistentes e sem exposição das credenciais nos erros de login.

O professor exige identificação e expiração; o uso das claims sub/iat/exp, exigência de iat, id decimal canônico, ausência de perfil no token e cabeçalhos de cache são decisões de implementação. Hash fictício para e-mail inexistente é uma medida adicional. HS256 e 30 minutos mantêm as decisões da etapa 2.

Erros de formato de requisição são distintos de credenciais incorretas: e-mail com formato inválido ou campo ausente recebe 422; e-mail válido inexistente ou senha incorreta recebe 401. A mensagem de 401 não identifica qual credencial falhou.

## Testes

Evidências em `docs/evidencias/aps4-etapa5/`:

Resultado final: **94 testes aprovados** (78 anteriores e 16 novos), pip check sem conflitos e `git diff --check` sem erros. HTTP real confirmou cadastro 201, login 200, credenciais incorretas 401 e JSON incompleto 422. Assinatura, expiração e identidade do token retornado foram verificadas com chave temporária. Os servidores de teste foram encerrados; APS 3 e bancos reais permanecem preservados.

- `testes-login.txt`: 8 testes de login com bancos e chaves temporários. Login válido, normalização, esquema bearer, cabeçalhos, igualdade das falhas 401, hash fictício, JSON inválido, campos extras, administrador, falhas de configuração/banco e OpenAPI JSON.
- `testes-tokens.txt`: 8 testes de JWT. Claims e duração configurada; expirado; emissão futura; assinatura com outra chave; payload adulterado; algoritmo não permitido; algoritmo none; claims ausentes; ids inválidos; datas inválidas; token malformado e validação da identidade na emissão.
- `testes.txt`: regressão completa da base e das etapas anteriores.
- `dependencias.txt`: pip check.
- `http.json`: demonstração por HTTP real com banco temporário; token e credenciais omitidos das evidências.
- `preservacao.json`: hashes da APS 3 e dos bancos reais, mais verificação de que a chave local não aparece em arquivos versionáveis.

Reprodução:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
```

Referências técnicas: [API do PyJWT](https://pyjwt.readthedocs.io/en/stable/api.html) e [exemplos de uso](https://pyjwt.readthedocs.io/en/stable/usage.html). O algoritmo permitido é definido junto da chave no servidor, sem confiar no alg informado pelo token.

## Pendências e limites

- `validar_token()` é uma função de segurança, ainda não uma dependência HTTP. Não foi criado endpoint temporário para testar tokens.
- Bearer nas rotas, consulta do usuário do token no banco, rejeição de usuário inexistente e GET /auth/me pertencem à etapa 6.
- Permissões por perfil pertencem à etapa 7. As rotas anteriores ainda não estão protegidas.
- Swagger visual e seus controles Bearer ainda não foram demonstrados. OpenAPI e chamadas HTTP foram verificados automaticamente.
- Nenhuma conta real foi criada ou modificada. APS 3 e bancos existentes preservados.
- Remoto e pacote final continuam pendentes.

Etapa 6 não iniciada.
