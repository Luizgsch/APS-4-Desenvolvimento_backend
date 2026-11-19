# APS 4 — Etapa 3: usuários e hash de senhas

Data: 18/11/2026. Escopo limitado à etapa 3. Login e criação controlada de administrador não foram implementados.

## Alterações

- Entidade `Usuario` independente de `Participante`: id, nome, email, senha_hash e perfil. E-mail único no SQLite, com NOCASE; perfil limitado por CHECK a `usuario` ou `administrador`.
- Schema de entrada `UsuarioCreate` separado de `UsuarioRead`. A resposta pública contém somente id, nome, email e perfil.
- `POST /usuarios` público retorna 201. O serviço constrói explicitamente a entidade e fixa `perfil="usuario"`. Todos os campos extras são rejeitados com 422, inclusive perfil, id e senha_hash.
- Nome obrigatório, entre 1 e 120 caracteres após remover espaços externos; e-mail validado por EmailStr, normalizado para minúsculas e único no banco.
- Senha obrigatória com 8 a 128 caracteres, sem aceitar somente espaços. Espaços de uma senha válida são preservados. SecretStr mascara a senha na representação do schema.
- `security/passwords.py` centraliza geração e verificação por `pwdlib.PasswordHash.recommended()`, usando Argon2id e salt aleatório da biblioteca. Nenhuma senha original é persistida.
- Duplicidade de e-mail retorna 409; outras falhas SQLAlchemy continuam como 500 genérico. O conflito é identificado pela restrição específica, com rollback.
- Handler de validação retorna mensagem fixa em `/usuarios`, inclusive para campos extras e JSON malformado. Nenhum corpo, input ou contexto de erro é devolvido. O comportamento de validação das rotas anteriores é preservado.
- Modelo registrado na metadata: `create_all()` adiciona a tabela ao iniciar a API, sem apagar tabelas ou dados existentes. Nenhuma inicialização foi feita sobre os bancos reais durante os testes.
- README atualizado com campos, regras e exemplo de cadastro. O teste herdado que enumerava três tabelas foi atualizado para incluir `usuarios`.

## Requisitos do PDF e decisões

- **Seções 3 e 3.1:** entidade/tabela, cadastro público, validações, e-mail único, resposta sem senha/hash e impedimento de escolha pública de privilégios.
- **Seção 4:** hash apropriado pela biblioteca, armazenamento exclusivo do hash e função de verificação reutilizável.
- **Seção 11:** códigos 201, 409 e 422 e respostas sem dados sensíveis. 401 e 403 pertencem às etapas de autenticação e autorização.
- A separação controller/model/schema/service/security segue a seção 12 e a arquitetura solicitada pelo usuário.

O professor exige validações mínimas e critérios de senha documentados; não determina os limites escolhidos. Os limites de nome e senha, normalização integral do e-mail, rejeição de qualquer campo extra e mensagem fixa de validação são decisões de implementação. A sugestão pwdlib/Argon2 foi adotada. Usuário e participante não possuem vínculo automático.

## Testes e evidências

Evidências em `docs/evidencias/aps4-etapa3/`:

Resultado final: **68 testes aprovados** (57 anteriores e 11 novos), pip check sem conflitos, HTTP real aprovado e `git diff --check` sem erros. Os servidores temporários foram encerrados.

- `testes-usuarios.txt`: 11 testes específicos, aprovados. Cadastro e resposta pública; Argon2id persistido e verificação correta/incorreta; salt aleatório; limites e espaços; duplicidade; tentativa de privilégio; JSON malformado; restrições no banco; persistência em outro processo; rollback e erros genéricos; OpenAPI com schemas separados.
- `testes.txt`: execução da suíte completa, incluindo CRUD, inscrições, relatórios e configuração de segurança.
- `dependencias.txt`: pip check sem conflitos.
- `http.json`: HTTP real com Uvicorn e banco temporário: cadastro 201, duplicidade 409 e tentativa de perfil administrativo 422. Valores de senha e hash omitidos das evidências; o hash foi verificado diretamente no banco temporário.
- `preservacao.json`: hashes confirmam preservação dos arquivos da APS 3 e de ambos os bancos reais.

Na primeira regressão, um teste antigo esperava exatamente três tabelas. Ele foi atualizado para incluir a nova tabela. Nenhuma regra anterior precisou de alteração. Na primeira demonstração HTTP, a limpeza do banco temporário encontrou WinError 32 por conexão SQLite de verificação ainda aberta; corrigido com fechamento explícito e execução repetida com sucesso. Isso não afetou dados reais.

Para repetir:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
```

Referências técnicas: [pwdlib](https://frankie567.github.io/pwdlib/) e [estrutura dos erros Pydantic](https://docs.pydantic.dev/latest/errors/errors/). A resposta fixa de validação evita devolver os valores de entrada presentes nos erros padrão.

## Pendências

- Etapa 4: procedimento controlado para administrador; nenhum usuário público é promovido automaticamente.
- Login, JWT, /auth/me, proteção das rotas e autorização permanecem nas etapas seguintes.
- A interface Swagger não foi operada visualmente; OpenAPI foi validado automaticamente e a rota foi exercitada por HTTP real.
- O remoto e o empacotador herdados continuam pendentes de adaptação para a entrega da APS 4.
- A tabela será criada no banco local na próxima inicialização normal da API. Os testes criaram tabelas apenas em bancos temporários.

Etapa 4 não iniciada.
