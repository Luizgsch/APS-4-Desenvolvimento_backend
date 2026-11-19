# APS 4 — Etapa 6: usuário autenticado e proteção das rotas

Data: 18/11/2026. Somente etapa 6. Autorização por perfil não foi antecipada.

## Alterações

- Criado `security/dependencies.py` com HTTPBearer e dependência `get_usuario_atual()`.
- O esquema BearerJWT é documentado no OpenAPI e permite inserir o token pelo botão Authorize do Swagger. O login continua recebendo JSON, sem mudar para formulário OAuth2.
- A dependência valida o JWT pela função da etapa 5, consulta o usuário no banco e retorna um DTO público UsuarioRead. Não confia em nome, perfil ou identificador livre enviado pelo cliente.
- Criado GET /auth/me, com id, nome, email e perfil do usuário atual e Cache-Control no-store. Senha e hash não são retornados.
- Protegidos cadastro, atualização e exclusão de eventos e participantes; realização de inscrições; os três relatórios; e /auth/me.
- Token ausente, esquema incorreto, token inválido/expirado/adulterado e usuário inexistente retornam o mesmo 401 com WWW-Authenticate Bearer. Problema de configuração é 503 e falha de banco é 500 genérico.
- A leitura da identidade usa uma sessão curta própria, encerrada antes da transação de negócio. Isso evita manter uma leitura SQLite aberta antes do bloqueio de escrita usado nas inscrições e alterações de capacidade. Os dados da identidade retornados já foram carregados do banco.
- Testes legados de negócio passaram a usar um administrador temporário criado pelo serviço local e login HTTP real. Não há override da dependência de autenticação. Clientes recriados após reinicialização mantêm o cabeçalho do token.
- O teste de consultas de relatório agora espera uma consulta de identidade e uma consulta consolidada por relatório; continua verificando ausência de consultas adicionais por linha.
- O script `validar_cenarios.py` passou a criar conta descartável, fazer login, enviar Bearer e renovar o login ao reiniciar o servidor. Sua saída padrão passa a `docs/evidencias/aps4-regressao.json`, preservando o registro histórico da APS 3. Quando executado pelo main do script, a chave também é temporária.
- README atualizado com matriz de acesso e instruções para Bearer no Swagger.

## Requisitos e decisões

- **Seção 6:** validador JWT integrado à autenticação HTTP.
- **Seção 7:** Bearer e dependência centralizada; todas as operações mínimas exigem autenticação.
- **Seção 9:** /auth/me usa a identidade do token validado e consulta o banco, sem senha/hash.
- **Seção 11:** 401 para credenciais ausentes ou inválidas e mensagens genéricas.

O professor exige autenticação para as operações mínimas. HTTPBearer(auto_error=False), nome BearerJWT, DTO público, sessão curta de identidade, cabeçalhos e separação de erros de infraestrutura são decisões de implementação. Consultas públicas de eventos, participantes e inscrições permanecem como antes nesta etapa; as regras adicionais de acesso serão definidas na etapa 7.

## Testes e evidências

Em `docs/evidencias/aps4-etapa6/`:

Resultado final: **104 testes aprovados** (94 anteriores e 10 novos), pip check sem conflitos e 12 cenários de continuidade aprovados com Bearer por HTTP real, incluindo reinicialização. /auth/me retornou 200 com token válido e 401 sem token, com token inválido, expirado, de usuário inexistente e de usuário removido. APS 3 e bancos reais preservados; servidores de teste encerrados.

- `testes-protecao.txt`: 10 testes específicos, sem desativar a autenticação. Todas as rotas mínimas sem token, com token inválido e expirado; /auth/me sem segredos; id de query ignorado; consulta da identidade atual no banco; claims extras não substituem perfil/nome; token de usuário inexistente/removido; esquema incorreto; token de query rejeitado; operações completas com token válido; OpenAPI; erros genéricos e fechamento de sessão.
- `testes.txt`: regressão completa, incluindo concorrência, duplicidade, capacidade, cascatas, persistência, três relatórios e etapas de segurança anteriores.
- `dependencias.txt`: pip check.
- `cenarios-regressao.json`: 12 cenários de continuidade da APS 3, agora autenticados por HTTP real, com reinicialização do servidor. Não são os 12 cenários completos de entrega da APS 4, previstos para etapa 8.
- `http.json`: demonstração HTTP real de /auth/me e rejeição de credenciais inválidas, sem registrar tokens ou senhas.
- `preservacao.json`: hashes da APS 3 e bancos reais, com segredo local fora dos arquivos versionáveis.

Reprodução:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 scripts\validar_cenarios.py
```

Referência técnica: [HTTPBearer no FastAPI](https://fastapi.tiangolo.com/reference/security/). A opção auto_error=False permite devolver o mesmo erro 401 definido pela aplicação para cabeçalho ausente ou inadequado.

## Pendências e limites

- Etapa 7: restringir operações administrativas e definir acessos adicionais. Nesta etapa, um usuário comum autenticado ainda pode alterar eventos; isso não representa a entrega final da autorização.
- Os testes verificaram OpenAPI e HTTP; a interação visual com o botão Authorize no Swagger ainda não foi demonstrada.
- Não houve criação de contas reais nem alteração dos bancos de trabalho. Nenhum segredo real foi registrado nas evidências.
- Remoto e empacotador continuam pendentes para entrega final.

Etapa 7 não iniciada.
