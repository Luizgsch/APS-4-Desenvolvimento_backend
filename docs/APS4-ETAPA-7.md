# APS 4 — Etapa 7: autorização por perfil

Data: 18/11/2026. Escopo: autorização. Etapa 8 não iniciada.

## Alterações

- Criada dependência `get_administrador()` em `security/dependencies.py`. Ela depende da identidade consultada no banco por `get_usuario_atual()`, preservando a separação das regras de segurança das rotas.
- Criação, atualização e exclusão de eventos restritas a administradores.
- Participantes e listas de inscritos deixam de ser públicos: leitura disponível a ambos os perfis autenticados; alterações de participantes somente por administradores.
- Os três relatórios restritos a administradores. Inscrições continuam disponíveis a ambos os perfis autenticados. Eventos continuam com leitura pública; /auth/me continua retornando a própria identidade.
- Autenticado sem permissão retorna 403 genérico; ausência ou invalidade de credenciais continua retornando 401. Perfil enviado por corpo, query, cabeçalhos ou claims extras não é aceito como fonte de privilégio.
- Consulta de perfil no banco ocorre em cada requisição. Rebaixamento de administrador é respeitado pelo token já emitido na próxima requisição.
- Nenhuma entidade, relação ou regra de negócio foi alterada. Usuário e participante continuam independentes.
- O script de regressão agora cria seu administrador descartável pelo serviço local, no banco temporário, antes de obter o token pelo login HTTP. Não usa cadastro público nem promoção via HTTP.
- Teste de fluxo protegido da etapa 6 atualizado para usar administrador nas operações agora restritas. Testes de token ausente/inválido/expirado passaram a incluir as novas consultas protegidas.
- README atualizado com matriz final de permissões e justificativas das decisões adicionais.

## Regras mínimas e decisões adicionais

| Operação | Regra aplicada | Origem |
| --- | --- | --- |
| Criar, alterar e excluir eventos | Somente administrador | Mínimo da seção 8 |
| Consultar eventos | Ambos os perfis; também público | Acesso dos perfis exigido; acesso público mantido como decisão da equipe |
| Consultar participantes e inscritos | Ambos os perfis autenticados | Administrador exigido; acesso comum e exigência de autenticação são decisões adicionais |
| Criar, alterar e excluir participantes | Somente administrador | Decisão adicional; seção 7 exige pelo menos autenticação |
| Realizar inscrições | Ambos os perfis autenticados | Mínimo das seções 7 e 8 |
| Consultar relatórios | Somente administrador | Acesso do administrador exigido; exclusividade é decisão adicional |
| Consultar /auth/me | Próprio usuário autenticado | Seção 9 |

Usuários comuns podem consultar nome, e-mail e curso de todos os participantes para realizar inscrições. Visitantes anônimos não podem consultar esses dados. Não há vínculo de propriedade entre usuário e participante: o identificador de participante da inscrição seleciona a entidade de negócio, enquanto o token identifica quem está autenticado. É permitido aos autenticados inscrever qualquer participante já cadastrado. Essa regra acadêmica evita criar uma associação que o PDF não exige e que os dados anteriores não possuem; administradores controlam o cadastro dos participantes.

## Requisitos do PDF atendidos nesta etapa

- **Seções 7 e 8:** autenticação preservada, autorização no servidor, perfis e 403 para autenticado sem permissão; restrição das alterações de eventos; inscrições disponíveis aos autenticados; acessos adicionais definidos e documentados.
- **Seção 10:** CRUD, relacionamentos, controle de vagas, duplicidade, integridade e relatórios preservados conforme permissões.
- **Seção 11:** distinção entre 401 e 403, sem expor credenciais.

As regras adicionais estão identificadas acima; não são apresentadas como exigências literais do professor.

## Testes e evidências

Em `docs/evidencias/aps4-etapa7/`:

Resultado final: **112 testes aprovados** (104 anteriores e 8 novos), pip check sem conflitos e `git diff --check` sem erros. Os 12 cenários de continuidade passaram com administrador temporário; outras 16 requisições HTTP reais demonstraram permissões e a distinção 401/403. Concorrência, vagas, duplicidades e relatórios continuam aprovados. Servidores de teste encerrados; APS 3 e bancos reais preservados.

- `testes-autorizacao.txt`: 8 testes novos. Usuário comum recebe 403 nas seis alterações de eventos/participantes e nos três relatórios, sem alterar dados; pode consultar eventos/participantes/inscritos e inscrever respeitando vagas e duplicidade; visitante recebe 401 nos novos acessos protegidos; administrador executa operações; perfil falso em claims/corpo/query/cabeçalhos não concede acesso; mudança no banco afeta tokens anteriores; OpenAPI e inexistência de endpoint de promoção.
- `testes.txt`: regressão completa, incluindo concorrência, cascatas, capacidade, persistência e segurança das etapas anteriores.
- `dependencias.txt`: pip check.
- `cenarios-regressao.json`: 12 cenários de continuidade com administrador temporário e login HTTP, incluindo reinicialização.
- `http.json`: demonstração real de 401/403 e operações de administrador/usuário comum, com tokens e senhas omitidos.
- `preservacao.json`: hashes confirmando que APS 3 e bancos reais permanecem preservados, sem chave local em arquivos versionáveis.

Comandos de reprodução:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 scripts\validar_cenarios.py
```

Os testes não substituem a dependência de autenticação: usam contas, chaves, bancos e login reais de teste. As alterações diretas de perfil aparecem somente nos testes de revogação, em banco temporário, para simular mudança de estado; não existe rota pública para realizar essa alteração.

## Pendências

- Etapa 8: consolidar os 12 cenários de segurança exigidos, evidências finais e demonstração de Bearer no Swagger.
- Etapa 9: documentação e pacote finais, conferência de segredos e repositório próprio da APS 4.
- Interação visual com Swagger ainda pendente. OpenAPI e HTTP são verificações automatizadas.
- Nenhuma conta ou dado real foi criado ou alterado nesta etapa.

Etapa 8 não iniciada.
