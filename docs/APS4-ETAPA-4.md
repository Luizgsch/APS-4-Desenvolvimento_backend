# APS 4 — Etapa 4: criação controlada de administrador

Data: 18/11/2026. Escopo: procedimento local de criação. Etapa 5 não iniciada.

## Alterações

- Criado `scripts/criar_administrador.py`, executado localmente com o Python da `.venv`.
- Nome e e-mail são solicitados pelo terminal; senha e confirmação usam `getpass`, sem eco. Se `getpass` sinalizar que não consegue ocultar a entrada, o comando interrompe o procedimento.
- Não há senha padrão, credencial fixa, argumento de senha ou leitura de senha por variável de ambiente.
- O comando exibe o banco de destino, reutiliza `UsuarioCreate` para validar os dados e só acessa o banco após a confirmação e a validação.
- `service/usuario_service.py` passou a oferecer `criar_administrador()`. Cadastro comum e criação administrativa compartilham a persistência e o serviço de hash da etapa 3.
- O cadastro público mantém `perfil="usuario"`; somente o comando local chama a criação administrativa. Nenhum controller importa a função administrativa.
- Nenhuma conta existente é promovida ou alterada. E-mail duplicado é recusado e recebe mensagem explícita. A execução repetida preserva o hash e o perfil existentes.
- Perfis permitidos são validados no serviço compartilhado e pelo CHECK já existente no banco: `usuario` e `administrador`.
- Erros de validação e banco não mostram senha, hash, parâmetros SQL nem traceback. A confirmação de sucesso mostra apenas id, e-mail e perfil.
- README atualizado com o procedimento e seus limites. Não houve mudança de dependências ou endpoints.

## Requisitos do PDF e decisões

- **Seção 3.1:** estratégia segura e documentada para criar administradores iniciais; impossibilidade de obter privilégios pelo corpo do cadastro público.
- **Seção 8:** perfis `administrador` e `usuario` definidos e validados. As permissões das rotas serão aplicadas na etapa 7; não são consideradas concluídas aqui.

O professor exige uma estratégia segura e documentada; não impõe um comando específico. O comando local, senha oculta com confirmação, ausência de argumentos de credenciais, recusa de promoção de contas existentes e códigos de saída são decisões de implementação. O acesso ao terminal, ao projeto e ao arquivo SQLite deve ficar com quem administra a instalação: o comando não substitui os controles de acesso do sistema operacional.

## Execução

```powershell
cd D:\Projetos\APS-4-Desenvolvimento-backend
.\.venv\Scripts\python.exe scripts\criar_administrador.py
```

Informe nome, e-mail e senha de sua escolha no terminal local. As mesmas regras da etapa 3 são aplicadas: nome de 1 a 120 caracteres após remover espaços externos, e-mail válido normalizado e único, senha entre 8 e 128 caracteres, não composta somente por espaços. A confirmação é exata, preservando espaços de senhas válidas.

Não é preciso iniciar a API nem informar JWT_SECRET_KEY para esse comando: criação local não emite tokens. Tabelas ausentes são criadas por `create_all()` sem apagar dados. Se o e-mail já existir, nenhuma conta será criada ou promovida; use outro e-mail.

Ajuda: `.\.venv\Scripts\python.exe scripts\criar_administrador.py --help`.
Códigos de saída: 0 sucesso/ajuda; 1 e-mail duplicado ou erro de banco; 2 dados inválidos, argumentos não permitidos ou impossibilidade de ocultar senha; 130 interrupção da entrada.

## Testes e evidências

Evidências atuais: `docs/evidencias/aps4-etapa4/`.

Resultado final: **78 testes aprovados** (68 anteriores e 10 novos), `pip check` sem conflitos e `git diff --check` sem erros. Os hashes confirmaram preservação da APS 3 e dos bancos reais; a chave local continua fora dos arquivos versionáveis.

- `testes-administrador.txt`: 10 testes específicos aprovados. Criação administrativa e hash Argon2id; confirmação diferente; validações; duplicidade sem promoção de conta pública; repetição sem alteração de hash; recusa do fallback de senha visível; cancelamento; rollback e mensagem genérica; recusa de argumentos sem eco e execução da ajuda fora da pasta; cadastro público comum e inexistência de endpoint administrativo.
- `testes.txt`: regressão completa com as funcionalidades anteriores e os novos testes.
- `dependencias.txt`: verificação de compatibilidade por `pip check`.
- `preservacao.json`: comparação dos hashes da APS 3 e de ambos os bancos reais, sem expor credenciais.

As entradas do terminal são simuladas nos testes. A ajuda também é executada em subprocesso fora da pasta do projeto. Os testes usam exclusivamente bancos temporários e validam o hash pela mesma função de verificação usada no projeto. Nenhuma senha administrativa real foi escolhida, solicitada pela conversa ou gravada no banco de trabalho.

Para repetir:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_criar_administrador.py -v
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

## Pendências e limitações

- O operador deverá executar o comando em terminal interativo para criar sua conta administrativa real. Nenhuma credencial foi inventada ou compartilhada nesta entrega.
- Digitação oculta em terminal real não foi verificada manualmente; chamadas, tratamento do fallback e resultados persistidos foram testados de forma automatizada.
- Login/JWT: etapa 5. Proteção e permissões: etapas 6 e 7. A existência de perfis ainda não restringe as rotas atuais.
- Remoto e empacotador herdados continuam pendentes para a entrega final.
- A pasta da APS 3 e os bancos existentes permanecem preservados.

Etapa 5 não iniciada.
