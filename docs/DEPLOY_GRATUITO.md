# Deploy gratuito com contas persistentes

O Render Free suspende a API após 15 minutos sem tráfego. A primeira requisição
depois disso pode levar cerca de um minuto. Seu sistema de arquivos também é
temporário: contas e redações guardadas no SQLite local somem ao suspender,
reiniciar ou publicar novamente. Um banco PostgreSQL externo resolve a perda
de dados; ele não impede a suspensão da API gratuita.

## Configurar o banco

1. Crie um projeto no plano **Free** do [Neon](https://console.neon.tech/).
   Escolha uma região próxima da API, se disponível. O serviço Render atual
   está em Oregon.
2. Em **Connect**, copie a URL de conexão PostgreSQL da branch principal.
   Ela começa com `postgresql://` e contém usuário, senha e host. Guarde-a
   como senha: não a envie por chat nem a coloque no GitHub ou no Vercel.
3. No Render, abra o serviço **ENEM → Environment → Edit** e adicione
   `DATABASE_URL` com a URL completa. A variável pertence apenas à API.
4. Publique o backend que inclui `psycopg[binary]`. Ele cria as tabelas e
   carrega o catálogo de provas no banco vazio. Depois confira
   `https://enem-6zen.onrender.com/health/ready` e
   `https://enem-6zen.onrender.com/v1/exams?all=true`.
5. Crie uma conta de teste e faça login. Suspenda/republique a API e faça
   login novamente com a mesma conta para validar a persistência.

As contas que estavam apenas no SQLite temporário do Render não podem ser
recuperadas após a suspensão ou republicação que apagou o arquivo. Pode ser
necessário cadastrar-se uma última vez após a troca para PostgreSQL.

O arquivo `.env` local pode continuar usando SQLite para desenvolvimento.
Não compartilhe a URL do banco nos logs de suporte ou em capturas de tela.
