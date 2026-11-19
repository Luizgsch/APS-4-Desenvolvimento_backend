# APS 4 — Etapa 2: configuração de segurança

Data: 18/11/2026. Escopo: dependências e configuração. Etapa 3 não iniciada.

## Alterações

- Instalados `pwdlib[argon2]==0.4.2` e `PyJWT==2.15.1`, conforme as sugestões de bibliotecas do PDF.
- Instalado `python-dotenv==1.2.4` para leitura do arquivo local. Dependências transitivas também foram fixadas no `requirements.txt`, mantendo a convenção da base.
- Criado `security/config.py`, separado das rotas. A função `load_security_settings()` lê `.env` na raiz e as variáveis do processo, com prioridade para estas últimas. A leitura não altera `os.environ` e não interpola valores do arquivo.
- Algoritmo permitido: `HS256`, fixo no servidor. Duração padrão: 30 minutos; `ACCESS_TOKEN_EXPIRE_MINUTES` permite definir outro inteiro positivo.
- `JWT_SECRET_KEY` é obrigatória, sem fallback. Valores vazios, menores que 32 bytes ou iguais ao exemplo são rejeitados. Mensagens de erro não mostram os valores.
- A chave é encapsulada em `SecretStr` e excluída do `repr` da configuração. O valor só deverá ser extraído explicitamente pelo futuro serviço JWT.
- Criado `.env.example` com valor fictício. A preparação gerou uma chave local com `secrets.token_urlsafe(48)` apenas quando `.env` estava ausente, sem imprimir o valor e sem sobrescrever configurações existentes.
- `.gitignore` ampliado para `.env.*`, `.key` e `.pem`, mantendo `.env.example` versionável.
- README atualizado com configuração, geração de chave e limites do estado atual.

## Relação com o PDF

- **Seção 4:** bibliotecas de hash apropriadas preparadas e dependências registradas. Hash de senhas de usuários permanece para a etapa 3.
- **Seção 6:** chave externa ao código, algoritmo permitido e duração definidos. Geração e validação de tokens permanecem para a etapa 5.
- **Seção 15:** instruções reproduzíveis, dependências e exemplo sem segredo real preparados. A entrega completa permanece para a etapa 9.

O professor exige hash apropriado, assinatura, chave externa, algoritmo, expiração e proteção dos segredos. `pwdlib`/Argon2 e PyJWT são sugestões do documento. HS256, 30 minutos, mínimo de 32 bytes, leitura opcional de `.env`, prioridade do ambiente e `SecretStr` são decisões de implementação. Comprimento mínimo não comprova aleatoriedade; o procedimento documentado usa o gerador `secrets`.

## Validação

As evidências ficam em `docs/evidencias/aps4-etapa2/`:

Resultado: **57 testes aprovados**, `pip check` sem conflitos e smoke tests aprovados. A comparação SHA-256 confirmou preservação da APS 3 e de ambos os bancos reais. `git diff --check` passou.

- `dependencias.txt`: verificação de compatibilidade por `pip check`.
- `testes.txt`: regressão da base e testes da configuração. Os novos testes verificam chave ausente, vazia, curta e fictícia; segredo omitido; algoritmo fixo; prioridade do processo e duração inválida.
- `verificacao.json`: smoke tests das bibliotecas com credenciais exclusivamente temporárias; validação da configuração local sem exibir a chave; preservação da APS 3 e dos bancos por SHA-256.

Os smoke tests usam `PasswordHash.recommended()` para verificar Argon2id, uma senha correta e uma incorreta. PyJWT é exercitado com chave temporária, assinatura HS256 e decodificação com lista explícita de algoritmos permitidos. Isso valida a instalação das bibliotecas, sem criar serviços ou endpoints.

Comandos para repetir:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
```

Referências técnicas consultadas: [pwdlib](https://frankie567.github.io/pwdlib/) e [PyJWT](https://pyjwt.readthedocs.io/en/stable/). O fluxo das etapas e os requisitos acadêmicos continuam definidos pelo texto do usuário e pelo PDF.

## Pendências

- A configuração ainda não é consumida pela aplicação: os serviços de segurança futuros deverão carregá-la antes de realizar operações. Importar o módulo não exige chave nem protege rotas automaticamente.
- Usuários, armazenamento de hash, criação de administrador, login, validação JWT, Bearer e autorização permanecem nas próximas etapas.
- Não há endpoint novo, alteração de banco ou mudança nas regras da APS 3.
- O remoto ainda aponta para a APS 3. Nenhuma publicação foi feita.
- O empacotador herdado ainda tem nome de APS 3 e não inclui `security/` nem `.env.example`. Sua adaptação fica para a etapa 9; ele não foi executado nesta etapa.
- Etapa 3 aguarda solicitação do usuário.
